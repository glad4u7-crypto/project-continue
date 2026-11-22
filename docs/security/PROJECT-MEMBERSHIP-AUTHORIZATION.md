# Project Membership Authorization

## Enforcement modes

- `APP_ENV=production` always requires a signed-in administrator by default.
- Set `AUTHORIZATION_ENFORCED=true` to enable signed-in project members (Owner, Editor, Viewer) in production or non-production environments.
- Membership enforcement requires `SESSION_SIGNING_KEY` with at least 32 bytes of high-entropy secret material. Do not commit this value.
- If `AUTHORIZATION_ENFORCED` is not enabled outside production, the legacy single-user development/Colab experience remains unchanged. Do not expose that mode to untrusted users or the public internet.

## First-time setup

1. Configure `SESSION_SIGNING_KEY`.
2. On a fresh database only, configure `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` before first startup. The password must be at least 12 characters.
3. Sign in as the administrator.
4. Open each pre-existing project and use **Bootstrap my account as first project owner** if it has no owner yet.
5. In **Project access and members**, create enabled Owner/Editor/Viewer accounts as needed, then grant each account membership in the project.
6. Remove or rotate temporary credentials through the host's secret-management process after onboarding.

## Permission matrix

| Operation | Owner | Editor | Viewer | Non-member | Admin |
|---|---:|---:|---:|---:|---:|
| Read project, tasks, memory, checkpoints, notifications | Yes | Yes | Yes | No | Yes |
| Create/update tasks, dependencies, memory, checkpoints, sessions and decisions | Yes | Yes | No | No | Yes |
| Generate AI advice | Yes | Yes | Yes | No | Yes |
| Decide own AI approval | Yes | Yes | No | No | Yes |
| Edit project metadata, archive/restore, manage members | Yes | No | No | No | Yes |
| Create projects | Yes | No | No | No | Yes |
| Global scheduler controls and unscoped automation alerts | No | No | No | No | Yes |
| GitHub integration panel | No | No | No | No | Yes |

Project and resource scope is derived from canonical database rows. Caller-supplied project identifiers are not accepted as proof of resource ownership. Signed principals are HMAC-verified and rechecked against the live enabled account record on each authorization decision. AI approval requests are bound to their originating account and project.

## Operational boundary

This change adds repository code and CI tests only. It does not change the live database, configure host secrets, deploy the app, restart Streamlit, or reboot a Colab runtime. Enable membership mode and complete account onboarding on the target host before allowing non-admin users to connect.
