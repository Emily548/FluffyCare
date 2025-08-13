from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    avatar = models.ImageField(upload_to="avatars/", default="avatars/default.png", blank=True)

    def __str__(self):
        return self.username
    
# 定义 7 类情绪
EMOTION_CHOICES = [
    ("happy", "Happy"),
    ("sad", "Sad"),
    ("angry", "Angry"),
    ("surprise", "Surprise"),
    ("fear", "Fear"),
    ("disgust", "Disgust"),
    ("neutral", "Neutral"),
]

class ChatSession(models.Model):
    name = models.CharField(max_length=100, default="新会话")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class ChatLog(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    user_message = models.TextField()
    camera_emotion = models.CharField(max_length=50, choices=EMOTION_CHOICES, default="neutral")
    text_emotion = models.CharField(max_length=50, choices=EMOTION_CHOICES, default="neutral")
    raw_text_emotion = models.CharField(max_length=100, default="neutral")  # ✅ 新增字段
    gpt_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.created_at} | {self.user_message[:20]}..."


class EmotionLog(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    user_message = models.TextField()
    camera_emotion = models.CharField(max_length=50, choices=EMOTION_CHOICES)
    text_emotion = models.CharField(max_length=50, choices=EMOTION_CHOICES)
    raw_text_emotion = models.CharField(max_length=100, default="neutral")  # ✅ 新增字段
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["session", "timestamp"]),
        ]

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.camera_emotion}/{self.text_emotion}"
