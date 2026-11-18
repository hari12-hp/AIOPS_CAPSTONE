# Submission Checklist

## Local project deliverables

- [x] Independent responsive frontend with examples, input/error feedback, progress, solution and guide.
- [x] Separate pipeline console with stage states, durations, logs, quality/evaluation evidence and local tool links.
- [x] Architecture diagram and block explanation: `docs/architecture.svg`, `docs/architecture.md`.
- [x] High-level design and rationale: `docs/high_level_design.md`.
- [x] Low-level design and API I/O/error contracts: `docs/low_level_design.md`.
- [x] Test plan, cases, acceptance criteria and measured report: `docs/test_plan.md`, `docs/test_report.md`.
- [x] Nontechnical user manual and in-app guide: `docs/user_manual.md`, `frontend/help.html`.
- [x] Operator runbook, recording sequence and viva preparation.
- [x] A4 LaTeX report, separate documentation PDF, editable sources and rubric evidence map.
- [x] Reproducible pinned data/model identities, DVC graph/lock, local artifact remote and tracked model/evaluation outputs.
- [x] MLflow nested stage/training runs, explicit metrics/artifacts/lineage, executable registry model and acceptance-bound champion decision.
- [x] FastAPI → real MLflow Models Serve inference boundary.
- [x] Prometheus API/pipeline/model/process instrumentation, three Grafana dashboards, HTTP probes, tested alert/recording rules, persistent Alertmanager/inbox, delivery drill and recovery runbook.
- [x] Independent Docker images and nine-service Compose deployment with local ports.
- [x] Automated tests, MLprojects test command, live service verification and browser evidence.
- [x] Local CI/evaluation scripts and a GitHub workflow definition ready for a future owner push.
- [x] TA workflow orchestration and a fresh-checkout bootstrap script with pinned Hugging Face download links, logs and failure reporting; `docs/ta_quickstart.md`.
- [x] Source remains local; no GitHub commit/push or cloud deployment performed.

## Final handoff checks

The measured reports and `reports/evidence/` contain the actual outcomes. `output/submission/math-studio-submission.zip` is produced only after final runtime verification and local artifact synchronization. Its manifest and checksum support transfer and review. The archive excludes secrets, machine caches, virtual environments, databases and unrelated agent configuration.

## Presenter-owned submission items

- [ ] Record and submit your screen video using `docs/recording_guide.md`.
- [ ] Review the project and your Assignments 1-10 for the viva.
- [ ] Add your name/student identifiers if your institution requires them.
- [ ] Review the local changes and commit/push to your own GitHub repository when ready.

The repository supports all technical rubric categories. The evaluator assigns marks; viva performance and the personal recording cannot be guaranteed by repository checks. The five-case model smoke score must be presented with its sample size and limitations.
