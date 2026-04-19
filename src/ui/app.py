"""Streamlit UI for the Smart Food Ordering Assistant."""
from __future__ import annotations

import uuid
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Smart Food Ordering Assistant",
    page_icon="🍛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  /* Dark background */
  .stApp { background-color: #1a1a1a; color: #f0f0f0; }

  /* Sidebar */
  [data-testid="stSidebar"] { background-color: #111111; }

  /* Agent trace cards */
  .agent-card {
    border-radius: 10px;
    padding: 12px 16px;
    margin: 8px 0;
    font-family: monospace;
    font-size: 13px;
  }
  .agent-queued  { background: #2a2a2a; color: #888; border-left: 4px solid #555; }
  .agent-running { background: #2a1a00; color: #ffa500; border-left: 4px solid #ffa500; }
  .agent-done    { background: #0a2a0a; color: #6fdc6f; border-left: 4px solid #4caf50; }
  .agent-error   { background: #2a0a0a; color: #ff6b6b; border-left: 4px solid #f44336; }

  /* Order summary card */
  .order-card {
    background: #1e1e1e;
    border: 1px solid #ff9800;
    border-radius: 12px;
    padding: 24px;
    margin-top: 16px;
  }
  .order-title { color: #ff9800; font-size: 20px; font-weight: bold; margin-bottom: 12px; }
  .within-budget { background: #1b5e20; color: #a5d6a7; padding: 4px 12px; border-radius: 20px; font-size: 13px; }
  .over-budget   { background: #b71c1c; color: #ffcdd2; padding: 4px 12px; border-radius: 20px; font-size: 13px; }
  .item-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #333; }
  .total-row { display: flex; justify-content: space-between; padding: 10px 0; font-weight: bold; color: #ff9800; font-size: 16px; }
  .rationale { color: #bbb; font-style: italic; margin-top: 12px; font-size: 14px; }

  /* Input box */
  .stTextArea textarea { background: #2a2a2a; color: #f0f0f0; border: 1px solid #444; border-radius: 8px; }

  /* Button */
  .stButton > button {
    background: linear-gradient(135deg, #ff9800, #f57c00);
    color: #000;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 10px 32px;
    font-size: 15px;
  }
  .stButton > button:hover { background: linear-gradient(135deg, #ffb74d, #ff9800); }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ System Status")

    from src.config import settings
    st.markdown(f"**Model:** `{settings.ollama_model}`")

    from src.db.session import check_connection
    db_ok = check_connection()
    db_color = "#4caf50" if db_ok else "#f44336"
    db_label = "Connected" if db_ok else "Disconnected"
    st.markdown(f"**MySQL:** <span style='color:{db_color}'>{db_label}</span>", unsafe_allow_html=True)

    if "trace_id" in st.session_state and st.session_state.trace_id:
        st.markdown(f"**Trace ID:** `{st.session_state.trace_id}`")

    st.divider()
    st.markdown("**Example requests:**")
    examples = [
        "LKR 3000 for two people, spicy Sri Lankan, no seafood",
        "Budget 2500 rupees, vegetarian Indian for one",
        "Rs 4000 Italian food, 3 people, no pork",
        "5000 LKR Japanese for two",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex[:20]}", use_container_width=True):
            st.session_state.prefill = ex

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div style='text-align:center; padding: 16px 0 8px 0;'>
  <span style='font-size:48px'>🍛🍜🍕🍣🍔</span><br/>
  <h1 style='color:#ff9800; margin:4px 0;'>Smart Food Ordering Assistant</h1>
  <p style='color:#888; font-size:15px;'>Powered by local Ollama · LangGraph multi-agent system</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Layout: input left, trace right
# ---------------------------------------------------------------------------
col_input, col_trace = st.columns([1, 1], gap="large")

AGENT_LABELS = {
    "planner": "🧠 Planner — parsing your request",
    "restaurant_finder": "🔍 Restaurant Finder — searching options",
    "menu_selector": "🍽️ Menu Selector — choosing your dishes",
    "order_validator": "✅ Order Validator — confirming order",
    "error": "❌ Error handler",
}

with col_input:
    st.markdown("### 📝 Your Order Request")
    prefill = st.session_state.pop("prefill", "") if "prefill" in st.session_state else ""
    user_input = st.text_area(
        label="Describe what you want",
        value=prefill,
        height=120,
        placeholder="e.g. I have LKR 3000 for two people, craving spicy Sri Lankan, no seafood",
        label_visibility="collapsed",
    )
    submit = st.button("🍽️ Find My Order", use_container_width=True)

with col_trace:
    st.markdown("### 🤖 Agent Activity")
    trace_container = st.empty()

# ---------------------------------------------------------------------------
# Order result area (below columns)
# ---------------------------------------------------------------------------
order_container = st.empty()

# ---------------------------------------------------------------------------
# Run graph on submit
# ---------------------------------------------------------------------------
if submit and user_input.strip():
    tid = str(uuid.uuid4())[:8]
    st.session_state.trace_id = tid

    agent_states: dict[str, str] = {k: "queued" for k in AGENT_LABELS}
    agent_outputs: dict[str, Any] = {}

    def render_trace():
        lines = []
        for node, label in AGENT_LABELS.items():
            status = agent_states.get(node, "queued")
            css = f"agent-{status}"
            icon = {"queued": "⏳", "running": "⚡", "done": "✅", "error": "❌"}.get(status, "")
            lines.append(f'<div class="agent-card {css}">{icon} {label}</div>')
        trace_container.markdown("\n".join(lines), unsafe_allow_html=True)

    render_trace()

    from src.graph import build_graph
    from src.state import GraphState

    try:
        graph = build_graph()
        initial = GraphState(trace_id=tid, user_input=user_input)
        config = {"configurable": {"thread_id": tid}}

        final_order = None

        for event in graph.stream(initial.model_dump(), config=config):
            for node_name, node_output in event.items():
                if node_name in agent_states:
                    # Mark previous nodes done
                    for prev in list(agent_states.keys()):
                        if prev == node_name:
                            break
                        if agent_states[prev] == "running":
                            agent_states[prev] = "done"

                    agent_states[node_name] = "running"
                    render_trace()

                    agent_outputs[node_name] = node_output

                    # Check for errors
                    if node_output.get("errors"):
                        agent_states[node_name] = "error"
                    else:
                        agent_states[node_name] = "done"

                    # Capture final order
                    if node_output.get("order"):
                        final_order = node_output["order"]

                    render_trace()

        # Mark all still-queued as done (they were skipped/not needed)
        for node in agent_states:
            if agent_states[node] == "queued":
                agent_states[node] = "done"
        render_trace()

        # ---------------------------------------------------------------------------
        # Render order card
        # ---------------------------------------------------------------------------
        if final_order:
            from src.state import OrderSummary
            order: OrderSummary = (
                OrderSummary(**final_order) if isinstance(final_order, dict) else final_order
            )
            budget_badge = (
                '<span class="within-budget">✓ Within Budget</span>'
                if order.within_budget
                else '<span class="over-budget">⚠ Over Budget</span>'
            )
            items_html = "".join(
                f'<div class="item-row"><span>{i.name} × {i.quantity}</span>'
                f'<span>LKR {i.price * i.quantity:,.2f}</span></div>'
                for i in order.items
            )
            order_html = f"""
<div class="order-card">
  <div class="order-title">🏪 {order.restaurant_name} &nbsp; {budget_badge}</div>
  {items_html}
  <div class="item-row"><span>Delivery</span><span>LKR {order.delivery_fee:,.2f}</span></div>
  <div class="item-row"><span>Tax (10%)</span><span>LKR {order.tax:,.2f}</span></div>
  <div class="total-row"><span>Total</span><span>LKR {order.total:,.2f}</span></div>
  <div class="rationale">💬 {order.rationale}</div>
</div>
"""
            order_container.markdown(order_html, unsafe_allow_html=True)
        else:
            order_container.error("No valid order could be constructed for your request. Try relaxing your constraints or increasing the budget.")

    except Exception as exc:
        for node in agent_states:
            if agent_states[node] in ("running", "queued"):
                agent_states[node] = "error"
        render_trace()
        order_container.error(f"System error: {exc}")

elif submit and not user_input.strip():
    st.warning("Please enter your food order request.")
