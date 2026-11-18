from src.training.generation_contract import SYSTEM_PROMPT, decode_answer


class Tokenizer:
    eos_token_id = 0

    def decode(self, tokens, skip_special_tokens=True):
        return "x = 4"


def test_generation_protocol_respects_requested_format():
    assert (
        SYSTEM_PROMPT
        == "Solve the mathematics problem. Follow the requested answer format exactly."
    )


def test_length_limit_is_visible_without_warning_on_a_finished_response():
    tokenizer = Tokenizer()
    assert decode_answer(tokenizer, [1, 0], 2) == "x = 4"
    assert "length limit" in decode_answer(tokenizer, [1, 2], 2)
