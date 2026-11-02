#!/usr/bin/env python3
"""18차 M08~M16 연결 검수. Python 3.10+, Node, Playwright, Chromium 필요.
실행: python scripts/review_p18.py [--chromium PATH] [--output PATH]
외부 요청은 차단하며 결과·화면은 Git 제외 ref/review-p18에 저장한다.
"""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from fractions import Fraction
from math import sqrt
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from threading import Thread
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from review_p17 import QuietHandler, jump, layout, expanded_help

ROOT = Path(__file__).resolve().parents[1]


def sort_cards(page, context, failures):
    count = page.locator('#p2-pool .dcard').count()
    for _ in range(count):
        card = page.locator('#p2-pool .dcard').first
        answer = card.get_attribute('data-ans')
        card.focus()
        card.press('Enter')
        page.get_by_role('button', name=answer+' 칸에 놓기', exact=True).press('Enter')
    assert page.locator('#p2-count').inner_text() == f'{count} / {count}'
    layout(page, context+' sorted', failures)
    expanded_help(page, context+' sorted', failures)
    page.locator('#p2-reset').click()
    assert page.locator('#p2-pool .dcard').count() == count
    return count


def audit(page, number, failures):
    path = next((ROOT/'module_v1').glob(f'M{number:02}_*'))
    quiz = page.evaluate('('+re.search(r'var QUIZ=(\[.*?\n\]);',path.read_text(),re.S)[1]+')')
    assert len(quiz) == 6 and [q['goal'] for q in quiz] == [1,1,2,2,3,3]
    assert page.evaluate('''()=>{const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);return new Set(ids).size===ids.length;}''')
    page.locator('.station').nth(1).click()
    assert page.locator('.gmap .gn').count() == 3
    links = page.locator('.gmap [data-jump]').evaluate_all('es=>es.map(e=>({id:e.dataset.jump,mode:e.dataset.sortmode,label:e.textContent.trim()}))')
    for i,link in enumerate(links):
        page.locator('.station').nth(1).click()
        page.locator('.gmap [data-jump]').nth(i).click()
        assert page.locator('.slide.on').get_attribute('id') == link['id']
        if link.get('mode'):
            assert page.locator('#m13-sortmode').input_value() == link['mode']
        layout(page, f'M{number:02} goal {i+1}', failures)
    page.locator('.station').nth(0).click()
    slides = page.locator('.slide').count()
    for i in range(slides):
        current = page.locator('.slide.on')
        sid = current.get_attribute('id') or f'slide-{i}'
        context = f'M{number:02} {sid}'
        layout(page,context,failures)
        if re.fullmatch('q[1-6]',sid):
            q=quiz[int(sid[1:])-1]
            current.locator('.opts button').nth(q['ans']).click()
            assert current.locator('.fbp.ok').count() == 1
            layout(page,context+' answered',failures)
            current.locator('.back').click()
            assert page.locator('.slide.on').get_attribute('id') == q['back']
            jump(page,sid)
        if sid in ('p1','p2','p3'):
            expanded_help(page,context,failures)
        if i < slides-1:
            page.locator('#next').click()
    jump(page,'p2')
    count=sort_cards(page,f'M{number:02}',failures)
    return dict(module=number,slides=slides,quizzes=6,cards=count,goal_links=len(links))


def reading_checks(page, failures, output):
    jump(page,'p2')
    page.locator('#m13-sortmode').select_option('reading')
    assert page.locator('#p2-bins').evaluate('e=>getComputedStyle(e).gridTemplateColumns.split(" ").length') == 2
    expected={
        '범례 없는 오차 막대는 종류를 확인한 뒤 해석한다':'올바른 해석',
        'SD 막대는 개인 관측값의 퍼짐을 나타낸다':'올바른 해석',
        '별표를 가장 높은 해당 단계로 표시할 때 p=0.005는 **이다':'올바른 해석',
        'SE 막대는 개인 관측값의 표준편차이다':'잘못된 해석',
        '두 평균의 95% 구간이 겹치면 차이는 반드시 유의하지 않다':'잘못된 해석',
        'N.S.는 두 모집단 평균이 같다는 증명이다':'잘못된 해석',
    }
    for card in page.locator('#p2-pool .dcard').all():
        assert card.get_attribute('data-ans') == expected[card.inner_text()]
    # Wrong answer must not move a card or increase the count.
    card=page.locator('#p2-pool .dcard').first
    wrong='잘못된 해석' if card.get_attribute('data-ans')=='올바른 해석' else '올바른 해석'
    card.focus();card.press('Enter')
    page.get_by_role('button',name=wrong+' 칸에 놓기',exact=True).press('Enter')
    assert page.locator('#p2-count').inner_text()=='0 / 6'
    assert page.locator('#p2-pool .dcard').count()==6
    sort_cards(page,'M13 reading',failures)
    # Topic change resets selected card, completed cards, feedback, count and help.
    card=page.locator('#p2-pool .dcard').first
    card.focus();card.press('Enter')
    page.locator('#p2 details summary').click()
    page.locator('#m13-sortmode').select_option('errors')
    assert page.locator('#p2-pool .dcard').count()==6
    assert page.locator('#p2 .dcard.sel').count()==0
    assert page.locator('#p2 details').get_attribute('open') is None
    assert page.locator('#p2-bins .bin').count()==3
    page.locator('#m13-sortmode').select_option('reading')
    expanded_help(page,'M13 reading reset',failures)
    page.locator('#p2 details summary').click()
    page.screenshot(path=str(output/'M13-reading.png'))
    # Preserve the existing topic and check switching after completed work.
    page.locator('#m13-sortmode').select_option('errors')
    sort_cards(page,'M13 errors after switch',failures)
    return len(expected)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium',default=shutil.which('chromium'))
    parser.add_argument('--output',type=Path,default=ROOT/'ref/review-p18')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'result.json').unlink(missing_ok=True)
    assert args.chromium
    for n in range(8,17):
        path=next((ROOT/'module_v1').glob(f'M{n:02}_*'))
        with tempfile.TemporaryDirectory() as temp:
            js=Path(temp)/'module.js'
            js.write_text(re.search('<script>(.*?)</script>',path.read_text(),re.S)[1])
            subprocess.run(['node','--check',str(js)],check=True,capture_output=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    failures=[];errors=[];modules=[];reading=0
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1280,'height':800},reduced_motion='reduce')
            page.route('**/*',lambda route: route.continue_() if route.request.url.startswith(f'http://127.0.0.1:{server.server_port}/') else route.abort())
            page.on('pageerror',lambda error:errors.append(str(error)))
            for n in range(8,17):
                path=next((ROOT/'module_v1').glob(f'M{n:02}_*'))
                page.goto(f'http://127.0.0.1:{server.server_port}/'+quote(str(path.relative_to(ROOT))))
                print(f'Checking M{n:02}',flush=True)
                try:
                    modules.append(audit(page,n,failures))
                except Exception:
                    page.screenshot(path=str(args.output/f'M{n:02}-failure.png'))
                    print(json.dumps(failures,ensure_ascii=False),flush=True)
                    raise
                if n==13:reading=reading_checks(page,failures,args.output)
                if n in (9,13,15,16):
                    page.locator('.station').nth(1).click()
                    page.screenshot(path=str(args.output/f'M{n:02}-goals.png'))
                    jump(page,'p2')
                    page.locator('#p2 details summary').click()
                    layout(page,f'M{n:02} final help',failures)
                    page.screenshot(path=str(args.output/f'M{n:02}-help.png'))
            browser.close()
        # Independent arithmetic for existing teaching examples; no module function is called.
        expected_counts = [Fraction(100, 2)] * 2
        chi2 = sum((observed-expected)**2/expected for observed,expected in zip([60,40],expected_counts))
        difference_pp = 100*(Fraction(60,100)-Fraction(1,2))
        assert chi2 == 4 and difference_pp == 10
        # Separate normal-mean example from M13's existing body: individual
        # intervals overlap while the difference interval excludes zero.
        individual = [[10-1.96,10+1.96],[13-1.96,13+1.96]]
        difference_interval = [3-1.96*sqrt(2),3+1.96*sqrt(2)]
        assert individual[0][1] > individual[1][0] and difference_interval[0] > 0
        reference = dict(expected_counts=[float(x) for x in expected_counts],chi2=float(chi2),difference_pp=float(difference_pp),individual_intervals=individual,difference_interval=difference_interval)
        result=dict(modules=modules,reading_cards=reading,reference=reference,failures=failures,pageerrors=errors)
        (args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps(result,ensure_ascii=False,indent=2))
        assert not failures,failures[:10]
        assert not errors,errors
    finally:
        server.shutdown();server.server_close();thread.join()


if __name__=='__main__':main()
