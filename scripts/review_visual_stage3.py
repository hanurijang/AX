#!/usr/bin/env python3
"""M01–M16 redraw, native tables, and modal export verification."""
import argparse,itertools,json,re
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from lxml import etree
import numpy as np
from scipy import stats
from PIL import Image
from playwright.sync_api import sync_playwright
from review_p17 import QuietHandler,layout
from review_p26 import svg_collisions
ROOT=Path(__file__).resolve().parents[1]
TARGETS={1:'fig-bar',2:'m2-worlds',3:'m3-cost',4:'m4-raw',5:'m5-five',6:'m6-cond',7:'m7-z',8:'m8-rand',9:'m9-sqrt',10:'m10-twenty',11:'m11-p',12:'m12-calc',13:'m13-case',14:'m14-case',15:'m15-tukey',16:'m16-exp'}

def arr(n,name):
 s=next((ROOT/'module_v1').glob(f'M{n:02}_*')).read_text();m=re.search(r'\b'+name+r'\s*=\s*(?=\[)',s);return np.array(json.JSONDecoder().raw_decode(s[m.end():])[0])

def table(page,selector):return page.locator(selector+' tbody tr').evaluate_all('rs=>rs.map(r=>[...r.cells].map(c=>c.textContent))')

def goto_asset(page,eid):
 position=page.locator('#'+eid).evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e.closest(".slide"))')
 for _ in range(position):page.locator('#next').click()
 assert page.locator('.slide.on #'+eid).count()==1


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'ref/visual-stage3-20261104');parser.add_argument('--modules',type=int,nargs='+');args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
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
    for n,eid in TARGETS.items():
     if args.modules and n not in args.modules:continue
     file=next((ROOT/'module_v1').glob(f'M{n:02}_*'));page.goto(f'http://127.0.0.1:{server.server_port}/module_v1/{file.name}');page.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important}')
     if width==1280:
      counts['modules']+=1
      assets=page.locator('.slide svg,.slide table').evaluate_all('es=>es.map((e,i)=>({index:i+1,id:e.id,type:e.tagName.toLowerCase(),label:e.getAttribute("aria-label")||(e.caption&&e.caption.textContent)||"",caption:e.tagName.toLowerCase()==="table"?!!e.caption:null,scoped:e.tagName.toLowerCase()==="table"?[...e.querySelectorAll("th")].every(th=>th.hasAttribute("scope")):null}))')
      assert all(a['label'] for a in assets)
      assert all(a['caption'] and a['scoped'] for a in assets if a['type']=='table')
      counts['tables']+=sum(a['type']=='table' for a in assets);counts['SVGs']+=sum(a['type']=='svg' for a in assets)
      catalog.extend({'module':f'M{n:02}',**a} for a in assets)
     goto_asset(page,eid);counts['views']+=1
     def check(tag):
      counts['states']+=1;context=f'M{n:02}/{eid}/{width}/{tag}';layout(page,context,failures);failures.extend({'context':context,**issue} for issue in svg_collisions(page))
     check('initial')
     options=page.locator('.slide.on .v3-controls button')
     for k in range(options.count()):options.nth(k).click();check('option-'+str(k))
     if n==1:
      source=file.read_text();values=np.array(json.loads(re.search(r'var CASE=\{.*?values:(\[[^\]]*\])',source,re.S).group(1)))
      assert abs(float(page.locator('#fig-bar').get_attribute('data-mean'))-values.mean())<1e-12
      assert np.array_equal(page.locator('#fig-bar rect[data-value]').evaluate_all('es=>es.map(e=>+e.dataset.value)'),values)
     if n==4:
      counts4=page.locator('#m4-raw rect[data-count]').evaluate_all('es=>es.map(e=>+e.dataset.count)');expected=np.histogram(arr(4,'HEIGHTS')[:30],np.arange(145,195,5))[0]
      assert np.array_equal(counts4,expected) and sum(counts4)==30
      cells=[float(v) for row in table(page,'#m4-raw-values') for v in row[1:]];assert np.allclose(cells,arr(4,'HEIGHTS')[:30])
     if n==5:assert np.array_equal(sorted(page.locator('#m5-five circle[data-score]').evaluate_all('es=>es.map(e=>+e.dataset.score)')),np.sort(arr(5,'SC')))
     if n==6:
      cells=np.array([list(map(float,row[1:])) for row in table(page,'#m6-cond')]);assert np.all(cells[:,:3].sum(axis=1)==1) and np.all(cells[:,3]==1)
     if n==10:
      samples=[]
      for i in range(2):
       options.nth(i).click();samples+=page.locator('#m10-twenty circle[data-ci-low]').evaluate_all('es=>es.map(e=>({lo:+e.dataset.ciLow,hi:+e.dataset.ciHigh}))')
      assert len(samples)==20
      assert sum(s['lo']<=167.6<=s['hi'] for s in samples)==int(page.locator('#m10-twenty').get_attribute('data-included'))
     if n==11:
      values=np.concatenate([arr(11,'DRUG'),arr(11,'PLAC')]).astype(int);total=int(values.sum());extreme=sum(abs(2*sum(c)-total)>=76 for c in itertools.combinations(values,7))
      assert extreme==int(page.locator('#m11-p').get_attribute('data-extreme'))==70
      assert page.locator('#m11-p').get_attribute('data-total')=='3432'
     if n==12:
      a,b=arr(12,'DRUG'),arr(12,'PLAC');pooled=np.sqrt((np.sum((a-a.mean())**2)+np.sum((b-b.mean())**2))/(len(a)+len(b)-2));se=pooled*np.sqrt(1/len(a)+1/len(b));t=(a.mean()-b.mean())/se;cells=table(page,'#m12-calc')
      for actual,wanted in [(float(cells[1][-1]),pooled),(float(cells[2][-1]),se),(float(cells[3][-1].replace('−','-')),t)]:assert abs(actual-wanted)<.005
     if n==14:
      cells=table(page,'#m14-case');before=arr(14,'BEFORE');after=arr(14,'DRUG');assert np.array_equal(np.array([list(map(float,r[1:])) for r in cells]),np.column_stack([before,after,after-before]))
     if n==15:
      gs=[arr(15,k) for k in ['FA','FB','FC']];mse=sum(np.sum((g-g.mean())**2) for g in gs)/15;se=np.sqrt(mse/6);q=stats.studentized_range.ppf(.95,3,15)
      for row,(i,j) in zip(table(page,'#m15-tukey'),[(0,1),(0,2),(1,2)]):
       difference=gs[j].mean()-gs[i].mean();bounds=[float(v) for v in row[2].split(' ~ ')];assert abs(float(row[1])-difference)<.005 and np.max(abs(np.array(bounds)-[difference-q*se,difference+q*se]))<.005
       p=stats.studentized_range.sf(abs(difference)/se,3,15)
       assert p<.0001 if row[3].startswith('<') else abs(p-float(row[3]))<.00005
     if n==16:
      observed=arr(16,'BEET');expected=stats.contingency.expected_freq(observed);tables=page.locator('#m16-exp table')
      for idx,wanted in [(0,observed),(1,expected)]:
       rows=tables.nth(idx).locator('tbody tr').evaluate_all('rs=>rs.slice(0,2).map(r=>[...r.cells].slice(1,3).map(c=>+c.textContent))');assert np.allclose(rows,wanted)
     if n==16:
      assert page.locator('#m16-res thead th').nth(1).text_content()=='χ²'
      rows=table(page,'#m16-res');assert rows[2][1]=='사용하지 않음'
      expected_p=[stats.chi2_contingency(observed,correction=False).pvalue,stats.chi2_contingency(observed,correction=True).pvalue,stats.fisher_exact(observed).pvalue]
      assert all(abs(float(row[2])-p)<.0005 for row,p in zip(rows,expected_p))
     page.screenshot(path=str(args.output/f'M{n:02}-{width}.png'))
     original_slide=page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)');assets=page.locator('.slide.on svg,.slide.on table').count();page.locator('.v3-open').click()
     assert page.locator('#v3-visual-dialog').evaluate('d=>d.open')
     for i in range(assets):
      page.locator('#v3-visual-select').select_option(str(i));counts['viewer_assets']+=1
      preview=page.locator('.v3-sheet > *');tag=preview.evaluate('e=>e.tagName.toLowerCase()');assert page.locator('#v3-visual-svg').is_disabled()==(tag!='svg')
      if tag=='svg':
       assert preview.get_attribute('role')=='img'
       ids=preview.locator('[id]').evaluate_all('es=>es.map(e=>e.id)');assert len(ids)==len(set(ids)) and all(v.startswith('v3-copy-') for v in ids)
     if n==1 and width==1280:
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
     if n in [4,5,14,16]:page.screenshot(path=str(args.output/f'M{n:02}-viewer-{width}.png'))
     press('Escape');page.wait_for_function('!document.getElementById("v3-visual-dialog").open');assert page.locator('.v3-open').evaluate('e=>e===document.activeElement');assert page.locator('.v3-sheet > *').count()==0
     press('ArrowRight');assert page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)')==original_slide
     page.evaluate('document.activeElement.blur()');press('ArrowRight');assert page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)')==original_slide+1
     page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');press('ArrowLeft');assert page.locator('.slide.on').evaluate('e=>[...document.querySelectorAll(".slide")].indexOf(e)')==original_slide
     if n==1 and width==1280:
      page.locator('.station').first.click();page.locator('.v3-open').click();counts['reference_snapshots']+=1
      refs=page.locator('.v3-sheet svg').evaluate('s=>[...s.querySelectorAll("[href],[marker-end]")].map(e=>e.getAttribute("href")||e.getAttribute("marker-end"))')
      assert refs and all('v3-copy-' in r for r in refs)
      assert page.locator('.v3-sheet [role="button"],.v3-sheet [tabindex]').count()==0
      assert page.locator('.slide.on [role="button"]').count()>0
      press('Escape')
   browser.close()
 finally:server.shutdown();server.server_close();thread.join()
 result={'counts':counts,'failures':failures,'pageerrors':errors,'catalog':catalog};(args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'counts':counts,'failures':failures,'pageerrors':errors},ensure_ascii=False,indent=2));assert not failures and not errors

if __name__=='__main__':main()
