#!/usr/bin/env python3
"""Combine the source inventory with observed browser evidence; no module writes.

Classification is an initial implementation decision, not content certification.
Manual decisions override measurable typography/accessibility candidates.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter,defaultdict
from pathlib import Path
from lxml import html
ROOT=Path(__file__).resolve().parents[1]

# Actions for the six pilot families and specific semantic tables.
OVERRIDES={
'm5-town':('재작성','전체 범위·확대 분포·요약표를 분리해 극단값의 위치와 전후 수치를 연결','A'),
'm5-box':('정돈','기존 9명 자료 유지, 사분위수 규칙·수염 끝·경계 밖 점을 명시','A'),
'm5-five':('분할','5개 표현을 단계별 비교로 나눠 동일 자료·축·요약값을 연결','A'),
'm10-twenty':('정돈','포함/미포함을 색과 기호로 구분, 실제 포함 수와 표집 규칙 표시','B'),
'm10-tci':('정돈','±2SE 근사와 95% t구간의 계산·해석 구별 유지','B'),
'm10-p1-svg':('정돈','반복 구간의 생성 조건과 실현 포함률을 표시','B'),
'm13-case':('재작성','원자료와 평균/구간을 연결하고 SE 오차막대의 대상을 명시','B'),
'm13-bars3':('분할','SD·SE·CI 비교를 같은 자료의 단계별 그림으로 분리','B'),
'm13-stars':('재작성','점·구간과 p값을 연결하고 별표와 판정 방법을 구분','B'),
'm18-ls':('정돈','잔차의 수직 방향과 각 x에서 적합값 일치 유지','C'),
'm18-band':('분할','평균 신뢰구간과 새 관측 예측구간을 선택·단계 표시','C'),
'm18-p3-svg':('정돈','관측 범위·단위·선 종류로 예측구간 구별','C'),
'm18-coef':('재작성','SVG 수치표를 접근 가능한 HTML 회귀계수 표로 전환','C'),
'm28-graph':('정돈','DAG에 가정한 인과구조임을 명시하고 원인/관측 관계 구별','D'),
'm28-rct':('정돈','표본 상관의 변화와 모형에서 가정한 실제 효과를 구별','D'),
'm28-p3-svg':('정돈','미식별 효과는 ?로, 모형에서 정한 0은 가정으로 표시','D'),
'm29-po':('정돈','관측 잠재결과와 관측 불가능한 반사실을 기호로 구별','D'),
'm29-psm':('분할','매칭 연결과 공변량 균형·공통지지 확인을 나누어 제시','D'),
'm29-did':('정돈','관측 실선·반사실 점선과 DID 수치 및 평행추세 가정 유지','D'),
'm29-p3-svg':('정돈','전후 관측과 평행추세 반사실을 실습 결과에 연결','D'),
'm32-axis':('정돈','표준화·투영·축 부호를 명시하고 PC 방향과 분산 연결','E'),
'm32-cont':('정돈','고유값·기여율 분모·누적률을 같은 계산에서 생성','E'),
'm32-load':('분할','부하량은 HTML 표, 점수는 산점도로 분리하고 선택 시편 연결','E'),
'm32-p3-svg':('정돈','점수용 고유벡터 계수와 상관 부하량 구분','E'),
'm32-fa':('정돈','잠재인자의 생성 가정과 PCA의 선형 변환 방향 구별','E'),
'm31-trace':('재작성','저장된 표시용 축약 trace 대신 재현 가능한 전체 체인에서 생성','F'),
'm31-diff':('재작성','도수 합과 저장 표본수 일치하는 새 체인으로 히스토그램·요약 재계산','F'),
'm31-p3-svg':('재작성','동일 새 체인에서 임계값별 사후확률과 히스토그램 재계산','F'),
'm31-pois':('재작성','푸아송 사후 요약의 계산 설정을 확보하고 실제 곡선값의 강제 제한 제거','F'),
'm31-p1-svg':('재작성','원주율 추정값의 clamp를 제거하고 실제 값이 보이는 축/범위 표시','F'),
'm4-raw':('분할','원자료 숫자 48개 텍스트를 원자료 표와 분포 화면으로 분리',''),
'm8-rand':('분할','조밀한 무작위표집 라벨을 표집 과정과 결과 비교로 분리',''),
'm14-case':('분할','두 자료 구조·숫자 표를 짝/독립 비교 화면으로 분리',''),
'm17-rank':('분할','원자료와 순위 변환 표를 별도 단계로 분리',''),
'm19-case':('분할','공변량 원자료 표와 조건부 관계 그림을 분리',''),
}
PAGES={1:'24;61',2:'24',3:'35',4:'50',5:'61;63;66',6:'74;75;76;78',7:'83',8:'91;94;97',9:'100;103;107;108',10:'109;112',11:'123;126',12:'130;133',13:'136;137;138;141;143',14:'156;160',15:'161;163;165;166;167',16:'168;170;171;173',17:'180;186;190',18:'192;196;198;201',19:'211;216',20:'220;222;224;225;226',21:'234;235;238',22:'240;243;245',23:'247;249;251;253',24:'258;262',25:'266;267;268;272',26:'274;275;277;279',27:'280;282;283;285;287',28:'291;294;295;298',29:'301;303;305;307;309;310;311',30:'320',31:'326;333',32:'344;345',33:'350',34:'359',35:'374',36:'383',37:'390'}
P0={5,9,10,11,13,16,18,21,23,26,28,29,31,32,34,36}
P2={1,35}


def family(label):
    # Search-specific grouping; not a claim of identical figures or reusable math.
    if re.search('사후|체인|MCMC|깁스',label):return '베이즈·표집'
    if re.search('인과|경향 점수|반사실|중첩|이중차분',label):return '인과·설계'
    if re.search('주성분|인자분석|군집|덴드로',label):return '차원축소·군집'
    if re.search('오차 막대|신뢰구간|표준오차|검정력|α|β|p값|t분포',label):return '추론·구간·검정'
    if re.search('회귀|잔차|로지스틱|푸아송|AIC|ROC|판정표',label):return '회귀·모형평가'
    if re.search('분포|확률|히스토그램|평균|중앙값|분산|표준편차',label):return '분포·요약'
    if re.search('곡선|방정식|SIR|마르코프|무작위 행보',label):return '동역학·확률모형'
    return '개념·비유·흐름'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--runtime',type=Path,default=ROOT/'ref/visual-stage1-20261104/runtime.json');args=ap.parse_args()
    runtime=json.loads(args.runtime.read_text());observed={};bindings=defaultdict(set)
    for m in runtime['modules']:
        for a in m['assets']+m['tables']:observed[(m['module'],a['key'])]=a
        for c in m['controls']:
            for key in c['affected']:bindings[(m['module'],key)].add(c.get('id') or c.get('label',''))
    inventory=list(csv.DictReader((ROOT/'docs/VISUAL_ASSET_INVENTORY_20261104.csv').open()))
    docs={};elements={};sources={}
    for p in sorted((ROOT/'module_v1').glob('*.html')):
        d=html.fromstring(p.read_text());docs[p.name[:3]]=d;sources[p.name[:3]]=p.read_text()
        for typ in ['svg','table','img']:
            for i,e in enumerate(d.xpath('//'+typ),1):elements[(p.name[:3],f'{typ}:{i}')]=e
    result=[]
    for r in inventory:
        m=r['module'];number=int(m[1:]);key=f"{r['type']}:{r['type_source_order_1based']}";e=elements[(m,key)]
        a=observed[(m,key)];label=r['label_or_text_excerpt'];eid=r['element_id'];nav=not int(r['slide_source_order_1based'])
        exact=hashlib.sha256(re.sub(r'\s+',' ',html.tostring(e,encoding='unicode',with_tail=False)).encode()).hexdigest()[:16]
        action,reason,pilot=OVERRIDES.get(eid,('','',''))
        if nav:
            action,reason='유지','슬라이드 밖 공통 홈 이동 아이콘. 학습 그림의 재작성 대상에서 제외'
        elif r['type']=='table':
            action,reason='정돈',f"기존 의미 구조 유지, caption {a['captions']}개·scope 지정 {a['scoped']}/{a['headers']}개 보완"
        elif not action:
            issues=[]
            if a['under12']:issues.append(f"12px 미만 라벨 {a['under12']}개(최소 {a['minFont']:g}px)")
            if not a['label'] and not a['titles']:issues.append('SVG 이름 제공 방식 확인 필요')
            if issues:action,reason='정돈','; '.join(issues)+' — 글자 확대·축/범례 배치·대체 설명 점검'
            else:action,reason='유지','기존 구조 유지. 자동 측정에서 글자 크기·이름의 우선 수정 후보 없음; 내용 검수는 별도'
        sourcekind='공통 UI' if nav else '개념 요약표' if r['type']=='table' else '모듈 내 교육용 예시/개념도(요소별 자료 계보는 제작 시 확인)'
        line_refs=[str(i) for i,line in enumerate(sources[m].splitlines(),1) if eid and eid in line]
        result.append({**r,'asset_key':f'{m}/{key}','source_line':e.sourceline,'action':action,'decision_basis':reason,
          'priority':'공통' if nav else 'P0' if number in P0 else 'P2' if number in P2 else 'P1',
          'implementation_stage':0 if nav else 3 if number<=16 else 4 if number<=29 else 5,
          'pilot_family':pilot,'search_family': '공통 UI' if nav else family(label),
          'exact_source_group':exact,'source_pages_reference':'' if nav else PAGES[number],
          'source_binding':'해당 없음' if nav else '모듈 개념 대응 쪽; 개별 그림번호·실제 자료는 제작 전 확정',
          'data_kind':sourcekind,'source_id_occurrence_lines':';'.join(line_refs[:12]),
          'runtime_text_count':a.get('textCount',''),'runtime_min_font':a.get('minFont',''),
          'runtime_labels_under12':a.get('under12',''),'runtime_labels_under10':a.get('under10',''),
          'observed_controls':';'.join(sorted(bindings[(m,key)])),
          'validation_status':'실행·요소 대응 확인; 내용·제작물 검수 전',
          'dependency':'새 체인·모형 명세 생성 후 관련 그림·본문·문항 동시 갱신' if pilot=='F' and eid not in ['m31-p1-svg'] else '',
        })
    output=ROOT/'docs/VISUAL_WORKLIST_STAGE1_20261104.csv'
    with output.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0]),lineterminator="\n");w.writeheader();w.writerows(result)
    summary={'modules':len(runtime['modules']),'slides':sum(m['slides'] for m in runtime['modules']),
             'source_assets':len(result),'actions':dict(Counter(r['action'] for r in result)),
             'slide_svg':sum(r['type']=='svg' and int(r['slide_source_order_1based'])>0 for r in result),
             'ui_svg':sum(r['type']=='svg' and not int(r['slide_source_order_1based']) for r in result),
             'table':sum(r['type']=='table' for r in result),'control_states':sum(m['states'] for m in runtime['modules']),
             'svg_with_under12':sum(bool(r['runtime_labels_under12']) for r in result),
             'svg_with_under10':sum(bool(r['runtime_labels_under10']) for r in result),
             'exact_source_groups':len({r['exact_source_group'] for r in result}),
             'pageerrors':len(runtime['pageerrors']),
             'module_actions':{m:dict(Counter(r['action'] for r in result if r['module']==m)) for m in docs}}
    (args.runtime.parent/'classification-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    assert len(result)==len(observed)==759
    assert len({r['asset_key'] for r in result})==len(result)
    assert not runtime['pageerrors']

if __name__=='__main__':main()
