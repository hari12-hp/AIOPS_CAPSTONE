from src.data.common import normalise_question, record_id
from src.data.split_dataset import bucket
def test_normalisation_and_deterministic_bucket():
    assert normalise_question("  X\n +  Y ") == "x + y"
    assert bucket("x + y",42)==bucket("x + y",42)
def test_record_id_is_stable(): assert record_id({"problem":"x","solution":"y"})==record_id({"problem":" x ","solution":"y"})
