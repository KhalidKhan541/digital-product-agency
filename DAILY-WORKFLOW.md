# Daily Workflow — Digital Product Agency

## Daily Schedule (Your Time: PKT)

### Morning (9 AM PKT / 4 AM UTC)

**Check GitHub Actions for overnight runs**
- Review workflow runs in the Actions tab
- Identify any failures that need attention
- Note successful pipeline progress

**Review daily briefing issue**
- Open the latest daily briefing issue
- Review summary of overnight activity
- Note any action items flagged

**Check pipeline status**
- Review pipeline board or tracking issue
- Identify new creators added to pipeline
- Note any creators ready for next step

### Mid-Day (12 PM PKT / 7 AM UTC)

**Review generated DMs**
- Check any auto-generated DM drafts
- Edit or approve drafts for sending
- Ensure personalization is appropriate

**Send DMs to new creators**
- Send approved DMs via Twitter/X
- Log sent messages in pipeline
- Schedule follow-up reminders

**Update pipeline status**
- Mark DMs as sent
- Update creator status in tracking
- Note any responses received

### Evening (6 PM PKT / 1 PM UTC)

**Check for replies**
- Review Twitter/X DM inbox
- Check email for creator responses
- Note interested creators

**Update pipeline with responses**
- Move replied creators to next stage
- Flag any issues or objections
- Schedule follow-ups for non-responders

**Run create-product for interested creators**
- Initiate product creation for confirmed creators
- Provide necessary assets or information
- Track product creation progress

### Night (9 PM PKT / 4 PM UTC)

**Send email sequences**
- Trigger scheduled email sequences
- Review email content before sending
- Log sent emails in pipeline

**Review analytics**
- Check pipeline conversion metrics
- Review product launch performance
- Note any trends or patterns

**Plan tomorrow**
- Review next day's schedule
- Prepare any needed materials
- Set priorities for morning

---

## Weekly Tasks

### Monday: Find New Creators
- Search for potential creator partners
- Research creator audiences and content
- Add qualified creators to pipeline

### Tuesday-Wednesday: Send Outreach
- Send initial DMs to new creators
- Follow up with previous outreach
- Track response rates

### Thursday-Friday: Follow Up
- Follow up with non-responders
- Engage with interested creators
- Move conversations forward

### Weekend: Create Products, Launch
- Finalize product creation
- Launch products with creators
- Monitor launch performance

---

## Automation Summary

### Automated (No Manual Action Required)

| Workflow | Trigger | What It Does |
|----------|---------|--------------|
| Daily Briefing | Cron: 4 AM UTC | Summarizes pipeline status and overnight activity |
| DM Generation | Cron: 6 AM UTC | Generates personalized DM drafts for new creators |
| Email Sequences | Cron: 5 PM UTC | Sends scheduled follow-up emails |
| Pipeline Tracking | On push | Updates pipeline status based on activity |
| Product Creation | Manual trigger | Creates digital product assets |

### Manual Actions Required

| Task | When | How |
|------|------|-----|
| Send DMs | Mid-Day | Review and send via Twitter/X |
| Check replies | Evening | Review inbox and update pipeline |
| Run create-product | Evening | Trigger workflow manually |
| Review analytics | Night | Check dashboard and metrics |
| Plan tomorrow | Night | Review pipeline and set priorities |

---

## Quick Commands

### Check Pipeline Status
```
gh issue list --label "pipeline" --state open
```

### View Latest Briefing
```
gh issue list --label "daily-briefing" --limit 1
```

### Trigger DM Generation
```
gh workflow run generate-dms
```

### Trigger Product Creation
```
gh workflow run create-product -f creator="CREATOR_NAME"
```

### Send Email Sequence
```
gh workflow run send-emails -f sequence="welcome"
```

### View Workflow Runs
```
gh run list --limit 5
```

### Check Failed Runs
```
gh run list --status failure --limit 5
```

---

## Notes

- All times are in PKT (Pakistan Standard Time, UTC+5)
- Pipeline tracking is maintained in GitHub Issues
- Product assets are stored in the designated repository
- Analytics are updated after each major action
