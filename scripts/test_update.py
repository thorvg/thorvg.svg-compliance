import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image


SPEC = importlib.util.spec_from_file_location("update", Path(__file__).with_name("update.py"))
update = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update)


class UpdateTest(unittest.TestCase):
    def test_chrome_baseline_survives_reference_rendering_and_rejects_stale_sources(self):
        suite = next(s for s in update.CONFIG["suites"] if s["id"] == "wpt-svg2-reftests")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "test.svg"
            source.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            image = root / "baselines/test.skia-123.png"
            image.parent.mkdir()
            Image.new("RGB", (10, 10), "black").save(image)
            metadata = [{"id": suite["id"], "revision": "pinned"}]
            (image.parent / "index.json").write_text(json.dumps({
                "chrome_version": "153", "skia_revision": "123",
                "revisions": {suite["id"]: "pinned"},
                "tests": {f"{suite['id']}/test.svg": {
                    "image": "baselines/test.skia-123.png", "source_sha256": update.sha256(source),
                    "suitability": "suitable", "reason": "Repeated Chrome captures agree.",
                }},
            }))
            record = {
                "suite": suite["id"], "test": "test.svg", "_key": "test", "resolution": [10, 10], "elements": [],
                "_source_path": source, "_reference_svg": root / "ref.svg",
            }

            def render(requests, tool, environment):
                self.assertEqual(list(requests), [(str(source), (10, 10))])
                for destinations in requests.values():
                    for destination in destinations:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        Image.new("RGB", (10, 10), "black").save(destination)
                return {}

            with patch.object(update, "ROOT", root), patch.object(update, "CACHE", root / "cache"):
                update.apply_baselines([record], metadata)
                with patch.object(update, "render_requests", render):
                    _, results = update.finalize([record], {suite["id"]: suite}, root, None)
                self.assertEqual(results[0]["status"], "PASS")
                self.assertEqual(results[0]["reference_image"], "baselines/test.skia-123.png")
                self.assertEqual(results[0]["reference_renderer"], "Chrome 153 / Skia 123")
                self.assertEqual(results[0]["baseline_suitability"], "suitable")
                record.update(baseline_suitability="unsuitable", baseline_reason="Unstable recursive rendering.")
                with patch.object(update, "render_requests", render):
                    _, skipped = update.finalize([record], {suite["id"]: suite}, root, None)
                self.assertEqual(skipped[0]["status"], "SKIP")
                self.assertEqual(skipped[0]["visual_status"], "SKIP")
                self.assertEqual(skipped[0]["issue_type"], "unsuitable-baseline")
                self.assertEqual(skipped[0]["reason"], "Unstable recursive rendering.")
                self.assertEqual(skipped[0]["mae"], 0)
                _, summary = update.write_data(skipped, {suite["id"]: suite}, [
                    {**metadata[0], "index": "README.md"},
                ], {})
                self.assertEqual([summary["suites"][0][k] for k in ("total", "pass", "fail", "skip")], [1, 0, 0, 1])
                with self.assertRaisesRegex(RuntimeError, "needs review"):
                    update.apply_baselines([record], [{"id": suite["id"], "revision": "new"}])
                record["resolution"] = [20, 20]
                with self.assertRaisesRegex(RuntimeError, "dimension mismatch"):
                    update.apply_baselines([record], metadata)
                source.write_text("changed")
                with self.assertRaisesRegex(RuntimeError, "needs review"):
                    update.apply_baselines([record], metadata)

    def test_installed_converter_skips_source_fetch_and_build(self):
        with tempfile.TemporaryDirectory() as directory:
            tool = Path(directory) / "tvg-svg2png"
            args = SimpleNamespace(svg2png=tool)
            with patch.object(update, "ensure_git_repo") as fetch, patch.object(update, "build_thorvg") as build:
                with self.assertRaisesRegex(RuntimeError, "Not an executable"):
                    update.prepare_renderer(args)
                tool.write_text("#!/bin/sh\nexit 0\n")
                tool.chmod(0o755)
                selected, info = update.prepare_renderer(args)
                self.assertEqual(selected, tool.resolve())
                self.assertEqual(info["converter_sha256"], update.sha256(tool))
                self.assertIsNone(info["commit"])
                fetch.assert_not_called()
                build.assert_not_called()

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
