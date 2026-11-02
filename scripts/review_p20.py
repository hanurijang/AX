#!/usr/bin/env python3
"""20차 M24~M29 연결 검수. Python 3.10+, Node, Playwright, Chromium 필요.
실행: python scripts/review_p20.py [--chromium PATH] [--output PATH]
외부 요청은 차단하며 결과·화면은 Git 제외 ref/review-p20에 저장한다.
"""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from fractions import Fraction
from math import exp, sqrt, erfc
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
        layout(page,f'M{n} prediction {guess}',failures)
        expanded_help(page,f'M{n} prediction {guess}',failures)
        if guess==hi:
            page.locator('#p3 details summary').click()
            page.screenshot(path=str(output/f'M{n:02}-prediction.png'))
            page.locator('#p3 details summary').click()
        set_range(page,f'#m{n}-g',hi if guess==lo else lo)
        assert page.locator(f'#m{n}-msg3').get_attribute('class') == 'pmsg'
        # These modules retain previously revealed reference results.
        assert page.locator(f'#m{n}-act').inner_text() == actual
        results.append(dict(module=n,guess=guess,actual=actual))
    return results


def numeric_checks(page, n, failures):
    results=[]
    jump(page,'p3')
    if n==25:
        for i,(delta,sd) in enumerate([(9,9.9),(.5,10),(5,10),(5,2.5)]):
            page.locator('#m25-qs button').nth(i).click()
            expected=Fraction(str(delta))/Fraction(str(sd))
            step=float(page.locator('#m25-g').get_attribute('step'))
            set_range(page,'#m25-g',round(float(expected)/step)*step);page.locator('#m25-check').click()
            assert abs(text_number(page,'#m25-act')-float(expected))<=.0051
            layout(page,f'M25 d case {i}',failures)
            results.append(dict(module=n,case=i,d=float(expected)))
    elif n==26:
        for i,q in enumerate([Fraction(1,10),Fraction(3,10),Fraction(1,2),Fraction(4,5)]):
            for j,alpha in enumerate([Fraction(1,20),Fraction(1,200)]):
                page.locator('#m26-qq button').nth(i).click();page.locator('#m26-qa button').nth(j).click()
                tp=1000*q*Fraction(4,5);fp=1000*(1-q)*alpha;ratio=fp/(fp+tp)
                set_range(page,'#m26-g',round(100*float(ratio)));page.locator('#m26-check').click()
                assert abs(text_number(page,'#m26-act')-100*float(ratio))<=.051
                assert abs(text_number(page,'#m26-cnt')-float(tp+fp))<=.051
                if i==0 and j==1:assert '위양성 4.5건' in page.locator('#m26-p3-svg').text_content()
                layout(page,f'M26 Q/alpha {i}/{j}',failures)
                expanded_help(page,f'M26 Q/alpha {i}/{j}',failures)
                results.append(dict(module=n,q=float(q),alpha=float(alpha),ratio=float(ratio),count=float(tp+fp)))
        jump(page,'p1')
        for difference,index,size in [(0,0,5),(7,2,20),(.5,6,200),(0,11,5000)]:
            set_range(page,'#m26-D',difference);set_range(page,'#m26-n',index)
            variance=200/size
            bf=sqrt(variance/(variance+100))*exp(difference*difference*100/(2*variance*(variance+100)))
            p=erfc(abs(difference)/sqrt(2*variance))
            assert abs(text_number(page,'#m26-b')-bf)<= (.0051 if bf>=1 else .00051)
            shown=page.locator('#m26-p').inner_text()
            assert p<.001 if '<' in shown else abs(float(shown)-p)<=.00051
            layout(page,f'M26 BF {difference}/{size}',failures)
            results.append(dict(module=n,difference=difference,size=size,bayes_factor=bf,p=p))
    elif n==27:
        for i,size in enumerate([10,20,50,100]):
            page.locator('#m27-qm button').nth(i).click();page.locator('#m27-check').click()
            pairs=sum(range(size));expected=Fraction(pairs,20);cutoff=Fraction(1,20*pairs)
            assert abs(text_number(page,'#m27-act')-float(expected))<=.0051
            assert abs(text_number(page,'#m27-bf')-float(cutoff))<=float(cutoff)*.0051
            layout(page,f'M27 pairs {size}',failures)
            results.append(dict(module=n,variables=size,pairs=pairs,expected=float(expected),cutoff=float(cutoff)))
    elif n==28:
        for i,effect in enumerate([Fraction(0),Fraction(-1,50),Fraction(-1,20)]):
            page.locator('#m28-qs button').nth(i).click();page.locator('#m28-check').click()
            expected=10*effect
            assert abs(text_number(page,'#m28-act')-float(expected))<=.0051
            layout(page,f'M28 generated effect {i}',failures)
            results.append(dict(module=n,case=i,effect=float(expected)))
    elif n==29:
        for i,row in enumerate([['2.4','1.9','2.0','1.8'],['3.0','2.6','2.5','2.6'],['2.2','2.0','2.2','1.9']]):
            before_a,after_a,before_b,after_b=map(Fraction,row)
            expected=(after_a-before_a)-(after_b-before_b)
            page.locator('#m29-qs button').nth(i).click();set_range(page,'#m29-g',float(expected));page.locator('#m29-check').click()
            assert abs(text_number(page,'#m29-act')-float(expected))<=.0051
            assert page.locator('#m29-msg3').get_attribute('class')=='pmsg ok'
            assert '평행 경향' in page.locator('#m29-msg3').inner_text()
            layout(page,f'M29 DID {i}',failures)
            expanded_help(page,f'M29 DID {i}',failures)
            results.append(dict(module=n,case=i,did=float(expected)))
    return results

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium',default=shutil.which('chromium'))
    parser.add_argument('--output',type=Path,default=ROOT/'ref/review-p20')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'result.json').unlink(missing_ok=True)
    assert args.chromium
    for n in range(24,30):
        path=next((ROOT/'module_v1').glob(f'M{n:02}_*'))
        with tempfile.TemporaryDirectory() as temp:
            js=Path(temp)/'module.js'
            js.write_text(re.search('<script>(.*?)</script>',path.read_text(),re.S)[1])
            subprocess.run(['node','--check',str(js)],check=True,capture_output=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    failures=[];errors=[];modules=[];predictions=[];numbers=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1280,'height':800},reduced_motion='reduce')
            page.route('**/*',lambda route: route.continue_() if route.request.url.startswith(f'http://127.0.0.1:{server.server_port}/') else route.abort())
            page.on('pageerror',lambda error:errors.append(str(error)))
            for n in range(24,30):
                path=next((ROOT/'module_v1').glob(f'M{n:02}_*'))
                page.goto(f'http://127.0.0.1:{server.server_port}/'+quote(str(path.relative_to(ROOT))))
                print(f'Checking M{n:02}',flush=True)
                try:
                    modules.append(audit(page,n,failures))
                    predictions.extend(prediction_checks(page,n,failures,args.output))
                    numbers.extend(numeric_checks(page,n,failures))
                except Exception:
                    page.screenshot(path=str(args.output/f'M{n:02}-failure.png'))
                    print(json.dumps(failures,ensure_ascii=False),flush=True)
                    raise
                if n in (24,25,26,27,28,29):
                    page.locator('.station').nth(1).click()
                    page.screenshot(path=str(args.output/f'M{n:02}-goals.png'))
                    jump(page,'p2')
                    page.locator('#p2 details summary').click()
                    layout(page,f'M{n:02} final help',failures)
                    page.screenshot(path=str(args.output/f'M{n:02}-help.png'))
            browser.close()
        prior=Fraction(1,10); posterior=3*prior/(3*prior+1-prior)
        reference=dict(posterior_probability=float(posterior),replication_fraction=float(Fraction(35,97)))
        assert posterior==Fraction(1,4)
        result=dict(modules=modules,predictions=predictions,numbers=numbers,reference=reference,failures=failures,pageerrors=errors)
        (args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps(result,ensure_ascii=False,indent=2))
        assert not failures,failures[:10]
        assert not errors,errors
    finally:
        server.shutdown();server.server_close();thread.join()


if __name__=='__main__':main()
