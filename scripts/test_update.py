import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from PIL import Image


SPEC = importlib.util.spec_from_file_location("update", Path(__file__).with_name("update.py"))
update = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update)


class UpdateTest(unittest.TestCase):
    def test_failed_command_prints_diagnostics(self):
        output = io.StringIO()
        command = [sys.executable, "-c", "import sys; print('build output'); print('compiler error', file=sys.stderr); sys.exit(7)"]
        with redirect_stderr(output), self.assertRaises(subprocess.CalledProcessError) as raised:
            update.run(command)
        self.assertEqual(raised.exception.returncode, 7)
        self.assertIn("build output", output.getvalue())
        self.assertIn("compiler error", output.getvalue())
        output = io.StringIO()
        with redirect_stderr(output):
            result = update.run(command, check=False)
        self.assertEqual(result.returncode, 7)
        self.assertIn("compiler error", result.stdout)
        self.assertEqual(output.getvalue(), "")

    def test_bundled_and_separate_converter_builds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, cli_tools = root / "thorvg", root / "cli-tools"
            executable = "tvg-svg2png.exe" if update.os.name == "nt" else "tvg-svg2png"
            library_build, cli_build = root / "thorvg-build", root / "cli-tools-build"
            for build in (library_build, cli_build):
                (build / "meson-private").mkdir(parents=True)
                (build / "meson-private/coredata.dat").touch()
                (build / executable).touch()
            with patch.object(update, "CACHE", root), patch.object(update, "run") as run:
                self.assertEqual(update.build_thorvg(source), library_build / executable)
                self.assertIn("-Dtools=svg2png", run.call_args_list[0].args[0])
                run.assert_called_with(["meson", "compile", "-C", library_build, "tvg-svg2png"])
                run.reset_mock()
                self.assertEqual(update.build_thorvg(source, cli_tools), cli_build / executable)
                self.assertNotIn("-Dtools=svg2png", run.call_args_list[0].args[0])
                self.assertEqual(run.call_args_list[1].args[0], ["meson", "compile", "-C", library_build])
                setup = run.call_args_list[2].args[0]
                self.assertIn(f"--pkg-config-path={library_build / 'meson-uninstalled'}", setup)
                self.assertIn("--clearcache", setup)
                run.assert_called_with(["meson", "compile", "-C", cli_build, "tvg-svg2png"])

    def test_wpt_static_svg_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "svg"
            root.mkdir()
            (root / "ref.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')
            (root / "test.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" xmlns:h="http://www.w3.org/1999/xhtml"><h:link rel="match" href="ref.svg"/><circle/></svg>')
            self.assertEqual(len(update.wpt_pairs(root)), 1)
            (root / "test.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" xmlns:h="http://www.w3.org/1999/xhtml"><h:link rel="match" href="ref.svg"/><animate/></svg>')
            self.assertEqual(update.wpt_pairs(root), [])

    def test_aa_comparison_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            reference, rendered, diff = directory / "a.png", directory / "b.png", directory / "d.png"
            Image.new("RGB", (10, 10), "white").save(reference)
            Image.new("RGB", (10, 10), "white").save(rendered)
            metrics = update.compare_images(reference, rendered, diff, {"blur_radius": 0.6, "channel_delta": 24})
            self.assertEqual(metrics["changed_ratio"], 0)
            self.assertEqual(metrics["mae"], 0)
            self.assertTrue(diff.exists())

    def test_result_classification(self):
        suite = next(suite for suite in update.CONFIG["suites"] if suite["id"] == "resvg-test-suite")
        cases = [
            ("match", "feFlood", "PASS", "none"),
            ("mismatch", "marker", "FAIL", "visual-mismatch"),
            ("text-match", "textPath", "PASS", "none"),
            ("text-mismatch", "text", "FAIL", "visual-mismatch"),
            ("error", "feFlood", "FAIL", "render-error"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.png"
            Image.new("RGB", (10, 10), "white").save(reference)
            records = [{
                "suite": suite["id"], "test": f"{name}.svg", "elements": [element],
                "resolution": [10, 10], "_key": name, "_source_path": root / f"{name}.svg",
                "_reference_path": reference,
            } for name, element, *_ in cases]

            def render(requests, tool, environment):
                errors = {}
                for key, destinations in requests.items():
                    name = Path(key[0]).stem
                    if name == "error":
                        errors[key] = "render failed"
                        continue
                    for destination in destinations:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        Image.new("RGB", key[1], "white" if name in {"match", "text-match"} else "black").save(destination)
                return errors

            with patch.object(update, "CACHE", root), patch.object(update, "render_requests", render):
                _, results = update.finalize(records, {suite["id"]: suite}, root, None)
                _, summary = update.write_data(results, {suite["id"]: suite}, [{
                    "id": suite["id"], "index": "README.md", "revision": "test",
                }], {})
            by_test = {row["test"]: row for row in results}
            for name, _, status, issue in cases:
                with self.subTest(name=name):
                    row = by_test[f"{name}.svg"]
                    self.assertEqual((row["status"], row["visual_status"], row["issue_type"]), (status, status, issue))
            counts = summary["suites"][0]
            self.assertEqual([counts[key] for key in ("total", "pass", "fail")], [5, 2, 3])


if __name__ == "__main__":
    unittest.main()
