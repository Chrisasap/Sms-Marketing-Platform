import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "./stores/auth";
import Layout from "./components/layout/Layout";
import AdminLayout from "./components/layout/AdminLayout";
import CommandPalette from "./components/ui/CommandPalette";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Campaigns from "./pages/Campaigns";
import CampaignNew from "./pages/CampaignNew";
import Contacts from "./pages/Contacts";
import ContactImport from "./pages/ContactImport";
import Lists from "./pages/Lists";
import Inbox from "./pages/Inbox";
import Numbers from "./pages/Numbers";
import Compliance from "./pages/Compliance";
import BrandRegister from "./pages/BrandRegister";
import CampaignRegister from "./pages/CampaignRegister";
import AIAgents from "./pages/AIAgents";
import AIAgentConfig from "./pages/AIAgentConfig";
import Templates from "./pages/Templates";
import Automations from "./pages/Automations";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";
import Billing from "./pages/Billing";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminTenants from "./pages/admin/AdminTenants";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminDLCQueueV2 from "./pages/admin/AdminDLCQueueV2";
import AdminDLCAnalytics from "./pages/admin/AdminDLCAnalytics";
import AdminRevenue from "./pages/admin/AdminRevenue";
import AdminSystem from "./pages/admin/AdminSystem";
import AdminAuditLog from "./pages/admin/AdminAuditLog";
import AdminSettings from "./pages/admin/AdminSettings";
import type { ReactNode } from "react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { token } = useAuthStore();
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <CommandPalette />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/campaigns" element={<Campaigns />} />
            <Route path="/campaigns/new" element={<CampaignNew />} />
            <Route path="/contacts" element={<Contacts />} />
            <Route path="/contacts/import" element={<ContactImport />} />
            <Route path="/lists" element={<Lists />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/numbers" element={<Numbers />} />
            <Route path="/compliance" element={<Compliance />} />
            <Route path="/compliance/brands/new" element={<BrandRegister />} />
            <Route path="/compliance/campaigns/new" element={<CampaignRegister />} />
            <Route path="/ai-agents" element={<AIAgents />} />
            <Route path="/ai-agents/:id" element={<AIAgentConfig />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/automations" element={<Automations />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/settings/billing" element={<Billing />} />
          </Route>
          <Route element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/tenants" element={<AdminTenants />} />
            <Route path="/admin/tenants/:id" element={<AdminTenants />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/dlc-queue" element={<AdminDLCQueueV2 />} />
            <Route path="/admin/dlc-analytics" element={<AdminDLCAnalytics />} />
            <Route path="/admin/revenue" element={<AdminRevenue />} />
            <Route path="/admin/system" element={<AdminSystem />} />
            <Route path="/admin/audit-log" element={<AdminAuditLog />} />
            <Route path="/admin/settings" element={<AdminSettings />} />
          </Route>
        </Routes>
        <Toaster
          position="top-right"
          toastOptions={{
            className: "!bg-navy-800 !text-white !border !border-white/10",
            duration: 4000,
          }}
        />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
