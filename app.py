"""
app.py — TIDEPOOL Command Agent
Top layer of the TIDEPOOL AI Operating System.
"""
import streamlit as st
import json
from datetime import datetime
from auth import check_password

st.set_page_config(
    page_title="TIDEPOOL Command",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .stApp { background-color: #0a0f0f; }
  .command-header { display: flex; align-items: center; justify-content: space-between; padding: 1.2rem 0 0.6rem 0; border-bottom: 1px solid #1a2a2a; margin-bottom: 1.5rem; }
  .command-wordmark { font-size: 1.6rem; font-weight: 800; color: #00C2A8; letter-spacing: 0.12em; font-family: monospace; }
  .command-subtitle { font-size: 0.75rem; color: #4a7070; letter-spacing: 0.08em; margin-top: 2px; }
  .command-badge { background: #0d2020; border: 1px solid #00C2A8; color: #00C2A8; font-size: 0.65rem; letter-spacing: 0.12em; padding: 4px 10px; border-radius: 4px; font-family: monospace; }
  .banner-critical { background: #1a0505; border: 1px solid #FF3B3B; border-left: 4px solid #FF3B3B; color: #FF3B3B; padding: 0.7rem 1rem; border-radius: 6px; margin-bottom: 0.8rem; font-size: 0.85rem; font-family: monospace; }
  .banner-warning { background: #1a0e05; border: 1px solid #FF6B35; border-left: 4px solid #FF6B35; color: #FF6B35; padding: 0.7rem 1rem; border-radius: 6px; margin-bottom: 0.8rem; font-size: 0.85rem; font-family: monospace; }
  .metric-card { background: #0d1a1a; border-radius: 8px; padding: 1rem 1.1rem; border: 1px solid #1a2e2e; height: 100%; }
  .metric-card.critical { border-color: #FF3B3B; border-left: 3px solid #FF3B3B; }
  .metric-card.warning { border-color: #FF6B35; border-left: 3px solid #FF6B35; }
  .metric-card.healthy { border-color: #00C2A8; border-left: 3px solid #00C2A8; }
  .metric-label { font-size: 0.65rem; color: #4a7070; letter-spacing: 0.12em; text-transform: uppercase; font-family: monospace; margin-bottom: 4px; }
  .metric-value { font-size: 1.5rem; font-weight: 700; font-family: monospace; color: #e0f0f0; line-height: 1.2; }
  .metric-value.critical { color: #FF3B3B; }
  .metric-value.warning { color: #FF6B35; }
  .metric-value.healthy { color: #00C2A8; }
  .metric-sub { font-size: 0.7rem; color: #3a5555; font-family: monospace; margin-top: 3px; }
  .brief-box { background: #0d1a1a; border: 1px solid #1a3030; border-left: 3px solid #00C2A8; border-radius: 8px; padding: 1rem 1.2rem; margin: 1rem 0; color: #b0c8c8; font-size: 0.88rem; line-height: 1.7; }
  .brief-label { font-size: 0.62rem; color: #00C2A8; letter-spacing: 0.14em; text-transform: uppercase; font-family: monospace; margin-bottom: 0.5rem; }
  .chat-bubble-user { background: #0d2a20; border: 1px solid #00C2A8; border-radius: 12px 12px 2px 12px; padding: 0.7rem 1rem; color: #c0e8e0; font-size: 0.85rem; margin-left: auto; max-width: 80%; }
  .chat-bubble-claude { background: #0d1a1a; border: 1px solid #1a3030; border-radius: 12px 12px 12px 2px; padding: 0.85rem 1rem; color: #b0c8c8; font-size: 0.85rem; max-width: 90%; line-height: 1.65; font-family: monospace; }
  .chat-role-label { font-size: 0.6rem; color: #3a5555; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 4px; }
  .section-header { font-size: 0.65rem; color: #4a7070; letter-spacing: 0.15em; text-transform: uppercase; font-family: monospace; margin: 1.5rem 0 0.75rem 0; border-bottom: 1px solid #1a2a2a; padding-bottom: 0.4rem; }
  .sku-card { background: #0d1a1a; border: 1px solid #1a2e2e; border-radius: 8px; padding: 0.9rem 1rem; }
  .sku-name { font-size: 0.7rem; color: #4a7070; letter-spacing: 0.1em; text-transform: uppercase; font-family: monospace; }
  .sku-bags { font-size: 1.3rem; font-weight: 700; font-family: monospace; color: #e0f0f0; }
  .sku-velocity { font-size: 0.72rem; color: #3a5555; font-family: monospace; }
  .stub-card { background: #0d1a1a; border: 1px solid #00C2A8; border-radius: 10px; padding: 3rem 2rem; text-align: center; max-width: 480px; margin: 4rem auto; }
  .stub-title { font-size: 1.1rem; color: #00C2A8; font-family: monospace; font-weight: 700; margin-bottom: 0.6rem; }
  .stub-sub { font-size: 0.82rem; color: #4a7070; line-height: 1.6; }
  .pipeline-row { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #1a2a2a; font-size: 0.8rem; font-family: monospace; color: #b0c8c8; }
  .pipeline-row:last-child { border-bottom: none; }
  .stage-badge { font-size: 0.65rem; padding: 2px 7px; border-radius: 4px; font-family: monospace; }
  .stage-in-progress { background: #0d2a20; color: #00C2A8; border: 1px solid #00C2A870; }
  .stage-warm { background: #1a1a05; color: #FFD700; border: 1px solid #FFD70070; }
  .stage-cold { background: #1a1a1a; color: #4a7070; border: 1px solid #2a3030; }
  .stage-won { background: #0d2a10; color: #00FF80; border: 1px solid #00FF8070; }
  .stage-dead { background: #1a0505; color: #FF3B3B50; border: 1px solid #FF3B3B30; }
  .sync-timestamp { font-size: 0.62rem; color: #2a4040; font-family: monospace; text-align: right; margin-top: 0.4rem; }
  .stTabs [data-baseweb="tab-list"] { background: #0a0f0f; gap: 4px; }
  .stTabs [data-baseweb="tab"] { background: #0d1a1a; color: #4a7070; border-radius: 6px 6px 0 0; font-family: monospace; font-size: 0.78rem; letter-spacing: 0.08em; padding: 8px 18px; border: 1px solid #1a2a2a; border-bottom: none; }
  .stTabs [aria-selected="true"] { background: #0d2020 !important; color: #00C2A8 !important; border-color: #00C2A8 !important; }
  .stTextInput input { background: #0d1a1a !important; border: 1px solid #1a3030 !important; color: #c0e8e0 !important; font-family: monospace !important; border-radius: 8px !important; }
  .stButton button { background: #00C2A8 !important; color: #0a0f0f !important; font-family: monospace !important; font-weight: 700 !important; border: none !important; border-radius: 6px !important; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    defaults = {
        "conversation_history": [],
        "situation_brief": None,
        "data_context": None,
        "last_refresh": None,
        "chat_started": False,
        "pending_question": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()

if not check_password():
    st.stop()


@st.cache_data(ttl=120, show_spinner=False)
def load_data_context():
    try:
        from data_context import assemble_data_context
        return assemble_data_context()
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "cash": {"balance": 0.0, "monthly_burn": 0.0, "runway_months": 0.0},
            "pnl": {"net": 0.0, "revenue": 0.0, "production_cogs": 9531.45, "opex": 0.0, "gifting_cogs": 0.0},
            "inventory": {
                "blueberry_lemon": {"available": 0, "velocity_30d": 0, "days_remaining": 0, "status": "unknown"},
                "cherry_lime": {"available": 0, "velocity_30d": 0, "days_remaining": 0, "status": "unknown"},
                "peach_mango": {"available": 0, "velocity_30d": 0, "days_remaining": 0, "status": "unknown"},
                "total_available": 0,
                "suppress_new_commitments": False,
            },
            "pipeline": {"total_weighted_value": 0.0, "active_count": 0, "in_progress_count": 0, "warm_lead_count": 0, "top_opportunity": "N/A", "leads": []},
            "gifting": {"total_bags_gifted": 0, "total_cogs": 0.0, "confirmed_count": 0},
            "recent_events": [],
            "sales_placeholder": {"leads": [], "outreach_log": [], "commit_history": []},
            "marketing_placeholder": {"creator_roster": [], "event_log": [], "content_performance": [], "demand_signal": {}},
        }


def get_context():
    ctx = load_data_context()
    st.session_state["data_context"] = ctx
    return ctx


def render_global_banners(ctx):
    inv = ctx.get("inventory", {})
    cash = ctx.get("cash", {})
    runway = cash.get("runway_months", 99)
    suppress = inv.get("suppress_new_commitments", False)
    if runway < 1:
        st.markdown('<div class="banner-critical">🔴 Critical: Less than 1 month cash runway</div>', unsafe_allow_html=True)
    if suppress:
        st.markdown('<div class="banner-warning">⚠ Ops Agent: Do not commit new wholesale orders — inventory below threshold</div>', unsafe_allow_html=True)
    for sku_key in ("blueberry_lemon", "cherry_lime", "peach_mango"):
        sku = inv.get(sku_key, {})
        if sku.get("status") == "critical":
            name = sku_key.replace("_", " ").title()
            st.markdown(f'<div class="banner-critical">🔴 Inventory Critical: {name} — {sku.get("days_remaining", 0)} days remaining</div>', unsafe_allow_html=True)
        elif sku.get("status") == "warning":
            name = sku_key.replace("_", " ").title()
            st.markdown(f'<div class="banner-warning">⚠ Inventory Warning: {name} — {sku.get("days_remaining", 0)} days remaining</div>', unsafe_allow_html=True)


st.markdown("""
<div class="command-header">
  <div>
    <div class="command-wordmark">TIDEPOOL</div>
    <div class="command-subtitle">Command Agent &nbsp;·&nbsp; S&OP Brain</div>
  </div>
  <div class="command-badge">S&OP SYSTEM &nbsp;·&nbsp; COMMAND LAYER</div>
</div>
""", unsafe_allow_html=True)

with st.spinner("Syncing live data..."):
    ctx = get_context()

render_global_banners(ctx)

tab_home, tab_ops, tab_finance, tab_sales, tab_marketing = st.tabs([
    "HOME", "OPS", "FINANCE", "SALES", "MARKETING"
])

with tab_home:
    st.markdown('<div class="section-header">Situation Snapshot</div>', unsafe_allow_html=True)

    cash_data = ctx.get("cash", {})
    pnl_data = ctx.get("pnl", {})
    inv_data = ctx.get("inventory", {})
    pipeline_data = ctx.get("pipeline", {})

    cash_bal = cash_data.get("balance", 0)
    monthly_burn = cash_data.get("monthly_burn", 0)
    runway = cash_data.get("runway_months", 0)
    net_pnl = pnl_data.get("net", 0)
    total_bags = inv_data.get("total_available", 0)
    pipeline_val = pipeline_data.get("total_weighted_value", 0)

    runway_class = "critical" if runway < 1 else ("warning" if runway < 2 else "healthy")
    pnl_class = "critical" if net_pnl < -10000 else ("warning" if net_pnl < 0 else "healthy")
    bags_class = "critical" if total_bags < 50 else ("warning" if total_bags < 150 else "healthy")
    cash_class = "critical" if cash_bal < 500 else ("warning" if cash_bal < 1500 else "healthy")
    pipe_class = "healthy" if pipeline_val > 2000 else ("warning" if pipeline_val > 500 else "critical")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="metric-card {cash_class}"><div class="metric-label">Cash</div><div class="metric-value {cash_class}">${cash_bal:,.0f}</div><div class="metric-sub">BlueVine</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card {runway_class}"><div class="metric-label">Runway</div><div class="metric-value {runway_class}">{runway:.1f} mos</div><div class="metric-sub">at ${monthly_burn:,.0f}/mo</div></div>', unsafe_allow_html=True)
    with c3:
        pnl_sign = "+" if net_pnl >= 0 else ""
        st.markdown(f'<div class="metric-card {pnl_class}"><div class="metric-label">P&L</div><div class="metric-value {pnl_class}">{pnl_sign}${net_pnl:,.0f}</div><div class="metric-sub">live</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card {bags_class}"><div class="metric-label">Bags Available</div><div class="metric-value {bags_class}">{total_bags:,}</div><div class="metric-sub">across all SKUs</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="metric-card {pipe_class}"><div class="metric-label">Pipeline</div><div class="metric-value {pipe_class}">${pipeline_val:,.0f}</div><div class="metric-sub">weighted</div></div>', unsafe_allow_html=True)

    st.markdown(f'<div class="sync-timestamp">Last synced: {ctx.get("timestamp", "")[:19]} UTC</div>', unsafe_allow_html=True)
    st.markdown("")

    brief_col, refresh_col = st.columns([9, 1])
    with refresh_col:
        if st.button("↻", help="Refresh brief"):
            st.session_state["situation_brief"] = None
            load_data_context.clear()
            st.rerun()

    if st.session_state["situation_brief"] is None:
        with st.spinner("Generating situation brief..."):
            try:
                from claude_client import generate_situation_brief
                brief = generate_situation_brief(ctx)
                st.session_state["situation_brief"] = brief
            except Exception as e:
                st.session_state["situation_brief"] = f"Brief unavailable: {e}"

    with brief_col:
        st.markdown(f'<div class="brief-box"><div class="brief-label">Situation Brief</div>{st.session_state["situation_brief"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Command Interface</div>', unsafe_allow_html=True)

    if st.session_state["conversation_history"]:
        chat_html = ""
        for turn in st.session_state["conversation_history"]:
            if turn["role"] == "user":
                q = turn["content"].split("Question: ")[-1] if "Question: " in turn["content"] else turn["content"]
                chat_html += f'<div style="margin-bottom:0.75rem"><div class="chat-role-label">YOU</div><div class="chat-bubble-user">{q}</div></div>'
            else:
                chat_html += f'<div style="margin-bottom:0.75rem"><div class="chat-role-label">COMMAND</div><div class="chat-bubble-claude">{turn["content"]}</div></div>'
        st.markdown(chat_html, unsafe_allow_html=True)
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state["conversation_history"] = []
            st.session_state["chat_started"] = False
            st.rerun()

    if not st.session_state["chat_started"]:
        st.markdown("")
        suggestions = [
            "What should we prioritize this week?",
            "How many bags can we commit to new wholesale?",
            "What's our path to breakeven?",
            "Which lead should Cameron close first?",
        ]
        chip_cols = st.columns(len(suggestions))
        for i, (col, suggestion) in enumerate(zip(chip_cols, suggestions)):
            with col:
                if st.button(suggestion, key=f"chip_{i}"):
                    st.session_state["pending_question"] = suggestion
                    st.session_state["chat_started"] = True
                    st.rerun()

    if st.session_state.get("pending_question"):
        question = st.session_state["pending_question"]
        st.session_state["pending_question"] = None
        with st.spinner("Thinking..."):
            try:
                from claude_client import chat as claude_chat
                fresh_ctx = load_data_context()
                response = claude_chat(question, fresh_ctx, st.session_state["conversation_history"])
                st.session_state["conversation_history"].append({"role": "user", "content": f"Current business data:\n{json.dumps(fresh_ctx, default=str)}\n\nQuestion: {question}"})
                st.session_state["conversation_history"].append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Claude error: {e}")
        st.rerun()

    st.markdown("")
    input_col, btn_col = st.columns([9, 1])
    with input_col:
        user_input = st.text_input(label="", placeholder="Ask anything about TIDEPOOL...", key="chat_input", label_visibility="collapsed")
    with btn_col:
        send = st.button("Send", key="send_btn")

    if send and user_input.strip():
        question = user_input.strip()
        st.session_state["chat_started"] = True
        with st.spinner("Thinking..."):
            try:
                from claude_client import chat as claude_chat
                fresh_ctx = load_data_context()
                response = claude_chat(question, fresh_ctx, st.session_state["conversation_history"])
                st.session_state["conversation_history"].append({"role": "user", "content": f"Current business data:\n{json.dumps(fresh_ctx, default=str)}\n\nQuestion: {question}"})
                st.session_state["conversation_history"].append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Claude error: {e}")
        st.rerun()


with tab_ops:
    st.markdown('<div class="section-header">Inventory Status</div>', unsafe_allow_html=True)

    inv = ctx.get("inventory", {})
    skus = {
        "Blueberry Lemon": inv.get("blueberry_lemon", {}),
        "Cherry Lime": inv.get("cherry_lime", {}),
        "Peach Mango": inv.get("peach_mango", {}),
    }
    sku_cols = st.columns(3)
    for col, (name, data) in zip(sku_cols, skus.items()):
        status = data.get("status", "unknown")
        border_color = "#FF3B3B" if status == "critical" else ("#FF6B35" if status == "warning" else "#00C2A8")
        with col:
            st.markdown(f'<div class="sku-card" style="border-left: 3px solid {border_color}"><div class="sku-name">{name}</div><div class="sku-bags">{data.get("available", 0):,} bags</div><div class="sku-velocity">{data.get("velocity_30d", 0):.1f} bags/day · {data.get("days_remaining", 0)} days</div><div class="sku-velocity" style="margin-top:4px; color:{border_color}">{status.upper()}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Sales Pipeline Demand</div>', unsafe_allow_html=True)
    pipeline = ctx.get("pipeline", {})
    leads = pipeline.get("leads", [])

    pipe_meta_cols = st.columns(4)
    pipe_metrics = [
        ("Total Weighted", f"${pipeline.get('total_weighted_value', 0):,.0f}"),
        ("Active Leads", str(pipeline.get("active_count", 0))),
        ("In Progress", str(pipeline.get("in_progress_count", 0))),
        ("Reorder Signal", pipeline.get("reorder_urgency", "N/A")),
    ]
    for col, (label, val) in zip(pipe_meta_cols, pipe_metrics):
        with col:
            st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value" style="font-size:1.1rem">{val}</div></div>', unsafe_allow_html=True)

    if leads:
        st.markdown("")
        stage_css = {"In Progress": "stage-in-progress", "Warm Lead": "stage-warm", "Cold Lead": "stage-cold", "Closed Won": "stage-won", "Dead": "stage-dead"}
        rows_html = ""
        for lead in leads[:10]:
            css = stage_css.get(lead["stage"], "stage-cold")
            rows_html += f'<div class="pipeline-row"><span>{lead["venue"]}</span><span><span class="stage-badge {css}">{lead["stage"]}</span></span><span>{lead["bags"]:.0f} bags</span><span>${lead["weighted_value"]:,.0f}</span></div>'
        st.markdown(f'<div style="background:#0d1a1a; border:1px solid #1a2e2e; border-radius:8px; padding:0.75rem 1rem;"><div style="display:flex; justify-content:space-between; font-size:0.62rem; color:#3a5555; font-family:monospace; letter-spacing:0.1em; padding-bottom:0.5rem; border-bottom:1px solid #1a2a2a; text-transform:uppercase;"><span>Venue</span><span>Stage</span><span>Bags</span><span>Weighted $</span></div>{rows_html}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="sync-timestamp">Ops data via live_state.json · {ctx.get("timestamp", "")[:19]} UTC</div>', unsafe_allow_html=True)


with tab_finance:
    st.markdown('<div class="section-header">Finance Command Center</div>', unsafe_allow_html=True)

    cash_d = ctx.get("cash", {})
    pnl_d = ctx.get("pnl", {})
    gifting_d = ctx.get("gifting", {})

    cash_b = cash_d.get("balance", 0)
    burn = cash_d.get("monthly_burn", 0)
    rwy = cash_d.get("runway_months", 0)
    net = pnl_d.get("net", 0)
    revenue = pnl_d.get("revenue", 0)
    opex = pnl_d.get("opex", 0)
    prod_cogs = pnl_d.get("production_cogs", 9531.45)
    gift_cogs = pnl_d.get("gifting_cogs", 0)
    total_bags_inv = ctx.get("inventory", {}).get("total_available", 0)

    rwy_class = "critical" if rwy < 1 else ("warning" if rwy < 2 else "healthy")
    net_class = "critical" if net < -10000 else ("warning" if net < 0 else "healthy")
    cash_class2 = "critical" if cash_b < 500 else ("warning" if cash_b < 1500 else "healthy")

    f1, f2, f3, f4, f5 = st.columns(5)
    with f1:
        st.markdown(f'<div class="metric-card {cash_class2}"><div class="metric-label">Cash Balance</div><div class="metric-value {cash_class2}">${cash_b:,.0f}</div><div class="metric-sub">BlueVine</div></div>', unsafe_allow_html=True)
    with f2:
        burn_class = "warning" if burn > 2000 else "healthy"
        st.markdown(f'<div class="metric-card {burn_class}"><div class="metric-label">Monthly Burn</div><div class="metric-value {burn_class}">${burn:,.0f}</div><div class="metric-sub">per month</div></div>', unsafe_allow_html=True)
    with f3:
        st.markdown(f'<div class="metric-card {rwy_class}"><div class="metric-label">Runway</div><div class="metric-value {rwy_class}">{rwy:.1f} mos</div><div class="metric-sub">at current burn</div></div>', unsafe_allow_html=True)
    with f4:
        pnl_sign = "+" if net >= 0 else ""
        st.markdown(f'<div class="metric-card {net_class}"><div class="metric-label">Net P&L</div><div class="metric-value {net_class}">{pnl_sign}${net:,.0f}</div><div class="metric-sub">live</div></div>', unsafe_allow_html=True)
    with f5:
        bags_cls = "warning" if total_bags_inv < 150 else "healthy"
        st.markdown(f'<div class="metric-card {bags_cls}"><div class="metric-label">Bags Remaining</div><div class="metric-value {bags_cls}">{total_bags_inv:,}</div><div class="metric-sub">across all SKUs</div></div>', unsafe_allow_html=True)

    st.markdown("")
    pl1, pl2 = st.columns(2)
    with pl1:
        net_color = "#00C2A8" if net >= 0 else "#FF3B3B"
        net_sign = "+" if net >= 0 else ""
        st.markdown(f'<div style="background:#0d1a1a; border:1px solid #1a2e2e; border-radius:8px; padding:1rem 1.2rem;"><div class="brief-label">Revenue & Costs</div><div class="pipeline-row"><span>Shopify Revenue</span><span style="color:#00C2A8">+${revenue:,.2f}</span></div><div class="pipeline-row"><span>Production COGS</span><span style="color:#FF6B35">-${prod_cogs:,.2f}</span></div><div class="pipeline-row"><span>Operating Expenses</span><span style="color:#FF6B35">-${opex:,.2f}</span></div><div class="pipeline-row"><span>Gifting COGS</span><span style="color:#FF6B35">-${gift_cogs:,.2f}</span></div><div class="pipeline-row" style="border-top:1px solid #2a3a3a; margin-top:4px; padding-top:8px; font-weight:700"><span>Net P&L</span><span style="color:{net_color}">{net_sign}${net:,.2f}</span></div></div>', unsafe_allow_html=True)
    with pl2:
        st.markdown(f'<div style="background:#0d1a1a; border:1px solid #1a2e2e; border-radius:8px; padding:1rem 1.2rem;"><div class="brief-label">Gifting Program</div><div class="pipeline-row"><span>Total Bags Gifted</span><span style="color:#b0c8c8">{gifting_d.get("total_bags_gifted", 0)}</span></div><div class="pipeline-row"><span>Total Gifting COGS</span><span style="color:#FF6B35">-${gifting_d.get("total_cogs", 0):,.2f}</span></div><div class="pipeline-row"><span>Confirmed Returns</span><span style="color:#00C2A8">{gifting_d.get("confirmed_count", 0)}</span></div></div>', unsafe_allow_html=True)

    st.markdown(f'<div class="sync-timestamp">Finance data via FinanceLog + FinanceSummary · {ctx.get("timestamp", "")[:19]} UTC</div>', unsafe_allow_html=True)


with tab_sales:
    st.markdown('<div class="section-header">Pipeline Overview</div>', unsafe_allow_html=True)

    pipeline = ctx.get("pipeline", {})
    leads = pipeline.get("leads", [])

    ps1, ps2, ps3, ps4, ps5 = st.columns(5)
    with ps1:
        st.markdown(f'<div class="metric-card healthy"><div class="metric-label">Weighted Value</div><div class="metric-value healthy">${pipeline.get("total_weighted_value", 0):,.0f}</div><div class="metric-sub">across all stages</div></div>', unsafe_allow_html=True)
    with ps2:
        st.markdown(f'<div class="metric-card healthy"><div class="metric-label">Active Partners</div><div class="metric-value healthy">{sum(1 for l in leads if l["stage"] == "Active")}</div><div class="metric-sub">wholesale live</div></div>', unsafe_allow_html=True)
    with ps3:
        st.markdown(f'<div class="metric-card warning"><div class="metric-label">In Progress</div><div class="metric-value warning">{pipeline.get("in_progress_count", 0)}</div><div class="metric-sub">needs close</div></div>', unsafe_allow_html=True)
    with ps4:
        st.markdown(f'<div class="metric-card warning"><div class="metric-label">Warm Leads</div><div class="metric-value warning">{pipeline.get("warm_lead_count", 0)}</div><div class="metric-sub">needs outreach</div></div>', unsafe_allow_html=True)
    with ps5:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total Leads</div><div class="metric-value">{len(leads)}</div><div class="metric-sub">in CRM</div></div>', unsafe_allow_html=True)

    st.markdown("")
    if st.button("Who should Cameron call today?", key="cameron_call"):
        with st.spinner("Thinking..."):
            try:
                from claude_client import chat as claude_chat
                fresh_ctx = load_data_context()
                response = claude_chat(
                    "Who should Cameron call or contact today to move the pipeline forward? Be specific: name the venue, the stage, why it is the highest priority right now, and what Cameron should say.",
                    fresh_ctx, []
                )
                st.session_state["cameron_answer"] = response
            except Exception as e:
                st.session_state["cameron_answer"] = f"Error: {e}"

    if st.session_state.get("cameron_answer"):
        st.markdown(f'<div class="brief-box"><div class="brief-label">Cameron Priority Call</div>{st.session_state["cameron_answer"]}</div>', unsafe_allow_html=True)

    stage_order = ["Active", "In Progress", "Warm Lead", "Contacted", "Prospect"]
    stage_css = {"Active": "stage-won", "In Progress": "stage-in-progress", "Warm Lead": "stage-warm", "Contacted": "stage-cold", "Prospect": "stage-cold"}

    for stage in stage_order:
        stage_leads = [l for l in leads if l["stage"] == stage]
        if not stage_leads:
            continue
        css = stage_css.get(stage, "stage-cold")
        st.markdown(f'<div class="section-header"><span class="stage-badge {css}">{stage}</span> &nbsp; {len(stage_leads)} leads</div>', unsafe_allow_html=True)
        rows_html = ""
        for lead in stage_leads:
            fit_color = "#00C2A8" if lead["fit_score"] >= 7 else ("#FFD700" if lead["fit_score"] >= 5 else "#FF6B35")
            franchise_tag = ' <span style="font-size:0.6rem;color:#FF6B35;border:1px solid #FF6B35;border-radius:3px;padding:1px 5px;">FRANCHISE</span>' if lead["franchise"] else ""
            next_action = (lead["next_action"][:40] + "...") if len(lead["next_action"]) > 40 else lead["next_action"]
            rows_html += f'<div class="pipeline-row"><span style="min-width:180px;font-weight:600">{lead["venue"]}{franchise_tag}</span><span style="min-width:120px;color:#4a7070">{lead["category"]}</span><span style="min-width:60px;color:{fit_color}">fit {lead["fit_score"]:.0f}/10</span><span style="min-width:80px;color:#00C2A8">${lead["weighted_value"]:,.0f}</span><span style="min-width:60px;color:#4a7070">{lead["owner"]}</span><span style="color:#3a5555;font-size:0.75rem">{next_action}</span></div>'
        st.markdown(f'<div style="background:#0d1a1a;border:1px solid #1a2e2e;border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem;"><div style="display:flex;justify-content:space-between;font-size:0.6rem;color:#3a5555;font-family:monospace;letter-spacing:0.1em;padding-bottom:0.5rem;border-bottom:1px solid #1a2a2a;text-transform:uppercase;"><span style="min-width:180px">Venue</span><span style="min-width:120px">Category</span><span style="min-width:60px">Fit</span><span style="min-width:80px">Weighted $</span><span style="min-width:60px">Owner</span><span>Next Action</span></div>{rows_html}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="sync-timestamp">CRM data via SalesLeads · {ctx.get("timestamp", "")[:19]} UTC</div>', unsafe_allow_html=True)


with tab_marketing:
    st.markdown('<div class="stub-card"><div style="font-size:2rem; margin-bottom:0.8rem">📣</div><div class="stub-title">Marketing Agent integration coming soon</div><div class="stub-sub">Creator ROI, event performance, content intelligence, and demand signals will surface here.</div></div>', unsafe_allow_html=True)
