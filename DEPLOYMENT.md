# 🚀 Deploying PDFChat to Render

This guide will help you deploy your PDFChat API to Render's free tier.

## Prerequisites

- GitHub account (to connect your repository)
- Google API Key (for Gemini AI) - [Get one here](https://ai.google.dev/)
- Render account (free) - [Sign up here](https://render.com)

## Quick Start (5-10 minutes)

### Step 1: Push to GitHub

Ensure your latest code (including `render.yaml`) is pushed to your repository:

```bash
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

### Step 2: Deploy on Render

1. **Sign up/Login** to [Render](https://render.com)
   - Use "Sign in with GitHub" for easy integration

2. **Create New Blueprint**
   - Click "New +" button → Select "Blueprint"
   - Connect your GitHub account if not already connected
   - Select repository: `DragonneHymz/PDFChat` (or your fork)
   - Render will auto-detect the `render.yaml` file

3. **Configure Environment Variables**
   - Render will prompt for required secrets
   - **IMPORTANT**: Set `GOOGLE_API_KEY` to your actual Google AI API key
   - `SECRET_KEY` will be auto-generated (or set your own)
   - Other variables are pre-configured in `render.yaml`

4. **Deploy**
   - Click "Apply" to start deployment
   - First build takes 2-3 minutes
   - Monitor progress in the Render dashboard

### Step 3: Access Your API

Once deployed, you'll get a URL like:
```
https://pdfchat-api-xyz.onrender.com
```

**Test your deployment:**
- API Docs: `https://your-app.onrender.com/docs`
- Health Check: `https://your-app.onrender.com/` (should return {"message": "Welcome to PDFChat API"})

## What Gets Deployed

✅ FastAPI backend with all endpoints  
✅ SQLite database (persistent storage)  
✅ ChromaDB vector database (persistent storage)  
✅ Agent memory (LangGraph checkpointer)  
✅ File upload support (max 20MB)  
✅ HTTPS/SSL (automatic)  
✅ CORS enabled (for frontend integration)  

## Persistent Storage

Render mounts a 1GB persistent disk at `/opt/render/project/src/data` for:
- `pdfchat.db` - SQLite database
- `chroma_db/` - Vector embeddings
- `agent_memory.db` - Conversation checkpoints

**This data persists across deployments and restarts.**

## Environment Variables

Configure these in Render dashboard:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | ✅ Yes | - |
| `SECRET_KEY` | JWT signing key | ✅ Yes | Auto-generated |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | No | 60 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | No | 7 |
| `SESSION_INACTIVITY_DAYS` | Auto-archive inactive sessions | No | 30 |
| `SESSION_RETENTION_DAYS` | Delete old sessions | No | 90 |

## Free Tier Limitations

- **Instance spins down** after 15 minutes of inactivity
- **Cold start**: First request takes ~50 seconds after spin-down
- **Memory**: 512MB RAM
- **Storage**: 1GB persistent disk
- **Build minutes**: 500 hours/month runtime

💡 **Tip**: Subsequent requests are fast once the instance is running.

## Auto-Deployment

Render automatically deploys when you push to your default branch (main):

```bash
git push origin main
# Render starts building automatically (~2-3 minutes)
```

## Monitoring & Logs

**View logs in Render dashboard:**
1. Go to your service
2. Click "Logs" tab
3. Real-time logs appear here

**Check service status:**
- Green = Running
- Yellow = Building
- Red = Failed (check logs)

## Common Issues & Solutions

### 1. Cold Start Delays
**Problem**: First request after inactivity takes 50+ seconds  
**Solution**: This is normal on free tier. Consider paid tier ($7/month) for always-on instances.

### 2. Build Fails
**Problem**: Deployment fails during build  
**Solution**: Check logs for missing dependencies or Python version issues.
```bash
# Ensure requirements.txt is up to date locally
pip freeze > requirements.txt
```

### 3. GOOGLE_API_KEY Not Set
**Problem**: 500 errors related to Google AI  
**Solution**: Set `GOOGLE_API_KEY` in Render dashboard → Environment section.

### 4. Database Locked Errors
**Problem**: SQLite database locked  
**Solution**: Rare on single-instance setup. Check logs and restart service if needed.

## Updating Your Deployment

Simple git workflow:

```bash
# Make changes locally
git add .
git commit -m "Your update message"
git push origin main

# Render auto-deploys in 2-3 minutes
```

## Testing Locally Before Deploying

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env-template .env
# Edit .env with your GOOGLE_API_KEY

# Run locally
uvicorn api:app --reload

# Test at http://localhost:8000/docs
```

## Connecting a Frontend

Update your frontend API base URL to:
```javascript
const API_BASE_URL = 'https://your-app.onrender.com'
```

CORS is already configured to allow all origins.

## Upgrading to Paid Tier

For production use, consider Render's paid tiers ($7+/month):
- ✅ No cold starts (always-on)
- ✅ More memory & CPU
- ✅ Auto-scaling
- ✅ More storage

---

## Quick Reference Commands

```bash
# View render.yaml
cat render.yaml

# Check environment variables
cat .env-template

# Test locally
uvicorn api:app --reload --port 8000

# Deploy
git push origin main
```

## Support

- **Render Docs**: https://render.com/docs
- **PDFChat Issues**: https://github.com/DragonneHymz/PDFChat/issues
- **Google AI Studio**: https://ai.google.dev/

---

**Ready to deploy?** Just follow Step 2 above and you'll be live in minutes! 🎉
