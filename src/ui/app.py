"""FoodMAS — production-ready Streamlit UI."""
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
/* ── Base ── */
.stApp { background: #080808; }
.block-container {
    max-width: 820px !important;
    padding: 0 1.5rem 4rem 1.5rem !important;
    margin: 0 auto;
}
section[data-testid="stSidebar"],
header[data-testid="stHeader"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
#MainMenu, footer { display: none !important; }

/* ── Hero ── */
.hero {
    text-align: center;
    padding: 3rem 0 2rem 0;
}
.hero-logo { font-size: 3.2rem; line-height: 1; }
.hero-title {
    font-size: 2.4rem;
    font-weight: 800;
    color: #ffffff;
    margin: 0.5rem 0 0 0;
    letter-spacing: -0.03em;
}
.hero-sub { color: #555; font-size: 0.95rem; margin-top: 0.35rem; }

/* ── Input card ── */
.input-card {
    background: #111;
    border: 1px solid #222;
    border-radius: 18px;
    padding: 1.5rem 1.75rem;
}
.stTextArea label { display: none; }
.stTextArea textarea {
    background: #0a0a0a !important;
    color: #eee !important;
    border: 1.5px solid #2a2a2a !important;
    border-radius: 10px !important;
    font-size: 1rem !important;
    line-height: 1.5 !important;
    resize: none !important;
    caret-color: #ff9500;
}
.stTextArea textarea:focus {
    border-color: #ff9500 !important;
    box-shadow: 0 0 0 3px rgba(255, 149, 0, 0.12) !important;
    outline: none !important;
}
.stTextArea textarea::placeholder { color: #3a3a3a !important; }

/* ── Chip label ── */
.chip-label { color: #3a3a3a; font-size: 0.75rem; margin: 1rem 0 0.4rem 0; }

/* ── Chip buttons ── */
div[data-testid="column"] .stButton > button {
    background: #131313 !important;
    color: #555 !important;
    border: 1px solid #222 !important;
    border-radius: 999px !important;
    padding: 4px 10px !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: all 0.15s !important;
    width: 100% !important;
}
div[data-testid="column"] .stButton > button:hover {
    background: #1a1000 !important;
    color: #ff9500 !important;
    border-color: #ff9500 !important;
}

/* ── Primary submit button ── */
.submit-row .stButton > button,
div[data-testid="stButton-primary"] > button {
    background: linear-gradient(135deg, #ff9500 0%, #e07800 100%) !important;
    color: #000 !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.7rem 2rem !important;
    width: 100% !important;
    margin-top: 1rem;
    transition: opacity 0.18s !important;
    letter-spacing: 0.01em;
}
.submit-row .stButton > button:hover { opacity: 0.86 !important; }

/* ── Agent pipeline ── */
.pipeline-outer {
    background: #0e0e0e;
    border: 1px solid #1e1e1e;
    border-radius: 18px;
    padding: 1.75rem 1.25rem 1.5rem 1.25rem;
    margin: 1.5rem 0;
    overflow-x: auto;
}
.pipeline-title {
    color: #333;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    text-align: center;
    margin-bottom: 1.25rem;
}
.pipeline-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    min-width: 540px;
}
.step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    min-width: 110px;
    max-width: 160px;
}
.step-bubble {
    width: 54px; height: 54px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.35rem;
    border: 2px solid;
    transition: all 0.35s ease;
    position: relative;
}
.step-name {
    font-size: 0.68rem;
    font-weight: 700;
    margin-top: 9px;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    transition: color 0.35s;
}
.step-desc { font-size: 0.65rem; margin-top: 3px; text-align: center; color: #333; }

/* connector */
.conn {
    flex: 0 0 28px;
    height: 2px;
    position: relative;
    top: -22px;
    transition: background 0.35s;
}

/* State: pending */
.s-pending .step-bubble { background: #0d0d0d; border-color: #222; color: #2a2a2a; }
.s-pending .step-name   { color: #2a2a2a; }

/* State: active */
.s-active .step-bubble {
    background: #1a0f00;
    border-color: #ff9500;
    color: #ff9500;
    box-shadow: 0 0 14px rgba(255,149,0,0.35);
    animation: beat 1.1s ease-in-out infinite;
}
.s-active .step-name { color: #ff9500; }

/* State: done */
.s-done .step-bubble { background: #071207; border-color: #30d158; color: #30d158; }
.s-done .step-name   { color: #30d158; }

/* State: error */
.s-error .step-bubble { background: #180606; border-color: #ff453a; color: #ff453a; }
.s-error .step-name   { color: #ff453a; }

/* Connectors */
.conn-pending { background: #1e1e1e; }
.conn-active  { background: linear-gradient(90deg, #30d158, #ff9500); }
.conn-done    { background: #30d158; }

@keyframes beat {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,149,0,0.5); }
    50%       { box-shadow: 0 0 0 10px rgba(255,149,0,0); }
}

/* ── Order card ── */
.order-card {
    background: #0e0e0e;
    border: 1px solid #1e1e1e;
    border-radius: 18px;
    padding: 1.75rem 2rem;
    margin-top: 0.25rem;
}
.order-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 1.25rem;
}
.rest-name { color: #fff; font-size: 1.18rem; font-weight: 700; }
.badge-ok {
    background: #071407; color: #30d158;
    border: 1px solid #1a4a1a;
    padding: 3px 12px; border-radius: 999px;
    font-size: 0.76rem; font-weight: 600;
}
.badge-over {
    background: #1a0707; color: #ff453a;
    border: 1px solid #4a1a1a;
    padding: 3px 12px; border-radius: 999px;
    font-size: 0.76rem; font-weight: 600;
}
.sep { border: none; border-top: 1px solid #1a1a1a; margin: 0.65rem 0; }
.line { display: flex; justify-content: space-between; padding: 4px 0; color: #666; font-size: 0.9rem; }
.line span:last-child { color: #bbb; font-variant-numeric: tabular-nums; }
.line-bold { display: flex; justify-content: space-between; padding: 8px 0 2px 0; font-weight: 700; font-size: 1.05rem; color: #fff; }
.line-bold span:last-child { color: #ff9500; }
.rationale { color: #3a3a3a; font-size: 0.82rem; font-style: italic; margin-top: 1.1rem; padding-top: 0.85rem; border-top: 1px solid #161616; line-height: 1.6; }

/* ── Error box ── */
.err-box {
    background: #120808;
    border: 1px solid #3a1a1a;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    color: #ff6b6b;
    font-size: 0.9rem;
    line-height: 1.6;
    margin-top: 0.5rem;
}

/* ── Reset / new order button ── */
.new-order-wrap .stButton > button {
    background: transparent !important;
    color: #444 !important;
    border: 1px solid #222 !important;
    border-radius: 10px !important;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.25rem !important;
    margin-top: 1.25rem;
    width: auto !important;
    transition: all 0.15s !important;
}
.new-order-wrap .stButton > button:hover {
    color: #ff9500 !important;
    border-color: #ff9500 !important;
    background: #1a1000 !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

PIPELINE_STEPS = [
    ("planner",           "🧠", "Understanding",   "Parsing your request"),
    ("restaurant_finder", "🔍", "Searching",        "Finding restaurants"),
    ("menu_selector",     "🍽️",  "Building meal",    "Selecting dishes"),
    ("order_validator",   "✅", "Confirming",       "Reviewing totals"),
]
STEP_KEYS = [s[0] for s in PIPELINE_STEPS]

EXAMPLES = [
    "LKR 3000 for two, spicy Sri Lankan, no seafood",
    "Vegetarian Indian, budget Rs 2000",
    "Japanese for two, LKR 5000",
    "Italian dinner, 3 people, LKR 6000, no pork",
    "BBQ American, Rs 4000, Colombo",
]


def _pipeline_html(states: dict[str, str]) -> str:
    parts: list[str] = []
    for i, (key, icon, name, desc) in enumerate(PIPELINE_STEPS):
        status = states.get(key, "pending")
        # connector
        if i > 0:
            prev_status = states.get(STEP_KEYS[i - 1], "pending")
            conn_cls = (
                "conn-done"    if prev_status == "done" else
                "conn-active"  if prev_status == "active" else
                "conn-pending"
            )
            parts.append(f'<div class="conn {conn_cls}"></div>')
        parts.append(f"""
<div class="step s-{status}">
  <div class="step-bubble">{icon}</div>
  <div class="step-name">{name}</div>
  <div class="step-desc">{desc}</div>
</div>""")

    return (
        '<div class="pipeline-outer">'
        '<div class="pipeline-title">AI Agent Workflow</div>'
        '<div class="pipeline-row">' + "".join(parts) + "</div>"
        "</div>"
    )


def _order_html(order: Any) -> str:
    from src.state import OrderSummary
    o: OrderSummary = OrderSummary(**order) if isinstance(order, dict) else order
    badge = (
        '<span class="badge-ok">✓ Within budget</span>'
        if o.within_budget
        else '<span class="badge-over">⚠ Over budget</span>'
    )
    items_rows = "".join(
        f'<div class="line"><span>{it.name}'
        + (f' <span style="color:#333">×{it.quantity}</span>' if it.quantity > 1 else "")
        + f"</span><span>LKR {it.price * it.quantity:,.0f}</span></div>"
        for it in o.items
    )
    return f"""
<div class="order-card">
  <div class="order-head">
    <div class="rest-name">🏪 {o.restaurant_name}</div>
    {badge}
  </div>
  {items_rows}
  <hr class="sep"/>
  <div class="line"><span>Delivery fee</span><span>LKR {o.delivery_fee:,.0f}</span></div>
  <div class="line"><span>Tax (10%)</span><span>LKR {o.tax:,.0f}</span></div>
  <hr class="sep"/>
  <div class="line-bold"><span>Total</span><span>LKR {o.total:,.0f}</span></div>
  <div class="rationale">💬 {o.rationale}</div>
</div>"""


# ── Session defaults ──────────────────────────────────────────────────────────
for _k, _v in [("phase", "idle"), ("final_order", None), ("pipeline_states", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-logo">🍽️</div>
  <div class="hero-title">FoodMAS</div>
  <div class="hero-sub">Tell us what you're craving — our AI agents handle the rest.</div>
</div>
""", unsafe_allow_html=True)


# ── Input section ─────────────────────────────────────────────────────────────
pipeline_slot = st.empty()
result_slot   = st.empty()

# Always re-render the pipeline and result if already computed
if st.session_state.phase == "done" and st.session_state.pipeline_states:
    pipeline_slot.markdown(
        _pipeline_html(st.session_state.pipeline_states), unsafe_allow_html=True
    )
if st.session_state.phase == "done" and st.session_state.final_order:
    result_slot.markdown(
        _order_html(st.session_state.final_order), unsafe_allow_html=True
    )
if st.session_state.phase == "error" and st.session_state.pipeline_states:
    pipeline_slot.markdown(
        _pipeline_html(st.session_state.pipeline_states), unsafe_allow_html=True
    )

# ── New-order button when result is visible ───────────────────────────────────
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

# ── Input form (visible only in idle / error phase) ───────────────────────────
if st.session_state.phase in ("idle", "error"):
    user_input = st.text_area(
        label="order",
        height=96,
        placeholder="e.g. LKR 3000 for two people — spicy Sri Lankan food, no seafood",
    )

    st.markdown('<div class="chip-label">✨ Quick ideas — click to order instantly</div>', unsafe_allow_html=True)
    chip_cols = st.columns(len(EXAMPLES))
    for col, ex in zip(chip_cols, EXAMPLES):
        with col:
            short = ex if len(ex) <= 26 else ex[:24] + "…"
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

                # Mark all preceding steps done
                for prev in STEP_KEYS:
                    if prev == node_name:
                        break
                    if agent_states[prev] in ("pending", "active"):
                        agent_states[prev] = "done"

                has_err = bool(node_output.get("errors"))
                agent_states[node_name] = "error" if has_err else "active"
                pipeline_slot.markdown(_pipeline_html(agent_states), unsafe_allow_html=True)

                time.sleep(0.4)  # hold "active" state briefly so user sees it

                agent_states[node_name] = "error" if has_err else "done"
                pipeline_slot.markdown(_pipeline_html(agent_states), unsafe_allow_html=True)

                if node_output.get("order"):
                    final_order = node_output["order"]

        # Resolve any still-pending steps
        for k in STEP_KEYS:
            if agent_states[k] == "pending":
                agent_states[k] = "done"
        pipeline_slot.markdown(_pipeline_html(agent_states), unsafe_allow_html=True)

        st.session_state.pipeline_states = agent_states

        if final_order:
            st.session_state.phase       = "done"
            st.session_state.final_order = final_order
            result_slot.markdown(_order_html(final_order), unsafe_allow_html=True)
            # Show new-order button without full rerun
            st.rerun()
        else:
            st.session_state.phase = "error"
            result_slot.markdown("""
<div class="err-box">
  😕 No match found for your request.<br/>
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
  <span style="color:#522">{exc}</span>
</div>""", unsafe_allow_html=True)
        st.rerun()

elif submit and not user_input.strip():
    st.warning("Please describe what you'd like to eat.")
