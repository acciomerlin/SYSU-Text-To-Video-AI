import os

from langdetect import detect
from openai import OpenAI
import json

if len(os.environ.get("GROQ_API_KEY")) > 30:
    from groq import Groq
    model = "qwen-qwq-32b"
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY")
        )
else:
    OPENAI_API_KEY = os.getenv('OPENAI_KEY')
    model = "gpt-4o"
    client = OpenAI(api_key=OPENAI_API_KEY)


def generate_script(topic):
    # 自动检测语言
    try:
        lang_code = detect(topic)
    except:
        lang_code = 'en'  # 默认英文

    is_chinese = lang_code.startswith("zh")

    # 根据语言选择 prompt
    if is_chinese:
        prompt = (
            """你是一位擅长创意写作和数字内容创作的专家，专门将用户关于校园生活的想法转化为精彩的短视频短篇小说（约 100 字以内）。

            你的目标是帮助用户生成高质量、吸引人的个性化剧本，这些剧本将用于通过多模态 AI 和 Agent 系统自动生成视频。

            用户会简单描述一个校园场景的创意。你需要将其扩展为完整短篇故事，内容包含：
            - 角色（例如学生、教授、社团成员等）
            - 场景（如教室、图书馆、食堂、宿舍等）
            - 情节结构（开头、转折、高潮、结尾）
            - 如有需要，可加入简单的动作与对话

            短篇故事应具有画面感和情绪张力，适合转换为真实校园视频、动画或风格化画面。可以创意搞笑，也可以温馨感人。

            例如用户输入：
            - “考试周的崩溃瞬间”
            - “新生开学第一天的迷路事件”
            - “校园猫的一天”
            - “如果老师变成了学生”

            你现在的任务是根据用户的校园创意，输出一个短篇故事。

            格式：
            只输出一个 JSON 对象，如：
            {"script": "这是一个精彩又细节丰富的剧本..."}
            """
        )
    else:
        prompt = (
            """USE ONLY ENGLISH. You are an expert creative writer and digital content assistant specialized in transforming user ideas about campus life into engaging and imaginative **short stories** (approximately 100 words).

        Your goal is to help users generate high-quality, personalized short narratives that can be turned into short videos using multimodal AI and agent-based systems.

        The user will briefly describe a creative idea about a campus scenario. You will develop it into a vivid, emotionally engaging short story, including:
        - Characters (e.g., students, professors, club members)
        - Setting (e.g., classroom, dormitory, library, cafeteria)
        - Basic plot structure (intro, twist, climax, and conclusion)
        - Optional light action or dialogue to enhance storytelling

        The story should have visual and emotional appeal, suitable for conversion into video content (live-action, animated, or stylized). It can be humorous, touching, or imaginative.

        Example user prompts:
        - "A breakdown moment during exam week"
        - "A freshman lost on the first day"
        - "A day in the life of a campus cat"
        - "If a professor turned into a student"

        Your task is to generate a compact, engaging short story based on the user's campus idea.

        Format:
        Only return a single valid JSON object with the key "script", for example:
        {"script": "Here is a vivid and emotionally engaging short story..."}
        """
        )

    response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": topic}
            ]
        )
    content = response.choices[0].message.content
    print("[原始输出]:", content)

    script = extract_json_script(content)
    print("[提取脚本]:", script)
    return script

import json
import re

def extract_json_script(raw_str):
    """
    从原始 LLM 返回文本中提取 JSON，转义非法字符，并返回 script 字段。
    """
    try:
        # 尝试直接解析
        return json.loads(raw_str)["script"]
    except json.JSONDecodeError as e:
        # 提取 JSON 结构
        json_match = re.search(r'\{.*\}', raw_str, re.DOTALL)
        if not json_match:
            raise ValueError("未能找到 JSON 格式") from e

        json_str = json_match.group(0)

        # 替换非法字符：裸换行、裸回车、制表符
        json_str_cleaned = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')

        try:
            return json.loads(json_str_cleaned)["script"]
        except Exception as final_e:
            raise ValueError("修复后的 JSON 依旧解析失败") from final_e
