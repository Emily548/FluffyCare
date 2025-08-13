from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from .forms import RegisterForm, LoginForm

import json, os, requests, cv2
import numpy as np
from PIL import Image
from fer import FER
from langdetect import detect
from .models import ChatSession, ChatLog, EmotionLog
from .gpt_helper import generate_response
from datetime import datetime
from django.utils.timezone import make_aware, is_naive

User = get_user_model()

# ✅ 表情分析器
emotion_detector = FER()
VALID_EMOTIONS = ["happy", "sad", "angry", "surprise", "fear", "disgust", "neutral"]
EMOTION_KEYWORDS = {
    "happy": ["开心", "高兴", "快乐", "幸福", "happy", "joyful", "excited"],
    "sad": ["伤心", "难过", "悲伤", "sad", "unhappy", "depressed"],
    "angry": ["生气", "愤怒", "angry", "mad", "furious"],
    "surprise": ["惊讶", "惊喜", "wow", "omg", "surprised"],
    "fear": ["害怕", "恐惧", "担心", "fear", "afraid", "anxious"],
    "disgust": ["恶心", "讨厌", "厌恶", "disgust", "gross"],
    "neutral": ["嗯", "好", "ok", "normal", "fine"]
}

# ✅ 注册视图
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            if User.objects.filter(username=form.cleaned_data['username']).exists():
                return render(request, 'register.html', {'form': form, 'error': 'Username already exists'})
            User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

# ✅ 登录视图
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = User.objects.get(email=email)
                user = authenticate(request, username=user.username, password=password)
                if user:
                    login(request, user)
                    return redirect('session_list')
            except User.DoesNotExist:
                pass
        return render(request, 'login.html', {'form': form, 'error': 'Invalid email or password'})
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

# ✅ 登出
def logout_view(request):
    logout(request)
    return redirect('login')

# ✅ 辅助函数
def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

def local_emotion_correction(text, gpt_emotion):
    text_lower = text.lower()
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(word in text or word in text_lower for word in keywords):
            return emotion
    return gpt_emotion

def analyze_text_emotion(text):
    try:
        prompt = f"""请判断用户话语属于以下情绪之一：
["happy", "sad", "angry", "surprise", "fear", "disgust", "neutral"]。
输出 JSON：{{"emotion":"<emotion>","reason":"<简要原因>"}}。
用户输入: "{text}" """

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-3-8b-instruct",
                "messages": [
                    {"role": "system", "content": "你是情绪分析助手，严格输出 JSON"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }
        )
        result = response.json()
        data = json.loads(result["choices"][0]["message"]["content"])
        gpt_emotion = data.get("emotion", "neutral").lower()
        reason = data.get("reason", "未提供原因")
        return gpt_emotion if gpt_emotion in VALID_EMOTIONS else "neutral", reason
    except:
        return "neutral", "分析失败"

# ✅ 会话主页（改为固定三只动物）
@login_required(login_url='/login/')
def session_list_view(request):
    sessions = [
        {"id": 1, "name": "Lulu Pig", "animal": "pig", "image": "animals/pig.jpg"},
        {"id": 2, "name": "Bubble Puppy", "animal": "dog", "image": "animals/dog.jpg"},
        {"id": 3, "name": "Fluffy Bunny", "animal": "rabbit", "image": "animals/rabbit.jpg"},
    ]
    return render(request, "session_list.html", {"sessions": sessions})

# ✅ 聊天界面（增加 animal 传递）
@login_required(login_url='/login/')
def chat_view(request, session_id):
    animals = {
        1: {"name": "Lulu Pig", "animal": "pig"},
        2: {"name": "Bubble Puppy", "animal": "dog"},
        3: {"name": "Fluffy Bunny", "animal": "rabbit"},
    }
    if session_id not in animals:
        return render(request, "404.html", status=404)

    session_info = animals[session_id]
    # logs 依然取数据库里的聊天记录
    logs = ChatLog.objects.filter(session_id=session_id).order_by("created_at")
    return render(request, "chat.html", {
        "session": {
            "id": session_id,
            "name": session_info["name"],
            "animal": session_info["animal"]
        },
        "logs": logs
    })


# ✅ 聊天逻辑
@csrf_exempt
def chat_api(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    data = json.loads(request.body)
    user_input = data.get("message", "").strip()
    style = data.get("style", "friend")
    camera_emotion = data.get("emotion", "neutral").strip().lower()
    camera_emotion = camera_emotion if camera_emotion in VALID_EMOTIONS else "neutral"

    language = detect_language(user_input)
    gpt_emotion, reason = analyze_text_emotion(user_input)
    final_emotion = local_emotion_correction(user_input, gpt_emotion)

    history = [{"user": log.user_message, "bot": log.gpt_response}
               for log in ChatLog.objects.filter(session=session).order_by("-created_at")[:10][::-1]]

    response_text = generate_response(user_input, style, history)

    # ✅ 修复 5 分钟内不重复询问的问题
    now = timezone.now()
    last_care_time_str = request.session.get("last_care_time")
    last_care_time = None
    if last_care_time_str:
        try:
            parsed_time = datetime.fromisoformat(last_care_time_str)
            last_care_time = make_aware(parsed_time) if is_naive(parsed_time) else parsed_time
        except ValueError:
            last_care_time = None  # 忽略错误格式

    should_show_care = (
        camera_emotion in {"sad", "angry", "fear", "disgust"} or
        final_emotion in {"sad", "angry", "fear", "disgust"}
    )

    if should_show_care and (not last_care_time or (now - last_care_time).total_seconds() > 300):
        care_msg = "你还好吗？想聊聊嘛？" if language.startswith("zh") else "Are you okay? Want to talk?"
        response_text = care_msg + "\n\n" + response_text
        request.session["last_care_time"] = now.isoformat()
        request.session.modified = True

    # ✅ 记录日志
    ChatLog.objects.create(session=session, user_message=user_input,
                           camera_emotion=camera_emotion, text_emotion=final_emotion,
                           gpt_response=response_text)
    EmotionLog.objects.create(session=session, user_message=user_input,
                              camera_emotion=camera_emotion, text_emotion=final_emotion)

    return JsonResponse({
        "response": response_text,
        "camera_emotion": camera_emotion,
        "text_emotion": final_emotion,
        "reason": reason,
        "language": language
    })


# ✅ 摄像头情绪识别
from django.utils import timezone  # 确保这行在文件开头已导入

@csrf_exempt
def detect_emotion(request):
    if request.method == 'POST':
        image_file = request.FILES.get('frame')
        try:
            img = Image.open(image_file)
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            result = emotion_detector.detect_emotions(img_cv)
            emotion = max(result[0]['emotions'], key=result[0]['emotions'].get) if result else 'neutral'
        except:
            emotion = 'neutral'

        # 负面情绪检测逻辑
        negative_emotions = {"sad", "angry", "fear", "disgust"}
        alert = False

        if emotion in negative_emotions:
            count = request.session.get("negative_count", 0) + 1
            request.session["negative_count"] = count
        else:
            request.session["negative_count"] = 0

        # ✅ 添加：3分钟内不重复提醒
        if request.session["negative_count"] >= 3:
            now = timezone.now()
            last_alert_time_str = request.session.get("last_alert_time")
            last_alert_time = timezone.datetime.fromisoformat(last_alert_time_str) if last_alert_time_str else None

            if not last_alert_time or (now - last_alert_time).total_seconds() > 180:
                alert = True
                request.session["last_alert_time"] = now.isoformat()
            request.session["negative_count"] = 0  # 重置计数（无论是否弹窗）

        return JsonResponse({
            'emotion': emotion,
            'alert': alert,
            'alert_message': "You don't seem okay. Want to talk?" if alert else ""
        })


# ✅ 情绪趋势图（🚧改为返回JSON数据用于前端绘图）
@login_required(login_url='/login/')
def trend_view(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    logs = EmotionLog.objects.filter(session=session).order_by("timestamp")

    trend_data = [
        {
            "timestamp": timezone.localtime(log.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "camera_emotion": log.camera_emotion,
            "text_emotion": log.text_emotion,
        }
        for log in logs
    ]

    return JsonResponse(trend_data, safe=False)
import statistics
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ChatSession, EmotionLog

def analyze_emotion_suggestions(camera_emotions):
    emotion_scores = {
        "happy": 1,
        "neutral": 2,
        "surprise": 3,
        "fear": 4,
        "disgust": 4,
        "sad": 5,
        "angry": 5
    }
    scores = [emotion_scores.get(e, 2) for e in camera_emotions if e in emotion_scores]
    if not scores:
        return "C", "We couldn't gather enough emotion data. Try using the system longer."

    avg = sum(scores) / len(scores)
    std_dev = statistics.stdev(scores) if len(scores) > 1 else 0

    if avg < 1.6:
        level = "A"
    elif avg < 2.5:
        level = "B"
    elif avg < 3.5:
        level = "C"
    elif avg < 4.5:
        level = "D"
    else:
        level = "E"

    # ✅ 仅给出温柔建议，不评判状态
    suggestion_table = {
        "A": [
            "🌟 Keep shining! Enjoy a good meal today, and don’t forget to share a smile with someone.",
            "☀️ You're glowing! Stretch a little, sip your favorite drink, and keep the cozy vibes going."
        ],
        "B": [
            "🌼 A short walk, some fresh air, and warm food might make your day even better.",
            "🧸 Try calling a friend or listening to a cheerful tune. Little joys go a long way!"
        ],
        "C": [
            "🍵 Slow down a bit. A calm evening and some gentle stretches might feel nice.",
            "🌙 Rest well tonight. Your favorite snack and soft music can work wonders."
        ],
        "D": [
            "🎧 Take a deep breath and play a song that brings comfort. You deserve soft things.",
            "🫖 Drink something warm, get some sunlight, and let yourself rest gently today."
        ],
        "E": [
            "🌈 Be kind to yourself today. A nap, a small walk, or hugging a pillow might feel nice.",
            "💖 Everything doesn’t need to be perfect. Just eat something warm and take things slowly."
        ]
    }

    suggestion = suggestion_table[level][1 if std_dev >= 0.8 else 0]
    return level, suggestion


@login_required(login_url='/login/')
def trend_page_view(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    logs = EmotionLog.objects.filter(session=session).order_by("timestamp")
    camera_emotions = [log.camera_emotion for log in logs]
    level, suggestion = analyze_emotion_suggestions(camera_emotions)

    return render(request, 'trend.html', {
        'session_id': session_id,
        'emotion_level': level,
        'suggestion': suggestion
    })
