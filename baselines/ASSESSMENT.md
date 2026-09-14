# Baseline 적합성 재검사 (2026-09-14)

앞선 검사에서 문제가 발견되었거나 검증되지 않았던 **12개**를 Chrome 153.0.8010.36 / Skia `4f574af24448`로 재출력했다. 결과는 **적합 5개, 부적합 7개**다. 전체 582개 Chrome 이미지에 대한 신규 적합성 판정은 아니다.

각 테스트는 로딩 완료 및 폰트 준비 후 60/500/1500ms 대기로 3회 캡처했다. 로딩 한도는 30초다. WPT 3개는 reference SVG도 같은 조건에서 3회 캡처했다(총 45회 시도). 로딩 시간 초과 시 로딩을 중단한 후 진단용으로만 캡처했다. 공개 이미지는 각 테스트의 마지막 시도에서 얻은 출력이다.

적합은 이 환경에서 **Chrome 호환성 비교용 이미지로 사용 가능**하다는 뜻이며, SVG 명세 준수나 ThorVG PASS를 뜻하지 않는다. 반복 출력이 같더라도 필요한 리소스가 빠졌거나 로딩이 완료되지 않았으면 부적합이다. Chrome 자체의 의도된 참조 제한은 해당 브라우저 동작으로 기록한다.

부적합 이미지는 `.skia-4f574af24448.unsuitable.png`로 표시하고 리포트에서 `SKIP`으로 분류했다. 통과율은 `PASS / (PASS + FAIL)`로 계산한다. 표시되는 차이 이미지와 수치는 진단용이며 합격·불합격 판정 근거에서 제외한다.

| 세트 | 테스트 / 새 이미지 | 판정 | 근거 |
|---|---|---|---|
| resvg-test-suite | [filters/feImage/recursive-links-2.svg](resvg-test-suite/filters/feImage/recursive-links-2.skia-4f574af24448.unsuitable.png) | 부적합 | 재귀 필터. 이번 3회는 같지만 이전 반복 출력에서 픽셀 변동이 확인되어 재현성을 보장할 수 없음. |
| resvg-test-suite | [filters/feImage/self-recursive.svg](resvg-test-suite/filters/feImage/self-recursive.skia-4f574af24448.unsuitable.png) | 부적합 | 자기 참조 재귀 필터. 이번 반복 출력에서도 픽셀이 달라짐. |
| resvg-test-suite | [structure/use/xlink-to-an-external-file.svg](resvg-test-suite/structure/use/xlink-to-an-external-file.skia-4f574af24448.unsuitable.png) | 부적합 | 3회 모두 로딩이 30초를 초과함. 로딩 중단 후 얻은 진단 이미지로, 완료된 출력이 아님. |
| w3c-svg-tiny-1.2 | [interact-focus-212-t.svg](w3c-svg-tiny-1.2/interact-focus-212-t.skia-4f574af24448.unsuitable.png) | 부적합 | 필요한 images/earth.jpg가 HTTP 404로 누락됨. |
| w3c-svg-tiny-1.2 | [linking-refs-202-t.svg](w3c-svg-tiny-1.2/linking-refs-202-t.skia-4f574af24448.png) | 적합 | 대기 한도를 30초로 늘린 재검사에서 3회 모두 로딩 완료·픽셀 일치. Chrome 호환성 비교용으로 적합. |
| w3c-svg-tiny-1.2 | [linking-refs-203-t.svg](w3c-svg-tiny-1.2/linking-refs-203-t.skia-4f574af24448.unsuitable.png) | 부적합 | 3회 모두 시간 초과. 1회는 캡처 실패, 로딩 중단 후 얻은 2개 진단 이미지도 서로 다름. |
| w3c-svg-tiny-1.2 | [linking-refs-205-t.svg](w3c-svg-tiny-1.2/linking-refs-205-t.skia-4f574af24448.unsuitable.png) | 부적합 | 필요한 svg/svglib3.svg가 HTTP 404로 누락됨. 3회 중 1회는 로딩 시간 초과도 발생. |
| w3c-svg-tiny-1.2 | [struct-image-07-t.svg](w3c-svg-tiny-1.2/struct-image-07-t.skia-4f574af24448.unsuitable.png) | 부적합 | 필요한 svg/smiley.png가 HTTP 404로 누락됨. |
| w3c-svg-tiny-1.2 | [struct-use-201-t.svg](w3c-svg-tiny-1.2/struct-use-201-t.skia-4f574af24448.png) | 적합 | 3회 모두 로딩 완료·픽셀 일치. 의도적으로 잘못된 data URI use 참조는 Chrome이 차단함. Chrome 호환성 비교용으로 적합. |
| wpt-svg2-reftests | [painting/reftests/paint-context-004.svg](wpt-svg2-reftests/painting/reftests/paint-context-004.skia-4f574af24448.png) | 적합 | 3회 반복 출력과 WPT reference SVG의 Chrome 출력이 픽셀 단위로 일치. 기존 빈 baseline을 교체함. |
| wpt-svg2-reftests | [painting/reftests/paint-context-008.svg](wpt-svg2-reftests/painting/reftests/paint-context-008.skia-4f574af24448.png) | 적합 | 3회 반복 출력과 WPT reference SVG의 Chrome 출력이 픽셀 단위로 일치. 기존 빈 baseline을 교체함. |
| wpt-svg2-reftests | [pservers/reftests/pattern-transform-01.svg](wpt-svg2-reftests/pservers/reftests/pattern-transform-01.skia-4f574af24448.png) | 적합 | 3회 반복 출력과 WPT reference SVG의 Chrome 출력이 픽셀 단위로 일치. 기존 빈 baseline을 교체함. |

재귀 필터 recursive-links-2는 이전 4회 검사(60/60/500/1500ms)에서 서로 다른 출력을 보였다. 이번 3회 일치만으로 이전 변동을 해소했다고 판단하지 않았다.

WPT 3개의 새 baseline을 적용하면 기존 ThorVG 결과는 모두 PASS에서 FAIL로 바뀐다. 기존 빈 이미지끼리의 일치가 통과로 잡히던 문제를 해소했다.

## W3C Tiny Revision 텍스트 제거

W3C SVG Tiny 1.2 static subset **207개 전체**에서 `xml:id="revision"`인 `<text>` 요소를 제거했다. 비교에 사용하는 SVG 자체를 처리하며, 다른 도형·텍스트·속성은 유지한다. UTF-16 파일 1개를 포함하여 원래 인코딩과 나머지 내용도 보존한다.

- Chrome/Skia baseline PNG 207개를 처리된 SVG로 다시 캡처했다. manifest의 source SHA-256도 해당 SVG를 가리킨다.
- `update.py`는 원본 캐시에서 corpus를 준비할 때마다 같은 처리를 적용하고, 그 SVG로 ThorVG 출력을 생성한다.
- 전체 이미지 픽셀을 비교한다. 사각형 제외, 크롭, 회색 마스킹 및 관련 메타데이터는 사용하지 않는다.
- `shapes-line-02-t`, `paint-stroke-08-t`, `struct-group-03-t` 등에서 Revision과 겹쳤던 도형은 텍스트 제거 후에도 남으며 비교에 포함된다.
- 기존 부적합 이미지의 표시는 유지한다. 로딩 중단 후 얻은 진단 이미지는 계속 `SKIP`이다.

`python3 scripts/update.py --svg2png /usr/local/bin/tvg-svg2png --offline` 전체 재실행 결과:

| 세트 | PASS | FAIL | SKIP |
|---|---:|---:|---:|
| wpt-svg2-reftests | 99 | 152 | 0 |
| w3c-svg-tiny-1.2 | 41 | 162 | 4 |
| resvg-test-suite | 643 | 1033 | 3 |
