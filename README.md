[![Corpus licenses](https://img.shields.io/badge/licences-per_corpus-green.svg?style=flat)](CORPORA.md#licensing)
[![Wikipedia](https://img.shields.io/badge/Wikipedia-000000?style=flat&logo=wikipedia&logoColor=white)](https://en.wikipedia.org/wiki/Thor_Vector_Graphics)
[![Discord](https://img.shields.io/badge/Community-5865f2?style=flat&logo=discord&logoColor=white)](https://discord.gg/n25xj6J6HM)
[![OpenCollective](https://img.shields.io/badge/OpenCollective-84B5FC?style=flat&logo=opencollective&logoColor=white)](https://opencollective.com/thorvg)

# ThorVG SVG Compliance

<p align="center">
  <img width="550" height="auto" src="https://raw.githubusercontent.com/thorvg/thorvg.site/main/readme/logo/animated_brand.svg" alt="ThorVG">
</p>

Check how [ThorVG](https://github.com/thorvg/thorvg) renders SVGs from public test
suites. The web report shows pass/fail results, reference images, and visual diffs.

## View the report

Results are included in this repository. From the repository root, start a local
server with Python 3:

```bash
python3 -m http.server 8000
```

Open [http://localhost:8000](http://localhost:8000) to search, filter, and compare
results. No ThorVG build is needed to view the report.

## Regenerate the report

Requires Python 3.12+, Git, a C++ compiler, pkg-config, FreeType, and Fontconfig.
On Ubuntu 24.04, run from the repository root:

```bash
sudo apt-get update
sudo apt-get install -y git g++ pkg-config python3 meson ninja-build python3-pil \
  libfreetype-dev libfontconfig1-dev

python3 scripts/update.py
```

This installs Meson, Ninja, and Pillow, then fetches ThorVG's latest `main` and the
test suites into `.cache/`. The updater builds ThorVG and its SVG converter
(fetching [CLI Tools](https://github.com/thorvg/thorvg.cli-tools) when needed),
then replaces `corpora/`, `assets/`, `data/`, and `CORPORA.md` with updated results.
Refresh the report to see them.

To test a local ThorVG checkout:

```bash
python3 scripts/update.py --thorvg /path/to/thorvg
```

Other options:

- `--thorvg-ref REF`: fetch a branch, tag, or commit instead of `main`; used without `--thorvg`.
- `--offline`: reuse cached sources without fetching; test suites and any required CLI Tools must already be cached.

## Read the results

| Test suite | Track | Compared against |
|------------|-------|------------------|
| WPT static SVG reftests | Conformance | Reference SVGs rendered by the same ThorVG build |
| W3C SVG Tiny 1.2 static subset | Advisory | W3C reference PNGs |
| resvg-test-suite | Diagnostic | Upstream reference PNGs |

`PASS` means the rendering meets the suite's visual thresholds. `FAIL` means a
visual mismatch or a rendering/loading error. Pass rates include all indexed
tests. The three tracks measure different things; they do not form a single SVG
compliance percentage.

See [CORPORA.md](CORPORA.md) for selection rules, comparison methods, and licenses,
or [config/suites.json](config/suites.json) for thresholds.
Download the [summary](data/summary.json) or per-test results as
[JSON](data/results.json) or [CSV](data/results.csv).

## Development

After installing the dependencies above, run the updater checks:

```bash
python3 -m unittest scripts/test_update.py
```

The [GitHub Actions workflow](.github/workflows/update-report.yml) regenerates and
commits results weekly or on manual dispatch.
