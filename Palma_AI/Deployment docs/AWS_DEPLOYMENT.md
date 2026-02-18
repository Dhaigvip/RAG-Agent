Client (Browser / API Client)
        ↓
Nginx (Reverse Proxy, HTTPS)
        ↓
Gunicorn (Process Manager)
        ↓
Uvicorn Workers (ASGI)
        ↓
FastAPI App (LangChain Agents)
        ↓
External APIs (OpenAI, Pinecone, etc.)


AWS EC2 (Ubuntu Linux)
    ├── systemd (process supervisor)
    ├── uv-managed Python environment
    ├── Gunicorn + Uvicorn
    └── Nginx


    3. Server Setup

SSH into the instance:

ssh -i yourkey.pem ubuntu@YOUR_PUBLIC_IP

Update packages:

sudo apt update
sudo apt install -y curl ca-certificates build-essential cmake nginx
4. Install uv
curl -Ls https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv --version

uv will:

Automatically create and manage the virtual environment

Use uv.lock for deterministic installs

5. Project Structure

Recommended structure:

/home/ubuntu/app
│
├── server.py
├── ingestion.py
├── query.py
├── pyproject.toml
├── uv.lock
├── .env
└── logs/

Important:

server.py must expose:

app = FastAPI()

uv.lock must be committed

.env must NOT be committed

6. Install Dependencies (Production Mode)

Inside the app directory:

cd /home/ubuntu/app
uv sync --frozen --no-dev

Explanation:

--frozen ensures lockfile is honored

--no-dev excludes dev dependencies

7. Environment Variables

Create .env:

nano /home/ubuntu/app/.env
chmod 600 /home/ubuntu/app/.env

Example:

UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000

OPENAI_API_KEY=xxxx
PINECONE_API_KEY=xxxx
PINECONE_ENV=xxxx

Production recommendation:

Use AWS Secrets Manager instead of a local .env file for real deployments.

8. Production Server Command

Correct production command:

uv run gunicorn server:app \
  -k uvicorn.workers.UvicornWorker \
  -w 2 \
  -b 127.0.0.1:8000 \
  --timeout 180 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile -

Explanation of key parameters:

Parameter	Purpose
-w 2	Two worker processes
-b 127.0.0.1:8000	Bind locally (security)
--timeout 180	Allow long agent runs
--max-requests	Prevent memory leaks

Avoid too many workers for LLM workloads due to memory and API limits.

9. systemd Service

Create service file:

sudo nano /etc/systemd/system/palma-ai.service

Service definition:

[Unit]
Description=Palma Help Agent API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/app
EnvironmentFile=/home/ubuntu/app/.env

ExecStart=/home/ubuntu/.local/bin/uv run gunicorn server:app \
  -k uvicorn.workers.UvicornWorker \
  -w 2 \
  -b 127.0.0.1:8000 \
  --timeout 180 \
  --graceful-timeout 30 \
  --keep-alive 5

Restart=always
RestartSec=3
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target

Enable service:

sudo systemctl daemon-reload
sudo systemctl enable palma-ai
sudo systemctl start palma-ai
sudo systemctl status palma-ai

View logs:

journalctl -u palma-ai -f
10. Nginx Reverse Proxy

Create configuration:

sudo nano /etc/nginx/sites-available/palma-ai

Basic config:

server {
  listen 80;
  server_name yourdomain.com;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 180s;
  }
}

Enable:

sudo ln -s /etc/nginx/sites-available/palma-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
11. Enable HTTPS (Let’s Encrypt)

Install certbot:

sudo apt install -y certbot python3-certbot-nginx

Generate certificate:

sudo certbot --nginx -d yourdomain.com

Certbot will:

Configure SSL automatically

Install auto-renewal

12. Verification

Test locally:

curl http://127.0.0.1:8000/health

Test publicly:

curl https://yourdomain.com/health

Expected response:

{ "status": "ok" }