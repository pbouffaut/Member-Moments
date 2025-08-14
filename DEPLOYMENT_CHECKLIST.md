# 🚀 GitHub Deployment Checklist

## ✅ Completed Steps
- [x] Git repository initialized
- [x] All files committed
- [x] GitHub Actions workflow created
- [x] Dependencies installed and tested locally
- [x] App runs successfully

## 🔄 Next Steps to Complete

### 1. Create GitHub Repository
- [ ] Go to [https://github.com/new](https://github.com/new)
- [ ] Repository name: `member-mom` (or your preferred name)
- [ ] **IMPORTANT**: Make it **Public** (required for free GitHub Actions)
- [ ] Don't initialize with README (we already have one)
- [ ] Click "Create repository"

### 2. Connect and Push to GitHub
```bash
# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/member-mom.git

# Rename branch to main (GitHub standard)
git branch -M main

# Push your code
git push -u origin main
```

### 3. Set Up GitHub Secrets
- [ ] Go to your repository → **Settings** → **Secrets and variables** → **Actions**
- [ ] Click **"New repository secret"**
- [ ] Add `SLACK_WEBHOOK_URL` with your Slack webhook URL
- [ ] Add `NEWSAPI_KEY` with your NewsAPI key (optional)

### 4. Verify GitHub Actions
- [ ] Go to **Actions** tab in your repository
- [ ] You should see "Scheduled Member Moments Run" workflow
- [ ] It will run automatically every day at 9 AM UTC
- [ ] For testing: Click "Run workflow" button

## 🧪 Test Your Deployment

### Manual Test Run
1. Go to Actions tab
2. Click "Scheduled Member Moments Run"
3. Click "Run workflow"
4. Watch the workflow execute
5. Check the logs for any errors

### Expected Behavior
- ✅ Workflow starts successfully
- ✅ Dependencies install
- ✅ App runs and processes companies
- ✅ Slack notifications sent (if configured)
- ✅ Results uploaded as artifacts

## 🔧 Troubleshooting

### Common Issues
- **Workflow not showing**: Make sure repository is public
- **Dependencies fail**: Check requirements.txt is committed
- **Slack errors**: Verify webhook URL in secrets
- **Permission errors**: Check file paths in workflow

### Debug Commands
```bash
# Test locally first
python -m src.main --csv companies_with_locations.csv --config config.yaml --since_days 1

# Check git status
git status

# View workflow logs
# Go to Actions tab → Click on workflow run → View logs
```

## 📅 Schedule Customization

To change when the app runs, edit `.github/workflows/scheduled-run.yml`:

```yaml
# Current: Daily at 9 AM UTC
- cron: '0 9 * * *'

# Options:
- cron: '0 */6 * * *'      # Every 6 hours
- cron: '0 9,17 * * *'     # 9 AM and 5 PM UTC
- cron: '0 9 * * 1-5'      # Weekdays only at 9 AM
```

## 🎯 Success Indicators

You'll know it's working when:
- ✅ GitHub Actions tab shows successful workflow runs
- ✅ Slack receives notifications (if configured)
- ✅ Artifacts are uploaded after each run
- ✅ No errors in workflow logs

## 📞 Need Help?

- Check the full `DEPLOYMENT.md` for detailed instructions
- Review GitHub Actions logs for specific error messages
- Test locally first to isolate issues

---

**🎉 Once completed, your Member Moments app will run automatically every day!**
