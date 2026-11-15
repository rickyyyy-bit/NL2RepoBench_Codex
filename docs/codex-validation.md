# Validation scope and research limitations

This integration targets the DeepSeek fork at baseline `bbd664bdb093351f78b3b2670da9ee53745b27ee`. Codex is added through the existing `main.py` entry point. OpenHands, DeepSeek teamwork, benchmark task data and the original evaluator remain unchanged.

## Evidence established locally

The offline checks cover all three entry-point routes, task/prompt transfer, shared evaluator identity, model-setting forwarding, key redaction, saved-submission preservation, container ownership/cleanup and failure handling. Nine simulated process/event outcomes were compared against DeepSeek. These tests do not constitute model generation.

The review's saved-replay absolute-symlink defect is fixed: internal links are rebased to relative links to resolved targets in the new copy. All 24 offline tests passed, including six new regression tests covering absolute file/directory links, relative/chained links, external targets, broken links, cycles, two-copy isolation and repeated replay preservation. A synthetic Docker check used the original Dockerfile builder and verified all five fixture paths after both copies and the Docker COPY step, with the original source location unavailable. The original source/link text was unchanged. No model generation or benchmark grading was rerun for this fix; the evaluator remains unchanged. This concerns saved-submission preparation, not the generated-code test failures reported below.

Two saved `math-verify` submissions were previously replayed through the original evaluator:

| Saved agent | Model / effort recorded by original run | Passed | Failed | Install exit | Pytest exit |
|---|---|---:|---:|---:|---:|
| Codex | GPT-6.1 Sol / medium | 165 / 192 | 27 | 0 | 1 |
| OpenHands | GPT-6.1 Sol / medium | 162 / 192 | 30 | 1 | 1 |

The two replays used the same 192 test identifiers and the benchmark image's original tests and packaging. Saved sources and old results were hash-checked and retained. Those private local artifacts are not bundled here; users can replay their own saved submissions using the guide. These are regression checks of grading, not a newly controlled generation experiment.

The saved OpenHands repository has a flat package layout. The benchmark's retained packaging expects `src`, so installation failed with `error in 'egg_base' option: 'src' does not exist or is not a directory`. The original evaluator continued, and `/workspace` made the generated package importable for all 192 tests. This integration deliberately preserves that behavior; the OpenHands result is not a clean-installation result.

## Dependency policy

The original evaluator removes generated packaging files before copying source onto the benchmark image. For math-verify, the retained image packaging uses `latex2sympy2_extended==1.10.2`. A generated declaration of 1.10.1 does not override it. No version alignment to generated dependency declarations is introduced. A DeepSeek submission with the same flat-layout conflict would encounter the same shared packaging rule; no actual DeepSeek failure is inferred from that observation.

## Model settings and output limits

The pinned Codex CLI 0.167.2 was checked with networking disabled and a loopback server that rejected every request. Its serialized requests contained the configured model `gpt-6.1-sol` and medium effort. They contained no explicit output-token cap. Adding the tested `model_max_output_tokens=16384` CLI setting did not add a cap. The backend therefore continues to reject `maxTokens` rather than claim support. The server/model's effective default was not measured.

DeepSeek's profile defaults to `maxTokens: 16384`; forwarding of an explicitly supplied Responses model, medium effort and context value was verified offline, but its live request behavior was not verified. The earlier experimental OpenHands Sol launcher configured 128000 output tokens; it is not the stock OpenHands backend in this release. The stock launcher does not forward `reasoningEffort`, `contextWindow` or `maxTokens`, nor does it connect that earlier experimental ELM Responses adapter.

These output limits are not aligned. A context-window setting or a tool-history limit is not a replacement for a generated-response cap. The official reference defines those settings separately. [Official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)

## What cannot yet be claimed

- No fresh generation-and-grading task has been completed through this final integration path. The earlier runs and saved-submission replays are not a substitute for that check.
- No saved DeepSeek result or installed DeepSeek agent image was available for a real DeepSeek run. Live Sol/medium compatibility is not established for it.
- The stock OpenHands entry point needs the experimental transport integration before a matched ELM Sol/medium run can be claimed.
- Agent-specific prompts, tools and runtimes differ. DeepSeek retains a lead plus at least two teammates; Codex is single-agent. Total compute is not equalized merely by using the same wall-clock timeout.
- Generation images and host requirements retain some upstream/unpinned dependencies. Image IDs and installed versions should be recorded for an experiment; a fixed CLI version alone does not pin the entire environment.

Publish this as an integration with documented limitations, not evidence that one agent outperforms another under fully matched conditions. A later controlled comparison needs verified model settings, an explicit budget/output-limit policy, and new trials under the chosen protocol.
