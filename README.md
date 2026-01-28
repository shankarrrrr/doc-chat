# AI Doctor - Health Assistant Platform

A full-stack health assistant application with AI-powered health insights, symptom analysis, and doctor recommendations.

## Tech Stack

- **Frontend**: React 19 + TypeScript + Vite
- **Backend**: Django 5.2 + PostgreSQL
- **Authentication**: Supabase Auth
- **AI**: Google Gemini API
- **Maps**: Google Maps API

---

## 🚀 Deploy to Railway

### Prerequisites

1. A [Railway](https://railway.app) account
2. A [Supabase](https://supabase.com) project (for authentication)
3. A [Google Cloud](https://console.cloud.google.com) account (for Gemini AI and Maps API)

---

### Step 1: Fork/Clone the Repository

```bash
git clone <your-repo-url>
cd ai-doctor
```

---

### Step 2: Set Up Supabase

1. Go to [Supabase](https://supabase.com) and create a new project
2. Go to **Settings > API** and copy:
   - Project URL (`SUPABASE_URL`)
   - Anon/Public key (`SUPABASE_ANON_KEY`)
3. Go to **Authentication > Providers** and enable **Google** provider:
   - Add your Google OAuth credentials
   - Set redirect URL to: `https://your-frontend.railway.app`

---

### Step 3: Get Google API Keys

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable these APIs:
   - **Generative Language API** (for Gemini)
   - **Maps JavaScript API**
   - **Places API**
4. Go to **Credentials** and create an API key
5. Restrict the key to the APIs above

---

### Step 4: Deploy Backend to Railway

1. Go to [Railway](https://railway.app) and click **New Project**

2. Select **Deploy from GitHub repo** and choose your repository

3. Railway will detect the project. Click on the service and go to **Settings**:
   - Set **Root Directory** to: `backend`
   - Set **Start Command** to: `gunicorn config.wsgi --bind 0.0.0.0:$PORT`

4. Add a **PostgreSQL** database:
   - Click **New** > **Database** > **PostgreSQL**
   - Railway will automatically set `DATABASE_URL`

5. Go to **Variables** tab and add these environment variables:

```env
# Django
DJANGO_SECRET_KEY=<generate-a-secure-random-string>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=<your-backend>.railway.app

# Database (Railway auto-provides these, but you can also use individual vars)
POSTGRES_DB=${{Postgres.PGDATABASE}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}

# CORS (add your frontend URL after deploying it)
CORS_ALLOWED_ORIGINS=https://<your-frontend>.railway.app
CSRF_TRUSTED_ORIGINS=https://<your-frontend>.railway.app

# Supabase
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_ANON_KEY=<your-supabase-anon-key>

# Google APIs
GEMINI_API_KEY=<your-gemini-api-key>
GOOGLE_MAPS_API_KEY=<your-google-maps-api-key>
```

6. Click **Deploy** and wait for the build to complete

7. Once deployed, run migrations:
   - Go to **Settings** > **Deploy** section
   - The `release` command in Procfile will auto-run migrations

8. Note your backend URL (e.g., `https://ai-doctor-backend.railway.app`)

---

### Step 5: Deploy Frontend to Railway

1. In the same Railway project, click **New** > **GitHub Repo**

2. Select the same repository

3. Go to **Settings**:
   - Set **Root Directory** to: `frontend`
   - Set **Build Command** to: `npm install && npm run build`
   - Set **Start Command** to: `npx serve dist -s -l $PORT`

4. Go to **Variables** tab and add:

```env
VITE_API_URL=https://<your-backend>.railway.app
VITE_SUPABASE_URL=https://<your-project>.supabase.co
VITE_SUPABASE_ANON_KEY=<your-supabase-anon-key>
VITE_GOOGLE_MAPS_API_KEY=<your-google-maps-api-key>
```

5. Click **Deploy**

6. Note your frontend URL and update:
   - Backend's `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`
   - Supabase's redirect URLs in Authentication settings

---

### Step 6: Update CORS Settings

After both services are deployed, update the backend's environment variables:

```env
CORS_ALLOWED_ORIGINS=https://<your-frontend>.railway.app
CSRF_TRUSTED_ORIGINS=https://<your-frontend>.railway.app
DJANGO_ALLOWED_HOSTS=<your-backend>.railway.app
```

Redeploy the backend for changes to take effect.

---

### Step 7: Configure Supabase Redirect URLs

1. Go to Supabase Dashboard > Authentication > URL Configuration
2. Add your frontend URL to:
   - **Site URL**: `https://<your-frontend>.railway.app`
   - **Redirect URLs**: `https://<your-frontend>.railway.app`

---

## 🔧 Local Development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env file and configure
cp .env.example .env
# Edit .env with your values

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy env file and configure
cp .env.example .env
# Edit .env with your values

# Start dev server
npm run dev
```

---

## 📁 Project Structure

```
├── backend/
│   ├── api/                 # Django app with views, models, services
│   ├── config/              # Django settings and URLs
│   ├── manage.py
│   ├── requirements.txt
│   ├── Procfile            # Railway/Heroku process file
│   └── railway.json        # Railway configuration
│
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── lib/            # Utilities and helpers
│   │   └── App.tsx         # Main app component
│   ├── package.json
│   └── railway.json        # Railway configuration
│
└── README.md
```

---

## 🔑 Environment Variables Reference

### Backend

| Variable | Description | Required |
|----------|-------------|----------|
| `DJANGO_SECRET_KEY` | Django secret key | Yes |
| `DJANGO_DEBUG` | Debug mode (false in production) | Yes |
| `DJANGO_ALLOWED_HOSTS` | Allowed hostnames | Yes |
| `POSTGRES_*` | Database credentials | Yes |
| `CORS_ALLOWED_ORIGINS` | Frontend URLs for CORS | Yes |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins for CSRF | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `GOOGLE_MAPS_API_KEY` | Google Maps API key | Optional |
| `TWILIO_*` | Twilio credentials for calling | Optional |

### Frontend

| Variable | Description | Required |
|----------|-------------|----------|
| `VITE_API_URL` | Backend API URL | Yes |
| `VITE_SUPABASE_URL` | Supabase project URL | Yes |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps API key | Optional |

---

## 🛠 Troubleshooting

### Build Fails on Railway

- Check that `Root Directory` is set correctly (`backend` or `frontend`)
- Verify all required environment variables are set
- Check build logs for specific errors

### CORS Errors

- Ensure `CORS_ALLOWED_ORIGINS` includes your frontend URL with `https://`
- Make sure there are no trailing slashes in the URLs
- Redeploy backend after changing CORS settings

### Database Connection Issues

- Verify PostgreSQL addon is attached to your backend service
- Check that `POSTGRES_*` variables reference the correct Railway variables
- Try using `DATABASE_URL` format instead of individual variables

### Authentication Not Working

- Verify Supabase URL and anon key are correct in both frontend and backend
- Check Supabase redirect URLs include your frontend domain
- Ensure Google OAuth is properly configured in Supabase

---

## 📝 Generate Django Secret Key

Run this Python command to generate a secure secret key:

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Or use an online generator like [Djecrety](https://djecrety.ir/)

---

## 📄 License

MIT License
