import sys
import os
import uuid
import time
import random
from datetime import datetime

import plotly.graph_objects as go
import pandas as pd

import streamlit as st

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from src.orchestration.manager import process_transaction
    from src.utils.logger import get_recent_decisions, get_decision_stats
    _PIPELINE_OK = True
    _PIPELINE_ERR = ""
except Exception as _e:
    _PIPELINE_OK = False
    _PIPELINE_ERR = str(_e)

st.set_page_config(
    page_title="FraudPulse — Decision Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Body ───────────────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] {
    background: #f8fafc;
    color: #0f172a;
    font-family: Arial, sans-serif;
}
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 2px solid #e2e8f0;
}

/* ── Header ─────────────────────────────────────────────────────────────── */
.fp-header {
    padding: 1rem 0;
    text-align: center;
    border-bottom: 2px solid #2563eb;
    margin-bottom: 1rem;
    background-color: #ffffff;
}
.fp-header h1 {
    font-size: 2.2rem;
    font-weight: bold;
    color: #2563eb;
    margin-bottom: 0px;
}
.fp-header p {
    color: #475569;
    font-size: 1rem;
}

/* ── Decision Badge ─────────────────────────────────────────────────────── */
.decision-badge {
    display: inline-block;
    padding: 0.4rem 1rem;
    border-radius: 4px; /* Less rounded */
    font-size: 1rem;
    font-weight: bold;
    border: 1px solid #000;
    margin-bottom: 0.75rem;
}
.badge-allow    { background:#dcfce7; color:#166534; border-color:#166534; }
.badge-verify   { background:#fef3c7; color:#92400e; border-color:#92400e; }
.badge-block    { background:#fee2e2; color:#991b1b; border-color:#991b1b; }
.badge-escalate { background:#f3e8ff; color:#6b21a8; border-color:#6b21a8; }

/* ── Cards ──────────────────────────────────────────────────────────────── */
.fp-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 4px; /* Simple corners */
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.05); /* Basic shadow */
}
.fp-card h3 {
    font-size: 1.1rem;
    font-weight: bold;
    color: #2563eb;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
}

/* ── Pipeline Step ───────────────────────────────────────────────────────── */
.pipeline-step {
    padding: 0.5rem;
    border: 1px solid #e2e8f0;
    margin-bottom: 0.5rem;
    background: #f8fafc;
}
.pipeline-step.done    { border-left: 4px solid #16a34a; }
.pipeline-step .step-icon { font-size: 1.2rem; margin-right: 5px; }
.pipeline-step .step-name {
    font-size: 0.95rem;
    font-weight: bold;
    color: #1e293b;
}
.pipeline-step .step-status {
    font-size: 0.85rem;
    color: #475569;
    display: block;
    margin-left: 1.5rem;
}
.pipeline-step.done .step-status { color: #166534; }

/* ── Reason pill ─────────────────────────────────────────────────────────── */
.reason-pill {
    display: block;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    padding: 0.2rem 0.5rem;
    font-size: 0.9rem;
    color: #334155;
    margin-bottom: 0.2rem;
}

/* ── Metric override ─────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    padding: 0.5rem;
}
[data-testid="stMetricLabel"] { color: #475569 !important; font-weight: bold; }
[data-testid="stMetricValue"] { color: #0f172a !important; }

/* ── Sidebar label ────────────────────────────────────────────────────────── */
.sidebar-section {
    font-size: 1rem;
    font-weight: bold;
    color: #2563eb;
    margin: 1rem 0 0.5rem;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 5px;
}
</style>
""", unsafe_allow_html=True)

DECISION_CFG: dict[str, dict] = {
    "allow":    {"emoji": "✅", "badge": "badge-allow",    "label": "APPROVED",   "color": "#16a34a"},
    "verify":   {"emoji": "🔔", "badge": "badge-verify",   "label": "VERIFY",     "color": "#ca8a04"},
    "block":    {"emoji": "🚫", "badge": "badge-block",    "label": "BLOCKED",    "color": "#dc2626"},
    "escalate": {"emoji": "🚨", "badge": "badge-escalate", "label": "ESCALATED",  "color": "#9333ea"},
}

PIPELINE_STAGES = [
    ("🔬", "Detection Agent",    "Flags suspicious score tier"),
    ("🔎", "Verification Agent", "Scores contextual risk factors"),
    ("⚙️", "Decision Engine",    "Maps risk level → action"),
    ("👤", "Customer Agent",     "Simulates OTP / push confirmation"),
    ("📋", "Escalation Agent",   "Finalises & logs outcome"),
]

if "history" not in st.session_state:
    st.session_state.history: list[dict] = []
if "last_result" not in st.session_state:
    st.session_state.last_result: dict | None = None

st.markdown("""
<div class="fp-header">
    <h1>FraudPulse Dashboard</h1>
    <p>Final Year Project - Decision Intelligence Platform</p>
</div>
""", unsafe_allow_html=True)

if not _PIPELINE_OK:
    st.error(f"⚠️ Pipeline could not be loaded: `{_PIPELINE_ERR}`")
    st.info("Make sure you run Streamlit from the **project root** directory:\n"
            "```bash\nstreamlit run dashboard/streamlit_app.py\n```")
    st.stop()

with st.sidebar:
    st.markdown('<h2 style="color: #2563eb; margin-bottom: 0;">🔍 FraudPulse</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color: #475569; font-size: 0.9rem; margin-top: 0;">Rule-Based Decision Intelligence</p>', unsafe_allow_html=True)
    st.divider()

    st.markdown('<div class="sidebar-section">Transaction Parameters</div>', unsafe_allow_html=True)

    fraud_score = st.slider(
        "Fraud Score (ML Output)",
        min_value=0.0, max_value=1.0, value=0.55, step=0.01,
        help="Probability of fraud as output by the ML scoring model."
    )

    amount = st.number_input(
        "Transaction Amount ($)",
        min_value=0.0, max_value=500_000.0, value=2_500.0, step=100.0,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        is_known_device = st.toggle("Known Device", value=True)
    with col_b:
        is_foreign = st.toggle("Foreign Txn", value=False)

    txn_hour = st.slider(
        "Transaction Hour",
        min_value=0, max_value=23, value=14,
        format="%d:00",
        help="0 = midnight, 23 = 11 PM"
    )

    velocity = st.slider(
        "Velocity (txns / hr)",
        min_value=1, max_value=20, value=2,
        help="How many transactions this account made in the last hour."
    )

    st.divider()
    analyze_btn = st.button(
        "🔍 Analyze Transaction",
        use_container_width=True,
        type="primary",
    )

    st.markdown('<div class="sidebar-section">Batch Simulation</div>', unsafe_allow_html=True)
    batch_count = st.slider("Simulations", 5, 100, 20)
    batch_btn   = st.button("▶ Run Batch", use_container_width=True)

    st.divider()
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.history   = []
        st.session_state.last_result = None
        st.rerun()

    if st.session_state.history:
        st.divider()
        st.markdown('<div class="sidebar-section">Session Stats</div>', unsafe_allow_html=True)
        total = len(st.session_state.history)
        st.metric("Total Analyzed", total)
        breakdown: dict[str, int] = {}
        for r in st.session_state.history:
            k = r.get("decision", "?")
            breakdown[k] = breakdown.get(k, 0) + 1
        for d, cnt in sorted(breakdown.items()):
            cfg = DECISION_CFG.get(d, {"emoji": "?", "label": d.upper(), "color": "#888"})
            st.markdown(
                f"{cfg['emoji']} **{cfg['label']}** — {cnt} &nbsp; "
                f"({cnt/total*100:.0f}%)",
                unsafe_allow_html=True,
            )

def make_gauge(risk_score: float, fraud_score: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_score,
        number={"suffix": " / 100", "font": {"size": 24, "color": "#0f172a"}},
        title={"text": "Composite Risk Score", "font": {"size": 14, "color": "#475569"}},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": "#94a3b8",
            },
            "bar": {"color": "#2563eb", "thickness": 0.3},
            "bgcolor": "#f1f5f9",
            "borderwidth": 1,
            "bordercolor": "#cbd5e1",
            "steps": [
                {"range": [0,  25], "color": "#dcfce7"},
                {"range": [25, 50], "color": "#fef08a"},
                {"range": [50, 75], "color": "#fca5a5"},
                {"range": [75, 100], "color": "#d8b4fe"},
            ],
            "threshold": {
                "line": {"color": "#ef4444", "width": 4},
                "thickness": 0.75,
                "value": risk_score,
            },
        },
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"family": "Arial"},
    )
    return fig

def make_history_donut(history: list[dict]) -> go.Figure:
    counts: dict[str, int] = {}
    for r in history:
        k = r.get("decision", "unknown")
        counts[k] = counts.get(k, 0) + 1

    labels = list(counts.keys())
    values = list(counts.values())
    
    color_map = {
        "allow": "#4ade80",
        "verify": "#facc15",
        "block": "#f87171",
        "escalate": "#c084fc",
        "unknown": "#94a3b8"
    }
    colors = [color_map.get(l, "#94a3b8") for l in labels]

    fig = go.Figure(go.Pie(
        labels=[DECISION_CFG.get(l, {"label": l.upper()})["label"] for l in labels],
        values=values,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color="#ffffff", width=1)),
        textinfo="label+percent",
        textfont={"color": "#0f172a", "size": 12},
    ))
    fig.update_layout(
        showlegend=False,
        height=220,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#ffffff",
    )
    return fig

def render_pipeline(result: dict) -> None:
    st.markdown('<div class="fp-card"><h3>🔗 Agent Pipeline</h3>', unsafe_allow_html=True)

    detection    = result.get("detection",    {})
    verification = result.get("verification", {})
    engine_r     = result.get("engine",       {})
    customer     = result.get("customer",     {})

    stage_details = [
        f"Confidence: {detection.get('confidence','?').upper()}",
        f"Risk score: {verification.get('risk_score','?')}/100",
        f"Action: {engine_r.get('action','?').upper()}",
        f"Response: {customer.get('customer_response','?')}",
        f"Final: {result.get('decision','?').upper()}",
    ]

    for (icon, name, desc), detail in zip(PIPELINE_STAGES, stage_details):
        st.markdown(
            f'<div class="pipeline-step done">'
            f'  <div><span class="step-icon">{icon}</span><span class="step-name">{name}</span></div>'
            f'  <span class="step-status">{detail}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

def render_result(result: dict) -> None:
    decision = result.get("decision", "block")
    cfg      = DECISION_CFG.get(decision, DECISION_CFG["block"])
    ver      = result.get("verification", {})
    det      = result.get("detection",    {})
    cust     = result.get("customer",     {})

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Decision", f"{cfg['emoji']} {cfg['label']}")
    with c2:
        st.metric("Risk Level", result.get("risk_level", "?").upper())
    with c3:
        st.metric("Fraud Score", f"{result.get('fraud_score', 0):.2%}")
    with c4:
        st.metric("Risk Score", f"{ver.get('risk_score', 0):.1f} / 100")

    st.markdown(
        f'<div style="text-align:center; margin: 0.5rem 0 1rem;">'
        f'<span class="decision-badge {cfg["badge"]}">{cfg["emoji"]} {cfg["label"]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1])

    with left:
        
        st.plotly_chart(
            make_gauge(ver.get("risk_score", 0), result.get("fraud_score", 0)),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with right:
        render_pipeline(result)

    st.markdown('<div class="fp-card"><h3>⚠️ Risk Factors</h3>', unsafe_allow_html=True)
    pills = "".join(
        f'<span class="reason-pill">• {r}</span>'
        for r in ver.get("reasons", ["None identified"])
    )
    st.markdown(pills, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    d1, d2 = st.columns(2)
    with d1:
        st.markdown('<div class="fp-card"><h3>🔬 Detection Agent</h3>', unsafe_allow_html=True)
        conf = det.get("confidence", "?")
        msg  = det.get("message", "")
        color = {
            "very_low": "#4ade80", "low": "#4ade80",
            "medium": "#fbbf24", "high": "#f87171", "critical": "#c084fc"
        }.get(conf, "#94a3b8")
        st.markdown(
            f'<span style="color:{color};font-weight:700">{conf.upper()}</span> — {msg}',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with d2:
        st.markdown('<div class="fp-card"><h3>👤 Customer Agent</h3>', unsafe_allow_html=True)
        if cust.get("confirmation_required"):
            resp = cust.get("customer_response", "?")
            icon = "✅" if resp == "confirmed" else "❌"
            color = "#4ade80" if resp == "confirmed" else "#f87171"
            st.markdown(
                f'<span style="color:{color}">{icon} {cust.get("message","")}</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span style="color:#64748b">No confirmation required for this risk level.</span>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("📋 Full Reason Chain & Action Detail"):
        st.code(result.get("reason", ""), language=None)
        st.info(f"**Action:** {result.get('action_detail', '')}")
        st.caption(f"Transaction ID: `{result.get('transaction_id','?')}`")

if analyze_btn:
    features = {
        "amount":                amount,
        "is_known_device":       is_known_device,
        "transaction_hour":      txn_hour,
        "is_foreign_transaction": is_foreign,
        "velocity":              velocity,
    }
    with st.spinner("🔍 Running fraud analysis pipeline…"):
        time.sleep(0.25)   
        result = process_transaction(
            fraud_score=fraud_score,
            features=features,
            transaction_id=str(uuid.uuid4())[:8].upper(),
        )

    st.session_state.last_result = result
    st.session_state.history.insert(0, {**result, "_ts": datetime.utcnow().isoformat()})

    st.success(f"Analysis complete — Decision: **{result['decision'].upper()}**")
    render_result(result)

elif st.session_state.last_result:
    
    render_result(st.session_state.last_result)
else:
    
    st.markdown("""
    <div style="text-align:center; padding:4rem 0; color:#334155;">
        <div style="font-size:3rem; margin-bottom:1rem;">🔍</div>
        <div style="font-size:1.2rem; font-weight:600; color:#475569;">
            Configure a transaction in the sidebar and click <em>Analyze</em>
        </div>
        <div style="font-size:0.85rem; margin-top:0.5rem; color:#1e3a5f;">
            Or run a Batch Simulation to populate history
        </div>
    </div>
    """, unsafe_allow_html=True)

if batch_btn:
    prog  = st.progress(0, text="Running batch simulation…")
    results: list[dict] = []
    for i in range(batch_count):
        fs = random.random()
        feats = {
            "amount":                round(random.uniform(1.0, 18_000.0), 2),
            "is_known_device":       random.choice([True, True, True, False]),
            "transaction_hour":      random.randint(0, 23),
            "is_foreign_transaction": random.choice([True, False, False]),
            "velocity":              random.randint(1, 12),
        }
        r = process_transaction(fs, feats)
        results.append({**r, "_ts": datetime.utcnow().isoformat()})
        st.session_state.history.insert(0, results[-1])
        prog.progress((i + 1) / batch_count, text=f"Simulating {i+1}/{batch_count}…")

    prog.empty()
    st.success(f"✅ Batch complete — {batch_count} transactions analyzed.")

    bd_col, tbl_col = st.columns([1, 2])
    with bd_col:
        st.markdown("##### Decision Breakdown")
        st.plotly_chart(
            make_history_donut(results),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with tbl_col:
        st.markdown("##### Batch Results")
        df_batch = pd.DataFrame([{
            "ID":         r.get("transaction_id","?"),
            "Score":      f"{r.get('fraud_score',0):.2%}",
            "Risk Level": r.get("risk_level","?").upper(),
            "Decision":    r.get("decision","?").upper(),
        } for r in results])
        st.dataframe(df_batch, use_container_width=True, height=260)

if st.session_state.history:
    st.divider()
    st.markdown("### 📋 Analysis History")

    hist_col, chart_col = st.columns([2, 1])

    with hist_col:
        df_hist = pd.DataFrame([{
            "Timestamp": h.get("_ts","")[:19].replace("T"," "),
            "ID":        h.get("transaction_id","?"),
            "Fraud Score": f"{h.get('fraud_score',0):.2%}",
            "Risk Level": h.get("risk_level","?").upper(),
            "Decision":   h.get("decision","?").upper(),
            "Risk Score":  h.get("verification",{}).get("risk_score","?"),
        } for h in st.session_state.history[:100]])
        st.dataframe(df_hist, use_container_width=True, height=320)

    with chart_col:
        st.markdown("##### Session Breakdown")
        st.plotly_chart(
            make_history_donut(st.session_state.history),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        total_hist = len(st.session_state.history)
        avg_score  = sum(h.get("fraud_score", 0) for h in st.session_state.history) / total_hist
        st.metric("Avg Fraud Score", f"{avg_score:.2%}")
        st.metric("Total Analyzed",  total_hist)
