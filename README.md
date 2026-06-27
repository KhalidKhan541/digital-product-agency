# Digital Product Launch Agency

Automated system to find creators, create digital products, and launch them using AI.

## How It Works

1. **Find Creators** - Daily search for creators with audience but no products
2. **Send Outreach** - Personalized DMs using AI
3. **Create Product** - Generate ebooks, guides, templates with Groq API
4. **Launch** - Email sequences via Gmail SMTP
5. **Track** - CRM dashboard in GitHub

## Setup

1. Fork this repo
2. Add secrets:
   - `GROQ_API_KEY` - Your Groq API key
   - `GMAIL_APP_PASSWORD` - Gmail App Password (see below)
3. Enable Actions
4. Add creators to `data/pipeline.csv`

## Gmail App Password Setup

1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Search "App Passwords"
4. Create password for "Mail"
5. Copy the 16-character password
6. Add as `GMAIL_APP_PASSWORD` secret

## Workflows

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| find-creators | Daily 9AM | Search for potential creators |
| send-outreach | Daily 2PM | Generate personalized DMs |
| create-product | Manual | Create digital product |
| send-emails | Manual | Send launch sequence |
| crm-tracker | Daily 8AM | Track pipeline status |

## Pipeline CSV Format

```csv
name,handle,followers,niche,status,notes
John Doe,@johndoe,25000,fitness,new,Great content no product
```

**Status values:** new, contacted, interested, negotiating, launched

## Cost

- GitHub Actions: Free
- Groq API: Free tier
- Gmail SMTP: Free
- **Total: $0/month**

## License

MIT
