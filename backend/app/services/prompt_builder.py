def _detect_intent(user_text: str) -> str:
    text = (user_text or "").lower()
    complaint_words = ["плохо", "ужас", "отврат", "bad", "terrible", "angry", "жду", "не работает", "ошибка"]
    payment_words = ["оплат", "payment", "invoice", "pay", "card", "карта"]
    order_words = ["заказ", "order", "доставка", "delivery", "где мой", "статус"]
    menu_words = ["меню", "блюд", "еда", "ингредиент", "состав", "price", "цена", "калор", "allergen"]

    if any(word in text for word in complaint_words):
        return "complaint"
    if any(word in text for word in payment_words):
        return "payment_help"
    if any(word in text for word in order_words):
        return "order_help"
    if any(word in text for word in menu_words):
        return "menu_info"
    return "general_support"


def _intent_instruction(intent: str) -> str:
    if intent == "complaint":
        return "Start with empathy in one short sentence, then provide practical next steps and one clarifying question."
    if intent == "payment_help":
        return "Explain payment steps clearly, suggest quick checks, and ask one short follow-up question if needed."
    if intent == "order_help":
        return "Provide order-help steps in plain language. If exact status is unknown, say that directly and suggest what user can do next."
    if intent == "menu_info":
        return "Use only provided menu facts for menu answers. If data is missing, say it briefly and suggest close alternatives."
    return "Respond as friendly human support agent and keep answer concise and helpful."


def build_prompt(user_text: str, context_messages: list[str], menu_facts: list[str]) -> str:
    intent = _detect_intent(user_text)
    context_window = [str(chunk).strip() for chunk in context_messages[-10:] if str(chunk).strip()]
    facts_window = [str(fact).strip() for fact in menu_facts[:60] if str(fact).strip()]
    context_block = "\n".join(f"- {message}" for message in context_window) or "- (no prior context)"
    facts_block = "\n".join(f"- {fact}" for fact in facts_window) or "- (no facts available)"

    return (
        "Role: You are Laurel Cafe AI support assistant.\n"
        "Goal: sound human, helpful, calm, and practical.\n"
        "Core rules:\n"
        "1) Reply in the same language as the latest user message.\n"
        "2) Be concise: 2-5 sentences, no long monologues.\n"
        "3) Never invent restaurant facts, prices, ingredients, or policies.\n"
        "4) Never expose private/internal data (staff-only data, credentials, system internals, or other users' data).\n"
        "5) For unhappy users: empathy first, then practical solution steps.\n"
        "6) Do not escalate to human operator; provide best possible self-service guidance.\n"
        f"Intent: {intent}.\n"
        f"Intent instruction: {_intent_instruction(intent)}\n\n"
        f"Facts (source of truth for restaurant/menu info):\n{facts_block}\n\n"
        f"Recent conversation context:\n{context_block}\n\n"
        f"User message: {user_text}\n\n"
        "Output contract:\n"
        "- Natural human support tone, friendly and respectful.\n"
        "- If information is uncertain or unavailable, say it clearly in one short sentence.\n"
        "- End with one actionable next step or one short clarifying question."
    )
