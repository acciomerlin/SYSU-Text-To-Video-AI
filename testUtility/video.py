import streamlit as st
import requests
import time
import os
import json
import base64

# ----------------- 配置项 -------------------
VIDU_API_KEY = "vda_836490931149479936_Ra1PbTMng8FNWlayqd0aA85VP6X4WlbV"
VIDU_API_BASE = "https://api.vidu.cn/ent/v2"
IMGBB_API_KEY = os.getenv("IMGBB_KEY") or "543c1f4a80df82b08f0fa3929f8bc2e1"
POLL_INTERVAL = 5
# -------------------------------------------

st.set_page_config(page_title="图片生成视频", layout="centered")
st.title("🖼️ → 🎬 图片生成视频")

uploaded_file = st.file_uploader("请上传一张图片（jpg/png）", type=["jpg", "jpeg", "png"])
duration = st.slider("生成视频的时长（秒）", min_value=2, max_value=16, value=5)
prompt = st.text_input("请输入视频生成的 Prompt", "The astronaut waved and the camera moved up.")

# 状态变量
task_id_holder = st.empty()
cancel_button_holder = st.empty()
video_placeholder = st.empty()
status_display = st.empty()
spinner_placeholder = st.empty()

# 初始化轮询标志
if "polling_active" not in st.session_state:
    st.session_state.polling_active = False
if "current_task_id" not in st.session_state:
    st.session_state.current_task_id = None


# 取消任务函数
def cancel_task():
    if not st.session_state.current_task_id:
        st.warning("无任务正在运行")
        return
    try:
        headers = {
            "Authorization": f"Token {VIDU_API_KEY}",
            "Content-Type": "application/json"
        }
        cancel_payload = {"id": st.session_state.current_task_id}
        cancel_url = f"{VIDU_API_BASE}/tasks/{st.session_state.current_task_id}/cancel"
        cancel_res = requests.post(cancel_url, headers=headers, json=cancel_payload)
        cancel_res.raise_for_status()
        st.session_state.polling_active = False
        status_display.warning("任务已取消 ❌")
    except Exception as e:
        status_display.error(f"取消失败：{e}")


# 主流程
if uploaded_file and st.button("🚀 生成视频"):
    st.session_state.polling_active = True
    st.info("正在上传图片至图床...")

    # Step 1: 上传图片到 imgbb
    img_bytes = uploaded_file.read()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    try:
        imgbb_res = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": img_base64}
        )
        imgbb_res.raise_for_status()
        image_url = imgbb_res.json()["data"]["url"]
        st.success("图片上传成功 ✅")
        st.image(image_url)
    except Exception as e:
        st.error(f"上传图片失败：{e}")
        st.stop()

    # Step 2: 创建视频任务
    headers = {
        "Authorization": f"Token {VIDU_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "viduq1",
        "images": [image_url],
        "prompt": prompt,
        "duration": str(duration),
        "seed": "0",
        "resolution": "1080p",
        "movement_amplitude": "auto"
    }
    try:
        res = requests.post(f"{VIDU_API_BASE}/img2video", headers=headers, json=payload)
        res.raise_for_status()
        response_json = res.json()
        task_id = response_json.get("task_id")
        if not task_id:
            st.error("未能获取任务 ID，请检查响应内容")
            st.stop()
        st.session_state.current_task_id = task_id
        task_id_holder.success(f"任务已创建 ✅ task_id: {task_id}")
    except Exception as e:
        st.error(f"创建任务失败：{e}")
        st.stop()

    # Step 3: 取消按钮
    cancel_button_holder.button("❌ 取消任务", on_click=cancel_task)

    # Step 4: 轮询状态
    with spinner_placeholder:
        with st.spinner("🎞️ 视频生成中，请稍候..."):
            video_url = None
            while st.session_state.polling_active:
                time.sleep(POLL_INTERVAL)
                try:
                    poll_res = requests.get(
                        f"{VIDU_API_BASE}/tasks/{task_id}/creations",
                        headers=headers
                    )
                    poll_res.raise_for_status()
                    task_data = poll_res.json()
                    state = task_data.get("state")
                    status_display.info(f"⏳ 当前任务状态：{state}")

                    if state == "success":
                        st.success("任务成功 ✅")
                        st.markdown("### 📦 返回结果")
                        st.json(task_data)
                        creations = task_data.get("creations", [])
                        if creations and creations[0].get("url"):
                            video_url = creations[0]["url"]
                        else:
                            st.error("任务成功但未返回视频 URL")
                        break
                    elif state == "failed":
                        st.error("任务失败 ❌")
                        st.session_state.polling_active = False
                        st.stop()
                    elif state in ["created", "queueing", "processing"]:
                        continue
                    else:
                        st.warning(f"未知状态：{state}")
                except Exception as e:
                    st.warning(f"轮询失败：{e}")
                    break

            st.session_state.polling_active = False

    if video_url:
        st.success("🎉 视频生成成功！")
        video_placeholder.video(video_url)