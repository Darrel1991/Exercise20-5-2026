# Secure AI Pipeline — Claude Code Instructions

This file is read automatically by Claude Code. It defines how the pipeline works,
what each command does, and the security rules Claude must follow at all times.

---

## What this pipeline does

A team-triggered AI pipeline. A team member runs a slash command in Claude Code,
Claude processes the task securely, shows a preview, and waits for human approval
before taking any action.

---

## Security rules — always follow these

1. NEVER take action (send email, update CRM, push to GitHub) without explicit human approval
2. NEVER process CONFIDENTIAL or RESTRICTED data through external tools
3. ALWAYS show a preview of the output and ask "Approve this? (yes/no)" before acting
4. ALWAYS scrub PII from inputs before processing — replace with [EMAIL], [PHONE], [NAME]
5. ALWAYS log what was done to logs/audit.log after each task
6. If in doubt about data sensitivity — stop and ask the user to clarify

---

## Data classification

Before processing any input, classify it:

- PUBLIC     → any tool allowed
- INTERNAL   → approved tools only, no external sharing
- CONFIDENTIAL → draft only, no external tools, human fills in placeholders
- RESTRICTED → stop immediately, tell user to handle manually

Signals for CONFIDENTIAL: client name, contract, invoice, salary, budget, customer data
Signals for RESTRICTED: source code secrets, trade secrets, NDA, legal matter, lawsuit

---

## Available commands

Run these in Claude Code terminal:

```
GENERAL
/pipeline_research        "your research question"
/pipeline_code            "review PR #123" or "triage issues"
/pipeline_comms           "draft email to [contact] about [topic]"
/pipeline_document        "draft [document type] about [topic]"
/pipeline_daily-summary   post today's activity summary to Zoho Projects
/pipeline_status          show recent pipeline activity
/pipeline_wrap-up         save a session wrap-up to docs/wrap-ups/
/pipeline_help            show all commands

BRAINSTORM & PLANNING
/pipeline_brainstorm      "topic or idea" — open-ended idea generation
/pipeline_team_devlead    "what to build" — framework / language / library recommendations

MULTI-AGENT
/pipeline_review          "client=X subject=Y" — runs all agents, one consolidated report

TEAM AGENTS (Redplanet Software Team)
/pipeline_team_architect   "your design question" — system architecture review
/pipeline_team_sysanalyst  "requirements to analyse" — requirements + MoSCoW
/pipeline_team_qc          "what to review" — quality check
/pipeline_team_security    "what to review" — client data protection + OWASP
/pipeline_team_tester      "what to test" — API + system integration tests
/pipeline_team_dba         "DB request" — Views, Stored Procs, Functions, Indexes,
                            query analysis, deadlock troubleshooting (SQL Server default)
```

## Install / re-install into a new project folder

When pasting `pipeline-cc` into a new folder:
1. Copy the ENTIRE folder — including `.claude/commands/` and `agents/`
2. Both directories must arrive intact — do not rely on partial copies
3. Verify with `/pipeline_help` after install — it must list ALL 17 commands above
4. If any command is missing, the corresponding file in `.claude/commands/` was not copied

---

## Agent behaviour rules

### Research Agent
- Summarise findings clearly with sources
- Flag low-confidence information
- Never present unverified data as fact

### Code Agent
- Review PRs for quality, security, and test coverage
- Triage issues by priority (P1–P4)
- NEVER push or merge — read only unless user explicitly approves a specific action
- Flag any secrets or credentials found in code immediately

### Comms / CRM Agent
- Always produce a DRAFT — never send autonomously
- Show full email preview before any send action
- For CRM updates: show exactly what field changes before writing

### Daily Summary Agent
- Summarise all activity from the current conversation (commands run, integrations set up, tasks completed, issues encountered)
- Format as a clean daily activity log
- Ask user to confirm the summary before posting
- Post to Zoho Projects as a new task using `python agents/daily_summary.py`
- Default project: check if "Internal" project exists — if not, post to "TNB Mobile GIS"
- Classification: INTERNAL

### Document Agent
- Use [PLACEHOLDER] for any data not provided
- For CONFIDENTIAL requests: framework only, human fills in sensitive details
- Show full document before filing to Google Drive

---

## Approval gate

Every command follows this flow:

1. Claude processes the task
2. Claude shows the output preview
3. Claude asks: "Approve this action? (yes / no / edit)"
4. User responds
5. If yes → Claude executes
6. If no → Claude discards
7. If edit → user gives feedback, Claude revises and asks again

---

## Audit log format

After every completed task, append to logs/audit.log:
```
[TIMESTAMP] | USER: [username] | COMMAND: [command] | CLASSIFICATION: [level] | ACTION: [what was done] | STATUS: [approved/rejected]
```
