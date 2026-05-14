from ..services.ai_service import AIService
from ..services.prompt_builder import build_prompt


def process_ai_message_task(message_text: str, context_messages: list[str], menu_facts: list[str], model: str, timeout_seconds: int, max_retries: int) -> dict:
    prompt = build_prompt(message_text, context_messages, menu_facts)
    ai_service = AIService(model=model, timeout_seconds=timeout_seconds, max_retries=max_retries)
    return ai_service.generate_reply(prompt)
