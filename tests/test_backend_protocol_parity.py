"""Offline contract checks: no real generation, credentials, or Docker calls."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from codex_backend import runner as codex
from deepseek import runner as deepseek
from openhands import openhands_app
import runner


class BackendProtocolParityTests(unittest.TestCase):
    def test_all_backends_share_scheduler_and_evaluator(self):
        for backend in (codex, deepseek, openhands_app):
            with self.subTest(backend=backend.__name__):
                for name in ('evaluate_result', 'run_batch', 'model_tasks', 'evaluation_enabled'):
                    self.assertIs(getattr(backend, name), getattr(runner, name))

    def test_deepseek_and_codex_forward_model_and_medium_effort(self):
        entry = {'moduleName': 'gpt-6.1-sol', 'protocol': 'openai-responses',
                 'baseUrl': 'https://example.invalid/v1', 'contextWindow': 200000,
                 'reasoningEffort': 'medium'}
        with patch.dict(os.environ, {'NL2REPO_API_KEY': 'offline-placeholder'}):
            codex_model, _ = codex.resolve_model(entry)
            deepseek_model, _ = deepseek.resolve_model(entry)
        for name in ('model', 'base_url', 'protocol', 'context_window', 'reasoning_effort'):
            self.assertEqual(codex_model[name], deepseek_model[name])
        with tempfile.TemporaryDirectory() as temp:
            profile = deepseek.write_profile(Path(temp), deepseek_model, 2)
            patches = {item['id']: item for item in json.loads(profile.read_text())}
            self.assertEqual(patches['agent-default-model']['config']['model'], 'gpt-6.1-sol')
            self.assertEqual(patches['agent-default-model']['config']['reasoningEffort'], 'medium')
            route = patches['llm-pi-ai']['config']['providers']['nl2repo-endpoint']
            self.assertEqual(route['api'], 'openai-responses')
            self.assertEqual(route['models'][0]['contextWindow'], 200000)
            self.assertEqual(route['models'][0]['maxTokens'], 16384)
            self.assertNotIn('max_tokens', codex_model)
            self.assertNotIn('offline-placeholder', profile.read_text())

    def test_same_task_and_unmodified_generated_files_reach_evaluator(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                source = Path(temp) / 'original.md'
                source.write_bytes(b'Identical benchmark task instructions\n')
                task = SimpleNamespace(md=str(source), proName='offline-example')
                image = {'id': 'sha256:offline-placeholder'}
                model = {'model': 'offline-model', 'base_url': 'https://example.invalid/v1',
                         'protocol': 'openai-responses', 'context_window': 200000,
                         'max_tokens': 16384, 'reasoning_effort': 'medium'}
                received = []

                def fake_container(args, name, directory, timeout, env=None):
                    self.assertEqual(timeout, 7200)
                    workspace = directory / 'workspace'
                    self.assertEqual((workspace / 'start.md').read_bytes(), source.read_bytes())
                    (workspace / 'pyproject.toml').write_bytes(b'generated packaging must reach evaluator\n')
                    (workspace / 'implementation.py').write_bytes(b'generated code\n')
                    (directory / 'stdout.jsonl').write_bytes(event_log)
                    return dict(outcome)

                def capture(result, selected_task, enabled):
                    self.assertIs(selected_task, task)
                    self.assertTrue(enabled)
                    expected = 'completed' if outcome['generation_status'] == 'completed' and not outcome.get('cleanup_error') else 'failed'
                    self.assertEqual(result['status'], expected)
                    workspace = Path(result['workspace_path'])
                    received.append({name: (workspace / name).read_bytes() for name in
                                     ('start.md', 'pyproject.toml', 'implementation.py')})
                    return result

                completed_event = b'{"type":"turn.completed"}\n'
                clean = {'generation_status': 'completed', 'exit_code': 0}
                cases = [
                    ('clean', clean, completed_event),
                    ('missing-event', clean, b''),
                    ('event-error', clean, b'{"type":"turn.failed","error":"diagnostic"}\n'),
                    ('recovered-error', clean, b'{"type":"error","message":"retry"}\n' + completed_event),
                    ('malformed-event', clean, b'\xffnot-json\n'),
                    ('nonzero', {'generation_status': 'failed', 'exit_code': 1}, completed_event),
                    ('timeout', {'generation_status': 'timeout', 'exit_code': 0}, completed_event),
                    ('create-error', {'generation_status': 'error', 'exit_code': None}, b''),
                    ('cleanup-error', {**clean, 'cleanup_error': 'offline cleanup failure'}, completed_event),
                ]
                for label, outcome, event_log in cases:
                    with self.subTest(case=label):
                        with patch.object(codex, 'run_container', side_effect=fake_container), \
                             patch.object(codex, 'evaluate_result', side_effect=capture):
                            codex._run_task('codex-' + label, task, model, 'offline-placeholder', 7200, image, True)
                        with patch.object(deepseek, 'run_batch_container', side_effect=fake_container), \
                             patch.object(deepseek, 'summarize_sessions', return_value={'status': 'offline-test'}), \
                             patch.object(deepseek, 'evaluate_result', side_effect=capture):
                            deepseek._run_task('deepseek-' + label, task, model,
                                              {'NL2REPO_MODEL_API_KEY': 'offline-placeholder'},
                                              {'teammates': 2, 'task_timeout_seconds': 7200}, image, True)
                        self.assertEqual(received[-2], received[-1])
                self.assertEqual(len(received), 2 * len(cases))
            finally:
                os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
