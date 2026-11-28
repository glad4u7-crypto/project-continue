"""Tests for immutable repository snapshot and patch validation boundaries."""
import tempfile
import unittest
from pathlib import Path

from src.dispatcher.repository_guard import (
    RepositoryAccessRejected,
    RepositorySnapshot,
    assert_pull_request_ready,
    build_pull_request_body,
    prepare_patch,
    summarize_diff,
    validate_patch,
    validate_target_branch,
)

SHA = "a" * 40


class RepositoryGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "README.md").write_text("hello", encoding="utf-8")
        (self.root / "config.json").write_text('{"ok": true}', encoding="utf-8")
        (self.root / "notes.txt").write_text("notes", encoding="utf-8")
        (self.root / ".env").write_text("SECRET=hidden", encoding="utf-8")
        self.snapshot = RepositorySnapshot(self.root, SHA)

    def tearDown(self):
        self.temp.cleanup()

    def test_read_file_is_bound_to_exact_commit_and_reports_hash(self):
        item = self.snapshot.read_file("README.md", expected_commit_sha=SHA)
        self.assertEqual(item.content, "hello")
        self.assertEqual(item.commit_sha, SHA)
        self.assertEqual(len(item.sha256), 64)
        with self.assertRaises(RepositoryAccessRejected):
            self.snapshot.read_file("README.md", expected_commit_sha="b" * 40)

    def test_tree_listing_excludes_hidden_and_disallowed_files(self):
        entries = self.snapshot.list_tree(expected_commit_sha=SHA)
        self.assertIn("README.md", entries)
        self.assertIn("config.json", entries)
        self.assertNotIn(".env", entries)

    def test_subdirectory_tree_listing_is_supported(self):
        nested = self.root / "src" / "dispatcher"
        nested.mkdir(parents=True)
        (nested / "runtime.py").write_text("pass", encoding="utf-8")
        self.assertEqual(
            self.snapshot.list_tree(expected_commit_sha=SHA, path="src/dispatcher"),
            ("src/dispatcher/runtime.py",),
        )

    def test_path_traversal_absolute_hidden_and_backslash_rejected(self):
        for path in ("../README.md", "/etc/passwd", ".env", "folder/.secret", "a\\b.py"):
            with self.subTest(path=path), self.assertRaises(RepositoryAccessRejected):
                self.snapshot.read_file(path, expected_commit_sha=SHA)

    def test_sensitive_extensions_and_unknown_extensions_rejected(self):
        for path in ("secret.pem", "state.sqlite3", "book.ipynb", "binary.exe"):
            with self.subTest(path=path), self.assertRaises(RepositoryAccessRejected):
                validate_patch(path=path, content="x", current_content=None, expected_blob_sha=None)

    def test_symlink_is_not_followed(self):
        outside = self.root.parent / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        (self.root / "linked.txt").symlink_to(outside)
        with self.assertRaises(RepositoryAccessRejected):
            self.snapshot.read_file("linked.txt", expected_commit_sha=SHA)

    def test_invalid_utf8_and_oversized_files_rejected(self):
        (self.root / "bad.txt").write_bytes(bytes([0xff]))
        with self.assertRaises(RepositoryAccessRejected):
            self.snapshot.read_file("bad.txt", expected_commit_sha=SHA)
        (self.root / "large.txt").write_bytes(b"x" * (256 * 1024 + 1))
        with self.assertRaises(RepositoryAccessRejected):
            self.snapshot.read_file("large.txt", expected_commit_sha=SHA)

    def test_branch_and_base_sha_guard(self):
        validate_target_branch(
            target_branch="phase20/patch-01", base_branch="main",
            observed_base_sha=SHA, expected_base_sha=SHA,
        )
        for target in ("main", "master", "docs/plan"):
            with self.subTest(target=target), self.assertRaises(RepositoryAccessRejected):
                validate_target_branch(
                    target_branch=target, base_branch="main",
                    observed_base_sha=SHA, expected_base_sha=SHA,
                )
        validate_target_branch(
            target_branch="feature/patch", base_branch="main",
            observed_base_sha=SHA, expected_base_sha=SHA,
        )
        with self.assertRaises(RepositoryAccessRejected):
            validate_target_branch(
                target_branch="phase20/patch-02", base_branch="main",
                observed_base_sha="b" * 40, expected_base_sha=SHA,
            )

    def test_patch_creation_and_overwrite_require_correct_blob_sha(self):
        created = validate_patch(
            path="new.md", content="draft", current_content=None, expected_blob_sha=None
        )
        self.assertEqual(created.size_bytes, 5)
        with self.assertRaises(RepositoryAccessRejected):
            validate_patch(
                path="new.md", content="draft", current_content="old", expected_blob_sha=None
            )
        old = validate_patch(
            path="new.md", content="old", current_content=None, expected_blob_sha=None
        )
        updated = validate_patch(
            path="new.md", content="new", current_content="old",
            expected_blob_sha=old.new_blob_sha,
        )
        self.assertEqual(updated.previous_blob_sha, old.new_blob_sha)
        with self.assertRaises(RepositoryAccessRejected):
            validate_patch(
                path="new.md", content="new", current_content="old",
                expected_blob_sha="c" * 40,
            )

    def test_json_and_secret_content_validation(self):
        for content in ("{broken", "-----BEGIN RSA PRIVATE KEY-----"):
            with self.subTest(content=content), self.assertRaises(RepositoryAccessRejected):
                validate_patch(
                    path="file.json" if content.startswith("{") else "file.txt",
                    content=content, current_content=None, expected_blob_sha=None,
                )

    def test_overwrite_requires_exact_current_blob_sha_and_stale_sha_fails_closed(self):
        old = "before\\n"
        correct_sha = validate_patch(
            path="README.md", content=old, current_content=None, expected_blob_sha=None
        ).new_blob_sha
        prepared = prepare_patch(
            target_branch="phase20/change-01", base_branch="main",
            observed_base_sha=SHA, expected_base_sha=SHA,
            path="README.md", new_content="after\\n",
            current_content=old, expected_blob_sha=correct_sha,
        )
        self.assertEqual(prepared.previous_blob_sha, correct_sha)
        with self.assertRaises(RepositoryAccessRejected):
            prepare_patch(
                target_branch="phase20/change-01", base_branch="main",
                observed_base_sha=SHA, expected_base_sha=SHA,
                path="README.md", new_content="after\\n",
                current_content=old, expected_blob_sha="b" * 40,
            )

    def test_stale_base_sha_and_main_direct_write_are_blocked(self):
        for branch in ("main", "master"):
            with self.subTest(branch=branch), self.assertRaises(RepositoryAccessRejected):
                prepare_patch(
                    target_branch=branch, base_branch="main",
                    observed_base_sha=SHA, expected_base_sha=SHA,
                    path="README.md", new_content="x",
                    current_content=None, expected_blob_sha=None,
                )
        with self.assertRaises(RepositoryAccessRejected):
            prepare_patch(
                target_branch="phase20/change-02", base_branch="main",
                observed_base_sha="b" * 40, expected_base_sha=SHA,
                path="README.md", new_content="x",
                current_content=None, expected_blob_sha=None,
            )

    def test_diff_review_reports_line_additions_deletions_and_blob_hashes(self):
        diff = summarize_diff(
            path="README.md", old_content="one" + chr(10) + "two" + chr(10),
            new_content="one" + chr(10) + "three" + chr(10) + "four" + chr(10),
        )
        self.assertEqual(diff.additions, 2)
        self.assertEqual(diff.deletions, 1)
        self.assertEqual(len(diff.new_blob_sha), 40)
        with self.assertRaises(RepositoryAccessRejected):
            summarize_diff(
                path="README.md", old_content="old", new_content="new",
                old_blob_sha="c" * 40,
            )

    def test_pr_body_contains_diff_risk_rollback_tests_and_exact_refs(self):
        diff = summarize_diff(path="README.md", old_content="old", new_content="new")
        body = build_pull_request_body(
            summary="Guard repository writes",
            risk="Path and stale SHA validation only",
            rollback="Revert the feature branch commit",
            test_results="Compile PASS; focused PASS; full PASS",
            changed_files=(diff,), base_sha=SHA, head_sha="b" * 40,
        )
        for token in ("Reviewed changes", "Risk assessment", "Rollback", "Test evidence", SHA, "b" * 40):
            self.assertIn(token, body)
        with self.assertRaises(RepositoryAccessRejected):
            build_pull_request_body(
                summary="", risk="risk", rollback="rollback", test_results="tests",
                changed_files=(diff,), base_sha=SHA, head_sha="b" * 40,
            )

    def test_pr_creation_gate_requires_green_compile_and_test_suites(self):
        diff = summarize_diff(path="README.md", old_content="old", new_content="new")
        args = dict(
            target_branch="phase20/change-03", base_branch="main",
            base_sha=SHA, head_sha="b" * 40, diff=(diff,),
            compile_passed=True, focused_tests_passed=True, full_tests_passed=True,
        )
        assert_pull_request_ready(**args)
        with self.assertRaises(RepositoryAccessRejected):
            assert_pull_request_ready(**{**args, "full_tests_passed": False})
        with self.assertRaises(RepositoryAccessRejected):
            assert_pull_request_ready(**{**args, "target_branch": "main"})

    def test_nul_and_empty_patch_rejected(self):
        for content in ("", "a" + chr(0) + "b"):
            with self.subTest(content=content), self.assertRaises(RepositoryAccessRejected):
                validate_patch(
                    path="file.txt", content=content,
                    current_content=None, expected_blob_sha=None,
                )


if __name__ == "__main__":
    unittest.main()
