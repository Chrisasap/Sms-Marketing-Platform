from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.websocket import websocket_endpoint
from app.routers import (
    auth,
    tenants,
    contacts,
    lists,
    campaigns,
    phone_numbers,
    messages,
    inbox,
    compliance,
    analytics,
    templates,
    automations,
    ai_agents,
    admin,
    billing,
    webhooks,
    api_keys,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="BlastWave SMS API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["tenants"])
app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["contacts"])
app.include_router(lists.router, prefix="/api/v1/lists", tags=["lists"])
app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(
    phone_numbers.router, prefix="/api/v1/numbers", tags=["numbers"]
)
app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
app.include_router(inbox.router, prefix="/api/v1/inbox", tags=["inbox"])
app.include_router(
    compliance.router, prefix="/api/v1/compliance", tags=["compliance"]
)
app.include_router(
    analytics.router, prefix="/api/v1/analytics", tags=["analytics"]
)
app.include_router(
    templates.router, prefix="/api/v1/templates", tags=["templates"]
)
app.include_router(
    automations.router, prefix="/api/v1/automations", tags=["automations"]
)
app.include_router(
    ai_agents.router, prefix="/api/v1/ai-agents", tags=["ai-agents"]
)
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(
    api_keys.router, prefix="/api/v1/api-keys", tags=["api-keys"]
)


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket_endpoint(websocket)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "blastwave-sms"}
