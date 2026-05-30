# Deployment Report — AI Infrastructure Monitoring & Intelligence Dashboard

- **Project:** AI Infrastructure Monitoring & Intelligence Dashboard
- **Version:** 1.0.0
- **Deployment date:** 2026-05-30 08:42 UTC
- **Server IP:** 89.117.62.208
- **Primary domain:** https://monitoringsystem.online (+ www)

---

## Assigned ports

| Component | Bind address | Notes |
|---|---|---|
| FastAPI backend | `127.0.0.1:8002` | uvicorn, 4 workers, behind nginx |
| Next.js frontend | `127.0.0.1:3001` | `next start -H 127.0.0.1`, behind nginx |
| Redis | `127.0.0.1:6379` | broker/result backend + rate-limit + locks |
| PostgreSQL | `localhost:5432` | database `ai_infra_db` |

All app components bind to loopback only; external traffic reaches them solely
through the nginx reverse proxy on 443/80.

---

## systemd services

| Service | Description | Status |
|---|---|---|
| `ai-infra-backend.service` | FastAPI backend (uvicorn, 4 workers) | active / enabled |
| `ai-infra-frontend.service` | Next.js frontend (`npm start`) | active / enabled |
| `ai-infra-celery.service` | Celery worker (concurrency 4) | active / enabled |

Supporting services: `nginx`, `postgresql`, `redis-server`, `fail2ban`,
`certbot.timer` — all active/enabled.

Unit files are version-controlled in `deploy/`.

---

## Nginx sites

| Site | Domain | Upstream |
|---|---|---|
| `ai-infra-dashboard` (new) | monitoringsystem.online | `/api`,`/docs`,`/health` → 8002; `/` → 3001 |
| `n8n` | growthengineai.space | localhost:5678 |
| `nc-dashboard` | ncperformancedashboard.space | 127.0.0.1:8001 |
| `stjosephharvestfinmgt.space` | stjosephharvestfinmgt.space | 127.0.0.1:8501 |
| `default` | catch-all (`_`) | — |

The new site uses name-based virtual hosting and does **not** affect the three
pre-existing production sites. Config: `deploy/nginx-ai-infra-dashboard.conf`
(+ `deploy/nginx-ai-infra-ratelimit.conf` for the `limit_req_zone`, which must
live in the http context).

### Security headers (served by nginx + the app)
HSTS (`max-age=63072000; includeSubDomains; preload`), X-Frame-Options,
X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy,
X-XSS-Protection, plus the app's Content-Security-Policy. Gzip enabled;
`client_max_body_size 10M`; API rate limit `10r/s` burst 20.

---

## SSL certificate

- **Domains:** monitoringsystem.online, www.monitoringsystem.online
- **Issuer:** Let's Encrypt (via certbot, webroot challenge)
- **Expiry:** Aug 28 2026 (notAfter=Aug 28 07:33:31 2026 GMT)
- **Auto-renewal:** `certbot.timer` (active + enabled); renews automatically
- **Protocols:** TLS 1.2 / 1.3 only

---

## Backups

- **Script:** `/root/scripts/backup_ai_infra_db.sh` (version-controlled at `deploy/backup_ai_infra_db.sh`)
- **Schedule:** daily at **02:00** via root crontab → `/var/log/ai_infra_backup.log`
- **Location:** `/root/backups/ai_infra_db/`
- **Format:** `pg_dump | gzip` then **AES-256-CBC (pbkdf2)** encrypted (`*.sql.gz.enc`)
- **Key:** `DB_BACKUP_ENCRYPTION_KEY` in `.env` (generated with `openssl rand -hex 32`)
- **Retention:** encrypted backups older than 7 days are pruned
- **Verified:** a backup was created and confirmed to decrypt to a valid `pg_dump`.

---

## Firewall & intrusion prevention

- **UFW:** active — default **deny incoming** / allow outgoing; **22, 80, 443** allowed (v4+v6).
  Pre-existing rules for other live services on this shared server (Streamlit
  8501, n8n 5678, Qdrant 6333, Ollama 11434, restricted PostgreSQL 5432) were
  **deliberately preserved** — a full UFW reset would have severed those live
  production services (see Maintenance notes).
- **fail2ban:** active with jails `sshd`, `nginx-http-auth`, `nginx-limit-req`
  (bantime 3600s, findtime 600s, maxretry 3).

---

## Security checklist results

| # | Check | Result |
|---|---|---|
| 1 | `.env` permissions = 600 | ✅ PASS |
| 2 | `.env` never committed to git | ✅ PASS (apex + nested) |
| 3 | backend / frontend / celery running | ✅ PASS |
| 4 | nginx config valid + running | ✅ PASS |
| 5 | PostgreSQL running | ✅ PASS |
| 6 | Redis running | ✅ PASS |
| 7 | UFW active | ✅ PASS |
| 8 | fail2ban running | ✅ PASS |
| 9 | pip-audit | ✅ No known vulnerabilities |
| 10 | npm audit | ✅ 0 high / 0 critical (2 moderate transitive, see notes) |
| 11 | `/health` reachable & `healthy` | ✅ PASS |
| 12 | backup script works | ✅ PASS |
| 13 | API requires auth (401 without token) | ✅ PASS |
| 14 | SSH credentials encrypted in DB | ✅ Mechanism verified (Phases 2/4); 0 servers currently registered |

---

## Health endpoint

`GET /health` (no auth) returns:
```json
{ "status": "healthy", "timestamp": "<utc>", "database": "connected", "redis": "connected", "version": "1.0.0" }
```
Reachable directly (`127.0.0.1:8002/health`) and via nginx (`https://monitoringsystem.online/health`).

---

## Accounts

- **Super Admin email:** philiposita1041@gmail.com (role `super_admin`, active).
  Created via `backend/scripts/create_super_admin.py`. The initial password was
  generated and stored **root-only** at `/root/ai_infra_super_admin_password.txt`
  (chmod 600) — **log in, change it, then delete that file.**

---

## Next steps & maintenance notes

1. **Rotate test accounts:** earlier phases created test users
   (`admin@monitoringsystem.online`, `viewer@x.com`, `admin2@x.com`) with known
   passwords — delete or rotate them now that the system is live.
2. **Change the Super Admin password** and delete `/root/ai_infra_super_admin_password.txt`.
3. **UFW reset was intentionally skipped.** The spec assumed all other app ports
   were loopback-bound, but several (8501, 5678, 6333, 11434, 5432) are
   externally bound and back live production sites. The hardening goal
   (default-deny + 22/80/443) is already met without breaking them. If you ever
   want a clean reset, first confirm those services are migrated behind nginx.
4. **npm moderate advisories** are transitive `postcss` via the Next.js build
   toolchain; the only "fix" downgrades Next.js to v9 (breaking), so they are
   intentionally left.
5. **Multi-worker scheduler:** the backend runs 4 uvicorn workers; APScheduler
   starts in each, but a Redis lock ensures only one worker dispatches each
   scheduled job (scan / retention / action-expiry).
6. **Third-party apt repo:** a pre-existing Caddy apt source has an unverifiable
   GPG key (warning only; unrelated to this project) — fix or remove it to keep
   `apt update` clean.
7. **Monitoring:** point uptime monitoring at `https://monitoringsystem.online/health`.
8. **Backups offsite:** consider copying the encrypted `*.enc` backups to remote
   storage; they are currently local-only.
