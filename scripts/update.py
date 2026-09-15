#!/usr/bin/env python3
"""Fetch the public corpora, render them with ThorVG, and publish the static report."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, ImageChops, ImageFilter, ImageStat


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
CONFIG = json.loads((ROOT / "config/suites.json").read_text())
W3C_DYNAMIC = re.compile(
    r"<(?:animate|animateColor|animateMotion|animateTransform|set|discard|mpath|"
    r"script|handler|listener|audio|video|animation)\b",
    re.I,
)
WPT_DYNAMIC = re.compile(
    r"<(?:[\w.-]+:)?(?:script|animate|animateColor|animateMotion|animateTransform|"
    r"set|discard|mpath)\b",
    re.I,
)
LINK = re.compile(r"<(?:[\w.-]+:)?link\b[^>]*>", re.I)
ATTRIBUTE = re.compile(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.S)
TAG = re.compile(r"<\s*(?!/|!|\?)(?:[\w.-]+:)?([A-Za-z_][\w.-]*)\b")
VISIBLE_ELEMENTS = {
    "a", "animation", "audio", "circle", "clipPath", "defs", "ellipse", "filter",
    "foreignObject", "g", "image", "line", "linearGradient", "marker", "mask", "path",
    "pattern", "polygon", "polyline", "radialGradient", "rect", "script", "stop", "style",
    "svg", "switch", "symbol", "text", "textPath", "tspan", "use", "video",
    "animate", "animateColor", "animateMotion", "animateTransform", "discard", "handler",
    "listener", "mpath", "set", "feBlend", "feColorMatrix", "feComponentTransfer",
    "feComposite", "feConvolveMatrix", "feDiffuseLighting", "feDisplacementMap",
    "feDistantLight", "feDropShadow", "feFlood", "feFuncA", "feFuncB", "feFuncG",
    "feFuncR", "feGaussianBlur", "feImage", "feMerge", "feMergeNode", "feMorphology",
    "feOffset", "fePointLight", "feSpecularLighting", "feSpotLight", "feTile", "feTurbulence",
}


def run(command, cwd=None, env=None, check=True):
    print("+", " ".join(map(str, command)))
    try:
        return subprocess.run(
            list(map(str, command)), cwd=cwd, env=env, check=check,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout.rstrip(), file=sys.stderr)
        raise


def git(path, *args):
    return run(["git", "-C", path, *args]).stdout.strip()


def ensure_git_repo(name, url, ref, sparse=None, offline=False):
    destination = CACHE / name
    if not (destination / ".git").exists():
        if offline:
            raise RuntimeError(f"Missing offline cache: {destination}")
        run(["git", "clone", "--filter=blob:none", "--no-checkout", url, destination])
    if not offline:
        run(["git", "-C", destination, "fetch", "--depth=1", "origin", ref])
        run(["git", "-C", destination, "checkout", "--detach", "FETCH_HEAD"])
    if sparse:
        run(["git", "-C", destination, "sparse-checkout", "set", *sparse])
    return destination


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_w3c(suite, offline=False):
    extracted = CACHE / suite["id"]
    if len(list((extracted / "svg").glob("*.svg"))) == 496:
        return extracted
    archive = CACHE / "downloads" / Path(suite["archive_url"]).name
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists() or sha256(archive) != suite["archive_sha256"]:
        if offline:
            raise RuntimeError(f"Missing offline archive: {archive}")
        print(f"Downloading {suite['archive_url']}")
        urllib.request.urlretrieve(suite["archive_url"], archive)
    if sha256(archive) != suite["archive_sha256"]:
        raise RuntimeError(f"Checksum mismatch: {archive}")
    temporary = CACHE / f".{suite['id']}-extract"
    shutil.rmtree(temporary, ignore_errors=True)
    temporary.mkdir(parents=True)
    with tarfile.open(archive) as source:
        source.extractall(temporary, filter="data")
    for path in temporary.rglob("*"):
        path.chmod(path.stat().st_mode | 0o600 | (0o100 if path.is_dir() else 0))
    shutil.rmtree(extracted, ignore_errors=True)
    temporary.rename(extracted)
    return extracted


def copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source, destination):
    if source.exists():
        shutil.copytree(source, destination, dirs_exist_ok=True)


def read_svg(path):
    return path.read_text(encoding="utf-8", errors="ignore")


def without_w3c_revision(svg):
    # Remove only the pinned suite's Revision text, preserving other content and the original encoding.
    encoding = "utf-16-le" if svg.startswith(b"\xff\xfe") else "utf-16-be" if svg.startswith(b"\xfe\xff") else "latin1"
    return re.sub(r'[ \t]*<text\b(?=[^>]*\s(?:xml:)?id\s*=\s*(["\'])revision\1)[^>]*>.*?</text\s*>[ \t]*(?:\r?\n)?', "", svg.decode(encoding), flags=re.S).encode(encoding)


def elements(text):
    found = [tag for tag in TAG.findall(text) if tag in VISIBLE_ELEMENTS]
    return sorted(set(found), key=lambda value: value.lower())


def title(text, fallback):
    match = re.search(r"<title\b[^>]*>(.*?)</title>", text, re.I | re.S)
    if not match:
        return fallback
    value = re.sub(r"<[^>]+>", "", match.group(1))
    return html.unescape(" ".join(value.split())) or fallback


def image_size(path):
    with Image.open(path) as image:
        return image.size


def feature_path(path):
    parts = [part for part in path.parent.parts if part not in {"reftests", "reference", "support"}]
    return "/".join(parts[:2]) if parts else "root"


def wpt_pairs(root):
    pairs = []
    for test in root.rglob("*.svg"):
        if "print" in test.name.lower() or "print" in test.relative_to(root).parts:
            continue
        text = read_svg(test)
        for link in LINK.findall(text):
            attrs = {key.lower(): value for key, _, value in ATTRIBUTE.findall(link)}
            if attrs.get("rel", "").lower() != "match":
                continue
            href = urlsplit(attrs.get("href", "")).path
            reference = ((root.parent / href.lstrip("/")) if href.startswith("/") else (test.parent / href)).resolve()
            try:
                reference.relative_to(root.resolve())
            except ValueError:
                continue
            if reference.suffix.lower() != ".svg" or not reference.is_file():
                continue
            if WPT_DYNAMIC.search(text) or WPT_DYNAMIC.search(read_svg(reference)):
                continue
            pairs.append((test, reference))
    return pairs


def base_record(suite, relative, source, source_url, title_text, source_elements, resolution):
    key = relative.with_suffix("").as_posix()
    return {
        "suite": suite["id"], "suite_name": suite["name"], "track": suite["track"],
        "spec": suite["spec"], "test": relative.as_posix(), "title": title_text,
        "elements": source_elements, "resolution": list(resolution), "upstream": source_url,
        "source": source, "_key": key,
    }


def prepare_corpora(suites, sources):
    destination = CACHE / "corpora-next"
    shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True)
    records, metadata = [], []

    suite = suites["resvg-test-suite"]
    upstream = sources[suite["id"]]
    revision = git(upstream, "rev-parse", "HEAD")
    target = destination / suite["id"]
    for svg in sorted((upstream / "tests").rglob("*.svg")):
        relative = svg.relative_to(upstream / "tests")
        reference = svg.with_suffix(".png")
        if not reference.exists():
            continue
        copy_file(svg, target / "svg" / relative)
        copy_file(reference, target / "reference" / relative.with_suffix(".png"))
        text = read_svg(svg)
        record = base_record(
            suite, relative, f"corpora/{suite['id']}/svg/{relative.as_posix()}",
            f"{suite['source_url']}/blob/{revision}/tests/{relative.as_posix()}",
            title(text, relative.stem), elements(text), image_size(reference),
        )
        record.update({
            "feature": feature_path(relative),
            "reference_image": f"corpora/{suite['id']}/reference/{relative.with_suffix('.png').as_posix()}",
            "_source_path": target / "svg" / relative,
            "_reference_path": target / "reference" / relative.with_suffix(".png"),
        })
        records.append(record)
    copy_tree(upstream / "resources", target / "resources")
    copy_tree(upstream / "fonts", target / "fonts")
    copy_file(upstream / "LICENSE", target / "LICENSE")
    metadata.append({**suite, "revision": revision, "index": "CORPORA.md"})

    suite = suites["wpt-svg2-reftests"]
    upstream = sources[suite["id"]]
    revision = git(upstream, "rev-parse", "HEAD")
    target = destination / suite["id"]
    copy_tree(upstream / "svg", target / "svg")
    copy_file(upstream / "LICENSE.md", target / "LICENSE.md")
    for svg, reference in wpt_pairs(upstream / "svg"):
        relative = svg.relative_to(upstream / "svg")
        reference_relative = reference.relative_to(upstream / "svg")
        text = read_svg(svg)
        record = base_record(
            suite, relative, f"corpora/{suite['id']}/svg/{relative.as_posix()}",
            f"{suite['source_url']}/blob/{revision}/svg/{relative.as_posix()}",
            title(text, relative.stem), elements(text), tuple(suite["resolution"]),
        )
        record.update({
            "feature": feature_path(relative),
            "reference_source": f"corpora/{suite['id']}/svg/{reference_relative.as_posix()}",
            "reference_image": f"assets/reference/{suite['id']}/{relative.with_suffix('.png').as_posix()}",
            "_source_path": target / "svg" / relative,
            "_reference_svg": target / "svg" / reference_relative,
        })
        records.append(record)
    metadata.append({**suite, "revision": revision, "index": "CORPORA.md"})

    suite = suites["w3c-svg-tiny-1.2"]
    upstream = sources[suite["id"]]
    revision = "2008-09-12 archive (sha256: " + suite["archive_sha256"][:12] + ")"
    target = destination / suite["id"]
    for svg in sorted((upstream / "svg").glob("*.svg")):
        text = read_svg(svg)
        if W3C_DYNAMIC.search(text):
            continue
        reference = upstream / "png" / svg.with_suffix(".png").name
        if not reference.exists():
            continue
        relative = Path(svg.name)
        copy_file(svg, target / "svg" / relative)
        (target / "svg" / relative).write_bytes(without_w3c_revision(svg.read_bytes()))
        copy_file(reference, target / "reference" / relative.with_suffix(".png"))
        source_elements = elements(read_svg(target / "svg" / relative))
        record = base_record(
            suite, relative, f"corpora/{suite['id']}/svg/{relative.as_posix()}",
            f"{suite['source_url']}svg/{relative.as_posix()}", title(text, relative.stem),
            source_elements, image_size(reference),
        )
        bits = relative.stem.split("-")
        record.update({
            "feature": "-".join(bits[:2]),
            "reference_image": f"corpora/{suite['id']}/reference/{relative.with_suffix('.png').as_posix()}",
            "_source_path": target / "svg" / relative,
            "_reference_path": target / "reference" / relative.with_suffix(".png"),
        })
        records.append(record)
    copy_tree(upstream / "resources", target / "resources")
    copy_tree(upstream / "images", target / "images")
    copy_file(upstream / "images/copyright-documents-19990405.html", target / "LICENSE.html")
    metadata.append({**suite, "revision": revision, "index": "CORPORA.md"})

    (destination / "index.json").write_text(json.dumps(metadata, indent=2) + "\n")
    apply_baselines(records, metadata)
    return destination, records, metadata


def apply_baselines(records, metadata):
    manifest = ROOT / "baselines/index.json"
    if not manifest.exists():
        return
    baselines = json.loads(manifest.read_text())
    revisions = {suite["id"]: suite["revision"] for suite in metadata}
    for record in records:
        key = f"{record['suite']}/{record['test']}"
        baseline = baselines["tests"].get(key)
        if baseline is None:
            continue
        if (revisions[record["suite"]] != baselines["revisions"][record["suite"]]
                or sha256(record["_source_path"]) != baseline["source_sha256"]):
            raise RuntimeError(f"Chrome baseline needs review after source update: {key}")
        reference = ROOT / baseline["image"]
        if image_size(reference) != tuple(record["resolution"]):
            raise RuntimeError(f"Chrome baseline dimension mismatch: {key}")
        record.pop("_reference_svg", None)
        record["_reference_path"] = reference
        record["reference_image"] = baseline["image"]
        record["reference_renderer"] = f"Chrome {baselines['chrome_version']} / Skia {baselines['skia_revision'][:12]}"
        if "suitability" in baseline:
            record["baseline_suitability"] = baseline["suitability"]
            record["baseline_reason"] = baseline["reason"]


def thorvg_info(path):
    commit = git(path, "rev-parse", "HEAD")
    describe = git(path, "describe", "--tags", "--always")
    dirty = bool(git(path, "status", "--porcelain", "--untracked-files=no"))
    return {
        "path": path.resolve(), "commit": commit, "version": describe,
        "dirty": dirty, "commit_url": f"https://github.com/thorvg/thorvg/commit/{commit}",
    }


def build_thorvg(source, cli_tools=None):
    build = CACHE / "thorvg-build"
    marker = build / ".source"
    if marker.exists() and marker.read_text() != str(source.resolve()):
        shutil.rmtree(build)
    reconfigure = ["--reconfigure"] if (build / "meson-private/coredata.dat").exists() else []
    options = ["-Dloaders=svg,ttf,otf", "-Dextra="]
    if cli_tools is None:
        options.append("-Dtools=svg2png")
    run(["meson", "setup", *reconfigure, build, source, *options])
    marker.write_text(str(source.resolve()))
    run(["meson", "compile", "-C", build, *(["tvg-svg2png"] if cli_tools is None else [])])
    if cli_tools is not None:
        pkg_config_path = build / "meson-uninstalled"
        build = CACHE / "cli-tools-build"
        reconfigure = ["--reconfigure", "--clearcache"] if (build / "meson-private/coredata.dat").exists() else []
        run(["meson", "setup", *reconfigure, build, cli_tools, "-Dtools=svg2png",
             f"--pkg-config-path={pkg_config_path}", "--wrap-mode=nofallback"])
        run(["meson", "compile", "-C", build, "tvg-svg2png"])
    tools = list(build.rglob("tvg-svg2png.exe" if os.name == "nt" else "tvg-svg2png"))
    if not tools:
        raise RuntimeError("Meson did not produce tvg-svg2png")
    return tools[0]


def prepare_renderer(args):
    if args.svg2png:
        tool = args.svg2png.expanduser().resolve()
        if not tool.is_file() or not os.access(tool, os.X_OK):
            raise RuntimeError(f"Not an executable SVG converter: {tool}")
        return tool, {
            "version": "installed ThorVG", "commit": None, "commit_url": None,
            "dirty": False, "converter_path": str(tool), "converter_sha256": sha256(tool),
        }
    source = args.thorvg.resolve() if args.thorvg else ensure_git_repo("thorvg", "https://github.com/thorvg/thorvg", args.thorvg_ref, offline=args.offline)
    if not (source / ".git").exists():
        raise RuntimeError(f"Not a ThorVG Git checkout: {source}")
    info = thorvg_info(source)
    cli_tools = None
    if not (source / "tools/svg2png/meson.build").exists():
        cli_tools = ensure_git_repo("thorvg-cli-tools", "https://github.com/thorvg/thorvg.cli-tools", "main", offline=args.offline)
        info["cli_tools_commit"] = git(cli_tools, "rev-parse", "HEAD")
    return build_thorvg(source, cli_tools), info


def font_environment(corpora):
    directories = [corpora / "resvg-test-suite/fonts", corpora / "w3c-svg-tiny-1.2/resources"]
    config = CACHE / "fonts.conf"
    cache = CACHE / "fontconfig"
    cache.mkdir(parents=True, exist_ok=True)
    config.write_text("<?xml version=\"1.0\"?><!DOCTYPE fontconfig SYSTEM \"fonts.dtd\"><fontconfig>" + "".join(f"<dir>{html.escape(str(path))}</dir>" for path in directories) + f"<cachedir>{html.escape(str(cache))}</cachedir><include ignore_missing=\"yes\">/etc/fonts/fonts.conf</include></fontconfig>")
    environment = os.environ.copy()
    environment.update({"FONTCONFIG_FILE": str(config), "FONTCONFIG_PATH": str(config.parent)})
    return environment


def render_requests(requests, tool, environment):
    errors, temporary = {}, {}
    for key in requests:
        source, resolution = key
        source = Path(source)
        token = hashlib.sha1(f"{source}:{resolution}".encode()).hexdigest()[:12]
        temp = source.with_name(f".thorvg-{token}-{source.name}")
        shutil.copy2(source, temp)
        temporary[key] = (temp, temp.with_suffix(".png"))

    def render_chunk(keys):
        if not keys:
            return
        width, height = keys[0][1]
        result = run([tool, *(temporary[key][0] for key in keys), "-r", f"{width}x{height}", "-b", "ffffff"], env=environment, check=False)
        missing = []
        for key in keys:
            output = temporary[key][1]
            if output.exists():
                for destination in requests[key]:
                    copy_file(output, destination)
                output.unlink()
            else:
                missing.append(key)
        if not missing:
            return
        if len(missing) == 1:
            key = missing[0]
            message = " | ".join(result.stdout.strip().splitlines()[-3:]) or f"renderer exit {result.returncode}"
            errors[key] = message.replace(str(temporary[key][0]), Path(key[0]).name)
            return
        middle = len(missing) // 2
        render_chunk(missing[:middle])
        render_chunk(missing[middle:])

    by_resolution = {}
    for key in requests:
        by_resolution.setdefault(key[1], []).append(key)
    try:
        for keys in by_resolution.values():
            for offset in range(0, len(keys), 100):
                render_chunk(keys[offset:offset + 100])
    finally:
        for svg, png in temporary.values():
            svg.unlink(missing_ok=True)
            png.unlink(missing_ok=True)
    return errors


def white_rgb(path):
    rgba = Image.open(path).convert("RGBA")
    result = Image.new("RGB", rgba.size, "white")
    result.paste(rgba.convert("RGB"), mask=rgba.getchannel("A"))
    return result


def max_channel(image):
    red, green, blue = image.split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue)


def compare_images(reference_path, rendered_path, diff_path, comparison):
    reference, rendered = white_rgb(reference_path), white_rgb(rendered_path)
    if reference.size != rendered.size:
        raise ValueError(f"dimension mismatch: {reference.size} != {rendered.size}")
    radius = comparison["blur_radius"]
    reference_blur = reference.filter(ImageFilter.GaussianBlur(radius))
    rendered_blur = rendered.filter(ImageFilter.GaussianBlur(radius))
    difference = ImageChops.difference(reference_blur, rendered_blur)
    delta = max_channel(difference)
    changed = delta.point([0] * (comparison["channel_delta"] + 1) + [255] * (255 - comparison["channel_delta"]))
    changed_pixels = changed.histogram()[255]
    total = reference.width * reference.height
    white = Image.new("RGB", reference.size, "white")
    reference_content = max_channel(ImageChops.difference(reference, white)).point(lambda value: 255 if value > 2 else 0)
    rendered_content = max_channel(ImageChops.difference(rendered, white)).point(lambda value: 255 if value > 2 else 0)
    content = ImageChops.lighter(reference_content, rendered_content)
    content_pixels = content.histogram()[255]
    changed_content = ImageChops.multiply(changed, content).histogram()[255]
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    backdrop = Image.blend(reference, white, 0.82)
    Image.composite(Image.new("RGB", reference.size, "#e52222"), backdrop, changed).save(diff_path, optimize=True)
    return {
        "changed_ratio": changed_pixels / total,
        "content_changed_ratio": changed_content / content_pixels if content_pixels else changed_pixels / total,
        "mae": sum(ImageStat.Stat(difference).mean) / 3,
    }


def finalize(records, suites, corpora, tool):
    assets = CACHE / "assets-next"
    shutil.rmtree(assets, ignore_errors=True)
    (assets / "rendered").mkdir(parents=True)
    Image.new("RGB", (512, 512), "#f1f3f5").save(assets / "render-error.png")
    requests = {}
    for record in records:
        resolution = tuple(record["resolution"])
        rendered = assets / "rendered" / record["suite"] / f"{record['_key']}.png"
        record["_rendered_path"] = rendered
        requests.setdefault((str(record["_source_path"]), resolution), []).append(rendered)
        if record.get("_reference_svg"):
            reference = assets / "reference" / record["suite"] / f"{record['_key']}.png"
            record["_reference_path"] = reference
            requests.setdefault((str(record["_reference_svg"]), resolution), []).append(reference)
    errors = render_requests(requests, tool, font_environment(corpora))

    suite_map = {suite["id"]: suite for suite in suites.values()}
    public = []
    for record in records:
        suite = suite_map[record["suite"]]
        source_key = (str(record["_source_path"]), tuple(record["resolution"]))
        reference_key = (str(record["_reference_svg"]), tuple(record["resolution"])) if record.get("_reference_svg") else None
        render_error = errors.get(source_key)
        reference_error = errors.get(reference_key) if reference_key else None
        diff = assets / "diff" / record["suite"] / f"{record['_key']}.png"
        visual_status, reason = "FAIL", render_error or reference_error
        metrics = {"changed_ratio": 1.0, "content_changed_ratio": 1.0, "mae": 255.0}
        if not reason:
            try:
                metrics = compare_images(record["_reference_path"], record["_rendered_path"], diff, CONFIG["comparison"])
                visual_status = "PASS" if (
                    metrics["mae"] <= suite["max_mae"]
                    and metrics["changed_ratio"] <= suite["max_changed_ratio"]
                    and metrics["content_changed_ratio"] <= suite["max_content_changed_ratio"]
                ) else "FAIL"
            except Exception as error:
                reason = str(error)
        if reason:
            status, issue = "FAIL", "render-error"
            rendered_url = "assets/render-error.png" if not record["_rendered_path"].exists() else f"assets/rendered/{record['suite']}/{record['_key']}.png"
            diff_url = "assets/render-error.png"
        else:
            status, issue, reason = visual_status, ("none" if visual_status == "PASS" else "visual-mismatch"), ("visual-match" if visual_status == "PASS" else "visual-diff")
            rendered_url = f"assets/rendered/{record['suite']}/{record['_key']}.png"
            diff_url = f"assets/diff/{record['suite']}/{record['_key']}.png"
        if record.get("baseline_suitability") == "unsuitable":
            status, visual_status, issue = "SKIP", "SKIP", "unsuitable-baseline"
            reason = record["baseline_reason"]
        item = {key: value for key, value in record.items() if not key.startswith("_") and key != "resolution"}
        item.update(metrics)
        item.update({
            "status": status, "visual_status": visual_status, "issue_type": issue, "reason": reason,
            "rendered_image": rendered_url, "diff_image": diff_url,
        })
        public.append(item)
    return assets, public


def write_data(records, suites, metadata, thorvg):
    data = CACHE / "data-next"
    shutil.rmtree(data, ignore_errors=True)
    data.mkdir()
    records.sort(key=lambda row: (row["suite"], row["test"]))
    (data / "results.json").write_text(json.dumps(records, separators=(",", ":")) + "\n")
    fields = ["suite", "track", "test", "title", "feature", "elements", "status", "visual_status", "issue_type", "reason", "changed_ratio", "content_changed_ratio", "mae", "source", "reference_image", "reference_renderer", "baseline_suitability", "baseline_reason", "rendered_image", "diff_image", "upstream"]
    with (data / "results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in records:
            writer.writerow({**row, "elements": "|".join(row["elements"])})
    summaries = []
    metadata_by_id = {item["id"]: item for item in metadata}
    for suite in suites.values():
        selected = [row for row in records if row["suite"] == suite["id"]]
        statuses = Counter(row["status"] for row in selected)
        summaries.append({
            "id": suite["id"], "name": suite["name"], "track": suite["track"], "spec": suite["spec"],
            "total": len(selected), "pass": statuses["PASS"], "fail": statuses["FAIL"],
            "skip": statuses["SKIP"],
            "index": metadata_by_id[suite["id"]]["index"],
            "revision": metadata_by_id[suite["id"]]["revision"],
        })
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thorvg": {key: value for key, value in thorvg.items() if key != "path"},
        "comparison": CONFIG["comparison"], "suites": summaries,
    }
    (data / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return data, summary


def write_corpus_index(metadata):
    lines = [
        "# Test corpora", "",
        "| Source | Track | Selection | Reference | License |",
        "|---|---|---|---|---|",
    ]
    for suite in metadata:
        lines.append(f"| [{suite['name']}]({suite['source_url']}) | {suite['track']} | {suite['selection']} | {suite['oracle']} | [{suite['license']}]({suite['license_url']}) |")
    lines += [
        "", "Cases in [baselines/index.json](baselines/index.json) use Chrome screenshots instead of the default reference.",
        "", "Images are composited on white and blurred before comparing RGB differences. Blur, channel tolerance, MAE and changed-pixel limits are set in [config/suites.json](config/suites.json).",
        "", "Counts and source revisions are in [data/summary.json](data/summary.json). Bundled fonts retain their individual license files.", "",
    ]
    temporary = ROOT / ".CORPORA.md.next"
    temporary.write_text("\n".join(lines))
    temporary.replace(ROOT / "CORPORA.md")


def replace_directory(source, destination):
    if destination.parent != ROOT:
        raise RuntimeError(f"Refusing broad replacement: {destination}")
    backup = CACHE / f"{destination.name}-previous"
    shutil.rmtree(backup, ignore_errors=True)
    if destination.exists():
        destination.rename(backup)
    try:
        source.rename(destination)
    except Exception:
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    shutil.rmtree(backup, ignore_errors=True)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    renderer = parser.add_mutually_exclusive_group()
    renderer.add_argument("--svg2png", type=Path, help="Use this installed converter without fetching or building ThorVG")
    renderer.add_argument("--thorvg", type=Path, help="Use this local ThorVG checkout without fetching it")
    renderer.add_argument("--thorvg-ref", default="main", help="ThorVG ref to fetch when --thorvg is omitted")
    parser.add_argument("--offline", action="store_true", help="Use only existing source caches")
    return parser.parse_args()


def main():
    args = parse_args()
    CACHE.mkdir(exist_ok=True)
    tool, thorvg = prepare_renderer(args)
    suites = {suite["id"]: suite for suite in CONFIG["suites"]}
    sources = {
        "resvg-test-suite": ensure_git_repo("resvg-test-suite", suites["resvg-test-suite"]["source_url"], suites["resvg-test-suite"]["source_ref"], offline=args.offline),
        "wpt-svg2-reftests": ensure_git_repo("wpt", suites["wpt-svg2-reftests"]["source_url"], suites["wpt-svg2-reftests"]["source_ref"], sparse=["svg"], offline=args.offline),
        "w3c-svg-tiny-1.2": ensure_w3c(suites["w3c-svg-tiny-1.2"], args.offline),
    }
    corpora, records, metadata = prepare_corpora(suites, sources)
    assets, records = finalize(records, suites, corpora, tool)
    data, _ = write_data(records, suites, metadata, thorvg)
    replace_directory(corpora, ROOT / "corpora")
    replace_directory(assets, ROOT / "assets")
    replace_directory(data, ROOT / "data")
    write_corpus_index(metadata)
    baseline = thorvg["commit"][:12] if thorvg["commit"] else thorvg["converter_path"]
    print(f"Published {len(records)} indexed SVG results for {thorvg['version']} ({baseline}).")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
