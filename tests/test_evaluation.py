import json
from pathlib import Path
from src.training.model_metadata import git_metadata
def test_git_metadata_is_explicit_when_git_unavailable():
    metadata=git_metadata(".")
    assert set(metadata)=={"git_commit","git_dirty"}
