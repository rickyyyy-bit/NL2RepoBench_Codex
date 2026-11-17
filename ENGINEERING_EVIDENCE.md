# What I did well

| Strong point | Supporting evidence | Remaining limitation |
| --- | --- | --- |
| **Kept grading consistent.** | The task definitions and prompt match the official NL2RepoBench checkout. The integration uses its original grader, with a diagnostic ZIP fix that preserves symbolic links. Grading uses a separate copy of the generated workspace. | The reported measurements cover the tasks in the results report. |
| **Checked what the backend sends and records.** | Request captures confirmed the model and medium reasoning setting. The live runs recorded generation time and token usage. | The effective server-side output limit remains unverified. |
| **Kept the benchmark easy to run.** | The launcher reads `config.json` through the original `python main.py` entry point. Offline tests covered the Codex and OpenHands launch paths, Docker cleanup, and the path from generated files to a score. | Package verification simulated Docker and model calls. See the [results report](NL2RepoBench_Codex_Results.md) for the earlier live runs. |
