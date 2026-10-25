import contextlib
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gitjam as gj  # noqa: E402


class LevelTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def make(self, n):
        path = os.path.join(self.tmp, f"level-{n}")
        gj.LEVELS[n]["setup"](path)
        return path

    def test_unsolved_levels_fail(self):
        for n in sorted(gj.LEVELS):
            with self.subTest(level=n):
                ok, _ = gj.LEVELS[n]["check"](self.make(n))
                self.assertFalse(ok)

    def test_generated_repos_do_not_inherit_git_hooks(self):
        p = self.make(1)
        hooks_path = gj.git(p, "config", "--get", "core.hooksPath")
        self.assertEqual(hooks_path, os.path.join(p, ".git", "gitjam-hooks"))

    def test_level_1_solution(self):
        p = self.make(1)
        gj.git(p, "branch", "-f", "feature", "main")
        gj.git(p, "reset", "-q", "--hard", "HEAD~1")
        self.assertTrue(gj.check_1(p)[0])

    def test_level_2_solution(self):
        p = self.make(2)
        gj.git(p, "switch", "-c", "rescue")
        self.assertTrue(gj.check_2(p)[0])

    def test_level_3_solution(self):
        p = self.make(3)
        gj.git(p, "reset", "-q", "--hard", "HEAD@{1}")
        self.assertTrue(gj.check_3(p)[0])

    def test_level_4_solution(self):
        p = self.make(4)
        gj.write(p, "greeting.txt", "hello\nfrom main\nfrom feature\n")
        gj.git(p, "add", "greeting.txt")
        gj.git(p, "commit", "-q", "-m", "Merge feature")
        self.assertTrue(gj.check_4(p)[0])

    def test_level_5_solution(self):
        p = self.make(5)
        bad = gj.git(p, "log", "--format=%H", "--grep=Oops bad config")
        gj.git(p, "revert", "--no-edit", bad)
        self.assertTrue(gj.check_5(p)[0])

    def test_level_5_rewriting_history_fails(self):
        p = self.make(5)
        gj.git(p, "reset", "-q", "--hard", "HEAD~2")
        self.assertFalse(gj.check_5(p)[0])

    def test_cli_start_and_check(self):
        old = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, old)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(gj.main(["start", "2"]), 0)
            repo = os.path.join(self.tmp, gj.PLAY_DIR, "level-2")
            self.assertTrue(os.path.isdir(repo))
            self.assertEqual(gj.main(["check", repo]), 1)
            gj.git(repo, "switch", "-c", "rescue")
            self.assertEqual(gj.main(["check", repo]), 0)
        self.assertIn("PASS", out.getvalue())

    def test_check_from_subdirectory(self):
        p = self.make(2)
        gj.write(gj.git_dir(p), gj.LEVEL_FILE, "2")
        nested = os.path.join(p, "nested")
        os.mkdir(nested)
        self.assertEqual(gj.find_repo(nested), p)

    def test_invalid_level_metadata_is_reported(self):
        p = self.make(2)
        gj.write(os.path.join(p, ".git"), gj.LEVEL_FILE, "99")
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(gj.main(["check", p]), 1)
        self.assertIn("Unknown gitjam level", err.getvalue())

    def test_cli_rejects_extra_arguments(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(gj.main(["list", "unexpected"]), 2)
        self.assertIn("Too many arguments", out.getvalue())


if __name__ == "__main__":
    unittest.main()
