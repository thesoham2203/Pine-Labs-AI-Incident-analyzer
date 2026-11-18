"""
AI-Powered Incident Analyzer — Streamlit UI
Pine Labs · Technology Operations
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.ai_analyzer import analyze_with_ai
from src.log_parser import parse_logs
from src.pattern_analyzer import analyze_patterns
from src.report_generator import generate_report
from src.severity_classifier import classify_severity

# ── Constants ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
SAMPLE_DIR = ROOT / "sample_logs"
SAMPLES = sorted(SAMPLE_DIR.glob("*.log"))
MAX_UPLOAD_BYTES = 2 * 1024 * 1024

SEVERITY_CONFIG = {
    "Critical": {"color": "#dc2626", "bg": "#fef2f2", "border": "#fca5a5", "emoji": "🔴", "icon": "🚨"},
    "High":     {"color": "#ea580c", "bg": "#fff7ed", "border": "#fdba74", "emoji": "🟠", "icon": "⚠️"},
    "Medium":   {"color": "#ca8a04", "bg": "#fefce8", "border": "#fde047", "emoji": "🟡", "icon": "🔶"},
    "Low":      {"color": "#16a34a", "bg": "#f0fdf4", "border": "#86efac", "emoji": "🟢", "icon": "ℹ️"},
    "None":     {"color": "#0369a1", "bg": "#f0f9ff", "border": "#7dd3fc", "emoji": "✅", "icon": "✅"},
}

CONFIDENCE_CONFIG = {
    "confirmed":   ("✅", "Confirmed", "#16a34a"),
    "likely":      ("🔶", "Likely",    "#ca8a04"),
    "possible":    ("❓", "Possible",  "#6b7280"),
    "unverified":  ("⚠️", "Unverified","#dc2626"),
}

SAMPLE_DESCRIPTIONS = {
    "payment_api_timeout.log":  "💳 Payment API cascade — DB pool exhaustion → API timeouts",
    "database_connection.log":  "🗄️  Database connection failures — read-replica failover gone wrong",
    "auth_service_failure.log": "🔐 Auth service failure — JWKS certificate expiry chain",
    "post_deploy_spike.log":    "🚀 Post-deploy error spike — bad release, clean rollback",
    "ambiguous_thin.log":       "🔍 Ambiguous / thin logs — insufficient evidence scenario",
    "mixed_incident.log":       "🔀 Mixed incident — unrelated failures on separate services",
    "healthy_system.log":       "✅ Healthy system — baseline, no errors",
}

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Incident Analyzer · Pine Labs",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global typography */
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; }

/* Header band */
.hero-band {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #0f766e 100%);
    padding: 2rem 2.5rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    color: white;
}
.hero-band .brand { font-size: 0.75rem; font-weight: 700; letter-spacing: 0.15em; opacity: 0.6; text-transform: uppercase; margin-bottom: 0.4rem; }
.hero-band h1 { font-size: 2rem; font-weight: 800; margin: 0 0 0.3rem; color: #fff; }
.hero-band .subtitle { font-size: 0.95rem; opacity: 0.75; margin: 0; }

/* Severity banner */
.severity-banner {
    padding: 1.25rem 1.5rem;
    border-radius: 10px;
    border-left: 5px solid;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.severity-banner .level-label { font-size: 1.5rem; font-weight: 800; }
.severity-banner .level-sub { font-size: 0.8rem; opacity: 0.75; margin-top: 0.1rem; }

/* KPI cards */
.kpi-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.kpi-card .kpi-value { font-size: 1.75rem; font-weight: 800; color: #0f172a; }
.kpi-card .kpi-label { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #64748b; margin-top: 0.1rem; }
.kpi-card .kpi-sub { font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem; }

/* Finding cards */
.finding-card {
    padding: 0.85rem 1rem;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    margin-bottom: 0.6rem;
    background: #fafafa;
}
.finding-card .conf-badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    margin-bottom: 0.4rem;
}
.finding-card .description { font-size: 0.88rem; color: #1e293b; line-height: 1.4; }
.finding-card .citation { font-size: 0.75rem; color: #64748b; margin-top: 0.3rem; font-family: monospace; }

/* Check cards */
.check-card {
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin-bottom: 0.5rem;
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
}
.check-readonly { background: #f0fdf4; border: 1px solid #bbf7d0; }
.check-team { background: #fff7ed; border: 1px solid #fed7aa; }
.check-card .check-badge {
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    margin-top: 0.1rem;
}
.badge-ro { background: #dcfce7; color: #15803d; }
.badge-td { background: #fed7aa; color: #c2410c; }
.check-card .check-action { font-size: 0.85rem; color: #1e293b; font-weight: 500; }
.check-card .check-hyp { font-size: 0.75rem; color: #64748b; margin-top: 0.2rem; }

/* Escalation alert */
.escalation-box {
    background: #fef2f2;
    border: 1px solid #fca5a5;
    border-left: 4px solid #dc2626;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-top: 1rem;
}
.escalation-box .esc-title { font-weight: 700; color: #991b1b; margin-bottom: 0.3rem; }
.escalation-box .esc-body { font-size: 0.85rem; color: #7f1d1d; }

/* Tab styling */
div[data-testid="stTabs"] [role="tab"] {
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: 0.03em;
}

/* Upload area */
div[data-testid="stFileUploader"] {
    border-radius: 10px;
}

/* Sidebar */
section[data-testid="stSidebar"] { background: #0f172a; }
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #f1f5f9 !important; }
section[data-testid="stSidebar"] .stMarkdown a { color: #38bdf8 !important; }
section[data-testid="stSidebar"] hr { border-color: #334155 !important; }

/* Insufficient evidence alert */
.insufficient-box {
    background: #fffbeb;
    border: 1px solid #fcd34d;
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin: 0.5rem 0;
}

/* Score bar */
.score-bar-bg {
    background: #e2e8f0;
    border-radius: 999px;
    height: 8px;
    margin-top: 0.5rem;
    overflow: hidden;
}
.score-bar-fill {
    height: 8px;
    border-radius: 999px;
    transition: width 0.6s ease;
}
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ Incident Analyzer")
    st.markdown("**Pine Labs · Technology Operations**")
    st.markdown("---")

    st.markdown("### How it works")
    st.markdown("""
1. **Parse** — normalize and number every log line
2. **Detect** — regex patterns, error rates, affected paths  
3. **Score** — rate-based severity with critical-path overrides  
4. **AI analysis** — single Groq call for root cause & summary  
5. **Verify** — citation check on every confirmed finding  
6. **Report** — downloadable incident brief
    """)
    st.markdown("---")

    st.markdown("### Severity levels")
    for level, cfg in SEVERITY_CONFIG.items():
        if level != "None":
            st.markdown(f"{cfg['emoji']} **{level}**")

    st.markdown("---")
    st.markdown("### Confidence tags")
    st.markdown("""
✅ **Confirmed** — cited in log  
🔶 **Likely** — inferred from pattern  
❓ **Possible** — speculative  
⚠️ **Unverified** — citation failed  
    """)
    st.markdown("---")
    st.markdown("### Action types")
    st.markdown("""
🟢 **Read-only** — safe to run now  
🟠 **Team decision** — requires owning team approval  
    """)
    st.markdown("---")
    st.caption("v1.0 · Sample data only · No production logs")


# ── Hero header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-band">
    <div class="brand">Pine Labs · Technology Operations</div>
    <h1>🛡️ AI Incident Analyzer</h1>
    <p class="subtitle">Turn application logs into an evidence-led incident brief in seconds.</p>
</div>
""", unsafe_allow_html=True)


# ── Input section ──────────────────────────────────────────────────────────────
with st.container():
    st.subheader("📋 Log Input")
    st.caption("Choose a sample scenario, upload a `.log` / `.txt` file, or paste log lines directly.")

    col_src1, col_src2, col_src3 = st.columns(3)
    with col_src1:
        btn_sample = st.button("📂 Use Sample Scenario", use_container_width=True,
                               type="secondary" if st.session_state.get("src") != "sample" else "primary")
    with col_src2:
        btn_upload = st.button("⬆️ Upload File", use_container_width=True,
                               type="secondary" if st.session_state.get("src") != "upload" else "primary")
    with col_src3:
        btn_paste = st.button("📝 Paste Log Text", use_container_width=True,
                              type="secondary" if st.session_state.get("src") != "paste" else "primary")

    if btn_sample:
        st.session_state["src"] = "sample"
    if btn_upload:
        st.session_state["src"] = "upload"
    if btn_paste:
        st.session_state["src"] = "paste"
    if "src" not in st.session_state:
        st.session_state["src"] = "sample"

    source = st.session_state["src"]
    log_text = ""
    input_error = None

    st.markdown("<div style='margin-top:0.75rem'></div>", unsafe_allow_html=True)

    if source == "sample":
        sample_names = [p.name for p in SAMPLES]
        sample_labels = [SAMPLE_DESCRIPTIONS.get(n, n) for n in sample_names]
        label_to_name = dict(zip(sample_labels, sample_names))

        selected_label = st.selectbox(
            "Choose a scenario",
            options=["— select a scenario —"] + sample_labels,
            index=0,
            label_visibility="collapsed",
        )
        if selected_label and selected_label != "— select a scenario —":
            selected_name = label_to_name[selected_label]
            log_text = (SAMPLE_DIR / selected_name).read_text(encoding="utf-8")
            with st.expander("📄 Preview log", expanded=False):
                st.code(log_text, language="text", line_numbers=True)

    elif source == "upload":
        uploaded = st.file_uploader(
            "Choose a .log or .txt file (max 2 MB)",
            type=["log", "txt"],
            label_visibility="collapsed",
        )
        if uploaded:
            if uploaded.size > MAX_UPLOAD_BYTES:
                input_error = "File exceeds the 2 MB limit. Please split the file or paste a relevant excerpt."
            else:
                payload = uploaded.getvalue()
                if b"\x00" in payload:
                    input_error = "Only plain-text log files are supported (binary content detected)."
                else:
                    log_text = payload.decode("utf-8", errors="replace")
                    with st.expander(f"📄 Preview: {uploaded.name}", expanded=False):
                        st.code(log_text[:8000], language="text", line_numbers=True)
                        if len(log_text) > 8000:
                            st.caption(f"Preview truncated. Full {len(log_text):,} characters will be analyzed.")

    else:  # paste
        log_text = st.text_area(
            "Paste log lines",
            height=260,
            placeholder="2026-11-18 10:15:32 ERROR PaymentService - API request timed out after 30000ms",
            label_visibility="collapsed",
        )

    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
    analyze_btn = st.button("🔍 Analyze Incident", type="primary", use_container_width=True)


# ── Cache invalidation ─────────────────────────────────────────────────────────
input_fingerprint = hashlib.sha256(log_text.encode("utf-8")).hexdigest() if log_text else ""
if st.session_state.get("analyzed_fingerprint") != input_fingerprint:
    st.session_state.pop("result", None)


# ── Run analysis ───────────────────────────────────────────────────────────────
if analyze_btn:
    st.session_state.pop("result", None)
    if input_error:
        st.error(f"⛔ {input_error}")
    elif not log_text.strip():
        st.warning("Please select a sample, upload a file, or paste some log text first.")
    else:
        progress = st.progress(0, text="Parsing log lines…")
        try:
            records = parse_logs(log_text)
            progress.progress(25, text="Detecting patterns and calculating rates…")
            analysis = analyze_patterns(records)
            progress.progress(50, text="Scoring severity…")
            # Pre-classify before AI so the spinner shows the right message
            pre_severity = classify_severity(analysis)
            progress.progress(65, text="Requesting AI root-cause analysis from Groq…")
            ai = analyze_with_ai(records, analysis)
            progress.progress(90, text="Generating incident report…")
            severity = classify_severity(analysis, ai.get("severity", {}).get("level"))
            report = generate_report(analysis, severity, ai)
            progress.progress(100, text="Done.")
            st.session_state["result"] = (analysis, ai, severity, report)
            st.session_state["analyzed_fingerprint"] = input_fingerprint
            progress.empty()
        except ValueError as exc:
            progress.empty()
            st.error(f"⛔ {exc}")
        except Exception as exc:
            progress.empty()
            st.error(f"⛔ Unexpected error: {exc}")


# ── Results ────────────────────────────────────────────────────────────────────
if "result" in st.session_state:
    analysis, ai, severity, report = st.session_state["result"]
    level = severity["level"]
    cfg = SEVERITY_CONFIG.get(level, SEVERITY_CONFIG["None"])

    st.markdown("---")

    # ── Severity banner ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="severity-banner" style="background:{cfg['bg']};border-left-color:{cfg['color']};border:1px solid {cfg['border']};border-left:5px solid {cfg['color']};">
        <div style="font-size:2.5rem">{cfg['icon']}</div>
        <div>
            <div class="level-label" style="color:{cfg['color']}">{level.upper()} SEVERITY</div>
            <div class="level-sub">{severity['reason']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Score breakdown bar
    score = severity["score"]
    bar_color = cfg["color"]
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
        <span style="font-size:0.75rem;color:#64748b;font-weight:600;white-space:nowrap">Score {score}/100</span>
        <div class="score-bar-bg" style="flex:1">
            <div class="score-bar-fill" style="width:{score}%;background:{bar_color}"></div>
        </div>
        <span style="font-size:0.7rem;color:#94a3b8">Components: rate={severity['components']['error_rate']} · level={severity['components']['level']} · blast={severity['components']['blast_radius']} · duration={severity['components']['duration']}</span>
    </div>
    """, unsafe_allow_html=True)

    if severity.get("ai_disagreement"):
        st.info(f"💡 Groq suggested **{severity['ai_level']}** severity. The displayed level is the deterministic rule-based result.", icon="ℹ️")

    # ── KPI row ────────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    kpis = [
        (k1, f"{analysis['error_rate_per_minute']:.1f}", "Error Rate", "errors / min"),
        (k2, str(analysis["error_count"]), "Total Errors", f"{analysis['warning_count']} warnings"),
        (k3, f"{analysis['window_minutes']:.1f} min", "Log Window", f"{analysis['error_duration_minutes']:.1f} min of errors"),
        (k4, str(analysis["service_count"]), "Affected Services", ", ".join(analysis["error_services"][:2]) or "none identified"),
        (k5, str(analysis["total_lines"]), "Log Lines", "parsed and analyzed"),
    ]
    for col, val, label, sub in kpis:
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    # AI availability notice
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    if ai.get("available"):
        st.success("✅ Groq AI analysis completed. All confirmed findings have been verified against cited log lines.", icon="✅")
    else:
        err_msg = ai.get("error", "AI analysis unavailable; showing deterministic analysis only.")
        st.info(f"ℹ️ {err_msg}", icon="ℹ️")

    if ai.get("insufficient_evidence"):
        st.markdown("""
        <div class="insufficient-box">
            ⚠️ <strong>Insufficient evidence</strong> — the logs contain too few signals to determine a root cause with confidence.
            Collect more log data, expand the time window, or check upstream services before concluding.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab_overview, tab_evidence, tab_report = st.tabs(["📊 Overview & Analysis", "📈 Evidence & Timeline", "📄 Incident Report"])

    # ── Tab 1: Overview ────────────────────────────────────────────────────────
    with tab_overview:
        col_patterns, col_findings = st.columns([1, 1], gap="medium")

        with col_patterns:
            st.markdown("#### 🔎 Detected Error Patterns")
            if analysis["pattern_summary"]:
                pattern_df = pd.DataFrame(analysis["pattern_summary"])
                pattern_df.columns = ["Pattern", "Count", "Rate /min", "First Seen", "Last Seen"]
                st.dataframe(pattern_df, hide_index=True, use_container_width=True)
                # Mini bar chart of pattern counts
                chart_df = pd.DataFrame({
                    "Pattern": [r["Pattern"] for r in pattern_df.to_dict("records")],
                    "Count": [r["Count"] for r in pattern_df.to_dict("records")],
                }).set_index("Pattern")
                st.bar_chart(chart_df, use_container_width=True, height=200)
            else:
                st.markdown("""
                <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:1rem;text-align:center;color:#15803d;">
                    ✅ No error patterns detected — system appears healthy.
                </div>
                """, unsafe_allow_html=True)

        with col_findings:
            st.markdown("#### 🧠 Root Cause Findings")
            findings = ai.get("root_cause_analysis", {}).get("findings", [])
            if findings:
                for finding in findings:
                    conf = finding.get("confidence", "unknown")
                    verified = finding.get("verified")
                    icon, label, color = CONFIDENCE_CONFIG.get(conf, ("❓", conf.title(), "#6b7280"))
                    # Override for unverified confirmed
                    if conf == "confirmed" and verified is False:
                        icon, label, color = CONFIDENCE_CONFIG["unverified"]

                    st.markdown(f"""
                    <div class="finding-card">
                        <span class="conf-badge" style="background:{color}20;color:{color};">
                            {icon} {label}
                        </span>
                        <div class="description">{finding.get('description', 'No description.')}</div>
                        {f'<div class="citation">📌 {finding["line_ref"]}</div>' if finding.get("line_ref") else ''}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("No root cause findings were returned by the AI.")

        # Diagnostic checks
        st.markdown("#### 🛠️ Diagnostic Checks & Escalation")
        checks = ai.get("diagnostic_checks", [])
        if checks:
            ro_checks = [c for c in checks if c.get("type") == "read_only"]
            td_checks = [c for c in checks if c.get("type") != "read_only"]

            if ro_checks:
                st.markdown("**🟢 Safe to run (read-only)**")
                for i, check in enumerate(ro_checks, 1):
                    st.markdown(f"""
                    <div class="check-card check-readonly">
                        <span class="check-badge badge-ro">#{i} Read‑only</span>
                        <div>
                            <div class="check-action">{check.get('action', '')}</div>
                            <div class="check-hyp">Tests: {check.get('tests_hypothesis', '')}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            if td_checks:
                st.markdown("**🟠 Requires owning team decision**")
                for i, check in enumerate(td_checks, 1):
                    st.markdown(f"""
                    <div class="check-card check-team">
                        <span class="check-badge badge-td">#{i} Team decision</span>
                        <div>
                            <div class="check-action">{check.get('action', '')}</div>
                            <div class="check-hyp">Tests: {check.get('tests_hypothesis', '')}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.caption("No diagnostic checks were returned.")

        escalation = ai.get("escalation", {})
        if escalation.get("should_escalate"):
            st.markdown(f"""
            <div class="escalation-box">
                <div class="esc-title">🚨 Escalation Required</div>
                <div class="esc-body">
                    <strong>Escalate to:</strong> {escalation.get('to', 'Owning service team')}<br>
                    <strong>Reason:</strong> {escalation.get('reason', '')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:0.75rem 1rem;margin-top:0.75rem;color:#15803d;font-size:0.85rem;">
                ✅ No escalation required at this time.
            </div>
            """, unsafe_allow_html=True)

    # ── Tab 2: Evidence & Timeline ─────────────────────────────────────────────
    with tab_evidence:
        timeline = analysis.get("timeline", [])
        if timeline:
            timeline_df = pd.DataFrame(timeline)
            ts_col = "timestamp"
            if ts_col in timeline_df.columns:
                timeline_df[ts_col] = pd.to_datetime(timeline_df[ts_col], errors="coerce")
                valid_ts = timeline_df.dropna(subset=[ts_col])
                if not valid_ts.empty:
                    st.markdown("#### 📈 Errors & Warnings Over Time")
                    chart_data = (
                        valid_ts.set_index(ts_col)
                        .resample("min")
                        .size()
                        .rename("Events per minute")
                    )
                    if not chart_data.empty:
                        st.bar_chart(chart_data, use_container_width=True, height=220)

            st.markdown("#### 🗒️ Log Evidence (Warnings & Errors)")
            display_df = timeline_df.copy()
            if "timestamp" in display_df.columns:
                display_df["timestamp"] = display_df["timestamp"].astype(str).str[:19]
            # Color-code the level column
            level_colors = {
                "ERROR": "🔴",
                "FATAL": "💀",
                "CRITICAL": "💀",
                "WARN": "🟡",
            }
            if "level" in display_df.columns:
                display_df["level"] = display_df["level"].map(lambda x: f"{level_colors.get(x, '⚪')} {x}")

            st.dataframe(
                display_df[["line_number", "timestamp", "level", "source", "message"]],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "line_number": st.column_config.NumberColumn("Line", width="small"),
                    "timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
                    "level": st.column_config.TextColumn("Level", width="small"),
                    "source": st.column_config.TextColumn("Service", width="medium"),
                    "message": st.column_config.TextColumn("Message", width="large"),
                },
            )
        else:
            st.markdown("""
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:1.5rem;text-align:center;color:#15803d;margin-top:1rem;">
                <div style="font-size:2rem">✅</div>
                <div style="font-weight:600;margin-top:0.5rem">No warnings or errors found</div>
                <div style="font-size:0.85rem;opacity:0.75;margin-top:0.25rem">This log appears healthy — no events to chart.</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tab 3: Report ──────────────────────────────────────────────────────────
    with tab_report:
        st.markdown("#### 📄 Incident Report")
        st.caption("This report is suitable for sharing with an operations or engineering team.")

        c1, c2 = st.columns([1, 1])
        with c1:
            st.download_button(
                "⬇️ Download as Markdown",
                data=report,
                file_name=f"incident_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True,
                type="primary",
            )
        with c2:
            if st.button("📋 Show Markdown Source", use_container_width=True):
                st.session_state["show_md_src"] = not st.session_state.get("show_md_src", False)

        if st.session_state.get("show_md_src"):
            st.code(report, language="markdown")

        st.markdown("---")
        st.markdown(report)
