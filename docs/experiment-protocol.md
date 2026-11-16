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
- One live `math-verify` generation-and-grading run completed through this standalone entry point on 15 November 2026. A subsequent five-task pilot on 15-16 November exercised the same Codex backend with `gpt-6.1-sol` and medium reasoning and exposed archive and dependency limitations. Its unmodified outcomes and separately recovered grades are distinguished in [verification](validation.md). This is not validation of all 104 tasks or other providers/settings.
- The diagnostic ZIP writer dereferences file symlinks. A generated `.venv/bin/python` link whose target exists only in the generation container can therefore block grading. The pilot recovered two scores with a separate archive-only workaround; that workaround is not incorporated in this source snapshot. Saved-submission replay also rejects broken/external links intentionally, so normal replay is not a workaround for these virtual environments.
- The preserved command runner splits commands into arguments without shell interpretation. The `parse` installation command contains `&`, which is passed literally to pip and fails. Testing continues under the retained scoring policy.
- The grader removes generated packaging and uses the task image's packaging. A submission's declared dependency may therefore be unavailable. In the pilot, `structlog` failed before test execution because `typing_extensions` was missing; its recorded zero is a setup outcome, not 828 executed failures. No dependency adjustment is included here.
- Generation permits network access, and upstream target-project source reuse was observed for `parse`, `structlog` and `boltons`. A specification-only implementation study needs a separately defined and enforced source-reuse policy. The observed scores do not establish such a study.
- Generation-image base tags and transitive host dependencies are not fully frozen. Record and reuse the actual environments/image IDs across a study.
- Task images are external NL2RepoBench assets. Their availability and installed dependencies remain operational requirements; independence from other agents does not make grading self-contained without Docker assets.
- Replayed scores and offline fixture tests establish evaluation behavior, not agent superiority or a controlled multi-agent experiment.

This package supplies an independent Codex runner and a common grader. Fairness also requires an experiment design with matched controls and disclosed differences.
