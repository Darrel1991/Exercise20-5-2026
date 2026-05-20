# Secure AI Pipeline — Claude Code Edition

Team-triggered AI pipeline. No separate API costs — runs entirely through Claude Code
which is already included in your Team plan.

---

## How it works

```
Team member opens Claude Code in terminal
        ↓
Types a pipeline command  e.g. /pipeline:code "review PR #42"
        ↓
Claude reads CLAUDE.md → knows the security rules + agent behaviour
        ↓
Claude uses MCP tools (GitHub / Google / filesystem) to do the task
        ↓
Claude shows a PREVIEW and asks "Approve? (yes / no / edit)"
        ↓
Team member reviews and decides
        ↓
Claude acts only if approved → logs the transaction
```

---

## Setup — 4 steps

### Step 1 — Add your credentials

```bash
cp .env.example .env
# Edit .env — fill in all credentials
```

**GitHub token** — create at https://github.com/settings/tokens
- Type: Fine-grained personal access token
- Permissions: `Contents` (read/write), `Administration` (read/write), `Issues` (read/write), `Pull requests` (read/write)

**Zoho credentials** — create at https://api-console.zoho.com
- Create a Web Client app
- Scopes: `ZohoProjects.portals.ALL,ZohoProjects.projects.ALL,ZohoProjects.tasks.ALL`
- Run OAuth flow to get refresh token (see comms.md for instructions)

**Google credentials** — create at https://console.cloud.google.com
- Enable: Gmail API, Drive API, Docs API
- Create OAuth 2.0 credentials → download JSON → run OAuth flow for refresh token

**SharePoint / Azure** — ⏳ Pending IT Admin setup
- Azure App ID: `86005979-1675-4637-b217-7d7eb8e3d37c`
- Tenant ID: `d4025e3f-3d65-435e-b432-28a328dab4cd`
- IT Admin needs to: grant `Sites.ReadWrite.All` permission + generate client secret

### Step 2 — Start the Logger Service

The logger must be running before using any pipeline command so all errors and actions are captured.

```powershell
cd logger
.\start.ps1
```

Logger runs on `http://localhost:5000`. Log from any language:

```python
# Python
requests.post("http://localhost:5000/log", json={"level":"ERROR","service":"MyApp","message":"Something failed"})
```
```javascript
// JavaScript
fetch("http://localhost:5000/log", {method:"POST", body: JSON.stringify({level:"ERROR", service:"MyApp", message:"Something failed"})})
```
```powershell
# PowerShell
Invoke-RestMethod -Uri "http://localhost:5000/log" -Method Post -ContentType "application/json" -Body '{"level":"ERROR","service":"MyApp","message":"Something failed"}'
```

Logger endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Check logger is running |
| `/log` | POST | Log error / warning / info + optional stack trace |
| `/audit` | POST | Log pipeline audit entry |
| `/logs?type=errors&lines=50` | GET | View recent error logs |
| `/logs?type=audit&lines=50` | GET | View recent audit logs |

### Step 3 — Install MCP servers

```bash
npx -y @modelcontextprotocol/server-github --help
npx -y @modelcontextprotocol/server-gdrive --help
```

Claude Code picks up `.mcp.json` automatically — no extra config needed.

### Step 4 — Open Claude Code in this folder

```bash
cd pipeline-cc
claude
```

Claude Code reads `CLAUDE.md` on startup and is ready to run pipeline commands.

---

## Commands

| Command | What it does |
|---------|-------------|
| `/pipeline:research "topic"` | Research + summarise from Drive or web |
| `/pipeline:code "review PR #N"` | PR review posted to GitHub after approval |
| `/pipeline:code "triage issues"` | Prioritised issue list |
| `/pipeline:comms "draft email to X about Y"` | Email draft → send after approval |
| `/pipeline:comms "update CRM lead X"` | CRM update instructions for Zoho |
| `/pipeline:document "draft report on X"` | Document draft → save to Drive after approval |
| `/pipeline:daily-summary` | Summarise today's activity and post to Zoho Projects |
| `/pipeline:status` | Show recent audit log entries |
| `/pipeline:help` | Show all commands |

---

## Real usage examples

**Morning PR review:**
```
/pipeline:code "review all open PRs on the main branch"
```
Claude fetches open PRs, reviews each one, shows you the summaries.
You say yes → Claude posts review comments to GitHub.

**Client follow-up email:**
```
/pipeline:comms "draft a follow-up email to our lead about the proposal we sent Monday"
```
Claude drafts the email, shows you the full text.
You say "edit — make it shorter" → Claude revises.
You say yes → Claude sends via Gmail.

**Weekly report:**
```
/pipeline:document "draft a weekly engineering update covering PRs merged and issues closed this week"
```
Claude pulls GitHub activity, drafts the report.
You say yes → Claude saves to Google Drive.

---

## File structure

```
pipeline-cc/
├── CLAUDE.md              ← Claude Code reads this automatically — rules + commands
├── .mcp.json              ← MCP server config (GitHub, Google, filesystem)
├── .env.example           ← Copy to .env — add your credentials
├── .env                   ← Your credentials (never commit this)
├── agents/
│   ├── research.md        ← Research agent behaviour + output format
│   ├── code.md            ← Code agent behaviour + output format
│   ├── comms.md           ← Comms/CRM agent behaviour + output format
│   ├── document.md        ← Document agent behaviour + output format
│   ├── daily-summary.md   ← Daily summary agent behaviour + output format
│   └── daily_summary.py   ← Script that posts summary to Zoho Projects
├── logger/
│   ├── app.py             ← Logger REST API service (language-agnostic)
│   ├── requirements.txt   ← Python dependencies (Flask)
│   └── start.ps1          ← Start the logger service (PowerShell)
├── logs/
│   ├── errors.log         ← All errors, warnings, and info logs
│   └── audit.log          ← Every pipeline action logged here
└── README.md              ← This file
```

---

## Customising agent behaviour

Each agent's behaviour is in `agents/*.md`. Edit the system prompt section to:
- Change the output format
- Add new task types
- Tighten or loosen security rules
- Add company-specific context

Example — add your company name to the Comms agent:
```markdown
## Company context
Company name: Acme Corp
Email signature: [Name] | [Title] | Acme Corp | acmecorp.com
CRM pipeline stages: New Lead → Contacted → Proposal → Negotiation → Closed
```

---

## Zoho Projects

Zoho is connected via direct OAuth2 REST API (not MCP). Credentials are in `.env`:
- `ZOHO_CLIENT_ID` — from https://api-console.zoho.com
- `ZOHO_CLIENT_SECRET` — from https://api-console.zoho.com
- `ZOHO_REFRESH_TOKEN` — generated via OAuth flow

Portal: **redplanet0** (Redplanet Solutions (M) Sdn Bhd)

The Comms agent handles Zoho by:
1. Drafting the CRM/project update
2. Showing you the exact fields to change
3. Executing via REST API after your approval

**Note:** Project creation requires Admin role. Contact **Catherine Lee** (catherine@redplanet.com.my) to create new projects.

When Zoho publishes an official MCP endpoint, add it to `.mcp.json` and update `agents/comms.md`.

---

## SharePoint (Pending)

SharePoint connection requires IT Admin action:
- Azure App: **AI PipeLine** (ID: `86005979-1675-4637-b217-7d7eb8e3d37c`)
- Tenant: `d4025e3f-3d65-435e-b432-28a328dab4cd`
- IT Admin must grant `Sites.ReadWrite.All` and generate a client secret

Once done, add to `.env`:
```
AZURE_CLIENT_ID=86005979-1675-4637-b217-7d7eb8e3d37c
AZURE_TENANT_ID=d4025e3f-3d65-435e-b432-28a328dab4cd
AZURE_CLIENT_SECRET=<from IT Admin>
SHAREPOINT_SITE_URL=https://redplanet.sharepoint.com/sites/internal
```

---

## Audit log

Every pipeline action is logged automatically to `logs/audit.log` via the Logger Service:

```
[2026-05-12 06:28:26 UTC] | USER: darrel.low@redplanet.com.my | COMMAND: /pipeline:research | CLASSIFICATION: INTERNAL | ACTION: Searched Zoho tasks | STATUS: approved
```

Error logs are written to `logs/errors.log`:
```
[2026-05-12 06:28:26 UTC] | LEVEL: ERROR | SERVICE: Zoho | USER: darrel.low@redplanet.com.my | MESSAGE: Token refresh failed - 401 Unauthorized
[2026-05-12 06:28:26 UTC] | LEVEL: ERROR | SERVICE: Python | USER: darrel.low@redplanet.com.my | MESSAGE: IndexError: list index out of range
  TRACE: File app.py line 42
  IndexError
```

View logs live:
```powershell
# Last 50 error logs
Invoke-RestMethod "http://localhost:5000/logs?type=errors&lines=50"

# Last 50 audit logs
Invoke-RestMethod "http://localhost:5000/logs?type=audit&lines=50"
```

---

## Cost

Zero additional cost. Claude Code is included in your Team plan.
No separate API key needed.
