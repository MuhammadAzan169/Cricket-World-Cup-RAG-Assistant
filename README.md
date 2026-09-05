# 🏏 Cricket World Cup RAG Assistant

A retrieval-augmented chatbot that answers questions about every ICC Cricket World Cup from **2003 to 2023**, backed by hybrid search (dense FAISS embeddings + BM25 sparse retrieval) over cleaned ball-by-ball match data, tournament summaries, player statistics and curated memorable-moments narratives.

This is a **monorepo** with two independently deployable apps:

| Folder      | What it is                                     | Deploys to           |
| ----------- | ---------------------------------------------- | -------------------- |
| `backend/`  | FastAPI RAG API (retrieval + LLM generation)    | **Render** (free plan) |
| `frontend/` | Static site: landing page + chatbot UI          | **Vercel**           |

Locally, a single `app.py` at the repo root runs **both** together.

---

## Table of contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Local installation](#local-installation)
4. [Environment variables](#environment-variables)
5. [Running locally with `app.py`](#running-locally-with-apppy)
6. [Local vs. production behaviour](#local-vs-production-behaviour)
7. [Deploying the backend to Render](#deploying-the-backend-to-render)
8. [Deploying the frontend to Vercel](#deploying-the-frontend-to-vercel)
9. [Render free-plan limitations](#render-free-plan-limitations)
10. [API reference](#api-reference)
11. [Rebuilding the search index](#rebuilding-the-search-index)
12. [Troubleshooting](#troubleshooting)
13. [Repository layout](#repository-layout)

---

## Architecture

```
                       ┌──────────────────────────┐
  Browser ────────────▶│  frontend/  (Vercel)     │
                       │  static HTML/CSS/JS      │
                       └───────────┬──────────────┘
                                   │  fetch(API_BASE_URL + /chat/stream)
                                   ▼
                       ┌──────────────────────────┐
                       │  backend/   (Render)     │
                       │  FastAPI + uvicorn       │
                       └───────────┬──────────────┘
                                   │
             ┌─────────────────────┼─────────────────────┐
             ▼                     ▼                     ▼
     fastembed (ONNX)      FAISS + BM25 index     OpenRouter API
     all-MiniLM-L6-v2      (prebuilt, in repo)    (LLM generation)
     → query embedding     → hybrid retrieval     → final answer
```

The retrieval pipeline: classify the query → hybrid search (dense + BM25) → re-rank → assemble context under a character budget → generate with the LLM, streaming tokens back over SSE.

**API base URL wiring.** The frontend never hardcodes a backend URL in its source. `frontend/js/config.js` is *generated*:

* on Vercel, by `build.mjs` from the `API_BASE_URL` environment variable;
* locally, by `app.py`, pointing at your local backend.

It is gitignored for exactly that reason. If it is missing entirely, the JS falls back to `http://localhost:8000` when served from `localhost`.

---

## Prerequisites

| Tool               | Version   | Needed for                                    |
| ------------------ | --------- | --------------------------------------------- |
| **Python**         | 3.10–3.12 | Backend and `app.py` (3.12 is what Render runs) |
| **Node.js**        | 18+       | *Only* for the Vercel build — not needed locally |
| **Git**            | any       | Cloning / deploying                            |
| **OpenRouter key** | —         | LLM generation — free at <https://openrouter.ai/keys> |

You do **not** need a GPU. You do **not** need Node.js to run the project locally — `app.py` generates the frontend config in Python.

---

## Local installation

```bash
git clone <your-repo-url>
cd Cricket-World-Cup-RAG-Assistant

# 1. Virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. Install ALL local dependencies (includes the local-only cross-encoder)
pip install -r backend/requirements-local.txt

# 3. Configure the backend
cp backend/.env.example backend/.env      # Windows: copy backend\.env.example backend\.env
#    then open backend/.env and set LLM_API_KEY

# 4. Verify the setup
python app.py --check
```

### The two dependency files

| File                             | Contents                                            | Used by                    |
| -------------------------------- | --------------------------------------------------- | -------------------------- |
| `backend/requirements.txt`       | Render-safe set. No torch. Fits in 512MB.            | Render build, Docker image |
| `backend/requirements-local.txt` | The above **plus** `torch` + `sentence-transformers` | Local development          |

`torch` is deliberately kept out of `backend/requirements.txt`: it needs 300–400MB of RAM just to import, which does not fit in Render's free instance.

---

## Environment variables

### Backend — `backend/.env` locally, Render dashboard in production

| Variable                     | Required | Default                        | Notes                                                    |
| ---------------------------- | -------- | ------------------------------ | -------------------------------------------------------- |
| `LLM_API_KEY`                | **Yes*** | —                              | OpenRouter (or any OpenAI-compatible) key                 |
| `OPENROUTER_API_KEY1..N`     | No       | —                              | Optional rotation pool; *any* var with this prefix is auto-discovered and tried in order when one is rate-limited |
| `OPENROUTER_MODEL_1..N`      | No       | —                              | Optional model fallback chain, tried in sorted order      |
| `APP_ENV`                    | No       | `render` on Render, else `local` | Selects the runtime profile (see below)                 |
| `LLM_PROVIDER`               | No       | `openrouter`                   |                                                          |
| `LLM_MODEL`                  | No       | `openai/gpt-oss-20b:free`      |                                                          |
| `LLM_BASE_URL`               | No       | `https://openrouter.ai/api/v1` |                                                          |
| `LLM_MAX_TOKENS`             | No       | `3000`                         |                                                          |
| `LLM_TEMPERATURE`            | No       | `0.3`                          |                                                          |
| `LLM_MAX_KEYS_PER_MODEL`     | No       | `6`                            | Caps retry fan-out for one question                       |
| `LLM_REQUEST_BUDGET_SECONDS` | No       | `45`                           | Wall-clock cap for one generation                         |
| `ALLOWED_ORIGINS`            | No       | `*`                            | Comma-separated CORS origins, no trailing slash. **Set this in production.** |
| `PORT`                       | No       | `8000`                         | Render injects this automatically                         |
| `CROSS_ENCODER_RERANK`       | No       | follows `APP_ENV`              | `true` locally, `false` on Render                         |
| `EMBEDDING_MODEL`            | No       | `sentence-transformers/all-MiniLM-L6-v2` | Served via fastembed/ONNX                |
| `KB_LOG_LEVEL`               | No       | `INFO`                         |                                                          |

\* At least one of `LLM_API_KEY` or `OPENROUTER_API_KEY*` must be set — the backend refuses to start without a key.

### Frontend — Vercel dashboard

| Variable       | Required | Notes                                                             |
| -------------- | -------- | ----------------------------------------------------------------- |
| `API_BASE_URL` | Yes      | Your Render URL, e.g. `https://cricket-rag-api.onrender.com`, **no trailing slash** |

Not needed locally — `app.py` writes the local value for you.

> **Secrets never live in source.** `.env` files are gitignored; only `.env.example` templates are committed. The frontend has no secrets at all — everything it receives ships to the browser, which is why the LLM key stays server-side.

---

## Running locally with `app.py`

```bash
python app.py
```

That single command:

1. Runs a preflight check (dependencies, prebuilt index, API key).
2. Writes `frontend/js/config.js` pointing at your local backend.
3. Starts the FastAPI backend with `APP_ENV=local` (uvicorn, `backend/` as cwd).
4. Waits for `/health` to come up — the first run downloads the embedding model.
5. Serves the frontend as a static site, mirroring the Vercel rewrites (`/chat-page`, clean URLs).
6. Opens your browser.

```
  Web app   http://localhost:5500/
  Chatbot   http://localhost:5500/chatbot.html
  API       http://localhost:8000
  API docs  http://localhost:8000/docs
```

Press **Ctrl+C** to stop everything. If 8000 or 5500 are busy, `app.py` moves to the next free port automatically.

### Options

| Flag                    | Effect                                              |
| ----------------------- | --------------------------------------------------- |
| `--check`               | Run the preflight checks and exit                    |
| `--no-browser`          | Don't open a browser tab                             |
| `--backend-port 8001`   | Move the API                                         |
| `--frontend-port 3000`  | Move the web app                                     |
| `--backend-only`        | API only                                             |
| `--reload`              | Auto-reload the backend on code changes              |

### Running the parts separately

```bash
# Backend only
cd backend && uvicorn server:app --reload --port 8000

# Backend CLI (no browser at all)
cd backend && python main.py
cd backend && python main.py --query "Who won the 2011 World Cup?"
cd backend && python main.py --status

# Frontend only (needs Node.js)
cd frontend && npm run dev
```

---

## Local vs. production behaviour

The same code runs in both places; `config.py` picks a profile from `APP_ENV`, which defaults to `render` when Render's `RENDER=true` is present and `local` everywhere else.

| Capability                          | Local (`APP_ENV=local`)                        | Render (`APP_ENV=render`)                    |
| ----------------------------------- | ---------------------------------------------- | -------------------------------------------- |
| Dense embeddings                    | ✅ local model — fastembed ONNX MiniLM-L6-v2   | ✅ same local model (small enough to fit)    |
| BM25 sparse retrieval               | ✅                                              | ✅                                            |
| **Cross-encoder re-ranker** (torch) | ✅ enabled — highest answer quality             | ❌ disabled — falls back to metadata re-rank  |
| LLM generation                      | 🌐 OpenRouter API                               | 🌐 OpenRouter API                             |
| Index rebuild (`POST /build`)       | ✅ full rebuild from `backend/Cricket Data/`    | ⚠️ works but is slow and can hit the RAM cap  |
| Depends on the deployed backend     | ❌ never — fully self-contained                 | —                                            |

Embeddings run **locally in both environments** — fastembed serves a quantized ONNX export through onnxruntime, with no torch dependency, so it fits comfortably in 512MB. Only the cross-encoder re-ranker, which genuinely needs torch, is local-only. When it is off, retrieval degrades gracefully to the metadata-boost re-ranker rather than failing.

To reproduce the production profile locally:

```bash
cd backend && APP_ENV=render uvicorn server:app --port 8000
```

Confirm which profile is live at any time:

```bash
curl https://your-service.onrender.com/health
# {"status":"healthy","environment":"render","cross_encoder":false,...}
```

---

## Deploying the backend to Render

`backend/render.yaml` documents the exact service settings and the full environment-variable list.

### Option A — Web service from the dashboard (recommended)

1. Push this repo to GitHub.
2. Render dashboard → **New +** → **Web Service** → select the repo.
3. Configure:

   | Setting           | Value                |
   | ----------------- | -------------------- |
   | Root Directory    | `backend`            |
   | Runtime           | `Docker`             |
   | Dockerfile Path   | `backend/Dockerfile` |
   | Health Check Path | `/health`            |
   | Instance Type     | `Free`               |

4. Add the environment variables from the table above. At minimum:
   * `LLM_API_KEY` — your OpenRouter key
   * `ALLOWED_ORIGINS` — your Vercel URL(s), comma-separated, no trailing slash
   * `APP_ENV=render`
5. Deploy. The first build takes ~5–10 minutes (the Docker image pre-downloads the embedding model).

### Option B — Render Blueprint

Blueprints are only read from the **repository root**, so copy `backend/render.yaml` to `./render.yaml` and add `rootDir: backend` under the service. Then: **New +** → **Blueprint** → select the repo, and fill in the variables marked `sync: false`.

### Option C — Native Python runtime (no Docker)

| Setting        | Value                                          |
| -------------- | ---------------------------------------------- |
| Root Directory | `backend`                                      |
| Build Command  | `pip install -r requirements.txt`               |
| Start Command  | `uvicorn server:app --host 0.0.0.0 --port $PORT` |

Also set `APP_ENV=render`. This builds faster but re-downloads the embedding model on every cold start; the Docker path bakes it into the image instead.

### Verify

```bash
curl https://your-service.onrender.com/health
curl -X POST https://your-service.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Who won the 2011 World Cup?"}'
```

---

## Deploying the frontend to Vercel

1. Vercel dashboard → **Add New** → **Project** → import this repo.
2. **Root Directory: `frontend`** ← this is the important step in a monorepo.
3. Framework Preset: **Other**. Vercel picks up `frontend/vercel.json`, which already sets:
   * Build Command `node build.mjs`
   * Output Directory `.`
   * Clean URLs, the `/chat-page` rewrite, and security headers.
4. Environment Variables → add:

   | Name           | Value                                       | Environments                     |
   | -------------- | ------------------------------------------- | -------------------------------- |
   | `API_BASE_URL` | `https://your-service.onrender.com`         | Production, Preview, Development |

5. Deploy.
6. **Go back to Render** and set `ALLOWED_ORIGINS` to your Vercel domain(s):

   ```
   https://your-app.vercel.app,https://your-app-git-main-you.vercel.app
   ```

   Then redeploy the Render service. Skipping this is the single most common cause of a working backend that the deployed frontend can't call.

---

## Render free-plan limitations

| Limitation                  | What it means                                                     | Mitigation                                                          |
| --------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| **512MB RAM**               | torch/sentence-transformers don't fit                             | `APP_ENV=render` disables the cross-encoder; fastembed ONNX is used instead |
| **Spins down after 15 min idle** | First request after a nap takes 30–60s while the container boots | The UI shows a loading state; the Docker image pre-bakes the model so the wake-up is as short as possible |
| **Shared CPU**              | Generation is slower than local                                    | `OMP_NUM_THREADS=1`, single uvicorn worker, capped retry fan-out     |
| **Ephemeral disk**          | `history.txt` and any rebuilt index vanish on restart              | The index is committed to the repo and ships inside the image        |
| **750 instance-hours/month**| One always-on free service would exceed it                         | The idle spin-down keeps usage under the cap                         |
| **Build timeouts**          | Very large images can fail to build                                | No compilers in the image; wheels only                               |

**Do not set `APP_ENV=local` on Render** — it enables the torch code path, and the instance will be OOM-killed.

---

## API reference

| Method | Path             | Purpose                                                |
| ------ | ---------------- | ------------------------------------------------------ |
| `GET`  | `/health`        | Health check + active environment profile              |
| `GET`  | `/status`        | Index stats, model info, conversation state            |
| `POST` | `/chat`          | `{"question": "..."}` → full answer with sources       |
| `POST` | `/chat/stream`   | Same, streamed as SSE (`meta`, `token`, `done` events) |
| `POST` | `/build`         | Rebuild the FAISS + BM25 index                         |
| `POST` | `/clear-history` | Clear conversation history                             |
| `GET`  | `/docs`          | Interactive OpenAPI docs                               |

---

## Rebuilding the search index

The prebuilt index (`backend/index/`) is committed, so a fresh clone works immediately. Rebuild it after changing anything under `backend/Cricket Data/`:

```bash
cd backend
python main.py --build-index
```

Then commit the regenerated `backend/index/` files so Render and Docker pick them up. Rebuilding **on** Render is not recommended on the free plan.

---

## Troubleshooting

**`ValueError: Missing API key` on startup**
No `LLM_API_KEY` or `OPENROUTER_API_KEY*` was found. Locally, check `backend/.env` exists and has a real key (not `your-api-key-here`). On Render, check the service's Environment tab and redeploy — new variables need a redeploy.

**CORS error in the browser console on the deployed site**
`ALLOWED_ORIGINS` on Render doesn't include your Vercel origin. Set it to the exact origin — scheme included, **no trailing slash** — and redeploy. Preview deployments have their own domains, so add those too, or leave it unset while debugging (defaults to `*`).

**The deployed frontend calls `localhost:8000`**
`API_BASE_URL` isn't set on Vercel, or was added after the last build. Set it, then **redeploy** — it is baked in at build time, not read at runtime.

**First request to the deployed API takes 30–60 seconds, or times out once**
Free-plan cold start. The instance spun down after 15 idle minutes. Retry; the second request is fast. The chat UI handles this: the status pill shows **Offline**, the typing indicator switches to “the server may be waking up” after 10s, and a failed send returns a “may be waking up — try again” message rather than an error dump.

**The chat bubble appears but stays empty**
Should not happen — the streaming client keeps its render state per message, cancels any queued repaint when a message completes, and falls back to the non-streaming `/chat` endpoint if the SSE connection drops or goes 90s without data. If you do see it, check the browser console and the Render logs for the LLM provider error underneath.

**Render deploy gets OOM-killed / "Ran out of memory"**
Something enabled the torch path. Confirm `CROSS_ENCODER_RERANK=false` and `APP_ENV=render`, and that the build used `backend/requirements.txt` and not `requirements-local.txt`.

**`ModuleNotFoundError: No module named 'faiss'` (or fastembed, rank_bm25)**
Dependencies aren't installed in the active interpreter. Activate your venv and run `pip install -r backend/requirements-local.txt`. `python app.py --check` reports exactly what's missing.

**First local run stalls for a minute at "Loading embedding model"**
It's downloading MiniLM (~80MB) from the Hugging Face Hub. It is cached afterwards. On Windows you may see a harmless symlink warning, and a CUDA provider warning from onnxruntime — both are safe to ignore; the CPU provider is used.

**`Port 8000 is already in use`**
`app.py` shifts to the next free port automatically. To pin one: `python app.py --backend-port 8001`.

**Chatbot answers "the server is still starting up"**
The index or embedding model hasn't finished loading. Wait for `/health` to return 200, or check `/status` for vector and chunk counts.

**Empty or irrelevant answers**
Check `GET /status` — `total_vectors` should be ~1400. If it's 0, the index didn't load; rebuild with `python main.py --build-index` from `backend/`.

---

## Repository layout

```
.
├── app.py                      ← run the whole thing locally
├── .gitignore
├── README.md
│
├── backend/                    ← deploy this folder to Render
│   ├── server.py               FastAPI app + endpoints
│   ├── main.py                 CricketChatbot: pipeline, LLM rotation, CLI
│   ├── config.py               all tunables + environment detection
│   ├── embeddings_utils.py     EmbeddingsManager: hybrid search + re-rank
│   ├── Embedding/              chunking, embeddings, ingestion, vector store
│   ├── Cricket Data/           source dataset (matches, stats, narratives)
│   ├── index/                  prebuilt FAISS + BM25 index (committed)
│   ├── scripts/                dataset/eval helper scripts
│   ├── Dockerfile              Render-free-plan image
│   ├── render.yaml             Render service definition
│   ├── requirements.txt        Render-safe deps
│   ├── requirements-local.txt  + local-only torch cross-encoder
│   ├── docs/                   system documentation
│   └── .env.example
│
├── frontend/                   ← deploy this folder to Vercel
│   ├── index.html              landing page
│   ├── chatbot.html            chat UI
│   ├── js/script.js            shared logic + API base resolution
│   ├── js/chatbot.js           SSE streaming chat client
│   ├── js/config.js            GENERATED — gitignored
│   ├── assets/css/style.css
│   ├── build.mjs               writes js/config.js from API_BASE_URL
│   ├── vercel.json
│   ├── package.json
│   ├── docs/                   UI guide
│   └── .env.example
```

---

## License

Educational / portfolio project. Cricket data is derived from publicly available ICC Cricket World Cup records.
