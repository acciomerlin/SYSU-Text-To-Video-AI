import base64
import os
import re
import shutil
import time
import uuid
from http import HTTPStatus
from pathlib import PurePosixPath
from urllib.parse import urlparse, unquote
import requests
import streamlit as st
from dashscope import ImageSynthesis
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from utility.history.history_manager import SimpleHistory
from utility.script.script_generator import generate_script

# 加载 .env
load_dotenv()
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
VIDU_API_KEY = os.getenv("VIDU_API_KEY")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")
VIDU_API_BASE = "https://api.vidu.cn/ent/v2"
POLL_INTERVAL = 5
# 替换成你自己的ImageMagick 安装路径
os.environ["IMAGEMAGICK_BINARY"] = r"D:\Program Files\ImageMagick-7.1.1-Q16\magick.exe"


def get_download_link(file_path, file_label):
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:video/mp4;base64,{b64}" download="{file_label}.mp4">📥 点击下载最终视频</a>'
    return href


# 输入合法性检查
def is_valid_input(language: str, text: str) -> bool:
    text = text.strip()
    if not text:
        return False
    if language == "English":
        return bool(re.fullmatch(r"[A-Za-z0-9\s.,!?'-]+", text))
    elif language == "中文":
        return bool(re.match(r"[\u4e00-\u9fff]", text[0]))
    return False


# 图像生成
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


# 音频生成
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


def merge_videos_and_audios(video_urls, audio_urls, captions):
    # 临时目录
    tmpdir = "temp_merge"
    os.makedirs(tmpdir, exist_ok=True)

    video_clips = []

    try:
        # 下载视频和音频，读取为moviepy对象
        for i, (v_url, a_url) in enumerate(zip(video_urls, audio_urls)):
            v_path = download_file(v_url, tmpdir, f"video{i}")
            a_path = download_file(a_url, tmpdir, f"audio{i}")

            video_clip = VideoFileClip(v_path)
            audio_clip = AudioFileClip(a_path)

            text = captions[i]
            subtitle = TextClip(
                txt=text,
                fontsize=48,
                font="冬青黑體簡體中文-W3",  # 建议：Mac: 黑体 Windows: SimHei
                color='white',
                stroke_color='black',
                method='label'
            ).set_position(("center", video_clip.h - 150)).set_duration(video_clip.duration)

            composite_clip = CompositeVideoClip([video_clip, subtitle])
            composite_clip = composite_clip.set_audio(audio_clip)

            video_clips.append(composite_clip)

        final_video = concatenate_videoclips(video_clips, method="compose")

        output_path = os.path.join(tmpdir, "final_video.mp4")
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=25)

        # 读取视频二进制
        with open(output_path, "rb") as f:
            video_bytes = f.read()

        return video_bytes

    finally:
        # 清理临时文件夹（调试时可以注释掉）
        shutil.rmtree(tmpdir, ignore_errors=True)

# start ui
st.set_page_config(page_title="校园AI短视频生成器", layout="centered")
st.title("🎬 校园AI短视频生成器")

language_option = st.selectbox("请选择语言", ["中文", "English"])
topic = st.text_input("请输入你想要生成视频的校园主题", "")
language = 1 if language_option == "中文" else 0

# 会话变量初始化
for key in ["script", "scene_texts", "image_urls", "video_urls", "final_video_data", "final_video_url",
            "final_video_path"]:
    st.session_state.setdefault(key, None)

# 历史记录功能初始化
history = SimpleHistory()
history.render()

# 主流程 + ui
st.markdown("## 🖊️ 生成主题剧本")
if topic:
    if not is_valid_input(language_option, topic):
        if language_option == "中文":
            st.error("❌ 输入格式错误：请输入以中文字符开头的内容，可包含中文标点（如：。！？）")
        else:
            st.error("❌ 输入格式错误：仅允许英文、数字、空格和标点符号（如 . , ! ? ' -）")
    else:
        st.success("✅ 输入格式合法")

        if st.button("1️⃣ 生成剧本"):
            with st.spinner("生成剧本中..."):
                st.session_state.script = generate_script(topic, language)
                st.success("✅ 剧本生成完成")

        if st.session_state.script:
            st.text_area("📜 剧本内容（只读）", st.session_state.script, height=150, disabled=True)
            # 图像风格选择模块（支持推荐标签点击填入）
            default_styles = ["宫崎骏风格", "迪士尼卡通", "中国水墨", "儿童绘本风", "像素画风", "油画质感", "赛博朋克",
                              "毕加索风格"]

            st.markdown("## 🖼️ 生成剧本场景")
            st.markdown("🎨 推荐图像风格（点击可填入）：")

            cols = st.columns(len(default_styles))
            for i, style in enumerate(default_styles):
                if cols[i].button(style):
                    st.session_state["selected_style"] = style

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

                # 初始化图像URL列表
                st.session_state.image_urls = [None] * len(st.session_state.scene_texts)

                with st.spinner("生成中..."):
                    progress = st.progress(0, text="开始生成图片...")
                    for idx, text in enumerate(st.session_state.scene_texts):
                        try:
                            # ✅ 构造带前文的 prompt
                            if idx > 0:
                                prev_text = st.session_state.scene_texts[idx - 1]
                                prompt = f"在“{prev_text}”的前提下，你接下来根据“{text}”生成图片"
                            else:
                                prompt = text

                            url = generate_single_caption_image(final_style, prompt)
                            st.session_state.image_urls[idx] = url

                            progress.progress((idx + 1) / len(st.session_state.scene_texts),
                                              text=f"已完成第 {idx + 1}/{len(st.session_state.scene_texts)} 张")
                        except Exception as e:
                            st.warning(f"第 {idx + 1} 张生成失败：{e}")
                    progress.empty()
                    st.success("🎉 所有图片生成完成")

                    for idx, (url, text) in enumerate(zip(st.session_state.image_urls, st.session_state.scene_texts)):
                        print(f"{url}")
                        if url is not None:
                            history.add_record(url, label=f"🖼️ 场景 {idx + 1} - {text[:10]} 图片")
                        else:
                            st.warning("当前资源未生成成功，跳过展示/处理")
                    st.rerun()
        # 展示每张图 + 生成视频/音频按钮
        if st.session_state.image_urls:
            if "video_urls" not in st.session_state or st.session_state.video_urls is None:
                st.session_state.video_urls = [None] * len(st.session_state.image_urls)
            if "audio_urls" not in st.session_state or st.session_state.audio_urls is None:
                st.session_state.audio_urls = [None] * len(st.session_state.image_urls)

            for idx, (img_url, text) in enumerate(zip(st.session_state.image_urls, st.session_state.scene_texts)):
                with st.container():
                    st.markdown(f"### 场景{idx + 1}图片")
                    if img_url:
                        st.image(img_url, caption=text, use_container_width=True)
                    else:
                        st.warning(f"⚠️ 场景 {idx + 1} 图片未生成成功，无法展示")

                    cols = st.columns(2)
                    cols = st.columns(2)

                    # 生成视频按钮及展示
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
                                        history.add_record(video_url, label=f"🎞️场景 {idx + 1} {text[:10]} 视频下载")
                                        st.rerun()
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

                    # 生成音频按钮及展示
                    with cols[1]:
                        if st.button(f"🎵 生成背景音 - 场景 {idx + 1}", key=f"gen_audio_{idx}"):
                            try:
                                st.empty()
                                audio_url = generate_audio(
                                    prompt="舒缓小声的，音色干净的不要炸耳朵的，为" + text + "场景做的的轻快连贯重复不停的背景音乐",
                                    duration=5.0)
                                st.session_state.audio_urls[idx] = audio_url
                                st.success(f"✅ 场景 {idx + 1}{text[:10]} 背景音生成成功")
                                history.add_record(audio_url, label=f"🎵 场景 {idx + 1} {text[:10]} 音频下载")
                                st.rerun()

                            except Exception as e:
                                st.warning(f"❌ 场景 {idx + 1} 音频生成失败：{e}")

                        if st.session_state.audio_urls[idx]:
                            st.audio(st.session_state.audio_urls[idx], format="audio/mp3")

            # 判断是否所有视频和音频均已生成，显示合成按钮
            all_video_ready = all(url is not None for url in st.session_state.video_urls)
            all_audio_ready = all(url is not None for url in st.session_state.audio_urls)
            all_video_ready = True  # test
            all_audio_ready = True  # test

            if all_video_ready and all_audio_ready:
                st.markdown("## 🤩 生成最终短视频")
                if st.button("## 🎬 合成最终视频"):
                    with st.status("🎬 视频合成中，请稍候...", expanded=True) as status:
                        try:
                            # 原始数据
                            video_urls = st.session_state.video_urls
                            audio_urls = st.session_state.audio_urls
                            captions = st.session_state.scene_texts

                            # ✅ 只保留那些视频和音频都已生成的场景
                            # 出于测试目的（在不是5个场景都生成的时候，测试时），只暂时拼接其中几个场景
                            valid_data = [
                                (v, a, c) for v, a, c in zip(video_urls, audio_urls, captions)
                                if v is not None and a is not None
                            ]

                            # 拆分成各自列表
                            video_urls_filtered, audio_urls_filtered, captions_filtered = zip(*valid_data)

                            video_data = merge_videos_and_audios(
                                video_urls_filtered,
                                audio_urls_filtered,
                                captions_filtered
                            )
                            st.success("✅ 合成完成！播放最终视频：")
                            st.video(video_data)
                            status.update(label="✅ 合成完成", state="complete")
                            # 合成视频之后：
                            output_path = "/tmp/final_video.mp4"
                            with open(output_path, "wb") as f:
                                f.write(video_data)
                            st.session_state.final_video_path = output_path
                            history.add_record(output_path, label=f"🎬 {topic} 合成视频下载", is_file=True,
                                               filename="final_video")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 合成失败：{e}")
                            status.update(label="❌ 合成失败", state="error")

if st.session_state.final_video_path:
    # st.markdown("✌️ 合成成功！！最终视频：")
    st.video(st.session_state.final_video_path)
