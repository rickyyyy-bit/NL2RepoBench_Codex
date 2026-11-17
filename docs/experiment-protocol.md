# Experiment protocol and limitations

The evaluator is independent of the generation agent. The bundled task instructions, task metadata, packaging rules, test commands and passed-test scorer retain the NL2RepoBench protocol. Moving the evaluator into `benchmark/` changes its import location, not its grading behavior.

## Controls for a comparison

Use the same task set, task instructions, evaluation image IDs, evaluator revision, test commands and scoring policy for every experimental condition. Use the same model endpoint/version and explicitly verified reasoning settings. Predeclare generation timeouts, retry policy, tool/network access, resources, number of trials and the treatment of failures. Keep failed attempts in the denominator; do not select only successful submissions.

Use `benchmark/prompt.py` as the common task instruction where the experimental design allows it. Record agent-specific system instructions and tools as part of the experimental condition. Grading external saved code here makes evaluation consistent; it cannot establish that those repositories were generated under matched conditions.

Record the repository revision, the protocol manifest, generation and evaluation image IDs, host `pip freeze`, model settings, per-run duration and available token usage. Generation results record the image ID, model settings, prompt, completion policy and diagnostics. Evaluation results record the test image ID and command exit codes. For replay, retain the generating agent's original metadata separately.

## Preserved evaluation behavior

The evaluator copies source, removes generated packaging and selected generated test files, overlays the remaining source onto the task image, then executes the task's installation/test commands. The image supplies packaging and dependencies. A generated dependency declaration does not override that policy.

Installation failure does not automatically stop testing or invalidate the passed-test score under this protocol. Inspect and report installation outcomes separately. Changing this rule, dependencies, test cleanup or scoring would define a different protocol and must be applied to all comparison conditions.

## Limits that still matter

- Codex has no verified explicit per-request output-token cap in this adapter. `maxTokens` is rejected. The server's effective output default is unknown; this package cannot claim an equal-token-budget comparison.
- Model/reasoning forwarding can be checked locally, but provider compatibility requires a live run. No fresh generation-and-grading experiment has been completed through this standalone entry point yet.
- Generation-image base tags and transitive host dependencies are not fully frozen. Record and reuse the actual environments/image IDs across a study.
- Task images are external NL2RepoBench assets. Their availability and installed dependencies remain operational requirements; independence from other agents does not make grading self-contained without Docker assets.
- Replayed scores and offline fixture tests establish evaluation behavior, not agent superiority or a controlled multi-agent experiment.

This package supplies an independent Codex runner and a common grader. Fairness also requires an experiment design with matched controls and disclosed differences.
