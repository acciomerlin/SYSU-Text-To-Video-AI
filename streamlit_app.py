import asyncio
import traceback
import re
import streamlit as st
from dotenv import load_dotenv
import streamlit.components.v1 as components

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

def generate_single_caption_image_placeholder():
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
                    st.session_state.captions = generate_timed_captions(st.session_state.audio_path, st.session_state.script, "base",language)
                    st.success("✅ 字幕生成完成")
                except Exception as e:
                    st.error(f"❌ 字幕生成出错: {e}")

        # 字幕预览
        if st.session_state.captions:
            st.markdown("#### 📑 字幕预览")
            st.json(st.session_state.captions)

        if st.session_state.captions:
            st.markdown("#### 📑 字幕列表")

            col_all, _ = st.columns([2, 6])
            with col_all:
                if st.button("🖼️ 一键生成所有字幕图"):
                    try:
                        generate_all_caption_images_placeholder()
                        st.success("✅ 所有字幕图生成完成（待实现）")
                    except Exception as e:
                        st.error(f"❌ 批量生成字幕图失败: {e}")

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
                                st.info(f"你点击了第 {idx} 个字幕图按钮（待实现）")
                    else:
                        st.warning(f"⛔ 第 {idx} 条字幕时间范围格式错误：{time_range}")
                else:
                    st.warning(f"⚠️ 第 {idx} 条字幕结构异常：{item}")

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

