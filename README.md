# AI Job Search Platform — MVP, Phases 1–5 (complete)

**Phase 1** (infrastructure, security, onboarding): sign up → upload resume →
AI-parsed profile → user verifies & saves.

**Phase 2** (AI tailoring & Gatekeeper): paste a job description → AI gap
analysis → optional gap-filling Q&A (skip-friendly) → tailored resume
(`.docx`) + cover letter, fact-checked by a second "Gatekeeper" agent before
the user sees them → tone switching and Hebrew/English translation.

**Phase 3** (Kanban dashboard & email parsing): the dashboard is now a real
6-column board (status changed via dropdown, not drag-and-drop — see the
plan's as-built notes for why). Gmail can be connected (a separate OAuth
flow from login, since it needs its own stored refresh token) and is synced
twice a day by a Railway Cron Job, or on demand via "סנכרן אימיילים עכשיו".
A fourth agent (Email Parser) classifies incoming mail and either auto-links
it to the right application or prompts the user to pick from candidates. A
manual paste box in Settings covers anyone without Gmail connected.

**Phase 4** (interview simulator): a "התחל הכנה לראיון" button appears on any
card in the "ראיון טלפוני"/"ראיון טכנולוגי" columns. It starts a mock
interview with a persona chosen deterministically from the job title (HR /
technical / product manager), asks exactly 5 questions one at a time (plain
request/response, not token streaming — see the plan's as-built notes), then
produces a rubric-based feedback report (score, strengths, improvements,
per-question rewrite suggestions) that can be revisited or redone from
scratch at any time.

**Phase 5** (admin portal, RBAC, 2FA, account pause): `/admin.html` shows KPI
tiles, a searchable user directory, and (Super Admin only) an error-monitoring
grid — every endpoint checks the caller's `profiles.role` server-side, not
just the UI. Super Admin accounts require mandatory TOTP 2FA (Supabase's own
MFA, via Google Authenticator or similar) — first login after promotion walks
through enrollment with a QR code, every login after that requires the code.
Also closes a gap from Phase 1: accounts can now actually be paused (by the
user themselves in Settings, or by a Super Admin) — a paused account's AI
tools and Gmail sync stop, and it's excluded from the cron sync. A pre-existing
bug was also fixed here: returning users logging in were being sent back to
the resume-upload screen instead of their dashboard (nothing had ever checked
whether they'd already completed onboarding).

All 5 PRD roadmap phases for MVP scope are now built.

## Architecture

- **`/web`** — static HTML/CSS/vanilla JS (Vite, no framework), RTL Hebrew UI.
- **`/ai-service`** — Python + FastAPI + CrewAI, hosted on Railway. Also acts
  as the auth proxy: it's the only thing that talks to Supabase Auth
  directly, so the refresh token can be set as a real HttpOnly/Secure/SameSite
  cookie (a static-JS frontend can never set one itself).
- **`/supabase`** — Postgres schema + RLS policies + Auth config, applied via
  the Supabase CLI or pasted into the SQL editor.

## One-time setup (things only you can do)

1. **Supabase project** — create one at supabase.com. From Project Settings,
   grab: `SUPABASE_URL`, the `anon` key, the `service_role` key, and the JWT
   secret (Settings → API → JWT Settings).
   Apply the schema: `supabase link` then `supabase db push`, or paste
   `supabase/migrations/0001_init.sql` into the SQL editor. Also review
   `supabase/config.toml` and apply the `[auth]` settings in the dashboard
   (Authentication → Settings) if you're not using the CLI to manage them.
   Create a public Storage bucket named `resumes` if the migration's
   `insert into storage.buckets` didn't take effect in the dashboard.

2. **Google Cloud OAuth client** (for Google Sign-In) — create a project at
   console.cloud.google.com, configure the OAuth consent screen in **Testing**
   mode (100 test-user cap, acceptable for this stage — add each tester's
   email under "Test users"), create an OAuth Client ID (Web application) with
   authorized redirect URI `https://<your-supabase-project>.supabase.co/auth/v1/callback`.
   Put the Client ID/Secret into Supabase Auth → Providers → Google (or
   `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` env vars if managing via CLI).

3. **OpenAI API key** — for the CrewAI agents.

4. **Railway project** — for deploying `ai-service` (Dockerfile included).
   Set its environment variables from `ai-service/.env.example`, with
   `COOKIE_SECURE=true` and `FRONTEND_URL`/`AI_SERVICE_URL` set to your real
   deployed URLs.

5. **Gmail integration (Phase 3)** — on the same Google Cloud OAuth client
   from step 2: enable the Gmail API, add `https://www.googleapis.com/auth/gmail.readonly`
   on the OAuth consent screen's scopes, and add `{AI_SERVICE_URL}/gmail/connect/callback`
   as an additional authorized redirect URI. Set `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`
   (same values as step 2) as `ai-service` env vars — this is a *direct*
   Google OAuth flow (not through Supabase), since it needs its own stored
   refresh token for background sync.

6. **Railway Cron Job for email sync** — create a second service in the same
   Railway project, from the same repo: Start Command
   `python -m app.jobs.sync_gmail`, Cron Schedule `0 6,18 * * *` (twice
   daily), same environment variables as the web service.

7. **Enable Supabase's TOTP MFA provider (Phase 5)** — in the Supabase
   dashboard: Authentication → Providers → Multi-Factor Authentication →
   enable TOTP (it's off by default on new projects). Without this,
   `/auth/mfa/enroll` will fail for any Super Admin account.

8. **Promote your first Super Admin(s) manually** — self-promotion is
   blocked by design. After the person signs up normally, in the Supabase
   SQL editor: `update profiles set role = 'super_admin' where id = '<their auth.users uuid>';`
   (find the uuid in Authentication → Users, or `select id, email from auth.users;`).
   Use `role = 'support'` the same way for read-only admin access.

## Local development

```bash
# ai-service
cd ai-service
cp .env.example .env   # fill in the values from step 1-3 above
pip install -r requirements.txt
uvicorn app.main:app --reload

# web (separate terminal)
cd web
cp .env.example .env   # fill in SUPABASE_URL / SUPABASE_ANON_KEY
npm install
npm run dev
```

Open http://localhost:5173.

## Manual verification checklist

- [ ] Sign up with email/password not meeting the policy → inline error, no request sent.
- [ ] Sign up with a valid password → lands on the resume-upload screen.
- [ ] Upload a real PDF or DOCX resume → parsed fields appear on the profile screen.
- [ ] Edit a field, add/remove a work-experience entry, save → redirected to the dashboard stub.
- [ ] Refresh the dashboard page → still logged in (session restored from the HttpOnly cookie, not localStorage).
- [ ] Log out, then try to open `/dashboard.html` directly → redirected to sign-in.
- [ ] "Sign in with Google" completes and lands on the dashboard.
- [ ] Two different users each get their own `core_profiles` row and can't read the other's (test via a second account, or `curl` the REST API with one user's access token requesting another user's row — should come back empty).

**Phase 2:**
- [ ] From the dashboard, "+ הוספת משרה חדשה" → paste a real job description for a role reasonably close to the test user's resume → "נתח משרה" shows a plausible match % and a requirement list.
- [ ] Continue into the Q&A wizard → answer some questions, skip others (skipping shows the encouraging tip, never blocks) → on the last question, documents generate automatically.
- [ ] The tailored resume preview and cover letter appear; the `.docx` download opens correctly in Word; its content is traceable to either the original resume or an answered question — no invented employers/dates/skills.
- [ ] Switching the cover-letter tone updates the letter without creating a second entry in `applications` for the same job (check the table row count).
- [ ] Clicking the language toggle translates both documents and updates the same `applications` row (not a new one).
- [ ] A second user cannot call `/documents/translate` with the first user's `application_id` (should 404), and cannot open the first user's signed `tailored-documents` file URL after it expires.
- [ ] If you temporarily break the Gatekeeper (e.g. edit `core_profiles.parsed_data` to remove something the job requires so the tailoring agent is tempted to invent it), confirm the preview screen shows the "שימו לב" trust-warning banner with specific violations instead of silently returning a bad draft.

**Phase 3:**
- [ ] Dashboard shows all 6 columns; changing a card's status dropdown updates it immediately and persists across a page reload.
- [ ] Settings → "חבר את Gmail" completes a full Google consent round-trip (using a test-user Google account added to the OAuth consent screen) and lands back on Settings showing "מחובר כ-...".
- [ ] Send yourself a fake "we'd like to schedule a phone screen" email referencing a company you have an open application with, from that connected Gmail account.
- [ ] Click "סנכרן אימיילים עכשיו" on the dashboard → confirm the matching card either updates automatically (high-confidence match) or the unlinked-emails banner offers it as a candidate → clicking a candidate links it and updates the card.
- [ ] Paste the same email text into Settings' manual box for a **second** test user and confirm it does *not* offer the first user's applications as candidates.
- [ ] Disconnect Gmail → confirm the `gmail_connections` row is gone and `/gmail/sync-now` then returns 400.
- [ ] Manually run `python -m app.jobs.sync_gmail` locally against a connected test account and confirm it processes without needing any HTTP request (this is what the Railway Cron Job runs).

**Phase 4:**
- [ ] A card in "ראיון טלפוני" or "ראיון טכנולוגי" shows "התחל הכנה לראיון"; other columns don't.
- [ ] Starting it picks a persona that matches the job (e.g. a technical title → "מנהל/ת פיתוח טכנולוגי") and asks a relevant first question.
- [ ] Answer all 5 questions → the 6th "turn" never happens automatically; the input disables and a message prompts you to get feedback.
- [ ] "סיום הראיון וקבלת משוב" works both after all 5 questions **and** if clicked early (e.g. after only 2 answers).
- [ ] The feedback report shows a plausible score, non-empty strengths/improvements, and a per-question rewrite suggestion for every question actually asked.
- [ ] "בצע סימולציה חוזרת" starts a genuinely new session (check `simulations` has a second row for the same `application_id`, not an overwrite).
- [ ] Reload the feedback page directly via its `?simulation_id=` URL later — it still renders correctly from the DB, not just from in-memory state.
- [ ] A second user cannot `GET /simulations/{id}` for the first user's simulation (404).

**Phase 5:**
- [ ] A regular user logging in a second time lands directly on the dashboard, not the resume-upload screen (the routing-bug fix).
- [ ] Promote a test account to `super_admin` via SQL → next login redirects to `/mfa.html` in enrollment mode with a scannable QR code → scan it in Google Authenticator, enter the code → lands in the app with a real session (refresh the page — still logged in, confirming the cookie was actually set this time, not just at the password step).
- [ ] Log out and log back in with that same account → this time `/mfa.html` shows the code-only challenge screen (not enrollment again) → correct code logs in; a wrong code shows an inline error without navigating away.
- [ ] A `support`-role test account can open `/admin.html` and see KPI tiles + the user table (no pause buttons, no error grid, no pause column), and `GET /admin/errors` / `PATCH /admin/users/{id}/pause` both 403 directly.
- [ ] A `regular`-role account hitting `/admin.html` sees "אין לך הרשאה" and bounces to the dashboard; `GET /admin/stats` 403s directly.
- [ ] In Settings, "השהה חשבון" → confirm `/documents/generate`, `/jobs/analyze`, `/parse-resume`, `/emails/manual`, `/gmail/sync-now`, and `/simulations/start` all 403 for that account, while the Kanban board (`GET`) and `/gmail/status` still work → "הפעל חשבון מחדש" restores everything.
- [ ] A Super Admin pausing another user's account from `/admin.html` has the same effect as that user pausing themselves.
- [ ] Trigger an AI JSON-parse failure deliberately (or just wait for one) and confirm it shows up in `/admin/errors` with a sensible `source` value.

## Automated tests

```bash
cd ai-service
pytest
```

Covers resume text extraction (PDF/DOCX), the Tailoring↔Gatekeeper retry loop,
the email classify-and-link control flow (AUTO_LINK / MANUAL_LINK_PROMPT /
NO_MATCH / duplicate-message handling), the interview simulator's 5-question
cap + persona heuristic, and RBAC/account-pause gating — LLM calls mocked
throughout, since these tests are about control flow, not prompt quality.
Everything else is either thin plumbing or delegated to Supabase/OpenAI/CrewAI/
Gmail directly.
