# BlastWave SMS - Multi-Tenant SMS/MMS Marketing Platform

## Technical Specification v1.0

---

## 1. Overview

BlastWave SMS is a multi-tenant SaaS platform enabling businesses to sign up, register their brands for 10DLC compliance, manage phone numbers, build contact lists, and execute mass SMS/MMS marketing campaigns — all through a flashy, modern React dashboard with real-time analytics.

**Carrier:** Bandwidth V2 API (Messaging, Numbers, Campaign Management)
**Backend:** Python (FastAPI) + Celery + Redis + PostgreSQL
**Frontend:** React 18 + TypeScript + Tailwind CSS + Framer Motion + Recharts
**Payments:** Stripe (subscriptions + usage-based metering + prepaid credits)
**Infrastructure:** Docker Compose, Nginx, Let's Encrypt

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React SPA (Vite)                        │
│  Tailwind + Framer Motion + Recharts + React Query          │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                   Nginx Reverse Proxy                        │
│              TLS termination, rate limiting                  │
└──────┬───────────────────┬──────────────────────────────────┘
       │                   │
┌──────▼──────┐    ┌───────▼─────────────────────────────────┐
│  WebSocket  │    │         FastAPI Application              │
│  Server     │    │  REST API + Webhook Receiver + Auth      │
│  (live      │    │  + Stripe Webhooks                       │
│   updates)  │    └──────┬───────────┬───────────────────────┘
└─────────────┘           │           │
                   ┌──────▼──┐  ┌─────▼──────┐
                   │ Celery  │  │ Celery     │
                   │ Workers │  │ Beat       │
                   │ (send,  │  │ (scheduled │
                   │  import,│  │  campaigns,│
                   │  AI)    │  │  cleanup)  │
                   └────┬────┘  └────────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
   ┌──────▼──┐   ┌─────▼───┐  ┌─────▼──────┐
   │PostgreSQL│   │  Redis  │  │ Bandwidth  │
   │  (data)  │   │ (queue, │  │  V2 API    │
   │          │   │  cache, │  │            │
   │          │   │  pubsub)│  │            │
   └──────────┘   └─────────┘  └────────────┘
```

---

## 3. Multi-Tenant Data Model

### 3.1 Tenant Isolation Strategy
- **Database-level:** All tables include `tenant_id` foreign key with row-level security (RLS) policies
- **Bandwidth-level:** Each tenant maps to a Bandwidth Sub-Account (Site) with dedicated Location(s)
- **API-level:** JWT tokens embed `tenant_id`; all queries scoped automatically via SQLAlchemy middleware

### 3.2 Core Database Schema

```
tenants
├── id (UUID, PK)
├── name (company name)
├── slug (URL-safe identifier)
├── owner_user_id (FK -> users)
├── stripe_customer_id
├── stripe_subscription_id
├── plan_tier (free_trial | starter | growth | enterprise)
├── credit_balance (Decimal - prepaid SMS credits)
├── bandwidth_site_id (Bandwidth sub-account)
├── bandwidth_location_id
├── bandwidth_application_id
├── settings (JSONB - timezone, default_from, etc.)
├── status (active | suspended | cancelled)
├── created_at / updated_at
└── deleted_at (soft delete)

users
├── id (UUID, PK)
├── tenant_id (FK -> tenants)
├── email (unique)
├── password_hash (argon2)
├── first_name / last_name
├── role (owner | admin | manager | sender | viewer)
├── mfa_secret (TOTP)
├── mfa_enabled (bool)
├── last_login_at
├── is_active (bool)
├── created_at / updated_at
└── api_keys[] (hashed, scoped)

phone_numbers
├── id (UUID, PK)
├── tenant_id (FK)
├── number (E.164)
├── type (local | toll_free | short_code)
├── bandwidth_order_id
├── campaign_id (FK -> campaigns_10dlc)
├── status (active | pending | released)
├── capabilities (sms | mms | voice)
├── monthly_cost (Decimal)
├── created_at / updated_at

brands_10dlc
├── id (UUID, PK)
├── tenant_id (FK)
├── bandwidth_brand_id
├── entity_type (private_profit | public_profit | nonprofit | government | sole_proprietor)
├── legal_name / dba_name
├── ein
├── street / city / state / zip / country
├── website
├── vertical (retail | healthcare | finance | etc.)
├── stock_symbol / stock_exchange
├── trust_score (0-100, from TCR vetting)
├── vetting_status (pending | scored | vetted | failed)
├── registration_status (registered | pending | rejected)
├── created_at / updated_at

campaigns_10dlc
├── id (UUID, PK)
├── tenant_id (FK)
├── brand_id (FK -> brands_10dlc)
├── bandwidth_campaign_id
├── use_case (marketing | mixed | low_volume | etc.)
├── description
├── sample_messages (text[])
├── subscriber_optin (bool)
├── subscriber_optout (bool)
├── subscriber_help (bool)
├── number_pool (bool)
├── embedded_links (bool)
├── embedded_phone (bool)
├── age_gated (bool)
├── mps_limit (int - messages per second allowed)
├── daily_limit (int - T-Mobile daily cap)
├── status (active | pending | rejected | expired)
├── created_at / updated_at

contact_lists
├── id (UUID, PK)
├── tenant_id (FK)
├── name
├── description
├── tag_color (hex color for UI)
├── contact_count (denormalized)
├── created_at / updated_at

contacts
├── id (UUID, PK)
├── tenant_id (FK)
├── phone_number (E.164)
├── email (optional)
├── first_name / last_name
├── custom_fields (JSONB)
├── status (active | unsubscribed | bounced | blocked)
├── opted_in_at
├── opted_out_at
├── opt_in_method (web_form | keyword | import | api)
├── last_messaged_at
├── message_count (int)
├── created_at / updated_at

contact_list_members (junction)
├── contact_id (FK)
├── list_id (FK)
├── added_at

campaigns (marketing campaigns, not 10DLC campaigns)
├── id (UUID, PK)
├── tenant_id (FK)
├── name
├── type (blast | drip | triggered | ab_test)
├── status (draft | scheduled | sending | paused | completed | cancelled | failed)
├── from_number_id (FK -> phone_numbers, nullable for number pool)
├── number_pool_ids (UUID[] - for rotating sender numbers)
├── message_template (text with {{merge_tags}})
├── media_urls (text[] for MMS)
├── target_list_ids (UUID[])
├── exclude_list_ids (UUID[])
├── segment_filter (JSONB - advanced targeting rules)
├── scheduled_at (timestamp, nullable)
├── send_window_start (time - e.g., 09:00)
├── send_window_end (time - e.g., 21:00)
├── send_window_timezone
├── throttle_mps (messages per second override)
├── total_recipients (int)
├── sent_count / delivered_count / failed_count / opted_out_count
├── ab_variants (JSONB - for A/B test campaigns)
├── created_by (FK -> users)
├── created_at / updated_at

campaign_messages
├── id (UUID, PK)
├── campaign_id (FK)
├── contact_id (FK)
├── tenant_id (FK)
├── from_number (E.164)
├── to_number (E.164)
├── message_body (text)
├── media_urls (text[])
├── bandwidth_message_id
├── status (queued | sending | delivered | failed | opted_out)
├── error_code (varchar)
├── error_description (text)
├── segments (int)
├── cost (Decimal)
├── sent_at / delivered_at / failed_at
├── created_at

conversations (2-way messaging)
├── id (UUID, PK)
├── tenant_id (FK)
├── contact_id (FK)
├── phone_number_id (FK - the tenant's number)
├── contact_phone (E.164)
├── status (open | closed | archived)
├── assigned_to (FK -> users, nullable)
├── last_message_at
├── unread_count (int)
├── tags (text[])
├── created_at / updated_at

messages (individual 2-way messages)
├── id (UUID, PK)
├── conversation_id (FK)
├── tenant_id (FK)
├── direction (inbound | outbound)
├── sender_type (contact | user | ai_agent | system)
├── sender_id (UUID - user or contact)
├── body (text)
├── media_urls (text[])
├── bandwidth_message_id
├── status (queued | sending | delivered | failed | read)
├── error_code
├── segments (int)
├── cost (Decimal)
├── created_at

auto_replies
├── id (UUID, PK)
├── tenant_id (FK)
├── phone_number_id (FK, nullable - global if null)
├── trigger_type (keyword | regex | all_inbound | after_hours)
├── trigger_value (text - the keyword or regex pattern)
├── response_body (text)
├── media_urls (text[])
├── is_active (bool)
├── priority (int - for ordering)
├── created_at / updated_at

ai_agents
├── id (UUID, PK)
├── tenant_id (FK)
├── name
├── phone_number_ids (UUID[] - assigned numbers)
├── system_prompt (text - persona and instructions)
├── model (gpt-4o | claude-sonnet | etc.)
├── temperature (float)
├── max_tokens (int)
├── knowledge_base (JSONB - FAQ pairs, product info, URLs)
├── escalation_rules (JSONB - when to hand off to human)
├── is_active (bool)
├── conversation_count (int)
├── avg_response_time_ms (int)
├── created_at / updated_at

ai_agent_logs
├── id (UUID, PK)
├── agent_id (FK)
├── conversation_id (FK)
├── inbound_message (text)
├── ai_response (text)
├── model_used
├── tokens_used (int)
├── latency_ms (int)
├── escalated (bool)
├── created_at

scheduled_messages
├── id (UUID, PK)
├── tenant_id (FK)
├── contact_id (FK)
├── from_number_id (FK)
├── body (text)
├── media_urls (text[])
├── scheduled_at (timestamp)
├── status (pending | sent | cancelled | failed)
├── campaign_id (FK, nullable)
├── created_at

drip_sequences
├── id (UUID, PK)
├── tenant_id (FK)
├── name
├── trigger_event (opt_in | keyword | tag_added | manual | api)
├── is_active (bool)
├── created_at / updated_at

drip_steps
├── id (UUID, PK)
├── sequence_id (FK)
├── step_order (int)
├── delay_minutes (int - wait time after previous step)
├── message_template (text)
├── media_urls (text[])
├── condition (JSONB - optional filter before sending)
├── created_at

drip_enrollments
├── id (UUID, PK)
├── sequence_id (FK)
├── contact_id (FK)
├── current_step (int)
├── status (active | completed | cancelled | paused)
├── enrolled_at
├── next_step_at (timestamp)
├── completed_at

opt_out_log
├── id (UUID, PK)
├── tenant_id (FK)
├── contact_id (FK)
├── phone_number (E.164)
├── keyword_used (STOP, UNSUBSCRIBE, etc.)
├── bandwidth_message_id
├── created_at

webhooks_log (Bandwidth webhook audit trail)
├── id (UUID, PK)
├── tenant_id (FK, nullable)
├── event_type (message-sending | message-delivered | message-failed | message-received)
├── bandwidth_message_id
├── payload (JSONB)
├── processed (bool)
├── processing_error (text)
├── created_at

billing_events
├── id (UUID, PK)
├── tenant_id (FK)
├── type (sms_sent | mms_sent | number_rental | ai_token | subscription)
├── quantity (int)
├── unit_cost (Decimal)
├── total_cost (Decimal)
├── stripe_invoice_item_id
├── campaign_id (FK, nullable)
├── created_at

templates
├── id (UUID, PK)
├── tenant_id (FK)
├── name
├── category (marketing | transactional | opt_in | opt_out | custom)
├── body (text with {{merge_tags}})
├── media_urls (text[])
├── is_shared (bool - visible to all users in tenant)
├── created_by (FK -> users)
├── created_at / updated_at
```

---

## 4. Feature Specifications

### 4.1 Authentication & Multi-Tenancy

**Registration Flow:**
1. User signs up with email/password -> email verification
2. Create tenant (company name, industry)
3. Auto-provision Bandwidth Sub-Account + Location + Messaging Application
4. Stripe customer created, free trial started (14 days)
5. Redirect to onboarding wizard

**Auth System:**
- JWT access tokens (15 min) + refresh tokens (7 days) stored in httpOnly cookies
- Role-based access control (RBAC): Owner > Admin > Manager > Sender > Viewer
- Multi-factor authentication (TOTP) - required for Owner/Admin
- API key authentication for programmatic access (scoped per-key)
- Session management: view active sessions, revoke remotely
- Password reset via email with rate limiting

**Tenant Switching:**
- Users can belong to multiple tenants (agency model)
- Tenant selector dropdown in navbar

### 4.2 10DLC Registration & Compliance

**Brand Registration:**
- Guided wizard collecting: legal name, EIN, address, website, entity type, vertical
- Submits to Bandwidth Brand API -> TCR
- Displays trust score once received
- Option to request enhanced vetting for higher throughput

**Campaign Registration:**
- Select use case type (marketing, mixed, low volume, etc.)
- Provide sample messages (min 2)
- Declare features: opt-in/out, embedded links, number pooling, age gating
- Auto-generates compliant opt-in/out language suggestions
- Status tracking with webhook-driven updates

**Compliance Dashboard:**
- Trust score visualization with tier breakdown (T-Mobile daily caps)
- Campaign status cards with MPS/daily limits displayed
- Alerts for expiring campaigns or compliance issues
- Auto STOP/HELP keyword handling per CTIA guidelines

### 4.3 Phone Number Management

**Number Search & Purchase:**
- Search by area code, city, state, zip, or toll-free prefix
- Filter by capabilities (SMS, MMS, Voice)
- Bulk ordering support
- Real-time availability check via Bandwidth Numbers API
- Numbers auto-assigned to tenant's Bandwidth Location

**Number Porting:**
- Port-in wizard with LOA (Letter of Authorization) generation
- Bulk port request submission
- Port status tracking (submitted -> FOC received -> completed)
- Toll-free porting validation (up to 5000 numbers per request)

**Toll-Free Verification:**
- Guided submission form
- Status tracking (Restricted -> Pending -> Verified/Denied)
- Automatic retry guidance on denial

**Number Pool Management:**
- Group numbers into pools for campaign rotation
- Round-robin or random selection during send
- Per-number send rate tracking to avoid carrier flags
- Auto-warm-up schedules for new numbers

### 4.4 Contact & List Management

**Contact Import:**
- CSV/Excel upload with column mapping wizard
- Drag-and-drop interface with animated progress
- Duplicate detection (merge or skip)
- Phone number validation and E.164 normalization
- Invalid number filtering with downloadable rejection report
- Import history with undo capability

**Contact Management:**
- Searchable/filterable contact table with infinite scroll
- Custom field definitions per tenant (text, number, date, dropdown)
- Contact profile page with full conversation history and activity timeline
- Tag system for micro-segmentation
- Bulk operations: tag, move to list, delete, export

**List Management:**
- Create unlimited lists with color-coded labels
- Smart lists (dynamic based on filter rules - e.g., "contacted in last 30 days")
- Static lists (manually curated or from import)
- List intersection/exclusion for campaign targeting
- List health score (% active, % unsubscribed, % bounced)

**Opt-In/Opt-Out Management:**
- TCPA-compliant opt-in tracking with timestamp + method
- Universal opt-out (STOP keyword auto-processed globally)
- Per-campaign opt-out option
- Opt-out sync across all lists instantly
- Re-opt-in flow via confirmed keyword
- Opt-out audit log for compliance

### 4.5 Campaign Builder & Mass Sending

**Campaign Types:**
1. **Blast** - Send to entire list(s) immediately or scheduled
2. **Drip Sequence** - Automated multi-step sequences with delays
3. **Triggered** - Send based on events (opt-in, keyword, tag change, API call)
4. **A/B Test** - Split audience, test variants, auto-select winner

**Campaign Builder UI:**
- Step-by-step wizard with live preview (shows how message renders on phone mockup)
- Merge tag insertion ({{first_name}}, {{company}}, {{custom_field}})
- Character counter with segment calculator (GSM-7 vs UCS-2 detection)
- MMS media upload with preview (drag-and-drop, max 500KB recommended)
- URL shortener with click tracking built-in
- Emoji picker
- Template library (save/load reusable templates)

**Scheduling:**
- Immediate send or future schedule (date/time picker with timezone)
- Send window enforcement (e.g., only 9am-9pm recipient's timezone)
- Timezone-aware delivery using contact's area code -> timezone mapping
- Recurring campaign option (daily, weekly, monthly)

**Sending Engine:**
- Celery workers pull from Redis queue
- Respects per-campaign MPS throttle and 10DLC tier limits
- Number pool rotation (round-robin across sender numbers)
- Automatic segment splitting for long messages
- Real-time progress bar via WebSocket
- Pause/Resume/Cancel controls during send
- Automatic retry for transient Bandwidth errors (429, 5xx)
- Dead letter queue for permanently failed messages

**Throughput Management:**
- Per-tenant rate limiting based on their 10DLC tier
- Global rate limiter respecting Bandwidth account-wide limits
- Queue priority system (paid tiers get priority)
- Estimated send time calculator shown in UI before launch

### 4.6 Two-Way Messaging / Inbox

**Conversation Inbox:**
- Real-time inbox (WebSocket-driven) with unread badges
- Conversation list with search, filter by status/tag/assigned user
- Chat-style message thread view (like iMessage/WhatsApp layout)
- Media preview inline (images, video thumbnails)
- Contact info sidebar in conversation view
- Quick reply with template insertion
- Typing indicator for agents

**Assignment & Routing:**
- Auto-assign to team members (round-robin or least-busy)
- Manual reassignment
- Department/team routing rules
- Priority flags and internal notes (not sent to contact)
- Conversation tags for categorization

**Auto-Replies & Keywords:**
- Keyword-based auto-responses (e.g., "HOURS" -> sends business hours)
- Regex pattern matching for flexible triggers
- After-hours auto-reply with custom message
- Cascading priority (keyword > AI agent > default reply)

### 4.7 AI Agents

**Agent Configuration:**
- Name, persona, and system prompt (detailed instructions)
- Choose LLM model (GPT-4o, Claude Sonnet, etc.)
- Temperature and max token controls
- Knowledge base builder: FAQ pairs, product catalogs, free-text docs, website URLs
- Test chat interface (simulate conversations before going live)

**Agent Behavior:**
- Processes inbound messages for assigned phone numbers
- Context-aware: sees full conversation history
- Merge tag access (knows contact's name, custom fields)
- Escalation rules: hand off to human when confidence is low, topic is sensitive, or contact requests it
- Response delay simulation (doesn't reply in 0.5s like a bot - configurable 3-15s)
- Operating hours: can be active only during certain times

**Agent Analytics:**
- Conversations handled vs escalated
- Average response time
- Token usage and cost tracking
- Satisfaction signals (opt-outs after AI interaction)
- Full conversation log with AI reasoning

### 4.8 Analytics & Reporting Dashboard

**Real-Time Dashboard:**
- Animated counters: messages sent today, delivered, failed, responses
- Live sending progress for active campaigns (animated progress ring)
- Delivery rate gauge (target 95%+)
- Cost ticker (real-time spend today)

**Campaign Analytics:**
- Delivery rate, failure rate, opt-out rate per campaign
- Click-through rate (for shortened URLs)
- Response rate and average response time
- Cost per message / cost per engagement
- Segment performance breakdown
- Heatmap: best send times based on response data
- A/B test results with statistical significance indicator

**Tenant-Wide Analytics:**
- Message volume over time (area chart with gradient fill)
- Number utilization (messages per number)
- Contact growth chart
- Opt-out trend analysis
- Top performing campaigns leaderboard
- Monthly spend breakdown by category (SMS, MMS, numbers, AI)

**Export & Reporting:**
- Download reports as CSV or PDF
- Scheduled report emails (daily/weekly/monthly digest)
- Custom date range picker
- Filterable by campaign, list, number, date range

### 4.9 Stripe Billing & Payments

**Plan Tiers:**

| Feature | Free Trial | Starter ($49/mo) | Growth ($149/mo) | Enterprise ($499/mo) |
|---|---|---|---|---|
| Duration | 14 days | - | - | - |
| Included SMS | 100 | 2,000 | 10,000 | 50,000 |
| Included MMS | 25 | 500 | 2,500 | 12,500 |
| Phone Numbers | 1 | 5 | 25 | 100 |
| Users/Seats | 1 | 3 | 10 | Unlimited |
| AI Agent | No | 1 agent | 5 agents | Unlimited |
| Contacts | 500 | 5,000 | 50,000 | Unlimited |
| Drip Sequences | 1 | 5 | 25 | Unlimited |
| API Access | No | Basic | Full | Full + Webhooks |
| Support | Email | Email | Priority | Dedicated |
| Overage SMS | N/A | $0.02 | $0.015 | $0.01 |
| Overage MMS | N/A | $0.05 | $0.04 | $0.03 |

**Billing Features:**
- Stripe Checkout for initial subscription
- Stripe Billing Portal for self-service plan changes
- Usage-based metering via Stripe Usage Records API
- Prepaid credit system (buy credits in bulk at discount)
- Auto top-up option (when credits drop below threshold)
- Invoice history with downloadable PDF invoices
- Promo code / coupon support
- Failed payment handling (grace period -> suspension -> cancellation)
- Stripe webhooks for real-time billing event processing

### 4.10 API & Webhooks (Tenant-Facing)

**REST API (for Growth+ plans):**
- Full CRUD for contacts, lists, messages
- Campaign trigger endpoint
- Send single message endpoint
- Webhook subscription management
- API key management (create, rotate, revoke, scope)
- Rate limiting: 100 req/min (Growth), 500 req/min (Enterprise)
- OpenAPI 3.0 spec with interactive Swagger docs

**Outbound Webhooks (Enterprise):**
- Configurable webhook URLs per event type
- Events: message.delivered, message.failed, message.received, contact.opted_out, campaign.completed
- HMAC-SHA256 signature verification
- Retry with exponential backoff (up to 24 hours)
- Webhook delivery log in dashboard

### 4.11 Admin Panel (Platform Operator)

**Tenant Management:**
- View/search all tenants
- Impersonate tenant (login as)
- Suspend/unsuspend accounts
- Override plan limits
- View tenant Bandwidth sub-account details

**Platform Monitoring:**
- Global message volume dashboard
- Bandwidth API health status
- Celery worker status and queue depths
- Error rate monitoring
- Revenue dashboard (MRR, churn, growth)

**System Configuration:**
- Stripe product/plan management
- Default rate limits
- Bandwidth account credentials
- Email templates (transactional emails)
- Feature flags for gradual rollout

---

## 5. Bandwidth V2 Integration Layer

### 5.1 API Client Architecture

```python
# Core Bandwidth client - wraps all V2 API interactions
class BandwidthClient:
    """Multi-tenant Bandwidth V2 API client."""

    BASE_MESSAGING = "https://messaging.bandwidth.com/api/v2/users/{account_id}/messages"
    BASE_NUMBERS = "https://dashboard.bandwidth.com/api/accounts/{account_id}"
    BASE_CAMPAIGNS = "https://dashboard.bandwidth.com/api/accounts/{account_id}/campaignManagement/10dlc"

    # Auth: HTTP Basic (api_token, api_secret)
    # All requests include tenant context for sub-account routing

    # Messaging
    async def send_message(tenant, to, from_num, text, media_urls=None, tag=None)
    async def get_message_status(tenant, message_id)

    # Numbers
    async def search_numbers(area_code, state, city, quantity, type)
    async def order_numbers(tenant, numbers, site_id, location_id)
    async def release_number(tenant, number)
    async def list_tenant_numbers(tenant)

    # 10DLC
    async def register_brand(tenant, brand_data)
    async def get_brand_status(tenant, brand_id)
    async def register_campaign(tenant, brand_id, campaign_data)
    async def get_campaign_status(tenant, campaign_id)

    # Sub-Account Management
    async def create_site(tenant_name)  # Creates Bandwidth sub-account
    async def create_location(site_id, location_name)
    async def create_application(name, callback_url, inbound_callback_url)
    async def assign_application_to_location(site_id, location_id, app_id)

    # Toll-Free
    async def submit_tf_verification(tenant, number, verification_data)
    async def get_tf_verification_status(tenant, number)
```

### 5.2 Webhook Processing

**Inbound Webhook Endpoint:** `POST /api/v1/webhooks/bandwidth`

```
Bandwidth -> Nginx -> FastAPI webhook handler -> Redis pub/sub
                                              -> PostgreSQL (log)
                                              -> Celery task (process)
```

**Webhook Event Handlers:**
- `message-delivered`: Update campaign_message status, increment counters, deduct credits
- `message-failed`: Update status, log error code, trigger retry if transient
- `message-sending`: Update intermediate MMS status
- `message-received`: Create/update conversation, trigger auto-reply chain (keyword -> AI -> default), push via WebSocket to inbox

**Security:**
- Validate Bandwidth callback signatures
- IP allowlist for Bandwidth webhook IPs
- Idempotency via `bandwidth_message_id` deduplication

### 5.3 Rate Limiting Engine

```python
class TenantRateLimiter:
    """Redis-based sliding window rate limiter per tenant."""

    # Enforces:
    # 1. Per-campaign MPS (from 10DLC tier)
    # 2. Per-tenant aggregate MPS
    # 3. T-Mobile daily cap tracking
    # 4. Global Bandwidth account MPS

    # Uses Redis sorted sets for sliding window
    # Segment-aware: 2-segment SMS counts as 2 against limit
```

---

## 6. Frontend Design System

### 6.1 Visual Identity
- **Theme:** Dark mode primary with light mode toggle
- **Colors:** Deep navy (#0f172a) background, electric blue (#3b82f6) primary, emerald (#10b981) success, amber (#f59e0b) warning, rose (#f43f5e) danger
- **Typography:** Inter for UI, JetBrains Mono for numbers/stats
- **Animations:** Framer Motion for page transitions, micro-interactions, number counters
- **Charts:** Recharts with gradient fills and smooth animations
- **Glass morphism** effects on cards and modals

### 6.2 Key UI Components
- **Animated sidebar** with collapsible sections and notification badges
- **Command palette** (Ctrl+K) for quick navigation
- **Toast notifications** with slide-in animation and progress bar
- **Skeleton loaders** for all async content
- **Phone mockup preview** for message composition (realistic iPhone frame)
- **Drag-and-drop** everywhere: list reordering, file upload, contact import
- **Real-time counters** that animate up as messages send
- **Confetti animation** when campaign completes successfully
- **Data tables** with column resizing, sorting, filtering, bulk selection
- **Responsive** - works on tablet/mobile for inbox monitoring on the go

### 6.3 Page Structure
```
/                          -> Dashboard (animated stats, recent activity)
/campaigns                 -> Campaign list with status filters
/campaigns/new             -> Campaign builder wizard
/campaigns/:id             -> Campaign detail + live analytics
/campaigns/:id/report      -> Post-campaign report
/inbox                     -> 2-way conversation inbox
/inbox/:conversationId     -> Conversation thread
/contacts                  -> Contact management
/contacts/import           -> Import wizard
/contacts/:id              -> Contact profile
/lists                     -> List management
/lists/:id                 -> List detail + members
/numbers                   -> Phone number management
/numbers/search            -> Search & buy numbers
/numbers/porting           -> Port-in wizard
/compliance                -> 10DLC dashboard
/compliance/brands/new     -> Brand registration wizard
/compliance/campaigns/new  -> Campaign registration wizard
/ai-agents                 -> AI agent management
/ai-agents/:id             -> Agent config + test chat
/ai-agents/:id/logs        -> Agent conversation logs
/templates                 -> Message template library
/automations               -> Drip sequences & auto-replies
/automations/drip/new      -> Drip sequence builder
/analytics                 -> Tenant-wide analytics
/analytics/reports         -> Scheduled reports
/settings                  -> Tenant settings
/settings/billing          -> Stripe billing portal
/settings/team             -> User/role management
/settings/api              -> API keys & docs
/settings/webhooks         -> Outbound webhook config
/admin                     -> Platform admin panel (super-admin only)
```

---

## 7. Security & Compliance

### 7.1 Security
- All data encrypted at rest (PostgreSQL TDE) and in transit (TLS 1.3)
- Passwords hashed with Argon2id
- JWT with short expiry + refresh token rotation
- CSRF protection on all state-changing endpoints
- Input sanitization and parameterized queries (SQLAlchemy ORM)
- Rate limiting on auth endpoints (5 attempts -> 15 min lockout)
- API keys hashed with SHA-256, only shown once on creation
- Audit log for all admin actions
- Content Security Policy headers
- CORS restricted to known origins

### 7.2 TCPA / Messaging Compliance
- Mandatory opt-in before any marketing message
- STOP/HELP/CANCEL keyword handling (automatic, cannot be disabled)
- Opt-out processed within seconds, before next message can send
- Quiet hours enforcement (no messages 9pm-8am recipient local time by default)
- Message content scanning for prohibited content
- Consent timestamp and method recorded for every contact
- Campaign-level unsubscribe tracking
- DNC (Do Not Call) list integration capability

### 7.3 Data Privacy
- Tenant data isolation via RLS
- Data export capability (GDPR right to portability)
- Account deletion with full data purge option
- PII encryption for phone numbers and personal data
- 90-day message content retention (configurable per tenant)

---

## 8. Infrastructure & DevOps

### 8.1 Docker Compose Stack
```yaml
services:
  api:        # FastAPI application
  worker:     # Celery workers (send queue)
  worker-ai:  # Celery workers (AI processing)
  beat:       # Celery Beat scheduler
  websocket:  # WebSocket server for real-time updates
  db:         # PostgreSQL 16
  redis:      # Redis 7 (queue + cache + pub/sub)
  nginx:      # Reverse proxy + TLS
  migrate:    # Alembic migrations (run once)
```

### 8.2 Development Setup
```bash
git clone <repo>
cp .env.example .env  # Configure Bandwidth, Stripe, DB creds
docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api python seed.py  # Demo data
# Frontend
cd frontend && npm install && npm run dev
```

### 8.3 Environment Variables
```
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/blastwave
REDIS_URL=redis://redis:6379/0

# Bandwidth
BANDWIDTH_ACCOUNT_ID=
BANDWIDTH_API_TOKEN=
BANDWIDTH_API_SECRET=
BANDWIDTH_APPLICATION_ID=
BANDWIDTH_WEBHOOK_SECRET=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_STARTER=
STRIPE_PRICE_GROWTH=
STRIPE_PRICE_ENTERPRISE=

# AI
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Auth
JWT_SECRET=
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# App
APP_URL=https://app.blastwave.io
WEBHOOK_BASE_URL=https://api.blastwave.io
```

---

## 9. Tech Stack Summary

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, Recharts, React Query, React Router, Zustand |
| **Backend API** | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic |
| **Task Queue** | Celery 5 + Redis broker |
| **Database** | PostgreSQL 16 with RLS policies |
| **Cache/Pub-Sub** | Redis 7 |
| **WebSocket** | FastAPI WebSocket or Socket.IO |
| **Carrier** | Bandwidth V2 API (Messaging, Numbers, Campaign Management) |
| **Payments** | Stripe (Billing, Checkout, Webhooks, Usage Records) |
| **AI** | OpenAI GPT-4o / Anthropic Claude (via API) |
| **Auth** | JWT + Argon2id + TOTP (pyotp) |
| **Email** | Transactional via Resend or SES |
| **File Storage** | S3-compatible (MMS media, imports, exports) |
| **Containerization** | Docker + Docker Compose |
| **Reverse Proxy** | Nginx with Let's Encrypt |

---

## 10. Project Phases

### Phase 1: Foundation (Epics 1-4)
Core infrastructure, auth, multi-tenancy, database

### Phase 2: Bandwidth Integration (Epics 5-7)
Messaging API, number management, 10DLC registration

### Phase 3: Contact & Campaign Engine (Epics 8-10)
Contact/list management, campaign builder, sending engine

### Phase 4: Real-Time Features (Epics 11-13)
2-way inbox, WebSocket infrastructure, auto-replies

### Phase 5: Intelligence (Epics 14-15)
AI agents, analytics & reporting

### Phase 6: Monetization (Epics 16-17)
Stripe billing, tenant-facing API

### Phase 7: Polish & Admin (Epics 18-20)
Admin panel, UI polish, compliance hardening

### Phase 8: Testing & Launch (Epics 21-30)
Comprehensive testing for every module
