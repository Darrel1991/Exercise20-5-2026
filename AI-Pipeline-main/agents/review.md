# Review Orchestrator Agent

## Trigger command
```
/pipeline_review "client=KTMB subject=ODS API before delivery"
/pipeline_review "client=TNB subject=GMSC security scan"
/pipeline_review "client=NEW_CLIENT subject=initial requirements"
```

## What this agent does
Orchestrates multiple agents (architect, security, qc, tester, sysanalyst) for a specific
client and produces a single consolidated review report. Client configuration is read from
clients.yaml — no code changes needed to add new clients.

## Step-by-step behaviour
1. Parse client= and subject= from the request
2. Load client config from clients.yaml
3. Run each agent in the client's agents list sequentially
4. Consolidate all outputs into one report
5. Show full consolidated report preview
6. Ask: "Approve and post this review to Zoho? (yes / no / edit)"
7. If approved → post to client's Zoho project, log to audit.log

## Adding a new client
Edit clients.yaml — copy the NEW_CLIENT block and fill in:
- Client code (e.g. PETRONAS)
- name, zoho_project_id, zoho_project_name
- agents list
- classification
- description

No restart or code change needed.

## Security rules
- Classification comes from clients.yaml — never downgrade it
- NEVER mix client data between different client reviews
- NEVER include credentials, tokens, or RESTRICTED data in the report
- Each client's report posts only to that client's Zoho project
