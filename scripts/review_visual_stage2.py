#!/usr/bin/env python3
"""Pilot visual review: independent numerical checks + controls + two viewport sizes.

Writes screenshots and standalone SVGs; does not edit module source.
"""
import argparse,gzip,hashlib,json,re
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import numpy as np
from scipy import integrate,optimize,stats,signal
from playwright.sync_api import sync_playwright
from review_p17 import QuietHandler,layout,jump
from review_p26 import svg_collisions
from generate_m31_visual_data import diagnostic
ROOT=Path(__file__).resolve().parents[1]

def array(n,name):
 s=next((ROOT/'module_v1').glob(f'M{n:02}_*')).read_text();m=re.search(r'\b'+name+r'\s*=\s*(?=[\[{])',s)
 return np.array(json.JSONDecoder().raw_decode(s[m.end():])[0])

def independent_checks():
 meta=json.loads((ROOT/'data/visual_stage2/m31_summary.json').read_text());raw={}
 for name,digest in meta['full_chain_files'].items():
  file=ROOT/'data/visual_stage2'/name;assert hashlib.sha256(file.read_bytes()).hexdigest()==digest
  raw[name]=json.loads(gzip.decompress(file.read_bytes()))
 normal=np.array(raw['m31_normal_chains.json.gz']['chains'])[:,1001:];poisson=np.array(raw['m31_poisson_chains.json.gz']['chains'])[:,1001:]
 assert normal.shape==(5,5000,3) and poisson.shape==(5,5000,2)
 delta=normal[:,:,1]-normal[:,:,0];hist=np.histogram(delta,meta['delta']['edges'])[0]
 assert hist.sum()==25000 and np.array_equal(hist,array(31,'DH'))
 for k,p in meta['delta']['probabilities'].items():assert abs((delta>float(k)).mean()-p)<1e-14
 for j,key in [(0,'muA'),(1,'muB'),(2,'sigma')]:assert abs(normal[:,:,j].mean()-meta['diagnostics'][key]['mean'])<1e-12
 assert np.max(abs(np.quantile(delta,[.025,.975])-array(31,'DCI')))<1e-12
 # Independent integration of the common-SD posterior, with both means integrated out.
 ga,gb=array(31,'GA'),array(31,'GB');ss=sum(np.sum((y-y.mean())**2) for y in [ga,gb]);power=len(ga)+len(gb)-2
 mode=np.sqrt(ss/power);offset=-power*np.log(mode)-ss/(2*mode**2)
 def weight(sd):return np.exp(-power*np.log(sd)-ss/(2*sd**2)-offset) if sd>0 else 0
 mass=integrate.quad(weight,0,100,epsabs=1e-10)[0];mean=gb.mean()-ga.mean();factor=np.sqrt(1/len(ga)+1/len(gb))
 def cdf(v):return integrate.quad(lambda sd:weight(sd)*stats.norm.cdf(v,mean,sd*factor),0,100,epsabs=1e-9)[0]/mass
 exact_ci=[optimize.brentq(lambda v:cdf(v)-p,-40,70) for p in [.025,.975]]
 assert abs(delta.mean()-mean)<.15
 assert np.max(abs(np.quantile(delta,[.025,.975])-exact_ci))<.25
 assert abs((delta>10).mean()-(1-cdf(10)))<.01
 # Independent rectangular integration for the two-dimensional Poisson posterior.
 x,y=array(31,'FX'),array(31,'FY');a=np.linspace(-7,1,1601);b=np.linspace(0,1.2,1201)
 logw=a[:,None]*y.sum()+b[None,:]*np.sum(x*y)-np.exp(a[:,None])*np.exp(b[:,None]*x[None,:]).sum(axis=1)[None,:]
 w=np.exp(logw-logw.max());w/=w.sum();wa=w.sum(axis=1);wb=w.sum(axis=0)
 assert max(wa[0],wa[-1],wb[0],wb[-1])<1e-8
 quadrature={}
 for grid,p,idx,key in [(a,wa,0,'a'),(b,wb,1,'b')]:
  avg=float(grid@p);ci=np.interp([.025,.975],np.cumsum(p),grid)
  assert abs(poisson[:,:,idx].mean()-avg)<.04
  assert np.max(abs(np.quantile(poisson[:,:,idx],[.025,.975])-ci))<.06
  quadrature[key]={'mean':avg,'ci':ci.tolist()}
 # A known AR(1) process checks the scale of the custom ESS diagnostic.
 rng=np.random.default_rng(903);iid=rng.normal(size=(5,6000));ar=signal.lfilter([1],[1,-.8],iid,axis=1)[:,1000:]
 ess=diagnostic(ar)['ess_bulk'];expected=ar.size*(1-.8)/(1+.8)
 assert .6<ess/expected<1.5
 shifted=ar+np.arange(5)[:,None]*2;assert diagnostic(shifted)['rhat']>1.1
 dx=array(32,'DX');vm=dx.mean(0);vs=dx.std(0,ddof=1);z=(dx-vm)/vs;corr=np.corrcoef(dx.T)
 eig,vec=np.linalg.eigh(corr);idx=np.argsort(eig)[::-1];eig=eig[idx];vec=vec[:,idx]
 for k,inds in [(0,[0,1,2]),(1,[3,4])]:
  if vec[inds,k].sum()<0:vec[:,k]*=-1
 assert np.max(abs(array(32,'DS')-z@vec[:,:2]))<1e-9
 assert np.max(abs(array(32,'LOAD')-vec[:,:2]*np.sqrt(eig[:2])))<1e-9
 assert np.max(abs(array(32,'CONT')-eig/eig.sum()))<1e-9
 return {'retained_count':int(delta.size),'exact_delta_ci':exact_ci,'empirical_delta_ci':np.quantile(delta,[.025,.975]).tolist(),'poisson_quadrature':quadrature,'AR1_ess':ess,'AR1_expected_ess':expected,'PCA_points':len(dx),'max_rhat':max(d['rhat'] for d in meta['diagnostics'].values()),'min_bulk_ess':min(d['ess_bulk'] for d in meta['diagnostics'].values())}


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'ref/visual-stage2-20261104');ap.add_argument('--export',type=Path);ap.add_argument('--modules',type=int,nargs='+');args=ap.parse_args();args.export=args.export.resolve() if args.export else None;args.output.mkdir(parents=True,exist_ok=True)
 numerical=independent_checks();fail=[];errors=[];states=0;exports=[]
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));thread=Thread(target=server.serve_forever,daemon=True);thread.start()
 targets=[(5,'m5-town'),(10,'m10-tci'),(13,'m13-bars3'),(18,'m18-band'),(29,'m29-did'),(31,'m31-trace'),(31,'m31-p1-svg'),(31,'m31-diff'),(31,'m31-pois'),(32,'m32-load'),(32,'m32-scores')]
 if args.modules:targets=[target for target in targets if target[0] in args.modules]
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=browser.new_page(reduced_motion='reduce')
   page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{server.server_port}/') else r.abort());page.on('pageerror',lambda e:errors.append(str(e)))
   for width,height in [(1280,800),(1920,1080)]:
    page.set_viewport_size({'width':width,'height':height})
    for n,eid in targets:
     source=next((ROOT/'module_v1').glob(f'M{n:02}_*'));page.goto(f'http://127.0.0.1:{server.server_port}/module_v1/{source.name}');page.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important}')
     sid=page.locator('#'+eid).evaluate('e=>e.closest(".slide").id');jump(page,sid)
     def check(tag):
      nonlocal states
      states+=1;ctx=f'{n}/{eid}/{width}/{tag}';layout(page,ctx,fail);fail.extend({'context':ctx,**c} for c in svg_collisions(page))
      outside=page.locator('.slide.on').evaluate('''s=>{const v=document.querySelector('.viewport').getBoundingClientRect();return [...s.querySelectorAll('.v2-table,.v2-controls,.v2-note')].filter(e=>{const r=e.getBoundingClientRect();return r.left<v.left-1||r.right>v.right+1||r.top<v.top-1||r.bottom>v.bottom+1}).map(e=>e.id||e.className)}''')
      if outside:fail.append({'context':ctx,'outside':outside})
     check('initial')
     controls=page.locator('.slide.on .v2-controls button, .slide.on #m31-nb button')
     initially_pressed=[k for k in range(controls.count()) if controls.nth(k).get_attribute('aria-pressed')=='true']
     for k in range(controls.count()):controls.nth(k).click();check('button-'+str(k))
     if n==5:
      rows=page.locator('#m5-town-table tbody tr').evaluate_all('rows=>rows.map(r=>({...r.dataset}))')
      assert [int(r['count']) for r in rows]==[100,101]
      assert abs(float(rows[0]['mean'])-5088)<1e-12 and abs(float(rows[1]['mean'])-608800/101)<1e-9
      assert [float(r['median']) for r in rows]==[5088,5091]
     if n==13:
      lo=float(page.locator('#m13-bars3').get_attribute('data-low'));hi=float(page.locator('#m13-bars3').get_attribute('data-high'));drug=array(13,'DRUG')
      assert abs(lo-(drug.mean()-drug.std(ddof=1)))<1e-9 and abs(hi-(drug.mean()+drug.std(ddof=1)))<1e-9
     if n==18:
      vals=page.locator('#m18-band').evaluate('s=>({...s.dataset})');x=array(18,'MATH');y=array(18,'SCI');b=np.polyfit(x,y,1);yh=np.polyval(b,x);rs=np.sqrt(np.sum((y-yh)**2)/(len(x)-2));se=rs*np.sqrt(1/len(x)+(80-x.mean())**2/np.sum((x-x.mean())**2));t=stats.t.ppf(.975,8);center=np.polyval(b,80)
      assert abs(float(vals['meanLow'])-(center-t*se))<.002
      assert float(vals['predLow'])<float(vals['meanLow'])<float(vals['meanHigh'])<float(vals['predHigh'])
     if n==29:assert abs(float(page.locator('#m29-did').get_attribute('data-did'))+.3)<1e-12
     if n==31 and eid=='m31-p1-svg':
      outside_old=False
      for seed_change in range(12):
       page.locator('#m31-re').click();check('pi-seed-'+str(seed_change))
       params=page.locator('#m31-p1-svg').evaluate('s=>({lo:+s.dataset.piLow,hi:+s.dataset.piHigh,points:[...s.querySelectorAll("circle[data-pi-estimate]")].map(p=>({v:+p.dataset.piEstimate,y:+p.getAttribute("cy")}))})')
       assert len(params['points'])==5
       for point in params['points']:
        assert params['lo']<=point['v']<=params['hi']
        assert abs(point['y']-(170+(point['v']-params['lo'])/(params['hi']-params['lo'])*-125))<1e-8
        outside_old=outside_old or point['v']<2.6 or point['v']>3.7
      assert outside_old,'seeds must exercise a value outside the former clamp limits'
     if n==31 and eid=='m31-diff':assert page.locator('#m31-diff').get_attribute('data-count')=='25000'
     if n==32 and eid=='m32-scores':assert page.locator('#m32-scores circle[data-sample]').count()==50
     page.screenshot(path=str(args.output/f'M{n:02}-{eid}-{width}-changed.png'))
     for k in initially_pressed:controls.nth(k).click()
     check('restored')
     page.screenshot(path=str(args.output/f'M{n:02}-{eid}-{width}.png'))
     if args.export and width==1920 and page.locator('#'+eid).evaluate('e=>e.tagName.toLowerCase()')=='svg':
      args.export.mkdir(parents=True,exist_ok=True)
      content=page.locator('#'+eid).evaluate('s=>{const c=s.cloneNode(true);c.setAttribute("xmlns","http://www.w3.org/2000/svg");c.setAttribute("width",s.viewBox.baseVal.width);c.setAttribute("height",s.viewBox.baseVal.height);c.style.fontFamily=getComputedStyle(s).fontFamily;return new XMLSerializer().serializeToString(c)}')
      f=args.export/(eid+'.svg');f.write_text(content+'\n');exports.append(str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f))
   # Selected core scene exported at actual 4K raster size.
   page.set_viewport_size({'width':3840,'height':2160});source=next((ROOT/'module_v1').glob('M05_*'));page.goto(f'http://127.0.0.1:{server.server_port}/module_v1/{source.name}');jump(page,'s-4-2d');page.add_style_tag(content='*{animation:none!important;transition:none!important}');page.screenshot(path=str(args.output/'M05-4K.png'))
   browser.close()
 finally:server.shutdown();server.server_close();thread.join()
 result={'numerical':numerical,'viewport_states':states,'failures':fail,'pageerrors':errors,'exports':exports};(args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2));assert not fail and not errors

if __name__=='__main__':main()
