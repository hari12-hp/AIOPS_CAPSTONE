IGNORE_INDEX=-100
def completion_labels(tokenizer, messages, completion, max_length):
    """Masks prompt tokens by tokenizing prompt and prompt+assistant completion separately."""
    prompt=tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    full=prompt + completion + (getattr(tokenizer,"eos_token","") or "")
    prompt_ids=tokenizer(prompt, add_special_tokens=False)["input_ids"]
    ids=tokenizer(full, add_special_tokens=False, truncation=True, max_length=max_length)["input_ids"]
    labels=[IGNORE_INDEX]*min(len(prompt_ids),len(ids))+ids[len(prompt_ids):]
    return {"input_ids":ids,"attention_mask":[1]*len(ids),"labels":labels}
