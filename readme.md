# Nl2RepoBench

## Project Overview

NL2Repo is a benchmark designed to evaluate the performance of Large Language Models (LLMs) and coding agents on **long-horizon tasks** that require generating a **complete, runnable code repository from scratch (0-to-1)**. The benchmark consists of **104 distinct tasks**, each paired with its own testing environment.

## Running the Code

The runner supports **DeepSeek Harness with Agent Teams**, **OpenHands**, and **Codex CLI** in headless batch mode. Select a backend with `backend` in the JSON configuration or `--backend`. Existing configurations without that field continue to use OpenHands.

All three backends use local Docker containers and the same existing evaluator. Python launches generation through the Docker CLI; the evaluator uses `python-on-whales`. Use Linux (or Ubuntu in WSL), Python 3.10 or newer, a running Docker daemon, and Docker Buildx. Model endpoints must be reachable from inside Docker.

### Codex setup and manual testing

See [the Codex guide](docs/codex.md) for portable setup, saved-submission replay, and generation commands. See [validation and limitations](docs/codex-validation.md) for the verification scope, output-limit differences, and the observed OpenHands packaging failure.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
docker buildx version
bash scripts/build_codex.sh
cp config.codex.example.json config.codex.json
```

Edit the model, endpoint, and task in `config.codex.json`, set `NL2REPO_API_KEY`, then run:

```sh
python main.py --backend codex --config config.codex.json
```

Codex uses the exact OpenHands task prompt and unmodified `start.md`, with the fork's scheduler, result format, and evaluator. Its image contains Codex CLI 0.167.2 and Python 3.12. The `codex` object accepts `image` and `task_timeout_seconds` (default 7200). Each task gets a fresh workspace and temporary Codex home. Model configuration accepts `moduleName`, `baseUrl` (or `NL2REPO_BASE_URL`), `apiKeyEnv` (default `NL2REPO_API_KEY`), optional `reasoningEffort` and `contextWindow`, and `proNameList`. Only `protocol: "openai-responses"` is supported; incompatible settings are rejected. Keep keys in environment variables.

Codex uses the same grading eligibility rule as the existing backends: successful process/container completion with no cleanup error. `turn_completed`, `event_errors`, and malformed-event counts remain diagnostics and do not independently prevent grading. New runs record `completion_policy: "process_exit_and_cleanup"`. Timeouts and process/container failures remain ungraded failures.

`maxTokens` is rejected for Codex: this adapter has no verified per-request output-cap setting. The pinned CLI sends no explicit cap in the tested configuration, and the tested `model_max_output_tokens` override does not add one. This does not mean unlimited output; the server's effective default is unknown. See [validation and limitations](docs/codex-validation.md) for the remaining comparison limits.

`--saved-submission PATH` grades a fresh copy using the original evaluator, without launching any agent or requiring an API key. It requires exactly one configured model/task, always evaluates, and cannot be combined with `--skip-evaluation`. The backend label records provenance; the configured model name is a label for replay, not an independently verified fact about the saved files.

The original evaluator removes generated packaging and selected test files from its evaluation copy, overlays it onto the task's original benchmark image, and executes the original test commands and scorer. This integration preserves that behavior, including continuing after installation failures. Inspect command exit codes as well as the score. No alternative grader or dependency policy is introduced.

> **Note:** When running in headless mode across multiple machines, you must set up shared file management (e.g., NFS) or manually transfer files to the target machines in advance.

### DeepSeek Harness setup

The integration targets harness commit `639ed01539` and its session format v4. Agent Teams is experimental; upgrading the harness also requires reviewing the profile and session-log reader. The build script exports that commit from your local checkout into a temporary build context. It leaves the checkout unchanged and excludes untracked files, credentials, and installed dependencies.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
bash scripts/build_deepseek.sh ~/deepseek-harness
cp config.deepseek.example.json config.deepseek.json
```

The image builds the harness with Node 24, pnpm 11.7.0, and Python 3.12. Building requires network access to install dependencies and sufficient memory for the harness build. It does not run tests. Generation runs as your host UID/GID so workspace and session artifacts remain readable on Linux.

Edit `config.deepseek.json` to supply `moduleName`, the endpoint protocol, and task names. Then provide the endpoint and key:

```sh
export NL2REPO_BASE_URL='https://your-endpoint.example/v1'
export NL2REPO_API_KEY='your-api-key'
python main.py --config config.deepseek.json
```

The example sets `evaluate: false`: it generates code and records team activity without running benchmark tests. Set `evaluate: true` to run the existing evaluator after a successful generation. `--skip-evaluation` overrides that setting for any backend.

For an endpoint running on the Docker host, use `host.docker.internal` in the URL instead of `localhost`, and ensure the endpoint listens on an interface Docker can reach.

#### Endpoint settings

Each `startPro` entry configures one model:

| Field | Meaning |
|---|---|
| `moduleName` | Exact model ID accepted by the endpoint |
| `protocol` | `openai-completions` (default), `openai-responses`, `anthropic-messages`, or `deepseek-messages` |
| `baseUrl` | API base URL; an empty value uses `NL2REPO_BASE_URL` |
| `apiKeyEnv` | Key environment variable, default `NL2REPO_API_KEY` |
| `contextWindow` | Model context capacity, default 131072 tokens |
| `maxTokens` | Configured per-request output limit, default 16384 tokens |
| `reasoningEffort` | Optional provider-supported effort; omit for the provider default |
| `reasoningEfforts` | Optional pi-ai model mapping, e.g. `{"high": "high"}`; `false` declares a non-reasoning model |
| `compat` | Optional pi-ai wire compatibility settings, such as `{"thinkingFormat": "deepseek"}` |
| `proNameList` | Task directories under `test_files` |

`openai-completions` selects pi-ai's Chat Completions transport. `deepseek-messages` selects the native DeepSeek Messages adapter, which uses `x-api-key` authentication. Its endpoint must support that protocol; an OpenAI-compatible `/v1` endpoint should use `openai-completions`. Native DeepSeek efforts are `off`, `low`, `high`, and `max`; other transports use their declared model capabilities. The lead and teammates inherit the same model configuration. No additional model or search credentials are needed.

Use environment variables for credentials. The legacy `sk` field is also accepted, but the generated DeepSeek profile and result JSON omit the key. `config.deepseek.json` and run artifacts are ignored by Git.

#### Team execution

The `deepseek` object configures `teammates` (default 2, minimum 2), `task_timeout_seconds` (default 7200), and optionally `image` (default `nl2repobench-deepseek:639ed01539`). `max_pool_size` limits concurrent benchmark tasks; each task may run a lead plus its teammates, so start with 1 until endpoint capacity is known.

Every task uses a fresh workspace and `DSH_HOME`. The `nl2repo` profile composes the harness base, headless runner, and experimental Agent Teams bundle. The prompt explicitly requires delegation, shared task tracking, lead/teammate messaging, and direct teammate communication. Teammates share the same workspace and coordinate file edits through task ownership.

Generation captures stdout, stderr, container status, and all persisted agent sessions. The session reader requires:

- The configured number of successfully created teammates.
- Delivered messages in both directions between the lead and each teammate.
- At least one delivered message between distinct teammates.
- A nonempty task board with no unfinished tasks.
- Completed final turns and no pending inbox or undelivered team messages.

These checks are reported in `team.status`. They record whether the requested workflow occurred; they do not establish code correctness or the quality of the collaboration, and they do not affect `status` or evaluation. The harness exits as soon as the lead finishes, so the prompt requires the lead to call `wait_agent` on every teammate first.

The task container has shell and filesystem access within its own runtime, with no interactive approvals. It mounts only that task's workspace and harness state. Session upload and external search are disabled in this profile.

### OpenHands setup

Before starting, ensure that Docker is installed locally and that the following images are available:

- `docker.all-hands.dev/all-hands-ai/openhands:0.56`
- `docker.all-hands.dev/all-hands-ai/runtime:0.56-nikolaik`

The runtime image comes with Python 3.12. To use another runtime image, update `RUNTIME_IMAGE` in `openhands/openhands_app.py`.

Run the existing configuration with:

```sh
python main.py --config config.json
```

OpenHands uses `template/config.template.toml` with per-task model and workspace settings. The optional top-level `task_timeout_seconds` defaults to 7200. The host does not need the OpenHands Python package; the agent runs in the OpenHands image.

## Data Layout

1. The `test_files` directory contains all repository-related task data, including:
   - A `.txt` file specifying the number of test cases
   - The repository documentation in `.md` format
   - Two `.json` files used for testing

2. Each task gets `workspaces/<task-model-uuid>/`. Its `workspace/` contains the original generated repository. If evaluation is enabled, the evaluator operates on a separate `evaluation/workspace/` copy because it removes package and test files before building its image.

3. Each task produces `result/<task-model-uuid>.json`, including failures. `generation_status`, `evaluation_status`, and DeepSeek's `team.status` report separate outcomes. `score` and `test_score` retain the existing passed-test count when evaluated; they are `null` when ungraded. A `completed` run does not mean every benchmark test passed. The CLI exits nonzero if any task fails to complete its requested stages.

4. The project is launched using a `config.json` file. A sample configuration is shown below:

```json
{
  "startPro": [
    {
      "moduleName": "",
      "baseUrl": "",
      "sk": "",
      "proNameList": [
        "math-verify"
      ]
    }
  ],
  "max_pool_size": 20
}
```

### Configuration Fields

- **startPro**: A list of task nodes.
  - Each node corresponds to a single model configuration.
  - **proNameList**: A list of task names, which must match the subdirectory names under `test_files`.

- **max_pool_size**: The maximum number of concurrent threads. Once this limit is reached, additional tasks will be queued until resources become available.

### DeepSeek artifacts

```text
workspaces/<task-model-uuid>/
  workspace/                 Generated repository, retained unchanged by evaluation
  prompt.txt                 Exact task prompt
  stdout.jsonl               Headless CLI event projection for the lead
  stderr.log                 Harness diagnostics
  container.log              Docker lifecycle diagnostics
  dsh-home/
    profiles/nl2repo/         Generated profile manifest and Cordis patch
    sessions/                Complete persisted lead and teammate session logs
    user/                    Container user's home and dependency caches
  evaluation/workspace/      Optional evaluation copy
result/<task-model-uuid>.json
```

The CLI event projection omits teammate events and truncates some values. Use `dsh-home/sessions/` for the full communication history. Containers are removed after their exit status is captured; timeouts stop the task container and retain diagnostics. The evaluator and its `linux/amd64` task images remain unchanged.
