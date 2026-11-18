"""Create a portable source + DVC-object archive without secrets or machine state."""

from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main():
    output = ROOT / "output/submission"
    output.mkdir(parents=True, exist_ok=True)
    if not (ROOT / ".dvc/cache-store").exists():
        raise SystemExit("Run .venv/bin/dvc push to create the local artifact store first")
    selected = []
    # Explicit allowlist: avoids accidentally including .aws, .env, tokens or venvs.
    for folder in [
        "src",
        "tests",
        "configs",
        "scripts",
        "docs",
        "frontend",
        "monitoring",
        ".github",
    ]:
        selected.extend(
            p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts
        )
    for folder in ["artifacts", "models", "reports/evaluation"]:
        selected.extend((ROOT / folder).rglob("*.dvc"))
    selected.extend(p for p in (ROOT / "reports/evidence").rglob("*") if p.is_file())
    selected.extend(p for p in (ROOT / ".dvc/cache-store").rglob("*") if p.is_file())
    for name in [
        "README.md",
        "SUBMISSION_CHECKLIST.md",
        "THIRD_PARTY_NOTICES.md",
        "requirements.lock",
        "requirements-test.txt",
        "requirements-report.txt",
        "params.yaml",
        "dvc.yaml",
        "dvc.lock",
        "MLproject",
        "python_env.yaml",
        "pyproject.toml",
        "docker-compose.yml",
        "Dockerfile.backend",
        "Dockerfile.frontend",
        ".dockerignore",
        ".env.example",
        ".gitignore",
        ".dvc/config",
        ".dvc/.gitignore",
        ".dvcignore",
        "reports/test-results.xml",
    ]:
        path = ROOT / name
        if path.is_file():
            selected.append(path)
    selected = sorted(set(selected))
    manifest = {
        "source_git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_included": True,
        "files": {str(p.relative_to(ROOT)): digest(p) for p in selected},
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    destination = output / "math-studio-submission.zip"
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5
    ) as archive:
        for path in selected:
            archive.write(path, arcname="capstone/" + str(path.relative_to(ROOT)))
        archive.write(manifest_path, arcname="capstone/SUBMISSION_MANIFEST.json")
    checksum = digest(destination)
    (output / "SHA256SUMS").write_text(f"{checksum}  {destination.name}\n")
    print(
        json.dumps(
            {
                "archive": str(destination),
                "files": len(selected),
                "bytes": destination.stat().st_size,
                "sha256": checksum,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
