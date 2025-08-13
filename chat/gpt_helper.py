import requests
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件

API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ✅ 支持的风格
CHAT_STYLES = {
    "friend": "Reply in a relaxed and friendly tone as a close friend.",
    "psychologist": "As a psychological counselor, offer professional, patient, and warm emotional support.",
    "parent": "As a caring parent, reply with love, warmth, and reassurance.",
    "cartoon": "As a lively and humorous cartoon character, reply with fun and positive energy."
}

def generate_response(user_input, style="friend", history=None):
    """
    根据用户输入和聊天风格生成自然回复，支持上下文和 Few-shot 示例。
    - style: "friend", "psychologist", "parent", "cartoon"
    - history: 上下文消息列表 [{"user": "...", "bot": "..."}]
    """

    # ✅ 风格描述
    style_prompt = CHAT_STYLES.get(style, CHAT_STYLES["friend"])

    # ✅ Few-shot 示例 (覆盖不同风格 + 冲突处理)
    few_shot_examples = [
        # 🌟 Friend 风格
        {"role": "system", "content": "You are a warm and empathetic friend who responds naturally and casually."},
        {"role": "user", "content": "I'm feeling really down today."},
        {"role": "assistant", "content": "Oh no, that sounds rough. Want to share what’s been bothering you? I’m here for you."},
        {"role": "user", "content": "I feel like no one understands me."},
        {"role": "assistant", "content": "I get that, feeling misunderstood can be really lonely. But I’m here, and I do want to understand."},

        # 🌟 Psychological Counselor 风格
        {"role": "system", "content": "You are a professional psychological counselor who listens calmly and supports the user emotionally."},
        {"role": "user", "content": "最近总是觉得焦虑，很压抑。"},
        {"role": "assistant", "content": "谢谢你分享这个感受，这一定不容易。能聊聊让你焦虑的原因吗？"},

        # 🌟 Parent 风格
        {"role": "system", "content": "You are like a caring parent who comforts and encourages."},
        {"role": "user", "content": "我今天心情不好，什么都不想做。"},
        {"role": "assistant", "content": "宝贝，没关系的，偶尔有这样的日子很正常。你愿意告诉我是什么让你这么累吗？"},

        # 🌟 情绪冲突示例
        {"role": "system", "content": "You notice a conflict between facial and text emotion, and respond gently."},
        {"role": "user", "content": "I’m fine, really."},
        {"role": "assistant", "content": "I hear you saying you’re fine, but you seem a bit down. That’s okay—we can talk about anything if you want."}
    ]

    # ✅ 构建消息
    messages = [{"role": "system", "content": f"You are an empathetic assistant. {style_prompt}"}]
    messages += few_shot_examples  # 注入 Few-shot 示例

    # ✅ 添加历史上下文
    if history:
        for msg in history[-6:]:  # 取最近6轮，避免 prompt 太长
            messages.append({"role": "user", "content": msg["user"]})
            messages.append({"role": "assistant", "content": msg["bot"]})

    # ✅ 当前用户输入
    messages.append({"role": "user", "content": user_input})

    print("🔥 调用 GPT，风格:", style)
    print("上下文消息数量:", len(messages))

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-3-8b-instruct",  # ✅ LLaMA-3 模型
                "messages": messages,
                "temperature": 0.85,  # 增加创造性
                "top_p": 0.9
            },
            timeout=30
        )

        print(f"✅ API HTTP 状态码: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        return reply.strip()

    except Exception as e:
        print("❌ OpenRouter API 出错:", e)
        return "Oops, I encountered an error, but I'm still here for you. ❤️"


# ✅ 测试代码
if __name__ == "__main__":
    # 模拟历史上下文
    test_history = [
        {"user": "Hi, I feel a bit sad today.", "bot": "I'm sorry to hear that. Do you want to talk about it?"},
        {"user": "Yes, it's just stressful at work.", "bot": "That sounds tough. How long have you been feeling this way?"}
    ]
    print("🔥 测试回复：")
    print(generate_response("I don't know what to do next.", style="psychologist", history=test_history))
