"""FoodMAS — light Streamlit UI."""
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Tokens ── */
:root {
    color-scheme: only light;
    --bg-base:    #F7F7F4;
    --surface:    #FFFFFF;
    --surface-2:  #F1F3EE;
    --edge-1:     #E1E4DC;
    --edge-2:     #CED4C8;
    --ink-1:      #171A16;
    --ink-2:      #52584F;
    --ink-3:      #747B70;
    --accent:     #2F6F4E;
    --accent-2:   #245A3F;
    --accent-dim: #E7F0EA;
    --green:      #26734D;
    --green-dim:  #E7F4EC;
    --red:        #A33A34;
    --red-dim:    #F8E9E7;
    --focus:      rgba(23, 26, 22, 0.18);
    --font-ui:    'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --r-sm:       8px;
    --r-md:       10px;
    --r-lg:       12px;
}

/* ── Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, .stApp {
    background: var(--bg-base) !important;
    color: var(--ink-1) !important;
    font-family: var(--font-ui) !important;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}
.block-container {
    max-width: 780px !important;
    padding: 1.25rem 1rem 4rem !important;
    margin: 0 auto;
}
section[data-testid="stSidebar"],
header[data-testid="stHeader"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
#MainMenu, footer { display: none !important; }
button, textarea { touch-action: manipulation; }
button:focus-visible,
textarea:focus-visible {
    outline: 2px solid var(--focus) !important;
    outline-offset: 2px !important;
}

/* ── Hero ── */
.hero {
    padding: 1rem 0 1.35rem;
    text-align: left;
}
.hero-eyebrow {
    display: inline-flex;
    align-items: center;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 0.55rem;
}
.hero-title {
    font-family: var(--font-ui);
    font-size: clamp(2.5rem, 8vw, 4.25rem);
    font-weight: 800;
    color: var(--ink-1);
    margin: 0;
    line-height: 0.98;
    letter-spacing: 0;
    text-wrap: balance;
}
.hero-title .accent { color: var(--accent); }
.hero-rule { display: none; }
.hero-sub {
    max-width: 560px;
    margin: 0.8rem 0 0;
    font-size: 1rem;
    color: var(--ink-2);
    line-height: 1.55;
    font-weight: 400;
}

/* ── Text area ── */
.stTextArea label { display: none; }
.stTextArea textarea {
    min-height: 112px !important;
    background: var(--surface) !important;
    color: var(--ink-1) !important;
    border: var(--border-hairline, 1px) solid var(--edge-2) !important;
    border-radius: var(--r-md) !important;
    font-family: var(--font-ui) !important;
    font-size: 16px !important;
    line-height: 1.55 !important;
    resize: vertical !important;
    caret-color: var(--accent);
    transition: border-color 0.2s, box-shadow 0.2s !important;
    padding: 0.95rem 1rem !important;
    box-shadow: 0 1px 2px rgba(23, 26, 22, 0.04) !important;
}
.stTextArea textarea:focus {
    border-color: var(--ink-1) !important;
    box-shadow: 0 0 0 3px var(--focus) !important;
    outline: none !important;
}
.stTextArea textarea::placeholder { color: var(--ink-3) !important; }

/* ── Chip label ── */
.chip-label {
    font-size: 0.78rem;
    color: var(--ink-2);
    margin: 1rem 0 0.5rem;
    font-weight: 600;
}

/* ── Chip buttons ── */
html body .stApp div[data-testid="column"] button[kind="secondary"][data-testid="stBaseButton-secondary"],
html body .stApp div[data-testid="column"] button[data-testid="stBaseButton-secondary"],
html body .stApp div[data-testid="stColumn"] button[kind="secondary"][data-testid="stBaseButton-secondary"],
html body .stApp div[data-testid="stColumn"] button[data-testid="stBaseButton-secondary"],
div[data-testid="column"] div[data-testid="stButton"] > button,
div[data-testid="stColumn"] div[data-testid="stButton"] > button,
div[data-testid="column"] .stButton > button {
    min-height: 44px !important;
    color-scheme: only light !important;
    appearance: none !important;
    -webkit-appearance: none !important;
    background: var(--surface) !important;
    background-color: var(--surface) !important;
    background-image: none !important;
    color: var(--ink-2) !important;
    -webkit-text-fill-color: var(--ink-2) !important;
    border: 1px solid var(--edge-1) !important;
    border-radius: var(--r-sm) !important;
    padding: 0.55rem 0.75rem !important;
    font-size: 0.8rem !important;
    font-family: var(--font-ui) !important;
    font-weight: 600 !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease,
                transform 0.15s ease !important;
    width: 100% !important;
    box-shadow: 0 1px 2px rgba(23, 26, 22, 0.04) !important;
}
html body .stApp div[data-testid="column"] button[data-testid="stBaseButton-secondary"] *,
html body .stApp div[data-testid="column"] button[data-testid="stBaseButton-secondary"] p,
html body .stApp div[data-testid="stColumn"] button[data-testid="stBaseButton-secondary"] *,
html body .stApp div[data-testid="stColumn"] button[data-testid="stBaseButton-secondary"] p {
    background: transparent !important;
    color: var(--ink-2) !important;
    -webkit-text-fill-color: var(--ink-2) !important;
}
html body .stApp div[data-testid="column"] button[data-testid="stBaseButton-secondary"]:active,
html body .stApp div[data-testid="stColumn"] button[data-testid="stBaseButton-secondary"]:active,
div[data-testid="column"] div[data-testid="stButton"] > button:active,
div[data-testid="stColumn"] div[data-testid="stButton"] > button:active,
div[data-testid="column"] .stButton > button:active {
    transform: scale(0.98) !important;
}
@media (hover: hover) and (pointer: fine) {
    html body .stApp div[data-testid="column"] button[data-testid="stBaseButton-secondary"]:hover,
    html body .stApp div[data-testid="stColumn"] button[data-testid="stBaseButton-secondary"]:hover,
    div[data-testid="column"] div[data-testid="stButton"] > button:hover,
    div[data-testid="stColumn"] div[data-testid="stButton"] > button:hover,
    div[data-testid="column"] .stButton > button:hover {
        background: var(--accent-dim) !important;
        background-color: var(--accent-dim) !important;
        background-image: none !important;
        color: var(--accent-2) !important;
        -webkit-text-fill-color: var(--accent-2) !important;
        border-color: #B8CDBF !important;
    }
    html body .stApp div[data-testid="column"] button[data-testid="stBaseButton-secondary"]:hover *,
    html body .stApp div[data-testid="column"] button[data-testid="stBaseButton-secondary"]:hover p,
    html body .stApp div[data-testid="stColumn"] button[data-testid="stBaseButton-secondary"]:hover *,
    html body .stApp div[data-testid="stColumn"] button[data-testid="stBaseButton-secondary"]:hover p {
        color: var(--accent-2) !important;
        -webkit-text-fill-color: var(--accent-2) !important;
    }
}

/* ── Submit button ── */
html body .stApp button[kind="primary"][data-testid="stBaseButton-primary"],
html body .stApp button[data-testid="stBaseButton-primary"],
.submit-row .stButton > button {
    min-height: 48px !important;
    color-scheme: only light !important;
    appearance: none !important;
    -webkit-appearance: none !important;
    background: var(--accent) !important;
    background-color: var(--accent) !important;
    background-image: none !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-weight: 700 !important;
    font-size: 0.93rem !important;
    font-family: var(--font-ui) !important;
    border: none !important;
    border-radius: var(--r-md) !important;
    padding: 0.8rem 1.25rem !important;
    width: 100% !important;
    margin-top: 1rem;
    transition: background-color 0.15s ease, transform 0.15s ease !important;
    box-shadow: none !important;
}
html body .stApp button[data-testid="stBaseButton-primary"] *,
html body .stApp button[data-testid="stBaseButton-primary"] p {
    background: transparent !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}
html body .stApp button[data-testid="stBaseButton-primary"]:active,
.submit-row .stButton > button:active {
    transform: scale(0.99) !important;
}
@media (hover: hover) and (pointer: fine) {
    html body .stApp button[data-testid="stBaseButton-primary"]:hover,
    .submit-row .stButton > button:hover {
        background: var(--accent-2) !important;
        background-color: var(--accent-2) !important;
        background-image: none !important;
    }
    html body .stApp button[data-testid="stBaseButton-primary"]:hover *,
    html body .stApp button[data-testid="stBaseButton-primary"]:hover p {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
}

/* ── Pipeline ── */
.pipeline-outer {
    background: var(--surface);
    border: 1px solid var(--edge-1);
    border-radius: var(--r-lg);
    padding: 1.25rem;
    margin: 1.5rem 0;
    overflow-x: auto;
    box-shadow: 0 1px 2px rgba(23, 26, 22, 0.04);
}
.pipeline-label {
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--ink-2);
    text-align: left;
    margin-bottom: 1.25rem;
}
.pl-track-wrap {
    position: relative;
    min-width: 460px;
}
.pl-track {
    position: absolute;
    top: 18px;
    left: 12.5%;
    right: 12.5%;
    height: 2px;
    background: var(--edge-1);
    border-radius: 2px;
    overflow: hidden;
}
.pl-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    transition: width 0.3s ease-out;
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
    width: 38px; height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.95rem;
    border: 1px solid;
    transition: background-color 0.2s ease-out, border-color 0.2s ease-out, color 0.2s ease-out;
    position: relative;
}
.step-name {
    font-size: 0.72rem;
    font-weight: 700;
    margin-top: 0.6rem;
    text-align: center;
    transition: color 0.2s ease-out;
    white-space: nowrap;
}
.step-hint {
    font-size: 0.68rem;
    margin-top: 0.15rem;
    text-align: center;
    color: var(--ink-3);
    white-space: nowrap;
}
/* pending */
.s-pending .step-node {
    background: var(--surface-2);
    border-color: var(--edge-1);
    color: var(--ink-3);
    font-size: 0.78rem;
    font-weight: 700;
}
.s-pending .step-name { color: var(--ink-3); }
/* active */
.s-active .step-node {
    background: var(--accent-dim);
    border-color: var(--accent);
    color: var(--accent);
}
.s-active .step-name { color: var(--accent); }
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

/* ── Order card ── */
.order-card {
    background: var(--surface);
    border: 1px solid var(--edge-1);
    border-radius: var(--r-lg);
    overflow: hidden;
    margin-top: 0.25rem;
    box-shadow: 0 1px 2px rgba(23, 26, 22, 0.04);
}
.order-stripe {
    height: 3px;
    background: var(--accent);
}
.order-body { padding: 1.25rem; }
.order-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--edge-1);
}
.rest-name {
    font-family: var(--font-ui);
    color: var(--ink-1);
    font-size: 1.25rem;
    font-weight: 800;
    line-height: 1.2;
    letter-spacing: 0;
}
.badge-ok {
    background: var(--green-dim);
    color: var(--green);
    border: 1px solid #BCDCC8;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    margin-top: 4px;
    white-space: nowrap;
}
.badge-over {
    background: var(--red-dim);
    color: var(--red);
    border: 1px solid #E7C5C0;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    margin-top: 4px;
    white-space: nowrap;
}
.rest-section {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--accent);
    padding: 1rem 0 0.5rem;
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
    gap: 1rem;
    padding: 0.45rem 0;
    color: var(--ink-2);
    font-size: 0.94rem;
}
.line-item-name { color: var(--ink-1); font-weight: 600; }
.line-item-qty  { color: var(--ink-3); font-size: 0.82rem; margin-left: 5px; }
.line-item-price { color: var(--ink-1); font-variant-numeric: tabular-nums; }
.sep { border: none; border-top: 1px solid var(--edge-1); margin: 0.8rem 0; }
.totals-block {
    background: var(--surface-2);
    border: 1px solid var(--edge-1);
    border-radius: var(--r-md);
    padding: 1rem;
    margin-top: 0.9rem;
}
.fee-line {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.25rem 0;
    font-size: 0.88rem;
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
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--ink-2);
}
.total-amount {
    font-family: var(--font-ui);
    font-size: 1.65rem;
    font-weight: 800;
    color: var(--accent);
    letter-spacing: 0;
    line-height: 1;
    font-variant-numeric: tabular-nums;
}
.rationale {
    color: var(--ink-2);
    font-size: 0.88rem;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--edge-1);
    line-height: 1.6;
}

/* ── Error box ── */
.err-box {
    background: var(--red-dim);
    border: 1px solid #E7C5C0;
    border-radius: var(--r-md);
    padding: 1rem;
    color: var(--red);
    font-size: 0.9rem;
    line-height: 1.6;
    margin-top: 0.5rem;
}

/* ── New order button ── */
.new-order-wrap .stButton > button {
    min-height: 44px !important;
    background: var(--surface) !important;
    color: var(--ink-2) !important;
    border: 1px solid var(--edge-1) !important;
    border-radius: var(--r-sm) !important;
    font-size: 0.9rem !important;
    font-family: var(--font-ui) !important;
    font-weight: 700 !important;
    padding: 0.65rem 1rem !important;
    margin-top: 1.25rem;
    width: auto !important;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease,
                transform 0.15s ease !important;
}
.new-order-wrap .stButton > button:active {
    transform: scale(0.98) !important;
}
@media (hover: hover) and (pointer: fine) {
    .new-order-wrap .stButton > button:hover {
        color: var(--accent-2) !important;
        border-color: #B8CDBF !important;
        background: var(--accent-dim) !important;
    }
}

/* ── Streamlit warning ── */
.stAlert { border-radius: var(--r-md) !important; }

@media only screen and (min-device-pixel-ratio: 2),
       only screen and (min-resolution: 192dpi) {
    :root { --border-hairline: 0.5px; }
}

@media (max-width: 680px) {
    .block-container {
        padding: 1rem 0.75rem 3rem !important;
    }
    .hero {
        padding-top: 0.5rem;
    }
    div[data-testid="column"] {
        min-width: 100% !important;
    }
    .order-body {
        padding: 1rem;
    }
    .line,
    .fee-line,
    .total-line {
        align-items: flex-start;
    }
}

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
    }
}
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
  <div class="hero-eyebrow">Food ordering</div>
  <h1 class="hero-title">Food<span class="accent">MAS</span></h1>
  <div class="hero-rule"></div>
  <p class="hero-sub">Tell us the cuisine, budget, people count, and restrictions. The agents return a ready order.</p>
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
        placeholder="LKR 3000 for two, spicy Sri Lankan, no seafood",
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
    submit = st.button("Find order", type="primary")
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
