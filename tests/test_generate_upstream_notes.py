import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = PROJECT_ROOT / "scripts" / "generate_upstream_notes.py"


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={repo.as_posix()}", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


class PullRequestApi(BaseHTTPRequestHandler):
    responses: dict[str, tuple[int, object]] = {}

    def do_GET(self) -> None:
        status, payload = self.responses.get(self.path, (200, []))
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


class GenerateUpstreamNotesTest(unittest.TestCase):
    def test_cli_lists_pull_request_associated_with_commit_between_tags(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            run_git(repo, "init", "--initial-branch=main")
            run_git(repo, "config", "user.name", "Release Test")
            run_git(repo, "config", "user.email", "release-test@example.com")
            run_git(repo, "config", "commit.gpgsign", "false")

            (repo / "README.md").write_text("baseline\n", encoding="utf-8")
            run_git(repo, "add", "README.md")
            run_git(repo, "commit", "-m", "Baseline")
            run_git(repo, "tag", "v0.1.0")

            (repo / "workflow.yml").write_text("fork-only workflow\n", encoding="utf-8")
            run_git(repo, "add", "workflow.yml")
            run_git(repo, "commit", "-m", "Add release workflow")
            fork_only_commit = run_git(repo, "rev-parse", "HEAD")

            (repo / "README.md").write_text("upstream change\n", encoding="utf-8")
            run_git(repo, "commit", "-am", "Update README")
            changed_commit = run_git(repo, "rev-parse", "HEAD")
            run_git(repo, "tag", "v0.2.0")

            PullRequestApi.responses = {
                f"/repos/Pxx500/test/commits/{fork_only_commit}/pulls": (
                    404,
                    {"message": "No commit found for SHA"},
                ),
                f"/repos/Pxx500/test/commits/{changed_commit}/pulls": (
                    200,
                    [
                        {
                            "title": "Document the test repository",
                            "html_url": "https://github.com/Pxx500/test/pull/7",
                            "merged_at": "2026-07-31T12:00:00Z",
                            "user": {"login": "friend"},
                            "base": {"repo": {"full_name": "Pxx500/test"}},
                        }
                    ],
                ),
            }
            server = ThreadingHTTPServer(("127.0.0.1", 0), PullRequestApi)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        str(GENERATOR),
                        "--upstream",
                        "Pxx500/test",
                        "--previous-tag",
                        "v0.1.0",
                        "--current-tag",
                        "v0.2.0",
                        "--api-url",
                        f"http://127.0.0.1:{server.server_port}",
                    ],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                )
            finally:
                server.shutdown()
                server.server_close()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("## Upstream changes", result.stdout)
            self.assertTrue(result.stdout.startswith("* "), result.stdout)
            self.assertIn("Document the test repository", result.stdout)
            self.assertIn("@friend", result.stdout)
            self.assertIn("https://github.com/Pxx500/test/pull/7", result.stdout)


if __name__ == "__main__":
    unittest.main()
