# Deployment Guide

This guide covers deploying the BigData Credit API for evaluators to test.

## Option 1: Deploy to Cloud Platform (Recommended)

### Railway (Easiest)

1. **Create Railway account** at https://railway.app
2. **New Project** → **Deploy from GitHub repo**
3. **Add PostgreSQL service** (Railway will auto-create)
4. **Add environment variables:**
   - `POSTGRES_URL` (auto-set by Railway)
   - `CLICKHOUSE_HOST` (your ClickHouse Cloud instance)
   - `CLICKHOUSE_PASSWORD` (your ClickHouse password)
   - `ADMIN_API_KEY` (generate a secure key)
   - `CLICKHOUSE_USER=default`
   - `CLICKHOUSE_PORT=8443`
   - `CLICKHOUSE_SECURE=true`
   - `CREDITS_PER_100_RECORDS=1`
   - `MAX_LIMIT=1000`
5. **Set start command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
6. **Deploy**

### Render

1. **Create account** at https://render.com
2. **New Web Service** → Connect GitHub repo
3. **Settings:**
   - Build Command: `pip install -r api/requirements.txt`
   - Start Command: `cd api && uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Add PostgreSQL database** (Render will auto-create)
5. **Add environment variables** (same as Railway above)
6. **Deploy**

### Heroku

1. **Install Heroku CLI**
2. **Login:** `heroku login`
3. **Create app:** `heroku create your-app-name`
4. **Add PostgreSQL:** `heroku addons:create heroku-postgresql:mini`
5. **Set environment variables:**
   ```bash
   heroku config:set CLICKHOUSE_HOST=your-host
   heroku config:set CLICKHOUSE_PASSWORD=your-password
   heroku config:set ADMIN_API_KEY=your-admin-key
   # ... etc
   ```
6. **Deploy:** `git push heroku main`

## Option 2: Local Deployment for Testing

### Prerequisites
- Docker and Docker Compose
- Python 3.10+

### Steps

1. **Clone the project:**
   ```bash
   git clone <repo-url>
   cd Big-Data-Project
   ```

2. **Setup environment:**
   ```bash
   cp api/.env.example api/.env
   # Edit api/.env with your credentials
   ```

3. **Start databases with Docker:**
   ```bash
   cd deployment
   docker-compose up -d
   ```

4. **Setup PostgreSQL:**
   ```bash
   psql -h localhost -U admin -d creditsystem -f ../api/db/migrations.sql
   # Password: admin123 (or your POSTGRES_PASSWORD)
   ```

5. **Install dependencies:**
   ```bash
   cd ..
   pip install -r api/requirements.txt
   ```

6. **Run API:**
   ```bash
   cd api
   uvicorn main:app --reload
   ```

## Database Setup

After deployment, run the migration:

```bash
# For cloud platforms, use their database console or CLI
psql $POSTGRES_URL -f api/db/migrations.sql

# Or manually:
psql -h host -U user -d database -f api/db/migrations.sql
```

## ClickHouse Setup

Ensure your ClickHouse instance has the `master_records` table. The loader script will create it automatically, or create manually:

```sql
CREATE TABLE IF NOT EXISTS master_records (
    canonical_key String,
    name String,
    first_name String,
    last_name String,
    email String,
    phone String,
    dob String,
    ingest_timestamp DateTime
)
ENGINE = MergeTree()
ORDER BY canonical_key;
```

## Testing the Deployment

1. **Health check:**
   ```bash
   curl https://your-app-url.railway.app/health
   ```

2. **Signup:**
   ```bash
   curl -X POST "https://your-app-url.railway.app/auth/signup" \
     -H "Content-Type: application/json" \
     -d '{"name": "Test User", "email": "test@example.com"}'
   ```

3. **Query (use API key from signup):**
   ```bash
   curl "https://your-app-url.railway.app/query?limit=10" \
     -H "x-api-key: your-api-key"
   ```

## Production Considerations

- Use HTTPS (most platforms provide this automatically)
- Set strong `ADMIN_API_KEY`
- Use environment variables for all secrets
- Enable database backups
- Monitor usage logs
- Set up rate limiting if needed

