# Test corpora

| Source | Track | Selection | Reference | License |
|---|---|---|---|---|
| [resvg independent renderer test suite](https://github.com/linebender/resvg-test-suite) | diagnostic | All SVG/PNG pairs in the upstream tests directory | Upstream PNG | [MIT](corpora/resvg-test-suite/LICENSE) |
| [WPT SVG2 static reftests](https://github.com/web-platform-tests/wpt) | conformance | SVG-to-SVG rel=match reftests without script, SMIL, or print behavior | ThorVG-rendered WPT reference SVG | [BSD-3-Clause](corpora/wpt-svg2-reftests/LICENSE.md) |
| [W3C SVG Tiny 1.2 static subset](https://www.w3.org/Graphics/SVG/Test/20080912/) | advisory | Static tests only; animation, script, handler, and multimedia tests are excluded | Chrome/Skia PNG after removing Revision text from the SVG | [W3C Document License (1999)](corpora/w3c-svg-tiny-1.2/LICENSE.html) |

Cases in [baselines/index.json](baselines/index.json) use Chrome screenshots instead of the default reference.

Images are composited on white and blurred before comparing RGB differences. Blur, channel tolerance, MAE and changed-pixel limits are set in [config/suites.json](config/suites.json).

Counts and source revisions are in [data/summary.json](data/summary.json). Bundled fonts retain their individual license files.
