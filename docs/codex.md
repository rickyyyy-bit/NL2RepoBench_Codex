# Configuration and manual testing

Use the setup and key-entry commands in the [README](../readme.md).

| Setting | Meaning |
|---|---|
| `startPro[].moduleName` | Exact provider model ID |
| `protocol` | `openai-responses` only |
| `baseUrl` | API base URL, or use `NL2REPO_BASE_URL` |
| `apiKeyEnv` | Key variable, default `NL2REPO_API_KEY` |
| `reasoningEffort` | Optional explicit supported effort |
| `contextWindow` | Optional context capacity; not an output budget |
| `proNameList` | Names of bundled task directories |
| `codex.image` | Generation image, default `nl2repobench-codex:0.167.2` |
| `codex.task_timeout_seconds` | Generation execution timeout, default 7200 |
| `max_pool_size` | Concurrent tasks, default 1 |
| `evaluate` | Whether to grade after generation, default true |

The adapter rejects `maxTokens`, `compat` and `reasoningEfforts`; those controls are not implemented. It does not fall back to a different API or model. The generation image pins Codex CLI 0.167.2. An existing image tag is left unchanged by the build script; record the actual image ID for experiments.

Internal replay symlinks are rebased in the copy so they survive the second evaluation copy and Docker COPY. External, broken and cyclic links are rejected. Keep the source stable during replay.

Run all offline tests from this repository:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
bash -n scripts/build_codex.sh
python main.py --help
```

These tests use synthetic generation and container outcomes. They do not contact a provider or prove live generation works.

The optional serialization probe runs the installed CLI against a rejecting local server. No successful model response or code generation occurs:

```bash
mkdir -p codex-evidence
docker run --rm --network none --entrypoint python \
  --volume "$PWD:/source:ro" --volume "$PWD/codex-evidence:/report:rw" \
  nl2repobench-codex:0.167.2 \
  /source/tests/probe_codex_request.py /source /report/request-probe.json
```

After generation, inspect `generation.json`, `result/*.json`, CLI logs, and `post_process_result.test_results.command_results`. Timeout, process/container failure and cleanup failure prevent normal grading. CLI event errors are diagnostic and do not independently override successful process completion.
