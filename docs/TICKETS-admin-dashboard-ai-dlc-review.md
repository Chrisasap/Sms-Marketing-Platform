# BlastWave SMS — Epics & Tickets
# Admin Dashboard + AI-Powered 10DLC Review

---

## EPIC 1: Admin Dashboard Foundation
> Build the admin layout shell, navigation, and dashboard home page with real-time platform KPIs.

### EPIC-1-T01: Admin Layout Shell & Routing
**Type:** Feature | **Priority:** P0 | **Est:** L
- Create `AdminLayout.tsx` with dedicated sidebar, top bar, and content area
- Admin sidebar links: Dashboard, Users, Tenants, DLC Queue, DLC Analytics, Revenue, System, Audit Log, Settings
- System health indicator (green/amber/red dot) in top bar
- Quick-search overlay (Cmd+K) for tenants/users
- Route guard: redirect non-superadmin users to `/` with toast error
- Wire up `/admin/*` routes in App.tsx router

**Acceptance Criteria:**
- [ ] `/admin` loads admin layout for superadmins
- [ ] Non-superadmin users are redirected with error message
- [ ] Sidebar navigation works for all admin routes
- [ ] Health indicator shows green when API is healthy
- [ ] Layout is responsive (collapses sidebar on mobile)

---

### EPIC-1-T02: Backend — Enhanced Platform Analytics Endpoints
**Type:** Feature | **Priority:** P0 | **Est:** L
- `GET /admin/analytics/overview` — KPI snapshot:
  - total_tenants, active_tenants_24h, new_tenants_7d, new_tenants_30d
  - total_users, active_users_24h
  - messages_24h, messages_7d, messages_30d
  - mrr (sum of active subscription values)
  - dlc_queue_pending, dlc_queue_avg_wait_hours
  - system_health (db, redis, bandwidth status)
- `GET /admin/analytics/messages?period=30d&granularity=daily` — Time series
- `GET /admin/analytics/revenue?period=12m` — Monthly revenue breakdown
- `GET /admin/analytics/tenants/growth?period=90d` — Signup trend
- All endpoints cached 60s in Redis

**Acceptance Criteria:**
- [ ] All 4 endpoints return correct data
- [ ] Time series endpoints support period and granularity params
- [ ] Response times < 500ms with Redis caching
- [ ] Only accessible by superadmins (403 for others)

---

### EPIC-1-T03: Dashboard Home Page — KPI Cards
**Type:** Feature | **Priority:** P0 | **Est:** M
- Top row: 6 KPI cards with animated counters (framer-motion)
  - Total Tenants (with +N new this week badge)
  - Active Today
  - Messages (24h) (with daily trend arrow)
  - MRR (formatted as currency)
  - DLC Queue (pending count, clickable → DLC Queue page)
  - System Health (green/amber/red with component breakdown)
- Auto-refresh every 60 seconds
- Skeleton loading states

**Acceptance Criteria:**
- [ ] All 6 cards display with animated count-up on load
- [ ] Cards show trend indicators (up/down arrows with %)
- [ ] DLC Queue card links to `/admin/dlc-queue`
- [ ] Data refreshes automatically every 60s
- [ ] Skeleton loaders while fetching

---

### EPIC-1-T04: Dashboard Home Page — Charts
**Type:** Feature | **Priority:** P1 | **Est:** L
- Install and configure Recharts with dark theme
- Message volume chart (line, 30-day default, toggle hourly/daily)
- Tenant growth chart (area, 90-day)
- Revenue trend chart (bar, 12-month)
- Plan distribution donut chart
- All charts have tooltips, responsive sizing, loading states

**Acceptance Criteria:**
- [ ] 4 charts render with real data from analytics endpoints
- [ ] Charts are responsive and readable on all screen sizes
- [ ] Dark theme consistent with app design system
- [ ] Tooltips show exact values on hover
- [ ] Toggle between time periods works

---

### EPIC-1-T05: Dashboard Home Page — Activity Feed & Recent Signups
**Type:** Feature | **Priority:** P1 | **Est:** M
- Recent signups table (last 10 tenants: name, plan, signup date, user count)
- DLC queue summary card (pending count, avg wait time, 7-day approval rate)
- Activity feed: last 20 platform events (polling every 30s)
  - Event types: tenant_signup, dlc_submission, dlc_approved, dlc_rejected, billing_event, system_error
- Backend: `GET /admin/activity-feed?limit=20`

**Acceptance Criteria:**
- [ ] Recent signups table shows real tenant data
- [ ] Activity feed updates automatically
- [ ] Each event type has distinct icon and color
- [ ] Clickable events navigate to relevant detail page

---

## EPIC 2: Tenant & User Management
> Full CRUD UI for managing tenants and users across the platform.

### EPIC-2-T01: Tenant List Page
**Type:** Feature | **Priority:** P0 | **Est:** M
- Paginated table: Name, Plan, Status, Users, Messages (30d), MRR, Created
- Search by tenant name or owner email
- Filter by: plan tier, status (active/suspended/trial)
- Sort by any column
- Row click → `/admin/tenants/:id`
- Bulk actions: suspend, change plan (with confirmation dialog)

**Acceptance Criteria:**
- [ ] Table loads all tenants with pagination
- [ ] Search finds tenants by name or owner email
- [ ] Filters and sorting work correctly
- [ ] Bulk suspend requires confirmation
- [ ] Clicking a row navigates to tenant detail

---

### EPIC-2-T02: Tenant Detail Page
**Type:** Feature | **Priority:** P1 | **Est:** L
- Header: Tenant name, plan badge, status badge, created date
- Quick actions: Suspend/Activate, Change Plan, Impersonate, Add Credits
- Tabs:
  - **Overview**: Usage stats (messages, contacts, numbers), credit balance, billing status
  - **Users**: List of users in tenant, role badges, last login
  - **Numbers**: Phone numbers, 10DLC status per number
  - **Billing**: Current plan, payment history, invoices
  - **Activity**: Tenant-specific event log
- Impersonate button opens new tab with tenant's dashboard (existing endpoint)

**Acceptance Criteria:**
- [ ] All tabs load correct data for selected tenant
- [ ] Impersonate opens tenant view in new tab
- [ ] Plan changes take effect immediately
- [ ] Credit adjustments are logged in audit trail

---

### EPIC-2-T03: User Management Page
**Type:** Feature | **Priority:** P1 | **Est:** M
- Backend: `GET /admin/users?search=&role=&tenant_id=&page=&per_page=`
- Backend: `PUT /admin/users/{id}` — update role, is_active, is_superadmin
- Paginated table: Name, Email, Tenant, Role, Superadmin badge, Last Login, Status
- Search by name or email
- Filter by role, superadmin status, active/inactive
- Inline actions: toggle active, grant/revoke superadmin (with confirmation)

**Acceptance Criteria:**
- [ ] All platform users listed with correct tenant association
- [ ] Search and filters work correctly
- [ ] Superadmin grant/revoke requires confirmation dialog
- [ ] Deactivating a user logs them out (invalidate tokens)
- [ ] Changes are audit-logged

---

## EPIC 3: AI-Powered 10DLC Review System
> The core value feature: OpenAI analyzes and enhances 10DLC submissions to maximize approval rates.

### EPIC-3-T01: Database Models — AIReviewResult & AIReviewPrompt
**Type:** Feature | **Priority:** P0 | **Est:** S
- Create Alembic migration for:
  - `ai_review_results` table:
    - id (UUID PK), dlc_application_id (FK), score (int), verdict (varchar),
    - issues (JSONB), enhanced_fields (JSONB), compliance_flags (JSONB),
    - summary (text), model_used (varchar), tokens_used (int), latency_ms (int),
    - created_at (timestamp)
  - `ai_review_prompts` table:
    - id (UUID PK), name (varchar unique), prompt_type (varchar),
    - system_prompt (text), model (varchar default 'gpt-4o'),
    - temperature (float default 0.3), is_active (bool), version (int),
    - created_by (FK -> users), created_at (timestamp)
- Create SQLAlchemy models
- Create Pydantic schemas

**Acceptance Criteria:**
- [ ] Migration runs cleanly on fresh and existing databases
- [ ] Models have proper relationships (AIReviewResult -> DLCApplication)
- [ ] Schemas validate all required fields
- [ ] Prompt versioning works (new version on update)

---

### EPIC-3-T02: AI Review Prompts — Seed Data & Management API
**Type:** Feature | **Priority:** P0 | **Est:** M
- Seed migration with initial prompts:
  - `brand_review_v1` — brand analysis prompt (from spec section 4.1)
  - `campaign_review_v1` — campaign analysis prompt (from spec section 4.1)
- API endpoints:
  - `GET /admin/dlc-queue/ai-prompts` — list all prompts
  - `GET /admin/dlc-queue/ai-prompts/{id}` — get prompt detail
  - `PUT /admin/dlc-queue/ai-prompts/{id}` — update prompt (creates new version)
  - `POST /admin/dlc-queue/ai-prompts/{id}/test` — test prompt with sample data
- Temperature default: 0.3 (low for consistent structured output)

**Acceptance Criteria:**
- [ ] Seed prompts are created on migration
- [ ] Editing a prompt creates version N+1 (old version preserved)
- [ ] Only one prompt per type can be active
- [ ] Test endpoint returns AI response for sample application data
- [ ] Prompt changes are audit-logged

---

### EPIC-3-T03: AI Review Celery Task
**Type:** Feature | **Priority:** P0 | **Est:** L
- New Celery task: `run_ai_dlc_review(application_id)` on `ai` queue
- Task flow:
  1. Load DLCApplication + form_data from DB
  2. Load active prompt for application type (brand or campaign)
  3. Build message with prompt template + application data
  4. Call OpenAI API (gpt-4o by default)
  5. Parse JSON response (with fallback for malformed responses)
  6. Save AIReviewResult to DB
  7. Update DLCApplication with `ai_score` and `ai_verdict` fields
- Error handling: retry 2x with exponential backoff, save error to result on final failure
- Rate limit: max 10 concurrent AI review calls

**Acceptance Criteria:**
- [ ] Task completes successfully for brand applications
- [ ] Task completes successfully for campaign applications
- [ ] Malformed AI responses are handled gracefully (stored as error)
- [ ] Token usage and latency are recorded
- [ ] Task retries on transient OpenAI errors
- [ ] Rate limiting prevents API overload

---

### EPIC-3-T04: AI Review API Endpoints
**Type:** Feature | **Priority:** P0 | **Est:** M
- `POST /admin/dlc-queue/{id}/ai-review` — Trigger AI review (enqueues Celery task)
  - Returns 202 Accepted with task_id
  - If review already exists and is < 1 hour old, return cached result
- `GET /admin/dlc-queue/{id}/ai-review` — Get latest AI review result
- `POST /admin/dlc-queue/{id}/ai-enhance` — Apply AI suggestions to application
  - Accepts: `{ "accept_fields": ["description", "sample_messages"] }` or `"all"`
  - Updates DLCApplication.form_data with enhanced values
  - Logs which suggestions were accepted
- Auto-trigger: When a new DLC application is submitted, automatically enqueue AI review

**Acceptance Criteria:**
- [ ] Triggering review returns 202 and enqueues task
- [ ] Cached results are returned for recent reviews
- [ ] AI enhance updates only the specified fields
- [ ] Auto-trigger fires on new DLC submissions
- [ ] All actions are audit-logged

---

### EPIC-3-T05: Enhanced DLC Queue Frontend — AI Review Panel
**Type:** Feature | **Priority:** P0 | **Est:** XL
- Upgrade AdminDLCQueue.tsx to full-width layout
- Queue table additions:
  - AI Score column with color-coded badge (green 75+, amber 50-74, red <50)
  - AI Verdict column (LIKELY_APPROVED / NEEDS_CHANGES / HIGH_RISK)
  - Sortable by AI score
  - Filter by AI verdict
  - Bulk approve: select all "LIKELY_APPROVED" with score > 85
- Detail panel (slide-out or full page):
  - **Left side**: Original submission fields (editable)
  - **Right side**: AI Review panel:
    - Score gauge (animated circular, reuse TrustScoreGauge pattern)
    - Verdict badge
    - Issue cards:
      - Severity icon (CRITICAL = red, WARNING = amber, INFO = blue)
      - Field name
      - Issue description
      - "Accept Suggestion" button → populates edit field on left
    - Compliance flags (if any)
    - AI summary paragraph
    - "Accept All Suggestions" button
    - "Re-run AI Review" button
  - **Bottom**: Admin notes textarea, Approve/Reject buttons
- Loading state while AI review is processing (spinner with "AI is analyzing...")
- Diff view: show original vs AI-enhanced side by side

**Acceptance Criteria:**
- [ ] AI score and verdict display in queue table
- [ ] Sorting and filtering by AI score/verdict works
- [ ] Detail panel shows AI review results alongside original data
- [ ] "Accept Suggestion" updates the corresponding field
- [ ] "Accept All" updates all fields with AI suggestions
- [ ] "Re-run" triggers new AI review and refreshes panel
- [ ] Bulk approve works for high-score applications
- [ ] Diff view clearly shows changes
- [ ] Loading states during AI processing
- [ ] Reject still requires rejection reason

---

### EPIC-3-T06: Auto-Enhancement on Submission (Tenant-Facing)
**Type:** Feature | **Priority:** P2 | **Est:** M
- When a tenant submits a brand/campaign registration, show them a "preview" step
- Backend runs AI review in real-time (or with loading spinner)
- Show tenant: "We found {N} improvements that could increase your approval chances"
- Tenant can accept/reject each suggestion before final submission
- This is OPTIONAL and can be skipped — tenant can submit original

**Acceptance Criteria:**
- [ ] Submission flow has a new "AI Review" step between form and confirm
- [ ] Suggestions are displayed clearly with before/after
- [ ] Tenant can accept individual suggestions
- [ ] Tenant can skip AI review and submit original
- [ ] AI review results are saved regardless of acceptance

---

## EPIC 4: Compliance Analytics Dashboard
> Track 10DLC review metrics, AI effectiveness, and compliance trends.

### EPIC-4-T01: Backend — Compliance Analytics Endpoints
**Type:** Feature | **Priority:** P1 | **Est:** M
- `GET /admin/analytics/compliance` returns:
  - total_submissions, total_approved, total_rejected, total_pending
  - approval_rate (overall and 30-day rolling)
  - avg_review_time_minutes
  - rejection_reasons breakdown (array of {reason, count})
  - ai_metrics:
    - total_ai_reviews
    - avg_ai_score
    - ai_suggestion_acceptance_rate
    - score_vs_outcome correlation (approved avg score vs rejected avg score)
  - time_series: daily approval/rejection counts for past 90 days

**Acceptance Criteria:**
- [ ] All metrics are calculated correctly
- [ ] Time series covers 90 days
- [ ] AI metrics only count applications with AI reviews
- [ ] Response cached 5 minutes in Redis
- [ ] Only accessible by superadmins

---

### EPIC-4-T02: Compliance Analytics Frontend Page
**Type:** Feature | **Priority:** P1 | **Est:** L
- KPI cards: Total Reviewed, Approval Rate, Avg Review Time, AI Accuracy
- Approval rate line chart (90 days)
- Rejection reasons horizontal bar chart
- AI score vs outcome scatter plot (validates AI effectiveness)
- Avg review time trend (line chart, with/without AI comparison)
- Top rejection reasons table with examples
- AI impact summary: "AI suggestions improved approval rate by X%"

**Acceptance Criteria:**
- [ ] All charts render with real data
- [ ] Scatter plot clearly shows AI score correlation with outcomes
- [ ] Review time comparison demonstrates AI value
- [ ] Page is useful for optimizing AI prompts (shows where AI is wrong)

---

## EPIC 5: Revenue & Billing Analytics
> Platform-level financial visibility for admin.

### EPIC-5-T01: Revenue Analytics Backend
**Type:** Feature | **Priority:** P1 | **Est:** M
- `GET /admin/analytics/revenue` returns:
  - mrr (monthly recurring revenue)
  - arr (annual run rate)
  - churn_rate_30d
  - plan_distribution: [{plan, count, revenue}]
  - revenue_time_series: monthly for past 12 months
  - top_tenants_by_revenue: top 10
  - credit_usage: total purchased, total consumed, remaining

**Acceptance Criteria:**
- [ ] MRR calculated from active subscriptions
- [ ] Churn rate based on tenant cancellations
- [ ] Plan distribution matches actual tenant data
- [ ] Top tenants list is accurate

---

### EPIC-5-T02: Revenue Analytics Frontend Page
**Type:** Feature | **Priority:** P1 | **Est:** M
- KPI cards: MRR, ARR, Churn Rate, Active Subscriptions
- Revenue trend bar chart (12 months)
- Plan distribution donut chart
- Top tenants by revenue table
- Credit usage breakdown

**Acceptance Criteria:**
- [ ] Charts render with financial data
- [ ] MRR/ARR formats as currency
- [ ] Churn rate shows trend direction

---

## EPIC 6: System Health & Audit
> Operational visibility into the platform infrastructure and admin actions.

### EPIC-6-T01: System Health Page
**Type:** Feature | **Priority:** P1 | **Est:** M
- Extend existing `/admin/health` and `/admin/workers` endpoints
- Display:
  - Service status cards (DB, Redis, Bandwidth API, Celery workers) — green/red
  - Celery queue depths (default, send, import, ai) — bar chart
  - Worker details: active tasks, uptime, memory
  - Error rate (last 24h) — if logging is available
  - Disk usage, DB size
- Auto-refresh every 15 seconds

**Acceptance Criteria:**
- [ ] All services show correct status
- [ ] Queue depths update in real-time
- [ ] Workers show current task counts
- [ ] Red indicators for unhealthy services

---

### EPIC-6-T02: Audit Log — Backend
**Type:** Feature | **Priority:** P1 | **Est:** M
- New model: `AuditLog` (id, actor_id, action, target_type, target_id, details JSONB, ip_address, created_at)
- Log all admin actions: tenant changes, user changes, DLC reviews, settings changes, impersonation
- API: `GET /admin/audit-log?actor=&action=&target_type=&date_from=&date_to=&page=`
- Retention: 1 year

**Acceptance Criteria:**
- [ ] All admin endpoints write audit entries
- [ ] Audit log is searchable and filterable
- [ ] Includes IP address and actor identity
- [ ] Cannot be deleted or modified (append-only)

---

### EPIC-6-T03: Audit Log — Frontend Page
**Type:** Feature | **Priority:** P2 | **Est:** M
- Paginated table: Timestamp, Admin, Action, Target, Details (expandable)
- Filter by: action type, admin, date range
- Search by target name/ID
- Expandable row shows full action details (JSON)

**Acceptance Criteria:**
- [ ] Table loads audit entries with pagination
- [ ] Filters narrow results correctly
- [ ] Expandable rows show full JSON details
- [ ] Timestamps in admin's local timezone

---

## EPIC 7: Admin Settings
> Platform-wide configuration management.

### EPIC-7-T01: Platform Settings Page
**Type:** Feature | **Priority:** P2 | **Est:** M
- Backend: `GET/PUT /admin/settings` — global config stored in Redis/DB
- Settings categories:
  - **Rate Limits**: Default message rate limits, registration limits
  - **Compliance**: Default quiet hours, required opt-out keywords
  - **AI**: Default model, temperature, auto-review toggle
  - **Billing**: Credit pricing, trial limits
  - **Feature Flags**: Enable/disable features platform-wide
- Change confirmation dialog with "are you sure" for destructive changes

**Acceptance Criteria:**
- [ ] Settings load current values
- [ ] Changes take effect immediately (or after specified delay)
- [ ] All changes are audit-logged
- [ ] Destructive changes require confirmation

---

---

# TESTING EPICS

---

## EPIC 8: Admin Dashboard Testing
> Comprehensive testing for all admin features.

### EPIC-8-T01: Backend Unit Tests — Admin Analytics Endpoints
**Type:** Test | **Priority:** P0 | **Est:** M
- Test `/admin/analytics/overview` returns correct KPI values
- Test `/admin/analytics/messages` with different periods/granularities
- Test `/admin/analytics/revenue` calculations (MRR, churn)
- Test `/admin/analytics/tenants/growth` time series
- Test Redis caching (second call returns cached, respects TTL)
- Test authorization (403 for non-superadmin)
- Test with empty data (new platform, no tenants)

**Acceptance Criteria:**
- [ ] All analytics endpoints have >90% code coverage
- [ ] Edge cases: zero data, single tenant, thousands of tenants
- [ ] Cache behavior verified
- [ ] Auth enforcement verified

---

### EPIC-8-T02: Backend Unit Tests — User & Tenant Management
**Type:** Test | **Priority:** P0 | **Est:** M
- Test CRUD operations on tenants (list, detail, update, suspend)
- Test user management (list, update role, grant/revoke superadmin)
- Test tenant impersonation (token generation, scope limits)
- Test bulk operations
- Test validation errors (invalid plan tier, self-demotion from superadmin)

**Acceptance Criteria:**
- [ ] All management endpoints have >90% code coverage
- [ ] Validation errors return proper 422 responses
- [ ] Superadmin cannot demote themselves
- [ ] Impersonation token has limited scope

---

### EPIC-8-T03: Backend Unit Tests — AI DLC Review
**Type:** Test | **Priority:** P0 | **Est:** L
- Test `run_ai_dlc_review` Celery task:
  - Mock OpenAI API, verify correct prompt construction
  - Test with valid JSON response → AIReviewResult saved correctly
  - Test with malformed JSON → error handled gracefully
  - Test retry behavior on transient errors
  - Test rate limiting
- Test AI review endpoints:
  - Trigger review → 202 returned, task enqueued
  - Get review → returns latest result
  - Apply enhancements → form_data updated correctly
  - Cached result returned for recent reviews
- Test prompt management:
  - CRUD operations on prompts
  - Version increment on update
  - Only one active prompt per type

**Acceptance Criteria:**
- [ ] All AI review code paths have >90% coverage
- [ ] OpenAI calls are mocked (no real API calls in tests)
- [ ] Malformed AI responses don't crash the system
- [ ] Enhancement application is atomic (all or nothing per field)

---

### EPIC-8-T04: Backend Unit Tests — Audit Log
**Type:** Test | **Priority:** P1 | **Est:** S
- Test audit entries created for each admin action type
- Test audit log query with filters
- Test pagination
- Test that audit entries cannot be deleted via API

**Acceptance Criteria:**
- [ ] Every admin-modifying endpoint creates an audit entry
- [ ] Filter combinations work correctly
- [ ] Audit entries are immutable via API

---

### EPIC-8-T05: Frontend Unit Tests — Admin Components
**Type:** Test | **Priority:** P1 | **Est:** L
- Test AdminLayout renders correctly for superadmin
- Test AdminLayout redirects non-superadmin
- Test KPI cards render with data and skeleton states
- Test charts render without errors (mock data)
- Test DLC queue table filtering/sorting
- Test AI review panel renders issues and suggestions
- Test "Accept Suggestion" updates field
- Test bulk approve flow

**Acceptance Criteria:**
- [ ] All admin components have snapshot tests
- [ ] Interactive elements (buttons, filters) trigger correct actions
- [ ] Loading/error/empty states are tested
- [ ] Mock API calls used throughout

---

### EPIC-8-T06: Integration Tests — AI Review End-to-End
**Type:** Test | **Priority:** P0 | **Est:** L
- Full flow: Submit DLC application → AI review auto-triggers → admin sees results → accepts suggestions → approves → Bandwidth submission
- Test with realistic brand application data
- Test with realistic campaign application data
- Test AI review with intentionally bad submission (low score, many issues)
- Test AI review with perfect submission (high score, no issues)
- Test re-running AI review after prompt change
- Test enhancement persistence (accepted fields survive page reload)

**Acceptance Criteria:**
- [ ] Complete happy path works end-to-end
- [ ] Bad submissions get low scores with actionable issues
- [ ] Good submissions get high scores with minimal/no issues
- [ ] Prompt changes affect subsequent reviews
- [ ] No data loss during enhancement flow

---

### EPIC-8-T07: Load & Performance Tests
**Type:** Test | **Priority:** P2 | **Est:** M
- Test admin dashboard with 1000+ tenants (query performance)
- Test analytics endpoints with 1M+ messages in DB
- Test DLC queue with 500+ pending applications
- Test concurrent AI reviews (10 simultaneous)
- Verify Redis caching reduces DB load
- Target: all admin pages load in < 2 seconds

**Acceptance Criteria:**
- [ ] Dashboard loads in < 2s with 1000 tenants
- [ ] Analytics queries use proper indexes
- [ ] Concurrent AI reviews don't cause OOM or timeouts
- [ ] Cache hit ratio > 80% for analytics endpoints

---

### EPIC-8-T08: Security Tests
**Type:** Test | **Priority:** P0 | **Est:** M
- Test all admin endpoints return 403 for:
  - Unauthenticated requests
  - Regular users (owner, admin, sender roles)
  - Users from other tenants
- Test impersonation token cannot access admin endpoints
- Test AI prompt injection: verify AI-generated content is sanitized
- Test bulk operations cannot exceed rate limits
- Test audit log cannot be bypassed

**Acceptance Criteria:**
- [ ] Zero admin endpoints accessible without superadmin
- [ ] Impersonation is properly scoped
- [ ] AI output is sanitized before display
- [ ] Rate limits enforced on all modifying endpoints

---

---

# TICKET DEPENDENCY GRAPH

```
EPIC-3-T01 (DB Models)
    ├── EPIC-3-T02 (Prompt Management)
    │       └── EPIC-3-T03 (AI Celery Task)
    │               └── EPIC-3-T04 (AI API Endpoints)
    │                       └── EPIC-3-T05 (AI Review Frontend)
    │                               └── EPIC-3-T06 (Tenant-Facing Enhancement)
    └── EPIC-8-T03 (AI Unit Tests)

EPIC-1-T01 (Admin Layout)
    ├── EPIC-1-T02 (Analytics Backend) ──→ EPIC-1-T03 (KPI Cards)
    │                                       └── EPIC-1-T04 (Charts)
    │                                               └── EPIC-1-T05 (Activity Feed)
    ├── EPIC-2-T01 (Tenant List) ──→ EPIC-2-T02 (Tenant Detail)
    ├── EPIC-2-T03 (User Management)
    ├── EPIC-4-T01 (Compliance Analytics Backend) ──→ EPIC-4-T02 (Compliance Analytics Frontend)
    ├── EPIC-5-T01 (Revenue Backend) ──→ EPIC-5-T02 (Revenue Frontend)
    └── EPIC-6-T01 (System Health)

EPIC-6-T02 (Audit Backend) ──→ EPIC-6-T03 (Audit Frontend)

EPIC-7-T01 (Settings) — independent

Testing depends on respective feature tickets being complete.
```

---

# PRIORITY ORDER (Recommended Build Sequence)

**Phase 1 — Foundation (Week 1-2)**
1. EPIC-1-T01 — Admin Layout Shell
2. EPIC-1-T02 — Analytics Backend
3. EPIC-3-T01 — AI Review DB Models

**Phase 2 — Core Dashboard (Week 2-3)**
4. EPIC-1-T03 — KPI Cards
5. EPIC-1-T04 — Charts
6. EPIC-2-T01 — Tenant List

**Phase 3 — AI Review (Week 3-5)**
7. EPIC-3-T02 — AI Prompts
8. EPIC-3-T03 — AI Celery Task
9. EPIC-3-T04 — AI API Endpoints
10. EPIC-3-T05 — AI Review Frontend (largest ticket)

**Phase 4 — Supporting Pages (Week 5-6)**
11. EPIC-2-T02 — Tenant Detail
12. EPIC-2-T03 — User Management
13. EPIC-4-T01 + T02 — Compliance Analytics
14. EPIC-6-T01 — System Health

**Phase 5 — Polish (Week 6-7)**
15. EPIC-1-T05 — Activity Feed
16. EPIC-5-T01 + T02 — Revenue Analytics
17. EPIC-6-T02 + T03 — Audit Log
18. EPIC-7-T01 — Platform Settings
19. EPIC-3-T06 — Tenant-Facing AI Enhancement

**Phase 6 — Testing (Week 7-8)**
20. EPIC-8-T01 through T08 — All test tickets

---

# SIZE ESTIMATES

| Size | Definition | Tickets |
|------|-----------|---------|
| S | < 4 hours | EPIC-3-T01, EPIC-8-T04 |
| M | 4-8 hours | EPIC-1-T03, EPIC-1-T05, EPIC-2-T01, EPIC-2-T03, EPIC-3-T02, EPIC-3-T04, EPIC-3-T06, EPIC-4-T01, EPIC-5-T01, EPIC-5-T02, EPIC-6-T01, EPIC-6-T02, EPIC-6-T03, EPIC-7-T01, EPIC-8-T01, EPIC-8-T02, EPIC-8-T07, EPIC-8-T08 |
| L | 1-2 days | EPIC-1-T01, EPIC-1-T02, EPIC-1-T04, EPIC-2-T02, EPIC-3-T03, EPIC-4-T02, EPIC-8-T03, EPIC-8-T05, EPIC-8-T06 |
| XL | 2-3 days | EPIC-3-T05 |

**Total: 28 tickets across 8 epics**
