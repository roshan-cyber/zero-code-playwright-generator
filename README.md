# Zero‑Code Playwright Generator

AI‑powered **E2E test generation** from natural language.  
Provide a URL, optional authentication details, and a plain‑English description of the test flow – the system returns a ready‑to‑run **Page Object Model (POM)** and a **pytest / Playwright test suite** in the language of your choice.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Natural‑language test authoring** | Write steps like “login, click *New Order*, fill form, submit, verify success toast”. |
| **Multi‑language output** | TypeScript, JavaScript, Python, Java (Playwright Test / pytest / JUnit). |
| **Two‑step workflow** | 1️⃣ Authenticate (optional) → 2️⃣ Provide target page & instructions → **Generate**. |
| **Authentication toggle** | “Authentication Required” (default) or “No Authentication (Public Site)”. |
| **Environment & Role** | Dev / QA / UAT + MCS / PAT / Manager / BA – influences generated data. |
| **Two‑pass AI navigation** | LLM first selects a selector for a pre‑action (e.g., “click *New Order* tab”), Playwright clicks it, then the final DOM is captured. |
| **High‑quality locators** | Strict selector ladder: `id → label → visible text → name → placeholder → data‑testid → role → class → xpath`. No hallucinated `getByTestId`. |
| **Dark / Light theme** | One‑click toggle persisted for the session. |
| **Copy‑to‑clipboard** | One‑click copy for each generated file. |
| **Docker‑ready** | `docker compose up --build` spins both services. |
| **CI‑ready** | FastAPI + Vite + Playwright – runs in GitHub Actions, GitLab CI, Azure Pipelines, etc. |

---

## 📦 Repository Layout

```
.
├── backend/                # FastAPI service
│   ├── main.py            # API routes (/create-session, /generate-pom)
│   ├── models.py          # Pydantic request/response schemas
│   ├── playwright_service.py   # DOM extraction, two‑pass navigation
│   ├── prompts.py         # System + user prompts for Nemotron‑3‑Ultra
│   ├── requirements.txt   # Python deps
│   ├── Dockerfile
│   └── .env.example
├── frontend/               # React + Vite SPA
│   ├── src/
│   │   ├── components/
│   │   │   └── ZeroCodeTestGenerator.jsx   # Main UI
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
* **Python 3.11+**  
* **Node 18+ / npm 9+**  
* **Playwright browsers** (`playwright install chromium`)  
* **NVIDIA API key** for Nemotron‑3‑Ultra (get it from <https://integrate.api.nvidia.com>)

---

### 1️⃣ Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

# copy example env and add your key
cp .env.example .env
# edit .env → NVIDIA_API_KEY=sk‑xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# start API (no --reload in production)
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

API will be at **http://localhost:8000** (health check `GET /health`).

---

### 2️⃣ Frontend

```bash
cd frontend
npm ci          # clean install
npm run dev
```

Vite dev server at **http://localhost:5173** (proxies `/api/*` → `http://localhost:8000`).

Open the UI, fill the form, click **Establish Active Session** (or choose *No Authentication*), then **Generate … Suite**. The right panel shows **Page Objects** and **Test Suite** tabs with syntax highlighting and copy buttons.

---

## 🐳 Docker (All‑in‑One)

```bash
# from repo root
docker compose up --build
```

* Backend → `http://localhost:8000`  
* Frontend → `http://localhost:5173`

Set `NVIDIA_API_KEY` in `.env` (or via `docker compose` environment).

---

## ☁️ Deployment (Railway Backend + Vercel Frontend)

This project is deployed as:

* **Backend** on Railway (recommended for Playwright runtime reliability)
* **Frontend** on Vercel

### 1) Deploy backend on Railway

1. Create a new Railway service from this repo.
2. Configure service settings:
   * **Root Directory**: `backend`
   * **Builder**: `Dockerfile`
   * **Dockerfile Path**: `Dockerfile`
3. In Railway Variables, set at least:
   * `NVIDIA_API_KEY=<your_key>` (or use BYOK from UI)
4. Deploy and verify health:

```bash
curl https://<your-railway-domain>/health
```

Expected response:

```json
{"status":"ok"}
```

### 2) Deploy frontend on Vercel

1. Create/import frontend project in Vercel from the same repo.
2. Configure:
   * **Root Directory**: `frontend`
   * **Framework Preset**: `Vite`
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
3. Add env var in Vercel frontend project:
   * `VITE_API_BASE_URL=https://<your-railway-domain>`

This makes the SPA call Railway directly for API requests (`/create-session`, `/generate-pom`) in production.

### 3) Optional Vercel rewrite mode

If you prefer edge rewrites instead of direct API base URL, keep `frontend/vercel.json` pointing to your Railway domain. For this repo, direct `VITE_API_BASE_URL` is recommended.

### 4) Common deployment checks

* Backend health returns `{"status":"ok"}`.
* Frontend and backend URLs are both public.
* Frontend env var `VITE_API_BASE_URL` matches Railway domain exactly (no trailing slash required).

### 5) Deployment commands (copy/paste)

Push latest code:

```bash
git add .
git commit -m "chore: deployment updates"
git push origin main
```

Verify Railway backend:

```bash
curl -i https://<your-railway-domain>/health
```

Expected:

```text
HTTP/2 200
{"status":"ok"}
```

Probe API endpoints quickly (422 is OK for empty payload and confirms routing):

```bash
curl -i -X POST https://<your-railway-domain>/generate-pom -H "Content-Type: application/json" -d "{}"
curl -i -X POST https://<your-railway-domain>/create-session -H "Content-Type: application/json" -d "{}"
```

Optional frontend route smoke test (if using Vercel rewrites):

```bash
curl -i -X POST https://<your-frontend-domain>/api/generate-pom -H "Content-Type: application/json" -d "{}"
curl -i -X POST https://<your-frontend-domain>/api/create-session -H "Content-Type: application/json" -d "{}"
```

PowerShell equivalents:

```powershell
Invoke-RestMethod https://<your-railway-domain>/health
Invoke-WebRequest -Method Post -Uri https://<your-railway-domain>/generate-pom -ContentType "application/json" -Body "{}"
Invoke-WebRequest -Method Post -Uri https://<your-railway-domain>/create-session -ContentType "application/json" -Body "{}"
```

---

## 🧪 Running Tests

```bash
# Backend unit tests (pytest)
cd backend
pytest -q

# Frontend lint / type‑check
cd frontend
npm run lint
```

---

## 📚 API Reference (excerpt)

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/create-session` | POST | `{environment, role, login_url, username, password}` | Performs login, returns `{status:"success", message:"Session verified"}`. |
| `/generate-pom` | POST | `{environment, role, language, login_url?, username?, password?, target_url, instructions}` | Returns `{pom_code, test_code}`. If `login_url` omitted → public‑site flow. |
| `/health` | GET | – | `{ "status": "ok" }` |

All request/response bodies are JSON. Errors use standard FastAPI validation format.

---

## 🔧 Configuration

| Variable | Location | Purpose |
|----------|----------|---------|
| `NVIDIA_API_KEY` | `backend/.env` | Auth for Nemotron‑3‑Ultra LLM |
| `VITE_API_BASE_URL` (optional) | Frontend env var (Vercel/local) | API base URL for production deployment (example: Railway backend domain) |
| `PLAYWRIGHT_BROWSERS_PATH` | Docker / CI | Custom browser cache location |

---

## 🎨 Theming

The UI stores the selected theme (`dark`/`light`) in React state and writes `data-theme="dark|light"` on the root container. All colours are driven by CSS custom properties (see `frontend/src/components/ZeroCodeTestGenerator.css`). Click the ☀️ / 🌙 button in the header to toggle.

---

## 🔐  Bring‑Your‑Own‑Key / Bring‑Your‑Own‑Model (BYOK / BYOM)

The generator now lets **every user supply their own LLM provider, model, and API key at run‑time** – no server‑side secret is required.

### Frontend (UI)

1. Click the **⚙️ Settings** button in the top‑right header.  
2. Choose an **API Provider** – *NVIDIA NIM, OpenRouter, OpenAI, Anthropic*.  
3. The **Model** dropdown updates automatically with the models that belong to the chosen provider.  
4. Paste **your personal API key** into the “Your API Key” field (password‑masked).  
5. Press **Validate & Close** – the modal closes and the three values  
   `provider`, `selectedModel`, `userApiKey` are stored in the browser session and sent with **every** backend request (`/create-session` and `/generate-pom`, using the configured API base URL).

### Backend (API)

* **Request models** (`GenerateTestRequest`, `GeneratePOMRequest`, `CreateSessionRequest`) now contain three optional fields:

```python
provider: str = Field(default="NVIDIA NIM")
model:    str = Field(default="nvidia/nemotron-3-ultra-550b-a55b")
user_api_key: Optional[str] = Field(default=None)
```

* **Dynamic LLM router** (`backend/llm_router.py`) builds an `AsyncOpenAI` client on‑the‑fly:

| Provider      | Base URL                                   | Auth handling |
|---------------|--------------------------------------------|---------------|
| NVIDIA NIM    | `https://integrate.api.nvidia.com/v1`      | `Authorization: Bearer <key>` |
| OpenRouter    | `https://openrouter.ai/api/v1`             | `Authorization: Bearer <key>` + `HTTP‑Referer`, `X‑Title` |
| OpenAI        | `https://api.openai.com/v1`                | standard `Authorization: Bearer <key>` |
| Anthropic     | `https://api.anthropic.com/v1` (OpenAI‑compatible) | standard `Authorization: Bearer <key>` |

* **Key resolution** – the user‑supplied `user_api_key` wins; if it’s empty the server falls back to the matching environment variable (`NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).

* **Reasoning / thinking budget** (`enable_thinking`, `reasoning_budget`) is attached **only** for Nemotron models (`"nemotron"` in the model name).

### Environment variables (optional fallbacks)

```bash
NVIDIA_API_KEY=…
OPENROUTER_API_KEY=…
OPENAI_API_KEY=…
ANTHROPIC_API_KEY=…
```

If the user provides a key in the UI, those env vars are ignored for that request.

### Docker / CI

No code changes required – just make sure the four `*_API_KEY` variables are **not baked into the image**; they’ll be supplied at runtime (or omitted if every user brings their own key).

---

With this BYOK/BYOM flow each team member can point the generator at **any OpenAI‑compatible endpoint and model they have access to**, keeping secrets out of the repository and the server. 🚀

---

## 🤝 Contributing

1. Fork & branch (`git checkout -b feat/awesome`).  
2. Follow existing code style (`black`, `eslint`, `prettier`).  
3. Add tests for new behaviour.  
4. Open a PR – CI will run lint, type‑check, unit tests, and a smoke run of the generator.

---

## 📄 License

MIT © 2026 – Zero‑Code Playwright Generator contributors.

---

## 🙏 Acknowledgements

* **NVIDIA Nemotron‑3‑Ultra** for the LLM backbone.  
* **Playwright** for rock‑solid browser automation.  
* **FastAPI**, **React**, **Vite**, **Framer Motion**, **React‑Toastify**, **react‑copy‑to‑clipboard** – the stack that makes the DX smooth.

---

*Happy testing!* 🚀