# Deployment Guide

## Deploy to Streamlit Cloud (Recommended)

Streamlit Cloud provides free hosting for Streamlit apps directly from GitHub.

### Prerequisites
- A public GitHub repository with the project code
- A Streamlit Cloud account (free)

### Steps

1. **Push your code to GitHub**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/investment-analysis.git
   git push -u origin main
   ```

2. **Sign up for Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

3. **Create a new app**
   - Click "New app"
   - Select your GitHub repository
   - Set the main file path to `app.py`
   - Click "Deploy"

4. **Configure Secrets**
   In the Streamlit Cloud dashboard, go to your app's settings and add your API keys under "Secrets":

   ```toml
   OPENAI_API_KEY = "sk-your-key-here"
   ALPHA_VANTAGE_API_KEY = "your-key-here"
   POLYGON_API_KEY = "your-key-here"
   PERPLEXITY_API_KEY = "pplx-your-key-here"
   NEWS_API_KEY = "your-key-here"
   OPENAI_MODEL = "gpt-4o-mini"
   ```

   These secrets are encrypted and never exposed in your code or repository.

5. **Your app is live!**
   Streamlit Cloud will provide a URL like `https://your-app.streamlit.app`

### Auto-Deploy
Streamlit Cloud automatically redeploys when you push to the main branch.

### Resource Limits (Free Tier)
- 1 GB RAM
- Apps sleep after inactivity (wake on visit)
- Public apps only on free tier

## Run Locally

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/investment-analysis.git
cd investment-analysis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## Streamlit Configuration

The `.streamlit/config.toml` file contains app settings:

```toml
[server]
maxUploadSize = 200
enableXsrfProtection = true

[theme]
primaryColor = "#c46161ff"
backgroundColor = "#202b3bff"
```

Customize these to match your preferred theme.
