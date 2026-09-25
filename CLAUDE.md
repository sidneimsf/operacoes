# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Internal operations-management system for a group of 4 facility-services companies (CORDSUL, KRETZER, STAR SUL, FLC) serving ~160 clients. Replaces WhatsApp/spreadsheet chaos between the back office (`escritorio`) and field supervisors (`supervisor`) with a single system of record: chamados (tickets), colaboradores (staff), custos diários (expense reimbursement), estoque (EPI/uniform stock), veículos, ASOs, and more. Portuguese throughout — see "Language and naming" below. Production: `operacoes.solarsync.com.br`.

**`README.md` is out of date** — it describes an early version of the product (a single-module ticketing app). The real system has grown substantially since (main.py alone is ~4700 lines across ~20 feature areas). Trust the code over the README for anything about scale, routes, or feature scope; the README's sections on the core chamado lifecycle (§3), auth model (§2), and dev/deploy mechanics (§8-10) are still accurate and worth reading for onboarding narrative.

## Architecture

Monolithic FastAPI app, no frontend build step — `app/static/` is served as-is.

```
Browser → nginx (VPS, port 80) → 127.0.0.1:8002 → container "app" (uvicorn, FastAPI, port 8000) → container "db" (Postgres 16, 127.0.0.1:5433)
```

- **Backend**: Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 (`Mapped`/`mapped_column` style, synchronous), Postgres 16, JWT auth (PyJWT/HS256) + bcrypt.
- **Frontend**: plain HTML/CSS/JS, no framework, no bundler, no npm. One page = one `.html` + one `.js` of the same name in `app/static/`.
- **Background jobs**: APScheduler `BackgroundScheduler` inside the app process (`app/main.py`), four cron jobs — ASO expiry alerts (08:00), pending-reimbursement alerts (19:00), probation-period alerts (08:10), and the weekly CRM digest (Mondays 08:20). Each job opens its own `SessionLocal()`.
- **File uploads**: stored on disk under `uploads/<area>/...` (colaboradores, custos_diarios, chamados, cronogramas), persisted via the `uploads_data` Docker volume — not in the DB, not in git.
- **PDF/Excel generation**: `folha_ponto.py` (reportlab) generates timesheets; several `/relatorios-dados/*` endpoints export via `openpyxl`.

### Repository map

```
app/
  main.py          # ALL routes (pages + API) — one file, grouped by "# ---" section comments
  models.py        # SQLAlchemy tables (~23 model classes)
  schemas.py       # Pydantic request/response models
  database.py      # engine, SessionLocal, get_db()
  security.py      # password hashing + JWT issue/decode
  init_db.py       # Base.metadata.create_all() — new tables only
  seed_clientes.py # seeds the 4 empresas + 160 clientes
  migrar_*.py      # one hand-written, idempotent migration script per schema change (no Alembic)
  alertas_*.py     # the background-job bodies (ASO, custos, experiência, crm)
  crm_saude.py     # CRM engine: per-client health score (0-100), contract alerts, portfolio insights - shared by /crm-dados/* and alertas_crm.py
  resumo_dia.py    # daily operations digest (CRM tab "Resumo do dia"): crosses the day's records per client, compares with the same weekday of the last 4 weeks; dates are Brasilia (UTC-3)
  resumo_dia_pdf.py # reportlab PDF of that digest
  email_alertas.py # SMTP sending helper shared by the alertas_* jobs
  folha_ponto.py   # timesheet PDF generation
  static/          # one .html + .js per screen, shared shell.js, single style.css
```

### Request flow / permission model

Every authenticated route depends on `usuario_atual` (decodes the JWT, loads the `Usuario`, checks `ativo`). Three layers of authorization sit on top of that, and routes pick whichever applies:

1. **`exigir_papel(*papeis)`** — hard role gate. Only two roles exist: `supervisor` and `escritorio`.
2. **`exigir_modulo(modulo)`** — the module-permission system (`MODULOS_PERMISSAO` in `main.py`). Each module (veiculos, asos, usuarios, criar_cliente, criar_colaborador, relatorios, estoque, mapa_servico, excluir_registros, crm) has a default (`padrao_escritorio_apenas` → escritorio-only, otherwise anyone logged in) that a `UsuarioPermissao` row can override per-user. Check with `tem_permissao(db, usuario, modulo)`; override always wins over the default.
3. **`exigir_super_admin`** — gates `/admin/permissoes*` (managing the overrides themselves); checks `Usuario.super_admin`.

The frontend mirrors module gating in `shell.js`'s `NAV_ITEMS` (`moduloPermissao` / `apenasSuperAdmin` keys hide nav items), but the backend check is what actually matters — never rely on the frontend hide alone when adding a protected route.

Two distinct "user" concepts, don't conflate them:
- **`Usuario`** — logs into the app (supervisor or escritorio).
- **`Colaborador`** — operational staff member tied to a `Cliente`. Never logs in; exists as a record for timesheets/documents/events.

### Routing convention

FastAPI serves both HTML pages and JSON from the same app, no `/api` prefix. Where a pretty path is already used by a page, the data endpoint gets a **`-dados`** suffix (e.g. `/clientes` = page, `/clientes-dados` = JSON). Endpoints with no page counterpart (`/empresas`, `/supervisores`) skip the suffix. Pages are `include_in_schema=False` so `/docs` (Swagger) shows only the real API.

### Chamado (ticket) lifecycle

The oldest and most load-bearing flow — three rules are enforced in the backend, not just convention:

1. `PATCH /chamados-dados/{id}` explicitly refuses `status: "finalizado"` — finishing a ticket only happens via `POST /chamados-dados/{id}/finalizar`, which requires the closing checklist.
2. The checklist has conditional-required fields (marking "houve pendência" or "enviou documento" makes the matching detail field required).
3. Finalizing resets `confirmacao_vista` to `false`; the ticket then shows on the *opener's* dashboard until they hit "Confirmar recebimento" (`POST /chamados-dados/{id}/confirmar`). This confirmation step is what closes the communication loop.

`TIPOS_CHAMADO` / `STATUS_CHAMADO` / `PRIORIDADES_CHAMADO` are constants at the top of `main.py`, served to the frontend via `GET /chamados-tipos` — never hardcode these lists in JS.

### Frontend shell

Every screen loads `app/static/shell.js` before its own script. `Shell.montar(paginaAtiva, titulo)` draws the sidebar (hiding nav items the user's role/module permissions can't see), topbar, and the "+ Abrir chamado" button, and redirects to `/login` if there's no session — call it first thing in every page's JS. `Shell.chamarApi(caminho, opcoes)` is the **only** sanctioned way to call the API: it attaches the bearer token, auto-logs-out on 401, and wraps errors as `Error` with `.status`/`.detalhe`. Session lives in `localStorage` under `operacoes_auth` (`access_token`, `id`, `nome`, `papel`), token valid 7 days (see `security.py`, `JWT_EXPIRA_HORAS`).

## Commands

No test suite, no linter, no npm — everything runs in Docker.

```bash
# start/rebuild after ANY change (no volume mount, no --reload — the image must be rebuilt)
docker compose up -d --build app

docker compose logs -f app              # tail logs
docker compose exec app bash            # shell in the container
docker compose exec app python init_db.py            # create new tables (does NOT alter existing ones)
docker compose exec app python <migrar_algo>.py       # run one specific migration
docker compose exec -it app python criar_usuario.py   # create a user (interactive)
docker compose down                     # stop (db volume persists)
docker compose down -v                  # also wipes the db volume — destructive, don't do it casually
```

Local URLs: app `http://localhost:8002/login`, Swagger `http://localhost:8002/docs`, Postgres `localhost:5433`.

Deploy (VPS, manual): `git pull origin main && docker compose up -d --build`, then run any new `migrar_*.py` by hand.

## Schema changes

There is no Alembic. `init_db.py` only creates tables that don't exist yet. **Adding/changing a column on an existing table requires a new hand-written `migrar_<algo>.py`**, idempotent (`ADD COLUMN IF NOT EXISTS` style — see `migrar_visita_acoes.py` for the minimal pattern) and non-destructive, committed in the same commit as the `models.py` change. This is the single most common way to break the app if skipped — a `models.py` edit alone never reaches the database.

## Language and naming conventions

- **Everything is Portuguese**: variables, functions, routes, tables, columns (`abrir_chamado`, `usuario_atual`, `chamados-dados`, `criado_em`).
- **Code/comments/docstrings are ASCII, no accents** (`"Cria um usuario de forma interativa"`). User-facing strings shown in the UI use normal accented Portuguese (`"Ocorrências"`, `"Não foi possível carregar"`).
- Business errors are raised as `HTTPException(detail=...)` in Portuguese — the frontend shows `detalhe` straight to the user, so write it as a real sentence.
- All routes live in `main.py`, grouped under `# ---` section-comment banners (e.g. `# Custos diarios (reembolso de despesas dos supervisores)`) — no `APIRouter` split yet. When adding a feature area, follow the existing section-comment convention rather than introducing a new file/router pattern.
- Each resource has a `serializar_<coisa>()` helper (e.g. `serializar_chamado`, `serializar_cliente`) used everywhere that resource is returned, so all screens get the same shape — always route new response-building through it rather than building dicts ad hoc.
- Dependencies are pinned exactly in `requirements.txt` (`fastapi==0.115.0`), no ranges.

## Environment variables

Defined in `.env` (gitignored, never commit it), modeled by `.env.example` — update the example in the same commit whenever you add a variable. Notable ones beyond DB/JWT: `SMTP_*` + `ALERTA_ASO_EMAILS` / `REEMBOLSO_EMAILS` / `ALERTA_EXPERIENCIA_EMAILS` / `ALERTA_CRM_EMAILS` feed the background alert jobs.

## Git workflow

Commit directly on `main` and push to `origin main` — no feature branches, no PRs (single developer; the VPS deploys from `main`). Commit messages: imperative verb, Portuguese, no accents, describing the effect not the file (e.g. `Adiciona checklist de finalizacao e confirmacao do escritorio`). Never commit `.env`, DB dumps, or real client data. A `models.py` change ships with its `migrar_*.py` in the same commit; a new env var ships with its `.env.example` line in the same commit.
