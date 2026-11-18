# Evaluation Rubric Evidence Map

This maps the supplied evaluation rubric to concrete repository files and demonstration evidence. It is an evidence checklist, not a promised grade. The technical categories total 20 points; the viva contributes a further 5 points through the presenter's own explanations.

| Rubric category | Points | Implementation and evidence |
|---|---:|---|
| Web frontend UI/UX | 3 | Independent responsive workspace, example questions, keyboard shortcut, input validation, progress/error feedback, safe answer rendering, copy action and in-app guide. `frontend/`, `docs/user_manual.md`, screenshots and browser test results. |
| ML pipeline visualization | 2 | Separate `pipeline.html` console with eleven stages, data counts, durations, statuses, run links, log tail and operations tool links. `GET /v1/pipeline/status`, `/v1/pipeline/logs`, MLflow parent/child runs and DVC DAG. |
| Design principles | 2 | Architecture SVG/Mermaid and block explanation; HLD rationale/tradeoffs; LLD endpoint inputs/outputs/errors. Frontend → configurable REST → FastAPI → separate MLflow inference. |
| Implementation | 2 | Typed models/configuration, narrow model-service object, functions for pipelines, exception boundaries, bounded logging labels, source documentation and automated tests. |
| Testing | 1 | `docs/test_plan.md`, test case inventory and acceptance criteria; `docs/test_report.md`; `reports/test-results.xml`; live runtime verification and browser checks. |
| Data engineering | 2 | Pinned bounded Parquet ingestion, local PySpark cleaning/normalization/deduplication, deterministic split with counts/hashes, EDA and measured throughput. `src/data/`, DVC stages and quality report. |
| Source control and CI | 2 | Existing Git repository; DVC DAG, dependency tracking, lock file and local artifact remote. Reproducible runner and evaluation script perform the local integration/gating sequence. Source/model/data/config identities are preserved. No remote CI run or GitHub upload is claimed. |
| Experiment tracking | 2 | MLflow parent/stage runs; trainer step loss; timings, source snapshot, environment freeze, Git dirty identity, output hashes and explicit metrics/artifacts beyond autologging; verified model versions and alias. |
| Exporter instrumentation and visualization | 2 | API, data pipeline, model exporter and process metrics; Prometheus scrapes; provisioned Grafana datasource/dashboard; seventeen alert rules, six recording rules, eight HTTP probes, Alertmanager, a persistent local inbox and a verified firing/resolved drill. Runtime checks record target health and generated metrics. |
| Software packaging | 2 | Real MLflow Models Serve `/invocations`, MLproject/python environment, FastAPI contract, independent backend/frontend images, nine-service Docker Compose and successful live HTTP boundary checks. |
| Viva | 5 | `docs/viva_guide.md` supports the project/tools/design discussion. The presenter must demonstrate their own understanding and review Assignments 1-10. Those personal viva outcomes cannot be verified by repository automation. |

## Mandatory document locations

1. Architecture diagram and block explanation: `docs/architecture.svg`, `docs/architecture.md`.
2. High-level design with rationale: `docs/high_level_design.md`.
3. Low-level design and API I/O: `docs/low_level_design.md`, live OpenAPI.
4. Test plan/cases: `docs/test_plan.md`; measured report: `docs/test_report.md`.
5. Nontechnical user manual: `docs/user_manual.md`, `frontend/help.html`.

`docs/project_report.pdf` consolidates the documents for review. `docs/recording_guide.md` supplies a suggested video sequence. The local submission ZIP includes code, required documents, reports, artifact objects, a file manifest and archive checksum.

## Evidence boundaries

Historical Gemma comparisons remain identifiable as earlier experiments. The fresh selected-model run uses Qwen. The generation smoke score is limited to five declared questions. Source is intentionally left uncommitted for the owner to review and commit; runs record the existing commit plus dirty state and preserve source snapshots. Artifact restoration is supported by the archive, while a source-only future GitHub clone requires the separate artifact bundle or a full rebuild.
