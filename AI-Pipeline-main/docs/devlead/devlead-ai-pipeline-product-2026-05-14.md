DEV LEAD RECOMMENDATION
───────────────────────────────────────
Topic:          AI Pipeline product — sellable to other companies
Classification: INTERNAL
Date:           2026-05-14
Context:        Redplanet Software — small team, consultancy, SaaS product pivot

What We're Building:
A commercial AI assistant pipeline product — similar to what Redplanet built
internally (AiPipeline) but packaged as a multi-tenant SaaS. Target buyers are
SMEs and mid-size companies in Malaysia that want an AI-assisted workflow
(research, document drafting, project management integration, team agents) but
lack the technical resources to build it themselves. Each customer gets their
own workspace, their own integrations (Zoho, GitHub, SharePoint), and their
own agents — all managed through a web dashboard without needing VS Code or
Claude Code.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDED STACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Language:    Python (backend) + TypeScript (frontend) — Python owns the AI
             agent logic you already have; TypeScript gives type-safe React UI
Framework:   FastAPI (backend API) + Next.js (frontend dashboard) — FastAPI is
             async-ready for LLM streaming; Next.js handles auth, routing, SSR
Database:    PostgreSQL (tenant data, audit logs) + Redis (session cache,
             job queue) — Postgres is battle-tested; Redis handles async agent
             jobs without blocking the UI
Hosting:     AWS (ap-southeast-1 Singapore) — closest region to Malaysia,
             meets data residency expectations for Malaysian enterprise clients;
             use ECS Fargate (no server management) + RDS Postgres + ElastiCache
Key Library: Anthropic Python SDK (Claude agents) + LangChain (optional agent
             orchestration) + Celery + Redis (async job queue for long-running
             agent tasks)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALTERNATIVES CONSIDERED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Option A: No-code platform (n8n / Make.com white-label)
  Pros: Fastest to market, no infrastructure to build
  Cons: Limited customisation, you don't own the product, margin is thin,
        hard to differentiate from competitors
  When to pick this instead: If you want to validate demand in under 4 weeks
                             before committing to a full build

Option B: Azure (instead of AWS)
  Pros: Easier SharePoint/M365 integration, familiar if IT Admin is Microsoft-
        aligned, Azure OpenAI available as fallback LLM
  Cons: More complex pricing, slightly higher ops overhead for a small team
  When to pick this instead: If most target clients are heavy Microsoft shops
                             (government, GLCs) — Azure makes the sales pitch easier

Option C: Supabase (instead of PostgreSQL + Redis separately)
  Pros: Faster to set up, built-in auth, real-time subscriptions, free tier
  Cons: Less control at scale, hosted outside Malaysia (data residency risk
        for CONFIDENTIAL client data)
  When to pick this instead: MVP only — swap to self-hosted Postgres before
                             onboarding paying enterprise clients

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEAM STRUCTURE SUGGESTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Minimum team:  1 backend dev (FastAPI + agents)
               1 frontend dev (Next.js)
               1 DBA (PostgreSQL)
               1 product owner (Darrel)

Ideal team:    Add 1 DevOps/cloud engineer (AWS, CI/CD)
               Add 1 QA engineer
               Add 1 sales/BD (Malaysian market)

DBA Requirements:
  Must have:  PostgreSQL Views, Functions, Stored Procedures
              Query performance tuning (EXPLAIN ANALYZE, index design)
              Deadlock analysis and resolution
              Schema design for multi-tenant SaaS
  Good to have: Redis experience, AWS RDS management, PDPA-aware
                data handling (Malaysian compliance)

Key hire priority:
  1st → DBA (unblocks schema design and audit log structure)
  2nd → Frontend dev (unblocks the sellable dashboard)
  3rd → DevOps (unblocks production deployment)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EFFORT ESTIMATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MVP:          6–8 weeks — web dashboard + one tenant, 3 agents (research,
              document, daily summary), Zoho integration, basic auth
Version 1.0:  4–5 months — multi-tenant, all 14 current agents, Zoho + GitHub
              integrations, audit logs, subscription billing (Stripe or iPay88
              for Malaysian market), onboarding flow
Full product: 8–10 months — custom agent builder (clients define their own
              agents via UI), white-label option, SSO, SLA support tier,
              Malaysian compliance (PDPA), API for OpenClaw/external agents

Risk: Anthropic API cost at scale — each customer running agents daily will
      accumulate significant token costs. Mitigate with usage caps per tier,
      prompt caching (already supported by Claude API), and tiered pricing
      that reflects actual API spend.

Decision: Build on FastAPI + Next.js + PostgreSQL hosted on AWS Singapore —
          reuse all existing Python agent logic, add a multi-tenant web
          dashboard, and go to market in 6–8 weeks with an MVP targeting
          2–3 pilot customers from Redplanet's existing client base.
───────────────────────────────────────
Approved by: Darrel Low (darrel.low@redplanet.com.my)
Date:        2026-05-14
