# 10-Minute Presentation Outline
## AI-Powered Incident Analyzer · Pine Labs Technology Operations

---

## Slide 1 — Problem Statement (1 min)

**Opening line:** "A support engineer gets paged at 2 AM with 200 log lines. What went wrong? How serious is it? What do they check first?"

Key points:
- Manual log triage is slow, inconsistent, and error-prone
- Support engineers need: fast summary, clear severity, safe first steps — not a wall of text
- This tool turns raw application logs into an evidence-led incident brief in seconds

---

## Slide 2 — Architecture (2 min)

Walk through the two-pass pipeline:

```
Raw Logs → Parser → Pattern Analyzer → Severity Classifier
                                   ↓
                              Groq AI (optional)
                                   ↓
                         Citation Verifier
                                   ↓
                         Incident Report
```

Emphasise:
- **Deterministic first** — severity is always rule-based, never AI-decided
- **AI adds depth** — root cause narrative, confidence-tagged findings, structured JSON
- **Citation verification** — the concrete anti-hallucination mechanism
- **Graceful fallback** — works fully without an API key

---

## Slide 3 — Live Demo (4 min)

**Scenario 1 — Payment API cascade (Critical)**
- Load `payment_api_timeout.log`
- Show: severity badge, score breakdown, KPI row (error rate, services)
- Highlight: pattern table, DB connection override, confirmed findings with citations
- Show: diagnostic checks ordered read-only → team-decision → escalation
- Download the Markdown report

**Scenario 2 — Ambiguous/thin logs (Low + insufficient evidence)**
- Load `ambiguous_thin.log`
- Show: "Insufficient evidence" flag
- Point out: tool says what it doesn't know, not just what it does

**Scenario 3 — Healthy system (None)**
- Load `healthy_system.log`
- Show: score = 0, no chart, green "no issues" state
- Point out: healthy logs are a first-class output, not an edge case

---

## Slide 4 — AI Integration Deep-Dive (2 min)

**How the prompt works:**
- System prompt defines the JSON schema and the evidence-only constraint
- User prompt sends pre-parsed structured data + numbered error lines (not raw logs)
- One call returns: root cause, severity, summary, checks, escalation, insufficient_evidence flag

**How hallucinations are controlled (the Q&A answer):**
1. Pre-parse → LLM gets numbered lines it can actually cite
2. Prompt requires `L<number>: 'quoted text'` for every confirmed finding
3. `citation_verifier.py` checks line exists + quote matches → failed = ⚠️ unverified

**Confidence tags:** confirmed ✅ · likely 🔶 · possible ❓ · unverified ⚠️

---

## Slide 5 — Limitations & Next Steps (1 min)

**Limitations:**
- Simulated data only; heuristics, not proven causation
- One supported log format (timestamped plain-text); free-form is best-effort
- Prototype: no auth, no streaming, no production PII masking

**Next steps (if productionised):**
- Log streaming via Kafka / Fluentd
- Vector DB for similar-incident retrieval
- PagerDuty / Jira integration
- PII masking before AI processing
- Fine-tuned model on historical incident data

---

## Q&A Prep

| Question | Strong answer |
|----------|--------------|
| Why Streamlit? | Fastest path to a polished prototype with upload, charts, and download. Focus on AI logic, not frontend engineering. |
| How do you stop hallucinations? | Three layers: pre-parsed numbered lines, citation requirement in the prompt, `citation_verifier.py` that programmatically checks every confirmed finding. Failed citations are downgraded and flagged — users never see a false fact presented as confirmed. |
| What if Groq is down? | Full deterministic pipeline still runs: parse → pattern detection → rate-based severity → report. The UI shows an info banner. |
| Why rate-based severity not counts? | 30 errors in 2 minutes is an emergency; 30 over a day is routine. Rate captures urgency. Override rules ensure a payment outage with 5 errors can't score Low. |
| Where did you use AI tools? | Transparent log in README: scaffolding, sample data, prompt iteration. The severity rubric, override rules, citation verifier, and fallback logic were written and reviewed as deterministic code by me — I can explain any line. |
| How would you scale this? | Kafka for streaming, vector DB for similar incidents, PagerDuty/Jira integration, role-based access, PII masking, fine-tuned model on past incidents. |
| What does the tool do when evidence is thin? | Returns `insufficient_evidence: true` and says so explicitly. Better to say "not enough data" than guess. |
| Why one LLM call not multiple? | Easier to test, explain, and debug. Single input → single output. No orchestration overhead for a prototype. |
