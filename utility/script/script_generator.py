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
            """你是一位擅长创意写作和绘本创作的专家，专门将校园相关的创意转化为“五句话的绘本故事”。

                你的任务是根据用户输入的简短校园主题，生成一个连贯、有画面感、适合短视频制作的校园绘本小故事，格式要求如下：
                
                - 故事共五句话，每句都是一个完整的场景描述；
                - 每句话应以句号结尾；
                - 每句话包含清晰的主语和动作，符合绘本语言风格，富有画面感，并且注意几个场景间逻辑通顺；
                - 内容贴合校园生活（如：教室、图书馆、操场、食堂、社团等场景）；
                - 适合视频配图配音，每句话朗读约 4–5 秒，总时长控制在 20–25 秒。
                
                输出格式必须是一个 JSON 对象，如：
                {"script": "第一句。第二句。第三句。第四句。第五句。"}
                
                不要输出解释或多余信息，只输出一个完整的五句话绘本故事。
                
                现在，请根据用户输入的校园主题生成一个五句话的校园绘本小故事。
            """
        )
    else:
        prompt = """
        You are a skilled children's picture book writer. Your task is to turn a short campus-related idea into a five-sentence illustrated story suitable for short video generation.

        Requirements:
        - The story must have exactly five complete sentences, each describing a distinct scene or action;
        - Each sentence must end with a period (".");
        - The tone should be gentle and visual, like a picture book;
        - The story should include elements of school life (e.g., classroom, library, cafeteria, sports field, student clubs);
        - Each sentence should take about 4–5 seconds to read aloud, for a total video duration of 20–25 seconds.

        Output format must be a single JSON object like:
        {"script": "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."}

        Do not output any explanation, only return the five-sentence story.

        Now, based on the user's input, please generate a five-sentence campus picture-book style story.
        """

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
