import re
from whisper_timestamped import load_model, transcribe_timestamped
from opencc import OpenCC
cc = OpenCC('t2s')  # 繁体转简体


def generate_timed_captions(audio_filename, script, model_size="base", language=0):
    whisper_model = load_model(model_size)

    # 将语言从 int 映射为 str
    lang_map     = {0: 'en', 1: 'zh'}
    language_str = lang_map.get(language, 'en')  # 默认英文

    gen = transcribe_timestamped(
        whisper_model,
        audio_filename,
        verbose=False,
        fp16=False,
        language=language_str  # ✅ 显式设定语言
    )

    if language == 0:
        return get_captions_with_time(gen, script, language)
    else:
        return get_captions_by_pauses(gen)

def get_captions_with_time(whisper_analysis, script, language):
    word_time_map = get_timestamp_mapping(whisper_analysis)
    captions      = split_script_into_captions(script, language)

    caption_pairs = []
    position      = 0
    start_time    = 0
    text          = whisper_analysis['text']

    for caption in captions:
        # 跳过空白字符
        while position < len(text) and text[position].isspace():
            position += 1

        end_pos  = position + len(caption)
        end_time = interpolate_time_from_dict(end_pos, word_time_map)

        if end_time:
            caption_pairs.append(((start_time, end_time), caption.strip()))
            start_time = end_time

        position = end_pos

    return caption_pairs

def get_captions_by_pauses(whisper_analysis, pause_threshold=0.4):
    segments = get_timestamp_segments_by_pause(whisper_analysis, pause_threshold)
    caption_pairs = [((start, end), text) for (start, end), text in segments]
    return caption_pairs

def split_script_into_captions(script: str, language: int = 0) -> list:
    """
    根据语言将剧本文本切分为字幕句段。
    - 中文使用顿号、逗号、句号作为切分点
    - 英文使用逗号、句号作为切分点
    返回每段字幕组成的字符串列表
    """
    captions = []
    if language == 1:
        # 中文切分：使用中文逗号、句号、顿号作为断句点
        segments = re.split(r'(，|。|、)', script)
        buffer   = ""
        for seg in segments:
            if seg in ['，', '。', '、']:
                buffer += seg
                captions.append(buffer.strip())
                buffer = ""
            else:
                buffer += seg
    else:
        # 英文切分：使用逗号和句号作为断句点
        segments = re.split(r'([,.])', script)
        buffer   = ""
        for seg in segments:
            if seg in [',', '.']:
                buffer += seg
                captions.append(buffer.strip())
                buffer = ""
            else:
                buffer += seg

    if buffer.strip():  # 收尾
        captions.append(buffer.strip())

    return [cap for cap in captions if cap]


def get_timestamp_mapping(whisper_analysis):
    index               = 0
    location_to_time    = {}
    for segment in whisper_analysis['segments']:
        for word in segment['words']:
            new_index = index + len(word['text']) + 1  # 加空格
            location_to_time[(index, new_index)] = word['end']
            index = new_index
    return location_to_time


def interpolate_time_from_dict(word_pos, time_dict):
    for (start, end), ts in time_dict.items():
        if start <= word_pos <= end:
            return ts
    return None

def get_timestamp_segments_by_pause(whisper_analysis, pause_threshold=0.4):
    words = [w for seg in whisper_analysis['segments'] for w in seg['words']]

    segments = []
    current_segment = []

    for i in range(len(words)):
        current_segment.append(words[i])

        # 判断是否到了停顿
        if i + 1 < len(words):
            gap = words[i + 1]['start'] - words[i]['end']
            if gap >= pause_threshold:
                segments.append(current_segment)
                current_segment = []

    # 处理最后一段
    if current_segment:
        segments.append(current_segment)

    # 构建时间段列表
    time_segments = []
    for segment in segments:
        start = segment[0]['start']
        end = segment[-1]['end']
        text = ''.join([w['text'] for w in segment])
        text = cc.convert(text)
        time_segments.append(((start, end), text.strip()))

    return time_segments





