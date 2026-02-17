# Palma AI Client Deployment Guide (Production Ready)

This guide covers deploying the React + Vite client for the Palma Help Agent and integrating it with the FastAPI backend you’ve already deployed.

---

## Overview

- Stack: React 19 + Vite 7
- Build output: `dist/` (static files)
- API usage: `src/api/client.ts` reads `VITE_API_BASE_URL` and calls `/chat`
- Recommended hosting: Nginx serving static client, proxying `/api` to FastAPI (Gunicorn/Uvicorn)

This architecture avoids CORS and works both on a single server and cloud deployments.

---

## Prerequisites

- Node.js: 20.19+ or 22.12+ (Vite requirement)
- NPM / PNPM / Yarn
- Access to Linux server running FastAPI
- Domain DNS pointing to server

> The client throws an error if `VITE_API_BASE_URL` is missing.

---

## Client Configuration

The client reads environment variables **at build time**.

### Required variables

| Variable | Description |
|--------|------|
| VITE_API_BASE_URL | API base URL |
| VITE_USE_CHAT_MOCK | Enables local mock mode |

---

### Production

Create `.env.production`

```env
VITE_API_BASE_URL=/api
VITE_USE_CHAT_MOCK=false

VITE_API_BASE_URL=http://localhost:8000
VITE_USE_CHAT_MOCK=true
```

Build the Client

From project root:
```bash
npm install
npm run build
npm run preview
```

Output directory:
```bash
dist/
Deploy with Nginx (Recommended)
```

This setup:

Serves SPA

Proxies API

Supports long LLM responses

Works with streaming agents

Copy build to server
```bash
Compress-Archive -Path .\dist\* -DestinationPath .\palma-client.zip
scp .\palma-client.zip ubuntu@<server>:/tmp/
```

On the server:
```bash
sudo mkdir -p /var/www/palma
sudo rm -rf /var/www/palma/*
sudo unzip -o /tmp/palma-client.zip -d /var/www/palma
sudo chown -R www-data:www-data /var/www/palma
Nginx Configuration
```

Create:
```bash
/etc/nginx/sites-available/palma
```
IMPORTANT

This configuration correctly strips /api prefix before forwarding to FastAPI.
```bash
server {
    listen 80;
    server_name your.domain;

    root /var/www/palma;
    index index.html;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;

        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Required for streaming / long AI responses
        proxy_read_timeout 300;
        proxy_send_timeout 300;
        proxy_buffering off;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff2?)$ {
        try_files $uri /index.html;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```
Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/palma /etc/nginx/sites-enabled/palma
sudo nginx -t
sudo systemctl reload nginx
HTTPS (Lets Encrypt)
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain
```
Verification

Open:
```bash
https://your.domain
```

Test API directly:
```bash
curl http://127.0.0.1:8000/health
```
Expected:
```bash
{ "status": "ok" }
```
Browser DevTools should show successful request:
```bash
/api/chat → 200
```