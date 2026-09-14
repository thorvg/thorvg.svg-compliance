# SVG corpus index

This is the human-readable index for every vendored test set. The full machine index is
[`data/results.json`](data/results.json), and the spreadsheet-friendly index is
[`data/results.csv`](data/results.csv).

| Set | Track | Indexed | Source revision | License |
|---|---:|---:|---|---|
| [resvg independent renderer test suite](corpora/resvg-test-suite/README.md) | diagnostic | 1679 | `d8e064337faf01bc5a9579187a56dbdbe3eacc72` | [MIT](https://github.com/linebender/resvg-test-suite/blob/main/LICENSE) |
| [WPT SVG2 static reftests](corpora/wpt-svg2-reftests/README.md) | conformance | 251 | `987a2d0c1a45f1a193f1f05d9508c4efc307c3bf` | [BSD-3-Clause](https://github.com/web-platform-tests/wpt/blob/master/LICENSE.md) |
| [W3C SVG Tiny 1.2 static subset](corpora/w3c-svg-tiny-1.2/README.md) | advisory | 207 | `2008-09-12 archive (sha256: 2203d6f44178)` | [W3C Document License (1999)](https://www.w3.org/Consortium/Legal/1999/copyright-documents-19990405) |

## Selection and reference policy

- **WPT** is the primary conformance track. Only static SVG-to-SVG equality reftests are indexed. Test and reference are rendered by the same ThorVG commit.
- **W3C SVG Tiny 1.2** is advisory. Animation, script, handler, and multimedia files are excluded. Only the Revision text element is removed from all 207 selected SVGs before generating both Chrome baselines and ThorVG output. The entire image is compared, including content behind the former label; no rectangle is masked or cropped.
- **resvg-test-suite** is diagnostic rather than normative. Its upstream PNGs are useful cross-renderer references. Font-sensitive and undefined-behavior cases use the same visual thresholds as other tests.
- **Chrome/Skia overrides:** Cases listed in [`baselines/index.json`](baselines/index.json) use the versioned Chrome test PNG instead of the default reference above. These snapshots measure browser compatibility, including formerly undefined cases; they are not normative SVG references. See [`baselines/README.md`](baselines/README.md) for the renderer and capture conditions.

## Pixel comparison

Both images are composited on white and blurred by 0.6 px before comparison. Pixels whose largest RGB-channel delta is at most 24 are ignored. Each suite additionally declares MAE, whole-image changed-ratio, and content-only changed-ratio limits in [`config/suites.json`](config/suites.json).

## Licensing

Each corpus directory contains the upstream license/notice. Bundled resvg fonts retain their individual license files.
