# Nginx Reverse Proxy for FastAPI + LangChain

This document explains how to expose the FastAPI service securely using **Nginx** as a reverse proxy, with optional HTTPS support.

---

## Architecture Overview


Internet
↓
Nginx (80 / 443)
↓
Gunicorn + Uvicorn workers
↓
FastAPI application (127.0.0.1:8000)


Nginx handles:
- Public endpoint exposure
- HTTPS termination
- Request forwarding
- Basic security headers

---

## 1. Install Nginx

```bash
sudo apt update
sudo apt install -y nginx

Enable and start Nginx:

sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
2. Firewall Configuration (if enabled)

If UFW is enabled:

sudo ufw allow 'Nginx Full'
sudo ufw status
3. Verify FastAPI is Running Internally

Your FastAPI service must be running on localhost:

curl http://127.0.0.1:8000/health

Expected response:

{
  "status": "ok"
}

If this fails, fix the FastAPI service before proceeding.

4. Create Nginx Site Configuration

Create a new site config:

sudo nano /etc/nginx/sites-available/palma-ai
HTTP Configuration (Port 80)
server {
    listen 80;
    server_name example.com api.example.com;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}

Replace:

example.com with your domain

Add/remove subdomains as needed

5. Enable the Site
sudo ln -s /etc/nginx/sites-available/palma-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
6. Test Public Access
curl http://example.com/health

Expected response:

{
  "status": "ok"
}

At this point, your API is publicly reachable over HTTP.

7. Enable HTTPS (Recommended – Let’s Encrypt)

Install Certbot:

sudo apt install -y certbot python3-certbot-nginx

Run Certbot:

sudo certbot --nginx -d example.com -d api.example.com

Certbot will:

Obtain SSL certificates

Modify Nginx config automatically

Enable HTTPS redirect

8. Resulting HTTPS Configuration (Reference)

After Certbot, your config will resemble:

server {
    listen 443 ssl;
    server_name example.com api.example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        proxy_read_timeout 300;
    }
}

HTTP traffic will automatically redirect to HTTPS.

9. Recommended Security Headers (Optional)

Add inside the server block:

add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
10. Common Pitfalls

Do NOT expose Gunicorn directly on public IP

Keep FastAPI bound to 127.0.0.1

Increase timeouts for LLM workloads

Ensure client_max_body_size supports large payloads