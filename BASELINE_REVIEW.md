# Baseline 재점검 — 2026-09-14

> 이 문서는 baseline 교체 전 감사 결과다. 후속 요청으로 불일치 577개의 활성 reference를 Chrome/Skia PNG로 전환했다. 현재 적용 목록과 조건은 [baselines/README.md](baselines/README.md), [baselines/index.json](baselines/index.json)에 있다. 아래 수치는 변경 전 결과를 보존한다.

현재 세트는 기능별 진단 자료로 사용할 수 있지만, 기존 PASS/FAIL 전체를 ThorVG의 SVG 정확도나 최신 Chrome 호환율로 해석하기에는 부적절하다. 미정의 동작의 안내 PNG, 동일 엔진에서 동시에 실패하는 reference, 폰트·리소스·viewport 조건, SVG Tiny 전용 기능을 구분해야 한다.

원본 SVG/PNG, 비교 설정, 기존 `data/`와 `assets/`는 변경하지 않았다. 이번 변경은 이 검토 문서이며 실행 자료는 `.cache/baseline-audit/`에 있다.

## 실행 조건과 범위

- 설치된 **Google Chrome 153.0.8010.36 (Linux headless)** 사용. [Google Stable 메타데이터](https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json)의 Stable과 일치했다. 메타데이터 시각은 `2026-09-13T21:16:06.145Z`이며 사본은 `.cache/chrome-versions.json`에 있다.
- 기존 2,137개 test SVG 전체와 WPT reference 251개를 실제 Chrome에서 렌더링했다. WPT test/reference는 800×600 조건에서도 전부 추가 실행했다. 총 2,890개 렌더링 조건 중 2,888개 성공, 2개 로딩 시간 초과. 일부 일시적인 시간 초과는 재시도에서 해소됐다.
- 독립 Chrome 프로필, localhost HTTP, 흰 배경, sRGB, SVG 문서 모드, 로딩 완료 및 `document.fonts.ready` 이후 캡처. WPT는 DPR 1, viewport 512×512와 800×600. resvg는 upstream 렌더러의 자연 크기/확대 방식을 따라 원본 PNG 해상도로 캡처했고 W3C는 PNG 해상도의 viewport를 사용했다.
- resvg 폰트 디렉터리와 Ahem을 감사 전용 Fontconfig에 등록했다. WPT 고정 revision `987a2d0c1a45f1a193f1f05d9508c4efc307c3bf`에서 `/fonts/ahem.css`, `/fonts/Ahem.ttf`, `/images/green-256x256.png`를 가져와 제공했다. 잘못된 상대 경로의 `fonts/FreeSans.woff`는 같은 revision에 이미 있는 `svg/import/woffs/FreeSans.woff`로 감사 서버에서 연결하고 관련 72개 렌더링 조건을 재실행했다. 원본 파일은 수정하지 않았다.
- ThorVG는 HEAD `6472cb7`의 기존 렌더링 결과를 재사용했다. 해당 결과는 `/usr/local/bin/tvg-svg2png`, 런타임 ThorVG 1.0.6, Public Sans 기본 폰트 조건이다. Chrome과 폰트 선택이 동일하지 않으므로 텍스트 차이를 모두 엔진 결함으로 분류하지 않았다.
- [`scripts/update.py`](scripts/update.py)의 `compare_images()`와 [`config/suites.json`](config/suites.json)의 임계값을 그대로 적용했다. 아래의 **일치**는 해당 이미지 비교 기준에서의 일치이며 스펙 적합 판정이 아니다. WPT 공식 runner의 개별 fuzzy 메타데이터 및 실행 환경을 완전히 재현한 결과도 아니다.

## 전체 결과

| 세트 | 대상 | Chrome와 baseline 일치 | 불일치 | 판정 보류 |
|---|---:|---:|---:|---:|
| resvg | 1,679 | 1,346 | 332 | 1 |
| WPT SVG2 | 251 | 212 | 39 | 0 |
| W3C SVG Tiny 1.2 | 207 | 0 | 206 | 1 |

resvg/W3C의 baseline은 제공된 PNG다. WPT의 이 표는 **Chrome가 렌더링한 test와 reference SVG끼리** 비교한 것이다. WPT는 512×512와 800×600 모두 212개 일치/39개 불일치로, 두 viewport 사이에서 판정이 바뀐 사례는 없었다.

직접적인 기존 ThorVG 이미지 대 Chrome test 이미지 비교에서는 resvg 644개, W3C 18개, WPT 9개가 일치했다. 특히 WPT 숫자는 아래의 root 크기 차이가 섞인 진단 수치이므로 ThorVG 호환율로 사용하면 안 된다.

## 확인된 문제

**1. resvg의 UB 안내 PNG가 실패 판정에 들어간다.**

[`resources/README.md`](corpora/resvg-test-suite/resources/README.md)는 `ub.png`를 undefined behavior 안내 이미지로 정의한다. 현재 reference 중 **56개**가 이 이미지와 일치하며, 기존 결과에서는 **56개 모두 FAIL**이다. 실제 기대 그림이 아니므로 픽셀 비교 대상과 성공률 분모에서 제외해야 한다. 예: `filters/enable-background/with-mask.svg`.

별도로 upstream `results.csv`의 과거 Chrome 상태는 성공 1,425 / 실패 193 / UNKNOWN 61이다. UNKNOWN 61개와 확인된 UB 이미지 56개는 같은 집합으로 취급하지 않았다. 과거 결과 역시 현재 Chrome 결과를 대신하지 않는다.

**2. resvg reference와 최신 Chrome의 동작이 다른 항목이 있다.**

Chrome와 PNG가 불일치한 **332개** 중 **53개**는 기존 ThorVG 출력과 Chrome 출력이 서로 일치했다. 이 53개는 곧바로 ThorVG만의 버그라고 할 수 없다. UB와 겹칠 수 있으므로 수치를 합산하면 안 된다.

예를 들어 [`accumulate-with-new.svg`](corpora/resvg-test-suite/svg/filters/enable-background/accumulate-with-new.svg)는 reference에 초록 사각형 2개, Chrome와 ThorVG에는 1개가 나타난다. Chrome–ThorVG 차이는 MAE 0.00394, changed ratio 0이다. 오래된 `enable-background` 기대 동작을 최신 브라우저 호환 기준과 분리해야 한다. 이 사실만으로 기존 reference가 스펙상 틀렸다고 결론 내릴 수는 없다.

332개 중 텍스트 요소가 있는 것은 191개다. 폰트·메트릭 차이가 포함되며, 각 불일치를 Chrome 회귀나 reference 오류로 확정하지 않았다.

**3. WPT에서 동일 엔진 reference 때문에 실제 누락을 PASS로 판정한다.**

다음 **3개는 기존 ThorVG test와 reference가 모두 완전히 흰 이미지여서 PASS**였다. Chrome에서는 test와 reference에 같은 도형이 나타나며 두 Chrome 이미지의 MAE와 changed ratio가 모두 0이다. 실제 누락을 숨기는 구체적인 사례다.

- [`paint-context-004.svg`](corpora/wpt-svg2-reftests/svg/painting/reftests/paint-context-004.svg): Chrome에는 파란 격자가 표시됨.
- [`paint-context-008.svg`](corpora/wpt-svg2-reftests/svg/painting/reftests/paint-context-008.svg): Chrome에는 도형이 표시됨.
- [`pattern-transform-01.svg`](corpora/wpt-svg2-reftests/svg/pservers/reftests/pattern-transform-01.svg): Chrome에는 흑백 패턴이 표시됨.

또한 기존 ThorVG PASS 111개 중 **12개는 Chrome test/reference 비교에서 불일치**했다. 이 12개 전체를 ThorVG 오판으로 확정할 수는 없다. Chrome 미지원 기능이나 reference 문제도 가능하다. `textpath-side-001/003/005.svg` 등이 여기에 포함되며, `textpath-side-003.svg`에서는 ThorVG 양쪽이 흰 화면이지만 Chrome에는 글자가 표시된다.

**4. WPT의 리소스와 viewport 계약이 CLI 조건과 다르다.**

- 선택된 test SVG 중 21개가 Ahem을 언급하고 22개가 루트 상대 리소스 경로를 사용한다. 기존 수집 방식은 WPT의 `/svg` 하위만 포함하므로 `/fonts/ahem.css`나 공통 `/images`를 그대로 제공하지 않는다.
- 실제 요청에서 FreeSans 상대 경로 오류와 `/images/green-256x256.png` 누락도 확인했다. 감사 서버에서 보완한 뒤에는 WPT 리소스의 HTTP 404가 favicon 외에는 남지 않았다. 외부 origin 차단 이벤트는 보안 동작 테스트와 별도로 기록했다.
- 기존 CLI는 모든 WPT test와 reference를 `-r 512x512`로 강제 확대한다. Chrome에서는 고정 `width`/`height`가 그대로 유지된다. **test 108/251개**, reference를 포함하면 **207/502개 문서**의 실제 root 크기가 512×512와 달랐다. 캔버스 크기가 같아도 SVG 내용의 크기가 같은 것은 아니다.
- 테스트 24개에 fuzzy 메타데이터가 있지만 현재 비교기는 suite 공통 임계값을 사용한다. 따라서 현재 결과를 공식 WPT PASS/FAIL로 표시하는 것은 부정확하다.

Ahem/FreeSans를 Chrome에 제공하는 것만으로 CLI 폰트 조건까지 맞춰지는 것은 아니다. Public Sans fallback으로만 렌더링하는 현재 CLI와 글꼴별 레이아웃을 비교하려면 폰트 공급 조건을 별도로 맞춰야 한다.

**5. W3C Tiny reference는 현재 Chrome의 일반 SVG baseline으로 쓰기 어렵다.**

Chrome에서도 전체 이미지 기준으로 **206개 모두 불일치**, 1개는 보류였다. 207개 중 **202개 소스에 `SVGFreeSansASCII`가 등장**하고, SVG 폰트·Tiny 전용 기능·하단 revision 라벨이 섞여 있다. Chrome은 SVG 폰트를 지원하지 않아 fallback 폰트로 그린다.

하단을 제외한 상단 300/360 영역을 보조 비교하면 **11개**는 Chrome와 공식 PNG가 일치한다. 예를 들어 [`struct-image-01-t.svg`](corpora/w3c-svg-tiny-1.2/svg/struct-image-01-t.svg)는 전체 비교에서 FAIL이지만 상단은 일치한다. 다만 같은 crop으로도 195개가 불일치하므로 하단 라벨만 제거하면 전체 문제가 해결되는 것은 아니다. 이 crop은 일부 본문을 자를 수 있는 진단용이며 새 정답 이미지로 사용하지 않았다.

[`coords-constr-201-t.svg`](corpora/w3c-svg-tiny-1.2/svg/coords-constr-201-t.svg)처럼 Tiny의 `ref(svg,...)` 변환을 기대하는 테스트는 Chrome 결과를 정답으로 삼기 어렵다. 이 사례는 공식 PNG의 revision `1.1`과 실제 소스의 `1.5`도 다르다.

리소스 누락도 있다: `interact-focus-212-t.svg`의 `../images/earth.jpg`, `linking-refs-205-t.svg`의 `svglib3.svg`, `struct-image-07-t.svg`의 `smiley.png` 요청은 404였다. 기존 파일 배치와 upstream 경로를 점검한 뒤 리소스 문제를 renderer 실패와 분리해야 한다.

최종 로딩 시간 초과는 resvg `structure/use/xlink-to-an-external-file.svg`, W3C `linking-refs-203-t.svg`다. 이 2개는 이미지 불일치로 집계하지 않았다.

## 권장 적용 순서

1. **분모 정리:** UB 안내 reference 56개, 리소스 미해결, 렌더링/로딩 오류를 visual FAIL과 분리한다. Tiny는 현재처럼 advisory로 두고 통합 정확도 수치에서 제외한다.
2. **WPT 조건 통일:** 공통 리소스와 폰트를 공급하고 root SVG 크기와 viewport를 구별한다. test/reference 관계 검사는 유지하되, 검증된 외부 엔진 이미지와의 대조를 추가해 양쪽 동시 누락을 잡는다. 무조건 빈 화면을 실패 처리하면 의도적으로 비어야 하는 테스트를 오판하므로 그렇게 고치면 안 된다.
3. **reference별 상태 기록:** `Chrome 일치`, `Chrome 불일치·스펙 확인 필요`, `미정의`, `환경 미충족`, `Tiny 전용`으로 구분한다. 39개 WPT Chrome 불일치 항목은 개별 스펙/다른 구현과 확인한 뒤 oracle 사용 여부를 정한다.
4. **회귀 기준 고정:** Chrome 버전, suite revision, 폰트 파일, viewport, DPR을 baseline과 함께 기록한다. “최신 Chrome”은 재점검 대상이지 자동으로 덮어쓸 정답이 아니다. resvg/W3C 원본 PNG는 보존한다.

## 상세 증거와 재현 자료

- [이미지 비교 및 전체 사례 목록](.cache/baseline-audit/index.html)
- [최종 개별 metrics와 렌더링 정보](.cache/baseline-audit/results.json), [집계](.cache/baseline-audit/summary.json)
- [Chrome 버전](.cache/baseline-audit/browser.json), [전체 실행 로그](.cache/baseline-audit/renders.jsonl), [리소스 보완 전 로그](.cache/baseline-audit/renders-before-resource-repair.jsonl)
- [Chrome 실행 스크립트](.cache/baseline-audit/render.mjs), [비교 스크립트](.cache/baseline-audit/compare.py), [마지막 변경분 재비교](.cache/baseline-audit/refresh.py)

재현은 저장소 루트에서 `node .cache/baseline-audit/render.mjs`와 `python3 .cache/baseline-audit/compare.py`를 사용한다. 렌더러는 성공한 조건을 재사용하므로 새 Chrome 감사 시에는 기존 로그/이미지를 별도 보관하고 새 실행 디렉터리를 사용해야 한다. `.cache/` 자료는 Git에 포함되지 않는 로컬 증거다.
