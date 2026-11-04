#!/usr/bin/env python3
"""M30–M37 visuals, independent math/geometry, and viewer/export verification."""
import argparse,json,re
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from lxml import etree
import numpy as np
from scipy import stats,optimize,special
from PIL import Image
from playwright.sync_api import sync_playwright
from review_p17 import QuietHandler,layout
from review_p26 import svg_collisions
ROOT=Path(__file__).resolve().parents[1]
TARGETS=[(30,'m30-mle'),(30,'m30-bayes'),(30,'m30-prior'),(31,'m31-trace'),(31,'m31-acf'),(31,'m31-diff'),(32,'m32-axis'),(32,'m32-cont'),(32,'m32-p1-svg'),(32,'m32-p3-svg'),(33,'m33-vs'),(33,'m33-km'),(33,'m33-dend'),(34,'m34-cm'),(34,'m34-roc'),(34,'m34-err'),(35,'m35-ideal'),(35,'m35-kind'),(35,'m35-solve'),(36,'m36-bif'),(36,'m36-ode'),(36,'m36-logi'),(36,'m36-eq'),(36,'m36-sir'),(36,'m36-ext'),(37,'m37-mat'),(37,'m37-p3-svg')]

def arr(n,name):
 s=next((ROOT/'module_v1').glob(f'M{n:02}_*')).read_text();m=re.search(r'\b'+name+r'\s*=\s*(?=\[)',s);return np.array(json.JSONDecoder().raw_decode(s[m.end():])[0])

def table(page,selector):return page.locator(selector+' tbody tr').evaluate_all('rs=>rs.map(r=>[...r.cells].map(c=>c.textContent))')

def goto_asset(page,eid):
 position=page.locator('#'+eid).evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e.closest(".slide"))')
 for _ in range(position):page.locator('#next').click()
 assert page.locator('.slide.on #'+eid).count()==1


def value(n,name):
 source=next((ROOT/'module_v1').glob(f'M{n:02}_*')).read_text();m=re.search(r'\b'+name+r'\s*=\s*',source);return json.JSONDecoder().raw_decode(source[m.end():])[0]

def number(text):return float(text.replace('−','-'))

def regression(y,*xs):
 X=np.column_stack([np.ones(len(y)),*xs]);coef=np.linalg.lstsq(X,y,rcond=None)[0];r=y-X@coef;df=len(y)-X.shape[1];se=np.sqrt(np.diag(np.linalg.inv(X.T@X)*(r@r/df)));return coef,se,df

def coefficient_table(page,selector,coef,se,df):
 rows=table(page,selector);bounds=np.column_stack([coef-stats.t.ppf(.975,df)*se,coef+stats.t.ppf(.975,df)*se]);pvalues=2*stats.t.sf(abs(coef/se),df)
 for i,row in enumerate(rows):
  assert abs(number(row[1])-coef[i])<.00051 and abs(number(row[2])-se[i])<.00051
  assert np.max(abs(np.array([number(x) for x in row[3].split('~')])-bounds[i]))<.0051
  assert pvalues[i]<.0001 if row[4].startswith('<') else abs(pvalues[i]-number(row[4]))<.000051

def numeric(page,n,eid,check):
 # Independent numerical and geometry checks are defined below.
 numerical_checks(page,n,eid,check)


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'ref/visual-stage5-20261104');parser.add_argument('--modules',type=int,nargs='+');args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));thread=Thread(target=server.serve_forever,daemon=True);thread.start()
 failures=[];errors=[];counts={'modules':0,'views':0,'states':0,'viewer_assets':0,'export_files':0,'tables':0,'SVGs':0,'keyboard_events':0,'reference_snapshots':0};catalog=[]
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=browser.new_page(reduced_motion='reduce',accept_downloads=True)
   def press(key):
    counts['keyboard_events']+=1;page.keyboard.press(key)
   page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{server.server_port}/') else r.abort());page.on('pageerror',lambda e:errors.append(str(e)))
   for width,height in [(1280,800),(1920,1080)]:
    page.set_viewport_size({'width':width,'height':height})
    seen_modules=set()
    for n,eid in TARGETS:
     if args.modules and n not in args.modules:continue
     file=next((ROOT/'module_v1').glob(f'M{n:02}_*'));page.goto(f'http://127.0.0.1:{server.server_port}/module_v1/{file.name}');page.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important}')
     if width==1280 and n not in seen_modules:
      seen_modules.add(n);counts['modules']+=1
      assets=page.locator('.slide svg,.slide table').evaluate_all('es=>es.map((e,i)=>({index:i+1,id:e.id,type:e.tagName.toLowerCase(),label:e.getAttribute("aria-label")||(e.caption&&e.caption.textContent)||"",caption:e.tagName.toLowerCase()==="table"?!!e.caption:null,scoped:e.tagName.toLowerCase()==="table"?[...e.querySelectorAll("th")].every(th=>th.hasAttribute("scope")):null}))')
      assert all(a['label'] for a in assets)
      assert all(a['caption'] and a['scoped'] for a in assets if a['type']=='table')
      counts['tables']+=sum(a['type']=='table' for a in assets);counts['SVGs']+=sum(a['type']=='svg' for a in assets)
      catalog.extend({'module':f'M{n:02}',**a} for a in assets)
     goto_asset(page,eid);counts['views']+=1
     def check(tag):
      counts['states']+=1;context=f'M{n:02}/{eid}/{width}/{tag}';layout(page,context,failures);failures.extend({'context':context,**issue} for issue in svg_collisions(page))
     check('initial')
     options=page.locator('.slide.on .v3-controls button,.slide.on .v2-controls button,.slide.on button.mbtn')
     for k in range(options.count()):options.nth(k).click();check('option-'+str(k))
     numeric(page,n,eid,check)
     page.screenshot(path=str(args.output/f'M{n:02}-{eid}-{width}.png'))
     original_slide=page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)');assets=page.locator('.slide.on svg,.slide.on table').count();page.locator('.v3-open').click()
     assert page.locator('#v3-visual-dialog').evaluate('d=>d.open')
     for i in range(assets):
      page.locator('#v3-visual-select').select_option(str(i));counts['viewer_assets']+=1
      preview=page.locator('.v3-sheet > *');tag=preview.evaluate('e=>e.tagName.toLowerCase()');assert page.locator('#v3-visual-svg').is_disabled()==(tag!='svg')
      if tag=='svg':
       assert preview.get_attribute('role')=='img'
       ids=preview.locator('[id]').evaluate_all('es=>es.map(e=>e.id)');assert len(ids)==len(set(ids)) and all(v.startswith('v3-copy-') for v in ids)
     if n==36 and eid=='m36-sir' and width==1280:
      page.locator('#v3-visual-zoom').fill('200');page.locator('#v3-visual-zoom').dispatch_event('input');assert page.locator('#v3-visual-scale').inner_text()=='200%'
      for selector,suffix in [('#v3-visual-svg','svg'),('#v3-visual-png','png')]:
       with page.expect_download() as info:page.locator(selector).click()
       download=info.value;out=args.output/f'viewer-export.{suffix}';download.save_as(out);counts['export_files']+=1
       if suffix=='svg':assert etree.parse(str(out)).getroot().get('viewBox')
       else:assert max(Image.open(out).size)==3840
     press('ArrowRight');assert page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)')==original_slide
     for _ in range(10):
      press('Tab');assert page.evaluate('document.getElementById("v3-visual-dialog").contains(document.activeElement)')
     for _ in range(3):
      press('Shift+Tab');assert page.evaluate('document.getElementById("v3-visual-dialog").contains(document.activeElement)')
     if n in [31,33,36,37]:page.screenshot(path=str(args.output/f'M{n:02}-{eid}-viewer-{width}.png'))
     press('Escape');page.wait_for_function('!document.getElementById("v3-visual-dialog").open');assert page.locator('.v3-open').evaluate('e=>e===document.activeElement');assert page.locator('.v3-sheet > *').count()==0
     press('ArrowRight');assert page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)')==original_slide
     page.evaluate('document.activeElement.blur()');press('ArrowRight');assert page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)')==original_slide+1
     page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');press('ArrowLeft');assert page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)')==original_slide
     if n==36 and eid=='m36-sir' and width==1280:
      page.locator('.v3-open').click();counts['reference_snapshots']+=1
      refs=page.locator('.v3-sheet svg').evaluate('s=>[...s.querySelectorAll("[marker-end]")].map(e=>e.getAttribute("marker-end"))');assert refs and all('v3-copy-' in r for r in refs);press('Escape')
   browser.close()
 finally:server.shutdown();server.server_close();thread.join()
 result={'counts':counts,'failures':failures,'pageerrors':errors,'catalog':catalog};(args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'counts':counts,'failures':failures,'pageerrors':errors},ensure_ascii=False,indent=2));assert not failures and not errors

def numerical_checks(page,n,eid,check):
 if n==30:
  x=arr(30,'XS')[:5];m=x.mean();sd=20/np.sqrt(5)
  if eid=='m30-mle':
   path=page.locator('#m30-mle path').first.get_attribute('d');p=np.array(re.findall(r'[-+]?\d*\.?\d+(?:e[-+]?\d+)?',path),float).reshape(-1,2);mus=520+np.arange(141)*.5
   assert np.allclose(p[:,0],50+(mus-520)/70*354,atol=.051) and np.allclose(p[:,1],130-((-(mus-m)**2/(2*sd**2))+8)/8*116,atol=.051)
  if eid=='m30-prior':
   rows=table(page,'#m30-prior');v=1/(1/15**2+5/20**2);pred=[[m,sd,stats.norm.sf(550,m,sd)],[v*(520/15**2+5*m/20**2),np.sqrt(v),0]];pred[1][2]=stats.norm.sf(550,*pred[1][:2]);actual=np.array([[number(t) for t in r[1:]] for r in rows]);assert np.allclose(actual,pred,atol=.051)
 if n==31 and eid=='m31-acf':
  import gzip
  source=json.loads(gzip.decompress((ROOT/'data/visual_stage2/m31_normal_chains.json.gz').read_bytes()));a=np.array(source['chains'])[:,1001:,:];data=value(31,'V5MCMC')
  for j in range(3):
   z=a[:,:,j]-a[:,:,j].mean(1,keepdims=True);expected=[np.mean(np.sum(z[:,:5000-k]*z[:,k:],axis=1)/np.sum(z*z,axis=1)) for k in range(21)];assert np.allclose(expected,data['acf'][j],atol=1e-14)
   pts=page.locator('#m31-acf polyline').nth(j).get_attribute('points');xy=np.array([list(map(float,p.split(','))) for p in pts.split()]);assert np.allclose(xy[:,1],118-(np.array(expected)+.1)/1.1*90)
  rows=table(page,'#m31-diag');assert len(rows)==3 and int(rows[2][2].replace(',',''))==5050
 if n==32:
  dx=arr(32,'DX');corr=np.corrcoef(dx.T);eig=np.linalg.eigvalsh(corr)[::-1];ratios=eig/5
  if eid=='m32-axis':assert abs(float(page.locator('#m32-axis').get_attribute('data-correlation'))-corr[0,2])<1e-12
  if eid=='m32-cont':
   rows=table(page,'#m32-cont');assert np.allclose([number(r[1]) for r in rows],eig,atol=.00051);assert np.allclose([number(r[2].replace('%','')) for r in rows],ratios*100,atol=.051)
  if eid=='m32-p1-svg':
   for r in [-.95,-.8,0,.8,.95]:
    page.locator('#m32-r').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',r);check('sample-r-'+str(r));points=page.locator('#m32-p1-svg circle[data-x]').evaluate_all('es=>es.map(e=>[+e.dataset.x,+e.dataset.y,+e.getAttribute("cx"),+e.getAttribute("cy")])');a=np.array(points);assert a.shape==(80,4);assert np.allclose(a[:,:2].mean(0),0,atol=1e-12) and np.allclose(a[:,:2].var(0,ddof=1),1);assert abs(np.corrcoef(a[:,:2].T)[0,1]-r)<1e-12;assert np.allclose(a[:,2],14+(a[:,0]+4)/8*180) and np.allclose(a[:,3],184-(a[:,1]+4)/8*180);assert np.max(abs(a[:,:2]))<4
  if eid=='m32-p3-svg':
   selected=dx[np.array([49,40,10,1,2])-1];z=(selected-dx.mean(0))/dx.std(0,ddof=1);assert np.max(abs(z))<3
 if n==33:
  if eid=='m33-km':
   pts=arr(33,'CP');cent=np.array([[2,45],[4.5,52],[3.2,68]],float);mu=pts.mean(0);sd=pts.std(0);z=(pts-mu)/sd;c=(cent-mu)/sd
   for _ in range(12):
    lab=((z[:,None,:]-c[None,:,:])**2).sum(2).argmin(1);c=np.array([z[lab==i].mean(0) for i in range(3)])
   rows=table(page,'#m33-centers');assert sum(int(row[1]) for row in rows)==60
   assert np.allclose([[number(v) for v in row[2:]] for row in rows],c*sd+mu,atol=.051)
  if eid=='m33-dend':
   from scipy.cluster.hierarchy import linkage,fcluster
   pts=arr(33,'CP');indices=arr(33,'DPS').astype(int);z=(pts-pts.mean(0))/pts.std(0);L=linkage(z[indices],method='average');assert len(set(fcluster(L,1.6,criterion='distance')))==3 and len(set(fcluster(L,.7,criterion='distance')))==5

 if n==34:
  p,neg=arr(34,'SPOS'),arr(34,'SNEG')
  if eid=='m34-cm':assert [[int(v) for v in row[1:]] for row in table(page,'#m34-cm')]==[[32,16,48],[8,144,152],[40,160,200]]
  if eid=='m34-roc':
   for name,positive,negative in [('A',p,neg),('B',arr(34,'SPB'),arr(34,'SNB'))]:
    auc=((positive[:,None]>negative).sum()+.5*(positive[:,None]==negative).sum())/(len(positive)*len(negative));pts=page.locator('#m34-roc path[data-model="'+name+'"]').get_attribute('d');xy=np.array(re.findall(r'[-+]?\d*\.?\d+(?:e[-+]?\d+)?',pts),float).reshape(-1,2);x=(xy[:,0]-52)/210;y=(236-xy[:,1])/210;assert abs(np.trapezoid(y,x)-auc)<.0006
  if eid=='m34-err':
   a=np.array([2,-3,-5,5,0]);b=np.array([2,-3,-5,20,0]);expect=np.array([[np.mean(v*v),np.sqrt(np.mean(v*v)),np.mean(abs(v))] for v in [a,b]]).T;rows=table(page,'#m34-err');assert np.allclose([[number(t) for t in r[1:]] for r in rows],expect,atol=.0051)
 if n==35 and eid=='m35-kind':
  paths=page.locator('#m35-kind path[data-walk]').evaluate_all('es=>es.map(e=>e.getAttribute("d"))');assert len(paths)==5
  for d in paths:
   xy=np.array(re.findall(r'[-+]?\d*\.?\d+',d),float).reshape(-1,2);v=20-(xy[:,1]-44)/182*40;assert np.allclose(abs(np.diff(v)),1,atol=.03) and np.max(abs(v))<=20
 if n==36:
  def pathpoints(selector):
   d=page.locator(selector).first.get_attribute('d');return np.array(re.findall(r'[-+]?\d*\.?\d+(?:e[-+]?\d+)?',d),float).reshape(-1,2)
  if eid=='m36-bif':
   xy=pathpoints('#m36-bif path[stroke="#B42318"]');assert np.allclose(xy[:,1],232-10*1.1**np.arange(16)/50*192,atol=.051)
  if eid=='m36-ode':
   xy=pathpoints('#m36-ode path[stroke="#B42318"]');ts=np.linspace(0,20,61);assert np.allclose(xy[:,1],124-5*np.exp(.139*ts)/90*114,atol=.051);assert 5*np.exp(.139*20)>80
  if eid=='m36-logi':
   xy=pathpoints('#m36-logi path[stroke="#B42318"]');ts=np.linspace(0,np.log(1400)/(np.log(2)/5),81);assert np.allclose(xy[:,1],226-np.exp(np.log(2)/5*ts)/1400*206,atol=.051)
  if eid=='m36-sir':
   from scipy.integrate import solve_ivp
   ts=np.arange(151);sol=solve_ivp(lambda t,y:[-.34*y[0]*y[1]/1000,.34*y[0]*y[1]/1000-.2*y[1],.2*y[1]],(0,150),[999,1,0],t_eval=ts,rtol=1e-10,atol=1e-11)
   for j,col in enumerate(['#2B8CC4','#B42318','#23704F']):
    xy=pathpoints('#m36-sir path[stroke="'+col+'"]');assert np.allclose(xy[:,1],124-sol.y[j]/1000*114,atol=.051)
   assert np.max(abs(sol.y.sum(0)-1000))<1e-8
 if n==37:
  if eid=='m37-mat':
   q=arr(37,'MQ');rows=table(page,'#m37-mat');assert np.allclose([[number(t) for t in r[1:4]] for r in rows],q) and np.allclose(q.sum(1),1)
  if eid=='m37-p3-svg':
   for i in range(3):
    page.locator('#m37-tb button').nth(i).click();page.locator('#m37-check').click();check('histogram-'+str(i));counts=page.locator('#m37-p3-svg rect[data-count]').evaluate_all('es=>es.map(e=>+e.dataset.count)');assert sum(counts)==500


if __name__=='__main__':main()
