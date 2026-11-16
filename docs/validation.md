# Verification scope

This package separates the benchmark evaluator and task prompt from generation adapters. It includes the task data and required benchmark modules; it is not an overlay requiring another repository.

The offline suite checks Codex configuration and failure handling, source preservation, replay links, and a complete launcher-to-grader pipeline with simulated container/model outcomes. A separate subprocess blocks imports of all agent modules while replaying a saved submission. Protocol file fingerprints detect changes to the bundled task data and evaluator snapshot.

The launcher pipeline test deliberately includes an installation failure followed by pytest output, ensuring that the recorded outcome preserves the benchmark's scoring policy. The numbers in that test are synthetic fixtures, not new model results.

All 25 offline tests passed from a separate copy containing only this standalone package. The launcher help and build-script syntax checks passed. A Docker check using synthetic files verified replay links after both copies and Docker COPY, with the original source location unavailable and container networking disabled. No model generation or benchmark grading was performed.

The tests used an existing isolated Python environment for host dependencies; they did not import source from the earlier repository. This was not a fresh dependency installation. Validation results are recorded in [verification.json](verification.json). Earlier experiment results and prior submission folders are preserved outside this repository. No historical score is presented as a new standalone experiment.

On 15 November 2026, a fresh `math-verify` task completed generation and grading through the unmodified standalone launcher using ELM, configured with `gpt-6.1-sol`, medium reasoning and a 200000 context window. Generation exited 0, installation exited 0, and all 192 benchmark tests ran: 168 passed, 24 failed, with zero reported errors. Pytest exited 1 because tests failed; the launcher exited 0 because the benchmark pipeline completed under its recorded scoring policy. Total time was approximately 10 minutes 39 seconds.

The evaluation image imported `/workspace/math_verify/__init__.py`, whose hash matched the generated submission and evaluation copy. Both run containers were removed. The source files in the run copy matched the standalone snapshot. Raw results, generated code and logs are retained separately from this publication folder; the verification record contains the run ID and image identities.

This establishes one live end-to-end task, not full correctness of generated code, validation of every task/provider, or an equal-budget agent comparison. The optional local request probe remains a separate serialization check. See [experiment limitations](experiment-protocol.md).

## Subsequent five-task pilot, 15-16 November 2026

Five new Codex attempts used the same backend and grader snapshot, ELM `gpt-6.1-sol`, medium reasoning, a 200000 context window and a 7200-second generation timeout. Task sizes were selected using specification length and test count. These are separate attempts from the earlier 168/192 result above.

| Task | Unmodified grading outcome | Separately recovered score |
|---|---|---|
| jsonlines | 26/27 passed | Not needed |
| parse | Archive failed before grading | 92/96 passed |
| math-verify | Archive failed before grading | 166/192 passed |
| structlog | Recorded 0/828; pytest stopped before tests because `typing_extensions` was missing | Not performed |
| boltons | 420/423 passed | Not needed |

All five Codex generation processes completed. For `parse` and `math-verify`, an isolated diagnostic ZIP correction preserved symlinks instead of following missing interpreter targets, then graded fresh copies of the saved submissions. Source checks confirmed that both original submissions were unchanged. Generation was not repeated. The recovered scores are not successful unmodified-runner grades: the recovery helper is outside this submission package and is not included as a runtime dependency.

The `parse` installation command failed in recovered grading because the retained runner passed literal `&` to pip; pytest still ran. The grader's packaging/dependency policy was unchanged. Upstream target-project source reuse was observed in the `parse`, `structlog` and `boltons` submissions, so these scores must not be presented as implementation from the specification alone or general agent superiority.

The pilot preserved task documents, task prompts, evaluation image identities and benchmark source hashes. Prepared package files matched saved submissions in import/source-tree checks; the latter checked files before installation, not the complete installed environment. A compact, Codex-only evidence record is included in [pilot-verification.json](pilot-verification.json). Raw source workspaces, conversations and original results remain outside the submission package.

This delivery retains the original implementation and protocol, including the documented archive and dependency limitations. It is suitable for supervisor review as an integration with pilot validation; it does not claim that every task works or that all research-comparison issues are resolved.

For the final delivery on 16 November 2026, all 25 offline tests passed again from a separate clean copy. The launcher help and build-script syntax checks passed. These checks used the existing isolated Python dependency environment, performed no model calls and did not rerun benchmark generation or grading. Only documentation/evidence changed from the standalone source snapshot. See [submission-verification.json](submission-verification.json).
