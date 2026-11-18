#!/usr/bin/env bash
# Export the editable A4 LaTeX sources without a host TeX installation.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
report_python="${REPORT_PYTHON_BIN:-python3}"
"$report_python" -c 'import pypdf' || {
  echo 'Install requirements-report.txt in the selected REPORT_PYTHON_BIN environment.' >&2
  exit 1
}
report_image='texlive/texlive@sha256:c572bf2d14631545769e5a8f8d315e7b8f8896b14720b1c7a063917d503fd46a'
mkdir -p output/latex
# Compilation has no network access and reads only the document sources.
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -v "$PWD/docs:/sources:ro" -v "$PWD/output/latex:/output" -w /sources \
  "$report_image" sh -c '
    for document in project_report documentation; do
      for pass in 1 2; do
        pdflatex -interaction=nonstopmode -halt-on-error -file-line-error \
          -output-directory=/output "$document.tex"
      done
    done
  ' > output/latex/build.log 2>&1
"$report_python" - <<'PY'
from pathlib import Path
from pypdf import PdfReader, PdfWriter

# Preserve the exact filename requested for the separate documentation PDF.
for source, destination, title in [
    ('project_report', 'project_report', 'AIOps Capstone Project - MathStudio'),
    ('documentation', 'documenttion', 'MathStudio - Documentation'),
]:
    reader = PdfReader(Path('output/latex') / f'{source}.pdf')
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer._info.get_object().clear()
    writer._root_object.pop('/Metadata', None)
    writer.add_metadata({'/Title': title, '/Author': 'Hariprasad',
                         '/Creator': 'LaTeX', '/Producer': 'pdfTeX'})
    path = Path('docs') / f'{destination}.pdf'
    with path.open('wb') as stream:
        writer.write(stream)
    output = PdfReader(path)
    assert '/CreationDate' not in output.metadata and '/ModDate' not in output.metadata
    assert all(abs(float(p.mediabox.width) - 595.276) < 1 and
               abs(float(p.mediabox.height) - 841.890) < 1 for p in output.pages)
    print(f'{path}: {len(output.pages)} A4 pages')
PY
