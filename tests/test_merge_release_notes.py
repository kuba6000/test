import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MERGER = PROJECT_ROOT / "scripts" / "merge_release_notes.py"


class MergeReleaseNotesTest(unittest.TestCase):
    def test_cli_adds_upstream_entries_to_existing_whats_changed_section(self) -> None:
        native_notes = """## What's Changed
* Local change by @local in https://github.com/fork/repo/pull/1

## New Contributors
* @local made their first contribution in https://github.com/fork/repo/pull/1

**Full Changelog**: https://github.com/fork/repo/compare/v1...v2
"""
        upstream_entries = (
            "* Upstream change by @upstream in "
            "https://github.com/upstream/repo/pull/7\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            native_file = temp / "native.md"
            upstream_file = temp / "upstream.md"
            native_file.write_text(native_notes, encoding="utf-8")
            upstream_file.write_text(upstream_entries, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(MERGER), str(native_file), str(upstream_file)],
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("## What's Changed"), 1)
        self.assertNotIn("## Upstream changes", result.stdout)
        self.assertLess(result.stdout.index("* Local change"), result.stdout.index("* Upstream change"))
        self.assertLess(result.stdout.index("* Upstream change"), result.stdout.index("## New Contributors"))
        self.assertIn("**Full Changelog**", result.stdout)

    def test_cli_creates_whats_changed_section_when_fork_has_no_pull_requests(self) -> None:
        native_notes = (
            "**Full Changelog**: "
            "https://github.com/fork/repo/compare/v1...v2\n"
        )
        upstream_entries = (
            "* Upstream-only change by @upstream in "
            "https://github.com/upstream/repo/pull/8\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            native_file = temp / "native.md"
            upstream_file = temp / "upstream.md"
            native_file.write_text(native_notes, encoding="utf-8")
            upstream_file.write_text(upstream_entries, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(MERGER), str(native_file), str(upstream_file)],
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("## What's Changed"), 1)
        self.assertLess(result.stdout.index("## What's Changed"), result.stdout.index("* Upstream-only change"))
        self.assertLess(result.stdout.index("* Upstream-only change"), result.stdout.index("**Full Changelog**"))

    def test_cli_inserts_before_full_changelog_when_new_contributors_is_absent(self) -> None:
        native_notes = """## What's Changed
* Local change by @local in https://github.com/fork/repo/pull/2

**Full Changelog**: https://github.com/fork/repo/compare/v2...v3
"""
        upstream_entries = (
            "* Another upstream change by @upstream in "
            "https://github.com/upstream/repo/pull/9\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            native_file = temp / "native.md"
            upstream_file = temp / "upstream.md"
            native_file.write_text(native_notes, encoding="utf-8")
            upstream_file.write_text(upstream_entries, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(MERGER), str(native_file), str(upstream_file)],
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("## What's Changed"), 1)
        self.assertLess(result.stdout.index("* Local change"), result.stdout.index("* Another upstream change"))
        self.assertLess(result.stdout.index("* Another upstream change"), result.stdout.index("**Full Changelog**"))


if __name__ == "__main__":
    unittest.main()
