# Deployment Guide for Member Moments

This guide covers several options for hosting and scheduling your Member Moments application.

## Option 1: GitHub Actions (Recommended for Starters)

**Pros:** Free, easy setup, no server management
**Cons:** Limited to GitHub repository, no persistent storage

### Setup Steps:

1. **Push your code to GitHub** (if not already done)
2. **Set up GitHub Secrets:**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add `SLACK_WEBHOOK_URL` with your Slack webhook
   - Add `NEWSAPI_KEY` with your NewsAPI key (optional)
3. **The workflow will run automatically** every day at 9 AM UTC
4. **Manual runs:** Go to Actions tab → "Scheduled Member Moments Run" → "Run workflow"

### Customize Schedule:
Edit `.github/workflows/scheduled-run.yml` and modify the cron expression:
```yaml
- cron: '0 9 * * *'  # Daily at 9 AM UTC
- cron: '0 */6 * * *'  # Every 6 hours
- cron: '0 9,17 * * *'  # Daily at 9 AM and 5 PM UTC
```

## Option 2: Docker + Cron (VPS/Cloud Server)

**Pros:** Full control, persistent storage, customizable
**Cons:** Requires server management, costs money

### Setup Steps:

1. **Deploy to a VPS** (DigitalOcean, Linode, AWS EC2, etc.)
2. **Install Docker:**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```
3. **Clone your repository:**
   ```bash
   git clone <your-repo>
   cd member_mom
   ```
4. **Set environment variables:**
   ```bash
   export SLACK_WEBHOOK_URL="your_webhook_url"
   export NEWSAPI_KEY="your_newsapi_key"
   ```
5. **Run with Docker:**
   ```bash
   docker-compose up -d
   ```
6. **Set up cron for scheduling:**
   ```bash
   crontab -e
   # Add this line to run every 6 hours:
   0 */6 * * * cd /path/to/member_mom && docker-compose run --rm member-mom
   ```

## Option 3: Python Scheduler Script (VPS/Cloud Server)

**Pros:** Simple, lightweight, easy to debug
**Cons:** Requires Python environment, manual process management

### Setup Steps:

1. **Deploy to a VPS**
2. **Install Python and dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Set environment variables:**
   ```bash
   export SLACK_WEBHOOK_URL="your_webhook_url"
   export NEWSAPI_KEY="your_newsapi_key"
   ```
4. **Run the scheduler:**
   ```bash
   python3 scheduler.py
   ```
5. **For production, use systemd service:**
   ```bash
   # Edit member-mom.service with correct paths
   sudo cp member-mom.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable member-mom
   sudo systemctl start member-mom
   ```

## Option 4: Cloud Functions (AWS Lambda, Google Cloud Functions)

**Pros:** Serverless, pay-per-use, auto-scaling
**Cons:** More complex setup, cold starts, time limits

### AWS Lambda Setup:

1. **Create Lambda function** with Python 3.11 runtime
2. **Upload your code** as a ZIP file
3. **Set environment variables** for Slack webhook and NewsAPI key
4. **Configure CloudWatch Events** for scheduling
5. **Set timeout** to 15 minutes (maximum)

## Option 5: Heroku (Simple Cloud Hosting)

**Pros:** Easy deployment, free tier available
**Cons:** Limited free tier, no persistent storage

### Setup Steps:

1. **Install Heroku CLI**
2. **Create Heroku app:**
   ```bash
   heroku create your-member-mom-app
   ```
3. **Set environment variables:**
   ```bash
   heroku config:set SLACK_WEBHOOK_URL="your_webhook_url"
   heroku config:set NEWSAPI_KEY="your_newsapi_key"
   ```
4. **Deploy:**
   ```bash
   git push heroku main
   ```
5. **Set up scheduler addon:**
   ```bash
   heroku addons:create scheduler:standard
   heroku addons:open scheduler
   # Add command: python -m src.main --csv companies_with_locations.csv --config config.yaml --since_days 1
   ```

## Environment Variables

Set these in your hosting environment:

- `SLACK_WEBHOOK_URL`: Your Slack incoming webhook URL
- `NEWSAPI_KEY`: Your NewsAPI key (optional)

## Monitoring and Logs

- **GitHub Actions:** Check the Actions tab for run history
- **Docker:** `docker-compose logs -f member-mom`
- **Systemd:** `sudo journalctl -u member-mom -f`
- **Scheduler script:** Check `scheduler.log` file

## Troubleshooting

### Common Issues:

1. **Slack webhook not working:**
   - Verify webhook URL is correct
   - Check if webhook is still active in Slack
   - Test with a simple curl command

2. **NewsAPI rate limits:**
   - Check your API key usage
   - Consider upgrading plan or reducing frequency

3. **Database issues:**
   - Ensure `events.db` is writable
   - Check disk space
   - Verify file permissions

### Debug Mode:
Run the app manually to see detailed output:
```bash
python -m src.main --csv companies_with_locations.csv --config config.yaml --since_days 1 --verbose
```

## Security Considerations

1. **Never commit API keys** to your repository
2. **Use environment variables** for sensitive data
3. **Restrict file permissions** on production servers
4. **Regular updates** for dependencies
5. **Monitor logs** for unusual activity

## Cost Estimates

- **GitHub Actions:** Free (2,000 minutes/month for public repos)
- **VPS:** $5-20/month depending on provider
- **AWS Lambda:** ~$0.20/month for daily runs
- **Heroku:** Free tier available, then $7/month
- **Google Cloud Functions:** Free tier available, then pay-per-use
