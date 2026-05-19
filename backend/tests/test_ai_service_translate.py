from app.services.ai_service import AIService


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_translate_text_parses_json_inside_markdown_fence(monkeypatch):
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": """```json
{\"kk\": \"Сәлем\", \"en\": \"Hello\"}
```"""
                        }
                    ]
                }
            }
        ]
    }

    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setattr("app.services.ai_service.requests.post", lambda *args, **kwargs: _Response(payload))

    service = AIService(model="gemini", timeout_seconds=5, max_retries=0)
    result = service.translate_text("Привет", "ru", ["kk", "en"])

    assert result["ok"] is True
    assert result["translations"]["kk"] == "Сәлем"
    assert result["translations"]["en"] == "Hello"


def test_translate_text_falls_back_only_missing_keys(monkeypatch):
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"kk": "Сәлем"}'
                        }
                    ]
                }
            }
        ]
    }

    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setattr("app.services.ai_service.requests.post", lambda *args, **kwargs: _Response(payload))

    service = AIService(model="gemini", timeout_seconds=5, max_retries=0)
    result = service.translate_text("Привет", "ru", ["kk", "en"])

    assert result["ok"] is True
    assert result["translations"]["kk"] == "Сәлем"
    assert result["translations"]["en"] == "Привет"
