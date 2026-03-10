# BlastWave SMS - Admin Dashboard & AI-Powered 10DLC Review

## Spec Document v1.0

---

## 1. Vision

Build a comprehensive, visually stunning superadmin dashboard that gives platform operators complete visibility into every tenant, user, message, and compliance action on the platform. Integrate OpenAI-powered 10DLC application review that uses carefully crafted prompts to analyze, score, and enhance brand/campaign submissions before they hit TCR — maximizing approval rates and minimizing back-and-forth.

---

## 2. Current State

### What Exists
- **Backend**: `/api/v1/admin/stats` returns basic counts (tenants, messages, revenue)
- **Backend**: `/api/v1/admin/tenants` lists tenants with filters
- **Backend**: `/api/v1/admin/dlc-queue` manual approve/reject workflow
- **Frontend**: `AdminDLCQueue.tsx` — single page for reviewing DLC applications
- **AI Infra**: OpenAI + Anthropic integration exists for customer-facing SMS agents
- **Role System**: `is_superadmin` flag on User model, `require_superadmin()` dependency

### What's Missing
- No admin dashboard homepage with real-time platform analytics
- No user management UI (create/disable/promote superadmins)
- No tenant deep-dive analytics
- No AI-assisted 10DLC review (scoring, suggestions, auto-enhancement)
- No compliance analytics (approval rates, rejection trends, avg review time)
- No audit log viewer
- No system configuration panel
- No revenue/billing analytics

---

## 3. Architecture

### 3.1 Admin Frontend Shell

New route group `/admin/*` with dedicated layout:
- Left sidebar: Admin navigation (distinct from tenant user nav)
- Top bar: System health indicators, notification bell, quick search
- All pages use the existing GlassCard design system with dark theme

### 3.2 Admin Pages

| Route | Page | Description |
|-------|------|-------------|
| `/admin` | Dashboard | Real-time platform KPIs, charts, activity feed |
| `/admin/users` | User Management | All users across all tenants, role management |
| `/admin/tenants` | Tenant Management | Tenant list with health scores, deep-dive |
| `/admin/tenants/:id` | Tenant Detail | Full tenant profile, usage, billing, users |
| `/admin/dlc-queue` | 10DLC Review Queue | AI-enhanced review (upgraded from current) |
| `/admin/dlc-analytics` | Compliance Analytics | Approval rates, rejection trends, AI impact |
| `/admin/revenue` | Revenue & Billing | MRR, churn, plan distribution, projections |
| `/admin/system` | System Health | Worker status, queue depths, error rates |
| `/admin/audit-log` | Audit Log | Every admin action, searchable and filterable |
| `/admin/settings` | Platform Settings | Global config, feature flags, rate limits |

### 3.3 Backend API Additions

New endpoints under `/api/v1/admin/`:

**Analytics**
- `GET /analytics/overview` — Real-time KPI snapshot
- `GET /analytics/messages` — Message volume time series (hourly/daily/monthly)
- `GET /analytics/revenue` — Revenue time series, MRR, churn rate
- `GET /analytics/tenants/growth` — Tenant signup trend
- `GET /analytics/compliance` — DLC approval rates, AI impact metrics

**User Management**
- `GET /users` — List all users (cross-tenant), search, filter by role
- `PUT /users/{id}` — Update user role, active status
- `POST /users/{id}/superadmin` — Grant superadmin
- `DELETE /users/{id}/superadmin` — Revoke superadmin

**AI-Powered DLC Review**
- `POST /dlc-queue/{id}/ai-review` — Trigger AI analysis of an application
- `POST /dlc-queue/{id}/ai-enhance` — AI rewrites/enhances the submission
- `GET /dlc-queue/ai-prompts` — List active review prompts
- `PUT /dlc-queue/ai-prompts/{id}` — Update a review prompt

**Audit**
- `GET /audit-log` — Paginated audit log with filters

**Settings**
- `GET /settings` — Platform-wide settings
- `PUT /settings` — Update settings

---

## 4. AI-Powered 10DLC Review System

This is the crown jewel. The AI review system analyzes 10DLC brand and campaign submissions to:

1. **Score** the application's likelihood of approval (0-100)
2. **Flag** specific issues that would cause rejection
3. **Suggest** improvements with exact replacement text
4. **Auto-enhance** the submission with optimized language (admin-approved before submit)

### 4.1 AI Review Prompts

#### Brand Review Prompt
```
You are a 10DLC compliance expert reviewing brand registrations for The Campaign Registry (TCR).
Your job is to evaluate brand submissions and maximize their approval probability.

Evaluate the following brand registration:
- Legal Name: {legal_name}
- Entity Type: {entity_type}
- EIN: {ein}
- Website: {website}
- Vertical: {vertical}
- Description: {brand_description}

Analyze for:
1. LEGAL NAME: Does it match what would appear on IRS records? Flag if it looks informal or uses DBA-style names without proper entity suffix.
2. EIN FORMAT: Is the EIN in valid XX-XXXXXXX format? Flag if missing or malformed.
3. WEBSITE: Does the domain look legitimate? Flag if no website, parked domain indicators, or mismatch with brand name.
4. VERTICAL: Is the selected vertical appropriate for the described business? Flag mismatches.
5. ENTITY TYPE: Does the entity type match the business description? (e.g., sole proprietor claiming to be a nonprofit)
6. DESCRIPTION: Is the business description clear, professional, and specific enough for TCR review?

For each issue found, provide:
- Severity: CRITICAL (will cause rejection), WARNING (may cause rejection), INFO (could be improved)
- Field: Which field has the issue
- Issue: What's wrong
- Suggestion: Exact replacement text or action to fix

Return a JSON object:
{
  "score": <0-100>,
  "verdict": "LIKELY_APPROVED" | "NEEDS_CHANGES" | "HIGH_RISK",
  "issues": [...],
  "enhanced_fields": { field: suggested_value, ... },
  "summary": "One paragraph summary of the review"
}
```

#### Campaign Review Prompt
```
You are a 10DLC compliance expert reviewing campaign registrations for The Campaign Registry (TCR).
Your goal is to maximize approval rates while ensuring full TCPA/CTIA compliance.

Evaluate the following campaign registration:
- Use Case: {use_case}
- Description: {description}
- Sample Messages: {sample_messages}
- Message Flow: {message_flow}
- Help Keywords: {help_keywords}
- Opt-Out Keywords: {opt_out_keywords}
- Opt-In Description: {opt_in_description}

TCR APPROVAL CRITERIA (evaluate against ALL of these):

1. USE CASE MATCH: Does the description accurately match the selected use case category?
   TCR rejects mismatched use cases immediately.

2. SAMPLE MESSAGES (most common rejection reason):
   - Must include opt-out language: "Reply STOP to unsubscribe" or similar
   - Must include business name/identifier in the message
   - Must be realistic examples of what will actually be sent
   - Must match the declared use case
   - Should include at minimum 2 distinct sample messages
   - Marketing messages must clearly identify as promotional

3. MESSAGE FLOW / CONSENT:
   - Must clearly describe HOW consumers opt in (web form, point of sale, text keyword, etc.)
   - Must describe WHAT consumers are opting into (type + frequency of messages)
   - Must not imply purchased lists or shared consent
   - "Customers opt in on our website" is TOO VAGUE — needs specifics

4. OPT-OUT HANDLING:
   - STOP must be a supported keyword (minimum)
   - Should also support: STOP, CANCEL, UNSUBSCRIBE, END, QUIT
   - Help keyword should return contact information

5. DESCRIPTION:
   - Must be specific about message content and purpose
   - Generic descriptions like "marketing messages" get rejected
   - Should specify frequency (e.g., "up to 4 messages per month")

6. COMPLIANCE FLAGS:
   - SHAFT content (Sex, Hate, Alcohol, Firearms, Tobacco) requires special use case
   - Loan/lending requires specific compliance language
   - Cannabis/CBD is prohibited on most carrier paths
   - Gambling requires age verification disclosure

For each issue, provide severity, field, issue description, and EXACT replacement text.

If sample messages need improvement, rewrite them to be compliant while preserving the business intent.

Return JSON:
{
  "score": <0-100>,
  "verdict": "LIKELY_APPROVED" | "NEEDS_CHANGES" | "HIGH_RISK",
  "issues": [...],
  "enhanced_fields": {
    "description": "improved description",
    "sample_messages": ["improved msg 1", "improved msg 2"],
    "opt_in_description": "improved opt-in flow",
    ...
  },
  "compliance_flags": ["any SHAFT or restricted content flags"],
  "summary": "One paragraph summary"
}
```

### 4.2 AI Enhancement Flow

```
User submits 10DLC application
         |
         v
  [Save to DB as pending_review]
         |
         v
  [Auto-trigger AI Review] -----> Celery task on `ai` queue
         |                              |
         |                    [Call OpenAI with review prompt]
         |                              |
         |                    [Parse JSON response]
         |                              |
         |                    [Save AIReviewResult to DB]
         |                              |
         v                              v
  [Admin opens review queue] ---> [Sees AI score + issues + suggestions]
         |
         |--- [Accept AI suggestions] ---> [Fields auto-updated]
         |--- [Manually edit] -----------> [Admin tweaks fields]
         |--- [Override AI] -------------> [Proceed with original]
         |
         v
  [Admin clicks Approve] ---> [Submit to Bandwidth/TCR]
```

### 4.3 AI Review Data Model

New model: `AIReviewResult`
```
- id: UUID
- dlc_application_id: FK -> DLCApplication
- score: Integer (0-100)
- verdict: String (LIKELY_APPROVED / NEEDS_CHANGES / HIGH_RISK)
- issues: JSONB (array of issue objects)
- enhanced_fields: JSONB (field -> suggested value mapping)
- compliance_flags: JSONB (array of flag strings)
- summary: Text
- model_used: String (e.g., "gpt-4o")
- tokens_used: Integer
- latency_ms: Integer
- created_at: DateTime
```

### 4.4 Prompt Management

Prompts stored in DB so superadmins can iterate without code deploys:

New model: `AIReviewPrompt`
```
- id: UUID
- name: String (e.g., "brand_review_v1", "campaign_review_v1")
- prompt_type: String ("brand_review" | "campaign_review")
- system_prompt: Text
- model: String (default "gpt-4o")
- temperature: Float (default 0.3 — low for consistency)
- is_active: Boolean
- version: Integer (auto-increment)
- created_by: FK -> User
- created_at: DateTime
```

---

## 5. Admin Dashboard Design

### 5.1 Dashboard Home (`/admin`)

**Top Row — KPI Cards (animated counters):**
| Total Tenants | Active Today | Messages (24h) | MRR | DLC Queue | System Health |
|---|---|---|---|---|---|

**Second Row — Charts (2-column):**
- Left: Message volume (line chart, 30 days, hourly granularity option)
- Right: Tenant growth (area chart, 90 days)

**Third Row — Charts (2-column):**
- Left: Revenue trend (bar chart, 12 months)
- Right: Plan distribution (donut chart)

**Fourth Row — Tables (2-column):**
- Left: Recent signups (last 10 tenants, with plan + status)
- Right: DLC queue summary (pending count, avg wait time, approval rate)

**Bottom Row — Activity Feed:**
- Real-time log of admin-relevant events (new signups, DLC submissions, billing events, errors)

### 5.2 DLC Review Queue (Enhanced)

**Queue View:**
- Table with columns: Tenant | Type | Submitted | AI Score | AI Verdict | Status | Actions
- Color-coded AI scores: green (75+), amber (50-74), red (<50)
- Filter by: status, type, AI verdict, date range
- Sort by: submission date, AI score, tenant name
- Bulk actions: approve all "LIKELY_APPROVED" with score > 85

**Detail View (slide-out panel, full-width):**
- Left column: Original submission fields
- Right column: AI review results
  - Score gauge (animated, like trust score gauge)
  - Issue cards with severity badges
  - "Accept Suggestion" button per field (populates edit field)
  - "Accept All AI Suggestions" button
- Bottom: Admin notes, approve/reject buttons
- "Re-run AI Review" button (if prompt was updated)

### 5.3 Compliance Analytics (`/admin/dlc-analytics`)

- Approval rate over time (line chart)
- Rejection reasons breakdown (horizontal bar chart)
- AI score vs actual outcome (scatter plot — validates AI accuracy)
- Average review time (with/without AI comparison)
- Top rejection reasons table
- AI impact metrics: % of suggestions accepted, score improvement after enhancement

---

## 6. Tech Stack Additions

| Component | Technology | Reason |
|-----------|-----------|--------|
| Charts | Recharts | Already in React ecosystem, composable, dark-theme friendly |
| Animated counters | framer-motion | Already in project |
| Data tables | Existing DataTable component | Extend with new features |
| Date picker | react-datepicker or similar | For date range filters |
| AI calls | OpenAI gpt-4o | Best at structured JSON output and compliance reasoning |
| Real-time feed | Polling (30s) or SSE | Start with polling, upgrade to SSE later |

---

## 7. Security Considerations

- All admin routes require `is_superadmin` — no exceptions
- Tenant impersonation generates audit log entry
- AI review results are immutable once created (create new, don't update)
- Prompt changes create new versions (old versions preserved)
- Admin settings changes require confirmation dialog
- Rate limit AI review calls: max 10 per minute per admin
- Sanitize all AI-generated content before rendering in admin UI

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| 10DLC approval rate | > 90% (up from industry avg ~70%) |
| Average review time | < 2 minutes (down from ~10 min manual) |
| AI suggestion acceptance rate | > 60% |
| Admin time per DLC review | Reduced by 75% |
| Dashboard load time | < 2 seconds |

---

## 9. Out of Scope (v1)

- Real-time WebSocket updates (use polling for v1)
- White-label admin panel
- Multi-admin collaboration (comments, assignments)
- Automated approval without human review
- Custom report builder
- Mobile admin app
