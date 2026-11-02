#!/usr/bin/env python3
"""25차 문항·실습 키보드 조작과 슬라이드 단축키 검사.
실행: PYTHONDONTWRITEBYTECODE=1 python scripts/review_p25.py
Python 3.10+, Node, Playwright, Chromium 필요. 외부 요청 차단.
공통 도우미 review_p17.py를 사용하고 출력은 Git 제외 ref/review-p25에 저장.
"""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from threading import Thread
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from review_p17 import QuietHandler, jump, layout
ROOT=Path(__file__).resolve().parents[1]
KEYS=['ArrowRight','ArrowLeft','PageDown','PageUp']


def index(page):
    return page.evaluate("()=>[...document.querySelectorAll('.slide')].indexOf(document.querySelector('.slide.on'))")


def keep_slide(page, control):
    before=index(page);control.focus()
    for key in KEYS:
        page.keyboard.press(key);assert index(page)==before,(control,key)


def audit(page, n, source, failures):
    quiz=page.evaluate('('+re.search(r'var QUIZ=(\[.*?\n\]);',source,re.S)[1]+')')
    jump(page,'q1');keep_slide(page,page.locator('#q1 .opts button').first)
    page.locator('#q1 .opts button').nth(quiz[0]['ans']).focus();page.keyboard.press('Enter')
    assert page.locator('#q1 .fbp.ok').count()==1
    layout(page,f'M{n:02} quiz Enter',failures)
    page.locator('#q1 .back').focus();page.keyboard.press('Enter')
    assert page.locator('.slide.on').get_attribute('id')==quiz[0]['back']
    # The rail and goal jump buttons remain native buttons.
    page.locator('.station').nth(1).click()
    keep_slide(page,page.locator('.station').nth(1))
    keep_slide(page,page.locator('.gmap [data-jump]').first)
    page.locator('.gmap [data-jump]').first.focus();page.keyboard.press('Enter')
    assert page.locator('.slide.on').get_attribute('id')=='q1'
    jump(page,'p1');summary=page.locator('#p1 summary').first
    keep_slide(page,summary)
    summary.focus();page.keyboard.press('Enter');assert summary.evaluate('e=>e.parentElement.open')
    layout(page,f'M{n:02} help Enter',failures)
    page.keyboard.press('Space');assert not summary.evaluate('e=>e.parentElement.open')
    jump(page,'p2');card=page.locator('#p2-pool .dcard').first
    count=page.locator('#p2-pool .dcard').count();answer=card.get_attribute('data-ans')
    keep_slide(page,card);keep_slide(page,page.locator('#p2-bins .bin').first)
    card.focus();page.keyboard.press('Enter');assert 'sel' in card.get_attribute('class').split()
    page.keyboard.press('Space');assert 'sel' not in card.get_attribute('class').split()
    page.keyboard.press('Enter')
    page.get_by_role('button',name=answer+' 칸에 놓기',exact=True).focus();page.keyboard.press('Space')
    assert page.locator('#p2-count').inner_text()==f'1 / {count}'
    layout(page,f'M{n:02} card Space',failures)
    page.locator('#p2-reset').focus();page.keyboard.press('Enter')
    assert page.locator('#p2-pool .dcard').count()==count
    jump(page,'p3');button=page.locator('#p3 button').first
    keep_slide(page,button);button.focus();page.keyboard.press('Enter')
    assert page.locator('.slide.on').get_attribute('id')=='p3'
    layout(page,f'M{n:02} practice Enter',failures)
    # Exercise a real range control, including its own input event handlers.
    jump(page,'p1')
    if page.locator('#p1 input[type=range]').count()==0:jump(page,'p3')
    slider=page.locator('.slide.on input[type=range]').first
    before=index(page);value=float(slider.input_value());high=float(slider.get_attribute('max'))
    slider.focus();page.keyboard.press('ArrowRight' if value<high else 'ArrowLeft')
    assert index(page)==before and float(slider.input_value())!=value
    # Modified keyboard commands must not become slide commands.
    jump(page,'q1');page.locator('body').evaluate('e=>document.activeElement.blur()')
    for key in ['Control+ArrowRight','Shift+ArrowRight','Alt+ArrowRight','Meta+ArrowRight']:
        before=index(page);page.keyboard.press(key);assert index(page)==before,key
    # Synthetic defensive cases; these are not an end-to-end IME test.
    for mode in ['composing','prevented']:
        before=index(page)
        page.evaluate("""mode=>{const e=new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true,isComposing:mode==='composing'});if(mode==='prevented')e.preventDefault();document.body.dispatchEvent(e);} """,mode)
        assert index(page)==before,mode
    # Background and explicit footer navigation keep the original shortcuts.
    for key,delta in [('ArrowRight',1),('ArrowLeft',-1),('PageDown',1),('PageUp',-1)]:
        page.locator('body').evaluate('e=>document.activeElement.blur()')
        before=index(page);page.keyboard.press(key);assert index(page)==before+delta,key
    page.locator('#prev').focus();before=index(page);page.keyboard.press('ArrowRight');assert index(page)==before+1
    page.locator('#prev').focus();page.keyboard.press('ArrowLeft');assert index(page)==before
    return dict(module=n,protected_controls=7,protected_key_cases=28,modifier_cases=4,synthetic_cases=2,navigation_cases=6,range_cases=1,native_activation=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium',default=shutil.which('chromium'))
    parser.add_argument('--output',type=Path,default=ROOT/'ref/review-p25')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True);assert args.chromium
    (args.output/'result.json').unlink(missing_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}/'
    failures=[];errors=[];checks=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
            page=browser.new_page(viewport=dict(width=1280,height=800),reduced_motion='reduce')
            page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
            page.on('pageerror',lambda e:errors.append(str(e)))
            for n in range(1,38):
                path=next((ROOT/'module_v1').glob(f'M{n:02}_*'));source=path.read_text()
                with tempfile.TemporaryDirectory() as tmp:
                    js=Path(tmp)/'check.js';js.write_text(re.search('<script>(.*?)</script>',source,re.S)[1]);subprocess.run(['node','--check',str(js)],check=True,capture_output=True)
                response=page.goto(base+quote(str(path.relative_to(ROOT))));assert response.status==200
                print(f'Checking M{n:02}',flush=True)
                try:checks.append(audit(page,n,source,failures))
                except Exception:
                    page.screenshot(path=str(args.output/f'M{n:02}-failure.png'));raise
                if n in (1,14,37):
                    jump(page,'p2');page.locator('#p2-pool .dcard').first.focus();page.screenshot(path=str(args.output/f'M{n:02}-keyboard.png'))
            browser.close()
        result=dict(checks=checks,failures=failures,pageerrors=errors)
        (args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
        assert not failures,failures
        assert not errors,errors
    finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':main()
