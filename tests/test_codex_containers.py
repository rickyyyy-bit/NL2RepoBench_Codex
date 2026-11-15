"""Exercise lifecycle failures without starting or removing real containers."""
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from codex_backend import containers


class CodexContainerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.owned_id = 'a' * 64

    def docker_command(self, args, **kwargs):
        if args[0] == 'create':
            Path(args[args.index('--cidfile') + 1]).write_text(self.owned_id)
            return SimpleNamespace(stdout=self.owned_id, stderr='')
        if args[0] == 'inspect':
            return SimpleNamespace(stdout=json.dumps([{'State': {
                'Running': False, 'Status': 'exited', 'ExitCode': 0, 'OOMKilled': False, 'Error': ''}}]))
        if args[0] == 'stop':
            return SimpleNamespace(stdout='', stderr='')
        raise AssertionError('Unexpected Docker operation')

    def test_success_removes_only_the_created_id(self):
        with patch.object(containers, 'docker_command', side_effect=self.docker_command), \
             patch.object(containers.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run:
            result = containers.run_container(['offline-image'], 'offline-name', self.directory, 1)
        self.assertEqual(result['generation_status'], 'completed')
        self.assertEqual(run.call_args_list[-1].args[0], ['docker', 'rm', '--force', self.owned_id])

    def test_failed_creation_does_not_remove_a_container_by_name(self):
        failure = subprocess.CalledProcessError(1, ['docker', 'create'], stderr='invalid image')
        with patch.object(containers, 'docker_command', side_effect=failure), \
             patch.object(containers.subprocess, 'run') as run:
            result = containers.run_container(['offline-image'], 'existing-name', self.directory, 1)
        self.assertEqual(result['generation_status'], 'error')
        run.assert_not_called()

    def test_timeout_stays_timeout_even_if_stopped_container_exits_zero(self):
        with patch.object(containers, 'docker_command', side_effect=self.docker_command), \
             patch.object(containers.subprocess, 'run', side_effect=[
                 subprocess.TimeoutExpired(['docker', 'start'], 1), SimpleNamespace(returncode=0)]):
            result = containers.run_container(['offline-image'], 'offline-name', self.directory, 1)
        self.assertEqual(result['generation_status'], 'timeout')
        self.assertEqual(result['exit_code'], 0)

    def test_cleanup_failure_is_reported(self):
        with patch.object(containers, 'docker_command', side_effect=self.docker_command), \
             patch.object(containers.subprocess, 'run', side_effect=[
                 SimpleNamespace(returncode=0), SimpleNamespace(returncode=1)]):
            result = containers.run_container(['offline-image'], 'offline-name', self.directory, 1)
        self.assertIn('cleanup_error', result)


if __name__ == '__main__':
    unittest.main()
