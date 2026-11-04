#!/usr/bin/env python3
"""M17–M29 visuals, independent math/geometry, and viewer/export verification."""
import argparse,itertools,json,re
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
TARGETS=[(17,'m17-rank'),(18,'m18-coef'),(19,'m19-table'),(19,'m19-case'),(19,'m19-std'),(20,'m20-int'),(20,'m20-anova'),(20,'m20-mc'),(20,'m20-vif'),(20,'m20-curve'),(20,'m20-p1-svg'),(21,'m21-orci'),(21,'m21-odds'),(22,'m22-table'),(23,'m23-aic'),(23,'m23-wald'),(23,'m23-vs'),(24,'m24-pub'),(25,'m25-tbl'),(26,'m26-tree'),(26,'m26-p1-svg'),(27,'m27-myth'),(27,'m27-pairs'),(28,'m28-graph'),(29,'m29-psm')]

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
 if n==17:
  rows=table(page,'#m17-rank');x,y=arr(17,'MATH'),arr(17,'SCI');assert np.array_equal(np.array([[number(v) for v in row[1:]] for row in rows]),np.column_stack([x,stats.rankdata(x),y,stats.rankdata(y)]))
 if n==18:coefficient_table(page,'#m18-coef',*regression(arr(18,'SCI'),arr(18,'MATH')))
 if n==19:
  coef,se,df=regression(arr(19,'WT'),arr(19,'HT'),arr(19,'WS'))
  if eid=='m19-table':coefficient_table(page,'#m19-table',coef,se,df)
  if eid=='m19-case':
   allrows=[]
   for b in page.locator('#m19-pages button').all():b.click();check('raw-data-page');allrows+=table(page,'#m19-case')
   actual=np.array([[number(v) for v in row] for row in allrows]);expected=np.column_stack([np.arange(1,21),arr(19,'WT'),arr(19,'HT'),arr(19,'WS'),arr(19,'EX')]);assert np.array_equal(actual,expected)
  if eid=='m19-std':
   rows=table(page,'#m19-std');assert np.allclose([number(r[2]) for r in rows],coef[1:]*np.std(np.column_stack([arr(19,'HT'),arr(19,'WS')]),axis=0,ddof=1),atol=.005)
 if n==20:
  mc=value(20,'MC')
  if eid=='m20-anova':
   tw=value(20,'TW');Y=[];design=[]
   for key,values in tw.items():
    a,b=2*int(key[0])-1,2*int(key[1])-1
    for y in values:Y.append(y);design.append([1,a,b,a*b])
   X=np.array(design);Y=np.array(Y);coef=np.linalg.lstsq(X,Y,rcond=None)[0];res=Y-X@coef;ss=coef[1:]**2*len(Y);mse=res@res/16;rows=table(page,'#m20-anova')
   assert np.allclose([number(row[1]) for row in rows[:3]],ss,atol=.05)
   assert np.allclose([number(row[3]) for row in rows[:3]],ss/mse,atol=.005)
   assert abs(number(rows[3][1])-res@res)<.05
  if eid=='m20-mc':
   points=page.locator('#m20-mc circle[data-coefficient]').evaluate_all('es=>es.map(e=>({r:e.dataset.rho,v:+e.dataset.coefficient,y:+e.getAttribute("cy")}))');assert len(points)==600
   assert sum(p['v']>7 for p in points)>0
   for p in points:assert abs(p['y']-(226+(p['v']+6)/18*(30-226)))<1e-8
  if eid=='m20-p1-svg':
   for i,r in enumerate(['0','0.5','0.9','0.99']):
    page.locator('#m20-r button').nth(i).click();check('coefficients-'+r)
    points=page.locator('#m20-p1-svg circle[data-b1]').evaluate_all('es=>es.map(e=>({b1:+e.dataset.b1,b2:+e.dataset.b2,x:+e.getAttribute("cx"),y:+e.getAttribute("cy")}))');assert len(points)==150
    assert np.array_equal([[p['b1'],p['b2']] for p in points],mc[r])
    for p in points:
     assert abs(p['x']-(50+(p['b1']+6)/18*390))<1e-8
     assert abs(p['y']-(176+(p['b2']+6)/18*(10-176)))<1e-8
  if eid=='m20-vif':
   coords=np.array([float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?',page.locator('#m20-vif path[data-vif-curve]').get_attribute('d'))]).reshape(-1,2);r=np.linspace(0,.985,201);assert np.max(abs(coords[:,1]-(124-1/(1-r*r)*2.5)))<1e-8
   assert 1/(1-r[-1]**2)>30
  if eid=='m20-curve':
   x=arr(20,'CVX');y=arr(20,'CVY');xx=np.linspace(-.3,9.3,201)
   for degree in [1,2,6]:
    path=page.locator(f'#m20-curve path[data-degree="{degree}"]');coords=np.array([float(v) for v in re.findall(r'-?\d+(?:\.\d+)?',path.get_attribute('d'))]).reshape(-1,2)
    yy=np.polynomial.polynomial.polyval((xx-4.5)/4.5,np.polynomial.polynomial.polyfit((x-4.5)/4.5,y,degree));assert np.max(abs(coords[:,1]-(170+(yy+1)/10*-150)))<.051
    assert path.evaluate('e=>!!e.closest("g[clip-path]")')
 if n==21:
  if eid=='m21-odds':
   rows=table(page,'#m21-odds');assert rows[-2][-1]=='6' and rows[-1][-1]=='2';assert abs((.8/.2)/(.4/.6)-6)<1e-12
  else:
   x,y=arr(21,'BX'),arr(21,'BY');X=np.column_stack([np.ones(len(x)),x]);fit=optimize.minimize(lambda b:np.sum(np.logaddexp(0,X@b)-y*(X@b)),[0,0],jac=lambda b:X.T@(special.expit(X@b)-y),method='BFGS');p=special.expit(X@fit.x);se=np.sqrt(np.diag(np.linalg.inv(X.T@(p[:,None]*(1-p[:,None])*X))));expected=np.exp([fit.x[1],fit.x[1]-stats.norm.ppf(.975)*se[1],fit.x[1]+stats.norm.ppf(.975)*se[1]])
   actual=page.locator('#m21-orci').evaluate('e=>[+e.dataset.or,+e.dataset.low,+e.dataset.high]');assert np.allclose(actual,expected,atol=1e-8)
 if n==22:assert '0~m' in table(page,'#m22-table')[0][1]
 if n==23:
  if eid=='m23-aic':
   models=value(23,'MS');rows=table(page,'#m23-aic');aics=[-2*models[m]['ll']+2*models[m]['k'] for m in ['M1','M2','M3']]
   assert np.allclose([number(row[3]) for row in rows],aics,atol=.0051) and np.allclose([number(row[4]) for row in rows],np.array(aics)-min(aics),atol=.0051)
  if eid=='m23-wald':
   x,y=arr(23,'FX'),arr(23,'FY');rows=table(page,'#m23-wald')
   for degree,indices in [(1,[(0,0),(1,1)]),(2,[(2,2)])]:
    X=np.column_stack([x**j for j in range(degree+1)]);fit=optimize.minimize(lambda b:np.sum(np.exp(X@b)-y*(X@b)),[-2.54,.577] if degree==1 else [-3,.72,-.01],jac=lambda b:X.T@(np.exp(X@b)-y),method='BFGS');se=np.sqrt(np.diag(np.linalg.inv(X.T@(np.exp(X@fit.x)[:,None]*X))))
    for ri,j in indices:
     assert abs(number(rows[ri][1])-fit.x[j])<.000006 and abs(number(rows[ri][2])-se[j])<.000051
 if n==24:
  data=value(24,'PUB')['4'];assert sum(data['ha'])==1000 and sum(data['hp'])==129 and all(a>=b for a,b in zip(data['ha'],data['hp']))
  assert [int(r[1]) for r in table(page,'#m24-summary')]==[1000,129]
 if n==25:assert table(page,'#m25-tbl')[1][1]=='|r|'
 if n==26:
  if eid=='m26-tree':
   rows=table(page,'#m26-tree');assert [[int(v) for v in r[1:]] for r in rows]==[[100,80,20],[900,45,855],[1000,125,875]];assert 45/125==.36
  else:
   for diff,index in [(0,11),(15,11),(-5,0),(7,2)]:
    for selector,val in [('#m26-D',diff),('#m26-n',index)]:page.locator(selector).evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',val)
    check('BF-boundary');text=page.locator('#m26-b').inner_text();assert text!='0.000'
    if diff==0 and index==11:assert '< 0.032' in page.locator('#m26-p1-svg').text_content()
 if n==27 and eid=='m27-pairs':
  for r in table(page,'#m27-pairs'):
   m=int(r[0]);pairs=m*(m-1)//2;assert int(r[1])==pairs and abs(number(r[2])-pairs*.05)<1e-9;assert abs(number(r[3])-.05/pairs)/(.05/pairs)<.005
 if n==29:
  z,t,ps,pairs=arr(29,'DZ'),arr(29,'DT'),arr(29,'DPS'),arr(29,'DPR').astype(int);assert len(pairs)==69 and np.all(t[pairs[:,0]]==1) and np.all(t[pairs[:,1]]==0)
  denom=np.sqrt((z[t==1].var(ddof=1)+z[t==0].var(ddof=1))/2);before=(z[t==1].mean()-z[t==0].mean())/denom;after=(z[pairs[:,0]].mean()-z[pairs[:,1]].mean())/denom;actual=page.locator('#m29-psm').evaluate('s=>[+s.dataset.before,+s.dataset.after,+s.dataset.denominator]');assert np.allclose(actual,[before,after,denom],atol=1e-12) and abs(after)<abs(before)
  for label in [0,1]:assert abs(np.histogram(ps[t==label],np.arange(0,1.01,.1))[0].sum()/sum(t==label)-1)<1e-12

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'ref/visual-stage4-20261104');parser.add_argument('--modules',type=int,nargs='+');args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
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
     options=page.locator('.slide.on .v3-controls button,.slide.on button.mbtn')
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
     if n==28 and width==1280:
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
     if n in [19,20,28,29]:page.screenshot(path=str(args.output/f'M{n:02}-{eid}-viewer-{width}.png'))
     press('Escape');page.wait_for_function('!document.getElementById("v3-visual-dialog").open');assert page.locator('.v3-open').evaluate('e=>e===document.activeElement');assert page.locator('.v3-sheet > *').count()==0
     press('ArrowRight');assert page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)')==original_slide
     page.evaluate('document.activeElement.blur()');press('ArrowRight');assert page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)')==original_slide+1
     page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');press('ArrowLeft');assert page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)')==original_slide
     if n==28 and width==1280:
      page.locator('.v3-open').click();counts['reference_snapshots']+=1
      refs=page.locator('.v3-sheet svg').evaluate('s=>[...s.querySelectorAll("[marker-end]")].map(e=>e.getAttribute("marker-end"))');assert refs and all('v3-copy-' in r for r in refs);press('Escape')
   browser.close()
 finally:server.shutdown();server.server_close();thread.join()
 result={'counts':counts,'failures':failures,'pageerrors':errors,'catalog':catalog};(args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'counts':counts,'failures':failures,'pageerrors':errors},ensure_ascii=False,indent=2));assert not failures and not errors

if __name__=='__main__':main()
