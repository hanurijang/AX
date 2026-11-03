#!/usr/bin/env python3
"""그림의 도형 좌표와 통계량 대조: python scripts/review_p27.py.
NumPy, Playwright, Chromium 필요. 외부 요청 차단. 출력 /tmp/ax-review/p27.
"""
import json,re,itertools
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer
from threading import Thread
import numpy as np
from playwright.sync_api import sync_playwright
from review_p17 import QuietHandler,layout,set_range
from review_p26 import svg_collisions
ROOT=Path(__file__).resolve().parents[1];OUT=Path('/tmp/ax-review/p27')
def array(n,name):
 s=next((ROOT/'module_v1').glob(f'M{n:02}_*')).read_text().split('<script>')[-1];m=re.search(r'\b'+name+r'\s*=\s*([\[])',s);return json.JSONDecoder().raw_decode(s[m.start(1):])[0]
def main():
 OUT.mkdir(parents=True,exist_ok=True);fail=[];errors=[];count={'ci_batches':0,'intervals':0,'regression_settings':0,'residuals':0,'likelihood_settings':0,'polynomial_points':0};outside=0
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));thread=Thread(target=server.serve_forever);thread.start()
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=browser.new_page(viewport={'width':1280,'height':800});page.on('pageerror',lambda e:errors.append(str(e)));page.route('**/*',lambda r:r.continue_() if r.request.url.startswith('http://127.0.0.1:') else r.abort())
   def openmod(n,sid):
    f=next((ROOT/'module_v1').glob(f'M{n:02}_*'));page.goto(f'http://127.0.0.1:{server.server_port}/module_v1/{f.name}');page.add_style_tag(content='*{animation:none!important;transition:none!important}');page.evaluate('id=>document.querySelectorAll(".slide").forEach(s=>s.classList.toggle("on",s.id===id))',sid)
   def visual(ctx):
    layout(page,ctx,fail)
    fail.extend({'context':ctx,**x} for x in svg_collisions(page))
   def intervals(selector,ybottom,ytop):
    nonlocal outside
    values=page.locator(selector).evaluate('s=>({lo:+s.dataset.axisLow,hi:+s.dataset.axisHigh,lines:[...s.querySelectorAll("line[data-ci-low]")].map(e=>({lo:+e.dataset.ciLow,hi:+e.dataset.ciHigh,y1:+e.getAttribute("y1"),y2:+e.getAttribute("y2")}))})')
    for i,c in enumerate(values['lines']):
     bot,top=(ybottom,ytop) if len(values['lines'])==20 else (18+(i//24)*68+62,18+(i//24)*68+2)
     Y=lambda v:bot+(v-values['lo'])/(values['hi']-values['lo'])*(top-bot)
     assert values['lo']<=c['lo']<=c['hi']<=values['hi']
     assert abs(c['y1']-Y(c['hi']))<1e-7 and abs(c['y2']-Y(c['lo']))<1e-7
     outside+=int(c['lo']<156 or c['hi']>180);count['intervals']+=1
   openmod(10,'s-4-4a');intervals('#m10-grid',0,0);visual('M10 grid')
   page.evaluate('document.querySelectorAll(".slide").forEach(s=>s.classList.toggle("on",s.id==="p1"))')
   for ni,si in itertools.product(range(3),range(2)):
    page.locator('#m10-n button').nth(ni).click();page.locator('#m10-s button').nth(si).click()
    for k in range(12):
     page.locator('#m10-redo').click();intervals('#m10-p1-svg',186,12);count['ci_batches']+=1;visual(f'M10 {ni}/{si}/{k}')
   page.screenshot(path=str(OUT/'M10.png'))
   openmod(18,'p1');xs=np.array(array(18,'MATH'));ys=np.array(array(18,'SCI'))
   for a,b in itertools.product([-20,16,50],[.2,.73,1.4]):
    set_range(page,'#m18-a',a);set_range(page,'#m18-b',round(b*100));svg=page.locator('#m18-p1-svg');lo=float(svg.get_attribute('data-axis-low'));hi=float(svg.get_attribute('data-axis-high'));Y=lambda y:156+(y-lo)/(hi-lo)*(8-156)
    lines=svg.locator('line[data-student]').evaluate_all('es=>es.map(e=>({i:+e.dataset.student,y1:+e.getAttribute("y1"),y2:+e.getAttribute("y2")}))')
    assert len(lines)==10
    for c in lines:
     i=c['i'];assert abs(c['y1']-Y(ys[i]))<1e-7 and abs(c['y2']-Y(a+b*xs[i]))<1e-7;count['residuals']+=1
    assert abs(float(page.locator('#m18-e').inner_text())-np.sum((a+b*xs-ys)**2))<.051;count['regression_settings']+=1;visual(f'M18 {a}/{b}')
   page.screenshot(path=str(OUT/'M18.png'))
   openmod(21,'p1');xs=np.array(array(21,'BX'));ys=np.array(array(21,'BY'))
   for a,b in itertools.product([-10,-4.5,0],[0,.88,2]):
    set_range(page,'#m21-a',round(a*10));set_range(page,'#m21-b',round(b*100));ll=np.sum(ys*(a+b*xs)-np.logaddexp(0,a+b*xs));svg=page.locator('#m21-p1-svg');low=float(svg.get_attribute('data-loglik-low'));bars=svg.locator('rect[data-loglik]').evaluate_all('es=>es.map(e=>({value:+e.dataset.loglik,height:+e.getAttribute("height"),y:+e.getAttribute("y")}))')
    assert len(bars)==2 and abs(bars[0]['value']-ll)<1e-5
    for bar in bars:assert bar['y']==46 and abs(bar['height']-94*bar['value']/low)<1e-6
    assert bars[0]['value']<=bars[1]['value']+1e-5 and bars[0]['height']>=bars[1]['height']-1e-5
    count['likelihood_settings']+=1;visual(f'M21 {a}/{b}')
   page.screenshot(path=str(OUT/'M21.png'))
   openmod(23,'p1');of=array(23,'OF')
   for d in range(1,8):
    page.locator('#m23-d button').nth(d-1).click();path=page.locator('#m23-p1-svg g[clip-path] path').get_attribute('d');coords=np.array([float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',path)]).reshape(-1,2);xx=np.linspace(34,68,241);yy=np.polynomial.polynomial.polyval((xx-52)/16,of[d-1]['b']);expected=170+(yy-30)/40*(10-170)
    assert len(coords)==241 and np.max(np.abs(coords[:,1]-expected))<=.051
    assert page.locator('#m23-p1-svg clipPath rect').count()==1;count['polynomial_points']+=len(coords);visual(f'M23 {d}')
   page.screenshot(path=str(OUT/'M23.png'));browser.close()
 finally:server.shutdown();server.server_close();thread.join()
 result={'counts':count,'intervals_beyond_old_axis':outside,'failures':fail,'pageerrors':errors};(OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False));assert not fail and not errors
if __name__=='__main__':main()
