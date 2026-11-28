"""Tests for immutable repository snapshot and patch validation boundaries."""
import tempfile
import unittest
from pathlib import Path

from src.dispatcher.repository_guard import (
    RepositoryAccessRejected,
    RepositorySnapshot,
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

    def test_nul_and_empty_patch_rejected(self):
        for content in ("", "a" + chr(0) + "b"):
            with self.subTest(content=content), self.assertRaises(RepositoryAccessRejected):
                validate_patch(
                    path="file.txt", content=content,
                    current_content=None, expected_blob_sha=None,
                )


if __name__ == "__main__":
    unittest.main()
