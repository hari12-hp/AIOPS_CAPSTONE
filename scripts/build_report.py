"""Generate two self-contained A4 LaTeX documents for the built-in editor.

The main report contains design, data, model, evaluation and measured outputs.
The separate documentation contains the user and operator material.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage[a4paper,margin=25mm]{geometry}
\usepackage{microtype}
\usepackage{amsmath,amssymb}
\usepackage{booktabs,longtable,array}
\usepackage{enumitem}
\usepackage{url}
\usepackage[hidelinks]{hyperref}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,calc}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\setlength{\emergencystretch}{2em}
\renewcommand{\arraystretch}{1.2}
\setlist{nosep,leftmargin=*}
\pagestyle{plain}
\raggedbottom
\date{}
\hypersetup{pdfauthor={Hariprasad},pdftitle={AIOps Capstone Project - MathStudio}}
\begin{document}
"""

FLOW = r"""\begin{center}
\begin{tikzpicture}[
 box/.style={draw,rounded corners=2pt,align=center,text width=43.5mm,minimum height=16mm,inner sep=4pt,font=\small},
 flow/.style={-{Latex[length=2mm]},semithick}]
\node[box] (ui) at (0,0) {Nginx frontend\\\footnotesize Solver, pipeline and guide};
\node[box] (api) at (5.3,0) {FastAPI\\\footnotesize Validation and request metrics};
\node[box] (serve) at (10.6,0) {MLflow Models Serve\\\footnotesize Qwen base and LoRA adapter};
\draw[flow] (ui.east)--(api.west);
\draw[flow] (api.east)--(serve.west);
\node[box] (dvc) at (0,-3.2) {DVC pipeline\\\footnotesize Ingest, Spark, train and evaluate};
\node[box] (track) at (5.3,-3.2) {MLflow tracking\\\footnotesize Runs, metrics and artifacts};
\node[box] (registry) at (10.6,-3.2) {Model registry\\\footnotesize Accepted champion alias};
\draw[flow] (dvc.east)--(track.west);
\draw[flow] (track.east)--(registry.west);
\draw[flow] (registry.north)--(serve.south);
\node[box] (prom) at (0,-6.4) {Prometheus\\\footnotesize Metrics, recording and alert rules};
\node[box] (graf) at (5.3,-6.4) {Grafana\\\footnotesize Operations, alerts and ML lifecycle};
\node[box] (probe) at (10.6,-6.4) {Blackbox Exporter\\\footnotesize Eight HTTP readiness checks};
\draw[flow] (prom.east)--(graf.west);
\draw[flow] (probe.north)--++(0,0.6)-|(prom.north);
\node[box] (am) at (2.65,-9.6) {Alertmanager\\\footnotesize Grouping, inhibition and silences};
\node[box] (inbox) at (7.95,-9.6) {Local alert inbox\\\footnotesize Firing and resolved notifications};
\draw[flow] (prom.south)--++(0,-0.7)-|(am.north);
\draw[flow] (am.east)--(inbox.west);
\end{tikzpicture}
\end{center}
"""


def escape(text):
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    text = text.replace("→", " -> ").replace("↗", "").replace("⌘", "Command")
    text = text.replace("–", "--").replace("—", "---").replace("≥", ">=").replace("≤", "<=")
    return "".join(replacements.get(char, char) for char in text)


def inline(text):
    # Tokenize before escaping so Markdown and mathematical answers stay intact.
    pattern = r"(`[^`]+`|\$[^$]+\$|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)|https?://[^\s|]+)"
    parts = re.split(pattern, text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            raw = part[1:-1]
            if re.fullmatch(r"[0-9a-fA-F]{24,}", raw):
                code = r"\allowbreak{}".join(escape(raw[i : i + 8]) for i in range(0, len(raw), 8))
            else:
                code = escape(raw)
            code = (
                code.replace(r"\_", r"\_\allowbreak{}")
                .replace("/", r"/\allowbreak{}")
                .replace(".", r".\allowbreak{}")
                .replace("-", r"-\allowbreak{}")
            )
            out.append(r"\texttt{" + code + "}")
        elif part.startswith("$") and part.endswith("$"):
            out.append(part)
        elif part.startswith("**") and part.endswith("**"):
            out.append(r"\textbf{" + escape(part[2:-2]) + "}")
        elif re.fullmatch(r"\[[^\]]+\]\([^)]+\)", part):
            match = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", part)
            label, target = match.groups()
            label_text = escape(label)
            if re.fullmatch(r"[0-9a-fA-F]{24,}", label):
                label_text = r"\allowbreak{}".join(
                    escape(label[i : i + 8]) for i in range(0, len(label), 8)
                )
            if target.startswith(("http://", "https://")):
                out.append(r"\href{" + target.replace("%", r"\%") + "}{" + label_text + "}")
            else:
                out.append(label_text)
        elif part.startswith(("http://", "https://")):
            out.append(r"\url{" + part + "}")
        else:
            out.append(escape(part))
    return "".join(out)


def markdown(text):
    output = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("!["):
            continue
        if line == "<!-- pagebreak -->":
            output.append(r"\newpage")
        elif line.startswith("```"):
            language = line[3:]
            block = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            if language != "mermaid":
                import textwrap

                wrapped = "\n".join(
                    "\n".join(
                        textwrap.wrap(
                            row, width=75, replace_whitespace=False, drop_whitespace=False
                        )
                        or [""]
                    )
                    for row in block
                )
                output.append(
                    "\\begin{quote}\\small\n\\begin{verbatim}\n"
                    + wrapped
                    + "\n\\end{verbatim}\n\\end{quote}"
                )
        elif line.startswith("|"):
            rows = [line]
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = [
                [c.strip() for c in row.strip("|").split("|")]
                for row in rows
                if not re.fullmatch(r"[\s|:-]+", row)
            ]
            n = max(map(len, cells))
            width = 1 / n
            columns = (
                "@{}"
                + "".join(
                    r">{\raggedright\arraybackslash}p{"
                    + f"{width:.4f}"
                    + r"\dimexpr\textwidth-"
                    + str((n - 1) * 12)
                    + r"pt\relax}"
                    for _ in range(n)
                )
                + "@{}"
            )
            output.extend(
                [r"\begingroup\small", r"\begin{longtable}{" + columns + "}", r"\toprule"]
            )
            for row_index, row in enumerate(cells):
                row += [""] * (n - len(row))
                formatted = [inline(cell) for cell in row]
                if row_index == 0:
                    formatted = [r"\textbf{" + cell + "}" for cell in formatted]
                output.append(" & ".join(formatted) + r" \\")
                if row_index == 0:
                    output.extend(
                        [
                            r"\midrule",
                            r"\endfirsthead",
                            " & ".join(formatted) + r" \\",
                            r"\midrule",
                            r"\endhead",
                        ]
                    )
            output.extend([r"\bottomrule", r"\end{longtable}", r"\endgroup"])
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            command = "section" if level == 1 else "subsection" if level == 2 else "subsubsection"
            output.append("\\" + command + "*{" + inline(line.lstrip("#").strip()) + "}")
        elif re.match(r"^\d+\. ", line) or line.startswith("- "):
            numbered = bool(re.match(r"^\d+\. ", line))
            env = "enumerate" if numbered else "itemize"
            output.append("\\begin{" + env + "}")
            while True:
                item = re.sub(r"^(\d+\. |\- )", "", line)
                output.append(r"\item " + inline(item))
                if i >= len(lines):
                    break
                nxt = lines[i].strip()
                if not (re.match(r"^\d+\. ", nxt) if numbered else nxt.startswith("- ")):
                    break
                line = nxt
                i += 1
            output.append("\\end{" + env + "}")
        else:
            paragraph = [line]
            while (
                i < len(lines)
                and lines[i].strip()
                and not lines[i].lstrip().startswith(("#", "|", "```", "<!--", "- "))
            ):
                paragraph.append(lines[i].strip())
                i += 1
            output.append(inline(" ".join(paragraph)) + "\n")
    return "\n".join(output)


def source(name):
    return (DOCS / name).read_text()


def report_chapters():
    architecture = source("architecture.md")
    high = source("high_level_design.md").split("## Limits and future work")[0]
    high = high.replace(
        "The scope is a CPU demonstration of an AIOps application, with honest boundaries around model quality.",
        "I used a CPU setup so the complete workflow can run on one machine.",
    )
    low = source("low_level_design.md")
    low = low.replace(
        "| Grafana | http://localhost:13000 | Provisioned operations dashboard |",
        """| Grafana | http://localhost:13000 | Service, alert and ML lifecycle dashboards |
| Alertmanager | http://localhost:19093 | Alert routing, grouping and silences |
| Blackbox Exporter | Internal port 9115 | HTTP readiness probes |
| Alert inbox | http://localhost:19199 | Local firing and resolved notification history |""",
    )
    data = source("data_card.md").replace("# Data Card", "# Data")
    model = (
        source("model_card.md")
        .replace("# Model Card", "# Model")
        .replace("described in the data card", "described in the data section")
    )
    model = model.replace(
        "The upstream base model and historical comparison resources retain their own notices",
        "The upstream base model retains its own notices",
    )
    evaluation = source("evaluation_report.md").split("## Historical comparison")[0]
    evaluation = evaluation.replace("## Fresh selected-model experiment", "## Training setup")
    evaluation = evaluation.replace("Fresh Qwen LoRA", "Qwen LoRA")
    evaluation = evaluation.replace("The fresh model achieved", "The model returned")
    evaluation = evaluation.replace(
        "This is deliberately a small functionality test and must not be presented as general mathematics accuracy. Pattern matching can accept an answer containing the expected value; broader exact-answer and reasoning evaluation remains future work.",
        "The score covers these five questions. It is separate from the held-out completion-loss measurement.",
    )
    evaluation = re.sub(
        r"Registry `local-math-assistant-qwen-cpu-v2` version 3 is tagged `accepted`\.",
        "The accepted model is registered as `local-math-assistant-qwen-cpu-v2` and served through the `champion` alias.",
        evaluation,
    )
    evaluation = evaluation.replace("No new Git commit was made.", "")
    results = """# Results and Outputs

I checked the application at the API, pipeline and browser levels. The checks below use the project environment and the running local services. The JUnit output is in `reports/test-results.xml`; the live check reports and screenshots are kept in `reports/evidence/` and `docs/screenshots/`.

| Check | Measured result |
|---|---|
| Unit and contract tests | 58 passed; no failures or skipped cases |
| Application and live inference checks | 10 passed |
| Monitoring checks | 15 passed, including all dashboard queries and real alert delivery |
| Alert-rule scenarios | 9 passed |
| Recording-rule scenarios | 2 passed |
| Browser checks | 9 passed, including input feedback, example questions and mobile layout |
| Selected-model pipeline | All 11 stages completed |
| CPU resource benchmark | 2.109 seconds per microstep; 3.51 GiB process RSS |
| Spark cleaning | 799 of 800 records retained; 75.4 records per second |
| Generation smoke suite | 5 of 5 declared questions passed |
| Running stack | 9 services, 15 scrape targets, 8 HTTP probes and 3 dashboards |
| MLprojects test entry point | Passed in the project environment |

## Application outputs

These are the answers returned through the solver. FastAPI passes each question to MLflow Models Serve, then the browser renders the returned answer.

| Question | Returned answer |
|---|---|
| Solve $2x+3=11$ for $x$. Give only the final value. | $x=4$ |
| What is 7 multiplied by 8? | $56$ |
| What is $3/4+1/8$? Give only the simplified fraction. | $\\frac{7}{8}$ |
| Area of a rectangle with length 9 and width 4. | $36$ |
| What is 15 percent of 200? | $30$ |

The five-question outputs above are saved in the generation report. The separate HTTP checks also returned the correct algebra and fraction answers through Nginx, FastAPI and the model-serving endpoint.

## Verification output

The unit-test command returned:

```text
58 passed
```

The running-service checks returned:

```text
Application checks: 10 passed, 0 failed
Monitoring checks: 15 passed, 0 failed
HTTP readiness: 8 / 8 endpoints ready
Scrape inventory: 15 / 15 targets up
```

The alert-delivery check returned:

```text
PASS: Recent real Watchdog notification delivered
PASS: Controlled alert reached inbox as firing
PASS: Controlled alert reached inbox as resolved
```

The drill enabled a temporary metric, waited for Prometheus to fire the rule, and checked that Alertmanager delivered it to the local inbox. Disabling the metric produced a resolved notification. The application stayed available during the check.

## Integration checks

The API handled empty questions, invalid input, unavailable inference and unexpected errors with the expected response codes. Generated text was rendered safely in the browser. The mobile check used a 390-pixel viewport and found no horizontal overflow.

A pipeline diagnostic deliberately returned an error so failure tracking could be checked. During integration, an MLprojects interpreter mismatch, interrupted evaluation and a list-shaped EDA logging issue were corrected and the checks were rerun. The saved training epoch was reused when evaluation resumed. Formatting checks preserved the training code's syntax tree, and DVC metadata was refreshed without repeating the same computation. Failed runs remain in the experiment history.

The live checks also caught a stale backend address in Nginx after container recreation. The proxy now uses Docker DNS, and the API readiness probe goes through that proxy. The rerun passed both inference questions. Monitoring checks cover the running dashboards, rule evaluation, Watchdog delivery and the firing/resolved route.
"""
    return [architecture, high, low, data, model, evaluation, results]


def clean(text):
    text = text.replace("Math Studio", "MathStudio").replace("web workspace", "solver")
    # The report has no preparation, execution or printed log dates.
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", text)
    return text


def build():
    title = r"""\begin{titlepage}
\begin{center}
{\large Hariprasad}\\[4pt]
{\large Roll Number: DA24B005}\\[20pt]
{\LARGE\bfseries AIOps Capstone Project -- MathStudio}\\[8pt]
{\large Local Mathematics Assistant}\\[18pt]
\end{center}
"""
    summary = r"""The solver sends a question to FastAPI, which calls the registered Qwen model through MLflow Models Serve. The DVC pipeline handles data preparation, training and evaluation. MLflow keeps the runs and model artifacts, while Prometheus, Grafana and Alertmanager track service health and alert delivery.
\end{titlepage}
\setcounter{page}{2}
"""
    report = PREAMBLE + title + FLOW + summary
    report += "\n\\clearpage\n".join(markdown(clean(chapter)) for chapter in report_chapters())
    report += "\n\\end{document}\n"
    (DOCS / "project_report.tex").write_text(report)
    docs_title = r"""\begin{titlepage}\centering
{\large Hariprasad}\\[4pt]
{\large Roll Number: DA24B005}\\[25pt]
{\LARGE\bfseries MathStudio -- Documentation}\\[14pt]
{\large User guide, setup and operations}\\[30pt]
\begin{minipage}{0.85\textwidth}
This document covers using the solver, setting up the project, running the pipeline and monitoring the services. The design, training results and application outputs are in the separate project report.
\end{minipage}
\end{titlepage}
\setcounter{page}{2}
"""
    names = [
        "user_manual.md",
        "monitoring_guide.md",
        "operator_runbook.md",
        "ta_quickstart.md",
        "rubric_evidence.md",
        "recording_guide.md",
        "viva_guide.md",
    ]
    chapters = []
    for name in names:
        text = source(name)
        text = text.replace("data card", "data section").replace("model card", "model section")
        if name == "rubric_evidence.md":
            text = text.replace("It is an evidence checklist, not a promised grade. ", "")
        if name == "recording_guide.md":
            text = text.replace(
                "The video itself is a personal submission deliverable; record your screen and explain the choices in your own words.",
                "Record the workflow and explain each step as you show it.",
            )
        chapters.append(markdown(clean(text)))
    documentation = PREAMBLE + docs_title + "\n\\clearpage\n".join(chapters) + "\n\\end{document}\n"
    documentation = documentation.replace(
        "pdftitle={AIOps Capstone Project - MathStudio}", "pdftitle={MathStudio - Documentation}"
    )
    (DOCS / "documentation.tex").write_text(documentation)
    print("Generated docs/project_report.tex and docs/documentation.tex")


if __name__ == "__main__":
    build()
