#!/bin/bash

echo "🚀 Member Moments GitHub Setup Script"
echo "======================================"
echo ""

echo "📋 Next Steps to Complete GitHub Setup:"
echo ""

echo "1. 🌐 Go to GitHub.com and create a new repository:"
echo "   - Visit: https://github.com/new"
echo "   - Repository name: member-mom (or your preferred name)"
echo "   - Make it Public (required for free GitHub Actions)"
echo "   - Don't initialize with README (we already have one)"
echo "   - Click 'Create repository'"
echo ""

echo "2. 🔗 Add the remote origin (replace YOUR_USERNAME with your GitHub username):"
echo "   git remote add origin https://github.com/YOUR_USERNAME/member-mom.git"
echo ""

echo "3. 📤 Push your code:"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""

echo "4. 🔐 Set up GitHub Secrets:"
echo "   - Go to your repository → Settings → Secrets and variables → Actions"
echo "   - Click 'New repository secret'"
echo "   - Add SLACK_WEBHOOK_URL with your Slack webhook"
echo "   - Add NEWSAPI_KEY with your NewsAPI key (optional)"
echo ""

echo "5. ✅ The GitHub Action will run automatically every day at 9 AM UTC!"
echo ""

echo "📚 For manual runs:"
echo "   - Go to Actions tab → 'Scheduled Member Moments Run' → 'Run workflow'"
echo ""

echo "🔧 To test locally first:"
echo "   python -m src.main --csv companies_with_locations.csv --config config.yaml --since_days 1"
echo ""

echo "Need help? Check DEPLOYMENT.md for detailed instructions!"
