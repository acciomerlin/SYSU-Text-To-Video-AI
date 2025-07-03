import streamlit as st
from datetime import datetime

class SimpleHistory:
    def __init__(self, key="simple_history"):
        self.key = key
        if self.key not in st.session_state:
            st.session_state[self.key] = []

    def add_record(self, url, label="📥 下载资源"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (timestamp, url, label)
        st.session_state[self.key].append(entry)
        st.rerun()

    def render(self):
        st.sidebar.markdown("## 🕘 历史记录")
        for ts, url, label in reversed(st.session_state[self.key]):
            st.sidebar.markdown(f"### {ts}")
            st.sidebar.markdown(f"[{label}]({url})", unsafe_allow_html=True)
