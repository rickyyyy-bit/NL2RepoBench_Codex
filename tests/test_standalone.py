"""Exercise the standalone launcher and evaluator without model or Docker calls."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import main
import runner
from benchmark import evaluator
from codex_backend import runner as codex

ROOT = Path(__file__).resolve().parents[1]


class StandaloneTests(unittest.TestCase):
    def test_protocol_files_match_recorded_snapshot(self):
        manifest = json.loads((ROOT / 'docs/protocol-manifest.json').read_text())
        for relative, expected in manifest['sha256'].items():
            with self.subTest(path=relative):
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected)
        actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'test_files').rglob('*') if p.is_file()}
        self.assertEqual(actual, {p for p in manifest['sha256'] if p.startswith('test_files/')})

    def test_complete_launcher_pipeline_preserves_sources_and_records_install_failure(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'test_files/math-verify', root / 'test_files/math-verify')
            config = root / 'config.json'
            config.write_text(json.dumps({'evaluate': True, 'startPro': [{
                'moduleName': 'offline-model', 'baseUrl': 'https://example.invalid/v1',
                'reasoningEffort': 'medium', 'proNameList': ['math-verify']}]}))

            def generate(args, name, directory, timeout, env=None):
                workspace = directory / 'workspace'
                (workspace / 'implementation.py').write_text('VALUE = 42\n')
                (workspace / 'pyproject.toml').write_text('generated metadata\n')
                (directory / 'stdout.jsonl').write_text('{"type":"turn.completed"}\n')
                return {'generation_status': 'completed', 'exit_code': 0}

            def build(dockerfile, tag, host, logger):
                workspace = Path(dockerfile).parent / 'workspace'
                self.assertFalse((workspace / 'pyproject.toml').exists())
                self.assertEqual((workspace / 'implementation.py').read_text(), 'VALUE = 42\n')
                self.assertIn('nl2repobench/math-verify:1.0', Path(dockerfile).read_text())
                return 'sha256:offline-test-image'

            try:
                with patch('sys.argv', ['main.py', '--config', str(config)]), \
                     patch.object(main, '__file__', str(root / 'main.py')), \
                     patch.dict(os.environ, {'NL2REPO_API_KEY': 'offline-placeholder'}), \
                     patch.object(codex, 'image_info', return_value={'id': 'sha256:offline-image'}), \
                     patch.object(codex, 'run_container', side_effect=generate), \
                     patch.object(evaluator, 'build_test_image', side_effect=build), \
                     patch.object(evaluator, 'create_advanced_container', return_value=SimpleNamespace(id='offline')), \
                     patch.object(evaluator, 'execute_command_in_container', side_effect=[
                         (1, 'synthetic installation failure'), (1, '165 passed, 27 failed')]) as commands, \
                     patch.object(evaluator, 'stop_container'), patch.object(evaluator, 'remove_container'):
                    self.assertEqual(main.main(), 0)
                records = list((root / 'result').glob('*.json'))
                self.assertEqual(len(records), 1)
                result = json.loads(records[0].read_text())
                self.assertEqual(result['score'], 165)
                self.assertEqual(result['backend'], 'codex')
                self.assertEqual(result['evaluation_status'], 'completed')
                self.assertEqual([call.kwargs['command'] for call in commands.call_args_list],
                                 json.loads((root / 'test_files/math-verify/test_commands.json').read_text()))
                self.assertEqual(result['post_process_result']['test_results']['command_results'][0]['exit_code'], 1)
                self.assertTrue((Path(result['workspace_path']) / 'pyproject.toml').exists())
                self.assertFalse((Path(result['evaluation_workspace_path']) / 'pyproject.toml').exists())
                self.assertNotIn('offline-placeholder', records[0].read_text())
            finally:
                os.chdir(previous)

    def test_replay_runs_with_all_agent_imports_blocked(self):
        script = r'''
import importlib.abc, sys
class BlockAgents(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'codex_backend', 'deepseek', 'openhands'}:
            raise AssertionError('Agent import attempted: ' + fullname)
sys.meta_path.insert(0, BlockAgents())
from pathlib import Path
import json, os, tempfile
from types import SimpleNamespace
from unittest.mock import patch
import main, runner
sys.path.insert(0, str(Path.cwd()))
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    source = root / 'saved'
    source.mkdir()
    (source / 'code.py').write_text('VALUE = 42\n')
    spec = root / 'spec.md'
    spec.write_text('fixture task')
    task = SimpleNamespace(md=str(spec), proName='fixture')
    config = root / 'config.json'
    config.write_text('{}')
    os.chdir(root)
    with patch('sys.argv', ['main.py', '--config', str(config), '--saved-submission', str(source), '--submission-agent', 'agent-under-study']), patch.object(main, '__file__', str(root / 'main.py')), patch.object(main.test_data_service, 'read_all_test_data'), patch.object(runner, 'model_tasks', return_value=[({}, 'reported-model', task)]), patch('benchmark.evaluator.post_process_task', return_value={'status': 'success', 'pytest_results': {'passed': 1, 'total': 1}}):
        assert main.main() == 0
    result = json.loads(next((root / 'result').glob('*.json')).read_text())
    assert result['backend'] == 'agent-under-study'
    assert result['generation_performed'] is False
    assert result['score'] == 1
    assert (source / 'code.py').read_text() == 'VALUE = 42\n'
'''
        completed = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT,
                                   capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_failure_eligibility_and_skip_evaluation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'workspace').mkdir()
            task = SimpleNamespace(proName='fixture')
            for status, enabled in [('failed', True), ('error', True), ('completed', False)]:
                with self.subTest(status=status, enabled=enabled), \
                     patch.object(evaluator, 'post_process_task', side_effect=AssertionError('Must not grade')):
                    result = runner.evaluate_result({'status': status, 'workspace_path': str(root / 'workspace')}, task, enabled)
                    self.assertEqual(result['evaluation_status'], 'skipped')
                    self.assertIsNone(result['score'])


if __name__ == '__main__':
    unittest.main()
