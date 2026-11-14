# Installation and operation

Everything runs in Docker. This guide covers a first trial on a laptop, a pilot installation on a server, and day-to-day operation.

## 1. Requirements

| | Minimum |
|---|---|
| Docker Engine with the Compose plugin | Compose 2.24 or newer (`docker compose version`) |
| Memory | 4 GB free. Add 4 GB if you enable the guard model |
| Disk | 3 GB for images, plus the database |
| Network during the build | Access to Docker Hub, PyPI, npm and GitHub releases (for the language model) |
| Network at run time | The gateway must reach your model provider and, for live connectors, Microsoft Graph and the GitHub API |

Linux, macOS and Windows with WSL 2 all work.

## 2. First start (demo mode)

```bash
git clone https://github.com/m-zest/conformance_v2.1.git
cd conformance_v2.1
docker compose up -d --build
docker compose ps
```

Wait until `gateway` shows `healthy`. The first start creates the database, the administrator account, the sample tools and two weeks of synthetic activity.

| Service | Address | Purpose |
|---|---|---|
| `dashboard` | http://localhost:8080 | Web interface |
| `gateway` | http://localhost:8000 | API endpoint for AI tools, and the dashboard API |
| `demo-app` | http://localhost:8090 | Sample internal tool |
| `simulator` | http://localhost:9000 | Mock model provider and vendor APIs |
| `postgres` | internal only | Database |

Sign in to the dashboard with `admin@meridian.example` and the password `ChangeMe-Pilot-2026`.

The [README](../README.md#try-it-in-ten-minutes) has a ten minute walkthrough.

### Useful commands

```bash
docker compose logs -f gateway          # follow the gateway log
docker compose ps                       # service status
docker compose down                     # stop, keep data
docker compose down -v                  # stop and delete all data
./scripts/send-examples.sh              # send example requests
docker compose exec gateway python -m app.cli verify-ledger
```

`make help` lists shortcuts for the same commands.

## 3. Configuration

Copy the template and edit it. Every setting is documented in the file.

```bash
cp .env.example .env
docker compose up -d        # apply changes
```

The settings you will change first:

| Setting | Purpose |
|---|---|
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | First dashboard account. Only used when the database is empty |
| `SECRET_KEY` | Signs sessions and fingerprints. Generated and stored in the data volume if empty. Set it explicitly for a server installation and keep it safe |
| `POSTGRES_PASSWORD` | Database password. Set before the first start |
| `OPENAI_BASE_URL`, `OPENAI_API_KEY` | Your OpenAI, Azure OpenAI or self-hosted OpenAI-compatible endpoint |
| `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY` | Your Anthropic endpoint |
| `DASHBOARD_URL`, `GATEWAY_PUBLIC_URL` | The addresses people actually use. Shown in notification links and connection instructions |
| `DEMO_MODE`, `DEMO_SEED` | Demo tools and synthetic data |
| `STORE_PROMPTS`, `RETENTION_DAYS` | What is stored and for how long |
| `SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL`, `ALERT_WEBHOOK_URL`, `SMTP_*` | Where alerts are sent |
| `M365_COPILOT_MODE`, `GITHUB_COPILOT_MODE` | Connectors: `disabled`, `demo` or `live` |

### Model providers

| Provider | Settings |
|---|---|
| OpenAI | `OPENAI_BASE_URL=https://api.openai.com/v1` and `OPENAI_API_KEY` |
| Azure OpenAI | `OPENAI_BASE_URL=https://<resource>.openai.azure.com/openai/v1`, `OPENAI_API_KEY`, `OPENAI_AUTH_STYLE=api-key` |
| Anthropic | `ANTHROPIC_BASE_URL=https://api.anthropic.com` and `ANTHROPIC_API_KEY` |
| Self-hosted (vLLM, Ollama, others) | `OPENAI_BASE_URL=http://<host>:<port>/v1`, any value for the key if none is required |

Requests to `/v1/chat/completions` and `/v1/responses` go to the OpenAI-compatible upstream. Requests to `/v1/messages` go to the Anthropic upstream. Both can be configured at once.

Spend figures in the dashboard are estimates from token counts and a price table. Put your contracted prices in a JSON file, mount it into the gateway container and set `PRICING_PATH`. The format is described in `backend/app/pricing.py`.

## 4. From demo to pilot

Start the pilot from an empty installation so that no synthetic data is mixed with real activity.

1. Stop the demo and delete its data:

   ```bash
   docker compose down -v
   ```

2. In `.env` set:

   ```bash
   DEMO_MODE=false
   DEMO_SEED=false
   M365_COPILOT_MODE=disabled
   GITHUB_COPILOT_MODE=disabled
   ALERT_WEBHOOK_URL=
   ADMIN_EMAIL=<your address>
   ADMIN_PASSWORD=<a strong password>
   SECRET_KEY=<output of: openssl rand -base64 48>
   POSTGRES_PASSWORD=<a strong password>
   DASHBOARD_URL=https://ai-governance.<your domain>
   GATEWAY_PUBLIC_URL=https://ai-gateway.<your domain>
   COOKIE_SECURE=true
   ```

   plus your model provider settings.
3. Start with the pilot override, which leaves out the simulator and the sample tool and defaults the demo settings to off:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.pilot.yml up -d --build
   ```

   Use the same two `-f` options for every later `docker compose` command on this installation, or set `COMPOSE_FILE=docker-compose.yml:docker-compose.pilot.yml` in `.env`.
4. Sign in, register your first tool under **Tools** with the "Monitor only" policy, create a key and connect the tool as described in [INTEGRATIONS.md](INTEGRATIONS.md).
5. Add dashboard accounts for the people who will triage alerts under **Settings**.

[PILOT.md](PILOT.md) describes how to run the pilot itself.

## 5. TLS and network placement

The containers speak plain HTTP. In any shared environment put them behind the reverse proxy or ingress you already use for internal services, and terminate TLS there.

- Publish the dashboard (port 8080) and the gateway (port 8000) under two host names.
- Set `BIND_ADDRESS=127.0.0.1` when the reverse proxy runs on the same host, so the ports are not reachable directly.
- Set `COOKIE_SECURE=true` once the dashboard is served over HTTPS.
- Disable response buffering for the gateway host so that streamed answers are relayed as they arrive. In nginx: `proxy_buffering off;` and a `proxy_read_timeout` of several minutes.
- Restrict the dashboard to the corporate network or VPN.
- Allow outbound traffic from the gateway only to your model provider and the connector APIs.
- If you self-host models, configure them to verify the compliance token (see `sdk/conformance_verifier.py`) and accept traffic only from the gateway.

## 6. Optional detection layers

### Named entities

Included in the default image. It adds about 400 MB and detects names of people and places. To build without it set `INSTALL_NER=false` in `.env` and rebuild. To keep it installed but switched off set `NER_ENABLED=false`.

### Guard model (Llama Guard)

```bash
# .env
GUARD_LLM_ENABLED=true

docker compose --profile guard up -d
```

This starts an Ollama container and downloads `llama-guard3:1b` (about 1.6 GB). The status appears under **Settings, Detection layers**. A CPU is enough for the 1B model in the default asynchronous mode. For inline mode or the larger models use a GPU host and point `GUARD_LLM_URL` at it. [DETECTION.md](DETECTION.md) explains when the guard model is worth enabling.

## 7. Operation

### Backups

Two things hold state:

| What | Where | How to back up |
|---|---|---|
| Database | `pgdata` volume | `docker compose exec postgres pg_dump -U conformance conformance > backup.sql` |
| Signing key and generated secret | `gateway-data` volume, files `keys/signing_es256.pem` and `secret.key` | Copy the files to your secret store |

Losing the signing key does not break the ledger, but entries signed with the old key can no longer have their signatures checked. Losing `SECRET_KEY` invalidates dashboard sessions and resets repeat detection.

### Upgrades

```bash
git pull
docker compose up -d --build
```

The schema is created automatically. This version has no migration tool, so read the release notes before upgrading across versions that change tables.

### Monitoring the service

- `GET /healthz` on the gateway: the process is up.
- `GET /readyz` on the gateway: the database is reachable.
- **Settings** shows detector status and the number of records dropped or failed, which should stay at zero.
- Schedule `python -m app.cli verify-ledger` (exit code 1 on failure) and alert on it.

### Recovering access

```bash
docker compose exec gateway python -m app.cli reset-password admin@example.com 'a-new-long-password'
```

### Retention

Interaction records older than `RETENTION_DAYS` are deleted hourly. Ledger entries remain so that the chain stays verifiable.

## 8. Running without Docker

For development or a quick look on a machine without Docker:

```bash
pip install -r backend/requirements-dev.txt

# terminal 1: simulator
PYTHONPATH=. GATEWAY_JWKS_URL=http://127.0.0.1:8000/.well-known/jwks.json \
  uvicorn simulator.app:app --port 9000

# terminal 2: gateway with SQLite and demo data
PYTHONPATH=backend:. DEMO_MODE=true DEMO_SEED=true DEMO_APP_KEY=gw_demo_internal_assistant_local_only \
  SIMULATOR_URL=http://127.0.0.1:9000 OPENAI_BASE_URL=http://127.0.0.1:9000/v1 ANTHROPIC_BASE_URL=http://127.0.0.1:9000 \
  M365_COPILOT_MODE=demo GITHUB_COPILOT_MODE=demo NER_ENABLED=false \
  uvicorn app.main:app --port 8000

# terminal 3: dashboard
cd frontend && npm install && npm run dev      # http://localhost:5173
```

Without `DATABASE_URL` the gateway uses a SQLite file under `./data`.

## 9. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `gateway` stays in `starting` for a minute on first start | It is loading the demo data. `docker compose logs gateway` shows progress |
| Build fails with a certificate error while installing packages | Your network inspects TLS. Add your corporate CA to the base images or build on a network without inspection |
| Build fails downloading the language model | GitHub releases are not reachable. Set `INSTALL_NER=false`, or download the wheel once and pass it with `--build-arg NER_MODEL_URL=<your mirror>` |
| A tool gets `401 Unknown gateway key` | The key was mistyped or revoked. Create a new one under Tools |
| A tool gets `403 policy_violation` | Working as intended: the policy blocked the request. The message names what was detected |
| A tool gets `502` | The gateway cannot reach the model provider. Check `OPENAI_BASE_URL` or `ANTHROPIC_BASE_URL`, the provider key and outbound firewall rules |
| Requests appear under "Unattributed" | The tool does not send `X-End-User`, or it is not marked as trusted. See [INTEGRATIONS.md](INTEGRATIONS.md) |
| The simulator answers `missing compliance token` | You called the simulator directly. Call the gateway on port 8000 |
| Connector shows "Failed" | Hover the status on the Tools page, or read the gateway log. Usually missing permissions or consent |
| Port already in use | Change `GATEWAY_PORT`, `DASHBOARD_PORT`, `DEMO_APP_PORT` or `SIMULATOR_PORT` in `.env` |
| `env_file` error on `docker compose up` | Your Compose version is older than 2.24. Upgrade, or create an empty `.env` file |
