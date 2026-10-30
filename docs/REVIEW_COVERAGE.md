# 교재 검수 색인

갱신일: **2026-10-30, 한국 시간**. Git에 보존된 1~17차 기록을 차수·모듈별로 연결했다. 재개 순서·원본 자료·남은 일은 [작업 인계](WORK_HANDOFF.md)를 먼저 읽는다.

## 완료한 차수와 보존 커밋

각 문서의 완료는 그 문서에 명시한 수정·검사 범위에 한정한다. 표의 커밋은 해당 차수 결과가 포함된 커밋이며, 여러 차수가 한 커밋으로 묶인 경우도 있다. 원본교재 PDF 대조는 3차부터 기록되며 1~2차는 검수 매트릭스·가이드와 현행 소스 대조다.

| 차수 | 대상 | 주요 범위 | 보존 커밋 |
|---|---|---|---|
| [1차](CONTENT_REVIEW_20261028.md) | M07・M09・M21・M25・M29・M30・M36 | 우선 정확성·수치·해석 | `d88ffb5` |
| [2차](CONTENT_REVIEW_P1_20261028.md) | M14・M15・M33 | 검정 선택·다중비교·통계/기계학습 비교 | `d88ffb5` |
| [3차](CONTENT_REVIEW_TEXTBOOK_20261028.md) | M03・M19・M22 | 표집·다중회귀·푸아송 회귀 | `d88ffb5` |
| [4차](CONTENT_REVIEW_TEXTBOOK_P4_20261028.md) | M31・M32・M34・M37 | MCMC 진단·PCA 척도·누출·정상분포 | `d88ffb5` |
| [5차](CONTENT_REVIEW_TEXTBOOK_P5_20261028.md) | M10・M11・M12 | 신뢰구간·p값·t검정 연결 | `d88ffb5` |
| [6차](CONTENT_REVIEW_TEXTBOOK_P6_20261028.md) | M18・M26・M28 | 회귀·베이즈 인수·인과/상관 | `d88ffb5` |
| [7차](CONTENT_REVIEW_TEXTBOOK_P7_20261028.md) | M04・M05・M06 | 변수·기술통계·확률 | `9a86921` |
| [8차](CONTENT_REVIEW_TEXTBOOK_P8_20261028.md) | M13・M16・M17 | 오류/검정력·비율·상관 | `9a86921` |
| [9차](CONTENT_REVIEW_TEXTBOOK_P9_20261028.md) | M01・M02・M08 | 분석 목적·통계·추론/표집 | `9a86921` |
| [10차](CONTENT_REVIEW_TEXTBOOK_P10_20261028.md) | M20・M21・M23 | 모형 다듬기·GLM·모형 평가 | `557b256` |
| [11차](CONTENT_REVIEW_TEXTBOOK_P11_20261029.md) | M07・M09・M27 | 표준화·SE·p-해킹 | `557b256` |
| [12차](CONTENT_REVIEW_TEXTBOOK_P12_20261029.md) | M24・M35 | 재현성·모형·검증 환류 | `557b256` |
| [13차](CONTENT_REVIEW_TEXTBOOK_P13_20261029.md) | M14・M15 | 집단 비교 가정·순위 p값·F 계산 | `79ffc13` |
| [14차](CONTENT_REVIEW_TEXTBOOK_P14_20261029.md) | M25・M29 | 효과/실무 기준·추정 대상/인과 가정 | `d9a61fe` |
| [15차](CONTENT_REVIEW_TEXTBOOK_P15_20261029.md) | M30・M36 | 사후/예측·SIR 증가 조건/기간 | `8c9581f` |
| [16차](CONTENT_REVIEW_TEXTBOOK_P16_20261029.md) | M33 | 군집 거리·초기화·절단 구성원 | `3803f90` |
| [17차](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) | M01~M07 점검; M01·M03·M04·M05·M06·M07 변경 | 목표 연결·분산/조건부확률·가상 T·도움말 | `1fe4c51` |
| [홈 UI/UX](HOME_UI_REVIEW_20261029.md) | 홈·과정/모듈 탐색 | 검색·필터·최근 모듈·의견 폼·접근성 | `8d7b2d2` |

1~16차 및 홈 수정은 `3803f90` 이력에 포함되어 있다. 17차는 `1fe4c51`이며, 이 인계·색인 갱신 커밋이 뒤따른다. 최신 원격 보존 여부는 재개 시 Git으로 확인한다. 인계 문서 자체의 커밋은 다음 명령으로 확인한다.

```sh
git log -1 --oneline -- README.md docs/WORK_HANDOFF.md docs/REVIEW_COVERAGE.md
```

## 37개 모듈의 원본 환류·목표 연결 점검 기록

모든 모듈에 적어도 한 번의 원본 환류 기록이 있다. 아래는 **최신 원본 환류 기록**과 **17차 목표 연결 점검 범위**를 구별한 색인이다. M02·M03은 17차에서 원문 내용을 새로 수정하지 않았으므로 원본 환류 열의 이전 기록을 유지했다. 모든 목표·문항·실습·검수 매트릭스 항목이 해결되었다는 완료표는 아니다. 이전 차수의 수정도 누적되어 있으므로 각 문서의 유지 사항과 근거를 함께 확인한다.

| 모듈·현행 파일 | 최신 원본 환류 기록 | 17차 목표 연결 점검 |
|---|---|---|
| [M01 데이터분석의목적](../module_v1/M01_데이터분석의목적_v1.0.html) | [17차](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) | [17차 대응표](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) |
| [M02 통계학의역할과전체모습](../module_v1/M02_통계학의역할과전체모습_v1.0.html) | [9차](CONTENT_REVIEW_TEXTBOOK_P9_20261028.md) | [17차 대응표](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) |
| [M03 모집단과표본](../module_v1/M03_모집단과표본_v1.0.html) | [3차](CONTENT_REVIEW_TEXTBOOK_20261028.md) | [17차 대응표](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) |
| [M04 데이터유형과분포](../module_v1/M04_데이터유형과분포_v1.0.html) | [17차](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) | [17차 대응표](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) |
| [M05 기술통계량](../module_v1/M05_기술통계량_v1.0.html) | [17차](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) | [17차 대응표](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) |
| [M06 확률과확률분포](../module_v1/M06_확률과확률분포_v1.0.html) | [17차](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) | [17차 대응표](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) |
| [M07 정규분포와표준화](../module_v1/M07_정규분포와표준화_v1.0.html) | [17차](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) | [17차 대응표](CONTENT_REVIEW_TEXTBOOK_P17_20261030.md) |
| [M08 추론통계의직관](../module_v1/M08_추론통계의직관_v1.0.html) | [9차](CONTENT_REVIEW_TEXTBOOK_P9_20261028.md) | 17차 범위 밖 |
| [M09 표준오차](../module_v1/M09_표준오차_v1.0.html) | [11차](CONTENT_REVIEW_TEXTBOOK_P11_20261029.md) | 17차 범위 밖 |
| [M10 신뢰구간](../module_v1/M10_신뢰구간_v1.0.html) | [5차](CONTENT_REVIEW_TEXTBOOK_P5_20261028.md) | 17차 범위 밖 |
| [M11 가설검정의원리와p값](../module_v1/M11_가설검정의원리와p값_v1.1.html) | [5차](CONTENT_REVIEW_TEXTBOOK_P5_20261028.md) | 17차 범위 밖 |
| [M12 가설검정해보기](../module_v1/M12_가설검정해보기_v1.0.html) | [5차](CONTENT_REVIEW_TEXTBOOK_P5_20261028.md) | 17차 범위 밖 |
| [M13 검정결과읽기와두가지오류](../module_v1/M13_검정결과읽기와두가지오류_v1.0.html) | [8차](CONTENT_REVIEW_TEXTBOOK_P8_20261028.md) | 17차 범위 밖 |
| [M14 두집단평균비교](../module_v1/M14_두집단평균비교_v1.0.html) | [13차](CONTENT_REVIEW_TEXTBOOK_P13_20261029.md) | 17차 범위 밖 |
| [M15 세집단이상비교](../module_v1/M15_세집단이상비교_v1.0.html) | [13차](CONTENT_REVIEW_TEXTBOOK_P13_20261029.md) | 17차 범위 밖 |
| [M16 비율비교](../module_v1/M16_비율비교_v1.0.html) | [8차](CONTENT_REVIEW_TEXTBOOK_P8_20261028.md) | 17차 범위 밖 |
| [M17 산점도와상관](../module_v1/M17_산점도와상관_v1.0.html) | [8차](CONTENT_REVIEW_TEXTBOOK_P8_20261028.md) | 17차 범위 밖 |
| [M18 단순선형회귀](../module_v1/M18_단순선형회귀_v1.0.html) | [6차](CONTENT_REVIEW_TEXTBOOK_P6_20261028.md) | 17차 범위 밖 |
| [M19 다중회귀](../module_v1/M19_다중회귀_v1.0.html) | [3차](CONTENT_REVIEW_TEXTBOOK_20261028.md) | 17차 범위 밖 |
| [M20 회귀모형다듬기](../module_v1/M20_회귀모형다듬기_v1.0.html) | [10차](CONTENT_REVIEW_TEXTBOOK_P10_20261028.md) | 17차 범위 밖 |
| [M21 일반화선형모형과로지스틱회귀](../module_v1/M21_일반화선형모형과로지스틱회귀_v1.0.html) | [10차](CONTENT_REVIEW_TEXTBOOK_P10_20261028.md) | 17차 범위 밖 |
| [M22 푸아송회귀와다양한일반화선형모형](../module_v1/M22_푸아송회귀와다양한일반화선형모형_v1.0.html) | [3차](CONTENT_REVIEW_TEXTBOOK_20261028.md) | 17차 범위 밖 |
| [M23 모형의평가와비교](../module_v1/M23_모형의평가와비교_v1.0.html) | [10차](CONTENT_REVIEW_TEXTBOOK_P10_20261028.md) | 17차 범위 밖 |
| [M24 재현성](../module_v1/M24_재현성_v1.0.html) | [12차](CONTENT_REVIEW_TEXTBOOK_P12_20261029.md) | 17차 범위 밖 |
| [M25 p값과효과크기다시보기](../module_v1/M25_p값과효과크기다시보기_v1.0.html) | [14차](CONTENT_REVIEW_TEXTBOOK_P14_20261029.md) | 17차 범위 밖 |
| [M26 베이즈인수와좋은가설](../module_v1/M26_베이즈인수와좋은가설_v1.0.html) | [6차](CONTENT_REVIEW_TEXTBOOK_P6_20261028.md) | 17차 범위 밖 |
| [M27 p해킹](../module_v1/M27_p해킹_v1.0.html) | [11차](CONTENT_REVIEW_TEXTBOOK_P11_20261029.md) | 17차 범위 밖 |
| [M28 인과와상관](../module_v1/M28_인과와상관_v1.0.html) | [6차](CONTENT_REVIEW_TEXTBOOK_P6_20261028.md) | 17차 범위 밖 |
| [M29 인과를밝히는방법](../module_v1/M29_인과를밝히는방법_v1.0.html) | [14차](CONTENT_REVIEW_TEXTBOOK_P14_20261029.md) | 17차 범위 밖 |
| [M30 베이즈통계의사고방식](../module_v1/M30_베이즈통계의사고방식_v1.0.html) | [15차](CONTENT_REVIEW_TEXTBOOK_P15_20261029.md) | 17차 범위 밖 |
| [M31 MCMC와베이즈통계사례](../module_v1/M31_MCMC와베이즈통계사례_v1.0.html) | [4차](CONTENT_REVIEW_TEXTBOOK_P4_20261028.md) | 17차 범위 밖 |
| [M32 주성분분석과인자분석](../module_v1/M32_주성분분석과인자분석_v1.0.html) | [4차](CONTENT_REVIEW_TEXTBOOK_P4_20261028.md) | 17차 범위 밖 |
| [M33 기계학습과비지도학습](../module_v1/M33_기계학습과비지도학습_v1.0.html) | [16차](CONTENT_REVIEW_TEXTBOOK_P16_20261029.md) | 17차 범위 밖 |
| [M34 지도학습과예측성능](../module_v1/M34_지도학습과예측성능_v1.0.html) | [4차](CONTENT_REVIEW_TEXTBOOK_P4_20261028.md) | 17차 범위 밖 |
| [M35 모형이란](../module_v1/M35_모형이란_v1.0.html) | [12차](CONTENT_REVIEW_TEXTBOOK_P12_20261029.md) | 17차 범위 밖 |
| [M36 미분방정식모형](../module_v1/M36_미분방정식모형_v1.0.html) | [15차](CONTENT_REVIEW_TEXTBOOK_P15_20261029.md) | 17차 범위 밖 |
| [M37 확률모형과수리모형의역할](../module_v1/M37_확률모형과수리모형의역할_v1.0.html) | [4차](CONTENT_REVIEW_TEXTBOOK_P4_20261028.md) | 17차 범위 밖 |

M11의 현행 파일은 `v1.1`이다. 이전 `v1.0` 경로를 복원해 링크하지 않는다.

## 이 색인에 없는 완료 판단

- M01~M07의 목표 21개는 17차 대응표에 기록했다. M08 이후의 목표 연결과 과정 경계 점검은 [다음 할 일](WORK_HANDOFF.md)에 남아 있다.
- 사용자 제공 검수 매트릭스 전문은 Git에 없으므로, 이 표가 그 문서의 모든 이슈 ID·출고 기준을 대체하지 않는다.
- 1~16차의 검증 스크립트·JSON·화면은 저장소 밖에 있었고 새 환경에 없다. 17차 코드는 [scripts/review_p17.py](../scripts/review_p17.py)에 보존했다. 과거 결과와 이번에 재실행한 검사를 구별한다.
- 실제 배포 확인·외부 URL/권리 확인·전체 기기/입력 검증·전문가 감수·사용자 파일럿을 이 색인으로 완료 처리하지 않는다.

새 차수를 마치면 차수 표와 대상 모듈의 최신 기록을 함께 갱신하고, 범위·한계·남은 일은 차수 문서 및 작업 인계에 남긴다.
