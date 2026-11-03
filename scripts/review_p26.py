#!/usr/bin/env python3
"""26차 전체 그림·본문 검수의 재실행 검사.
python scripts/review_p26.py --output /tmp/ax-review/p26 [--screenshots]
수동 내용 감수를 대체하지 않는다. 외부 요청은 차단한다.
"""
import argparse,json,re,subprocess,tempfile
from pathlib import Path
from functools import partial
from threading import Thread
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from lxml import html
from review_p17 import QuietHandler,layout
ROOT=Path(__file__).resolve().parents[1]

def svg_collisions(page):
    return page.evaluate('''()=>{let out=[];for(const g of document.querySelectorAll('.slide.on svg')){const ts=[...g.querySelectorAll('text')].filter(t=>t.textContent.trim());for(let i=0;i<ts.length;i++)for(let j=i+1;j<ts.length;j++){const a=ts[i].getBoundingClientRect(),b=ts[j].getBoundingClientRect(),w=Math.min(a.right,b.right)-Math.max(a.left,b.left),h=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);if(w>2&&h>2&&w*h>Math.min(a.width*a.height,b.width*b.height)*.2)out.push({svg:g.id,text:[ts[i].textContent,ts[j].textContent]});}}return out}''')

def main():
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,default=Path('/tmp/ax-review/p26'));a.add_argument('--screenshots',action='store_true');args=a.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    failures=[];errors=[];collisions=[];modules=[];counts={'slides':0,'svgs':0,'quizzes':0,'range_states':0,'expanded_help':0}
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));thread=Thread(target=server.serve_forever);thread.start()
    try:
      with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1280,'height':800})
        page.route('**/*',lambda r:r.continue_() if r.request.url.startswith('http://127.0.0.1:') else r.abort())
        page.on('pageerror',lambda e:errors.append(str(e)))
        for path in sorted((ROOT/'module_v1').glob('*.html')):
          m=path.name[:3];source=path.read_text();doc=html.fromstring(source)
          bad=[e.tag for e in doc.iter() if isinstance(e.tag,str) and '<' in e.tag]
          if bad:failures.append({'context':m,'malformed_tags':bad})
          with tempfile.NamedTemporaryFile(suffix='.js',mode='w') as f:
            f.write('\n'.join(doc.xpath('//script/text()')));f.flush();r=subprocess.run(['node','--check',f.name],capture_output=True,text=True)
            if r.returncode:failures.append({'context':m,'syntax':r.stderr})
          page.goto(f'http://127.0.0.1:{server.server_port}/module_v1/{path.name}')
          page.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important}')
          quiz=page.evaluate('('+re.search(r'var QUIZ=(\[.*?\n\]);',source,re.S)[1]+')')
          total=page.locator('.slide').count();counts['svgs']+=page.locator('svg').count()
          for i in range(total):
            page.evaluate('i=>document.querySelectorAll(".slide").forEach((s,j)=>s.classList.toggle("on",i===j))',i)
            slide=page.locator('.slide.on');sid=slide.get_attribute('id') or str(i);ctx=m+'/'+sid;counts['slides']+=1
            layout(page,ctx,failures)
            for issue in svg_collisions(page):collisions.append({'context':ctx,**issue})
            if re.fullmatch('q[1-6]',sid):
              q=quiz[int(sid[1:])-1];slide.locator('.opts button').nth(q['ans']).click();counts['quizzes']+=1
              if slide.locator('.fbp.ok').count()!=1:failures.append({'context':ctx,'quiz':'correct answer not accepted'})
              layout(page,ctx+' answered',failures)
            if sid in ('p1','p3'):
              ranges=slide.locator('input[type=range]')
              for k in range(ranges.count()):
                control=ranges.nth(k);original=control.input_value()
                for attr in ('min','max'):
                  control.evaluate('(e,a)=>{e.value=e[a];e.dispatchEvent(new Event("input",{bubbles:true}));}',attr);counts['range_states']+=1;layout(page,ctx+' '+str(k)+' '+attr,failures)
                control.evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',original)
              details=slide.locator('details')
              for k in range(details.count()):
                details.nth(k).locator('summary').click();counts['expanded_help']+=1;layout(page,ctx+' help',failures);details.nth(k).locator('summary').click()
            if args.screenshots and (sid.startswith('s-4') or sid in ('p1','p3')):
              dest=args.output/m;dest.mkdir(exist_ok=True);page.screenshot(path=str(dest/f'{sid}.png'))
          modules.append({'module':m,'slides':total,'quizzes':len(quiz)});print(m,total,flush=True)
        browser.close()
    finally:server.shutdown();server.server_close();thread.join()
    result={'viewport':[1280,800],'counts':counts,'modules':modules,'failures':failures,'pageerrors':errors,'svg_collisions':collisions}
    (args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({**counts,'failures':len(failures),'pageerrors':len(errors),'collision_screens':len(set(x['context'] for x in collisions))},ensure_ascii=False))
    assert not failures and not errors and not collisions,(failures[:8],errors,collisions[:8])

if __name__=='__main__':main()
