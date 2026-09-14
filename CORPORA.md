# SVG corpus index

This is the human-readable index for every vendored test set. The full machine index is
[`data/results.json`](data/results.json), and the spreadsheet-friendly index is
[`data/results.csv`](data/results.csv).

| Set | Track | Indexed | Source revision | License |
|---|---:|---:|---|---|
| [resvg independent renderer test suite](corpora/resvg-test-suite/README.md) | diagnostic | 1679 | `d8e064337faf01bc5a9579187a56dbdbe3eacc72` | [MIT](https://github.com/linebender/resvg-test-suite/blob/main/LICENSE) |
| [WPT SVG2 static reftests](corpora/wpt-svg2-reftests/README.md) | conformance | 251 | `4493b11027761c7ff43352df94105dc9075e35d0` | [BSD-3-Clause](https://github.com/web-platform-tests/wpt/blob/master/LICENSE.md) |
| [W3C SVG Tiny 1.2 static subset](corpora/w3c-svg-tiny-1.2/README.md) | advisory | 207 | `2008-09-12 archive (sha256: 2203d6f44178)` | [W3C Document License (1999)](https://www.w3.org/Consortium/Legal/1999/copyright-documents-19990405) |
| [ThorVG official SVG regression assets](corpora/thorvg-regression/README.md) | regression | 5 | `a3a2b79ffef74d825e677998ef7c4cba8b55881e` | [MIT](https://github.com/thorvg/thorvg/blob/main/LICENSE) |

## Selection and reference policy

- **WPT** is the primary conformance track. Only static SVG-to-SVG equality reftests are indexed. Test and reference are rendered by the same ThorVG commit.
- **W3C SVG Tiny 1.2** is advisory. The 207 static files are copied unmodified; animation, script, handler, and multimedia files are excluded. W3C permits label-text variation; this report compares all selected files against the reference PNGs.
- **resvg-test-suite** is diagnostic rather than normative. Its upstream PNGs are useful cross-renderer references. Font-sensitive and undefined-behavior cases use the same visual thresholds as other tests.
- **ThorVG regression** compares official `test/resources` SVG files with an explicitly accepted ThorVG baseline. Accept a new baseline only with `--accept-regression-baseline`.

## Pixel comparison

Both images are composited on white and blurred by 0.6 px before comparison. Pixels whose largest RGB-channel delta is at most 24 are ignored. Each suite additionally declares MAE, whole-image changed-ratio, and content-only changed-ratio limits in [`config/suites.json`](config/suites.json).

## Licensing

Each corpus directory contains the upstream license/notice. The W3C files remain unmodified because the applicable W3C Document License does not grant a general right to create derivatives. Bundled resvg fonts retain their individual license files.
