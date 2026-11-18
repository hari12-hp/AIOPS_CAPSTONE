"""Shared instruction and completion handling for serving and acceptance checks."""

SYSTEM_PROMPT = "Solve the mathematics problem. Follow the requested answer format exactly."


def decode_answer(tokenizer, completion, limit):
    answer = tokenizer.decode(completion, skip_special_tokens=True).strip()
    if len(completion) >= limit and completion[-1] != tokenizer.eos_token_id:
        answer += "\n\nThis response reached the length limit. Try a more focused question."
    return answer
