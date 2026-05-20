# AiPipeline — Team Training Guide
**Redplanet Solutions (M) Sdn Bhd**
**Date:** 12 May 2026
**Prepared by:** Darrel Low (darrel.low@redplanet.com.my)

---

## Table of Contents

1. [What is AiPipeline?](#1-what-is-aipipeline)
2. [Prerequisites](#2-prerequisites)
3. [Setup — GitHub](#3-setup--github)
4. [Setup — Zoho Projects](#4-setup--zoho-projects)
5. [Setup — Logger Service](#5-setup--logger-service)
6. [How to Use Pipeline Commands](#6-how-to-use-pipeline-commands)
7. [Command Reference](#7-command-reference)
8. [Security Rules](#8-security-rules)
9. [Pending Setup (IT Admin Required)](#9-pending-setup-it-admin-required)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. What is AiPipeline?

AiPipeline is a team-triggered AI assistant that runs inside **Claude Code (VS Code)**. It allows your team to:

- Review GitHub pull requests and triage issues
- Draft and send emails via Gmail
- Create and update Zoho Projects tasks
- Draft documents and save to Google Drive
- Post daily activity summaries to Zoho Projects
- Log all errors and actions automatically

**How it works:**
```
You type a command in Claude Code
        ↓
Claude processes the task securely
        ↓
Claude shows you a PREVIEW
        ↓
You approve (yes / no / edit)
        ↓
Claude acts ONLY if you approve
        ↓
Action is logged to audit.log
```

> **Important:** Claude will NEVER take any action without your explicit approval.

---

## 2. Prerequisites

Before setting up, make sure you have:

- [ ] **VS Code** installed — https://code.visualstudio.com
- [ ] **Claude Code extension** installed in VS Code
- [ ] **Python 3.8+** installed — https://www.python.org/downloads
- [ ] **Git** installed — https://git-scm.com
- [ ] A **GitHub account**
- [ ] A **Zoho Projects account** (Redplanet portal: redplanet0)
- [ ] The `pipeline-cc` project folder opened in VS Code

---

## 3. Setup — GitHub

### Step 1: Create a GitHub Fine-Grained Token

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Fine-grained personal access token"**
3. Fill in:
   - **Token name:** `AiPipeline`
   - **Expiration:** 90 days (or custom)
   - **Resource owner:** Your GitHub username
   - **Repository access:** All repositories

4. Under **Permissions**, click **"+ Add permissions"** and set:

   | Permission | Level |
   |---|---|
   | Contents | Read and write |
   | Administration | Read and write |
   | Issues | Read and write |
   | Pull requests | Read and write |
   | Metadata | Read-only (auto) |

5. Click **"Generate token"**
6. **Copy the token immediately** — it won't show again!

### Step 2: Add Token to .env

Open the `.env` file in VS Code and replace the GitHub token:

```
GITHUB_TOKEN=github_pat_xxxxxxxxxxxxxxxxxxxx
```

### Step 3: Verify Connection

In Claude Code chat, type:
```
Test my GitHub connection
```

Claude will confirm your username and number of repositories.

---

## 4. Setup — Zoho Projects

### Step 1: Register a Zoho API App

1. Go to https://api-console.zoho.com
2. Log in with your Zoho account
3. Click **"Add Client"**
4. Choose **"Server-based Applications"**
5. Fill in:
   - **Client Name:** `AiPipeline`
   - **Homepage URL:** `http://localhost:80/`
   - **Authorized Redirect URIs:** `http://localhost:8080`
6. Click **Create**
7. Note down your **Client ID** and **Client Secret**

### Step 2: Add Credentials to .env

Open `.env` and fill in:

```
ZOHO_CLIENT_ID=your_client_id_here
ZOHO_CLIENT_SECRET=your_client_secret_here
ZOHO_REFRESH_TOKEN=        ← leave blank for now
```

### Step 3: Generate Authorization Code

Paste this URL in your browser (replace YOUR_CLIENT_ID):

```
https://accounts.zoho.com/oauth/v2/auth?scope=ZohoProjects.portals.ALL,ZohoProjects.projects.ALL,ZohoProjects.tasks.ALL&client_id=YOUR_CLIENT_ID&response_type=code&access_type=offline&redirect_uri=http://localhost:8080
```

- Click **Accept/Allow** on the Zoho consent screen
- Your browser will redirect to `http://localhost:8080/?code=1000.xxxx...`
- The page will show an error — **that is normal**
- **Copy the full URL** from the address bar

### Step 4: Exchange Code for Refresh Token

Run this in PowerShell (replace values):

```powershell
Invoke-RestMethod -Method Post -Uri "https://accounts.zoho.com/oauth/v2/token" `
  -Body "grant_type=authorization_code&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&redirect_uri=http://localhost:8080&code=YOUR_CODE" `
  -ContentType "application/x-www-form-urlencoded"
```

Copy the `refresh_token` value from the response and add it to `.env`:

```
ZOHO_REFRESH_TOKEN=1000.xxxxxxxxxxxxxxxx
```

### Step 5: Verify Connection

In Claude Code chat, type:
```
Check my Zoho connection
```

Claude will confirm your portal name and list your projects.

> **Note:** Only Portal Admins can create new projects. Contact **Catherine Lee** (catherine@redplanet.com.my) to create the **Internal** project.

---

## 5. Setup — Logger Service

The Logger Service must be running before using pipeline commands. It captures all errors and audit logs.

### Start the Logger

Open a terminal in VS Code and run:

```powershell
cd logger
.\start.ps1
```

The logger runs on `http://localhost:5000`.

### Verify Logger is Running

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/health"
```

Expected response:
```json
{
  "status": "ok",
  "service": "AiPipeline Logger"
}
```

### Keep Logger Running

Keep the terminal open while using the pipeline. If you close it, restart with `.\start.ps1`.

---

## 6. How to Use Pipeline Commands

### Opening Claude Code in VS Code

1. Open VS Code
2. Open the `pipeline-cc` folder (**File → Open Folder**)
3. Click the **Claude Code icon** in the sidebar (star/sparkle icon)
4. Type `/` in the chat box — you will see all pipeline commands

### Using a Command

1. Type `/pipeline_` in the chat box
2. Select a command from the dropdown
3. Add your request after the command
4. Claude will process and show a **preview**
5. Type `yes`, `no`, or `edit` to respond

**Example:**
```
/pipeline_code "review PR #5"
```

Claude will show the PR review → you approve → Claude posts the review to GitHub.

---

## 7. Command Reference

### `/pipeline_research "your question"`
Research a topic and summarise findings.

**Examples:**
```
/pipeline_research "best practices for GIS data management"
/pipeline_research "how to optimise drone detection accuracy"
```

---

### `/pipeline_code "request"`
Review pull requests or triage GitHub issues.

**Examples:**
```
/pipeline_code "review PR #42"
/pipeline_code "triage open issues"
/pipeline_code "summarise recent commits on main"
```

---

### `/pipeline_comms "request"`
Draft emails or prepare Zoho CRM updates.

**Examples:**
```
/pipeline_comms "draft follow-up email to Catherine about the Internal project"
/pipeline_comms "draft update email to client about ODS deployment"
```

---

### `/pipeline_document "request"`
Draft reports, memos, or meeting notes.

**Examples:**
```
/pipeline_document "draft weekly engineering update"
/pipeline_document "create meeting notes template for sprint review"
```

---

### `/pipeline_daily-summary`
Summarise today's activity and post to Zoho Projects.

- Run this at the **end of each day**
- Claude will draft the summary from your session
- You review and approve before it posts to Zoho
- Posts to **Internal** project (fallback: **TNB Mobile GIS**)

---

### `/pipeline_status`
Show recent audit log and error log entries.

```
/pipeline_status
```

---

### `/pipeline_help`
Show all available commands.

```
/pipeline_help
```

---

## 8. Security Rules

All team members must follow these rules:

| Rule | Description |
|---|---|
| **No autonomous actions** | Claude always asks for approval before acting |
| **Data classification** | Classify data before processing (PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED) |
| **No external sharing** | CONFIDENTIAL data stays local — no external tools |
| **PII scrubbing** | Replace personal data with [EMAIL], [PHONE], [NAME] |
| **Audit logging** | Every action is logged to `logs/audit.log` |
| **Stop if unsure** | If data sensitivity is unclear — stop and ask |

### Data Classification Guide

| Level | Description | What Claude can do |
|---|---|---|
| **PUBLIC** | Non-sensitive, general info | All tools allowed |
| **INTERNAL** | Internal team data | Approved tools only |
| **CONFIDENTIAL** | Client names, contracts, invoices, salaries | Draft only — no external tools |
| **RESTRICTED** | Secrets, NDA, legal matters, source code keys | Stop immediately — handle manually |

---

## 9. Pending Setup (IT Admin Required)

### SharePoint Integration

The following needs IT Admin action before SharePoint can be connected:

- **Azure App:** AI PipeLine
- **App ID:** `86005979-1675-4637-b217-7d7eb8e3d37c`
- **Tenant ID:** `d4025e3f-3d65-435e-b432-28a328dab4cd`

**IT Admin must:**
1. Go to Azure Portal → App registrations → AI PipeLine
2. Click **API permissions → + Add a permission → SharePoint**
3. Add `Sites.ReadWrite.All` (Application permission)
4. Click **Grant admin consent for Redplanet**
5. Go to **Certificates & secrets → + New client secret**
6. Share the secret value with Darrel Low

Once done, add to `.env`:
```
AZURE_CLIENT_SECRET=<value from IT Admin>
SHAREPOINT_SITE_URL=https://redplanet.sharepoint.com/sites/internal
```

### Google Workspace Integration

Google OAuth not yet configured. Required for:
- Gmail (send emails via `/pipeline_comms`)
- Google Drive (save documents via `/pipeline_document`)
- Google Docs/Sheets

Contact Darrel Low to set this up.

### Zoho Internal Project

Contact **Catherine Lee** (catherine@redplanet.com.my) to create a project named **Internal** in Zoho Projects portal `redplanet0`.

---

## 10. Troubleshooting

### "No matching commands" when typing /pipeline

- Restart VS Code completely
- Make sure the `pipeline-cc` folder is open
- Check that `.claude/commands/` folder exists with the command files

### Logger not responding

```powershell
cd logger
.\start.ps1
```

If port 5000 is already in use:
```powershell
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Zoho token expired

The refresh token does not expire. If you get a 401 error:
- Check that `ZOHO_REFRESH_TOKEN` in `.env` is correct
- Re-run the OAuth flow (Step 3-4 in Zoho Setup)

### GitHub 403 Forbidden

Your token may have expired or insufficient permissions:
- Go to https://github.com/settings/tokens
- Regenerate the token with correct permissions (see Setup — GitHub)
- Update `GITHUB_TOKEN` in `.env`

---

## Project File Structure

```
pipeline-cc/
├── CLAUDE.md                     ← Pipeline rules (read by Claude automatically)
├── README.md                     ← Setup guide
├── .env                          ← Credentials (NEVER share or commit)
├── .mcp.json                     ← MCP server config
├── .claude/
│   └── commands/                 ← Slash commands for VS Code
│       ├── pipeline_research.md
│       ├── pipeline_code.md
│       ├── pipeline_comms.md
│       ├── pipeline_document.md
│       ├── pipeline_daily-summary.md
│       ├── pipeline_status.md
│       └── pipeline_help.md
├── agents/
│   ├── research.md               ← Research agent behaviour
│   ├── code.md                   ← Code agent behaviour
│   ├── comms.md                  ← Comms agent behaviour
│   ├── document.md               ← Document agent behaviour
│   ├── daily-summary.md          ← Daily summary agent behaviour
│   └── daily_summary.py          ← Script to post summary to Zoho
├── logger/
│   ├── app.py                    ← Logger REST API (port 5000)
│   ├── requirements.txt          ← Python dependencies
│   └── start.ps1                 ← Start logger service
└── logs/
    ├── errors.log                ← All errors and warnings
    └── audit.log                 ← All approved pipeline actions
```

---

*For questions or issues, contact Darrel Low — darrel.low@redplanet.com.my*
