import axios, { type AxiosRequestConfig } from "axios";
import { useAuthStore } from "../stores/auth";

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach Bearer token from auth store to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token && token !== "authenticated") {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Token refresh with request queuing ---
let isRefreshing = false;
let failedQueue: {
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
  config: AxiosRequestConfig;
}[] = [];

function processQueue(error: unknown | null) {
  failedQueue.forEach(({ resolve, reject, config }) => {
    if (error) {
      reject(error);
    } else {
      resolve(api(config));
    }
  });
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    // Only handle 401s, and only once per request
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    // If the request didn't have a Bearer token (e.g. zustand not rehydrated
    // yet), don't try to refresh — just fail silently without logout.
    const hadToken = original.headers?.Authorization?.startsWith("Bearer ");
    if (!hadToken) {
      return Promise.reject(error);
    }

    original._retry = true;

    // If already refreshing, queue this request to retry after refresh completes
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject, config: original });
      });
    }

    isRefreshing = true;
    const store = useAuthStore.getState();

    try {
      // Send refresh_token in the request body (cookies may not work through proxy)
      const refreshPayload: Record<string, string> = {};
      if (store.refreshToken) {
        refreshPayload.refresh_token = store.refreshToken;
      }

      const res = await axios.post("/api/v1/auth/refresh", refreshPayload, {
        withCredentials: true,
      });

      const newAccessToken = res.data.access_token;
      if (newAccessToken) {
        store.setToken(newAccessToken);
        original.headers.Authorization = `Bearer ${newAccessToken}`;
      }

      isRefreshing = false;
      processQueue(null);
      return api(original);
    } catch (refreshError) {
      isRefreshing = false;
      processQueue(refreshError);

      // Only logout if the refresh explicitly returned 401 (token truly expired).
      // Don't logout on network errors or other failures.
      if (
        axios.isAxiosError(refreshError) &&
        refreshError.response?.status === 401
      ) {
        store.logout();
        window.location.href = "/login";
      }

      return Promise.reject(error);
    }
  }
);

export default api;
