# NL2RepoBench with Codex

This integration adds Codex as a backend for [NL2RepoBench](https://github.com/multimodal-art-projection/NL2RepoBench/tree/781a1da1ee41fb8edb0bed22f586d69111610edf). Use Linux or Ubuntu on WSL, Python 3.12, Docker with Buildx, and an ELM API key.

## Set up

From the extracted project directory, run:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
bash scripts/build_codex.sh
```

## Run

```bash
read -r -s -p 'ELM API key: ' NL2REPO_API_KEY
printf '\n'
export NL2REPO_API_KEY
python main.py
```

`main.py` reads `config.json`. The supplied configuration runs Codex on `jsonlines`. Change `startPro[0].proNameList` to run other tasks from `test_files/`. Results go to `result/`, and generated code and grading diagnostics go to `workspaces/`. The score is the number of tests passed.

To use an existing OpenHands configuration, run `python main.py --config path/to/openhands.json`. Configurations without a `backend` field use OpenHands.

See [SUBMISSION.md](SUBMISSION.md) for the overview, engineering evidence, and reported results.
