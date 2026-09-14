# Chrome/Skia baselines

582 cases now have Chrome **test SVG output**: resvg 333, WPT 42, and W3C SVG
Tiny 207. This includes seven unsuitable diagnostic images excluded from scoring.
The [12-case suitability reassessment](ASSESSMENT.md) records five suitable and
seven unsuitable results, including the previously incomplete captures.

- Chrome: **153.0.8010.36**, Linux headless.
- Skia revision: **4f574af2444846ceca4d277a8095c5d4229d175f**, from this Chrome
  release's [Chromium DEPS](https://github.com/chromium/chromium/blob/153.0.8010.36/DEPS).
- Filename: `<test-name>.skia-4f574af24448.png`. The suffix is the Skia commit,
  not a standalone Skia release version. These are Chrome document screenshots;
  SVG layout, CSS and fonts also depend on Chrome's Blink engine.
- Unsuitable images end in `.skia-4f574af24448.unsuitable.png`. Their manifest
  entries record `suitability` and `reason`; the report displays these fields and
  uses `SKIP`, excluding them from the `PASS / (PASS + FAIL)` rate. Diagnostic
  differences remain visible. Entries without these fields were not individually
  classified in this 12-case reassessment.
- Capture: white background, sRGB, document loading and `document.fonts.ready`
  completed for valid snapshots. Timeout diagnostic images were captured after
  stopping loading and are marked unsuitable. WPT uses a 512×512 CSS viewport at DPR 1; resvg uses the upstream
  natural-size/scale convention at its PNG resolution; W3C uses its PNG size.
- Fonts/resources: corpus resvg fonts and pinned WPT Ahem were supplied privately.
  WPT's `/images/green-256x256.png` was supplied from the pinned revision;
  broken relative `fonts/FreeSans.woff` requests were mapped to that revision's
  `svg/import/woffs/FreeSans.woff`. Other system fallback fonts remain
  environment-dependent. W3C missing resources remain reflected in its snapshots.

[`index.json`](index.json) selects these images over the usual upstream PNG or
ThorVG-rendered WPT reference. It records the
source hashes and corpus revisions; the updater rejects changed sources/revisions
until their snapshots are reviewed. Existing `reference_source` fields identify
upstream WPT reference SVGs, while `reference_image` and `reference_renderer`
identify the active comparison baseline.

For W3C Tiny, `update.py` removes only the `text` element with `id="revision"`
from all 207 SVG inputs. Both these Chrome PNGs and ThorVG output are rendered
from that same SVG, and the manifest hashes identify the processed inputs.
Other SVG content and the original encoding are preserved. The entire image is compared;
no rectangular region is masked or cropped. Original upstream PNGs are retained.

These snapshots measure **Chrome compatibility**, including the 56 former UB
placeholder cases and legacy Tiny behavior. They are not normative SVG expected
results. WPT root-size differences and the CLI's Public Sans fallback still affect
ThorVG comparisons; changing the baseline does not resolve those renderer setup
differences. Other cases retain their previous reference policy.
