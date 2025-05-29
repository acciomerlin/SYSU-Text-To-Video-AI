import asyncio
from gtts import gTTS
from langdetect import detect

async def generate_audio(text, outputFilename):
    try:
        await asyncio.to_thread(generate_audio_sync, text, outputFilename)
    except Exception as e:
        print("[TTS错误] gTTS 合成失败：", str(e))
        raise

def generate_audio_sync(text, outputFilename):
    try:
        lang_code = detect(text)  # 自动检测语言
    except:
        lang_code = "zh-TW"  # 默认中文（检测失败时）

    # gTTS 的语言代码转换
    if lang_code.startswith('zh'):
        lang = 'zh-CN'
    elif lang_code.startswith('en'):
        lang = 'en'
    else:
        lang = 'en'  # 默认英文，或根据实际支持情况设定

    print(f"[TTS] 检测语言: {lang_code} -> 使用模型: {lang}")
    tts = gTTS(text, lang=lang)
    tts.save(outputFilename)
