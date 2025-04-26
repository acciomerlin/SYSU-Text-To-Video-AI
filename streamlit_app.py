import traceback

import streamlit as st
import asyncio
import os
#for text generation, use openai or groq. groq model used: "llama3-70b-8192"
#note: use just one
# os.environ["OPENAI_KEY"]="openai-key"
os.environ['GROQ_API_KEY'] = ""
os.environ["PEXELS_KEY"]=""
import tempfile

from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
from utility.render.render_engine import get_output_media

os.environ["XDG_CACHE_HOME"] = "./.cache"

st.title("🎬 校园AI短视频生成器")

topic = st.text_input("请输入你想要生成视频的校园主题", "")

if st.button("开始生成") and topic.strip():
    try:
        with st.spinner("正在生成剧本..."):
            script = generate_script(topic)
            st.success("✅ 剧本生成完成")
            st.text_area("剧本内容", script, height=150)

        SAMPLE_FILE_NAME = "audio_tts.wav"
        VIDEO_SERVER = "pexel"

        with st.spinner("正在合成音频..."):
            asyncio.run(generate_audio(script, SAMPLE_FILE_NAME))
            st.success("✅ 音频生成完成")

        with st.spinner("正在生成字幕..."):
            timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
            st.success("✅ 字幕生成完成")
            st.json(timed_captions)

        with st.spinner("正在生成视频搜索关键词..."):
            search_terms = getVideoSearchQueriesTimed(script, timed_captions)
            st.json(search_terms)

        with st.spinner("正在下载背景视频..."):
            background_video_urls = generate_video_url(search_terms, VIDEO_SERVER)
            if not background_video_urls:
                st.warning("⚠️ 无法获取背景视频")
                st.stop()
            background_video_urls = merge_empty_intervals(background_video_urls)
            st.success("✅ 背景视频获取完成")

        with st.spinner("正在合成最终视频..."):
            output_path = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
            st.success("🎉 视频生成成功！")

        # 显示视频
        st.video(output_path)

    except Exception as e:
        tb = traceback.format_exc()
        st.error(f"❌ 出现错误: {e}")
        st.text("错误详情如下：")
        st.text(tb)
