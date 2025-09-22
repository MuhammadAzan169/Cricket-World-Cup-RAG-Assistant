import streamlit as st
from main import initialize_system
import time
import json
import os
from pathlib import Path

# ---------------------------
# Page Configuration
# ---------------------------
st.set_page_config(
    page_title="Cricket World Cup RAG Assistant",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# Constants
# ---------------------------
DATA_DIR = Path(os.getcwd())
GLOBAL_STATS_FILE = DATA_DIR / "global_stats.json"

# ---------------------------
# Custom CSS for dark professional theme
# ---------------------------
st.markdown("""
<style>
body {
    background-color: #0a0f2c;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
}
h1, h2, h3, h4 {
    color: #00bfff;
}
.stButton>button {
    background-color: #1f2a6c;
    color: #ffffff;
    border-radius: 8px;
    padding: 0.5em 1.2em;
    font-weight: bold;
}
.stButton>button:hover {
    background-color: #3a46a2;
}
.stTextInput>div>div>input {
    background-color: #1f2a6c;
    color: #ffffff;
    border-radius: 6px;
    border: 1px solid #3a46a2;
    padding: 0.4em;
}
.stMarkdown pre {
    background-color: #1f2a6c;
    color: #ffffff;
    border-radius: 6px;
    padding: 0.5em;
}
.dataframe th {
    background-color: #1f2a6c !important;
    color: #00bfff !important;
}
.dataframe td {
    background-color: #0f1433 !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Sidebar
# ---------------------------
st.sidebar.title("Cricket RAG Assistant")
st.sidebar.markdown("Ask questions about Cricket World Cups (2003-2023).")
st.sidebar.markdown("---")

example_queries = [
    "Who won the 2019 Cricket World Cup final?",
    "What was the final score of the 2003 World Cup final?",
    "Which matches in 2007 were decided by less than 10 runs?",
    "Who scored the most runs in 2015?",
    "Who took the most wickets in 2011?"
]

st.sidebar.subheader("Example Queries")
for q in example_queries:
    if st.sidebar.button(q):
        st.session_state['query'] = q

st.sidebar.markdown("---")
st.sidebar.subheader("Settings")
max_results = st.sidebar.slider("Max Results for RAG Search", 5, 100, 40)
refresh_btn = st.sidebar.button("Refresh Global Stats")

# ---------------------------
# Header
# ---------------------------
st.image("https://upload.wikimedia.org/wikipedia/commons/3/3a/Cricket_ball.png", width=80)
st.title("🏏 Cricket World Cup RAG Assistant")
st.markdown(
    """
    Ask any question about Cricket World Cups (2003-2023).  
    Examples:
    - Who won the 2019 Cricket World Cup final?  
    - What was the final score of the 2003 World Cup final?  
    - Which matches in 2007 were decided by less than 10 runs?
    """
)

# ---------------------------
# Initialize system (cached)
# ---------------------------
@st.cache_resource(show_spinner=True)
def load_system():
    return initialize_system()

with st.spinner("Initializing Cricket RAG System..."):
    qp = load_system()

# ---------------------------
# Query input
# ---------------------------
if 'query' not in st.session_state:
    st.session_state['query'] = ""

query_input = st.text_input("Type your question here:", st.session_state['query'])
st.session_state['query'] = query_input

# ---------------------------
# Load global stats
# ---------------------------
def load_global_stats():
    if GLOBAL_STATS_FILE.exists():
        with open(GLOBAL_STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

global_stats = load_global_stats()

# ---------------------------
# Display query results
# ---------------------------
if query_input:
    with st.spinner("Processing your query..."):
        start_time = time.time()
        answer = qp.process_query(query_input, max_results=max_results)
        elapsed = time.time() - start_time

    st.markdown("---")
    st.subheader("Answer")
    st.markdown(answer)

    st.caption(f"⏱ Query processed in {elapsed:.2f} seconds")

# ---------------------------
# Optional: display global stats
# ---------------------------
if st.checkbox("Show Global Stats Table"):
    if global_stats:
        st.markdown("---")
        st.subheader("World Cup Finals & Semi-finalists (2003-2023)")
        try:
            import pandas as pd
            finals_data = global_stats.get("finals", [])
            if finals_data:
                df = pd.DataFrame([
                    {
                        "Year": f.get("year",""),
                        "Winner": f.get("winner",""),
                        "Player of Match": ", ".join(f.get("player_of_match",[])),
                        "Semi-finalists": ", ".join(f.get("semi_finalists",[])),
                        "Final Score": f.get("score","")
                    } for f in finals_data
                ])
                st.dataframe(df)
            else:
                st.info("Global stats are empty.")
        except Exception as e:
            st.error(f"Error loading global stats table: {e}")
    else:
        st.info("Global stats not available.")

# ---------------------------
# Refresh stats button
# ---------------------------
if refresh_btn:
    with st.spinner("Refreshing global stats..."):
        qp.compute_global_stats()
        st.success("✅ Global stats refreshed.")

# ---------------------------
# Search history panel
# ---------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("Search History")
if 'history' not in st.session_state:
    st.session_state['history'] = []
if query_input and query_input not in st.session_state['history']:
    st.session_state['history'].append(query_input)
for idx, q in enumerate(reversed(st.session_state['history'][-20:]), 1):
    st.sidebar.markdown(f"{idx}. {q}")

# ---------------------------
# Footer
# ---------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#888888;'>Cricket RAG Assistant | Version 1.0 | Developed by Azan</div>",
    unsafe_allow_html=True
)
