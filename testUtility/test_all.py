import asyncio
import base64
import json
import os
import re
import uuid

import requests
import streamlit as st
import time
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
from dotenv import load_dotenv
from dashscope import ImageSynthesis

from utility.script.script_generator import generate_script

# ========== 加载 .env 配置 ==========
load_dotenv()
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
VIDU_API_KEY = os.getenv("VIDU_API_KEY")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")
VIDU_API_BASE = "https://api.vidu.cn/ent/v2"
POLL_INTERVAL = 5

st.set_page_config(page_title="校园AI短视频生成器", layout="centered")
st.title("🎬 校园AI短视频生成器")

language_option = st.selectbox("请选择语言", ["中文", "English"])
topic = st.text_input("请输入你想要生成视频的校园主题", "")
language = 1 if language_option == "中文" else 0

# 会话变量初始化
for key in ["script", "scene_texts", "image_urls", "video_urls"]:
    st.session_state.setdefault(key, None)


# ========== 输入合法性检查 ==========
def is_valid_input(language: str, text: str) -> bool:
    text = text.strip()
    if not text:
        return False
    if language == "English":
        return bool(re.fullmatch(r"[A-Za-z0-9\s.,!?'-]+", text))
    elif language == "中文":
        return bool(re.match(r"[\u4e00-\u9fff]", text[0]))
    return False


# ========== 图像生成 ==========
def generate_single_caption_image(style, txt):
    prompt = f"{style} 风格，{style} 风格，描绘{txt}场景"
    rsp = ImageSynthesis.call(
        api_key=DASHSCOPE_API_KEY,
        model="wanx2.1-t2i-turbo",
        prompt=prompt,
        n=1,
        size='1024*1024'
    )
    if rsp.status_code == HTTPStatus.OK:
        url = rsp.output.results[0].url
        filename = PurePosixPath(unquote(urlparse(url).path)).parts[-1]

        folder = "images"
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        with open(filepath, 'wb') as f:
            f.write(requests.get(url).content)

        return url
    else:
        raise Exception(f"图像生成失败: {rsp.status_code}, code: {rsp.code}, message: {rsp.message}")


# ========== 音频生成函数 ==========
def generate_audio(prompt, duration=5.0, seed=0):
    headers = {"Authorization": f"Token {VIDU_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "audio1.0",
        "prompt": prompt,
        "duration": duration,
        "seed": seed
    }
    res = requests.post(f"{VIDU_API_BASE}/text2audio", headers=headers, json=payload)
    if res.status_code != 200:
        raise Exception(f"音频生成请求失败：{res.status_code}")
    task_id = res.json()["task_id"]

    # 轮询查询任务状态
    poll_status = st.empty()
    while True:
        time.sleep(POLL_INTERVAL)
        poll = requests.get(f"{VIDU_API_BASE}/tasks/{task_id}/creations", headers=headers)
        poll_json = poll.json()
        state = poll_json.get("state", "")
        if state == "failed":
            raise Exception("音频生成失败")
        elif state == "success":
            poll_status.empty()  # ✅ 清除轮询状态提示
            return poll_json["creations"][0]["url"]
        else:
            poll_status.info(f"🎵 音频生成状态：{state}")


import os
import tempfile
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips


def download_file(url, folder, prefix):
    # 获取文件扩展名，例如 .mp4 或 .mp3
    path = urlparse(url).path
    ext = os.path.splitext(path)[-1]

    # 使用 uuid 保证唯一且简短
    filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
    local_path = os.path.join(folder, filename)

    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(local_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    return local_path


def merge_videos_and_audios(video_urls, audio_urls):
    # 临时目录存放下载文件
    with tempfile.TemporaryDirectory() as tmpdir:
        video_clips = []
        audio_clips = []

        # 下载视频和音频，读取为moviepy对象
        for i, (v_url, a_url) in enumerate(zip(video_urls, audio_urls)):
            v_path = download_file(v_url, tmpdir, f"video{i}")
            a_path = download_file(a_url, tmpdir, f"audio{i}")

            video_clip = VideoFileClip(v_path)
            audio_clip = AudioFileClip(a_path)

            video_clips.append(video_clip)
            audio_clips.append(audio_clip)

        # 合并视频
        final_video = concatenate_videoclips(video_clips, method="compose")

        # 合并音频
        final_audio = concatenate_audioclips(audio_clips)

        # 设置合成后的音频到视频
        final_video = final_video.set_audio(final_audio)

        # 导出最终视频文件
        output_path = os.path.join(tmpdir, "final_video.mp4")
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

        # 释放资源
        for clip in video_clips + audio_clips:
            clip.close()
        final_video.close()
        final_audio.close()

        # 读取导出文件的二进制，用于streamlit播放
        with open(output_path, "rb") as f:
            video_bytes = f.read()

        return video_bytes


# ========== 主流程 ==========
st.markdown("## 🖊️ 生成主题剧本")
if topic:
    if not is_valid_input(language_option, topic):
        st.error("❌ 输入格式错误")
    else:
        st.success("✅ 输入格式合法")

        if st.button("1️⃣ 生成剧本"):
            with st.spinner("生成剧本中..."):
                st.session_state.script = generate_script(topic, language)
                st.success("✅ 剧本生成完成")

        if st.session_state.script:
            st.text_area("📜 剧本内容（只读）", st.session_state.script, height=150, disabled=True)
            # ===== 🎨 图像风格选择模块（支持推荐标签点击填入） =====
            default_styles = ["宫崎骏风格", "迪士尼卡通", "中国水墨", "儿童绘本风", "像素画风", "油画质感", "赛博朋克",
                              "毕加索风格"]

            st.markdown("## 🖼️ 生成剧本场景")
            st.markdown("🎨 推荐图像风格（点击可填入）：")

            # 创建多列按钮布局
            cols = st.columns(len(default_styles))
            for i, style in enumerate(default_styles):
                if cols[i].button(style):
                    st.session_state["selected_style"] = style  # 点击某个按钮后，保存风格到 session_state

            # 获取默认文本：如果用户点了按钮就用它，否则为空
            default_text = st.session_state.get("selected_style", "")

            # 显示输入框，默认填入刚才点击的推荐风格
            user_style_input = st.text_input("✏️ 请输入图像风格（可参考上方标签）", value=default_text,
                                             placeholder="如：油画质感、像素画风、宫崎骏风格等")

            # 决定最终图像风格：优先使用用户输入，其次用推荐默认值
            final_style = user_style_input.strip() if user_style_input.strip() else default_styles[0]

            if st.button("2️⃣ 智能切分剧本，一键生成所有场景图片"):
                # 根据语言选择合适的句子分隔符（中文：。；英文：.）
                if language_option == "中文":
                    delimiters = "。"  # 可加入感叹号、问号
                else:
                    delimiters = "."
                # 正则表达式分割句子（保留分隔符后再 strip）
                import re

                pattern = rf"([^{delimiters}]*[{delimiters}])"
                segments = re.findall(pattern, st.session_state.script)
                st.session_state.scene_texts = [seg.strip() for seg in segments if seg.strip()]

                st.session_state.image_urls = [None] * len(st.session_state.scene_texts)

                with st.spinner("生成中..."):
                    progress = st.progress(0, text="开始生成图片...")
                    for idx, text in enumerate(st.session_state.scene_texts):
                        try:
                            url = generate_single_caption_image(final_style, text)
                            st.session_state.image_urls[idx] = url
                            progress.progress((idx + 1) / len(st.session_state.scene_texts),
                                              text=f"已完成第 {idx + 1}/{len(st.session_state.scene_texts)} 张")
                            # st.image(url, caption=text, use_container_width=True)
                        except Exception as e:
                            st.warning(f"第 {idx + 1} 张生成失败：{e}")
                    progress.empty()
                    st.success("🎉 所有图片生成完成")

        # --- 展示每张图 + 生成视频/音频按钮 ---
        if st.session_state.image_urls:
            # st.markdown("### 🖼️ 每个场景生成内容（图+视频+音）")

            if "video_urls" not in st.session_state or st.session_state.video_urls is None:
                st.session_state.video_urls = [None] * len(st.session_state.image_urls)
            if "audio_urls" not in st.session_state or st.session_state.audio_urls is None:
                st.session_state.audio_urls = [None] * len(st.session_state.image_urls)

            for idx, (img_url, text) in enumerate(zip(st.session_state.image_urls, st.session_state.scene_texts)):
                with st.container():
                    st.markdown(f"### 场景{idx + 1}图片")
                    st.image(img_url, caption=text, use_container_width=True)

                    cols = st.columns(2)
                    cols = st.columns(2)

                    # 左边：生成视频按钮及展示
                    with cols[0]:
                        if st.button(f"🎞️ 生成视频 - 场景 {idx + 1}", key=f"gen_vid_{idx}"):
                            try:
                                headers = {"Authorization": f"Token {VIDU_API_KEY}", "Content-Type": "application/json"}
                                payload = {
                                    "model": "viduq1",
                                    "images": [img_url],
                                    "prompt": text,
                                    "duration": "5",
                                    "seed": "0",
                                    "resolution": "1080p",
                                    "movement_amplitude": "auto",
                                    # "bgm": "true"
                                }
                                res = requests.post(f"{VIDU_API_BASE}/img2video", headers=headers, json=payload)
                                task_id = res.json()["task_id"]

                                poll_status = st.empty()
                                while True:
                                    time.sleep(POLL_INTERVAL)
                                    poll = requests.get(f"{VIDU_API_BASE}/tasks/{task_id}/creations", headers=headers)
                                    state = poll.json().get("state", "")
                                    if state == "success":
                                        video_url = poll.json()["creations"][0]["url"]
                                        st.session_state.video_urls[idx] = video_url
                                        poll_status.success(f"✅ 场景 {idx + 1} 视频生成成功")
                                        break
                                    elif state == "failed":
                                        poll_status.error(f"❌ 场景 {idx + 1} 视频生成失败")
                                        break
                                    else:
                                        poll_status.info(f"📡 场景 {idx + 1} 视频生成状态：{state}")
                            except Exception as e:
                                st.warning(f"场景 {idx + 1} 视频请求失败：{e}")

                        if st.session_state.video_urls[idx]:
                            st.video(st.session_state.video_urls[idx], format="video/mp4")

                    # 右边：生成音频按钮及展示
                    with cols[1]:
                        if st.button(f"🎵 生成背景音 - 场景 {idx + 1}", key=f"gen_audio_{idx}"):
                            try:
                                st.empty()
                                audio_url = generate_audio(
                                    prompt="舒缓小声的，音色干净的不要炸耳朵的，为" + text + "场景做的的轻快连贯重复不停的背景音乐",
                                    duration=5.0)
                                st.session_state.audio_urls[idx] = audio_url
                                st.success(f"✅ 场景 {idx + 1} 背景音生成成功")
                            except Exception as e:
                                st.warning(f"❌ 场景 {idx + 1} 音频生成失败：{e}")

                        if st.session_state.audio_urls[idx]:
                            st.audio(st.session_state.audio_urls[idx], format="audio/mp3")

            # ✅ 判断是否所有视频和音频均已生成，显示合成按钮
            all_video_ready = all(url is not None for url in st.session_state.video_urls)
            all_audio_ready = all(url is not None for url in st.session_state.audio_urls)
            all_video_ready = True
            all_audio_ready = True

            if all_video_ready and all_audio_ready:
                st.markdown("## 🤩 生成最终短视频")
                if st.button("## 🎬 合成最终视频"):
                    try:
                        video_data = merge_videos_and_audios(st.session_state.video_urls, st.session_state.audio_urls)
                        st.success("✅ 合成完成！播放最终视频：")
                        st.video(video_data)
                    except Exception as e:
                        st.error(f"合成失败：{e}")
