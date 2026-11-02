#!/usr/bin/env python3
"""19차 M17~M23 연결 검수. Python 3.10+, Node, Playwright, Chromium 필요.
실행: python scripts/review_p19.py [--chromium PATH] [--output PATH]
외부 요청은 차단하며 결과·화면은 Git 제외 ref/review-p19에 저장한다.
"""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from fractions import Fraction
from math import exp
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from threading import Thread
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from review_p17 import QuietHandler, jump, layout, expanded_help, set_range, text_number

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
    if number == 19:
        assert page.locator('#m19-plane').evaluate("e=>{const b=e.getBBox(),v=e.viewBox.baseVal;return b.x>=v.x && b.y>=v.y && b.x+b.width<=v.x+v.width && b.y+b.height<=v.y+v.height;}")
    page.locator('.station').nth(1).click()
    assert page.locator('.gmap .gn').count() == 3
    links = page.locator('.gmap [data-jump]').evaluate_all('es=>es.map(e=>({id:e.dataset.jump,mode:e.dataset.sortmode,label:e.textContent.trim()}))')
    for i,link in enumerate(links):
        page.locator('.station').nth(1).click()
        page.locator('.gmap [data-jump]').nth(i).click()
        assert page.locator('.slide.on').get_attribute('id') == link['id']
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



def prediction_checks(page, n, failures, output):
    jump(page, 'p3')
    slider = page.locator(f'#m{n}-g')
    lo, hi = float(slider.get_attribute('min')), float(slider.get_attribute('max'))
    results=[]
    for guess in (lo, hi):
        set_range(page,f'#m{n}-g',guess)
        assert page.locator(f'#m{n}-msg3').get_attribute('class') == 'pmsg'
        page.locator(f'#m{n}-check').click()
        assert page.locator(f'#m{n}-msg3').get_attribute('class') in ('pmsg ok','pmsg ng')
        actual=page.locator(f'#m{n}-act').inner_text()
        assert actual != '?'
        if n==20:
            assert text_number(page,'#m20-add') == 13+(35-32) == 16
            assert text_number(page,'#m20-act') == 30
            assert (35-32)-(30-13) == -14
        if n==21:
            # Initial concentration 6; coefficients are the existing fitted values.
            p=1/(1+exp(-(-4.4774+.87663*6)))
            assert abs(text_number(page,'#m21-act')-100*p) <= .051
            assert abs(text_number(page,'#m21-od')-p/(1-p)) <= .0051
        layout(page,f'M{n} prediction {guess}',failures)
        expanded_help(page,f'M{n} prediction {guess}',failures)
        if guess==hi:
            page.locator('#p3 details summary').click()
            page.screenshot(path=str(output/f'M{n:02}-prediction.png'))
            page.locator('#p3 details summary').click()
        set_range(page,f'#m{n}-g',hi if guess==lo else lo)
        assert page.locator(f'#m{n}-msg3').get_attribute('class') == 'pmsg'
        # M23 deliberately retains previously revealed reference results.
        assert page.locator(f'#m{n}-act').inner_text() == (actual if n==23 else '?')
        if n==21: assert page.locator('#m21-od').inner_text() == '?'
        if n==20: assert page.locator('#m20-add').inner_text() == '?'
        results.append(dict(module=n,guess=guess,actual=actual))
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium',default=shutil.which('chromium'))
    parser.add_argument('--output',type=Path,default=ROOT/'ref/review-p19')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'result.json').unlink(missing_ok=True)
    assert args.chromium
    for n in range(17,24):
        path=next((ROOT/'module_v1').glob(f'M{n:02}_*'))
        with tempfile.TemporaryDirectory() as temp:
            js=Path(temp)/'module.js'
            js.write_text(re.search('<script>(.*?)</script>',path.read_text(),re.S)[1])
            subprocess.run(['node','--check',str(js)],check=True,capture_output=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    failures=[];errors=[];modules=[];predictions=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1280,'height':800},reduced_motion='reduce')
            page.route('**/*',lambda route: route.continue_() if route.request.url.startswith(f'http://127.0.0.1:{server.server_port}/') else route.abort())
            page.on('pageerror',lambda error:errors.append(str(error)))
            for n in range(17,24):
                path=next((ROOT/'module_v1').glob(f'M{n:02}_*'))
                page.goto(f'http://127.0.0.1:{server.server_port}/'+quote(str(path.relative_to(ROOT))))
                print(f'Checking M{n:02}',flush=True)
                try:
                    modules.append(audit(page,n,failures))
                    predictions.extend(prediction_checks(page,n,failures,args.output))
                except Exception:
                    page.screenshot(path=str(args.output/f'M{n:02}-failure.png'))
                    print(json.dumps(failures,ensure_ascii=False),flush=True)
                    raise
                if n in (18,19,20,21,23):
                    page.locator('.station').nth(1).click()
                    page.screenshot(path=str(args.output/f'M{n:02}-goals.png'))
                    jump(page,'p2')
                    page.locator('#p2 details summary').click()
                    layout(page,f'M{n:02} final help',failures)
                    page.screenshot(path=str(args.output/f'M{n:02}-help.png'))
            browser.close()
        reference=dict(interaction=(35-32)-(30-13),delta_deviance=float(-2*(Fraction(-40)-Fraction(-38))),odds_ratio=exp(.877))
        result=dict(modules=modules,predictions=predictions,reference=reference,failures=failures,pageerrors=errors)
        (args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps(result,ensure_ascii=False,indent=2))
        assert not failures,failures[:10]
        assert not errors,errors
    finally:
        server.shutdown();server.server_close();thread.join()


if __name__=='__main__':main()
