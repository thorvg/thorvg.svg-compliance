[![Corpus licenses](https://img.shields.io/badge/licences-per_corpus-green.svg?style=flat)](CORPORA.md#licensing)
[![Wikipedia](https://img.shields.io/badge/Wikipedia-000000?style=flat&logo=wikipedia&logoColor=white)](https://en.wikipedia.org/wiki/Thor_Vector_Graphics)
[![Discord](https://img.shields.io/badge/Community-5865f2?style=flat&logo=discord&logoColor=white)](https://discord.gg/n25xj6J6HM)
[![OpenCollective](https://img.shields.io/badge/OpenCollective-84B5FC?style=flat&logo=opencollective&logoColor=white)](https://opencollective.com/thorvg)

# ThorVG SVG Compliance

<p align="center">
  <img width="550" height="auto" src="https://raw.githubusercontent.com/thorvg/thorvg.site/main/readme/logo/animated_brand.svg" alt="ThorVG">
</p>

Check how [ThorVG](https://github.com/thorvg/thorvg) renders SVGs from public test
suites against reference images and Chrome/Skia. The web report shows test
results, reference images, and visual diffs.

## View the report

Results are checked in. Run `python3 -m http.server 8000` from the repository root
and open [localhost:8000](http://localhost:8000).

## Update the report

On Ubuntu 24.04 (Python 3.12+):

```bash
sudo apt-get update
sudo apt-get install -y git g++ pkg-config python3 meson ninja-build python3-pil \
  libfreetype-dev libfontconfig1-dev
python3 scripts/update.py
```

The updater fetches and builds ThorVG and its converter in `.cache/`, then updates
the corpora and report. Changed corpus revisions or source hashes require updated
snapshots and [baseline metadata](baselines/index.json) before generation can finish.

```bash
python3 scripts/update.py --thorvg /path/to/thorvg
python3 scripts/update.py --svg2png /usr/local/bin/tvg-svg2png --offline
python3 scripts/update.py --help
```

`--offline` requires cached sources. `--svg2png` uses an installed converter and
skips building; keep its CLI Tools `fonts/PublicSans-Regular.ttf` available.
Font-family matching and CJK output depend on additional converter font support.

## Results

- **PASS / FAIL:** visual thresholds met / mismatch or rendering error.
- **SKIP:** unsuitable baseline; excluded from `PASS / (PASS + FAIL)`.
- Suites use different references; the rates are not a combined SVG compliance score.

See [test sources and comparison rules](CORPORA.md) and [thresholds](config/suites.json).
Download [JSON](data/results.json) or [CSV](data/results.csv);
[summary.json](data/summary.json) records counts and revisions.

## Maintenance

Run `python3 -m unittest scripts/test_update.py` for updater checks.
[GitHub Actions](.github/workflows/update-report.yml) updates the report weekly or on manual dispatch.

Project code is [MIT licensed](LICENSE); test assets and fonts retain their
[upstream licenses](CORPORA.md).
