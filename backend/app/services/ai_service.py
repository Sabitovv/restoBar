import os
import time

import requests


class AIService:
    def __init__(self, model: str, timeout_seconds: int, max_retries: int):
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def generate_reply(self, prompt: str) -> dict:
        api_key = os.getenv("AI_API_KEY")
        if not api_key:
            return {
                "ok": False,
                "error": "AI_API_KEY is not set",
                "fallback": "AI is not configured yet. Please contact support.",
            }

        started = time.time()
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are Laurel Cafe assistant. Answer only about menu, prices, ingredients, hours, delivery, payment and order status. "
                                    "If the question is outside this scope, politely redirect user to menu or support."
                                ),
                            },
                            {
                                "role": "user",
                                "content": prompt,
                            },
                        ],
                        "temperature": 0.3,
                    },
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"].strip()
                usage = payload.get("usage", {})
                latency_ms = int((time.time() - started) * 1000)
                return {
                    "ok": True,
                    "content": content,
                    "model": payload.get("model", self.model),
                    "token_in": usage.get("prompt_tokens"),
                    "token_out": usage.get("completion_tokens"),
                    "latency_ms": latency_ms,
                }
            except Exception as exc:
                fallback_text = "Sorry, I cannot answer right now. Please try again in a moment."
                if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 429:
                    fallback_text = "AI is temporarily unavailable due to API quota/rate limits. Please try again later."
                if attempt >= self.max_retries:
                    return {
                        "ok": False,
                        "error": str(exc),
                        "fallback": fallback_text,
                    }
        return {
            "ok": False,
            "fallback": "Sorry, I cannot answer right now. Please try again in a moment.",
        }
