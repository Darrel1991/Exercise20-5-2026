# Daily Summary Agent

## Trigger command
```
/pipeline:daily-summary
```

## What this agent does
Summarises everything done today in the current session and posts it as a new task
to Zoho Projects. Requires approval before posting.

## Step-by-step behaviour

1. **Collect** — scan the current session for all actions taken today:
   - Pipeline commands run
   - Integrations set up or tested
   - GitHub activity (repos created, commits, branches)
   - Zoho tasks created or updated
   - Errors encountered and resolved
   - Pending items not yet completed
2. **Draft** the summary using the output format below
3. **Show preview** to user
4. **Ask**: "Post this to Zoho? (yes / no / edit)"
5. **If approved** → run `python agents/daily_summary.py --summary "..." --date "YYYY-MM-DD"`
6. **Log** to logs/audit.log

## Output format

```
📋 DAILY SUMMARY — [DATE]
─────────────────────────────────────────
User:    [name]
Project: [Zoho project name]
Date:    [today's date]

✅ Completed Today:
• [task/action 1]
• [task/action 2]
• [task/action 3]

⏳ In Progress:
• [item still being worked on]

🔲 Pending / Blocked:
• [item blocked — reason]

─────────────────────────────────────────
Post this summary to Zoho Projects? (yes / no / edit)
```

## Zoho posting behaviour
- Script: `python agents/daily_summary.py`
- Default project: "Internal" (if exists) → fallback to "TNB Mobile GIS"
- Task name: `Daily Summary - [DATE]`
- Task description: full summary text
- Assigned to: current user (darrel.low@redplanet.com.my)

## Security rules
- Classification: INTERNAL — do not include CONFIDENTIAL or RESTRICTED data
- Never post without user approval
- Scrub any credentials or tokens from the summary
