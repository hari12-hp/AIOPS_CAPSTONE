# Third-Party Resources

This project uses public model/data resources and open-source software. Preserve each upstream project's applicable license and notices when redistributing its artifacts.

- Base model: [Qwen/Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), pinned to `7ae557604adf67be50417f59c2c2f167def9a775`.
- Historical comparison base: [google/gemma-3-1b-it](https://huggingface.co/google/gemma-3-1b-it), pinned to `dcc83ea841ab6100d6b47a070329e1ba4cf78752`. Historical evidence is retained; the current selected-model rebuild uses public Qwen.
- Dataset: [AI-MO/NuminaMath-1.5](https://huggingface.co/datasets/AI-MO/NuminaMath-1.5), pinned to `1b05109f9e5c1ad06c0663519502416c30b300f8`.
- Equation rendering uses a vendored [KaTeX](https://katex.org/) distribution under `frontend/vendor/katex/`; its original `LICENSE` and exact `VERSION` are preserved for offline operation.
- Runtime dependencies are listed with exact versions in `requirements.lock`; their own distributions contain the applicable notices.
- Container bases and monitoring images are specified in the Dockerfiles and Compose file.

The local artifact bundle contains LoRA adapters and a bounded data snapshot, not the complete upstream base-model weights. Model cards and attribution are technical provenance, not application branding or watermarks.
