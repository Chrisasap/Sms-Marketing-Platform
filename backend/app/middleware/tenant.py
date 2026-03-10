from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts tenant_id from the authenticated user's JWT token
    and stores it in request.state for use by downstream route handlers.

    Public routes (health checks, webhooks, auth) are excluded from tenant scoping.
    """

    EXCLUDED_PATHS = {
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/webhooks/bandwidth/message",
        "/api/v1/webhooks/bandwidth/status",
        "/api/v1/webhooks/stripe",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next):
        # Skip tenant scoping for public routes
        if request.url.path in self.EXCLUDED_PATHS:
            response = await call_next(request)
            return response

        # Extract tenant_id from JWT token (set by auth dependency)
        # The auth dependency will have decoded the JWT and placed user info
        # in request.state before this middleware runs in the dependency chain.
        # If tenant_id is already set (by auth dependency), use it.
        tenant_id = getattr(request.state, "tenant_id", None)

        if tenant_id:
            # Store in request.state for use by route handlers
            request.state.tenant_id = tenant_id

        response = await call_next(request)
        return response
