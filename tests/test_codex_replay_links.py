"""Replay links must stay inside each copy, without modifying saved sources."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import runner


class ReplayLinkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)
        self.source = self.root / 'saved'
        (self.source / 'pkg').mkdir(parents=True)
        (self.source / 'pkg/module.py').write_text('VALUE = 42\n')
        self.task = SimpleNamespace(md=str(self.root / 'unused.md'), proName='example')

    def replay(self, name='replay'):
        # Keep both real copy operations; substitute only the Docker grader.
        outcome = {'status': 'success', 'pytest_results': {'passed': 0, 'total': 0}}
        with patch('openhands.post_processor.post_process_task', return_value=outcome):
            result = runner.evaluate_saved_submission(self.source, name, self.task)
        self.assertEqual(result['evaluation_status'], 'completed')
        self.assertFalse(result['generation_performed'])
        return Path(result['workspace_path']), Path(result['evaluation_workspace_path'])

    def test_absolute_file_and_directory_links_are_rebased_in_both_copies(self):
        file_link = self.source / 'absolute.py'
        directory_link = self.source / 'alias'
        file_link.symlink_to(self.source / 'pkg/module.py')
        directory_link.symlink_to(self.source / 'pkg', target_is_directory=True)
        original_targets = (file_link.readlink(), directory_link.readlink())
        workspace, evaluation = self.replay()
        for copy in (workspace, evaluation):
            for name in ('absolute.py', 'alias'):
                self.assertFalse((copy / name).readlink().is_absolute())
                self.assertTrue((copy / name).resolve().is_relative_to(copy))
            self.assertEqual((copy / 'absolute.py').read_text(), 'VALUE = 42\n')
            self.assertEqual((copy / 'alias/module.py').read_text(), 'VALUE = 42\n')
        (evaluation / 'absolute.py').write_text('VALUE = 99\n')
        self.assertEqual((workspace / 'absolute.py').read_text(), 'VALUE = 42\n')
        self.assertEqual(file_link.read_text(), 'VALUE = 42\n')
        self.assertEqual((file_link.readlink(), directory_link.readlink()), original_targets)

    def test_relative_and_chained_links_remain_self_contained(self):
        (self.source / 'absolute.py').symlink_to(self.source / 'pkg/module.py')
        (self.source / 'chain.py').symlink_to('absolute.py')
        (self.source / 'nested').mkdir()
        (self.source / 'nested/up.py').symlink_to('../pkg/module.py')
        # This resolves internally in the source but its literal spelling would
        # escape a differently named replay directory if copied unchanged.
        (self.source / 'roundtrip.py').symlink_to('../saved/pkg/module.py')
        workspace, evaluation = self.replay()
        for copy in (workspace, evaluation):
            for name in ('absolute.py', 'chain.py', 'nested/up.py', 'roundtrip.py'):
                self.assertEqual((copy / name).read_text(), 'VALUE = 42\n')
                self.assertTrue((copy / name).resolve().is_relative_to(copy))
        self.assertEqual((self.source / 'chain.py').readlink(), Path('absolute.py'))
        self.assertEqual((self.source / 'roundtrip.py').readlink(), Path('../saved/pkg/module.py'))

    def test_external_file_and_directory_links_are_rejected_before_copy(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'data.py').write_text('unchanged')
        link = self.source / 'external'
        for target in (outside / 'data.py', Path('../outside/data.py'), outside):
            with self.subTest(target=str(target)):
                link.symlink_to(target, target_is_directory=target == outside)
                with self.assertRaisesRegex(ValueError, 'outside its source directory'):
                    runner.evaluate_saved_submission(self.source, 'rejected', self.task)
                link.unlink()
                self.assertFalse((self.root / 'workspaces/rejected').exists())
        self.assertEqual((outside / 'data.py').read_text(), 'unchanged')

    def test_broken_links_are_rejected_before_copy(self):
        link = self.source / 'broken'
        for target in (self.source / 'missing.py', Path('missing.py')):
            with self.subTest(target=str(target)):
                link.symlink_to(target)
                with self.assertRaisesRegex(ValueError, 'broken or cyclic link'):
                    runner.evaluate_saved_submission(self.source, 'rejected', self.task)
                link.unlink()
                self.assertFalse((self.root / 'workspaces/rejected').exists())

    def test_link_cycles_are_rejected_before_copy(self):
        (self.source / 'a').symlink_to('b')
        (self.source / 'b').symlink_to('a')
        with self.assertRaisesRegex(ValueError, 'broken or cyclic link'):
            runner.evaluate_saved_submission(self.source, 'rejected', self.task)
        self.assertFalse((self.root / 'workspaces/rejected').exists())

    def test_replays_remain_independent_of_source_and_one_another(self):
        (self.source / 'absolute.py').symlink_to(self.source / 'pkg/module.py')
        first, _ = self.replay('first')
        second, _ = self.replay('second')
        (second / 'absolute.py').write_text('second only')
        self.assertEqual((first / 'absolute.py').read_text(), 'VALUE = 42\n')
        self.assertEqual((self.source / 'absolute.py').read_text(), 'VALUE = 42\n')
        self.source.rename(self.root / 'source-not-available')
        self.assertEqual((first / 'absolute.py').read_text(), 'VALUE = 42\n')


if __name__ == '__main__':
    unittest.main()
