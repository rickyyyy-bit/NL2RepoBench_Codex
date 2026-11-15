"""Generate with Codex or evaluate a saved repository using NL2RepoBench."""
import argparse
from functools import partial
import json
import os
from pathlib import Path

from logging_config import get_logger
import test_data_service

logger = get_logger(__name__)
BACKENDS = ("codex",)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.codex.json"))
    parser.add_argument("--backend", choices=BACKENDS, help="Optional; generation defaults to Codex")
    parser.add_argument("--skip-evaluation", action="store_true")
    parser.add_argument("--saved-submission", type=Path,
                        help="Grade a copy of saved code without launching an agent")
    parser.add_argument("--submission-agent",
                        help="Provenance label for saved code, not a generation backend")
    args = parser.parse_args()
    with Path(args.config).expanduser().open(encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        parser.error("Configuration must be a JSON object")
    if args.saved_submission and args.skip_evaluation:
        parser.error("--saved-submission cannot be combined with --skip-evaluation")
    if args.submission_agent is not None and (not args.saved_submission or not args.submission_agent.strip()):
        parser.error("--submission-agent requires a saved submission and a nonempty label")
    if not args.saved_submission and (args.backend or config.get("backend", "codex")) != "codex":
        parser.error("This package supports Codex generation only")
    saved_submission = args.saved_submission.resolve() if args.saved_submission else None
    if args.skip_evaluation:
        config["evaluate"] = False
    os.chdir(Path(__file__).resolve().parent)
    test_data_service.test_data_list.clear()
    test_data_service.read_all_test_data()
    if saved_submission:
        from runner import Job, evaluate_saved_submission, model_tasks, new_run_id, run_batch
        selected = model_tasks(config)
        if len(selected) != 1:
            parser.error("--saved-submission requires exactly one configured model/task")
        _, model, task = selected[0]
        run_id = new_run_id(task.proName, model)
        label = args.submission_agent or "external"
        results = run_batch([Job(run_id, label, model, task.proName,
                                partial(evaluate_saved_submission, saved_submission, run_id, task))], 1)
    else:
        from codex_backend.runner import start_codex
        results = start_codex(config)
    failed = sum(result["status"] != "completed" for result in results)
    logger.info("Batch finished: %d tasks, %d failed", len(results), failed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
