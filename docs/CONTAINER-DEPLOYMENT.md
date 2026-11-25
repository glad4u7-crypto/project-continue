# Project Continue — Container Deployment

This is the provider-neutral production packaging for a single-host Docker Engine + Docker Compose deployment. It is a reproducible deployment target; it does not provision a cloud account, domain, TLS certificate, external backup destination, or monitoring service.

## Runtime design

- Python 3.11 slim image; Streamlit listens on container port 8501.
- Runs as unprivileged UID/GID 10001.
- Root filesystem is read-only; /tmp is a bounded tmpfs.
- Linux capabilities are dropped and privilege escalation is disabled.
- SQLite lives on the named persistent volume project_continue_data.
- Container health is checked through Streamlit's /_stcore/health endpoint.
- Host port binds to loopback by default. A trusted HTTPS reverse proxy must be configured before remote access.
- The application remains SQLite-backed. The optional PostgreSQL adapter is not selected by this deployment.

## Host prerequisites

- Linux host with Docker Engine and Docker Compose v2.
- Persistent local storage with enough capacity for the database and backups.
- A trusted reverse proxy / TLS termination layer for remote access.
- Host secret storage and a separate private backup destination.
- An operator-controlled domain, firewall and monitoring policy.

SQLite must use a durable local filesystem and a single-writer/coordinated access model. Do not mount the database on an arbitrary network filesystem or share one SQLite file across independent application replicas.

## First deployment

Run these commands on the selected production host, not in the user's Colab runtime:

```bash
git clone https://github.com/glad4u7-crypto/project-continue.git
cd project-continue
git checkout main
cp .env.production.example .env.production
chmod 600 .env.production
```

Edit .env.production using a secure editor. Set a unique administrator email and a password of at least 12 characters. Generate SESSION_SIGNING_KEY locally with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Store the generated value directly in the host secret manager or protected .env.production file. Do not paste it into chat, shell history, Git, or logs. Keep AUTHORIZATION_ENFORCED=false for initial administrator-only setup.

Build and start:

```bash
docker compose build --pull
docker compose up -d
docker compose ps
docker compose logs --tail=100 app
```

Verify the local health endpoint:

```bash
curl --fail http://127.0.0.1:8501/_stcore/health
```

The first container initialization creates the initial administrator only when the identity table has no users and both bootstrap values are present. After the first successful login, remove INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD from .env.production, then recreate the container during an approved maintenance window. The signing key must remain stable across deployments or existing sessions will be invalidated.

## Network and HTTPS

The Compose service binds to 127.0.0.1:8501 by default and is not directly exposed to the public network. Configure a trusted reverse proxy on the host to terminate HTTPS and proxy to the loopback port. Restrict inbound firewall access to the proxy's TLS port. Do not change the bind address to 0.0.0.0 unless the host firewall and TLS architecture have been reviewed.

## Enable project membership mode

Only after creating accounts and assigning each project's membership through the application's approved operator process, set AUTHORIZATION_ENFORCED=true. The current repository enforces membership in service paths; browser acceptance across two projects and Owner/Editor/Viewer/Non-member identities is still a required release check. Never enable membership mode without provisioning users and memberships first.

## Persistence and backup

The named Docker volume project_continue_data holds the SQLite database across container replacement. Confirm the volume exists and is backed up by the host's independent backup system. Do not treat a Docker volume as a backup.

Set PROJECT_CONTINUE_BACKUP_DIR for the host scheduler and invoke python scripts/run_verified_backup.py from a controlled backup job. The backup destination must be separate from the application volume, access-controlled, encrypted and preferably off-host. Schedule and alerting are host responsibilities; Compose does not silently create a scheduler.

## Upgrade and rollback

1. Record the currently deployed release SHA and confirm a recent verified backup.
2. Fetch and review the intended release.
3. Build the new image and run the health check.
4. Recreate only the container while retaining project_continue_data.
5. Verify sign-in, database persistence and logs.
6. If rollback is needed, redeploy the previous image while preserving the database. Database restore is a separate, explicitly approved recovery action.

Commands such as docker compose down -v delete the named persistent volume and must never be used as a routine update or rollback step.

## Security notes

- Never commit .env.production; it is ignored by Git.
- Never bake secrets into Docker build arguments or image layers.
- Keep the signing key stable and secret.
- Keep the app loopback-bound behind HTTPS.
- Use a unique bootstrap administrator password and remove bootstrap variables after first use.
- Keep the SQLite volume private and restrict host access.
- Pin and review image/base-image updates as part of release maintenance.
- The deployment is single-instance; horizontal scaling is not supported by this SQLite design.

## Verification and evidence

The repository CI builds the image and starts it with synthetic credentials against a temporary volume, then checks the Streamlit health endpoint. That verifies image build and container startup in CI, not a real host's DNS, HTTPS, persistent-volume durability, backup schedule, alerting or restore drill.

Record the exact deployed Git SHA, image digest, host, HTTPS result, volume test, backup timestamp, restore-drill result and operator approval in the release record.
