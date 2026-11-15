"""Codex generation adapter using the agent-independent benchmark evaluator."""
import json
import os
from functools import partial
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse

from benchmark.docker_cli import docker_command
from .containers import run_container
from .events import redact_bytes, summarize_events
from benchmark.prompt import PROMPT
from runner import Job, evaluate_result, evaluation_enabled, model_tasks, new_run_id, positive_int, run_batch, write_json

DEFAULT_IMAGE = 'nl2repobench-codex:0.167.2'
COMPLETION_POLICY = 'process_exit_and_cleanup'


def resolve_model(entry):
    if entry.get('protocol', 'openai-responses') != 'openai-responses':
        raise ValueError('Codex requires protocol=openai-responses; no automatic transport fallback')
    unsupported = {'maxTokens', 'compat', 'reasoningEfforts'} & entry.keys()
    if unsupported:
        raise ValueError(f'Unsupported Codex model settings: {sorted(unsupported)}')
    endpoint = entry.get('baseUrl') or os.environ.get('NL2REPO_BASE_URL')
    if not isinstance(endpoint, str):
        raise ValueError('Set baseUrl or NL2REPO_BASE_URL')
    parsed = urlparse(endpoint)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('baseUrl must be an HTTP(S) API endpoint without embedded credentials, query or fragment')
    key_env = entry.get('apiKeyEnv', 'NL2REPO_API_KEY')
    if not isinstance(key_env, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key_env):
        raise ValueError('apiKeyEnv must name an environment variable')
    secret = os.environ.get(key_env) or entry.get('sk')
    if not isinstance(secret, str) or not secret.strip():
        raise ValueError(f'Set {key_env} before launching Codex')
    public = {'model': entry['moduleName'], 'base_url': endpoint.rstrip('/'), 'protocol': 'openai-responses'}
    if 'reasoningEffort' in entry:
        effort = entry['reasoningEffort']
        if effort not in {'none', 'minimal', 'low', 'medium', 'high', 'xhigh'}:
            raise ValueError('Unsupported reasoningEffort')
        public['reasoning_effort'] = effort
    if 'contextWindow' in entry:
        public['context_window'] = positive_int(entry['contextWindow'], 'contextWindow')
    return public, secret


def image_info(image):
    try:
        inspected = docker_command(['image', 'inspect', image], capture_output=True, timeout=30)
        value = json.loads(inspected.stdout)[0]
        base = ['run', '--rm', '--network', 'none', '--env', 'CODEX_HOME=/tmp', '--entrypoint', 'codex', value['Id']]
        version = docker_command([*base, '--version'], capture_output=True, timeout=30).stdout.strip()
        help_text = docker_command([*base, 'exec', '--help'], capture_output=True, timeout=30).stdout
        for flag in ['--json', '--ephemeral', '--sandbox', '--skip-git-repo-check', '--model']:
            if flag not in help_text:
                raise ValueError(f'Codex image lacks required CLI flag {flag}')
        return {'tag': image, 'id': value['Id'], 'codex_version': version}
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError('Codex image unavailable or unusable; run scripts/build_codex.sh or set codex.image') from exc


def generation_args(image, workspace, home, model):
    args = ['--init', '--user', f'{os.getuid()}:{os.getgid()}',
            '--volume', f'{workspace}:/workspace:rw', '--volume', f'{home}:/home/codex:rw',
            '--workdir', '/workspace', '--env', 'HOME=/home/codex', '--env', 'CODEX_HOME=/home/codex',
            '--env', 'NL2REPO_MODEL_API_KEY', '--add-host', 'host.docker.internal:host-gateway',
            '--entrypoint', 'codex', image, '-a', 'never', 'exec', '--json', '--ephemeral',
            '--skip-git-repo-check', '--sandbox', 'danger-full-access', '--model', model['model'],
            '-c', 'model_provider="nl2repo"', '-c', 'model_providers.nl2repo.name="NL2RepoBench"',
            '-c', 'model_providers.nl2repo.wire_api="responses"',
            '-c', 'model_providers.nl2repo.env_key="NL2REPO_MODEL_API_KEY"',
            '-c', 'model_providers.nl2repo.base_url=' + json.dumps(model['base_url']),
            '-c', 'features.multi_agent=false', '-c', 'web_search="disabled"']
    if 'reasoning_effort' in model:
        args += ['-c', 'model_reasoning_effort=' + json.dumps(model['reasoning_effort'])]
    if 'context_window' in model:
        args += ['-c', 'model_context_window=' + str(model['context_window'])]
    return [*args, PROMPT]


def _run_task(run_id, test_data, model, secret, timeout, image, evaluate):
    run_dir = Path('workspaces').resolve() / run_id
    workspace = run_dir / 'workspace'
    workspace.mkdir(parents=True)
    shutil.copyfile(test_data.md, workspace / 'start.md')
    (run_dir / 'prompt.txt').write_text(PROMPT, encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='.codex-home-', dir=run_dir) as temporary:
        args = generation_args(image['id'], workspace, Path(temporary), model)
        write_json(run_dir / 'generation.json', {'agent': 'codex', 'image': image, 'model': model,
                   'prompt': PROMPT, 'timeout_seconds': timeout,
                   'command': [v.replace(temporary, '<temporary-home>') for v in args],
                   'completion_policy': COMPLETION_POLICY,
                   'evaluation_protocol': 'runner.evaluate_result -> benchmark.evaluator.post_process_task'})
        result = run_container(args, 'codex-' + run_id, run_dir, timeout,
                               env={**os.environ, 'NL2REPO_MODEL_API_KEY': secret})
    for name in ['stdout.jsonl', 'stderr.log', 'container.log']:
        path = run_dir / name
        if path.exists():
            path.write_bytes(redact_bytes(path.read_bytes(), secret))
    result = json.loads(redact_bytes(json.dumps(result).encode(), secret))
    events = summarize_events(run_dir / 'stdout.jsonl') if (run_dir / 'stdout.jsonl').exists() else {}
    result.update(events)
    finished = False
    if (run_dir / 'stdout.jsonl').exists():
        for line in (run_dir / 'stdout.jsonl').read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                finished |= json.loads(line).get('type') == 'turn.completed'
            except (ValueError, AttributeError):
                continue
    result.update(task_uuid=run_id, workspace_path=str(workspace), image=image, model=model,
                  generation_performed=True, turn_completed=finished, completion_policy=COMPLETION_POLICY)
    # Successful process completion and cleanup determine grading eligibility.
    # CLI event summaries remain diagnostics and do not independently veto grading.
    result['status'] = 'completed' if result['generation_status'] == 'completed' else 'failed'
    if result.get('cleanup_error'):
        result['status'] = 'failed'
    return evaluate_result(result, test_data, evaluate)


def start_codex(config):
    pool_size = positive_int(config.get('max_pool_size', 1), 'max_pool_size')
    evaluate = evaluation_enabled(config)
    supplied = config.get('codex', {})
    if not isinstance(supplied, dict) or supplied.keys() - {'image', 'task_timeout_seconds'}:
        raise ValueError('codex settings may contain only image and task_timeout_seconds')
    timeout = positive_int(supplied.get('task_timeout_seconds', config.get('task_timeout_seconds', 7200)), 'task_timeout_seconds')
    specifications = [(task, *resolve_model(entry)) for entry, _, task in model_tasks(config)]
    image = image_info(supplied.get('image', DEFAULT_IMAGE))
    jobs = []
    for task, model, secret in specifications:
        run_id = new_run_id(task.proName, model['model'])
        jobs.append(Job(run_id, 'codex', model['model'], task.proName,
                        partial(_run_task, run_id, task, model, secret, timeout, image, evaluate)))
    return run_batch(jobs, pool_size)
