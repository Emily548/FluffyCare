window.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("user-input");
    const emotion = document.getElementById("emotion");
    const chatBox = document.getElementById("chat-box");
    const moodDisplay = document.getElementById("mood-display");
  
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
  
      const userText = input.value.trim();
      const userEmotion = emotion.value;
  
      if (!userText) return;
  
      chatBox.innerHTML += `<div class="msg user">你：${userText}</div>`;
      input.value = "";
  
      const moodMap = {
        happy: "😊 高兴",
        sad: "😔 难过",
        angry: "😠 生气",
        neutral: "😐 中性"
      };
      moodDisplay.textContent = `当前情绪：${moodMap[userEmotion]}`;
  
      const response = await fetch("/api/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText, emotion: userEmotion })
      });
  
      const data = await response.json();
      chatBox.innerHTML += `<div class="msg bot">助手：${data.response}</div>`;
      chatBox.scrollTop = chatBox.scrollHeight;
    });
  });
  