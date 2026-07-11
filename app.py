"""Streamlit UI for the Data Analyst Agent with visible execution traces."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agent import DataAnalystAgent, TraceStep
from memory import MemoryStore

load_dotenv()

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

st.set_page_config(page_title="Data Analyst Agent", page_icon="📊", layout="wide")

st.title("📊 Data Analyst Agent")
st.caption(
    "Upload a CSV and ask questions. The agent uses safe tools only — no arbitrary code execution."
)

# Sidebar config
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Anthropic API Key", type="password", help="Or set ANTHROPIC_API_KEY in .env")
    max_steps = st.slider("Max agent steps", 3, 15, 10)
    use_planner = st.checkbox("Enable planner", value=True)
    use_memory = st.checkbox("Enable memory", value=True)
    st.caption(f"Model: `{MODEL}`")
    st.divider()
    st.markdown("**Safety model**")
    st.markdown(
        "- Model chooses tools, code executes them\n"
        "- Input sanitization on all string args\n"
        "- Step & token limits enforced\n"
        f"- Max loop limit: **{max_steps} steps**"
    )

# File upload
uploaded = st.file_uploader("Upload CSV", type=["csv"])
default_path = Path(__file__).parent / "data" / "sales.csv"

if uploaded:
    df = pd.read_csv(uploaded)
    st.success(f"Loaded {len(df)} rows × {len(df.columns)} columns from upload")
else:
    df = pd.read_csv(default_path)
    st.info(f"Using sample dataset: `data/sales.csv` ({len(df)} rows)")

with st.expander("Preview data"):
    st.dataframe(df.head(20))

# Example questions
EXAMPLES = [
    "Which product had the highest revenue?",
    "Which region is declining fastest?",
    "Are there outliers in revenue?",
    "Make a chart of monthly sales by region.",
    "Compare Q2 and Q3 by customer segment.",
]

st.subheader("Ask a question")
col1, col2 = st.columns([4, 1])
with col1:
    question = st.text_input("Your question", placeholder="e.g. Which product had the highest revenue?")
with col2:
    st.write("")
    st.write("")
    run_btn = st.button("Analyze", type="primary", use_container_width=True)

st.markdown("**Examples:** " + " · ".join(f"`{e}`" for e in EXAMPLES))

if run_btn and question:
    if not api_key and not Path(".env").exists():
        st.error("Please provide an Anthropic API key in the sidebar or .env file.")
    else:
        with st.spinner("Agent is thinking..."):
            agent = DataAnalystAgent(
                df=df,
                api_key=api_key or None,
                model=MODEL,
                max_steps=max_steps,
                memory=MemoryStore(),
            )
            result = agent.run(question, use_memory=use_memory, use_planner=use_planner)

        if result.success:
            st.subheader("Answer")
            st.markdown(result.answer)
        else:
            st.error(f"Agent error: {result.error}")

        # Metrics bar
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Steps", result.steps)
        m2.metric("Tools called", len(result.tools_called))
        m3.metric("Tokens used", result.total_tokens)
        m4.metric("Charts", len(result.chart_paths))

        # Charts
        for chart_path in result.chart_paths:
            if Path(chart_path).exists():
                st.image(chart_path, caption=Path(chart_path).name)

        # Trace viewer
        st.subheader("Agent Trace")
        for step in result.trace:
            icon = {
                "plan": "📝",
                "tool_call": "🔧",
                "tool_result": "📋",
                "answer": "✅",
                "error": "❌",
            }.get(step.type, "•")

            with st.expander(f"{icon} Step {step.step}: {step.type}" + (f" — {step.tool_name}" if step.tool_name else "")):
                if step.tool_input:
                    st.json(step.tool_input)
                st.code(step.content[:3000], language="json" if step.type == "tool_result" else "text")
                if step.latency_ms:
                    st.caption(f"Latency: {step.latency_ms:.0f}ms · Tokens: {step.tokens_used}")

# Memory panel
with st.expander("Memory (past Q&A)"):
    mem = MemoryStore()
    if mem.entries:
        for entry in mem.entries[-5:]:
            st.markdown(f"**Q:** {entry['question']}")
            st.markdown(f"**A:** {entry['answer'][:300]}")
            st.divider()
    else:
        st.caption("No past analyses yet. Run a question to populate memory.")
