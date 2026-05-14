from __future__ import annotations

import requests


class WebSearchService:
    def __init__(self, api_key: str, timeout_seconds: int = 7, max_results: int = 3):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_results = max_results

    def search_facts(self, query: str) -> list[str]:
        response = requests.post(
            "https://api.tavily.com/search",
            headers={"Content-Type": "application/json"},
            json={
                "api_key": self.api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": self.max_results,
                "include_answer": True,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()

        facts: list[str] = []
        answer = str(payload.get("answer") or "").strip()
        if answer:
            facts.append(f"Web answer: {answer}")

        for result in payload.get("results") or []:
            title = str(result.get("title") or "").strip()
            content = str(result.get("content") or "").strip()
            url = str(result.get("url") or "").strip()
            snippet = content[:400]
            if title or snippet:
                facts.append(f"Web source: {title} | {snippet} | {url}")

        return facts[: 1 + self.max_results]


def is_restaurant_intent(message_text: str) -> bool:
    text = message_text.lower()
    keywords = [
        "menu", "меню", "еда", "блюдо", "тағам", "ас", "price", "цена", "баға",
        "ingredient", "ингредиент", "құрамы", "delivery", "доставка", "жеткізу",
        "hours", "время работы", "жұмыс уақыты", "payment", "төлем", "оплата",
        "discount", "скидка", "жеңілдік", "restaurant", "ресторан", "мейрамхана",
    ]
    return any(keyword in text for keyword in keywords)
