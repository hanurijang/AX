#!/usr/bin/env python3
"""23차 전체 모듈 마무리 이동 검사.
실행: PYTHONDONTWRITEBYTECODE=1 python scripts/review_p23.py
필수: Python 3.10+, Node, Playwright, Chromium. 외부 요청 차단.
공통 화면 검사는 review_p17.py를 사용한다. 출력은 Git 제외 ref/review-p23.
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
from urllib.parse import quote, unquote, urlparse
from playwright.sync_api import sync_playwright
from review_p17 import QuietHandler, layout

ROOT=Path(__file__).resolve().parents[1]
CASES=[(n,n+1 if n<37 else None,next(c for c,limit in enumerate([7,16,23,29,37],1) if (n+1 if n<37 else n)<=limit)) for n in range(1,38)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium',default=shutil.which('chromium'))
    parser.add_argument('--output',type=Path,default=ROOT/'ref/review-p23')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'result.json').unlink(missing_ok=True)
    assert args.chromium
    for n,_,_ in CASES:
        source=next((ROOT/'module_v1').glob(f'M{n:02}_*')).read_text()
        with tempfile.TemporaryDirectory() as tmp:
            js=Path(tmp)/'check.js';js.write_text(re.search('<script>(.*?)</script>',source,re.S)[1])
            subprocess.run(['node','--check',str(js)],check=True,capture_output=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}/'
    errors=[];failures=[];checks=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
            for width,height in [(1280,800),(1024,768)]:
                page=browser.new_page(viewport=dict(width=width,height=height),reduced_motion='reduce')
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
                for n,target,course in CASES:
                    print(f'Checking M{n:02} {width}x{height}',flush=True)
                    path=next((ROOT/'module_v1').glob(f'M{n:02}_*'))
                    response=page.goto(base+quote(str(path.relative_to(ROOT))));assert response.status==200
                    # Real rail and final slide button, without calling private show().
                    page.locator('.station').nth(6).click()
                    while page.locator('.slide.on').get_attribute('id')!='end':page.locator('#next').click()
                    assert page.locator('#next').is_disabled()
                    link=page.locator('#end .nextlink');assert link.count()==1
                    expected=next((ROOT/'module_v1').glob(f'M{target:02}_*')) if target else ROOT/f'courses/course{course}.html'
                    href=link.get_attribute('href');assert (path.parent/href).resolve()==expected.resolve()
                    course_source=(ROOT/f'courses/course{course}.html').read_text()
                    if target:
                        title=re.search('<title>(.*?)</title>',expected.read_text())[1]
                        assert page.locator('#end .nextmod small').inner_text()==f'다음 모듈 · M{target:02} {title}'
                        assert expected.name in course_source
                    else:
                        assert '과정 마무리' in page.locator('#end .nextmod small').inner_text()
                        assert '다음 모듈' not in page.locator('#end h2').inner_text()
                    layout(page,f'M{n:02} end {width}',failures)
                    refs=page.locator('#end .refs')
                    refs.evaluate('e=>e.scrollTop=e.scrollHeight')
                    last=refs.locator('li').last.bounding_box();area=refs.bounding_box()
                    assert last['y']+last['height']<=area['y']+area['height']+1
                    refs.locator('a').last.focus()
                    assert refs.locator('a').last.evaluate('e=>document.activeElement===e')
                    refs.evaluate('e=>e.scrollTop=0')
                    link.focus();assert link.evaluate('e=>document.activeElement===e')
                    page.keyboard.press('Tab');page.keyboard.press('Shift+Tab')
                    assert link.evaluate('e=>document.activeElement===e')
                    assert link.evaluate('e=>getComputedStyle(e).outlineStyle')=='solid'
                    box=link.bounding_box();footer=page.locator('.bottombar').bounding_box()
                    assert box['y']+box['height']<=footer['y']+1
                    assert box['x']>=0 and box['x']+box['width']<=width
                    page.screenshot(path=str(args.output/f'M{n:02}-end-{width}.png'))
                    # Enter follows the ordinary anchor to the expected document.
                    with page.expect_navigation() as destination:
                        link.press('Enter')
                    assert destination.value.status==200
                    page.wait_for_url(lambda url:unquote(urlparse(str(url)).path)=='/'+str(expected.relative_to(ROOT)))
                    if target:
                        assert page.title()==title
                        assert page.locator('.slide.on').get_attribute('data-step')=='0'
                    else:
                        assert page.locator('h1').inner_text()=='베이즈·기계학습·수리 모형'
                        assert page.locator('a.card').count()==8
                    # Reload and pointer activation also reach the same target.
                    page.go_back();page.reload();page.locator('.station').nth(6).click()
                    while page.locator('.slide.on').get_attribute('id')!='end':page.locator('#next').click()
                    with page.expect_navigation() as destination:
                        page.locator('#end .nextlink').click()
                    assert destination.value.status==200
                    page.wait_for_url(lambda url:unquote(urlparse(str(url)).path)=='/'+str(expected.relative_to(ROOT)))
                    checks.append(dict(module=n,target=str(expected.relative_to(ROOT)),viewport=[width,height],keyboard=True,pointer=True))
                page.close()
            browser.close()
        result=dict(checks=checks,failures=failures,pageerrors=errors)
        (args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps(result,ensure_ascii=False,indent=2))
        assert not failures,failures
        assert not errors,errors
    finally:
        server.shutdown();server.server_close();thread.join()


if __name__=='__main__':main()
