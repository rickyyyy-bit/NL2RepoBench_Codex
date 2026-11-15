"""Select a generation backend and execute the configured benchmark batch."""

import argparse
import json
import os
from pathlib import Path

from logging_config import get_logger
import test_data_service

logger = get_logger(__name__)
BACKENDS = ("openhands", "deepseek", "codex")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.json"))
    parser.add_argument("--backend", choices=BACKENDS)
    parser.add_argument("--skip-evaluation", action="store_true", help="Generate repositories without running benchmark tests")
    parser.add_argument("--saved-submission", type=Path,
                        help="Evaluate a copy of an existing submission for one configured task, without generation or API credentials")
    args = parser.parse_args()
    with Path(args.config).expanduser().open(encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        parser.error("Configuration must be a JSON object")
    if args.saved_submission and args.skip_evaluation:
        parser.error("--saved-submission cannot be combined with --skip-evaluation")
    saved_submission = args.saved_submission.resolve() if args.saved_submission else None
    if args.skip_evaluation:
        config["evaluate"] = False
    backend = args.backend or config.get("backend", "openhands")
    if backend not in BACKENDS:
        parser.error(f"Unknown backend: {backend}")
    # Existing task metadata and evaluator paths are relative to the benchmark checkout.
    os.chdir(Path(__file__).resolve().parent)
    test_data_service.read_all_test_data()
    if saved_submission:
        from runner import evaluate_saved_submission, model_tasks, new_run_id, Job, run_batch
        from functools import partial
        selected = model_tasks(config)
        if len(selected) != 1:
            parser.error("--saved-submission requires exactly one configured model/task")
        _, model, task = selected[0]
        run_id = new_run_id(task.proName, model)
        results = run_batch([Job(run_id, backend, model, task.proName,
                            partial(evaluate_saved_submission, saved_submission, run_id, task))], 1)
    elif backend == "codex":
        from codex_backend.runner import start_codex
        results = start_codex(config)
    elif backend == "deepseek":
        from deepseek.runner import start_deepseek
        results = start_deepseek(config)
    else:
        from openhands.openhands_app import start_openhands
        results = start_openhands(config)
    failed = sum(result["status"] != "completed" for result in results)
    logger.info("%s batch finished: %d tasks, %d failed", backend, len(results), failed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
