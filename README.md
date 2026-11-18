# 🛡️ AI-Powered Incident Analyzer

> **Pine Labs · Technology Operations Internship — Practical AI Assignment 1**

A Streamlit prototype that turns raw application logs into a structured, evidence-led incident brief. It parses logs, detects error patterns, scores severity deterministically, optionally calls Groq for AI root-cause analysis, verifies every AI claim against real log lines, and produces a shareable Markdown report.

---

## ✨ Features at a Glance

| Feature | Detail |
|---------|--------|
| **Log ingestion** | File upload (`.log`, `.txt`), copy-paste, or 7 built-in sample scenarios |
| **Pattern detection** | Regex-based: timeouts, connection failures, auth errors, app exceptions, resource pressure, server errors |
| **Rate-based severity** | Errors-per-minute scoring with payment/auth safety floors and cascading overrides |
| **AI root-cause analysis** | Single Groq call; structured JSON with `confirmed / likely / possible` confidence tags |
| **Citation verification** | Every `confirmed` finding is checked against the actual numbered log line — failed citations become `⚠️ unverified` |
| **Safe recommendations** | Read-only diagnostic checks listed first; destructive actions labelled "team decision" |
| **Downloadable report** | Markdown incident brief ready for Slack, Jira, or email |
| **Graceful fallback** | Full deterministic analysis works without a Groq API key |

---

## 🚀 Quick Start

```powershell
# 1 — Clone / open the project folder
cd "D:\Pine Labs AI Incident analyzer"

# 2 — Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3 — Install dependencies
pip install -r requirements.txt

# 4 — Set up your API key (optional but recommended)
Copy-Item .env.example .env
# Edit .env and replace the placeholder with your Groq API key
# Get a free key at https://console.groq.com/keys

# 5 — Run the app
streamlit run app.py
```

The app opens at **http://localhost:8501** by default.

> **Without a Groq key** — the full deterministic pipeline (parsing, pattern analysis, severity scoring, report) still works. The UI shows an info banner and skips the AI step.

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *(none)* | Groq API key. Required for AI analysis. |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Override the Groq model. |

Variables are loaded from `.env` in the project root (via `python-dotenv`). Environment variables already set in the shell take precedence.

> Never commit `.env` to version control. It is in `.gitignore`.

---

## 🏗️ Architecture

```
Raw Log Input
      │
      ▼
┌─────────────────┐
│  Log Parser     │  Normalize, number lines, detect format
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Pattern Analyzer│  Regex patterns, error rate, service paths, timeline
└────────┬────────┘
         │
         ├──────────────────────────────────────┐
         ▼                                      ▼
┌─────────────────┐                   ┌──────────────────┐
│ Severity        │                   │ Groq AI Analyzer  │  (optional)
│ Classifier      │                   │ Single JSON call  │
│ (rate-based +   │                   └────────┬─────────┘
│  override rules)│                            │
└────────┬────────┘                   ┌────────▼─────────┐
         │                            │ Citation Verifier │
         │                            └────────┬─────────┘
         └──────────────┬─────────────────────┘
                        ▼
               ┌─────────────────┐
               │ Report Generator│
               └────────┬────────┘
                        ▼
               Streamlit Dashboard
               (severity · findings · checks · report)
```

### Two-pass design

1. **Deterministic pass** — fast, explainable, always runs. Produces error rates, pattern counts, timeline, and a severity score.
2. **AI pass** — optional Groq call. Receives pre-parsed structured data (not raw log noise) for better accuracy, lower token cost, and reliable line citations.

---

## 📂 Project Structure

```
├── app.py                      # Streamlit UI
├── requirements.txt
├── .env.example                # API key template
├── README.md
│
├── src/
│   ├── log_parser.py           # Parsing and normalization
│   ├── pattern_analyzer.py     # Regex patterns, rates, timeline
│   ├── ai_analyzer.py          # Groq integration + fallback
│   ├── citation_verifier.py    # AI claim verification
│   ├── severity_classifier.py  # Rate-based scoring + override rules
│   └── report_generator.py     # Markdown report
│
├── prompts/
│   └── analysis_prompt.py      # System prompt with JSON schema
│
├── sample_logs/                # 7 simulated scenarios (no production data)
│   ├── payment_api_timeout.log
│   ├── database_connection.log
│   ├── auth_service_failure.log
│   ├── post_deploy_spike.log
│   ├── ambiguous_thin.log
│   ├── mixed_incident.log
│   └── healthy_system.log
│
├── tests/                      # pytest unit + scenario tests
└── docs/
    └── presentation_outline.md
```

---

## 🎯 Severity Classification

Severity is **always deterministic** — the AI opinion is shown as context but cannot override the rule-based result.

### Rate-based score (0–100)

| Component | Max pts | Logic |
|-----------|--------:|-------|
| Error rate (errors/min) | 35 | 0 = 0 · ≤1 = 8 · ≤5 = 15 · ≤15 = 25 · >15 = 35 |
| Highest log level | 25 | FATAL/CRITICAL = 25 · ERROR = 15 · WARN = 5 · INFO = 0 |
| Blast radius (services) | 25 | ≥3 = 25 · 2 = 15 · 1 = 8 · 0 = 0 |
| Error window duration | 15 | >30 min = 15 · ≥10 = 10 · ≥2 = 6 · <2 = 3 · 0 errors = 0 |

**Healthy logs always score 0.**

### Score → severity

| Score | Severity |
|------:|----------|
| 0 | ✅ None |
| 1–24 | 🟢 Low |
| 25–49 | 🟡 Medium |
| 50–74 | 🟠 High |
| 75–100 | 🔴 Critical |

### Override rules (floors)

| Condition | Floor |
|-----------|-------|
| Payment-path errors sustained > 2 min | High |
| Auth-path errors sustained > 2 min | High |
| DB connection failures ≥ 3, sustained > 10 min | High |
| Payment path affected + cascading (≥ 2 services) | **Critical** |

---

## 🧪 Expected vs. Actual Severity

This table is the test contract — if the tool produces a different result, something is wrong.

| Scenario | Log file | Expected | Deterministic result | Key signal |
|----------|----------|----------|----------------------|------------|
| Payment API cascade | `payment_api_timeout.log` | 🔴 Critical | 🔴 Critical | Payment path + cascading override |
| DB connection failures | `database_connection.log` | 🟠 High | 🟠 High | Sustained DB failures floor |
| Auth service failure | `auth_service_failure.log` | 🟠 High | 🟠 High | Auth path override |
| Post-deploy spike | `post_deploy_spike.log` | 🟡 Medium | 🟡 Medium | Self-resolved, non-critical service |
| Ambiguous / thin | `ambiguous_thin.log` | 🟢 Low | 🟢 Low | Warnings only, no errors |
| Mixed incident | `mixed_incident.log` | 🟡 Medium | 🟡 Medium | Multi-service, no critical path |
| Healthy system | `healthy_system.log` | ✅ None | ✅ None | Score = 0, no errors |

Run `pytest -q` to verify these automatically.

---

## 🤖 AI Integration Details

### Hallucination prevention

Three enforced layers:

1. **Pre-parse before sending** — the LLM receives a structured summary + numbered log lines, not raw text. This anchors its response in real data.
2. **Citation required** — the system prompt requires every `confirmed` finding to cite `L<number>: 'quoted text'`.
3. **Citation verification** — `citation_verifier.py` programmatically checks that the cited line exists and contains the quoted text. Failed checks downgrade the finding from `confirmed` → `⚠️ unverified` with a visible flag in the UI.

### Evidence-only recommendations

Diagnostic checks are ordered: **read-only checks first → hypothesis tested → escalation → team-owned remediation**. Restarts and config changes are labelled "owning team decision" — never presented as confirmed safe actions.

### Single structured call

One Groq API call returns a JSON object with: `root_cause_analysis`, `severity`, `incident_summary`, `diagnostic_checks`, `escalation`, and `insufficient_evidence`. Single call = easier to test, explain, and debug.

---

## 🧪 Running Tests

```powershell
# From the project root with venv activated
pytest -q
```

Tests cover:
- Log parsing (timestamped, free-form, malformed, empty, encoding edge cases)
- Pattern detection (regex accuracy, rate calculation, service path identification)
- Severity classification (all score bands, override rules, healthy log = score 0)
- Citation verification (valid citation passes, wrong line/quote flagged, missing citation flagged)
- End-to-end scenario contracts (expected severity per sample log)

---

## 📋 Assumptions & Limitations

- All logs are **simulated**. No production or real user data was used.
- Supported log format: `YYYY-MM-DD HH:MM:SS LEVEL ServiceName - message`. Free-form lines fall back to keyword extraction.
- Pattern heuristics identify likely failure categories — they do not prove causation.
- Groq availability, model quality, and network access are not guaranteed.
- The severity rubric was designed for the assignment's scenario set; edge cases outside these patterns may need rubric tuning.
- This is a **prototype**, not a production log-ingestion or incident-management system.

---

## 🤝 Where AI Tools Were Used

| Area | AI contribution | My contribution |
|------|----------------|-----------------|
| Project scaffolding | File/folder structure suggestions | Architecture decisions, module boundaries |
| Sample log data | Drafted realistic log line content | Scenario design, expected severity validation |
| Boilerplate code | Function stubs, dataclass shapes | All logic: severity rubric, override rules, citation verifier, rate calculation |
| Prompt wording | Draft iterations | Final prompt structure, JSON schema, evidence-only constraint |
| Test cases | Draft test scenarios | Test assertions, coverage decisions, expected values |
| README | Draft sections | Full review, accuracy check, technical explanations |

The severity rubric, safety floor logic, citation-verification mechanism, and fallback behavior were written, reviewed, and tested as deterministic code against the project plan. I can explain every line.

---

## 🎤 Presentation

See [`docs/presentation_outline.md`](docs/presentation_outline.md) for the 10-minute walkthrough structure and anticipated Q&A questions.
