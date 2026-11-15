# Verification scope

This package separates the benchmark evaluator and task prompt from generation adapters. It includes the task data and required benchmark modules; it is not an overlay requiring another repository.

The offline suite checks Codex configuration and failure handling, source preservation, replay links, and a complete launcher-to-grader pipeline with simulated container/model outcomes. A separate subprocess blocks imports of all agent modules while replaying a saved submission. Protocol file fingerprints detect changes to the bundled task data and evaluator snapshot.

The launcher pipeline test deliberately includes an installation failure followed by pytest output, ensuring that the recorded outcome preserves the benchmark's scoring policy. The numbers in that test are synthetic fixtures, not new model results.

All 25 offline tests passed from a separate copy containing only this standalone package. The launcher help and build-script syntax checks passed. A Docker check using synthetic files verified replay links after both copies and Docker COPY, with the original source location unavailable and container networking disabled. No model generation or benchmark grading was performed.

The tests used an existing isolated Python environment for host dependencies; they did not import source from the earlier repository. This was not a fresh dependency installation. Validation results are recorded in [verification.json](verification.json). Earlier experiment results and prior submission folders are preserved outside this repository. No historical score is presented as a new standalone experiment.

A live provider generation-and-grading run remains outstanding. The optional local request probe rejects all requests and cannot replace that check. See [experiment limitations](experiment-protocol.md).
