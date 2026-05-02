"""FoodMAS — premium Streamlit UI."""
from __future__ import annotations

import time
import uuid
from typing import Any

import streamlit as st

# ── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="FoodMAS · Smart Food Ordering",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Consume auto-request BEFORE any rendering ────────────────────────────────
_auto_request: str | None = st.session_state.pop("_auto_request", None)

# ── Global styles ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,600;9..144,800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* ── Tokens ── */
:root {
    --bg-0:       #06050300;
    --bg-base:    #060503;
    --bg-1:       #0D0A07;
    --bg-2:       #141008;
    --bg-3:       #1A150E;
    --edge-0:     #181310;
    --edge-1:     #211A12;
    --edge-2:     #2E2518;
    --ink-1:      #EDE8DC;
    --ink-2:      #9A8E80;
    --ink-3:      #6B6258;
    --ink-4:      #504840;
    --amber:      #CF8B3C;
    --amber-lt:   #E8A558;
    --amber-dim:  rgba(207,139,60,0.08);
    --amber-glow: rgba(207,139,60,0.18);
    --green:      #5A9B6C;
    --green-dim:  rgba(90,155,108,0.08);
    --red:        #C0504A;
    --red-dim:    rgba(192,80,74,0.08);
    --font-d:     'Fraunces', Georgia, serif;
    --font-ui:    'Plus Jakarta Sans', system-ui, sans-serif;
    --r-sm:       8px;
    --r-md:       12px;
    --r-lg:       16px;
    --r-xl:       20px;
}

/* ── Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, .stApp {
    background: var(--bg-base) !important;
    font-family: var(--font-ui) !important;
    -webkit-font-smoothing: antialiased;
}
.block-container {
    max-width: 720px !important;
    padding: 0 1.25rem 6rem 1.25rem !important;
    margin: 0 auto;
}
section[data-testid="stSidebar"],
header[data-testid="stHeader"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
#MainMenu, footer { display: none !important; }

/* ── Grain texture ── */
.stApp::after {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='g'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23g)' opacity='1'/%3E%3C/svg%3E");
    opacity: 0.028;
    pointer-events: none;
    z-index: 9998;
}

/* ── Hero ── */
.hero {
    padding: 3.75rem 0 2.5rem;
    text-align: center;
}
.hero-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.64rem;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--amber);
    margin-bottom: 1.5rem;
    opacity: 0.75;
}
.hero-eyebrow::before,
.hero-eyebrow::after {
    content: '';
    display: block;
    width: 24px;
    height: 1px;
    background: var(--amber);
    opacity: 0.4;
}
.hero-title {
    font-family: var(--font-d);
    font-size: clamp(3.8rem, 9vw, 6rem);
    font-weight: 800;
    color: var(--ink-1);
    margin: 0;
    line-height: 0.93;
    letter-spacing: -0.025em;
}
.hero-title .accent { color: var(--amber); }
.hero-rule {
    width: 32px;
    height: 1px;
    background: var(--edge-2);
    margin: 1.75rem auto;
}
.hero-sub {
    font-size: 0.88rem;
    color: var(--ink-2);
    letter-spacing: 0.015em;
    line-height: 1.65;
    font-weight: 400;
}

/* ── Text area ── */
.stTextArea label { display: none; }
.stTextArea textarea {
    background: var(--bg-1) !important;
    color: var(--ink-1) !important;
    border: 1px solid var(--edge-2) !important;
    border-radius: var(--r-md) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
    resize: none !important;
    caret-color: var(--amber);
    transition: border-color 0.2s, box-shadow 0.2s !important;
    padding: 1rem 1.15rem !important;
}
.stTextArea textarea:focus {
    border-color: var(--amber) !important;
    box-shadow: 0 0 0 3px var(--amber-glow) !important;
    outline: none !important;
}
.stTextArea textarea::placeholder { color: var(--ink-4) !important; }

/* ── Chip label ── */
.chip-label {
    font-size: 0.64rem;
    color: var(--ink-2);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 1.1rem 0 0.5rem;
    font-weight: 500;
}

/* ── Chip buttons ── */
div[data-testid="column"] .stButton > button {
    background: var(--bg-1) !important;
    color: var(--ink-3) !important;
    border: 1px solid var(--edge-1) !important;
    border-radius: 999px !important;
    padding: 5px 12px !important;
    font-size: 0.72rem !important;
    font-family: var(--font-ui) !important;
    font-weight: 400 !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
div[data-testid="column"] .stButton > button:hover {
    background: var(--amber-dim) !important;
    color: var(--amber-lt) !important;
    border-color: rgba(207,139,60,0.3) !important;
}

/* ── Submit button ── */
.submit-row .stButton > button {
    background: linear-gradient(135deg, #E09A48 0%, #B86820 100%) !important;
    color: #0B0702 !important;
    font-weight: 700 !important;
    font-size: 0.93rem !important;
    font-family: var(--font-ui) !important;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border: none !important;
    border-radius: var(--r-md) !important;
    padding: 0.8rem 2rem !important;
    width: 100% !important;
    margin-top: 1.1rem;
    transition: opacity 0.2s, transform 0.2s !important;
    box-shadow: 0 4px 20px rgba(207,139,60,0.25) !important;
}
.submit-row .stButton > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 28px rgba(207,139,60,0.35) !important;
}

/* ── Pipeline ── */
.pipeline-outer {
    background: var(--bg-1);
    border: 1px solid var(--edge-1);
    border-radius: var(--r-xl);
    padding: 1.75rem 1.5rem 1.5rem;
    margin: 1.75rem 0;
    overflow-x: auto;
}
.pipeline-label {
    font-size: 0.58rem;
    font-weight: 600;
    color: var(--ink-2);
    text-transform: uppercase;
    letter-spacing: 0.18em;
    text-align: center;
    margin-bottom: 1.75rem;
}
.pl-track-wrap {
    position: relative;
    min-width: 460px;
}
.pl-track {
    position: absolute;
    top: 20px;
    left: 12.5%;
    right: 12.5%;
    height: 4px;
    background: var(--edge-2);
    border-radius: 2px;
    overflow: hidden;
}
.pl-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--green) 0%, var(--amber) 100%);
    border-radius: 2px;
    transition: width 0.55s cubic-bezier(0.4, 0, 0.2, 1);
    min-width: 0;
}
.pl-nodes {
    display: flex;
    justify-content: space-around;
    position: relative;
    z-index: 1;
}
.step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
}
.step-node {
    width: 44px; height: 44px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.05rem;
    border: 2px solid;
    transition: all 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
    position: relative;
}
.step-name {
    font-size: 0.6rem;
    font-weight: 700;
    margin-top: 10px;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    transition: color 0.3s;
    white-space: nowrap;
}
.step-hint {
    font-size: 0.57rem;
    margin-top: 3px;
    text-align: center;
    color: var(--ink-3);
    letter-spacing: 0.01em;
    white-space: nowrap;
}
/* pending */
.s-pending .step-node {
    background: var(--bg-2);
    border-color: var(--edge-2);
    color: var(--ink-3);
    font-size: 0.85rem;
    font-weight: 700;
}
.s-pending .step-name { color: var(--ink-3); }
/* active */
.s-active .step-node {
    background: var(--amber-dim);
    border-color: var(--amber);
    color: var(--amber);
    box-shadow: 0 0 0 4px var(--amber-glow);
    animation: ripple 1.6s ease-in-out infinite;
}
.s-active .step-name { color: var(--amber); }
/* done */
.s-done .step-node {
    background: var(--green-dim);
    border-color: var(--green);
    color: var(--green);
    font-size: 1rem;
    font-weight: 700;
}
.s-done .step-name { color: var(--green); }
/* error */
.s-error .step-node {
    background: var(--red-dim);
    border-color: var(--red);
    color: var(--red);
    font-size: 1rem;
    font-weight: 700;
}
.s-error .step-name { color: var(--red); }

@keyframes ripple {
    0%, 100% { box-shadow: 0 0 0 4px var(--amber-glow); }
    50%       { box-shadow: 0 0 0 12px rgba(207,139,60,0); }
}

/* ── Order card ── */
.order-card {
    background: var(--bg-1);
    border: 1px solid var(--edge-2);
    border-radius: var(--r-xl);
    overflow: hidden;
    margin-top: 0.25rem;
    animation: slide-up 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes slide-up {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}
.order-stripe {
    height: 2px;
    background: linear-gradient(90deg, var(--amber) 0%, rgba(207,139,60,0.25) 70%, transparent 100%);
}
.order-body { padding: 1.75rem 2rem 1.75rem; }
.order-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 1.5rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid var(--edge-1);
}
.rest-name {
    font-family: var(--font-d);
    color: var(--ink-1);
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1.05;
    letter-spacing: -0.015em;
}
.badge-ok {
    background: var(--green-dim);
    color: var(--green);
    border: 1px solid rgba(90,155,108,0.22);
    padding: 4px 13px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-top: 4px;
    white-space: nowrap;
}
.badge-over {
    background: var(--red-dim);
    color: var(--red);
    border: 1px solid rgba(192,80,74,0.22);
    padding: 4px 13px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-top: 4px;
    white-space: nowrap;
}
.rest-section {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--amber);
    padding: 1.1rem 0 0.5rem;
    opacity: 0.85;
}
.rest-section::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--edge-1);
}
.items-list { margin-bottom: 0.25rem; }
.line {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    color: var(--ink-2);
    font-size: 0.88rem;
}
.line-item-name { color: var(--ink-1); font-weight: 400; }
.line-item-qty  { color: var(--ink-3); font-size: 0.78rem; margin-left: 5px; }
.line-item-price { color: var(--ink-1); font-variant-numeric: tabular-nums; }
.sep { border: none; border-top: 1px solid var(--edge-1); margin: 0.8rem 0; }
.totals-block {
    background: var(--bg-0);
    border: 1px solid var(--edge-1);
    border-radius: var(--r-md);
    padding: 1rem 1.25rem;
    margin-top: 0.75rem;
}
.fee-line {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    font-size: 0.82rem;
    color: var(--ink-2);
}
.fee-line span:last-child { color: var(--ink-1); font-variant-numeric: tabular-nums; }
.total-line {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding-top: 0.85rem;
    margin-top: 0.5rem;
    border-top: 1px solid var(--edge-1);
}
.total-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-2);
}
.total-amount {
    font-family: var(--font-d);
    font-size: 2rem;
    font-weight: 700;
    color: var(--amber);
    letter-spacing: -0.02em;
    line-height: 1;
}
.rationale {
    color: var(--ink-2);
    font-size: 0.79rem;
    font-style: italic;
    margin-top: 1.25rem;
    padding-top: 1.1rem;
    border-top: 1px solid var(--edge-1);
    line-height: 1.75;
    letter-spacing: 0.01em;
}

/* ── Error box ── */
.err-box {
    background: var(--red-dim);
    border: 1px solid rgba(192,80,74,0.18);
    border-radius: var(--r-md);
    padding: 1.25rem 1.5rem;
    color: #C87070;
    font-size: 0.87rem;
    line-height: 1.7;
    margin-top: 0.5rem;
    animation: slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
}

/* ── New order button ── */
.new-order-wrap .stButton > button {
    background: transparent !important;
    color: var(--ink-3) !important;
    border: 1px solid var(--edge-2) !important;
    border-radius: var(--r-sm) !important;
    font-size: 0.83rem !important;
    font-family: var(--font-ui) !important;
    padding: 0.5rem 1.25rem !important;
    margin-top: 1.25rem;
    width: auto !important;
    transition: all 0.2s !important;
    letter-spacing: 0.02em;
}
.new-order-wrap .stButton > button:hover {
    color: var(--amber-lt) !important;
    border-color: rgba(207,139,60,0.35) !important;
    background: var(--amber-dim) !important;
}

/* ── Streamlit warning ── */
.stAlert { border-radius: var(--r-md) !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

PIPELINE_STEPS = [
    ("planner",           "🔮", "Understanding",  "Decoding your craving"),
    ("restaurant_finder", "📍", "Searching",       "Scouting the city"),
    ("menu_selector",     "✨", "Curating",        "Building your meal"),
    ("order_validator",   "🔒", "Confirming",      "Verifying totals"),
]
STEP_KEYS = [s[0] for s in PIPELINE_STEPS]

EXAMPLES = [
    "Spicy Sri Lankan, LKR 2500",
    "Vegetarian Indian, Rs 2000",
    "Japanese for two, 5000",
    "Italian dinner, 3 people, 6k",
    "American BBQ, Rs 4000",
]


def _pipeline_html(states: dict[str, str]) -> str:
    n = len(STEP_KEYS)
    done_count   = sum(1 for k in STEP_KEYS if states.get(k) == "done")
    active_count = sum(1 for k in STEP_KEYS if states.get(k) == "active")
    pct = min(100, int((done_count + active_count * 0.5) / (n - 1) * 100))

    nodes: list[str] = []
    for i, (key, icon, name, desc) in enumerate(PIPELINE_STEPS):
        status = states.get(key, "pending")
        if status == "pending":
            content = str(i + 1)
        elif status == "active":
            content = icon
        elif status == "done":
            content = "✓"
        else:
            content = "✕"
        nodes.append(
            f'<div class="step s-{status}">'
            f'<div class="step-node">{content}</div>'
            f'<div class="step-name">{name}</div>'
            f'<div class="step-hint">{desc}</div>'
            f'</div>'
        )

    return (
        '<div class="pipeline-outer">'
        '<div class="pipeline-label">AI Agent Workflow</div>'
        '<div class="pl-track-wrap">'
        f'<div class="pl-track"><div class="pl-fill" style="width:{pct}%"></div></div>'
        '<div class="pl-nodes">' + "".join(nodes) + "</div>"
        "</div>"
        "</div>"
    )


def _item_row(it: Any) -> str:
    qty_html = f'<span class="line-item-qty">× {it.quantity}</span>' if it.quantity > 1 else ""
    return (
        f'<div class="line">'
        f'<span><span class="line-item-name">{it.name}</span>{qty_html}</span>'
        f'<span class="line-item-price">LKR {it.price * it.quantity:,.0f}</span>'
        f'</div>'
    )


def _order_html(order: Any) -> str:
    from src.state import OrderSummary
    o: OrderSummary = OrderSummary(**order) if isinstance(order, dict) else order

    badge = (
        '<span class="badge-ok">✓ Within budget</span>'
        if o.within_budget
        else '<span class="badge-over">⚠ Over budget</span>'
    )

    is_multi = len({it.restaurant_name for it in o.items if it.restaurant_name}) > 1

    if is_multi:
        groups: dict[str, list[Any]] = {}
        for it in o.items:
            key = it.restaurant_name or "Other"
            groups.setdefault(key, []).append(it)
        items_html = ""
        for rest_name, items in groups.items():
            items_html += f'<div class="rest-section">🏪 {rest_name}</div>'
            items_html += '<div class="items-list">' + "".join(_item_row(it) for it in items) + "</div>"
        header_name = "Multi-Restaurant Order"
        header_icon = "🍽️"
    else:
        items_html = '<div class="items-list">' + "".join(_item_row(it) for it in o.items) + "</div>"
        header_name = o.restaurant_name
        header_icon = "🏪"

    return f"""
<div class="order-card">
  <div class="order-stripe"></div>
  <div class="order-body">
    <div class="order-head">
      <div class="rest-name">{header_icon} {header_name}</div>
      {badge}
    </div>
    {items_html}
    <div class="totals-block">
      <div class="fee-line"><span>Delivery fee</span><span>LKR {o.delivery_fee:,.0f}</span></div>
      <div class="fee-line"><span>Tax (10%)</span><span>LKR {o.tax:,.0f}</span></div>
      <div class="total-line">
        <span class="total-label">Total</span>
        <span class="total-amount">LKR {o.total:,.0f}</span>
      </div>
    </div>
    <div class="rationale">💬 {o.rationale}</div>
  </div>
</div>"""


# ── Session defaults ──────────────────────────────────────────────────────────
for _k, _v in [("phase", "idle"), ("final_order", None), ("pipeline_states", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-eyebrow">Multi-Agent AI Ordering</div>
  <h1 class="hero-title">Food<span class="accent">MAS</span></h1>
  <div class="hero-rule"></div>
  <p class="hero-sub">Describe your craving - our AI agents handle the rest.</p>
</div>
""", unsafe_allow_html=True)


# ── Slots ─────────────────────────────────────────────────────────────────────
pipeline_slot = st.empty()
result_slot   = st.empty()

if st.session_state.phase == "done" and st.session_state.pipeline_states:
    pipeline_slot.markdown(_pipeline_html(st.session_state.pipeline_states), unsafe_allow_html=True)
if st.session_state.phase == "done" and st.session_state.final_order:
    result_slot.markdown(_order_html(st.session_state.final_order), unsafe_allow_html=True)
if st.session_state.phase == "error" and st.session_state.pipeline_states:
    pipeline_slot.markdown(_pipeline_html(st.session_state.pipeline_states), unsafe_allow_html=True)

# ── New-order button ──────────────────────────────────────────────────────────
if st.session_state.phase in ("done", "error"):
    st.markdown('<div class="new-order-wrap">', unsafe_allow_html=True)
    if st.button("← New order"):
        st.session_state.phase = "idle"
        st.session_state.final_order = None
        st.session_state.pipeline_states = None
        pipeline_slot.empty()
        result_slot.empty()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ── Input form ────────────────────────────────────────────────────────────────
if st.session_state.phase in ("idle", "error"):
    user_input = st.text_area(
        label="order",
        height=90,
        placeholder="e.g.  LKR 3000 for two · spicy Sri Lankan · no seafood",
    )

    st.markdown('<div class="chip-label">Quick ideas</div>', unsafe_allow_html=True)
    chip_cols = st.columns(len(EXAMPLES))
    for col, ex in zip(chip_cols, EXAMPLES):
        with col:
            short = ex if len(ex) <= 24 else ex[:22] + "…"
            if st.button(short, key=f"chip_{ex[:14]}"):
                st.session_state["_auto_request"] = ex
                st.rerun()

    st.markdown('<div class="submit-row">', unsafe_allow_html=True)
    submit = st.button("Find My Order →")
    st.markdown("</div>", unsafe_allow_html=True)
else:
    user_input, submit = "", False


# ── Execute ───────────────────────────────────────────────────────────────────
request_text: str | None = (
    _auto_request
    or (user_input.strip() if submit and user_input.strip() else None)
)

if request_text and st.session_state.phase in ("idle", "error"):
    tid = str(uuid.uuid4())[:8]
    agent_states: dict[str, str] = {k: "pending" for k in STEP_KEYS}

    pipeline_slot.markdown(_pipeline_html(agent_states), unsafe_allow_html=True)
    result_slot.empty()

    from src.graph import build_graph
    from src.state import GraphState

    try:
        graph = build_graph()
        initial = GraphState(trace_id=tid, user_input=request_text)
        config  = {"configurable": {"thread_id": tid}}
        final_order = None

        for event in graph.stream(initial.model_dump(), config=config):
            for node_name, node_output in event.items():
                if node_name not in STEP_KEYS:
                    continue

                for prev in STEP_KEYS:
                    if prev == node_name:
                        break
                    if agent_states[prev] in ("pending", "active"):
                        agent_states[prev] = "done"

                has_err = bool(node_output.get("errors"))
                agent_states[node_name] = "error" if has_err else "active"
                pipeline_slot.markdown(_pipeline_html(agent_states), unsafe_allow_html=True)

                time.sleep(0.4)

                agent_states[node_name] = "error" if has_err else "done"
                pipeline_slot.markdown(_pipeline_html(agent_states), unsafe_allow_html=True)

                if node_output.get("order"):
                    final_order = node_output["order"]

        for k in STEP_KEYS:
            if agent_states[k] == "pending":
                agent_states[k] = "done"
        pipeline_slot.markdown(_pipeline_html(agent_states), unsafe_allow_html=True)

        st.session_state.pipeline_states = agent_states

        if final_order:
            st.session_state.phase       = "done"
            st.session_state.final_order = final_order
            result_slot.markdown(_order_html(final_order), unsafe_allow_html=True)
            st.rerun()
        else:
            st.session_state.phase = "error"
            result_slot.markdown("""
<div class="err-box">
  😕 &nbsp;No match found for your request.<br/>
  Try a higher budget, a different cuisine, or fewer dietary restrictions.
</div>""", unsafe_allow_html=True)
            st.rerun()

    except Exception as exc:
        for k in STEP_KEYS:
            if agent_states.get(k) in ("pending", "active"):
                agent_states[k] = "error"
        pipeline_slot.markdown(_pipeline_html(agent_states), unsafe_allow_html=True)
        st.session_state.phase = "error"
        st.session_state.pipeline_states = agent_states
        result_slot.markdown(f"""
<div class="err-box">
  Something went wrong — please try again.<br/>
  <span style="color:#6B3030">{exc}</span>
</div>""", unsafe_allow_html=True)
        st.rerun()

elif submit and not user_input.strip():
    st.warning("Please describe what you'd like to eat.")
