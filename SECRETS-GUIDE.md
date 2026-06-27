# Secrets Setup Guide

A beginner-friendly guide to configuring secrets and environment variables.

---

## 1. Groq API Key (Free)

Groq provides fast AI inference with a generous free tier.

### Steps:

1. Go to [console.groq.com](https://console.groq.com)
2. Click **Sign Up** (Google/GitHub login available)
3. After login, click **API Keys** in the left sidebar
4. Click **Create API Key**
5. Name it (e.g., `digital-product-agency`)
6. Copy the key immediately (it won't be shown again)

> **Screenshot description:** The Groq console dashboard shows a sidebar with "API Keys" highlighted. The main area displays a list of keys and a prominent "Create API Key" button.

**Free tier includes:** 30 requests/minute, 13,000+ tokens/minute on Llama 3 70B.

---

## 2. Gmail App Password

Gmail blocks regular password sign-ins from apps. An App Password lets this project send emails securely.

### Steps:

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Click **Security** in the left sidebar
3. Under "How you sign in to Google," click **2-Step Verification**
4. Enable 2FA if not already on (required for App Passwords)
5. Go back to Security, click **App passwords**
6. Under "Select app," choose **Mail**
7. Under "Select device," choose **Other (Custom name)** and type `digital-product-agency`
8. Click **Generate**
9. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

> **Screenshot description:** The App Passwords page shows a dropdown for app type, another for device, a "Generate" button, and a newly created password displayed in a yellow box with a copy icon.

**Important:** You won't be able to see this password again after closing the page.

---

## 3. Adding Secrets to GitHub

These secrets are used by GitHub Actions workflows.

### Steps:

1. Go to your repository on GitHub
2. Click **Settings** (top tab bar)
3. In the left sidebar, expand **Secrets and variables** and click **Actions**
4. Click **New repository secret**
5. Enter the **Name** exactly (case-sensitive) and paste the **Value**
6. Click **Add secret**

> **Screenshot description:** The GitHub Actions secrets page shows a list of existing secrets with eye icons to reveal values. The "New repository secret" button opens a form with Name and Value fields and a green "Add secret" button.

### Required Secrets:

| Secret Name       | Value                          |
|-------------------|--------------------------------|
| `GROQ_API_KEY`    | Your Groq API key              |
| `SENDER_EMAIL`    | Your Gmail address             |
| `GMAIL_APP_PASSWORD` | Your 16-char app password  |
| `RECIPIENT_EMAIL` | Email to receive reports       |

### Optional Secrets (for future Twitter automation):

| Secret Name           | Value                  |
|-----------------------|------------------------|
| `TWITTER_API_KEY`     | From developer.twitter.com |
| `TWITTER_API_SECRET`  | From developer.twitter.com |

---

## 4. Repository Variables (Non-Secret)

Some settings don't need to be secret. Use **Variables** instead:

1. Same page as secrets: **Settings > Secrets and variables > Actions**
2. Click the **Variables** tab
3. Click **New repository variable**
4. Add your variable name and value

> **Screenshot description:** The Variables tab shows a table of variable names and values with edit/delete buttons. The "New repository variable" button opens the same form layout as secrets.

---

## 5. Troubleshooting

### "Authentication failed" email error
- Your App Password may have extra spaces. Remove all spaces.
- Make sure 2-Step Verification is enabled on your Google account.
- Generate a new App Password if the old one was revoked.

### "Invalid API key" for Groq
- Check the secret name matches exactly: `GROQ_API_KEY`
- Ensure no trailing whitespace in the pasted value.
- Verify the key is still active at console.groq.com.

### GitHub Actions can't find secrets
- Secrets in a **forked repo** are not accessible. Use the original repo.
- Secret names are **case-sensitive**. `groq_api_key` is not the same as `GROQ_API_KEY`.
- Secrets are only available to workflows triggered by `push` or `pull_request`, not `workflow_dispatch` from forks.

### "Rate limit exceeded" (Groq)
- Free tier: 30 req/min. If you hit this, add a delay between API calls or upgrade at Groq console.

### Variables vs Secrets
- Use **secrets** for API keys, passwords, tokens.
- Use **variables** for non-sensitive config like email addresses, URLs, feature flags.

---

## Quick Checklist

- [ ] Groq API key created and added as `GROQ_API_KEY` secret
- [ ] 2FA enabled on Google account
- [ ] Gmail App Password generated and added as `GMAIL_APP_PASSWORD` secret
- [ ] `SENDER_EMAIL` and `RECIPIENT_EMAIL` secrets configured
- [ ] Test workflow runs successfully
