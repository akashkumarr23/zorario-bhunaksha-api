# Bihar Bhunaksha Scraper Backend (Render Free Tier)

Zero-cost FastAPI backend that scrapes **bhunaksha.bihar.gov.in** for the Zorario Partner App.
100% Free forever on Render.com — No credit card required.

---

## 🚀 How to Deploy on Render (Step-by-Step)

### Option A: Automatic via Blueprint (Easiest)
1. Push your repository to GitHub.
2. Go to [dashboard.render.com](https://dashboard.render.com).
3. Click **New +** → **Blueprint**.
4. Select your GitHub repository.
5. Render reads `render.yaml` automatically and configures:
   - **Name:** `zorario-bhunaksha`
   - **Plan:** Free ($0)
   - **Root directory:** `backend/bhunaksha_scraper`
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Click **Apply**. Done!

---

### Option B: Manual Web Service Setup
1. Go to [dashboard.render.com](https://dashboard.render.com) and click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Fill in these exact settings:
   - **Name:** `zorario-bhunaksha`
   - **Region:** `Singapore` (closest to India for low latency)
   - **Root Directory:** `backend/bhunaksha_scraper`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Select **Free** ($0 / month)
4. Under **Environment Variables**, add:
   - `BHUNAKSHA_BASE` = `https://bhunaksha.bihar.gov.in/bhunaksha`
   - `PYTHON_VERSION` = `3.11.8`
5. Click **Create Web Service**.

---

## 🔗 After Deployment

Render gives you a free HTTPS URL like:
`https://zorario-bhunaksha.onrender.com`

1. Test it in your browser: `https://zorario-bhunaksha.onrender.com/docs`
2. Update your Flutter app:
   In `lib/services/land_parcel_api_service.dart`, set:
   ```dart
   static const String _backendUrl =
       String.fromEnvironment('BHUNAKSHA_URL', defaultValue: 'https://zorario-bhunaksha.onrender.com');
   ```

---

## ⚡ Note on Render Free Tier Sleeping
- If unused for 15 minutes, Render spins down to conserve resources.
- When an agent or user opens the search for the first time, Render wakes up in ~15-20 seconds.
- The Flutter app has built-in graceful fallback data, so the user never sees a broken screen even during cold starts.
