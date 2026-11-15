# Codex backend

Codex CLI is a third backend alongside OpenHands and DeepSeek Harness. It uses the existing batch scheduler and benchmark evaluator. Existing configurations still default to OpenHands. This backend supports Linux and Ubuntu/WSL with Docker; native Windows Python execution is not supported.

## Setup

From a checkout, with Python 3.10+ (including venv support), Docker and its Buildx plugin installed:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
docker info >/dev/null
docker buildx version
bash scripts/build_codex.sh
cp config.codex.example.json config.codex.json
```

The build script creates `nl2repobench-codex:0.167.2`, containing Codex CLI 0.167.2, Python 3.12 and Node 22. It leaves an existing image tag unchanged. Dependencies are downloaded during a new image build. The build context is restricted to `docker/`, rather than the checkout's run artifacts or local configuration files.

On Windows, open an Ubuntu terminal using `wsl -d Ubuntu`, change to your checkout under `/mnt/c/...`, and run these Bash commands there. Ensure that Docker is available inside that WSL distribution.

## Configure and run a model

Edit `config.codex.json`:

| Field | Meaning |
|---|---|
| `moduleName` | Exact model identifier accepted by your provider |
| `protocol` | `openai-responses` only |
| `baseUrl` | Provider's API base URL, or leave empty and set `NL2REPO_BASE_URL` |
| `apiKeyEnv` | Key variable name; defaults to `NL2REPO_API_KEY` |
| `reasoningEffort` | Optional supported reasoning effort, forwarded explicitly |
| `contextWindow` | Optional positive context-capacity setting |
| `proNameList` | Task names under `test_files/` |

The top-level `codex` object accepts `image` and `task_timeout_seconds` (default 7200). `max_pool_size` defaults to 1. The example evaluates after generation; `--skip-evaluation` overrides this. The provider must support the selected model and settings. There is no model or transport fallback. `maxTokens`, `compat` and `reasoningEfforts` are rejected by this adapter rather than silently ignored.

Enter a key without echoing it or placing it in shell history, then launch:

```bash
read -r -s -p 'Provider API key: ' NL2REPO_API_KEY
printf '\n'
export NL2REPO_API_KEY
python main.py --backend codex --config config.codex.json
unset NL2REPO_API_KEY
```

This command performs a new model run. Each task gets a fresh workspace and temporary Codex home. Generation mounts only that task's workspace and home; the agent can execute commands without interactive approval inside its container. Container credentials are passed by environment-variable name, and known key values are redacted from retained CLI/lifecycle logs. Review generated artifacts before sharing them.

## Grade existing code without generation

Configure exactly one model/task and supply your own saved repository directory:

```bash
python main.py --backend codex --config config.codex.json \
  --saved-submission /absolute/path/to/saved/repository
```

No API key, agent image, or model call is required for replay. The evaluator still needs Docker, Buildx, the task's benchmark image and any network access required by its original installation commands. Replay always evaluates, even when the config sets `evaluate: false`, and cannot be combined with `--skip-evaluation`. Use the actual generating backend as the label; changing that label does not run the named agent or prove the saved code's origin.

Replay copies the submission into a new run. If `start.md` is present it must match the configured task. Internal file/directory symlinks are converted only in the copy to relative links to their resolved internal targets, including absolute links and link chains. They remain usable in the evaluator's second copy and inside Docker. Links outside the source, broken links and link cycles are rejected before copying. The original files and original link text remain unchanged. Keep the source directory stable during replay. Saved benchmark submissions and local evidence are not included in this code release.

## Results and failure handling

Each run writes `result/<task-model-uuid>.json` and a unique `workspaces/<task-model-uuid>/`. Generation retains `workspace/`, `prompt.txt`, `generation.json`, CLI output and lifecycle logs. The evaluator works on `evaluation/workspace/`, a separate copy.

- `generation_status` is `completed` for successful process/container completion, or `reused` for replay.
- Timeouts, nonzero exits, container errors and cleanup failures block normal post-generation grading, matching the existing backends.
- `turn_completed`, `event_errors` and malformed-event counts are diagnostic; they do not independently veto grading after successful process completion.
- New Codex runs record `completion_policy: "process_exit_and_cleanup"`.
- `score` is the original passed-test count. `completed` does not mean every test passed.
- Inspect installation exit codes under `post_process_result.test_results.command_results`. The original evaluator continues after installation failures and may still report a completed score.

The evaluator retains the original packaging/test removal, task image, commands and scorer. No generated dependency policy or alternate grader is introduced. See [validation and limitations](codex-validation.md) before interpreting scores as a controlled research comparison.

## Offline checks

With the host requirements installed, these tests use synthetic container/model outcomes and do not call a provider:

```bash
python -m unittest discover -s tests -p 'test_codex*.py' -v
python -m unittest discover -s tests -p 'test_backend_protocol_parity.py' -v
bash -n scripts/build_codex.sh
```

An optional request-serialization probe exercises the installed CLI against a rejecting loopback server. All model requests receive HTTP 401 and no code is generated. Keep networking disabled:

```bash
mkdir -p codex-evidence
docker run --rm --network none --entrypoint python \
  --volume "$PWD:/source:ro" --volume "$PWD/codex-evidence:/report:rw" \
  nl2repobench-codex:0.167.2 \
  /source/tests/probe_codex_request.py /source /report/request-probe.json
```

The synthetic probe uses `gpt-6.1-sol`, medium effort and a 200000 context setting. It tests serialization only, not provider availability or model behavior. It does not read your local provider configuration or credentials.
