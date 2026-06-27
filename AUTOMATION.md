# Automation Guide

This document explains the complete automated system for your digital product agency.

## How It Works

- System runs 100% on GitHub Actions
- No server needed, no costs
- All reports sent to your email

---

## Daily Automation

| Time (UTC) | Time (PKT) | What Runs | What You Get |
|------------|------------|-----------|--------------|
| 10:00 AM | 3:00 PM | DM Sender | Email with DMs to send |
| 8:00 PM | 1:00 AM | Daily Report | Email with summary |

---

## Weekly Automation

| Day | Time | What Runs | What You Get |
|-----|------|-----------|--------------|
| Monday | 8:00 AM | Find Creators | New creator list |
| Sunday | 9:00 AM | Weekly Report | Full analytics |

---

## Manual Workflows

| Workflow | When to Use |
|----------|-------------|
| auto-email-sender | When creator says yes |
| pipeline-updater | When status changes |
| auto-create-product | When ready to build |

---

## Secrets Required

| Secret | Purpose |
|--------|---------|
| GROQ_API_KEY | AI content generation |
| GMAIL_APP_PASSWORD | Email sending |
| SENDER_EMAIL | Your email |
| RECIPIENT_EMAIL | Where to send reports |

---

## Your Daily Routine

1. Check email for DMs (3 PM PKT)
2. Copy DMs to Twitter
3. Check email for daily report (1 AM PKT)
4. Update pipeline when creators reply
5. Run email sender when launching

---

## Files

| File | Purpose |
|------|---------|
| data/pipeline.csv | All creators |
| data/generated-dms.md | Today's DMs |
| data/email-log.md | Email history |
| data/reports/ | Weekly reports |
