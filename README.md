# SmartRoute — Enterprise AIOps LLM Gateway & MLOps Platform

[![CI Quality Gate](https://github.com/smartroute/smartroute-mlops/actions/workflows/ci.yml/badge.svg)](https://github.com/smartroute/smartroute-mlops/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![MLflow](https://img.shields.io/badge/MLflow-2.19.0-0194E2.svg?logo=mlflow)](https://mlflow.org)
[![React 19](https://img.shields.io/badge/React-19.3.1-61DAFB.svg?logo=react)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker)](https://www.docker.com)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.6.0-F7931E.svg?logo=scikit-learn)](https://scikit-learn.org)

> **SmartRoute** is an intelligent, cost-optimizing LLM Gateway designed for AI Operations (AIOps). It dynamically inspects incoming prompts, classifies their complexity using a **Hybrid Multi-Tier Routing Engine**, dispatches queries to the most cost-effective specialized model, verifies responses via a **Cascade Escalation Loop**, redacts sensitive PII with lossless rehydration, and enforces an end-to-end MLOps lifecycle with **MLflow model registry, zero-downtime hot-swapping, statistical drift detection (PSI/KS), and CI/CD quality gates**.

---

## 📑 Table of Contents

1. [Executive Summary & Core Value Proposition](#-executive-summary--core-value-proposition)
2. [End-to-End System Architecture](#-end-to-end-system-architecture)
3. [The Hybrid Routing Engine & Model Capability Fleet](#-the-hybrid-routing-engine--model-capability-fleet)
4. [Cascade Escalation & Verification Loop](#-cascade-escalation--verification-loop)
5. [Security & Responsible AI (DLP & Safety)](#-security--responsible-ai-dlp--safety)
6. [MLOps & AIOps Lifecycle](#-mlops--aiops-lifecycle)
   - [Data Engineering & Grounding](#data-engineering--grounding)
   - [Feature Engineering (Zero Train/Serve Skew)](#feature-engineering-zero-trainserve-skew)
   - [MLflow Registry & Champion/Challenger Promotion](#mlflow-registry--championchallenger-promotion)
   - [Zero-Downtime Model Hot-Swapping](#zero-downtime-model-hot-swapping)
   - [Statistical Drift Detection (PSI & KS-Test)](#statistical-drift-detection-psi--ks-test)
   - [CI/CD Model Quality Gate](#cicd-model-quality-gate)
7. [Provider Infrastructure (Groq, FreeLLMAPI, & Fail-Open Mock)](#-provider-infrastructure)
8. [Operations Dashboard (Frontend UI)](#-operations-dashboard-frontend-ui)
9. [Getting Started & Running Locally](#-getting-started--running-locally)
10. [API Reference & Telemetry Endpoints](#-api-reference--telemetry-endpoints)
11. [Verification, Tests, & Quality Gates](#-verification-tests--quality-gates)
12. [Prospective Roadmap & Future Architecture](#-prospective-roadmap--future-architecture)

---

## 🎯 Executive Summary & Core Value Proposition

In modern enterprise LLM deployments, **"always using the biggest model"** (e.g., GPT-4o, Claude 3.5 Sonnet, or GPT-OSS 120B) is an anti-pattern. Over 60% of enterprise queries are simple factual lookups, formatting requests, or brief synthesis that small 8B–20B models answer with identical quality at 10% of the cost and 5x the speed.

Conversely, static heuristic rules (like routing based purely on word count) fail on short math puzzles, riddles, and complex coding questions.

**SmartRoute solves this tradeoff by providing:**
1. **Measured Cost Savings (~11.5% to 35% on real distributions)** verified with counterfactual accounting (recording what every request would have cost on the expensive model vs. actual cost).
2. **Sub-15ms Hybrid Routing** combining sub-millisecond scikit-learn classification with small language model (SLM) semantic ambiguity resolution.
3. **Safety & Quality Net:** Automatic cascade retry if a cheap model hallucinates, refuses, or truncates.
4. **Complete AIOps/MLOps Lifecycle:** Full pipeline reproducibility from data prep through training, automated registry promotion, drift detection, and CI regression prevention.

---

## 🏗 End-to-End System Architecture

```
                                  USER / CLIENT APP / DASHBOARD
                                                │
                                    REST API (X-API-Key)
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               FASTAPI GATEWAY (PORT 8000)                              │
│                                                                                        │
│  [1. Authentication]   ──▶ SHA-256 hashed API key validation                           │
│  [2. Rate Limiter]     ──▶ Token-bucket algorithm (per-key burst & refill)             │
│  [3. PII Redaction]    ──▶ Regex + Luhn-validated card, Aadhaar, PAN, email, phone     │
│  [4. Injection Guard]  ──▶ Heuristic override & role-hijack pattern scanner            │
│                                                │                                       │
│                                                ▼                                       │
│  [5. Hybrid Routing Engine]                                                            │
│     ├── Strategy: "ml_fast"       ──▶ Tier-1 Scikit-learn Logistic Regression (<3ms)   │
│     ├── Strategy: "llm_semantic"  ──▶ Tier-2 SLM-Judge Intent Classifier (JSON prompt) │
│     └── Strategy: "hybrid"        ──▶ Tier-1 ML first; if confidence in ambiguous     │
│                                       zone (0.40–0.65), escalate to Tier-2 SLM-Judge   │
│                                                │                                       │
│                                                ▼                                       │
│  [6. Model Fleet Dispatch]                                                             │
│     ├── simple             ──▶ Fast/Nano (openai/gpt-oss-20b or llama-3.1-8b)         │
│     ├── moderate           ──▶ Balanced (openai/gpt-oss-120b or llama-3.3-70b)       │
│     ├── complex_reasoning  ──▶ Reasoning (deepseek-r1-70b or gpt-oss-120b)            │
│     └── complex_code       ──▶ Code Specialist (qwen/qwen3.8-27b or qwen-2.5-coder)   │
│                                                │                                       │
│                                                ▼                                       │
│  [7. Upstream Call]    ──▶ Groq Cloud API / FreeLLMAPI Proxy / Fail-Open Mock          │
│                                                │                                       │
│                                                ▼                                       │
│  [8. Cascade Escalation]                                                               │
│     └── If cheap model answered: inspect for refusal, hedge, shortness, or math fail. │
│         Trigger tripped? ──▶ Re-query Expensive Model & bill both (transparent cost)   │
│                                                │                                       │
│                                                ▼                                       │
│  [9. PII Rehydration]  ──▶ Swap typed tokens (<EMAIL_1>) back into final user answer   │
│  [10. Audit & Telemetry]                                                               │
│     ├── SQLite DB      ──▶ Log query, latencies, tokens, counterfactual savings        │
│     └── Prometheus     ──▶ Expose /metrics (traffic, drift score, escalations)         │
└───────────────────────────────────────┬──────────────┬─────────────────────────────────┘
                                        │              │
                       Loads @champion  ▼              ▼  Scrapes
                              MLflow Registry      Prometheus & Grafana
                                (Port 5000)         Dashboard (Port 3000)
```

---

## 🧠 The Hybrid Routing Engine & Model Capability Fleet

### Multi-Tier Hybrid Architecture

SmartRoute implements a two-tier hybrid routing pattern (pioneered by RouteLLM and enterprise gateways):

```
                       Incoming Clean Query
                                │
                                ▼
                   [ Tier 1: Fast ML Classifier ]
                  Scikit-Learn Logistic Regression
               Fitted on TF-IDF + 9 Linguistic Features
                        Execution time: < 3ms
                                │
             ┌──────────────────┴──────────────────┐
             ▼                                     ▼
   High Confidence (> 65%)                Ambiguous Zone (40% - 65%)
             │                                     │
             │                                     ▼
             │                        [ Tier 2: SLM-Judge Router ]
             │                       Fast Small Language Model (<400ms)
             │                       Evaluates reasoning depth & constraints
             │                                     │
             └──────────────────┬──────────────────┘
                                ▼
                 Dispatches to Specialized Model
```

#### Routing Strategies (Client-Selectable via API/Dashboard):
1. **`hybrid` (Default):** Runs Tier-1 ML first. If confidence is crisp, dispatches instantly. If the query falls in the ambiguous boundary (0.40–0.65 confidence or ambiguous moderate queries), it consults Tier-2 SLM-Judge.
2. **`ml_fast`:** Enforces pure sub-millisecond statistical classification for ultra-latency-sensitive workloads.
3. **`llm_semantic`:** Runs zero-shot semantic intent classification using an SLM structured prompt returning JSON categories.

---

### Model Capability Fleet Matrix

Rather than a primitive binary choice, SmartRoute supports a capability-matched fleet:

| Difficulty Class | Primary Routed Model | Alternative Fleet Model | Characteristics & Target Workload |
|---|---|---|---|
| **`simple`** | `openai/gpt-oss-20b` | `llama-3.1-8b-instant` | Near-zero latency (700+ tok/s), lowest token cost; definitions, facts, translations. |
| **`moderate`** | `openai/gpt-oss-120b` | `llama-3.3-70b-versatile` | High instruction-following, rich synthesis; open-ended essays, summaries, brainstorming. |
| **`complex_reasoning`** | `openai/gpt-oss-120b` | `deepseek-r1-distill-llama-70b` | Deep chain-of-thought, mathematical proofs, GSM8K word problems. |
| **`complex_code`** | `qwen/qwen3.8-27b` | `qwen-2.5-coder-32b` | Code syntax, AST analysis, algorithms, regex, debugging, SQL queries. |

---

## 🛡 Cascade Escalation & Verification Loop

Pre-execution routing is inherently probabilistic. When a query is routed to a cheap model, **SmartRoute does not assume the cheap answer is good**.

`gateway/cascade.py` executes a zero-cost heuristic verifier on the cheap model's completion before sending it to the user:

```python
# Verifier Triggers:
1. Refusals: r"\b(i (can't|cannot|am unable to|won't be able)|as an ai|i'm just an ai)\b"
2. Hedging:  r"\b(i'm not (sure|certain)|i don't know|it's (unclear|hard to say))\b"
3. Brevity:  len(answer.strip()) < 25 characters (almost certainly a truncated non-answer)
4. Math gap: Query demands numerical output ("how many", "calculate", "sum") but answer contains 0 digits.
```

**Honest Accounting:** If any trigger fires, the gateway retries the request on the expensive model. **Both calls are billed**, meaning false escalations transparently lower reported savings. This ensures the routing system cannot cheat its own cost metrics.

---

## 🔒 Security & Responsible AI (DLP & Safety)

Every request follows an immutable security pipeline (`gateway/security.py`):

1. **Authentication:**
   - Keys supplied via `X-API-Key`.
   - Never stored or compared in plaintext; hashed via SHA-256 (`hashlib.sha256`).
2. **Rate Limiting:**
   - In-memory thread-safe Token Bucket algorithm per API key.
   - Rejection returns HTTP `429 Too Many Requests` with a calculated `Retry-After` header.
3. **Data Loss Prevention (PII Redaction & Rehydration):**
   - High-precision regex pattern matchers for:
     - Email addresses (`<EMAIL_1>`)
     - Phone numbers (`<PHONE_1>`)
     - Indian PAN cards & Aadhaar numbers (`<PAN_1>`, `<AADHAAR_1>`)
     - Credit Card numbers validated with the **Luhn Algorithm** (`<CARD_1>`) so arbitrary 16-digit serial numbers are not falsely stripped.
   - **Lossless Rehydration:** The upstream LLM only ever sees placeholder tokens (`<EMAIL_1>`). On completion, the gateway safely rehydrates the original values so the end-user receives a coherent response without leaking private data to third-party model providers.
4. **Prompt-Injection Guard:**
   - Regex-based heuristic detector scanning for instruction-override attempts (`ignore previous instructions`, `system prompt override`, `jailbreak`, `DAN mode`). Flagged in database and Prometheus metrics without silently discarding user requests.
5. **Zero-PII Audit Logging:**
   - Telemetry logs record redaction counts and injection flags, never raw sensitive values.

---

## 🔄 MLOps & AIOps Lifecycle

```
   [ Data Engineering ] ──▶ router/prepare_data.py (SQuAD + Dolly + GSM8K + MBPP)
                                    │
                                    ▼
   [ Feature Contract ] ──▶ router/features.py (TF-IDF + 9 Numeric Signals)
                                    │
                                    ▼
   [ Model Training ]   ──▶ router/train.py (Scikit-Learn Logistic Regression Pipeline)
                                    │
                                    ▼
   [ Registry Promotion]──▶ MLflow Model Registry (Conditional @champion Promotion)
                                    │
                                    ▼
   [ Serving & Swapping]──▶ gateway/router_service.py (Zero-Downtime In-Memory Hot-Swap)
                                    │
                                    ▼
   [ Drift Monitoring ] ──▶ router/drift.py (PSI & KS-Test vs Reference Distribution)
                                    │
                                    ▼
   [ CI/CD Gate ]       ──▶ scripts/quality_gate.py (Fails build on cost/macro-F1 regression)
```

### Data Engineering & Grounding
Instead of templated synthetic prompts (which create circular 99% accuracy illusions), `router/prepare_data.py` builds ~900 stratified queries from real-world open datasets:
- **`simple`:** SQuAD v2 factual question-answer pairs.
- **`moderate`:** Databricks Dolly-15k (open_qa, general_qa, brainstorming).
- **`complex`:** GSM8K grade-school math word problems + MBPP Python coding challenges.
- **Holdout Set:** A dedicated 198-row stratified `holdout.csv` isolated strictly for baseline evaluations.

### Feature Engineering (Zero Train/Serve Skew)
`router/features.py` is the single source of truth imported by training, serving, and drift detection. Features include:
- TF-IDF word 1–2 n-grams.
- 9 Hand-Engineered Numeric Features: character length, word count, question mark count, digit ratio, average word length, code-fence presence, and regex keyword flags for reasoning, code, and synthesis.

### MLflow Registry & Champion/Challenger Promotion
- Every training run (`router/train.py`) logs hyperparameters, scalar metrics (accuracy, macro-F1, cost savings %), classification reports, and confusion matrices.
- Models are registered under `query-difficulty-router`.
- **Conditional Promotion Rule:** When a new model is registered, the training script queries the current `@champion` version in MLflow. If and only if the new candidate's `macro_f1` exceeds the incumbent's `macro_f1`, MLflow moves the `@champion` alias to the new model. Otherwise, it is tagged `@challenger`.

### Zero-Downtime Model Hot-Swapping
The FastAPI gateway (`gateway/router_service.py`) dynamically reads from `models:/query-difficulty-router@champion`. When `/admin/retrain` completes and promotes a new champion, the gateway hot-reloads the sklearn pipeline in memory **without dropping active HTTP connections or requiring a process restart**.

### Statistical Drift Detection (PSI & KS-Test)
`router/drift.py` tracks distribution shift between live inference traffic and the training baseline:
- **Population Stability Index (PSI):** Quantifies binned feature shift. `PSI < 0.1` (stable), `0.1 <= PSI < 0.25` (moderate shift), `PSI >= 0.25` (significant drift).
- **Kolmogorov-Smirnov (KS) Test:** Two-sample non-parametric test evaluating cumulative distributions.
- **Live Demo Affordance:** `POST /admin/simulate-drift` injects synthetic out-of-distribution traffic to demonstrate drift alerts on the dashboard in real time.

### CI/CD Model Quality Gate
In standard software engineering, CI only checks if unit tests pass. In AIOps, a model can pass all unit tests but secretly regress in economic utility.
`scripts/quality_gate.py` runs in GitHub Actions (`.github/workflows/ci.yml`):
- Fails the build if `macro_f1 < 0.85`.
- Fails the build if `cost_savings_pct < 10.0%` (guards against models that stay accurate by cowardly routing everything to the expensive model).

---

## 🌐 Provider Infrastructure

SmartRoute supports a pluggable provider abstraction (`gateway/providers.py`):

1. **Groq Cloud API (`GroqProvider`):**
   - High-speed inference using native LPUs (Language Processing Units).
   - Serves `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, and `qwen/qwen3.8-27b`.
   - Setup: Simply add `GROQ_API_KEY=gsk_...` to `.env`.
2. **FreeLLMAPI BYOK Proxy Integration:**
   - Fully compatible with [tashfeenahmed/freellmapi](https://github.com/tashfeenahmed/freellmapi).
   - FreeLLMAPI acts as an upstream aggregator proxy combining free-tier allowances from Groq, Google AI Studio, Cerebras, and Mistral behind a unified OpenAI-compatible endpoint.
   - To route SmartRoute through FreeLLMAPI:
     ```env
     GROQ_BASE_URL=http://localhost:3001/v1
     GROQ_API_KEY=your-freellmapi-master-key
     ```
3. **Fail-Open Deterministic Mock (`MockProvider`):**
   - The gateway automatically falls back to the deterministic mock if no key is present or if upstream APIs return errors.
   - Preserves representative latency and token length so offline viva presentations and load tests never fail due to Wi-Fi drops or upstream rate limits.

---

## 💻 Operations Dashboard (Frontend UI)

Built with **React 19, Vite, and Recharts**, styled with an engineering-focused dark ops aesthetic:

- **Routing Operations Control Panel:**
  - One-click strategy toggle: `Hybrid (ML + SLM)`, `Fast ML (<3ms)`, `SLM Judge (400ms)`.
  - Confidence threshold slider (0.00 – 1.00).
  - Live query input with instantaneous response display and metadata pill badges (Model selected, Tier used, Routing latency, Dollar savings).
  - One-click triggers for **Drift Simulation** and **MLflow Retraining**.
- **Live Telemetry Feed:** Real-time stream of incoming queries, predicted classes, target models, escalation badges, PII redactions, latencies, and costs.
- **Interactive Telemetry Visualizations:**
  - Cost Saved Timeline (cumulative actual vs. baseline).
  - Latency by Model distribution.
  - Query Difficulty Classification distribution.
  - Live Feature Drift (PSI) chart.

---

## ⚡ Getting Started & Running Locally

### Prerequisites
- Python 3.11+
- Node.js 20+ & npm

### Method 1: Local Setup (Recommended for Presentations)

```bash
# 1. Navigate to the project directory
cd smartroute-mlops

# 2. Set up environment configuration
cp .env.example .env
# (Optional) Open .env and add your GROQ_API_KEY=gsk_...

# 3. Create virtual environment & install Python dependencies
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

# 4. Prepare datasets and train the baseline model
python -m router.prepare_data
python -m router.drift
python -m router.train --no-mlflow

# 5. Install frontend dependencies
cd frontend
npm install
cd ..

# 6. Launch the Gateway Backend (Port 8000)
uvicorn gateway.main:app --host 0.0.0.0 --port 8000

# 7. In a separate terminal, launch the Frontend (Port 3000)
cd frontend
npm run dev -- --host 0.0.0.0 --port 3000
```

Open your browser:
- **Operations Dashboard:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Gateway Health Status:** [http://localhost:8000/health](http://localhost:8000/health)

---

### Method 2: Docker Compose (Full Stack with MLflow Server)

```bash
cp .env.example .env
docker compose up --build
```

- **Dashboard:** [http://localhost:3000](http://localhost:3000)
- **Gateway:** [http://localhost:8000](http://localhost:8000)
- **MLflow Registry UI:** [http://localhost:5000](http://localhost:5000)

---

## 📡 API Reference & Telemetry Endpoints

All endpoints require the `X-API-Key: demo-key-smartroute` header.

| Method | Path | Description | Sample Request / Purpose |
|---|---|---|---|
| `POST` | `/v1/chat` | Main routed completion endpoint | `{"query": "...", "strategy": "hybrid", "threshold": 0.60}` |
| `GET` | `/health` | Service health, current model version, active provider | Liveness probe & registry sync status |
| `GET` | `/stats` | Aggregated cost savings, model breakdown, cost timeline | Feeds dashboard metrics cards |
| `GET` | `/requests/recent` | Recent query request history and telemetry | Feeds dashboard live feed table |
| `GET` | `/drift` | Per-feature PSI and KS-test calculations | Returns drift evaluation report |
| `GET` | `/metrics` | Prometheus exposition format | Scraped by Prometheus agents |
| `POST` | `/admin/retrain` | Triggers retraining & conditional champion promotion | Zero-downtime hot-swap endpoint |
| `POST` | `/admin/simulate-drift` | Injects synthetic out-of-distribution traffic | Demo trigger for drift visualizer |

---

## 🧪 Verification, Tests, & Quality Gates

Run unit tests and verification with:

```bash
# Run test suite
pytest

# Execute CI model quality gate
python -m scripts.quality_gate

# Reproduce offline evaluation benchmarks
python -m eval.run_baselines
```

---

## 🚀 Prospective Roadmap & Future Architecture

For production cloud-native expansion, the following extensions are scoped:

1. **Kubernetes & Helm Deployment (`k8s/`):**
   - Horizontal Pod Autoscaler (HPA) scaling gateway pods on Prometheus `http_requests_total` metric.
   - Init-container pulling the latest `@champion` artifact from MLflow S3/GCS remote artifact store.
2. **Semantic Vector Caching:**
   - Redis or Qdrant vector similarity cache checking prompt embeddings prior to invoking Tier-1 classification (answering repeated or semantically identical queries in <2ms with zero token cost).
3. **Multi-Key Upstream Rotation with FreeLLMAPI:**
   - Deploying `tashfeenahmed/freellmapi` alongside the gateway on port `3001` to automatically balance across multiple free API keys with automatic HTTP 429 failover.
4. **Locust Distributed Load Testing (`locust/`):**
   - Benchmarking gateway throughput, rate limiter token replenishment, and p99 latency under concurrent synthetic query traffic.
