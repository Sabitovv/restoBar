def build_prompt(user_text: str, context_messages: list[str], menu_facts: list[str]) -> str:
    context_block = "\n".join(context_messages[-8:])
    facts_block = "\n".join(menu_facts[:30])
    return (
        "You are Laurel Cafe assistant. Answer only about menu, prices, ingredients, hours, delivery and payment. "
        "If user asks outside scope, suggest contacting operator.\n\n"
        f"Facts:\n{facts_block}\n\n"
        f"Conversation:\n{context_block}\n\n"
        f"User message: {user_text}\n"
        "Return concise answer."
    )
