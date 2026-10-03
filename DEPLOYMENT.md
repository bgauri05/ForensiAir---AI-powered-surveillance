# ForensiAIR Deployment Handbook

This guide provides end-to-end instructions for deploying the **ForensiAIR** surveillance platform (FastAPI Backend + React Frontend + SQLite DB / ML Engine).

---

## 🚀 Quick Deployment Options

| Deployment Method | Target Environment | Difficulty | Recommended For |
| :--- | :--- | :--- | :--- |
| **Docker Compose** | VPS / EC2 / Local Server | 🟢 Easy | Production & On-Premise |
| **Cloud PaaS (Render/Vercel)** | Render + Vercel / Netlify | 🟢 Easy | Cloud Hosting / Demos |
| **Direct Host (Systemd + Nginx)** | Linux Server (Ubuntu/Debian) | 🟡 Medium | Bare-metal Production |

---

## Option 1: Docker Compose (Recommended)

Docker Compose builds and orchestrates both the FastAPI Backend and the React Frontend with Nginx as a reverse proxy.

### Prerequisites
- Docker (v20.10+)
- Docker Compose (v2.0+)

### Step-by-step Execution

1. **Clone the repository and navigate to root**:
   ```bash
   git clone <your-repository-url>
   cd ForensiAir---AI-powered-surveillance
   ```

2. **Configure Production Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   APP_ENV=production
   SECRET_KEY=your_super_secret_jwt_key_change_me
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your_secure_admin_password
   INSPECTOR_USERNAME=inspector
   INSPECTOR_PASSWORD=your_secure_inspector_password
   ```

3. **Start the Application**:
   ```bash
   docker compose up --build -d
   ```

4. **Access the Application**:
   - **Frontend UI**: `http://localhost` (or `http://your-server-ip`)
   - **Backend API Docs**: `http://localhost:8000/docs`

5. **Stop & Management Commands**:
   ```bash
   # View logs
   docker compose logs -f

   # Stop services
   docker compose down
   ```

---

## Option 2: Cloud PaaS Deployment (Render + Vercel / Render Static)

### Deploying Backend on Render

1. Connect your GitHub repository to [Render.com](https://render.com).
2. Create a new **Web Service**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**:
     - `APP_ENV`: `production`
     - `SECRET_KEY`: `<random-secret-key>`
     - `ADMIN_USERNAME`: `<your-admin-user>`
     - `ADMIN_PASSWORD`: `<your-admin-pass>`
     - `INSPECTOR_USERNAME`: `<your-inspector-user>`
     - `INSPECTOR_PASSWORD`: `<your-inspector-pass>`

### Deploying Frontend on Vercel or Netlify

1. Connect the `frontend/` directory to Vercel/Netlify.
2. Set Build Settings:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add Environment Variable:
   - `VITE_API_BASE_URL`: `https://your-backend-name.onrender.com`

---

## Option 3: Direct Host Deployment (Linux / Ubuntu Server)

### Step 1: Backend Setup
1. Install Python 3.11 and create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Seed Database (if database is not present):
   ```bash
   python database/seed_db.py
   ```

3. Run FastAPI using Uvicorn or Gunicorn:
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```

### Step 2: Frontend Build
1. Build React application:
   ```bash
   cd frontend
   npm install
   npm run build
   ```

2. Copy static build output (`frontend/dist`) to your Nginx document root (`/var/www/forensiair`).

### Step 3: Nginx Reverse Proxy Configuration
Add Nginx configuration (`/etc/nginx/sites-available/forensiair`):
```nginx
server {
    listen 80;
    server_name forensiair.example.com;

    location / {
        root /var/www/forensiair;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable site & restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/forensiair /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## 🔒 Security & Maintenance Checklist

- [ ] Change default JWT `SECRET_KEY` in production.
- [ ] Set `APP_ENV=production` to enforce strict credential validation.
- [ ] Setup SSL/TLS using Let's Encrypt (`certbot --nginx`).
- [ ] Schedule regular backups of `forensiair.db`.
- [ ] If ML telemetry data updates, rerun `python database/seed_db.py` to refresh the SQLite database.
