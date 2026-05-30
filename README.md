<div align="center">

# 🛡️ AI Infrastructure Monitoring & Intelligence Dashboard

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](#-15-license)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-22c55e)](#)

**Monitor, analyze, and act on your entire Linux server fleet from one beautiful, AI-powered dashboard.**

</div>

---

The **AI Infrastructure Monitoring & Intelligence Dashboard** is a secure, web-based platform that lets an authorized administrator monitor many Linux servers from a single interface. An operator registers a server by entering its IP address and SSH credentials (password or private key); the system then connects over SSH using Paramiko and collects live infrastructure data — CPU, RAM, disk, uptime, running processes, open ports, network statistics and logs — **without installing any agent on the monitored server**. Collected data is sanitized, encrypted at rest, and sent to **Cerebras AI**, which produces a plain-English health summary, a 1–10 risk score, key findings, and recommended actions. Reports are generated automatically every 24 hours and on demand via a refresh button. The platform also includes a guarded **action-execution engine** (whitelisted commands, dual confirmation, time locks), a **10-point vulnerability scanner**, an **emergency kill switch** with forensic incident reporting, professional HTML email notifications, and full audit logging — all behind JWT authentication, role-based access control, and AES-256-GCM credential encryption.

---

## 📑 Table of Contents

1. [Capabilities & Features](#-1-capabilities--features)
2. [System Architecture](#-2-system-architecture)
3. [Tech Stack](#-3-tech-stack)
4. [Project Structure](#-4-project-structure)
5. [Prerequisites](#-5-prerequisites)
6. [Environment Variables](#-6-environment-variables)
7. [Installation & Deployment](#-7-installation--deployment)
8. [Systemd Services](#-8-systemd-services)
9. [Security Architecture](#-9-security-architecture)
10. [API Documentation](#-10-api-documentation)
11. [Monitored Server Requirements](#-11-monitored-server-requirements)
12. [Backup & Recovery](#-12-backup--recovery)
13. [Troubleshooting](#-13-troubleshooting)
14. [Roadmap](#-14-roadmap)
15. [License](#-15-license)
16. [Author](#-16-author)

---

## ✨ 1. Capabilities & Features

### 🖥️ Server Monitoring
- **Full metric collection over SSH** — CPU usage, RAM usage, disk usage (per mount), system uptime, top running processes, listening (open) ports, network statistics, load average, kernel version and OS information.
- **Log collection** — reads syslog, authentication logs, and nginx/PostgreSQL/application logs, parsed into timestamp, level, source, and message.
- **Monitor 10+ servers simultaneously** from one central dashboard.
- **Real-time metrics** with a **30-second silent auto-refresh** of the dashboard grid.
- **24-hour historical charts** rendered as smooth **area charts with gradient fills** (Recharts).
- **Color-coded warning thresholds** at **60% (warning)** and **80% (critical)** on CPU and RAM charts and gauges.
- **Accurate CPU reading** straight from `/proc/stat` (locale-independent, one-decimal precision).
- **Zero agents** — nothing is installed on the monitored servers.

### 🤖 AI Intelligence
- **Cerebras AI-powered** infrastructure analysis (model & key configured via `.env`).
- **Plain-English health summaries** of each server's condition.
- **Risk scoring from 1 to 10** with green/yellow/red color coding.
- **Key findings, security observations, and performance observations** parsed into structured sections.
- **Recommended actions** with **one-click execution** mapped to whitelisted commands.
- **Automatic daily reports** every 24 hours (configurable interval).
- **Manual refresh** for instant analysis at any time.
- **Robust response parsing** — strips markdown fences, recovers single-quoted/Python-dict JSON, and never stores or displays raw JSON; falls back to a clean structured error.

### 🔒 Security Features
- **AES-256-GCM encryption** for all SSH passwords and private keys at rest (master key in `.env`).
- **JWT authentication** with **15-minute** access tokens and **refresh-token rotation** (reuse detection).
- **Argon2id password hashing** (configurable time/memory/parallelism cost).
- **Rate limiting** (SlowAPI, Redis-backed) on authentication and API endpoints.
- **Role-Based Access Control** with **Super Admin, Admin, and Viewer** roles.
- **API-level RBAC enforcement** — restricted endpoints return **403** even when called directly.
- **Session timeout** with automatic logout after inactivity and a **2-minute warning modal**.
- **Intrusion detection** — email alert + temporary IP block after a configurable failed-login threshold.
- **Content-Security-Policy** and full security headers on all pages.
- **SSH key-only mode** per server (disables password auth for sensitive hosts).
- **Connection IP whitelisting** before any SSH session.
- **Full audit logging** of every login, logout, registration, action, scan, and system event.
- **Credential masking** — SSH secrets are never returned in API responses; reveal requires password re-verification (Super Admin only).

### 🚨 Emergency Response
- **Emergency Kill Switch** (Super Admin only) — immediately **revokes a server's stored SSH credentials** (password and key set to `NULL`), **cancels all pending/approved actions**, **terminates tracked SSH connections**, and marks the server offline.
- **Password re-verification required** to arm the kill switch.
- **Forensic incident report email** delivered instantly to the Super Admin, including a threat-level banner, executive summary, intruder-details section, indicators of compromise, immediate-action checklist, and a "what was wiped" confirmation — rendered as a professional HTML template.
- **Every incident is recorded in the audit log** for later review via the Audit Log viewer.

### 🛡️ Vulnerability Scanner
- **10-point security audit** run directly on a monitored server over SSH:
  1. Open ports audit · 2. Failed login attempts · 3. Authorized SSH keys · 4. World-writable files in `/etc` · 5. SUID files · 6. Processes running as root · 7. Unattended-upgrades check · 8. UFW firewall status · 9. SSH `PasswordAuthentication` config · 10. Critical disk usage.
- **Overall security score (0–100)** with pass / warning / critical counts.
- **"Fix It" buttons** that map a finding to a whitelisted remediation command and run it through the full action flow.
- **Scan history tracking** persisted per server.

### ⚡ Action Execution Engine
- **Server-side command whitelist** of **35 hardcoded commands** organized by risk: **20 low / 8 medium / 7 high**. User-supplied command strings are never executed.
- **Dry-run mode** to preview real command output before committing.
- **Multi-step confirmation** flow with **dashboard-password re-entry**.
- **Dual-admin confirmation** required for high-risk commands (a second Admin/Super Admin must approve).
- **60-second time-locked window** for high-risk actions during which the action can be cancelled.
- **Full command output captured** and stored in the audit log.
- **Immediate email alert** to the Super Admin on every execution.
- The command string is **re-resolved from the whitelist at execution time** as defense-in-depth.

### 📊 Dashboard & Visualization
- **Dark-themed, fully responsive** dashboard.
- **Server status grid** with color-coded online / offline / warning indicators and mini progress bars.
- **CPU, RAM, and disk gauge charts** with real-time values.
- **24-hour gradient area charts** per server for CPU, RAM, and disk.
- **Running-processes table** with search and sort, and an **open-ports table**.
- **Recent-logs panel** with color-coded severity.
- **Security-alerts panel** with live updates (auto-refresh).
- **Audit-log viewer** with full filtering and **CSV export**.

### 📧 Email Notification System
- **Professional, Gmail-friendly HTML templates** (inline CSS, 600px responsive) for every notification:
  - **Daily AI report** — risk circle, summary, findings, recommendations, metric snapshot.
  - **Intrusion alert** — attacker IP, attempt count, plain-English explanation, action checklist.
  - **New server registered** — server details + "connection verified" badge.
  - **Action executed** — risk-colored header, command code block, scrollable output, confirmer.
  - **Emergency forensic incident report** — full red incident layout with evidence sections.
- A `test_emails.py` script sends one sample of each type for visual verification.

### 🗄️ Data Management
- **PostgreSQL** with **row-level security** enabled on every table.
- **Encrypted storage** for sensitive columns (SSH credentials, encrypted process/port JSON, encrypted log lines, encrypted report snapshots).
- **Configurable retention policies** for metrics, logs, and AI reports.
- **Automated daily encrypted database backups** (`pg_dump` → gzip → AES-256-CBC).
- **Celery + Redis** task queue for background metric/log/AI processing.
- **APScheduler** for 24-hour report scheduling, daily retention cleanup, and 60-second pending-action expiry.

---

## 🏗️ 2. System Architecture

```text
                              ┌──────────────────────────┐
                              │       Browser / Client    │
                              │   (HTTPS, TLS 1.2 / 1.3)   │
                              └─────────────┬─────────────┘
                                            │ 443
                              ┌─────────────▼─────────────┐
                              │   Nginx Reverse Proxy + SSL │
                              │  (Let's Encrypt, HSTS, CSP) │
                              └──────┬───────────────┬─────┘
                          /api, /docs│               │ /  (everything else)
                                     │               │
                   ┌─────────────────▼───┐   ┌───────▼──────────────┐
                   │  FastAPI Backend     │   │  Next.js Frontend     │
                   │  127.0.0.1:8002      │   │  127.0.0.1:3001       │
                   │  (uvicorn, 4 workers)│   │  (next start)         │
                   └───┬───────┬─────┬────┘   └───────────────────────┘
                       │       │     │
        ┌──────────────┘       │     └───────────────┐
        │                      │                      │
┌───────▼────────┐   ┌─────────▼─────────┐   ┌────────▼────────┐
│  PostgreSQL 16  │   │  Redis 127.0.0.1   │   │  Celery Worker   │
│  localhost:5432 │   │  :6379 (broker +   │   │  (concurrency 4) │
│  (RLS, encrypted│   │  results + locks + │   │  metrics / logs /│
│   columns)      │   │  rate-limit store) │   │  AI / retention  │
└─────────────────┘   └───────────────────┘   └───────┬─────────┘
                                                       │
                  ┌────────────────────────────────────┼───────────────────┐
                  │                                     │                   │
        ┌─────────▼──────────┐              ┌───────────▼──────┐   ┌────────▼────────┐
        │  Monitored Servers  │              │   Cerebras AI API │   │   SMTP (Gmail)   │
        │  (SSH / Paramiko)   │              │   (HTTPS)         │   │   HTML emails    │
        │  CPU/RAM/disk/logs  │              │   risk analysis   │   │                  │
        └─────────────────────┘              └──────────────────┘   └─────────────────┘
```

APScheduler runs **inside the FastAPI process** (a Redis lock ensures only one of the 4 workers dispatches each scheduled job) and enqueues Celery tasks; the Celery worker performs the heavy SSH collection, AI analysis, and cleanup.

---

## 🧰 3. Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Frontend** | Next.js | 16.2.6 | React framework (App Router) |
| | React | 19.2.4 | UI library |
| | Tailwind CSS | 4.x | Utility-first styling / dark theme |
| | ShadCN-style UI | — | Hand-authored components (`components/ui`) |
| | Recharts | 3.8.1 | Charts (gauges, area charts) |
| | Axios | 1.16.1 | API client with auth interceptors |
| | TypeScript | 5.x | Type safety |
| **Backend** | FastAPI | 0.136.3 | Async API framework |
| | Python | 3.10+ (tested 3.12) | Language |
| | Uvicorn | 0.48.0 | ASGI server (4 workers) |
| | Pydantic | 2.13.4 | Validation / schemas |
| **Database** | PostgreSQL | 16 | Primary datastore (RLS) |
| | SQLAlchemy | 2.0.50 | Async ORM |
| | asyncpg | 0.31.0 | Async PostgreSQL driver |
| | Alembic | 1.18.4 | Schema migrations |
| **Queue / Scheduling** | Celery | 5.6.3 | Background task queue |
| | Redis | 6.4.0 (client) | Broker, results, locks, rate-limit store |
| | APScheduler | 3.11.2 | 24-hour reports, retention, expiry |
| **SSH** | Paramiko | 5.0.0 | SSH metric/log collection & execution |
| **AI** | Cerebras API | — | Infrastructure analysis |
| **Security** | argon2-cffi / passlib | 25.1.0 / 1.7.4 | Password hashing |
| | python-jose | 3.5.0 | JWT signing/verification |
| | cryptography | 48.0.0 | AES-256-GCM encryption |
| | SlowAPI | 0.1.9 | Rate limiting |
| | python-decouple | 3.8 | Secret/config management |
| **Email** | aiosmtplib | 5.1.0 | Async HTML email delivery |
| **Deployment** | Nginx | — | Reverse proxy + SSL termination |
| | systemd | — | Service management |
| | Certbot | — | Let's Encrypt SSL + auto-renew |
| | UFW | — | Host firewall |
| | Fail2ban | — | SSH / nginx brute-force protection |

---

## 📂 4. Project Structure

```text
AI_Infra_Monitoring/
├── README.md                       # This file
├── DEPLOYMENT_REPORT.md            # Generated production deployment report
├── .gitignore                      # Excludes .env, venv, node_modules, etc.
├── .env                            # Secrets & config (NEVER committed)
│
├── backend/                        # FastAPI application
│   ├── main.py                     # App entrypoint, routers, lifespan, /health
│   ├── config.py                   # Settings loaded from .env (python-decouple)
│   ├── database.py                 # Async SQLAlchemy engine + session factory
│   ├── celery_app.py               # Celery application + config
│   ├── requirements.txt            # Locked Python dependencies
│   ├── alembic.ini / alembic/      # Migration config + versioned migrations
│   │
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── user.py                 # Users (roles, force_password_change)
│   │   ├── server.py               # Registered servers (encrypted creds)
│   │   ├── metric.py               # Collected metrics (encrypted JSON cols)
│   │   ├── log.py                  # Collected logs (encrypted raw line)
│   │   ├── ai_report.py            # AI analysis reports
│   │   ├── audit_log.py            # Immutable audit trail
│   │   ├── refresh_token.py        # Hashed refresh tokens
│   │   ├── rate_limit.py           # Rate-limit tracking
│   │   ├── pending_action.py       # Action lifecycle records
│   │   ├── security_scan.py        # Vulnerability scan results
│   │   └── enums.py                # Roles, statuses, risk levels
│   │
│   ├── schemas/                    # Pydantic request/response models
│   │   ├── auth.py  server.py  metric.py  dashboard.py
│   │   ├── ai_report.py  action.py  security_scan.py
│   │
│   ├── routers/                    # API endpoints
│   │   ├── auth.py                 # Login, refresh, logout, change/verify password
│   │   ├── servers.py              # Register/manage servers, reveal, emergency-kill
│   │   ├── metrics.py              # Latest/history/refresh metrics
│   │   ├── ai_reports.py           # Latest/history/generate AI reports
│   │   ├── actions.py              # Whitelist, dry-run, confirm, execute, scan
│   │   └── dashboard.py            # Overview, status, alerts, audit logs, export
│   │
│   ├── services/                   # Business logic
│   │   ├── ssh_service.py          # SSH connect / test / client context manager
│   │   ├── metric_collector.py     # 12 read-only metric commands over SSH
│   │   ├── log_collector.py        # Log file collection & parsing
│   │   ├── data_sanitizer.py       # Redact secrets before store/AI
│   │   ├── metric_storage.py       # Encrypt/decrypt JSON metric columns
│   │   ├── ai_analysis_service.py  # Cerebras call + robust JSON parsing
│   │   ├── vulnerability_scanner.py# 10-point security audit
│   │   ├── action_executor.py      # Run whitelisted command over SSH
│   │   ├── connection_registry.py  # Track active SSH clients (kill switch)
│   │   ├── retention_service.py    # Delete expired metrics/logs/reports
│   │   ├── intrusion_detection.py  # Failed-login detection + alert
│   │   ├── audit_service.py        # Audit-log helper
│   │   ├── email_service.py        # aiosmtplib HTML/plaintext sender
│   │   ├── email_templates.py      # Reusable HTML email components
│   │   ├── report_email_service.py # Daily AI report email
│   │   ├── action_email_service.py # Registration + action-executed emails
│   │   └── forensic_email_service.py # Emergency-kill forensic incident email
│   │
│   ├── middleware/                 # rbac.py · rate_limit.py · ip_whitelist.py
│   ├── tasks/                      # Celery tasks + scheduler
│   │   ├── metric_tasks.py         # collect/analyze/scan-all/retention tasks
│   │   ├── action_tasks.py         # expire_pending_actions task
│   │   ├── scheduler.py            # APScheduler jobs (Redis-locked)
│   │   └── db.py                   # Per-task NullPool session helper
│   │
│   ├── utils/                      # command_whitelist.py · encryption.py
│   │   ├── security.py             # Argon2 + JWT helpers
│   │   └── security_check.py       # Startup env validation
│   │
│   └── scripts/                    # create_super_admin.py · test_emails.py
│
├── frontend/                       # Next.js application
│   ├── app/                        # App Router pages
│   │   ├── layout.tsx              # Root layout (AppShell)
│   │   ├── login/  settings/  unauthorized/
│   │   ├── dashboard/              # Main monitoring dashboard
│   │   ├── servers/                # List, register, [server_id], edit
│   │   ├── metrics/  ai-reports/  audit-logs/  security-alerts/  actions/
│   │   └── globals.css             # Dark theme + color system
│   ├── components/                 # AppShell, Sidebar, Header, panels, ui/*
│   ├── lib/                        # api.ts, useAuth, withAuth, sessionManager…
│   ├── next.config.ts              # CSP + security headers
│   ├── tailwind.config.js          # Color palette
│   └── package.json
│
└── deploy/                         # Production config (version-controlled)
    ├── ai-infra-backend.service
    ├── ai-infra-frontend.service
    ├── ai-infra-celery.service
    ├── nginx-ai-infra-dashboard.conf
    ├── nginx-ai-infra-ratelimit.conf
    ├── fail2ban-jail.local
    └── backup_ai_infra_db.sh
```

---

## ✅ 5. Prerequisites

- **Ubuntu 20.04 / 22.04 (or 24.04) VPS**
- **Python 3.10+** (tested on 3.12)
- **Node.js 18+** (tested on 24)
- **PostgreSQL 16**
- **Redis**
- **Nginx**
- A **domain name** with DNS A-record pointing to the server
- A **Cerebras API key**
- A **Gmail account with an App Password** enabled (for SMTP)
- **Minimum 2 GB RAM** recommended (4 GB+ for 10+ servers)

---

## 🔐 6. Environment Variables

All secrets live in `/root/projects/AI_Infra_Monitoring/.env` (permissions `600`, never committed). Below are the variable **names** and descriptions only — never commit real values.

### Application
| Variable | Description | Example |
|---|---|---|
| `APP_NAME` | Display name | `AI Infrastructure Monitoring Dashboard` |
| `APP_ENV` | Environment | `production` |
| `APP_DEBUG` | Debug flag | `False` |
| `APP_URL` | Public app URL | `https://your-domain.com` |
| `FRONTEND_URL` | Public frontend URL | `https://your-domain.com` |
| `SUPER_ADMIN_EMAIL` | Super Admin email (also certbot/SMTP) | `you@example.com` |

### Servers
| Variable | Description | Example |
|---|---|---|
| `BACKEND_HOST` / `BACKEND_PORT` | FastAPI bind address/port | `127.0.0.1` / `8002` |
| `FRONTEND_HOST` / `FRONTEND_PORT` | Next.js bind address/port | `127.0.0.1` / `3001` |

### Database
| Variable | Description | Example |
|---|---|---|
| `DATABASE_USER` | DB role | `ai_infra_admin` |
| `DATABASE_PASSWORD` | DB password | `********` |
| `DATABASE_NAME` | Database name | `ai_infra_db` |
| `DATABASE_HOST` / `DATABASE_PORT` | DB host/port | `localhost` / `5432` |
| `DATABASE_URL` | Reference URL (app derives async URL from parts) | `postgresql://…` |

### Authentication & Crypto
| Variable | Description | Example |
|---|---|---|
| `JWT_SECRET_KEY` | JWT signing secret (≥32 chars) | `********` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `15` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `ARGON2_TIME_COST` / `ARGON2_MEMORY_COST` / `ARGON2_PARALLELISM` | Argon2 parameters | `2` / `65536` / `2` |
| `SSH_ENCRYPTION_MASTER_KEY` | 32-byte hex key for AES-256-GCM | `********` |
| `DB_BACKUP_ENCRYPTION_KEY` | Backup encryption key (`openssl rand -hex 32`) | `********` |

### SSH, Rate Limiting & Session
| Variable | Description | Example |
|---|---|---|
| `SSH_CONNECTION_TIMEOUT` | Per-connection timeout (s) | `10` |
| `SSH_MAX_RETRY_LIMIT` | Connection retries | `3` |
| `RATE_LIMIT_LOGIN_MAX_ATTEMPTS` / `RATE_LIMIT_LOGIN_WINDOW_SECONDS` | Login rate limit | `5` / `60` |
| `RATE_LIMIT_API_MAX_REQUESTS` / `RATE_LIMIT_API_WINDOW_SECONDS` | API rate limit | `100` / `60` |
| `SESSION_INACTIVITY_TIMEOUT_MINUTES` | Auto-logout window | `30` |
| `INTRUSION_FAILED_LOGIN_THRESHOLD` / `INTRUSION_ALERT_WINDOW_MINUTES` | Intrusion thresholds | `3` / `10` |

### AI (Cerebras)
| Variable | Description | Example |
|---|---|---|
| `CEREBRAS_API_KEY` | Cerebras API key | `csk-********` |
| `CEREBRAS_MODEL` | Model name | `gpt-oss-120b` |
| `CEREBRAS_MAX_TOKENS` | Max response tokens | `1000` |

### Redis, Celery & Scheduling
| Variable | Description | Example |
|---|---|---|
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | Redis connection | `localhost` / `6379` / `0` |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Celery URLs | `redis://localhost:6379/0` |
| `SCHEDULER_REPORT_INTERVAL_HOURS` | AI report interval | `24` |

### Retention & Email
| Variable | Description | Example |
|---|---|---|
| `METRICS_RETENTION_DAYS` / `LOGS_RETENTION_DAYS` / `AI_REPORTS_RETENTION_DAYS` | Retention windows | `30` / `14` / `90` |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server | `smtp.gmail.com` / `587` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | SMTP credentials (App Password) | `you@gmail.com` / `********` |
| `SMTP_FROM_EMAIL` / `SMTP_TO_EMAIL` | From / alert recipient | `you@gmail.com` |
| `SMTP_USE_TLS` | STARTTLS | `True` |

### Nginx, SSL & Deployment
| Variable | Description | Example |
|---|---|---|
| `NGINX_SERVER_NAME` | Domain | `your-domain.com` |
| `SSL_CERT_PATH` / `SSL_KEY_PATH` | Let's Encrypt cert paths | `/etc/letsencrypt/live/…` |
| `DEPLOYMENT_USER` / `APP_DIR` / `ENV_FILE_PATH` | Deployment paths | `root` / `/root/projects/…` |
| `BACKEND_SERVICE_NAME` / `FRONTEND_SERVICE_NAME` | systemd unit names | `ai-infra-backend` / `ai-infra-frontend` |
| `UPTIME_MONITOR_URL` | External uptime target | `https://your-domain.com/health` |

---

## 🚀 7. Installation & Deployment

> The system was designed and deployed in six phases. The commands below assume Ubuntu and the repo at `/root/projects/AI_Infra_Monitoring`.

### 1. Clone the repository
```bash
git clone https://github.com/<owner>/AI-Infrastructure-Monitoring-Intelligence-Dashboard.git \
  /root/projects/AI_Infra_Monitoring
cd /root/projects/AI_Infra_Monitoring
```

### 2. Configure the `.env` file
```bash
nano .env              # fill in every variable (see Section 6)
chmod 600 .env         # restrict permissions
```

### 3. Phase 1–4 — backend, database, migrations
```bash
sudo apt-get update && sudo apt-get install -y python3-venv postgresql redis-server nginx

cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# PostgreSQL: create role + database (owned by the app role)
sudo -u postgres psql -c "CREATE ROLE ai_infra_admin LOGIN PASSWORD '<DATABASE_PASSWORD>';"
sudo -u postgres createdb -O ai_infra_admin ai_infra_db

# Run migrations (creates all 10 tables)
./venv/bin/alembic upgrade head
```

### 4. Create the Super Admin account
```bash
cd /root/projects/AI_Infra_Monitoring/backend
source venv/bin/activate
python scripts/create_super_admin.py --email you@example.com
# You will be securely prompted for the password (no echo).
```

### 5. Build the frontend
```bash
cd ../frontend
npm install
npm run build
```

### 6. Configure Nginx + obtain SSL
```bash
sudo cp deploy/nginx-ai-infra-ratelimit.conf /etc/nginx/conf.d/
sudo cp deploy/nginx-ai-infra-dashboard.conf /etc/nginx/sites-available/ai-infra-dashboard
sudo ln -s /etc/nginx/sites-available/ai-infra-dashboard /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Let's Encrypt certificate + auto-renewal
sudo certbot --nginx -d your-domain.com -d www.your-domain.com \
  --non-interactive --agree-tos --email you@example.com
```

### 7. Install & start systemd services
```bash
sudo cp deploy/ai-infra-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-infra-backend ai-infra-frontend ai-infra-celery
sudo systemctl start ai-infra-backend   # wait ~10s
sudo systemctl start ai-infra-celery    # wait ~5s
sudo systemctl start ai-infra-frontend
```

### 8. Harden & verify
```bash
# Firewall + fail2ban
sudo ufw default deny incoming && sudo ufw allow 22,80,443/tcp && sudo ufw enable
sudo cp deploy/fail2ban-jail.local /etc/fail2ban/jail.local && sudo systemctl restart fail2ban

# Verify
curl -s https://your-domain.com/health     # -> {"status":"healthy",...}
systemctl is-active ai-infra-backend ai-infra-frontend ai-infra-celery nginx postgresql redis-server
```

---

## ⚙️ 8. Systemd Services

| Service | Description | ExecStart |
|---|---|---|
| `ai-infra-backend.service` | FastAPI backend (uvicorn, 4 workers) | `uvicorn main:app --host 127.0.0.1 --port 8002 --workers 4` |
| `ai-infra-frontend.service` | Next.js frontend | `npm start` (`next start -H 127.0.0.1`, `PORT=3001`) |
| `ai-infra-celery.service` | Celery worker | `celery -A celery_app worker --concurrency=4` |

All units use `EnvironmentFile=/root/projects/AI_Infra_Monitoring/.env`, `Restart=always`, and start on boot.

```bash
# Start / stop / restart
sudo systemctl start|stop|restart ai-infra-backend
sudo systemctl start|stop|restart ai-infra-frontend
sudo systemctl start|stop|restart ai-infra-celery

# Status
systemctl status ai-infra-backend

# Live logs (journald)
journalctl -u ai-infra-backend -f
journalctl -u ai-infra-celery -n 100 --no-pager
journalctl -u ai-infra-frontend -f
```

---

## 🛡️ 9. Security Architecture

### Credential encryption at rest
- SSH passwords and private keys are encrypted with **AES-256-GCM** (`utils/encryption.py`) using a 32-byte key derived from `SSH_ENCRYPTION_MASTER_KEY`. Ciphertext format: URL-safe base64 of `nonce(12) ‖ ciphertext ‖ tag(16)`.
- Process/port JSON columns and raw log lines are stored encrypted; AI report snapshots are encrypted.
- Credentials are **never returned** by the API (masked as `••••••••`); the reveal endpoint requires Super Admin + password re-verification.

### Transport security
- Nginx terminates **TLS 1.2/1.3** with a Let's Encrypt certificate; all HTTP is 301-redirected to HTTPS.
- Security headers: **HSTS** (`max-age=63072000; includeSubDomains; preload`), `X-Frame-Options`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, plus a strict **Content-Security-Policy** from the Next.js app.
- App components bind to **loopback only**; external access is solely via Nginx.

### Authentication flow
1. `POST /api/v1/auth/login` → Argon2 verify → issues a **15-minute JWT access token** + an opaque **refresh token** (only its SHA-256 hash is stored).
2. `POST /api/v1/auth/refresh` **rotates** the refresh token (old token revoked; reuse is rejected).
3. Every request carries `Authorization: Bearer <access>`; the access token also enforces the inactivity window.
4. `401` → frontend clears tokens and redirects to `/login`; `403` → redirects to `/unauthorized`.

### RBAC model
| Capability | Viewer | Admin | Super Admin |
|---|:--:|:--:|:--:|
| View dashboard, metrics, AI reports | ✅ | ✅ | ✅ |
| Register / edit / delete servers | ❌ | ✅ | ✅ |
| Dry-run / request / execute actions | ❌ | ✅ | ✅ |
| Second-confirm a high-risk action (not own) | ❌ | ✅ | ✅ |
| View security alerts | ❌ | ✅ | ✅ |
| View audit logs / CSV export | ❌ | ❌ | ✅ |
| Reveal credentials | ❌ | ❌ | ✅ |
| Emergency kill switch | ❌ | ❌ | ✅ |

RBAC is enforced **server-side** via FastAPI dependencies (`require_viewer` / `require_admin` / `require_super_admin`) and **also** in the UI (nav items removed from the DOM, pages guarded by `withAuth`).

### Audit logging
Every login, logout, token refresh, password change, server registration/update/delete, credential reveal, action request/confirm/execute, security scan, intrusion event, and emergency kill is recorded in `audit_logs` with user identity, IP, target server, success flag, and timestamp.

### Intrusion detection thresholds
- After **`INTRUSION_FAILED_LOGIN_THRESHOLD`** (default 3) failed logins from one IP within **`INTRUSION_ALERT_WINDOW_MINUTES`** (default 10), an HTML alert email is sent and the IP is temporarily blocked.
- Login endpoints are additionally rate-limited (default **5 / 60s**); other endpoints **100 / 60s**.

### Emergency response procedure
The Super Admin re-enters their password and triggers the kill switch → credentials nullified, pending/approved actions cancelled, tracked SSH connections closed, server marked offline, audit entry written, and a forensic incident report email dispatched. **Re-register only after confirming the server is clean.**

---

## 📡 10. API Documentation

Base URL: `https://your-domain.com/api/v1` · Interactive docs: `/docs` (Swagger UI).

### Auth — `/api/v1/auth`
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/login` | Public | Authenticate, issue access + refresh tokens |
| POST | `/refresh` | Public (valid token) | Rotate refresh token |
| POST | `/logout` | Public (valid token) | Revoke a refresh token |
| GET | `/me` | Any | Current user profile |
| POST | `/change-password` | Any | Change own password (complexity enforced) |
| POST | `/verify-password` | Any | Re-verify current password (reveal gate) |

### Servers — `/api/v1/servers`
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/register` | Admin+ | Register a server (encrypts creds) |
| POST | `/test-connection` | Admin+ | Test SSH connectivity |
| GET | `/` | Any | List servers (masked creds) |
| GET | `/{server_id}` | Any | Get one server |
| PUT | `/{server_id}` | Admin+ | Update a server |
| DELETE | `/{server_id}` | Admin+ | Delete a server |
| POST | `/{server_id}/toggle-key-only` | Admin+ | Toggle key-only mode |
| POST | `/{server_id}/reveal-credentials` | Super Admin | Reveal decrypted credential |
| POST | `/{server_id}/emergency-kill` | Super Admin | Emergency kill switch |
| POST | `/{server_id}/security-scan` | Admin+ | Run 10-point vulnerability scan |
| GET | `/{server_id}/security-scan/latest` | Any | Latest scan |
| GET | `/{server_id}/security-scan/history` | Any | Scan history |

### Metrics — `/api/v1/metrics`
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/{server_id}/latest` | Any | Latest metric snapshot (decrypted) |
| GET | `/{server_id}/history` | Any | Time-series for last N hours |
| POST | `/{server_id}/refresh` | Admin+ | Queue a full scan (metrics→logs→AI) |
| GET | `/{server_id}/refresh/{task_id}/status` | Any | Poll Celery task status |

### AI Reports — `/api/v1/ai-reports`
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/{server_id}/latest` | Any | Latest AI report (structured) |
| GET | `/{server_id}/history` | Any | Paginated report history |
| POST | `/{server_id}/generate` | Admin+ | Queue a new AI analysis |

### Actions — `/api/v1/actions`
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/commands` | Any | Whitelist catalog (by risk level) |
| POST | `/dry-run` | Admin+ | Execute & return output, store nothing |
| POST | `/request` | Admin+ | Create a pending action |
| POST | `/{action_id}/verify-password` | Admin+ | Verify requester password |
| POST | `/{action_id}/second-confirm` | Admin+ (not requester) | Dual approval |
| POST | `/{action_id}/cancel` | Admin+ | Cancel a pending action |
| POST | `/{action_id}/execute` | Admin+ | Execute approved action |
| GET | `/{action_id}/status` | Admin+ | Action status + time lock |
| GET | `/awaiting-confirmation` | Admin+ | High-risk actions awaiting your confirm |
| GET | `/history` | Admin+ | Action history (own / all) |

### Dashboard — `/api/v1/dashboard`
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/overview` | Any | Counts + averages + 24h activity |
| GET | `/servers/status` | Any | Per-server status + latest metrics |
| GET | `/security-alerts` | Admin+ | Recent security events with severity |
| GET | `/audit-logs` | Super Admin | Paginated, filterable audit log |
| GET | `/audit-logs/export` | Super Admin | Full audit log as CSV |

### Health
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/health` | Public | `status`, `timestamp`, `database`, `redis`, `version` |

---

## 🖧 11. Monitored Server Requirements

To be monitored, a server must:
- **Be Linux-based** (Debian/Ubuntu/RHEL families supported by the standard commands).
- **Have SSH enabled** and reachable from the dashboard host.
- **Allow the dashboard server's IP** through its own firewall (and the dashboard's per-server IP whitelist).
- Provide an SSH account that can run the read-only collection commands (and, for privileged actions, `sudo`/root).

**No agent is installed.** Collection uses standard, read-only commands over SSH, for example:

| Purpose | Command (read-only) |
|---|---|
| CPU usage | `grep 'cpu ' /proc/stat \| awk '{...}'` |
| RAM usage | `free -m \| awk 'NR==2{...}'` |
| Disk usage | `df -h` |
| Uptime | `uptime -p` |
| Top processes | `ps aux --no-headers \| head -50` |
| Open ports | `ss -tlnp` |
| Network stats | `cat /proc/net/dev` |
| Logged-in users | `who` |
| Logs | `sudo tail -n N /var/log/{syslog,auth.log,...}` |

Privileged actions are limited to the **hardcoded whitelist** (e.g. `systemctl reload nginx`, `df -i`, `systemctl restart postgresql`) — arbitrary commands are never executed.

---

## 💾 12. Backup & Recovery

**How it works** — `deploy/backup_ai_infra_db.sh` runs daily at **02:00** via cron:
1. `pg_dump` the `ai_infra_db` database (auth + key sourced from `.env`),
2. gzip the dump,
3. encrypt with **AES-256-CBC (PBKDF2)** using `DB_BACKUP_ENCRYPTION_KEY`,
4. delete the plaintext dump, and
5. prune encrypted backups older than **7 days**.

**Location** — `/root/backups/ai_infra_db/backup_YYYYMMDD_HHMMSS.sql.gz.enc`
**Logs** — `/var/log/ai_infra_backup.log`

**Restore**
```bash
KEY=$(grep '^DB_BACKUP_ENCRYPTION_KEY=' /root/projects/AI_Infra_Monitoring/.env | cut -d= -f2-)
openssl enc -d -aes-256-cbc -pbkdf2 \
  -in /root/backups/ai_infra_db/backup_YYYYMMDD_HHMMSS.sql.gz.enc -k "$KEY" \
  | gunzip | PGPASSWORD='<DATABASE_PASSWORD>' psql -h localhost -U ai_infra_admin -d ai_infra_db
```

> 💡 Retention is local-only by default — copy `*.enc` files to remote/object storage for off-site durability.

---

## 🔧 13. Troubleshooting

| Symptom | Likely cause & fix |
|---|---|
| **Server shows offline** | SSH unreachable or creds revoked. Test from the dashboard host: `ssh user@ip`. Verify the dashboard IP is whitelisted on the target firewall, then click **Refresh**. |
| **CPU shows 0%** | Legacy `top`-based parsing on an unusual locale. The collector now reads `/proc/stat` directly with one-decimal precision — re-run a metric refresh. |
| **SSH authentication failed** | Wrong password/key, or key-only mode is on for a password attempt. Re-check credentials via **Edit server** and **Test Connection**. |
| **AI report not generating / "AI analysis unavailable"** | Cerebras endpoint/key/quota issue. Check `CEREBRAS_API_KEY`/`CEREBRAS_MODEL`; the fallback stores a clean structured message (never raw JSON). Retry generation. |
| **Email not sending** | Gmail App Password required (not your normal password). Verify `SMTP_*` and run `python scripts/test_emails.py`. |
| **Celery not processing tasks** | `systemctl status ai-infra-celery`; confirm Redis is up (`redis-cli ping` → `PONG`) and `CELERY_BROKER_URL` is correct; check `journalctl -u ai-infra-celery`. |
| **Nginx 502 Bad Gateway** | Backend/frontend not running or wrong upstream port. `systemctl restart ai-infra-backend ai-infra-frontend`; confirm 8002/3001 are listening (`ss -tlnp`). |
| **"Invalid email or password" on a correct password** | Email is matched case-insensitively now; clear any autofilled old value. After 3 failed tries the IP is temporarily blocked (intrusion lock, ~10 min). |
| **"Too many attempts"** | Rate limit / intrusion lock. Wait for the window to elapse or clear it. |

---

## 🗺️ 14. Roadmap

- 📱 **Mobile app** (iOS/Android companion)
- 👥 **Multi-user team support** with org/workspace separation
- 💬 **Slack integration** for alerts and reports
- 🎚️ **Custom alert thresholds** per server and per metric
- 🐳 **Docker / Docker Compose** deployment option
- 🪟 **Windows Server support** via WinRM
- ☸️ **Kubernetes cluster monitoring**
- 🧠 **Custom AI prompts per server** for tailored analysis

---

## 📄 15. License

Released under the **MIT License**.

```text
MIT License

Copyright (c) 2026 AI Infrastructure Monitoring & Intelligence Dashboard

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 👤 16. Author

**Project built and maintained by the owner.**

- 📧 Contact: `p*******@gmail.com`
- 🛡️ Built with security-first engineering: encrypted credentials, RBAC, audit logging, and AI-assisted analysis.

<div align="center">

**⭐ If this project helps you manage your infrastructure, consider starring the repository.**

*Built with FastAPI, Next.js, PostgreSQL, Celery, and Cerebras AI.*

</div>
