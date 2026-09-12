# Cloud deployment: HIOS Forecast

## Target architecture

Deploy the FastAPI container and PostgreSQL as separate managed services in the same cloud region. The phone-facing endpoint must use provider HTTPS. The database must not be reachable from the public internet; attach it through the platform’s private service network.

The recommended operational shape is:

```text
Phone / browser -- HTTPS + access gate --> HIOS container --> private PostgreSQL
                                      \-> Google / Solcast / Deye APIs
```

The container exposes only `/health` for an unauthenticated platform health probe. API routes retain their RS256 bearer-token protection. The forecast dashboard can also be protected with optional HTTP Basic access at the service edge using two server-side secrets.

## Container

The [Dockerfile](../../Dockerfile) runs checksum-verified SQL migrations before starting Uvicorn. It runs as a non-root `hios` user and deliberately excludes `.env`, PEM/key files, source archives and Git data through [`.dockerignore`](../../.dockerignore).

Build locally when Docker is available:

```powershell
docker build --tag hios-forecast:local .
```

## Required cloud secrets

Set these in the cloud platform’s secret store. Do not put their values in GitHub source, Docker build arguments, SharePoint or browser JavaScript.

| Secret | Purpose |
| --- | --- |
| `DATABASE_URL` | Private managed PostgreSQL connection URI with TLS required |
| `JWT_PUBLIC_KEY_FILE` | Mounted PEM public key file for RS256 validation |
| `JWT_ISSUER` / `JWT_AUDIENCE` | JWT validation boundary |
| `DEYE_APP_ID` / `DEYE_APP_SECRET` | Deye server-side integration |
| `GOOGLE_WEATHER_API_KEY` / `SOLCAST_API_KEY` | Weather integrations |
| `HIOS_DASHBOARD_USER` / `HIOS_DASHBOARD_PASSWORD` | Optional browser access gate for `/` and `/assets/*` |

The deployment must use an isolated production database with automatic backups, point-in-time recovery where available, TLS and no public database endpoint.

## Release procedure

1. Create a managed PostgreSQL service on a private network in the chosen region.
2. Build the `Dockerfile` from the `main` commit through the host’s GitHub integration.
3. Configure the required secrets in the host; mount the JWT public key as a secret file.
4. Configure `PORT=8000`, HTTPS-only ingress and the hostname.
5. Verify `GET /health` through the platform health check.
6. Sign in to the dashboard from a phone using the access gate and verify no secret appears in HTML or API responses.
7. Verify database backup/restore and record the deployment URL and release SHA.

## Current boundary

This repository is deployment-ready, but no cloud account, billing subscription, managed PostgreSQL instance, production hostname or external URL exists yet. Provisioning them is a separate, externally billable action and requires the account owner’s active cloud login.
