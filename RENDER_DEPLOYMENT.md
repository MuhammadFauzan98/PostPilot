# Deploying PostPilot to Render

This guide will help you deploy your PostPilot application to Render.

## Prerequisites

- A GitHub account with your PostPilot repository
- A Render account (sign up at https://render.com)
- Google OAuth credentials (for Google login functionality)

## Deployment Steps

### 1. Prepare Your Repository

Make sure all the deployment files are committed to your GitHub repository:
- `render.yaml` - Render configuration
- `build.sh` - Build script
- `requirements.txt` - Python dependencies (with gunicorn and psycopg2-binary)

### 2. Create a New Web Service on Render

1. Log in to your Render dashboard
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Render should auto-detect the `render.yaml` file

### 3. Configure Environment Variables

In the Render dashboard, set the following environment variables:

**Required:**
- `SECRET_KEY` - A secure random string (Render can generate this)
- `DATABASE_URL` - Auto-configured if using Render PostgreSQL
- `ENVIRONMENT` - Set to `production`

**For Google OAuth (if using):**
- `GOOGLE_CLIENT_ID` - Your Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Your Google OAuth client secret
- `GOOGLE_REDIRECT_URI` - Your Render app URL + `/auth/google/callback`
  - Example: `https://your-app-name.onrender.com/auth/google/callback`

### 4. Database Setup

If using the included `render.yaml`:
- A PostgreSQL database will be automatically created
- It will be linked to your web service
- The `DATABASE_URL` will be automatically set

### 5. Update Google OAuth Settings

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to your OAuth 2.0 credentials
3. Add your Render URL to "Authorized redirect URIs":
   - `https://your-app-name.onrender.com/auth/google/callback`
4. Add your Render URL to "Authorized JavaScript origins":
   - `https://your-app-name.onrender.com`

### 6. Deploy

1. Click "Create Web Service" in Render
2. Render will:
   - Install dependencies from `requirements.txt`
   - Run the `build.sh` script
   - Start your app with `gunicorn app:app`

### 7. Monitor Deployment

- Check the "Logs" tab in Render to monitor the deployment process
- The first deployment may take 5-10 minutes
- Once complete, your app will be available at `https://your-app-name.onrender.com`

## Troubleshooting

### Database Connection Issues
- Ensure `DATABASE_URL` is set correctly
- Check that psycopg2-binary is in requirements.txt

### Static Files Not Loading
- Verify the upload directory is being created in build.sh
- Check file permissions

### OAuth Redirect Issues
- Ensure `GOOGLE_REDIRECT_URI` matches exactly what's in Google Cloud Console
- Verify `SESSION_COOKIE_SECURE` is set to True in production

## Manual Deployment (Alternative)

If you prefer not to use `render.yaml`:

1. Create a new Web Service manually
2. Set these fields:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment**: Python 3
3. Add a PostgreSQL database from the Render dashboard
4. Link the database to your web service
5. Set all environment variables manually

## Notes

- Render's free tier may have cold starts (app sleeps after inactivity)
- The SQLite database will NOT persist on Render's free tier
- Use PostgreSQL (included in render.yaml) for production
- Make sure to set `SECRET_KEY` to a secure value in production
