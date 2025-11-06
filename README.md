# Research Newsletter - Customer Twins Research Digest

An automated research newsletter system that searches for papers on customer digital twins, synthetic users, and LLM agents for consumer research, summarizes them using OpenAI, and emails digests to your team.

## Features

- **Automated Paper Discovery**: Searches arXiv and Crossref for relevant research papers
- **AI-Powered Summarization**: Uses Google Gemini AI to generate tailored summaries
- **Email Digests**: Sends beautifully formatted HTML and plain text emails
- **Scheduled Execution**: Runs automatically every 4 hours via GitHub Actions
- **Duplicate Prevention**: Tracks sent papers to avoid repetition
- **Configurable Queries**: Customize search queries to match your research interests

## Quick Start

### 1. Fork or Clone the Repository

```bash
git clone https://github.com/aniketm-dl/research-radar.git
cd research-newsletter
```

### 2. Set Up GitHub Repository Secrets

Go to your repository's Settings > Secrets and variables > Actions, and add:

**Required Secrets:**
- `GEMINI_API_KEY`: Your Google Gemini API key (get from https://makersuite.google.com/app/apikey)
- `SMTP_USERNAME`: Your email address (e.g., your.email@gmail.com)
- `SMTP_PASSWORD`: Your email app password (NOT your regular password)
  - For Gmail: Go to Google Account Settings > Security > 2-Step Verification > App passwords
  - Generate an app-specific password for "Mail"

**Optional Secrets:**
- `SMTP_HOST`: SMTP server (default: smtp.gmail.com)
- `SMTP_PORT`: SMTP port (default: 465 for SSL)

### 3. Configure Recipients and Queries

Edit `config.yaml` to customize:

```yaml
email:
  recipients:
    - "team@yourcompany.com"  # Add your email addresses here
    - "researcher@yourcompany.com"
  from_name: "Research Radar"
  from_email: "your.email@gmail.com"  # Must match SMTP_USERNAME

search:
  queries:  # Customize these for your research focus
    - '"digital twin" AND consumer'
    - '"synthetic users" AND evaluation'
    # Add more queries as needed
```

### 4. Test Locally (Optional)

Install dependencies and test the system locally:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY="your-api-key"
export SMTP_USERNAME="your.email@gmail.com"
export SMTP_PASSWORD="your-app-password"

# Run the newsletter generator
python -m src.run
```

### 5. Enable GitHub Actions

The workflow will automatically run:
- Every 4 hours (0:00, 4:00, 8:00, 12:00, 16:00, 20:00 UTC)
- On manual trigger via GitHub Actions tab

To manually trigger:
1. Go to Actions tab in your repository
2. Click "Research Newsletter" workflow
3. Click "Run workflow"
4. Optionally enable debug logging

## Configuration Guide

### Search Queries

The system uses boolean search queries. Examples:

```yaml
search:
  queries:
    # Basic AND/OR operations
    - '"digital twin" AND (consumer OR customer)'

    # Multiple terms
    - '"synthetic users" OR "virtual personas" OR "digital humans"'

    # Complex queries
    - '(LLM OR "large language model") AND agent AND marketing'

    # Phrase matching
    - '"agent based simulation" AND behavior'
```

### Tuning Search Results

Adjust these parameters in `config.yaml`:

```yaml
search:
  search_window_days: 7        # How far back to search
  max_results_per_source: 12   # Results per query per source

summarization:
  max_summaries: 8             # Maximum papers per digest
  model: "gemini-pro"          # Or "gemini-1.5-pro" for enhanced performance
  temperature: 0.2             # Lower = more focused, higher = more creative
  max_tokens: 600              # Length of each summary
```

### Email Settings

```yaml
email:
  subject_prefix: "[Research Digest]"  # Customize subject line
  from_name: "AI Research Bot"         # Display name in emails
```

## Reducing Noise and Improving Relevance

### 1. Refine Search Queries

Make queries more specific:
```yaml
# Instead of:
- "digital twin"

# Use:
- '"digital twin" AND (consumer OR customer) AND (simulation OR model)'
```

### 2. Adjust Time Window

For less frequent but higher quality digests:
```yaml
search:
  search_window_days: 14  # Look back 2 weeks instead of 1
```

### 3. Reduce Maximum Summaries

Focus on top papers only:
```yaml
summarization:
  max_summaries: 5  # Send fewer but more relevant papers
```

### 4. Add Negative Filters

Exclude unwanted topics in queries:
```yaml
queries:
  - '"digital twin" AND consumer NOT industrial NOT manufacturing'
```

## Adding More Sources

To extend the system with additional paper sources:

### Semantic Scholar

Create `src/search_semantic.py`:
```python
class SemanticScholarSearcher:
    def search(self, query, lookback_days, max_results):
        # Implement Semantic Scholar API integration
        # Return papers in standard format
        pass
```

### SSRN RSS Feeds

Create `src/search_ssrn.py`:
```python
class SSRNSearcher:
    def search_rss(self, feed_url, lookback_days):
        # Parse SSRN RSS feeds
        # Return papers in standard format
        pass
```

Then update `src/run.py` to include the new sources.

## Monitoring and Troubleshooting

### View Workflow Runs

1. Go to the Actions tab in your GitHub repository
2. Click on a workflow run to see detailed logs
3. Check for any error messages

### Common Issues

**No papers found:**
- Check if queries are too specific
- Increase `search_window_days`
- Verify arXiv/Crossref APIs are accessible

**Gemini AI errors:**
- Verify API key is correct and valid
- Check rate limits on your Google AI account
- Try a different model (gemini-1.5-pro instead of gemini-pro)
- Check for content safety blocks in the logs

**Email not sending:**
- Verify SMTP credentials are correct
- For Gmail, ensure 2-factor authentication is enabled
- Check that app password (not regular password) is used
- Verify "Less secure app access" or use app passwords

**State file issues:**
- The workflow automatically commits state changes
- If corrupted, delete `state/seen_ids.json` and let it regenerate

### Manual State Reset

To reset and resend all papers:

```bash
# Reset state file
echo '{"papers": {}, "last_run": null}' > state/seen_ids.json

# Commit and push
git add state/seen_ids.json
git commit -m "Reset newsletter state"
git push
```

## Project Structure

```
research-newsletter/
├─ config.yaml               # Main configuration
├─ requirements.txt          # Python dependencies
├─ src/
│  ├─ run.py                # Main coordinator
│  ├─ search_arxiv.py       # arXiv search module
│  ├─ search_crossref.py    # Crossref search module
│  ├─ summarizer.py         # Google Gemini summarization
│  ├─ emailer.py            # SMTP email sender
│  └─ util_state.py         # State management
├─ prompt/
│  └─ summary_prompt.md     # Summarization prompt
├─ state/
│  └─ seen_ids.json         # Tracking sent papers
└─ .github/
   └─ workflows/
      └─ newsletter.yml     # GitHub Actions workflow
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/

# With coverage
pytest --cov=src tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Security Notes

- Never commit API keys or passwords to the repository
- Use GitHub Secrets for all sensitive information
- Regularly rotate API keys and app passwords
- Review email recipients list periodically

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review GitHub Actions logs for detailed error messages
3. Open an issue in the repository with:
   - Error messages
   - Configuration (without secrets)
   - Steps to reproduce

## Next Steps

After setup:
1. Monitor the first few automated runs
2. Adjust queries based on relevance of results
3. Fine-tune the summarization prompt if needed
4. Consider adding more paper sources
5. Set up additional notifications (Slack, Discord) for failures

---

Built with Python, Google Gemini AI, and GitHub Actions. Searches powered by arXiv and Crossref APIs.