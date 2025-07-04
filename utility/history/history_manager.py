import streamlit as st
import base64
from datetime import datetime
from pathlib import Path

class SimpleHistory:
    def __init__(self, key="simple_history"):
        self.key = key
        if self.key not in st.session_state:
            st.session_state[self.key] = []

    def add_record(self, url_or_path_or_bytes, label="📥 下载资源", is_file=False, filename="resource"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if is_file:  # 如果是本地文件路径或二进制内容
            if isinstance(url_or_path_or_bytes, (str, Path)):
                with open(url_or_path_or_bytes, "rb") as f:
                    data = f.read()
            elif isinstance(url_or_path_or_bytes, bytes):
                data = url_or_path_or_bytes
            else:
                raise TypeError("Unsupported file input type for base64 download")

            b64 = base64.b64encode(data).decode()
            ext = ".mp4" if "视频" in label else ".bin"
            url = f'data:application/octet-stream;base64,{b64}'
            download_link = f'<a href="{url}" download="{filename}{ext}">{label}</a>'
        else:
            # 普通 URL
            download_link = f'<a href="{url_or_path_or_bytes}" target="_blank">{label}</a>'

        st.session_state[self.key].append((timestamp, download_link))

    def render(self):
        st.sidebar.markdown("## 🕘 历史记录")
        for entry in reversed(st.session_state[self.key]):
            if len(entry) == 2:
                ts, link_html = entry
                st.sidebar.markdown(f"### {ts}")
                st.sidebar.markdown(link_html, unsafe_allow_html=True)
            elif len(entry) == 3:
                ts, url, label = entry
                st.sidebar.markdown(f"### {ts}")
                st.sidebar.markdown(f"[{label}]({url})", unsafe_allow_html=True)
            else:
                st.sidebar.warning("⚠️ 历史记录格式错误")

