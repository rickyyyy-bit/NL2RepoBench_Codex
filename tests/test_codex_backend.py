import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import main
import runner
from codex_backend import runner as codex
from deepseek import runner as deepseek
from openhands import openhands_app
from openhands.openhands_app import PROMPT


class CodexBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.previous)
        self.spec = self.root / 'spec.md'
        self.spec.write_text('original task instructions\n')
        self.task = SimpleNamespace(md=str(self.spec), proName='example')
        self.model = {'model': 'test-model', 'base_url': 'https://example.invalid/v1',
                      'reasoning_effort': 'medium'}
        self.image = {'id': 'sha256:test', 'codex_version': 'test'}

    def fake_generation(self, args, name, directory, timeout, env=None, finished=True):
        self.assertEqual(args[-1], PROMPT)
        self.assertNotIn('private-test-key', ' '.join(args))
        self.assertEqual(env['NL2REPO_MODEL_API_KEY'], 'private-test-key')
        workspace = directory / 'workspace'
        self.assertEqual((workspace / 'start.md').read_bytes(), self.spec.read_bytes())
        (workspace / 'pyproject.toml').write_text('[project]\nname="generated"\n')
        events = [{'type': 'item.completed', 'item': {'text': 'private-test-key'}}]
        events.append({'type': 'turn.completed', 'usage': {'input_tokens': 10}} if finished
                      else {'type': 'turn.failed', 'error': {'message': 'request failed'}})
        (directory / 'stdout.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
        return {'generation_status': 'completed', 'exit_code': 0}

    def test_generation_hands_unchanged_submission_to_shared_evaluator(self):
        seen = []
        def evaluate(result, task, enabled):
            self.assertIs(task, self.task)
            self.assertTrue(enabled)
            self.assertEqual(result['status'], 'completed')
            seen.append(Path(result['workspace_path']))
            self.assertTrue((seen[-1] / 'pyproject.toml').exists())
            return result
        with patch.object(codex, 'run_container', side_effect=self.fake_generation), patch.object(codex, 'evaluate_result', side_effect=evaluate):
            result = codex._run_task('one', self.task, self.model, 'private-test-key', 60, self.image, True)
        self.assertEqual(len(seen), 1)
        self.assertEqual(result['token_usage']['input_tokens'], 10)
        self.assertNotIn('private-test-key', (self.root / 'workspaces/one/stdout.jsonl').read_text())
        self.assertFalse(list((self.root / 'workspaces/one').glob('.codex-home-*')))

    def test_nonzero_process_cannot_be_scored_as_success(self):
        def failed(*args, **kwargs):
            result = self.fake_generation(*args, **kwargs, finished=False)
            result.update(generation_status='failed', exit_code=1)
            return result
        with patch.object(codex, 'run_container', side_effect=failed):
            result = codex._run_task('failed', self.task, self.model, 'private-test-key', 60, self.image, True)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['evaluation_status'], 'skipped')

    def test_event_errors_remain_diagnostic_after_clean_process_exit(self):
        def events_with_error(*args, **kwargs):
            return self.fake_generation(*args, **kwargs, finished=False)
        with patch.object(codex, 'run_container', side_effect=events_with_error), \
             patch.object(codex, 'evaluate_result', side_effect=lambda result, task, enabled: result) as evaluate:
            result = codex._run_task('event-error', self.task, self.model, 'private-test-key', 60, self.image, True)
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(result['turn_completed'])
        self.assertEqual(result['event_errors'][0]['type'], 'turn.failed')
        self.assertEqual(result['completion_policy'], 'process_exit_and_cleanup')
        evaluate.assert_called_once_with(result, self.task, True)

    def test_skip_evaluation_preserves_generation_result(self):
        with patch.object(codex, 'run_container', side_effect=self.fake_generation):
            result = codex._run_task('skip', self.task, self.model, 'private-test-key', 60, self.image, False)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['evaluation_status'], 'skipped')

    def test_explicit_response_model_settings(self):
        entry = {'moduleName': 'test-model', 'baseUrl': 'https://example.invalid/v1',
                 'reasoningEffort': 'medium', 'contextWindow': 200000}
        with patch.dict(os.environ, {'NL2REPO_API_KEY': 'private-test-key'}):
            public, secret = codex.resolve_model(entry)
        args = codex.generation_args('image', self.root, self.root, public)
        self.assertIn('model_reasoning_effort="medium"', args)
        self.assertIn('model_context_window=200000', args)
        self.assertIn('model_providers.nl2repo.wire_api="responses"', args)
        self.assertEqual(args[-1], PROMPT)
        self.assertNotIn(secret, json.dumps(public))
        self.assertNotIn(secret, json.dumps(args))

    def test_wrong_protocol_and_ignored_settings_are_rejected(self):
        for extra in [{'protocol': 'openai-completions'}, {'maxTokens': 100}]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                codex.resolve_model({'moduleName': 'test-model', **extra})

    def test_embedded_endpoint_credentials_rejected(self):
        with self.assertRaises(ValueError):
            codex.resolve_model({'moduleName': 'test', 'baseUrl': 'https://user:password@example.invalid/v1'})

    def test_saved_submission_is_copied_before_legacy_mutation(self):
        source = self.root / 'saved'
        source.mkdir()
        (source / 'start.md').write_bytes(self.spec.read_bytes())
        (source / 'pyproject.toml').write_text('original metadata')
        def evaluator(result, task, enabled):
            self.assertEqual(result['generation_status'], 'reused')
            self.assertFalse(result['generation_performed'])
            (Path(result['workspace_path']) / 'pyproject.toml').unlink()
            return result
        with patch.object(runner, 'evaluate_result', side_effect=evaluator):
            runner.evaluate_saved_submission(source, 'replay', self.task)
        self.assertEqual((source / 'pyproject.toml').read_text(), 'original metadata')

    def test_saved_submission_rejects_wrong_task(self):
        source = self.root / 'saved'
        source.mkdir()
        (source / 'start.md').write_text('different task')
        with self.assertRaises(ValueError):
            runner.evaluate_saved_submission(source, 'replay', self.task)

    def test_all_backend_dispatch_routes(self):
        config = self.root / 'config.json'
        config.write_text(json.dumps({'backend': 'openhands'}))
        for backend, module, name in [('codex', codex, 'start_codex'),
                                      ('deepseek', deepseek, 'start_deepseek'),
                                      ('openhands', openhands_app, 'start_openhands')]:
            with patch('sys.argv', ['main.py', '--config', str(config), '--backend', backend]), \
                 patch.object(main.os, 'chdir'), \
                 patch.object(main.test_data_service, 'read_all_test_data'), \
                 patch.object(module, name, return_value=[]) as selected:
                self.assertEqual(main.main(), 0)
                selected.assert_called_once()
        self.assertEqual(main.BACKENDS, ('openhands', 'deepseek', 'codex'))

    def test_saved_main_route_never_launches_generation(self):
        source = self.root / 'saved'
        source.mkdir()
        config = self.root / 'config.json'
        config.write_text(json.dumps({'backend': 'codex', 'startPro': []}))
        with patch('sys.argv', ['main.py', '--config', str(config), '--saved-submission', str(source)]), \
             patch.object(main.os, 'chdir'), \
             patch.object(main.test_data_service, 'read_all_test_data'), \
             patch.object(runner, 'model_tasks', return_value=[({}, 'test-model', self.task)]), \
             patch.object(runner, 'evaluate_saved_submission', return_value={'status': 'completed'}) as replay, \
             patch.object(codex, 'start_codex', side_effect=AssertionError('Generation forbidden')):
            self.assertEqual(main.main(), 0)
            replay.assert_called_once()


if __name__ == '__main__':
    unittest.main()
