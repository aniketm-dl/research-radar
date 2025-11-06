# Darpan Research Radar - Setup Guide

## Quick Setup for Darpan Labs Team

This automated research newsletter system is configured for Darpan Labs to track research on customer digital twins, synthetic users, and LLM agents for consumer research.

### 📧 Email Configuration
- **Recipients**:
  - manav@darpanlabs.ai
  - aniketg@darpanlabs.ai
  - aniketm@darpanlabs.ai
- **From**: aniketm@darpanlabs.ai
- **Subject Format**: `[Darpan Research Radar] - YYYY-MM-DD HH:MM UTC`

### 🚀 Local Testing

Run the setup script to test locally:

```bash
# Make the script executable (if not already)
chmod +x setup_local.sh

# Run the setup script
./setup_local.sh

# Activate virtual environment
source venv/bin/activate

# Run the newsletter
python -m src.run
```

### 🔐 GitHub Repository Setup

1. **Create the GitHub Repository** (if not already created):
   ```bash
   # The repository should be created at:
   # https://github.com/aniketm-dl/research-radar
   ```

2. **Add GitHub Secrets**:

   Go to: Settings > Secrets and variables > Actions

   Add these secrets:
   ```
   GEMINI_API_KEY = [Your Gemini API key - stored separately]

   SMTP_USERNAME = aniketm@darpanlabs.ai

   SMTP_PASSWORD = [Your Gmail app password - stored separately]
   ```

3. **Push the Code**:
   ```bash
   cd research-newsletter
   git add .
   git commit -m "Configure for Darpan Labs deployment"
   git push origin main
   ```

### ⏰ Automated Schedule

The newsletter runs automatically:
- **Every 4 hours**: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
- **Manual trigger**: Go to Actions tab > Research Newsletter > Run workflow

### 📊 Current Search Queries

The system searches for papers matching:
1. Digital twins for consumers/marketing/customers
2. Synthetic users and virtual personas
3. LLM agents for marketing and consumer behavior
4. Agent-based simulation for decision making
5. Survey augmentation and preference prediction
6. Test-retest reliability and accuracy metrics
7. Retrieval-augmented research and evaluation

### 🎯 Customization

To modify search queries, edit `config.yaml`:

```yaml
search:
  queries:
    - "your new search query here"
```

To change recipients, edit `config.yaml`:

```yaml
email:
  recipients:
    - "new.recipient@darpanlabs.ai"
```

### 🔍 Monitoring

1. **Check GitHub Actions**:
   - Go to Actions tab to see run history
   - Click on any run for detailed logs

2. **Email Delivery**:
   - Emails sent to all three recipients
   - Both HTML and plain text versions included

3. **State Tracking**:
   - `state/seen_ids.json` tracks sent papers
   - Automatically updated after each run

### 🆘 Troubleshooting

**If emails aren't sending:**
- Verify SMTP_PASSWORD in GitHub secrets (app password, not regular password)
- Check GitHub Actions logs for error messages
- Ensure Gmail 2FA is enabled and app password is valid

**If no papers are found:**
- Check if queries are too specific
- Increase `search_window_days` in config.yaml
- Verify API connectivity in GitHub Actions logs

**To reset and resend all papers:**
```bash
echo '{"papers": {}, "last_run": null}' > state/seen_ids.json
git add state/seen_ids.json
git commit -m "Reset newsletter state"
git push
```

### 📝 Important Notes

1. **API Key Security**: Never commit API keys directly to code
2. **App Password**: The Gmail password is an app-specific password, not the regular account password
3. **State File**: The system automatically commits state changes after each run
4. **Rate Limiting**: The system respects API rate limits for arXiv and Crossref

### 📞 Support

For issues or modifications, contact the Darpan Labs tech team.

---

**Last Updated**: November 6, 2024
**Configured By**: Aniket M
**Repository**: https://github.com/aniketm-dl/research-radar