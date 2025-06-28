import os

from openai import OpenAI


def generate_script(topic, language):
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

    if deepseek_api_key:
        print("使用 DeepSeek]")
        client = OpenAI(
            api_key=deepseek_api_key,
            base_url="https://api.deepseek.com/v1"
        )
        model = "deepseek-chat"
    else:
        print("没找到DeepSeek API key,返回]")
        raise EnvironmentError("未设置 DEEPSEEK_API_KEY 环境变量，请检查 .env 文件或系统环境变量")

    # 根据语言选择 prompt
    if language == 1:  # 中文
        prompt = (
            """你是一位擅长创意写作和短诗创作的专家，专门将用户关于校园生活的创意转化为“五句子押韵打油诗”形式的校园小故事。

                你的目标是根据用户输入的简单校园创意，生成一首内容连贯、有画面感、带有故事性和情绪张力的五句打油诗。诗歌需要符合以下要求：
                - 共五句，每句内容尽量精炼生动
                - 每句结尾押韵（可用 AABBA、AAAAA 或 ABABA 等常见格式）
                - 内容包含角色（如学生、老师、社团成员）、场景（如食堂、图书馆、教室、操场）和简单情节（如误会、巧遇、出糗、突发事件等）
                - 可以是搞笑、感人或反转，适合转化为短视频内容
                
                输出格式必须是一个 JSON 对象，如：
                {"script": "第一句，第二句，第三句，第四句，第五句。"}
                
                不要输出多首，不要输出解释或多余信息。每次只生成一首五句打油诗。
                
                用户输入将是一个校园创意关键词或简短描述，例如：
                - “考试周的精神崩溃”
                - “迎新晚会的乌龙现场”
                - “图书馆偶遇暗恋对象”
                - “老师变成了学生”
                
                现在，请根据用户的输入创作一首五句子押韵的打油诗校园小故事。
            """
        )
    else:
        prompt = (
            """You are an expert in creative writing and poetic storytelling, specializing in transforming users’ campus-life ideas into five-line rhyming limerick-style stories.

            Your goal is to generate a vivid, emotionally engaging, and story-rich five-line poem based on a simple campus-related prompt provided by the user. The poem must meet the following criteria:
            - Exactly five lines, each line concise and vivid
            - Lines should end in rhyming words (using common rhyme schemes like AABBA, AAAAA, or ABABA)
            - Content should include characters (e.g., student, teacher, club member), campus settings (e.g., cafeteria, library, classroom, dorm), and a light narrative arc (e.g., misunderstanding, surprise, mishap, emotional turn)
            - The tone can be humorous, touching, or surprising, suitable for short video adaptation
            - Exactly five lines, each line concise and vivid
            - Exactly five lines, each line concise and vivid
            
            Your output must be a single JSON object, like:
            {"script": "First line.Second line.Third line.Fourth line.Fifth line."}
            
            Do not generate multiple poems. Do not include any explanations or extra text. Only output one five-line rhyming campus story each time.
            
            The user will provide a short prompt such as:
            - "Mental breakdown during finals week"
            - "Freshman orientation mishap"
            - "Crush encounter in the library"
            - "When the teacher became a student"
            
            Now, based on the user’s input, generate one five-line rhyming campus story in the form of a limerick or poetic short tale.
        """
        )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": topic}
        ],

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
