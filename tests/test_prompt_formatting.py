from src.training.prompting import IGNORE_INDEX, completion_labels


class FakeTokenizer:
    eos_token = "<eos>"

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "P>"

    def __call__(self, text, **kwargs):
        return {"input_ids": list(range(len(text)))}


def test_prompt_is_masked_completion_is_trainable():
    row = completion_labels(FakeTokenizer(), [], "answer", 64)
    assert row["labels"][:2] == [IGNORE_INDEX, IGNORE_INDEX]
    assert any(v != IGNORE_INDEX for v in row["labels"][2:])
