# Local setup — senja-os

One-stop guide for getting the repo running on a local machine (human or agent
executor, e.g. Antigravity).

## 1. Access — no fork

This is a single-owner repo. **Do not fork.** Workflow is branch → PR:

```bash
git clone https://github.com/Thib2108/Thib2108-senja-os.git
cd Thib2108-senja-os
git checkout -b <branch-name>   # e.g. sprint-01-surreal-spike
```

Authentication is your normal GitHub login (HTTPS credential helper or SSH).
No tokens or MCP servers are involved locally — plain git.

> If the repo is ever renamed to `senja-os`, old clone URLs keep working via
> GitHub redirects.

## 2. Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.12+ | https://www.python.org or `uv python install 3.12` |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker (optional) | any recent | only needed for the SurrealDB container route |
| SurrealDB (alt.) | latest | `brew install surrealdb/tap/surreal` or `curl -sSf https://install.surrealdb.com \| sh` |

## 3. Install

From the repo root:

```bash
uv sync
```

This resolves the whole uv workspace: `packages/harness_kernel`,
`packages/contracts`, `services/api`.

## 4. Run the tests

```bash
cd services/api
uv run pytest -v
```

Expected without a database: `[memory]` params pass, `[surreal]` params skip,
`test_gates.py` passes.

## 5. Run SurrealDB (for the surreal params + bench)

```bash
docker run --rm -p 8000:8000 surrealdb/surrealdb:latest start --user root --pass root memory
# or: surreal start --user root --pass root memory
```

Then:

```bash
cd services/api
SURREAL_URL=ws://127.0.0.1:8000/rpc uv run pytest -v
```

Env-var convention (defaults): `SURREAL_URL=ws://127.0.0.1:8000/rpc`,
`SURREAL_NS=senja`, `SURREAL_DB=dev`, `SURREAL_USER=root`, `SURREAL_PASS=root`.

## 6. Where things live

| Path | What |
|---|---|
| `AGENTS.md` | Non-negotiable rules for any agent working in this repo — read first |
| `docs/HARVEST.md` | What may be transplanted from the document-studio quarry, and how |
| `docs/sprints/` | Execution briefs (one file per sprint) |
| `packages/harness_kernel` | Loops, gates, binding contract, decision records |
| `packages/contracts` | Edge registry enums, facet contracts |
| `services/api` | Store of record, migrations, ports, pipelines, tests |

## 7. Sprint workflow

1. Read `AGENTS.md`, then the sprint brief in `docs/sprints/`.
2. Branch, execute tasks in order, commit per task (`feat:` / `test:` / `chore:`).
3. Open a PR to `main`; **do not merge** — the architect reviews from the Notion side.
4. Print `=== SPRINT XX REPORT ===` / `=== QUESTION FOR ARCHITECT ===` blocks
   exactly as the brief specifies, for copy-paste back to the architect.
