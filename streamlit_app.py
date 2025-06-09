import asyncio
import os
import traceback
import re
import streamlit as st
from dotenv import load_dotenv
import streamlit.components.v1 as components
import requests
import time

load_dotenv()

from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
from utility.render.render_engine import get_output_media


def generate_all_caption_images_placeholder():
    # TODO: 实现生成所有字幕对应图的逻辑
    pass


def generate_single_caption_image_placeholder(txt):
    API_KEY = os.getenv('FLUX_API_KEY')
    API_BASE = "https://api.piapi.ai/api/v1"
    # 1. 提交生成任务
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    payload = {
        "model": "Qubico/flux1-dev",
        "task_type": "txt2img",
        "input": {
            "prompt": txt,
            "width": 1024,
            "height": 1024
        }
    }

    response = requests.post(f"{API_BASE}/task", json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to submit task: {response.text}")

    task_id = response.json()["data"]["task_id"]
    print(f"Task submitted. Task ID: {task_id}")

    # 2. 轮询任务状态
    while True:
        time.sleep(3)
        poll_response = requests.get(f"{API_BASE}/task/{task_id}", headers={"x-api-key": API_KEY})
        if poll_response.status_code != 200:
            raise Exception(f"Polling failed: {poll_response.text}")

        task_data = poll_response.json()["data"]
        status = task_data["status"]
        print(f"Task status: {status}")

        if status == "completed":
            image_url = task_data["output"]["image_url"]
            print(f"Image generated: {image_url}")
            return image_url
        elif status in ["failed", "retry"]:
            raise Exception(f"Task failed or needs retry: {task_data}")
    # TODO: 实现每个字幕单独生成图的逻辑
    pass


# ========== 输入检测 ==========
def is_valid_input(language: str, text: str) -> bool:
    text = text.strip()
    if not text:
        return False
    if language == "English":
        return bool(re.fullmatch(r"[A-Za-z0-9\s.,!?'-]+", text))
    elif language == "中文":
        return bool(re.match(r"[\u4e00-\u9fff]", text[0]))
    return False


# ========== Streamlit UI ==========
st.title("🎬 校园AI短视频生成器")

language_option = st.selectbox("请选择语言", ["中文", "English"])
topic = st.text_input("请输入你想要生成视频的校园主题", "")
language = 1 if language_option == "中文" else 0

# ========== 状态变量 ==========
if "script" not in st.session_state:
    st.session_state.script = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "captions" not in st.session_state:
    st.session_state.captions = None
if "search_terms" not in st.session_state:
    st.session_state.search_terms = None
if "video_urls" not in st.session_state:
    st.session_state.video_urls = None
if "final_video" not in st.session_state:
    st.session_state.final_video = None

SAMPLE_FILE_NAME = "audio_tts.wav"
VIDEO_SERVER = "pexel"

# ========== 输入检测 ==========
if topic:
    if not is_valid_input(language_option, topic):
        st.error("❌ 输入格式错误：英文模式下仅允许英文字母，中文模式下必须以中文字符开头")
    else:
        st.success("✅ 输入格式合法")

        # 1. 生成剧本
        if st.button("1️⃣ 生成剧本"):
            with st.spinner("生成剧本中..."):
                try:
                    st.session_state.script = generate_script(topic, language)
                    st.success("✅ 剧本生成完成")
                except Exception as e:
                    st.error(f"❌ 剧本生成出错: {e}")

        # 剧本预览（不放在按钮逻辑内）
        if st.session_state.script:
            st.text_area("📜 剧本内容", st.session_state.script, height=150)

        # 2. 合成音频
        if st.session_state.script and st.button("2️⃣ 合成音频"):
            with st.spinner("合成音频中..."):
                try:
                    asyncio.run(generate_audio(st.session_state.script, SAMPLE_FILE_NAME))
                    st.session_state.audio_path = SAMPLE_FILE_NAME
                    st.success("✅ 音频合成完成")
                except Exception as e:
                    st.error(f"❌ 音频合成出错: {e}")

        # 音频预览
        if st.session_state.audio_path:
            st.audio(st.session_state.audio_path, format="audio/wav")

        # 3. 生成字幕
        if st.session_state.audio_path and st.button("3️⃣ 生成字幕"):
            with st.spinner("生成字幕中..."):
                try:
                    st.session_state.captions = generate_timed_captions(st.session_state.audio_path,
                                                                        st.session_state.script, "base", language)
                    st.success("✅ 字幕生成完成")
                except Exception as e:
                    st.error(f"❌ 字幕生成出错: {e}")

        # 字幕预览
        if st.session_state.captions:
            st.markdown("#### 📑 字幕预览")
            st.json(st.session_state.captions)

        if st.session_state.captions:
            st.markdown("#### 📑 字幕列表")
            if "captions" not in st.session_state:
                st.session_state.captions = [([0.0, 2.5], "Hello"), ([2.5, 5.0], "World")]

            # 初始化 URL 数组（与 captions 等长）
            if "caption_img_urls" not in st.session_state:
                st.session_state.caption_img_urls = [""] * len(st.session_state.captions)

            # 一键生成按钮
            col_all, _ = st.columns([2, 6])
            with col_all:
                if st.button("🖼️ 一键生成所有字幕图"):
                    try:
                        for idx, item in enumerate(st.session_state.captions):
                            if st.session_state.caption_img_urls[idx] == "":
                                if isinstance(item, (list, tuple)) and len(item) == 2:
                                    _, text = item
                                    image_url = generate_single_caption_image_placeholder(text)
                                    st.session_state.caption_img_urls[idx] = image_url
                                    st.info(f"✅ 第 {idx} 条字幕图生成成功")
                                    st.write(st.session_state.caption_img_urls)  # 🔍 打印当前数组
                        st.success("✅ 所有字幕图生成完成")
                    except Exception as e:
                        st.error(f"❌ 批量生成字幕图失败: {e}")

            # 单独逐条生成
            for idx, item in enumerate(st.session_state.captions):
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    time_range, text = item
                    if isinstance(time_range, (list, tuple)) and len(time_range) == 2:
                        start = float(time_range[0])
                        end = float(time_range[1])

                        col1, col2 = st.columns([6, 2])
                        with col1:
                            st.markdown(f"**[{round(start, 2)}s - {round(end, 2)}s]** {text}")
                        with col2:
                            if st.button("生成图", key=f"caption_img_{idx}"):
                                st.info(f"你点击了第 {idx} 个字幕图按钮")
                                try:
                                    image_url = generate_single_caption_image_placeholder(text)
                                    st.session_state.caption_img_urls[idx] = image_url
                                    st.success(f"✅ 字幕 {idx + 1} 图像生成成功")
                                except Exception as e:
                                    st.error(f"图片生成失败：{e}")

                        # 展示图像
                        if st.session_state.caption_img_urls[idx]:
                            st.image(st.session_state.caption_img_urls[idx], caption=f"字幕图像 {idx + 1}",
                                     use_container_width=True)
                    else:
                        st.warning(f"⛔ 第 {idx} 条字幕时间范围格式错误：{time_range}")
                else:
                    st.warning(f"⚠️ 第 {idx} 条字幕结构异常：{item}")

            # 👇 每次渲染都打印一次数组（调试用）
            st.markdown("### 🧾 当前字幕图像 URL 列表")
            # 这个列表里存了字母的idx和对应的图片url， 如果图片没有生成url串就是空。
            st.write(st.session_state.caption_img_urls)

        # 4. 生成关键词
        if st.session_state.script and st.session_state.captions and st.button("4️⃣ 生成视频搜索关键词"):
            with st.spinner("生成搜索关键词中..."):
                try:
                    st.session_state.search_terms = getVideoSearchQueriesTimed(st.session_state.script,
                                                                               st.session_state.captions)
                    st.success("✅ 搜索关键词生成完成")
                except Exception as e:
                    st.error(f"❌ 关键词生成出错: {e}")

        # 搜索关键词预览
        if st.session_state.search_terms:
            st.json(st.session_state.search_terms)

        # 5. 获取背景视频
        if st.session_state.search_terms and st.button("5️⃣ 获取背景视频"):
            with st.spinner("获取背景视频中..."):
                try:
                    urls = generate_video_url(st.session_state.search_terms, VIDEO_SERVER)
                    if not urls:
                        st.warning("⚠️ 未找到背景视频")
                    else:
                        st.session_state.video_urls = merge_empty_intervals(urls)
                        st.success("✅ 背景视频获取完成")
                except Exception as e:
                    st.error(f"❌ 视频获取出错: {e}")

        # 视频链接预览
        if st.session_state.video_urls:
            st.json(st.session_state.video_urls)

        # 6. 合成最终视频
        if st.session_state.video_urls and st.button("6️⃣ 合成最终视频"):
            with st.spinner("视频合成中..."):
                try:
                    st.session_state.final_video = get_output_media(
                        SAMPLE_FILE_NAME,
                        st.session_state.captions,
                        st.session_state.video_urls,
                        VIDEO_SERVER
                    )
                    st.success("🎉 视频合成完成！")
                except Exception as e:
                    st.error(f"❌ 视频合成失败: {e}")

        # 最终视频预览
        if st.session_state.final_video:
            st.video(st.session_state.final_video)
