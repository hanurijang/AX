#!/usr/bin/env python3
"""24차 참고자료 표시·키보드 접근과 학습 이동 회귀 검사 검사.
실행: PYTHONDONTWRITEBYTECODE=1 python scripts/review_p24.py
필수: Python 3.10+, Node, Playwright, Chromium. 외부 요청 차단.
공통 화면 검사는 review_p17.py를 사용한다. 출력은 Git 제외 ref/review-p24.
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
from datetime import date
from playwright.sync_api import sync_playwright
from review_p17 import QuietHandler, layout

ROOT=Path(__file__).resolve().parents[1]
CASES=[(n,n+1 if n<37 else None,next(c for c,limit in enumerate([7,16,23,29,37],1) if (n+1 if n<37 else n)<=limit)) for n in range(1,38)]


def audit_references(page, config, failures, context):
    refs=page.locator('#end .refs')
    links=refs.locator('a.refsource')
    assert len(config)>0 and links.count()==len(config)
    assert [r['n'] for r in config]==list(range(1,len(config)+1))
    for text in page.locator('.cite').all_text_contents():
        assert all(int(n) in [r['n'] for r in config] for n in re.findall(r'\d+',text))
    page.keyboard.press('Tab')  # Establish keyboard modality for :focus-visible.
    for i,row in enumerate(config):
        link=links.nth(i)
        assert urlparse(row['url']).scheme=='https' and urlparse(row['url']).hostname
        assert not re.search(r'\s',row['url'])
        assert row['title'] and row['org'] and date.fromisoformat(row['date'][:10])<=date(2026,11,2)
        assert link.get_attribute('href')==row['url']
        assert link.get_attribute('target')=='_blank' and 'noopener' in link.get_attribute('rel').split()
        assert link.inner_text()==row['title']+' (새 탭)'
        assert refs.locator('.refmeta').nth(i).inner_text()==row['org']+' · '+row['date']
        link.focus();assert link.evaluate('e=>document.activeElement===e')
        assert link.evaluate('e=>getComputedStyle(e).outlineStyle')=='solid'
        box=link.bounding_box();area=refs.bounding_box()
        assert box['y']>=area['y']-1 and box['y']+box['height']<=area['y']+area['height']+1
    # While a source link has focus, slide shortcuts must not steal scrolling keys.
    links.first.focus();refs.evaluate('e=>e.scrollTop=0')
    if refs.evaluate('e=>e.scrollHeight>e.clientHeight+3'):
        page.keyboard.press('PageDown');page.wait_for_timeout(200)
        down=refs.evaluate('e=>e.scrollTop');assert down>0
        page.keyboard.press('PageUp');page.wait_for_timeout(200)
        assert refs.evaluate('e=>e.scrollTop')<down
    page.keyboard.press('ArrowLeft')
    assert page.locator('.slide.on').get_attribute('id')=='end'
    # The ordinary slide shortcut still works outside the references.
    page.locator('#prev').focus();page.keyboard.press('ArrowLeft')
    assert page.locator('.slide.on').get_attribute('id')!='end'
    page.locator('#next').click();assert page.locator('.slide.on').get_attribute('id')=='end'
    refs.evaluate('e=>e.scrollTop=0')
    layout(page,context+' references',failures)
    return len(config)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium',default=shutil.which('chromium'))
    parser.add_argument('--output',type=Path,default=ROOT/'ref/review-p24')
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
                    config=page.evaluate('('+re.search(r'var REFS=(\[.*?\n\]);',path.read_text(),re.S)[1]+')')
                    ref_count=audit_references(page,config,failures,f'M{n:02} {width}')
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
                    checks.append(dict(module=n,target=str(expected.relative_to(ROOT)),viewport=[width,height],keyboard=True,pointer=True,references=ref_count))
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
