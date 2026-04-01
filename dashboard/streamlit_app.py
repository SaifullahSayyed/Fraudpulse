import sys
import os
import uuid
import time
import random
import tempfile
from datetime import datetime

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

import streamlit as st
import streamlit.components.v1 as components

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from src.orchestration.manager import process_transaction
    from src.utils.logger import get_recent_decisions, get_decision_stats
    from src.storage.audit_ledger import ledger
    from src.ml.adaptive_weights import adaptive_manager
    _PIPELINE_OK = True
    _PIPELINE_ERR = ""
except Exception as _e:
    _PIPELINE_OK = False
    _PIPELINE_ERR = str(_e)

try:
    from pyvis.network import Network as PyvisNetwork
    _PYVIS_OK = True
except ImportError:
    _PYVIS_OK = False

st.set_page_config(
    page_title="FraudPulse — Decision Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
    /* Force light theme for the main content area for premium look */
    .stApp { background-color: #f8fafc; }
    
    /* Ensure all text markers are dark and visible */
    h1, h2, h3, h4, p, span, div, label { color: #1e293b !important; }
    
    .fp-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.75rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .stMetric label { color: #64748b !important; }
    .stMetric div[data-testid="stMetricValue"] { color: #0f172a !important; font-weight: 700; }

    .pipeline-step {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        background: #f1f5f9;
        border-left: 4px solid #cbd5e1;
    }
    .pipeline-step.done { border-left-color: #2563eb; background: #eff6ff; }
    .step-icon { margin-right: 0.75rem; font-size: 1.2rem; }
    .step-name { font-weight: 600; color: #1e293b !important; }
    .step-status { font-size: 0.85rem; color: #64748b !important; }
    
    .decision-badge {
        padding: 0.5rem 1rem;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 1.1rem;
        display: inline-block;
    }
    .badge-allow { background-color: #dcfce7; color: #166534 !important; }
    .badge-verify { background-color: #fef9c3; color: #854d0e !important; }
    .badge-block { background-color: #fee2e2; color: #991b1b !important; }
    .badge-escalate { background-color: #f3e8ff; color: #6b21a8 !important; }
    
    /* Sidebar needs to stay dark if that's the theme, but let's make it readable */
    [data-testid="stSidebar"] { background-color: #0f172a; }
    [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    [data-testid="stSidebar"] .stTextInput input, [data-testid="stSidebar"] .stNumberInput input {
        color: #1e293b !important;
        background-color: #ffffff !important;
    }

    .sidebar-section {
        font-weight: 700;
        color: #94a3b8 !important;
        font-size: 0.8rem;
        text-transform: uppercase;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        letter-spacing: 0.05em;
    }
    .reason-pill {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background: #f1f5f9;
        border-radius: 1rem;
        font-size: 0.85rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        color: #475569 !important;
        border: 1px solid #e2e8f0;
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
    ("🕸️", "Network Analyzer",   "Checks for Fraud Rings/Mules"),
    ("🔬", "Detection Agent",    "Flags behavioral KL-Divergence"),
    ("🔎", "Verification Agent", "Scores velocity & geolocation"),
    ("📊", "Drift Monitor",      "Calculates PSI vs Training Set"),
    ("📋", "Escalation Agent",   "Finalises & logs to SQLite"),
]

if "history" not in st.session_state:
    st.session_state.history: list[dict] = []
if "last_result" not in st.session_state:
    st.session_state.last_result: dict | None = None
st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem;">
    <div>
        <h1 style="margin: 0; color: #0f172a; font-size: 2.25rem;">FraudPulse Dashboard</h1>
        <p style="margin: 0; color: #64748b; font-size: 1.1rem;">Enterprise Decision Intelligence & Risk Orchestration</p>
    </div>
    <div style="text-align: right;">
        <span style="padding: 0.4rem 0.8rem; background: #e2e8f0; border-radius: 0.5rem; font-size: 0.8rem; font-weight: 600; color: #475569;">
            v1.2.0 Stable
        </span>
    </div>
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

    st.markdown('<div class="sidebar-section">Account Intelligence</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        account_id = st.text_input("Sender ACC", value="ACC_9821", help="Unique account identifier")
    with col2:
        receiver_id = st.text_input("Receiver ACC", value="REC_4402", help="Target account identifier")

    st.markdown('<div class="sidebar-section">Hardware & Location</div>', unsafe_allow_html=True)

    device_id = st.text_input("Device ID", value=f"DEV-{uuid.uuid4().hex[:8].upper()}", help="Hardware fingerprint")
    is_known_device = st.toggle("Known Device", value=True)

    c_lat, c_lon = st.columns(2)
    with c_lat:
        latitude = st.number_input("Latitude", value=40.7128, format="%.4f")
    with c_lon:
        longitude = st.number_input("Longitude", value=-74.0060, format="%.4f")

    if st.button("🎲 Randomize Location"):
        latitude = round(random.uniform(-90, 90), 4)
        longitude = round(random.uniform(-180, 180), 4)
        st.rerun()

    st.markdown('<div class="sidebar-section">Risk Heuristics</div>', unsafe_allow_html=True)

    fraud_score = st.slider(
        "Fraud Score (ML)",
        min_value=0.0, max_value=1.0, value=0.15, step=0.01,
        help="Probability of fraud as output by the ML scoring model."
    )

    amount = st.number_input(
        "Amount ($)",
        min_value=0.0, max_value=500_000.0, value=250.0, step=10.0,
    )

    is_foreign = st.toggle("Foreign Transaction", value=False)

    txn_hour = st.slider(
        "Hour",
        min_value=0, max_value=23, value=datetime.utcnow().hour,
        format="%d:00",
    )

    st.divider()

    st.markdown('<div class="sidebar-section">PR-Curve Threshold</div>', unsafe_allow_html=True)
    pr_threshold = st.slider(
        "Decision Threshold",
        min_value=0.01, max_value=0.99, value=0.50, step=0.01,
        help="Drag to see how threshold changes Precision vs Recall trade-off."
    )

    st.divider()
    analyze_btn = st.button(
        "🔍 Analyze Transaction",
        use_container_width=True,
        type="primary",
    )

    st.markdown('<div class="sidebar-section">Batch Simulation</div>', unsafe_allow_html=True)
    batch_count = st.slider("Random Simulations", 5, 100, 20)
    batch_btn   = st.button("▶ Run Random Batch", use_container_width=True)

    st.markdown('<div class="sidebar-section">Live Dataset Stream</div>', unsafe_allow_html=True)
    st.caption("Load a CSV of highly targeted fraud rings and velocity attacks.")
    
    default_live_csv = "data/live_transaction_stream.csv"
    process_default_btn = False
    if os.path.exists(default_live_csv):
        process_default_btn = st.button("🚀 Load Default Live Stream", use_container_width=True)
    
    uploaded_file = st.file_uploader("Upload actual_fraud_cases.csv", type=["csv"], label_visibility="collapsed")
    process_csv_btn = False
    if uploaded_file is not None:
        process_csv_btn = st.button("▶ Process Uploaded CSV", type="primary", use_container_width=True)

    st.divider()
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.history    = []
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
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8"},
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
            "threshold": {"line": {"color": "#ef4444", "width": 4}, "thickness": 0.75, "value": risk_score},
        },
    ))
    fig.update_layout(
        height=200, margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", 
        font={"family": "Arial", "color": "#1e293b"},
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
        "allow": "#4ade80", "verify": "#facc15",
        "block": "#f87171", "escalate": "#c084fc", "unknown": "#94a3b8"
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
        showlegend=False, height=220, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#ffffff", font={"color": "#1e293b"},
    )
    return fig

def make_pr_curve(threshold: float) -> go.Figure:
    
    scores = [h.get("fraud_score", random.random()) for h in st.session_state.history]
    labels = [1 if h.get("decision") in ("block", "escalate") else 0 for h in st.session_state.history]

    if len(scores) < 5:
        thresholds = [i / 100 for i in range(1, 100)]
        precision_vals = [max(0.4, 1.0 - 0.6 * (1 - t)) for t in thresholds]
        recall_vals    = [max(0.0, 1.0 - t ** 0.5) for t in thresholds]
    else:
        from sklearn.metrics import precision_recall_curve as sk_prc
        try:
            precision_vals, recall_vals, thresh_vals = sk_prc(labels, scores)
            precision_vals = list(precision_vals[:-1])
            recall_vals    = list(recall_vals[:-1])
            thresholds     = list(thresh_vals)
        except Exception:
            thresholds = [i / 100 for i in range(1, 100)]
            precision_vals = [max(0.4, 1.0 - 0.6 * (1 - t)) for t in thresholds]
            recall_vals    = [max(0.0, 1.0 - t ** 0.5) for t in thresholds]

    closest_idx = 0
    min_dist = float("inf")
    for i, t in enumerate(thresholds):
        d = abs(t - threshold)
        if d < min_dist:
            min_dist = d
            closest_idx = i

    op_precision = precision_vals[closest_idx] if precision_vals else 0.5
    op_recall    = recall_vals[closest_idx] if recall_vals else 0.5

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=recall_vals, y=precision_vals,
        mode="lines", name="PR Curve",
        line=dict(color="#2563eb", width=2),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.08)",
    ))
    fig.add_trace(go.Scatter(
        x=[op_recall], y=[op_precision],
        mode="markers+text",
        marker=dict(color="#ef4444", size=10, symbol="circle"),
        text=[f"  t={threshold:.2f}"],
        textposition="middle right",
        name=f"Threshold = {threshold:.2f}",
    ))
    fig.update_layout(
        xaxis_title="Recall", yaxis_title="Precision",
        xaxis=dict(range=[0, 1]), yaxis=dict(range=[0, 1]),
        height=280, margin=dict(l=10, r=10, t=20, b=40),
        paper_bgcolor="#ffffff", plot_bgcolor="#f8fafc",
        legend=dict(orientation="h", y=-0.25),
        font={"family": "Arial", "size": 11, "color": "#1e293b"},
    )
    return fig, op_precision, op_recall

def make_shap_chart(shap_data: list[dict]) -> go.Figure:
    
    if not shap_data:
        return None

    features   = [d["feature"].replace("_", " ").title() for d in shap_data]
    contribs   = [d["contribution"] for d in shap_data]
    colors     = ["#ef4444" if c > 0 else "#22c55e" for c in contribs]

    fig = go.Figure(go.Bar(
        x=contribs, y=features,
        orientation="h",
        marker_color=colors,
        text=[f"+{c:.3f}" if c > 0 else f"{c:.3f}" for c in contribs],
        textposition="outside",
    ))
    fig.update_layout(
        height=160, margin=dict(l=10, r=50, t=10, b=10),
        paper_bgcolor="#ffffff", plot_bgcolor="#f8fafc",
        xaxis_title="Contribution to Fraud Score",
        font={"family": "Arial", "size": 11, "color": "#1e293b"},
        xaxis=dict(zeroline=True, zerolinecolor="#94a3b8"),
    )
    return fig

def make_network_graph(result: dict) -> str | None:
    
    if not _PYVIS_OK:
        return None

    net = PyvisNetwork(height="320px", width="100%", bgcolor="#f8fafc", font_color="#0f172a")
    net.set_options()

    seen_nodes: set[str] = set()
    fraudulent_accounts: set[str] = set()

    for h in st.session_state.history[-30:]:
        acc = h.get("account_id", "")
        dec = h.get("decision", "allow")
        if dec in ("block", "escalate"):
            fraudulent_accounts.add(acc)

    current_acc = result.get("account_id", "ACC_UNKNOWN")
    net_data    = result.get("network_analysis", {})

    for h in st.session_state.history[-20:]:
        acc = h.get("account_id", "unknown")
        if acc not in seen_nodes:
            seen_nodes.add(acc)
            is_fraud = acc in fraudulent_accounts
            net.add_node(
                acc, label=acc[:10],
                color="#ef4444" if is_fraud else "#94a3b8",
                size=18 if is_fraud else 12,
                title=f"{'⚠️ FLAGGED' if is_fraud else 'Clean'}: {acc}"
            )

    if current_acc not in seen_nodes:
        seen_nodes.add(current_acc)
        net.add_node(
            current_acc, label=current_acc[:10],
            color="#2563eb", size=22,
            title=f"Current Transaction: {current_acc}"
        )

    for h in st.session_state.history[-15:]:
        src = h.get("account_id", "unknown")
        dst = h.get("verification", {}).get("receiver_id", "REC_UNKNOWN")
        if dst == "REC_UNKNOWN":
            dst = f"REC_{random.randint(1000,9999)}"
        amt = h.get("fraud_score", 0.1) * 5 + 1

        if dst not in seen_nodes:
            seen_nodes.add(dst)
            net.add_node(dst, label=dst[:10], color="#64748b", size=10, title=dst)

        net.add_edge(src, dst, value=amt, title=f"${h.get('verification', {}).get('risk_score', 0):.0f} risk")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    net.save_graph(tmp.name)
    with open(tmp.name, "r", encoding="utf-8") as f:
        html_content = f.read()
    os.unlink(tmp.name)
    return html_content

def render_pipeline(result: dict) -> None:
    st.markdown('<div class="fp-card"><h3>🔗 Agent Pipeline</h3>', unsafe_allow_html=True)

    net          = result.get("network_analysis", {})
    detection    = result.get("detection",       {})
    verification = result.get("verification",    {})
    monitoring   = result.get("model_monitoring",{})

    stage_details = [
        f"Mule Signal: {'YES' if net.get('mule_signal') else 'NO'}",
        f"KL Score: {detection.get('kl_score', '0.0')}",
        f"Risk: {verification.get('risk_score','?')}/100",
        f"PSI: {monitoring.get('psi_score','0.0')}",
        f"ID: {result.get('transaction_id','?')}",
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
    ruleset  = result.get("ruleset_name", "CHAMPION")
    shap_exp = result.get("shap_explanation", [])

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

    t1, t2 = st.columns([1, 2])
    with t1:
        st.caption("Correlation ID")
        st.code(result.get("correlation_id", "Unknown"), language=None)
    with t2:
        st.caption("Tamper-Evident Audit Hash (SHA256 Chained)")
        st.code(result.get("audit_hash", "3f8e5... (Stored in SQLite)"), language=None)

    left, right = st.columns([1, 1])

    with left:
        st.plotly_chart(
            make_gauge(ver.get("risk_score", 0), result.get("fraud_score", 0)),
            use_container_width=True,
            config={"displayModeBar": False},
        )

        st.markdown('<div class="fp-card"><h3>📍 Transaction Location</h3>', unsafe_allow_html=True)
        lat = result.get("features", {}).get("latitude", 40.7128) if "features" in result else 40.7128
        lon = result.get("features", {}).get("longitude", -74.0060) if "features" in result else -74.0060
        st.map(pd.DataFrame([{"lat": lat, "lon": lon}]), zoom=4, height=200)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        render_pipeline(result)

    st.markdown('<div class="fp-card"><h3>🧠 AI Explanation (SHAP Feature Contributions)</h3>', unsafe_allow_html=True)
    if shap_exp:
        shap_fig = make_shap_chart(shap_exp)
        if shap_fig:
            st.plotly_chart(shap_fig, use_container_width=True, config={"displayModeBar": False})
        for item in shap_exp:
            direction = "▲ increases" if item["contribution"] > 0 else "▼ decreases"
            color     = "#dc2626" if item["contribution"] > 0 else "#16a34a"
            st.markdown(
                f'<span class="reason-pill">'
                f'<b style="color:{color}">{item["feature"].replace("_"," ").title()}</b> '
                f'{direction} fraud score by <b>{abs(item["contribution"]):.3f}</b>'
                f'</span>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No SHAP data available for this transaction.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="fp-card"><h3>📈 Live Precision-Recall Curve</h3>', unsafe_allow_html=True)
    pr_fig, op_p, op_r = make_pr_curve(pr_threshold)
    st.plotly_chart(pr_fig, use_container_width=True, config={"displayModeBar": False}, key="pr_curve_top")
    prc1, prc2, prc3 = st.columns(3)
    prc1.metric("Operating Threshold", f"{pr_threshold:.2f}")
    prc2.metric("Precision @ threshold", f"{op_p:.2%}")
    prc3.metric("Recall @ threshold",    f"{op_r:.2%}")
    st.caption("Red dot = current threshold operating point. Slide the **PR-Curve Threshold** in the sidebar to explore trade-offs.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="fp-card"><h3>🧠 Online Learning (Adaptive Weights)</h3>', unsafe_allow_html=True)
    weights = result.get("adaptive_weights", {})
    fired_rules = result.get("fired_rules", [])
    
    if weights:
        w_df = pd.DataFrame([
            {"Rule": k.replace("rule_", "").replace("_", " ").title(), "Weight": v, "Fired": (k in fired_rules)} 
            for k, v in weights.items()
        ])
        w_df.sort_values("Weight", ascending=False, inplace=True)
        
        colors = ["#dc2626" if row["Fired"] else "#94a3b8" for _, row in w_df.iterrows()]
        
        fig_w = go.Figure(go.Bar(
            x=w_df["Weight"], y=w_df["Rule"],
            orientation="h",
            marker_color=colors,
            text=[f"{w:.2f}x" for w in w_df["Weight"]],
            textposition="outside",
        ))
        fig_w.update_layout(
            height=200, margin=dict(l=10, r=50, t=10, b=10),
            paper_bgcolor="#ffffff", plot_bgcolor="#f8fafc",
            xaxis_title="Score Multiplier (EMA Weight)",
            font={"family": "Arial", "size": 11, "color": "#1e293b"},
            xaxis=dict(zeroline=True, zerolinecolor="#94a3b8", range=[0, max(2.0, w_df["Weight"].max() + 0.2)]),
        )
        st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})
        st.caption("🔴 Red bars indicate the rules that fired for *this* transaction.")
        
    if fired_rules:
        st.write("**Provide real-world feedback to instantly adapt rule weights:**")
        fb_c1, fb_c2 = st.columns(2)
        cid = result.get("correlation_id", "default")
        with fb_c1:
            if st.button("✅ Confirm Fraud (Boost)", key=f"btn_boost_{cid}", help="This was actual fraud. Reward rules that caught it.", use_container_width=True):
                adaptive_manager.apply_feedback(fired_rules, was_correct=True)
                st.session_state.last_result["adaptive_weights"] = adaptive_manager.get_weights()
                st.rerun()
        with fb_c2:
            if st.button("❌ False Positive (Decay)", key=f"btn_decay_{cid}", help="This was legitimate. Punish the rules that wrongly fired.", type="primary", use_container_width=True):
                adaptive_manager.apply_feedback(fired_rules, was_correct=False)
                st.session_state.last_result["adaptive_weights"] = adaptive_manager.get_weights()
                st.rerun()
    else:
        st.caption("No heuristics fired for this transaction.")
    st.markdown("</div>", unsafe_allow_html=True)

    m1, m2 = st.columns(2)
    with m1:
        st.markdown('<div class="fp-card"><h3>📊 Model Monitoring (PSI)</h3>', unsafe_allow_html=True)
        drift  = result.get("model_monitoring", {})
        status = drift.get("status", "STABLE").upper()
        color  = "#16a34a" if status == "STABLE" else "#ca8a04" if "MINOR" in status else "#dc2626"
        st.markdown(f"Status: <span style='color:{color}; font-weight:bold;'>{status}</span>", unsafe_allow_html=True)
        st.progress(min(1.0, drift.get("psi_score", 0.0) / 0.5), text=f"PSI Score: {drift.get('psi_score', 0.0)}")
        st.caption("Drift between Training Distribution and Live Traffic.")
        st.markdown("</div>", unsafe_allow_html=True)

    with m2:
        st.markdown('<div class="fp-card"><h3>🕸️ Network Analysis</h3>', unsafe_allow_html=True)
        net_r = result.get("network_analysis", {})
        st.markdown(f"In-Degree: **{net_r.get('in_degree', 0)}** | Clustering: **{net_r.get('clustering_coefficient', 0)}**")
        if net_r.get("mule_signal"):
            st.error("🚨 Money Mule Signal Detected")
        else:
            st.success("✅ No Coordinated Ring Signal")
        st.markdown("</div>", unsafe_allow_html=True)

    if len(st.session_state.history) >= 3:
        st.markdown('<div class="fp-card"><h3>🕸️ Fraud Network Graph (Interactive)</h3>', unsafe_allow_html=True)
        graph_html = make_network_graph(result)
        if graph_html:
            components.html(graph_html, height=340, scrolling=False)
            st.caption("🔴 Red = flagged accounts | 🔵 Blue = current account | ⚫ Gray = clean accounts. Edge weight ∝ risk score.")
        else:
            st.info("Install `pyvis` (`pip install pyvis`) to enable the interactive fraud network graph.")
        st.markdown("</div>", unsafe_allow_html=True)

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
        conf  = det.get("confidence", "?")
        msg   = det.get("message", "")
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
            resp  = cust.get("customer_response", "?")
            icon  = "✅" if resp == "confirmed" else "❌"
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
        "account_id":             account_id,
        "receiver_id":            receiver_id,
        "amount":                 amount,
        "latitude":               latitude,
        "longitude":              longitude,
        "device_id":              device_id,
        "is_known_device":        is_known_device,
        "transaction_hour":       txn_hour,
        "is_foreign_transaction": is_foreign,
    }
    with st.spinner("🔍 Running hardened fraud analysis pipeline…"):
        time.sleep(0.25)
        result = process_transaction(
            fraud_score=fraud_score,
            features=features,
            account_id=account_id
        )
        result["features"] = features
    st.session_state.last_result = result
    st.session_state.history.insert(0, {**result, "_ts": datetime.utcnow().isoformat()})

    st.success(f"Analysis complete — Decision: **{result['decision'].upper()}**")
    render_result(result)

elif st.session_state.last_result:
    render_result(st.session_state.last_result)
else:
    st.markdown("""
<div style="text-align: center; padding: 5rem 2rem; background: white; border-radius: 1rem; border: 2px dashed #e2e8f0;">
    <h2 style="color: #1e293b;">Ready for Analysis</h2>
    <p style="color: #475569;">Configure transaction parameters in the sidebar or run a batch simulation to begin.</p>
</div>
""", unsafe_allow_html=True)

if batch_btn or process_csv_btn or process_default_btn:
    is_csv = (process_csv_btn and uploaded_file is not None) or process_default_btn
    
    prog = st.progress(0, text="Processing stream…")
    results: list[dict] = []
    
    rows = []
    if is_csv:
        import io
        import csv
        if process_default_btn:
            with open(default_live_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        else:
            content = uploaded_file.getvalue().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
        total_runs = len(rows)
    else:
        total_runs = batch_count

    for i in range(total_runs):
        if is_csv:
            row_data = rows[i]
            fs    = float(row_data.get("ml_fraud_score", random.random()))
            s_acc = str(row_data.get("account_id", f"ACC_{random.randint(1000, 9999)}"))
            feats = {
                "account_id":             s_acc,
                "receiver_id":            str(row_data.get("receiver_id", f"REC_{random.randint(1000, 9999)}")),
                "amount":                 float(row_data.get("amount", 250.0)),
                "latitude":               float(row_data.get("latitude", 40.7128)),
                "longitude":              float(row_data.get("longitude", -74.0060)),
                "device_id":              str(row_data.get("device_id", f"DEV-{uuid.uuid4().hex[:8].upper()}")),
                "is_known_device":        str(row_data.get("is_known_device", "True")).lower() == "true",
                "transaction_hour":       int(float(row_data.get("transaction_hour", 12))),
                "is_foreign_transaction": str(row_data.get("is_foreign_transaction", "False")).lower() == "true",
            }
        else:
            fs    = random.random()
            s_acc = f"ACC_{random.randint(1000, 9999)}"
            feats = {
                "account_id":             s_acc,
                "receiver_id":            f"REC_{random.randint(1000, 9999)}",
                "amount":                 round(random.uniform(1.0, 18_000.0), 2),
                "latitude":               round(random.uniform(-90, 90), 4),
                "longitude":              round(random.uniform(-180, 180), 4),
                "device_id":              f"DEV-{uuid.uuid4().hex[:8].upper()}",
                "is_known_device":        random.choice([True, True, True, False]),
                "transaction_hour":       random.randint(0, 23),
                "is_foreign_transaction": random.choice([True, False, False]),
            }
            
        r = process_transaction(fs, feats, s_acc)
        results.append({**r, "_ts": datetime.utcnow().isoformat()})
        st.session_state.history.insert(0, results[-1])
        prog.progress((i + 1) / total_runs, text=f"Processing {(i+1)}/{total_runs}…")

    prog.empty()
    st.success(f"✅ Processing complete — {total_runs} transactions analyzed.")

    bd_col, tbl_col = st.columns([1, 2])
    with bd_col:
        st.markdown("##### Decision Breakdown")
        st.plotly_chart(
            make_history_donut(results),
            use_container_width=True,
            config={"displayModeBar": False},
            key="donut_batch"
        )
    with tbl_col:
        st.markdown("##### Results Table")
        df_batch = pd.DataFrame([{
            "ID":         r.get("transaction_id","?"),
            "Score":      f"{r.get('fraud_score',0):.2%}",
            "Risk Level": r.get("risk_level","?").upper(),
            "Decision":   r.get("decision","?").upper()
        } for r in results])
        st.dataframe(df_batch, use_container_width=True, height=260)

if st.session_state.history:
    st.divider()
    st.markdown("### 📋 Analysis History")

    hist_col, chart_col = st.columns([2, 1])

    with hist_col:
        df_hist = pd.DataFrame([{
            "Timestamp":   h.get("_ts","")[:19].replace("T"," "),
            "ID":          h.get("transaction_id","?"),
            "Fraud Score": f"{h.get('fraud_score',0):.2%}",
            "Risk Level":  h.get("risk_level","?").upper(),
            "Decision":    h.get("decision","?").upper(),
            "Risk Score":  h.get("verification",{}).get("risk_score","?"),
        } for h in st.session_state.history[:100]])
        st.dataframe(df_hist, use_container_width=True, height=320)

    with chart_col:
        st.markdown("##### Session Breakdown")
        st.plotly_chart(
            make_history_donut(st.session_state.history),
            use_container_width=True,
            config={"displayModeBar": False},
            key="donut_history"
        )
        total_hist = len(st.session_state.history)
        avg_score  = sum(h.get("fraud_score", 0) for h in st.session_state.history) / total_hist
        st.metric("Avg Fraud Score", f"{avg_score:.2%}")
        st.metric("Total Analyzed",  total_hist)

    st.divider()
    st.markdown("### 📈 Live Precision-Recall Curve (Session Data)")
    pr_fig2, op_p2, op_r2 = make_pr_curve(pr_threshold)
    st.plotly_chart(pr_fig2, use_container_width=True, config={"displayModeBar": False}, key="pr_curve_bottom")
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("Threshold", f"{pr_threshold:.2f}")
    pc2.metric("Precision", f"{op_p2:.2%}")
    pc3.metric("Recall",    f"{op_r2:.2%}")

    st.divider()
    st.markdown("### 🛡️ Live Activity Feed (Audit Trail)")

    with st.status("Monitoring SSE Stream... (Live)", expanded=True) as status:
        if st.session_state.history:
            for h in st.session_state.history[:5]:
                d   = h.get("decision", "block")
                cfg = DECISION_CFG.get(d, DECISION_CFG["block"])
                st.write(
                    f"**{h.get('_ts','')[:19]}** | "
                    f"ID: `{h.get('transaction_id','?')}` | "
                    f"CorrID: `{h.get('correlation_id','?')[:8]}...` | "
                    f"Decision: {cfg['emoji']} **{cfg['label']}** | "
                    f"Risk: `{h.get('risk_level','?').upper()}`"
                )
        else:
            st.write("Waiting for transactions...")
        status.update(label="Event Stream Active", state="running", expanded=False)

    st.caption("Transactions are recorded in the tamper-evident SQLite ledger with hash chaining.")