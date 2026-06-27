# Workflows Index

## Auto Workflows (Run Automatically)

| Workflow | Schedule | What It Does |
|----------|----------|--------------|
| auto-find-creators | Monday 8AM UTC | Weekly search for new content creators using AI-generated Twitter queries |
| auto-generate-dms | Daily 10AM UTC | Generates personalized DMs for new creators in pipeline |
| find-creators | Daily 9AM UTC | Daily creator search across fitness, finance, tech, lifestyle niches |
| send-outreach | Daily 2PM UTC | Sends outreach DMs to creators (dry run by default) |
| crm-tracker | Daily 8AM UTC | Generates CRM dashboard with pipeline status and counts |

## Manual Workflows (Trigger When Needed)

| Workflow | Trigger | What It Does |
|----------|---------|--------------|
| create-product | Manual | Creates digital product (ebook, template, course, guide) with outline, content, landing page, and email sequence |
| send-emails | Manual | Generates and sends 5-email launch sequence to creator |
| auto-send-emails | Manual | Sends individual emails from templates with variable replacement |

## How to Trigger Manual Workflow

1. Go to **Actions** tab in GitHub
2. Select workflow from the left sidebar
3. Click **Run workflow**
4. Fill in required inputs
5. Click **Run workflow** button

### Input Reference

| Workflow | Inputs Required |
|----------|-----------------|
| create-product | creator_name, creator_handle, product_type (ebook/template/course/guide), niche |
| send-emails | recipient_email, recipient_name, product_name, launch_day (YYYY-MM-DD) |
| auto-send-emails | creator_email, creator_name, product_name, email_number (1-8) |

## Workflow Dependencies

```
find-creators / auto-find-creators
        │
        ▼
  data/pipeline.csv (new creators)
        │
        ▼
auto-generate-dms
        │
        ▼
   send-outreach
        │
        ▼
  (Creator responds)
        │
        ▼
   create-product
        │
        ▼
    send-emails / auto-send-emails
        │
        ▼
   data/email-log.md
```

### Dependency Details

| Workflow | Depends On | Produces |
|----------|------------|----------|
| find-creators | — | data/creators-report.md |
| auto-find-creators | — | data/search-report.md |
| auto-generate-dms | data/pipeline.csv | data/dm-log.md |
| send-outreach | data/pipeline.csv | data/dm-log.md |
| crm-tracker | data/pipeline.csv | data/crm-report.md |
| create-product | — | data/product.md |
| send-emails | data/email-templates.md | data/email-log.md |
| auto-send-emails | templates/email-templates.md | data/email-log.md |

## Key Files

| File | Description |
|------|-------------|
| `data/pipeline.csv` | Creator pipeline (name, handle, followers, niche, status) |
| `data/email-log.md` | Log of all sent emails |
| `data/dm-log.md` | Log of generated/sent DMs |
| `data/crm-report.md` | Daily CRM dashboard |
| `templates/email-templates.md` | 8-email sequence templates |
| `data/product.md` | Generated product content |

## Secrets Required

| Secret | Used By |
|--------|---------|
| GROQ_API_KEY | All AI-powered workflows |
| GMAIL_APP_PASSWORD | send-emails, auto-send-emails |
| SENDER_EMAIL | send-emails (vars), auto-send-emails (vars) |

## Pipeline Statuses

| Status | Meaning |
|--------|---------|
| new | Creator discovered, not yet contacted |
| contacted | DM or email sent, awaiting response |
| interested | Creator responded positively |
| product-created | Product generated for creator |
| launched | Product live and generating revenue |
