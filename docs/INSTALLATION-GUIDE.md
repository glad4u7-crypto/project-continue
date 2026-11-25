# Project Continue — Installation & Operator Guide

## 1. Supported baseline

- Python 3.11 or newer.
- Git.
- A private writable data directory for SQLite.
- An always-on host for any production scheduler.
- HTTPS termination and host secret storage for production.

Google Colab is a development/acceptance environment, not an always-on production host. Do not reboot or stop an existing Colab runtime/dashboard as an installation step.

## 2. Local development installation

From a clean checkout:

```bash
git clone https://github.com/glad4u7-crypto/project-continue.git
cd project-continue
git checkout main
python3.11 -m venv .venv
```

Activate the environment:

Linux/macOS:
```bash
source .venv/bin/activate
```

Windows PowerShell:
```powershell
.venv\\Scripts\\Activate.ps1
```

Install declared dependencies and create a local environment file:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Linux/macOS:
```bash
cp .env.example .env
mkdir -p .data
```

Windows PowerShell:
```powershell
Copy-Item .env.example .env
New-Item -ItemType Directory -Force .data
```

Edit `.env` with local non-production settings. Keep it untracked. Do not put real secrets in chat or Git.

Start the app:
```bash
streamlit run app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`).

Run tests:
```bash
python -m compileall -q .
python -m pytest -q
```

## 3. Container installation (single-host production)

For a reproducible Docker deployment, use the repository's Dockerfile and Compose definition. Follow `docs/CONTAINER-DEPLOYMENT.md` on the selected Linux host:

```bash
git clone https://github.com/glad4u7-crypto/project-continue.git
cd project-continue
cp .env.production.example .env.production
chmod 600 .env.production
# Edit .env.production using a secure editor; set unique admin credentials
docker compose build --pull
docker compose up -d
docker compose ps
curl --fail http://127.0.0.1:8501/_stcore/health
```

The service binds only to host loopback. Put a trusted HTTPS reverse proxy in front of it before remote access. SQLite and verified backups use separate named Docker volumes; configure independent off-host backup replication. Never run `docker compose down -v` during routine updates because it deletes persistent data.

## 3. Production configuration contract

Production must be configured using the hosting platform's environment/secret manager, not a committed `.env` file.

Required:
- `APP_ENV=production`
- `LOG_LEVEL=INFO` (or WARNING/ERROR; never DEBUG)
- `PROJECT_CONTINUE_DB` = absolute path on a persistent private volume
- `SESSION_SIGNING_KEY` = random secret with at least 32 bytes

Optional only when required:
- `GITHUB_REPOSITORY`
- `GITHUB_TOKEN` (read-only minimum permissions)
- AI provider/model/base URL/API key settings
- `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` for controlled first-admin bootstrap
- `PROJECT_CONTINUE_BACKUP_DIR` for the verified backup runner

Use a cryptographically secure random generator to create a signing key; do not use a human password. Example generation (prints a secret locally—store it directly in the host secret manager and do not paste it into chat):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The default production gate requires an administrator account. Bootstrap variables should be removed from the host environment after the first account is created. Passwords must meet the application's 12-character minimum.

To deliberately enable the signed-in project-member workflow, set `AUTHORIZATION_ENFORCED=true` in the host environment. Then sign in as the administrator, bootstrap the first owner for each existing project, create enabled accounts and grant Owner/Editor/Viewer memberships. Do not enable this mode before configuring the signing key and reviewing the account-onboarding process.

**Security release gate:** service-level project authorization is implemented in the repository, but exact-release CI, manual cross-project browser checks and host configuration remain required before public multi-user exposure. A provider-specific production setup remains pending until the provider is selected.

## 4. Persistent storage and permissions

- Create a private data directory owned by the application service account.
- Place the database on a persistent local block volume, not an ephemeral container layer.
- Place backups in a separate private directory/volume.
- Restrict database and backup permissions to the service/backup operator.
- Confirm the provider's volume persists across deploy/restart before accepting production.
- SQLite should use a single-writer or explicitly coordinated model; do not assume arbitrary network filesystems are safe.

Example Linux directory preparation (adapt paths and owner to the actual service account; review before running):
```bash
sudo install -d -m 700 -o projectcontinue -g projectcontinue /var/lib/project-continue
sudo install -d -m 700 -o projectcontinue -g projectcontinue /var/backups/project-continue
```

## 5. Start, stop, update and rollback

The exact service manager commands depend on the selected host/provider. Do not copy generic stop/restart commands into the live Colab environment.

For an approved host:
1. Record the currently deployed release SHA.
2. Verify a recent backup and its integrity.
3. Deploy the reviewed release using the provider's supported release mechanism.
4. Verify health and login before opening user access.
5. For rollback, redeploy the previous known-good release and retain the current database; do not restore or overwrite the DB unless a separately approved recovery procedure requires it.

## 6. Health verification

- Confirm the provider's process health probe succeeds.
- Confirm HTTPS and certificate validity.
- Confirm unauthenticated requests reach only the sign-in gate.
- Confirm an authorized operator can sign in.
- Confirm database persistence after an approved service restart/redeploy.
- Confirm backup runner succeeds on the host.
- Confirm logs do not contain secrets, credentials or private data.

A local Streamlit process starting successfully is not proof of production readiness.

## 7. Uninstall

On a disposable development machine, stop the local process, deactivate the virtual environment and remove the checkout when no needed work remains. Database and backup data are separate user data: export/verify what must be retained before deleting them. On production, use the provider's approved decommissioning and data-retention process.

## 8. Colab note

Use the existing project notebook/runtime and its established checkout/venv. Do not recreate the runtime, reinstall into or replace the running process, change its live DB path, or restart the current dashboard merely to follow this clean-machine guide.
