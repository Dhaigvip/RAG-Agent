# Palma AI Client Deployment Guide

This guide covers deploying the React + Vite client for the Palma Help Agent and integrating it with the FastAPI backend you’ve already deployed.

---

## Overview

- Stack: React 19 + Vite 7
- Build output: `dist/` (static files)
- API usage: `src/api/client.ts` reads `VITE_API_BASE_URL` and calls `/chat`
- Recommended hosting: Nginx serving static client, proxying `/api` to FastAPI (Gunicorn/Uvicorn on `127.0.0.1:8000`)

---

## Prerequisites

- Node.js: 20.19+ or 22.12+ (Vite requirement)
- NPM or PNPM/Yarn
- Access to your Linux server running the FastAPI service
- Domain/DNS pointed to the server (for HTTPS via Let’s Encrypt)

> Note: The client throws an error if `VITE_API_BASE_URL` is missing.

---

## Client Configuration

The client reads the following environment variables at build time:

- `VITE_API_BASE_URL`: Base URL for the API (e.g., `/api` when behind Nginx, or `https://api.example.com` when hosted separately)
- `VITE_USE_CHAT_MOCK`: `true` to use the local mock response during development, `false` for production

### Production env

Create a `.env.production` file (already added):

```env
VITE_API_BASE_URL=/api
VITE_USE_CHAT_MOCK=false
```

### Development env (optional)

Create a `.env.development` file if desired:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_CHAT_MOCK=true
```

> With `VITE_USE_CHAT_MOCK=true`, the client returns a mocked answer from `src/api/mockResponse.ts` and does not call the API.

---

## Build the Client

From the project root:

```powershell
npm install
npm run build
npm run preview
```

- Output is generated in `dist/`
- `npm run preview` serves the built files locally for a quick check

---

## Deploy with Nginx (Recommended)

This setup serves the client and proxies `/api` to your FastAPI service, avoiding CORS and simplifying configuration.

### Copy build to server

```powershell
# On Windows
Compress-Archive -Path .\dist\* -DestinationPath .\palma-client.zip
scp .\palma-client.zip ubuntu@<server>:/tmp/
```

```bash
# On the server (SSH)
sudo mkdir -p /var/www/palma
sudo rm -rf /var/www/palma/*
sudo unzip -o /tmp/palma-client.zip -d /var/www/palma
sudo chown -R www-data:www-data /var/www/palma
```

### Nginx site config

Create `/etc/nginx/sites-available/palma`:

```nginx
server {
    listen 80;
    server_name your.domain;

    root /var/www/palma;
    index index.html;

    # SPA: static files and fallback to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API to FastAPI (Gunicorn/Uvicorn on 127.0.0.1:8000)
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Optional: cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico)$ {
        try_files $uri /index.html;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }
}
```

Enable and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/palma /etc/nginx/sites-enabled/palma
sudo nginx -t
sudo systemctl reload nginx
```

### HTTPS (Let’s Encrypt)

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain
```

---

## Verification

- Open `https://your.domain/` in a browser and ask a question
- Check the API health on the server:

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{ "status": "ok" }
```

- In the browser dev tools, confirm that requests to `/api/chat` succeed

---

## Alternative Hosting Options

If you prefer a static hosting provider:

- **Vercel / Netlify / Azure Static Web Apps**
  - Set `VITE_API_BASE_URL` to your public API URL in environment settings
  - Use platform rewrites/proxies to route `/api` if the API is private
- **GitHub Pages**
  - Public API required; enable CORS in FastAPI

---

## Troubleshooting

- **Node version**: Vite requires Node 20.19+ or 22.12+. Upgrade if builds complain.
- **Missing env**: If `VITE_API_BASE_URL` is empty, the client throws an error in `src/api/client.ts`.
- **CORS**: If client and API are on different domains, enable CORS in FastAPI.
- **Mixed content**: Use HTTPS on both client and API to avoid blocked requests.
- **Caching**: After deployments, clear CDN/browser cache if assets look stale.
- **Mocking**: Toggle `VITE_USE_CHAT_MOCK` if you need offline/dev testing.

---

## Code References

- API client: `src/api/client.ts`
- Chat component: `src/components/Chat.tsx`
- Production env: `.env.production`
- Build output: `dist/`

---

## Quick Summary

1. Set `VITE_API_BASE_URL=/api` (production)
2. `npm install && npm run build`
3. Upload `dist/` to `/var/www/palma`
4. Configure Nginx to serve SPA and proxy `/api` to FastAPI
5. Add HTTPS, verify UI and `/health`
