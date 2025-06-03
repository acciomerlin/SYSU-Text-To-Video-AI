import os

from langdetect import detect
from openai import OpenAI

if len(os.environ.get("GROQ_API_KEY")) > 30:
    from groq import Groq

    model = "deepseek-r1-distill-llama-70b"
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY")
    )
else:
    OPENAI_API_KEY = os.getenv('OPENAI_KEY')
    model = "gpt-4o"
    client = OpenAI(api_key=OPENAI_API_KEY)


def generate_script(topic, language):
    is_chinese = 0
    if language == 1:
        is_chinese = 1

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
            不要使用剧本格式，不要使用括号或旁白风格的动作描述，不要加上“旁白：”或“（人物说话）”等格式。不要出现台词或人物说话格式。只输出一段自然、优美、仿佛出自小说或说书人之口的连续文字

            例如用户输入：
            - “考试周的崩溃瞬间”
            - “新生开学第一天的迷路事件”
            - “校园猫的一天”
            - “如果老师变成了学生”

            你现在的任务是根据用户的校园创意，输出一个短篇故事。再次强调，不要使用剧本格式，不要使用括号或旁白风格的动作描述，不要加上“旁白：”或“（人物说话）”等格式。不要出现台词或人物说话格式。只输出一段自然、优美、仿佛出自小说或说书人之口的连续文字

            格式：
            只输出一个 JSON 对象，如：
            {"script": "一天清晨..."}
            """
        )
    else:
        prompt = (
            """USE ONLY ENGLISH. You are an expert creative writer and digital content assistant specialized in transforming user ideas about campus life into engaging and imaginative **short stories** (strictly 100 words).

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
        ❗ Strict rules:
        - Do **not** use script format, stage directions, or parenthetical actions (e.g., (she walks in)).
        - Do **not** include any character dialogue in quotation marks or labeled lines.
        - Write it as if it’s told by a storyteller or in a short fiction passage.
        - The result should be a single, fluid, immersive prose paragraph, like in a storybook or novel.
        - 100 words

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
    从原始字符串中提取包含 "script" 字段的 JSON 并返回其值。
    """
    # 使用正则查找第一个 JSON 对象，要求里面包含 "script" 字段
    match = re.search(r'\{[^{}]*"script"\s*:\s*"[^"]*"[^{}]*\}', raw_str, re.DOTALL)

    if not match:
        raise ValueError("未能找到 JSON 格式")

    try:
        data = json.loads(match.group(0))
        return data["script"]
    except Exception as e:
        raise ValueError("解析 JSON 失败") from e
