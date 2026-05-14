import os
import time

import requests


class AIService:
    def __init__(self, model: str, timeout_seconds: int, max_retries: int):
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def generate_reply(self, prompt: str) -> dict:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {
                "ok": False,
                "error": "GEMINI_API_KEY is not set",
                "fallback": "AI is not configured yet. Please contact support.",
            }

        started = time.time()
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                    headers={
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "system_instruction": {
                            "parts": [
                                {
                                    "text": (
                                        "You are Laurel Cafe assistant. Reply in the same language as the user's latest message. "
                                        "For menu, prices, ingredients, hours, delivery, payment and order status - prioritize provided context facts. "
                                        "For general questions, feedback, or emotional messages, answer naturally and helpfully instead of refusing. "
                                        "If user is disappointed, start with empathy and suggest actionable next steps. "
                                        "Never disclose private/internal data, credentials, staff-only details, or other users' data."
                                    )
                                }
                            ]
                        },
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": prompt}],
                            },
                        ],
                        "generationConfig": {
                            "temperature": 0.3,
                        },
                    },
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                candidates = payload.get("candidates") or []
                if not candidates:
                    raise ValueError("No candidates returned by Gemini API.")
                parts = candidates[0].get("content", {}).get("parts", [])
                content = "\n".join([str(part.get("text", "")).strip() for part in parts if part.get("text")]).strip()
                if not content:
                    raise ValueError("Gemini returned empty content.")
                usage = payload.get("usageMetadata", {})
                latency_ms = int((time.time() - started) * 1000)
                return {
                    "ok": True,
                    "content": content,
                    "model": self.model,
                    "token_in": usage.get("promptTokenCount"),
                    "token_out": usage.get("candidatesTokenCount"),
                    "latency_ms": latency_ms,
                }
            except Exception as exc:
                fallback_text = "Sorry, I cannot answer right now. Please try again in a moment."
                if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 429:
                    fallback_text = "AI is temporarily unavailable due to Gemini API quota/rate limits. Please try again later."
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

    def translate_text(self, text: str, source_lang: str, targets: list[str]) -> dict:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"ok": False, "error": "GEMINI_API_KEY is not set"}

        safe_targets = [code for code in targets if code in {"kk", "ru", "en"}]
        if not safe_targets:
            return {"ok": False, "error": "No supported target languages."}

        prompt = (
            f"Translate text from {source_lang} to target languages: {', '.join(safe_targets)}. "
            "Return strictly JSON object with keys as language codes and translated string values. "
            f"Text: {text}"
        )

        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1},
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            raw = "\n".join([str(part.get("text", "")).strip() for part in parts if part.get("text")]).strip()
            translations = {}
            for code in safe_targets:
                marker = f'"{code}"'
                if marker in raw:
                    # Best-effort JSON parse without adding heavy deps
                    import json

                    try:
                        parsed = json.loads(raw)
                        translations = {k: str(v) for k, v in parsed.items() if k in safe_targets}
                        break
                    except Exception:
                        pass
            if not translations:
                for code in safe_targets:
                    translations[code] = text
            return {"ok": True, "translations": translations}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
