# Run the Codex integration

For a short overview and the engineering evidence, see [SUBMISSION.md](SUBMISSION.md).

## Install

Use Linux or Ubuntu on WSL with Python 3.12, Git, Docker with Buildx, and an ELM API key. The Docker daemon needs access to the benchmark task images, and the generation container needs to reach ELM.

From the directory containing this README, apply the integration to a fresh checkout of [Dalongbao’s NL2RepoBench fork](https://github.com/dalongbao/NL2RepoBench).

```bash
package_dir="$PWD"
git clone --config core.autocrlf=false https://github.com/dalongbao/NL2RepoBench.git nl2repobench-review
cd nl2repobench-review
git switch --detach bbd664bdb093351f78b3b2670da9ee53745b27ee
git apply --check "$package_dir/codex-integration.patch"
git apply "$package_dir/codex-integration.patch"
cp -R "$package_dir/codex_backend" .
cp "$package_dir/docker/codex.Dockerfile" docker/
cp "$package_dir/scripts/build_codex.sh" scripts/
cp "$package_dir/config.codex.example.json" config.codex.json

python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
bash scripts/build_codex.sh
```

## Run

The supplied configuration runs `jsonlines`. To run another task, change `proNameList` in `config.codex.json`.

```bash
read -r -s -p 'ELM API key: ' NL2REPO_API_KEY
printf '\n'
export NL2REPO_API_KEY
python main.py --config config.codex.json
unset NL2REPO_API_KEY
```

The runner writes one JSON file per run in `result/`, including the test score, generation duration and recorded token counts. Generated code and grading diagnostics are in `workspaces/`. Test scores count passed tests, so a completed run can include individual test failures.
