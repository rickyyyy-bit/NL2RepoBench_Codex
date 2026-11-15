# NL2RepoBench — standalone Codex runner

A self-contained runner for NL2RepoBench tasks, with Codex generation and an agent-independent evaluator. All required benchmark Python modules and task metadata are included. No other agent package, repository checkout, or service is required.

This is a complete repository, not a patch to another checkout. Use this directory as the GitHub repository root.

## Setup and run

Use Linux or Ubuntu/WSL, Python 3.12, Docker and Docker Buildx. Native Windows Python execution is not supported. The task evaluation images are downloaded from the NL2RepoBench container registry; they are benchmark assets, not agent runtimes. Image builds and task installation commands may require network access.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
docker info
docker buildx version
bash scripts/build_codex.sh
cp config.codex.example.json config.codex.json
```

Edit `config.codex.json` with the model ID, API base URL and task names. Supply a Responses-compatible provider and model supporting your configured reasoning effort.

```bash
read -r -s -p 'Provider API key: ' NL2REPO_API_KEY
printf '\n'
export NL2REPO_API_KEY
python main.py --config config.codex.json
unset NL2REPO_API_KEY
```

This performs generation and grading. Add `--skip-evaluation` for generation only. Each task has a separate workspace and temporary agent home. API keys are passed by environment-variable name and known key values are redacted from retained CLI logs.

## Evaluate saved code from any agent

Select exactly one model/task in the configuration, then run:

```bash
python main.py --config config.codex.json \
  --saved-submission /absolute/path/to/repository \
  --submission-agent agent-under-study
```

Replay requires no API key or generation image and imports no agent adapter. It copies the saved code before grading; original files remain unchanged. The agent label and configured model are reported provenance, not independently verified generation settings. An omitted agent label becomes `external`. Replay always evaluates and cannot be combined with `--skip-evaluation`.

## Repository structure

| Path | Purpose |
|---|---|
| `benchmark/` | Agent-independent evaluator, Docker helpers and fixed task prompt |
| `codex_backend/` | Codex generation, container lifecycle and diagnostics |
| `runner.py`, `main.py` | Scheduling, result recording, generation and replay entry points |
| `test_files/` | Bundled benchmark instructions, commands and test metadata |
| `docker/`, `scripts/` | Generation image and build command |
| `tests/` | Offline regression tests and optional request probe |

Results are written to `result/`; generated and evaluated copies are under separate directories in `workspaces/`. A completed run means its pipeline completed, not that all tests passed. Inspect installation exit codes and evaluation diagnostics alongside the passed-test count.

See [configuration and manual testing](docs/codex.md), [experiment protocol and limitations](docs/experiment-protocol.md), and [verification](docs/validation.md). Benchmark provenance and file fingerprints are recorded in [the protocol manifest](docs/protocol-manifest.json).
