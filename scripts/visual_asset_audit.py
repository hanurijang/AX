#!/usr/bin/env python3
"""Read-only browser audit for the visual redesign worklist.

Does not modify modules. Network is restricted to the temporary localhost server.
Font measurements are logical SVG units, not physical screen pixels.
"""
import argparse
import json
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from review_p17 import QuietHandler

ROOT = Path(__file__).resolve().parents[1]

MEASURE = r'''(outside=false) => {
 const svgs=[...document.querySelectorAll('svg')];
 const slides=[...document.querySelectorAll('.slide')];
 const slide=document.querySelector('.slide.on');
 return svgs.filter(s=>outside?!s.closest('.slide'):slide.contains(s)).map(s=>{
   const text=[...s.querySelectorAll('text')].filter(t=>t.textContent.trim());
   const sizes=text.map(t=>parseFloat(getComputedStyle(t).fontSize));
   return {key:'svg:'+ (svgs.indexOf(s)+1),id:s.id,slide:slides.indexOf(s.closest('.slide'))+1,
    slideId:s.closest('.slide')?.id||'',textCount:text.length,minFont:sizes.length?Math.min(...sizes):null,
    under12:sizes.filter(x=>x<12).length,under10:sizes.filter(x=>x<10).length,
    label:s.getAttribute('aria-label')||'',role:s.getAttribute('role')||'',
    titles:s.querySelectorAll('title').length,descriptions:s.querySelectorAll('desc').length,
    text:text.map(t=>t.textContent.trim()).join(' | '),
    nodes:s.querySelectorAll('*').length};
 });
}'''


def snapshot(page):
    return page.evaluate("""()=>Object.fromEntries([...document.querySelectorAll('.slide.on svg')].map(s=>[
      'svg:'+([...document.querySelectorAll('svg')].indexOf(s)+1),s.innerHTML]))""")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'ref/visual-stage1-20261104')
    parser.add_argument('--modules',nargs='*')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    results=[];errors=[]
    pilot={'M05':'m5-town','M10':'m10-tci','M18':'m18-band','M29':'m29-did',
           'M31':'m31-trace','M32':'m32-load'}
    try:
      with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1280,'height':800},reduced_motion='reduce')
        page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{server.server_port}/') else r.abort())
        page.on('pageerror',lambda e:errors.append(str(e)))
        for path in sorted((ROOT/'module_v1').glob('*.html')):
          module=path.name[:3]
          if args.modules and module not in args.modules:continue
          page.goto(f'http://127.0.0.1:{server.server_port}/module_v1/{quote(path.name)}')
          page.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important}')
          page.evaluate('document.fonts.ready')
          total=page.locator('.slide').count();assets=[];controls=[];states=0
          for idx in range(total):
            page.evaluate('i=>document.querySelectorAll(".slide").forEach((s,j)=>s.classList.toggle("on",i===j))',idx)
            assets.extend(page.evaluate(MEASURE))
            slide=page.locator('.slide.on')
            for k in range(slide.locator('input[type=range]').count()):
              control=slide.locator('input[type=range]').nth(k);original=control.input_value()
              info=control.evaluate('(e)=>({id:e.id,min:e.min,max:e.max,step:e.step})')
              changed=set()
              for position in ('min','middle','max'):
                before=snapshot(page)
                control.evaluate('''(e,pos)=>{const lo=+e.min,hi=+e.max,step=+e.step||1;
                  e.value=pos==='min'?lo:pos==='max'?hi:lo+Math.round((hi-lo)/2/step)*step;
                  e.dispatchEvent(new Event('input',{bubbles:true}));}''',position)
                after=snapshot(page);states+=1
                changed.update(key for key in after if after[key]!=before.get(key))
              control.evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',original)
              controls.append({**info,'slide':idx+1,'kind':'range','affected':sorted(changed)})
            if slide.get_attribute('id') in ('p1','p3'):
              buttons=slide.locator('button.mbtn')
              for k in range(buttons.count()):
                button=buttons.nth(k);before=snapshot(page);label=button.inner_text()
                button.click();after=snapshot(page);states+=1
                controls.append({'kind':'choice','slide':idx+1,'label':label,
                                 'affected':[key for key in after if after[key]!=before.get(key)]})
          assets.extend(page.evaluate('('+MEASURE+')(true)'))
          tables=page.evaluate('''()=>[...document.querySelectorAll('table')].map((t,i)=>({key:'table:'+(i+1),
             captions:t.querySelectorAll('caption').length,headers:t.querySelectorAll('th').length,
             scoped:t.querySelectorAll('th[scope]').length,rows:t.rows.length,
             slide:[...document.querySelectorAll('.slide')].indexOf(t.closest('.slide'))+1}))''')
          if module in pilot:
            page.evaluate('id=>document.querySelectorAll(".slide").forEach(s=>s.classList.toggle("on",s.contains(document.getElementById(id))))',pilot[module])
            page.screenshot(path=str(args.output/f'{module}-baseline.png'))
          results.append({'module':module,'slides':total,'assets':assets,'tables':tables,'controls':controls,'states':states})
          print(f'{module}: {total} slides, {len(assets)} SVG, {states} control states',flush=True)
        browser.close()
    finally:
      server.shutdown();server.server_close();thread.join()
    report={'viewport':[1280,800],'modules':results,'pageerrors':errors,
            'notes':'Read-only structure/control audit; does not certify statistical validity or all layout conditions.'}
    (args.output/'runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'modules':len(results),'slides':sum(m['slides'] for m in results),
       'svg':sum(len(m['assets']) for m in results),'tables':sum(len(m['tables']) for m in results),
       'states':sum(m['states'] for m in results),'pageerrors':len(errors)},ensure_ascii=False))
    assert not errors,errors

if __name__=='__main__':main()
