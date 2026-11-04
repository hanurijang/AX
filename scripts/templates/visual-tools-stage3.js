/* V3_VISUAL_TOOLS: current-state snapshots; no external resources or requests. */
(function(){
"use strict";
var stage=document.querySelector('.stage'),vp=document.querySelector('.viewport'),footer=document.querySelector('.bottombar');
if(!stage||!vp||!footer)return;
vp.querySelectorAll('.slide svg:not([aria-hidden="true"])').forEach(function(svg,i){svg.setAttribute('role','img');if(!svg.getAttribute('aria-label')&&!svg.getAttribute('aria-labelledby')){var title=svg.closest('.slide').querySelector('h2');svg.setAttribute('aria-label',(title?title.textContent.replace(/^Q\s*/, ''):'학습 그림')+' · 그림 '+(i+1));}});
var opener=document.createElement('button');opener.type='button';opener.className='v3-open';opener.textContent='그림·표 크게 보기';opener.setAttribute('aria-haspopup','dialog');opener.setAttribute('aria-controls','v3-visual-dialog');footer.insertBefore(opener,footer.querySelector('.spacer'));
var dialog=document.createElement('dialog');dialog.id='v3-visual-dialog';dialog.className='v3-dialog';dialog.setAttribute('aria-labelledby','v3-visual-heading');
dialog.innerHTML='<h2 id="v3-visual-heading">그림·표 크게 보기</h2><div class="v3-toolbar"><label>대상 <select id="v3-visual-select"></select></label><label>배율 <input id="v3-visual-zoom" type="range" min="100" max="250" step="25" value="100"><output id="v3-visual-scale">100%</output></label><button type="button" id="v3-visual-close">닫기</button></div><div class="v3-canvas" tabindex="0" aria-label="확대한 그림·표. 내용이 넓으면 가로로 스크롤하세요"><div class="v3-sheet"></div></div><div class="v3-toolbar"><button type="button" id="v3-visual-svg">SVG 저장</button><button type="button" id="v3-visual-png">고해상도 PNG 저장</button></div><p id="v3-visual-note" role="status" aria-live="polite"></p>';
document.body.appendChild(dialog);
var select=dialog.querySelector('select'),zoom=dialog.querySelector('input'),sheet=dialog.querySelector('.v3-sheet'),canvas=dialog.querySelector('.v3-canvas'),note=dialog.querySelector('#v3-visual-note'),svgButton=dialog.querySelector('#v3-visual-svg'),pngButton=dialog.querySelector('#v3-visual-png'),items=[],snapshot=null,busy=false;
function activeItems(){var slide=vp.querySelector('.slide.on');return slide?[].slice.call(slide.querySelectorAll('svg,table')):[];}
function update(){opener.disabled=!activeItems().length;}
function label(e,i){return (e.getAttribute('aria-label')||(e.querySelector('caption')&&e.querySelector('caption').textContent)||((e.tagName.toLowerCase()==='svg'?'그림 ':'표 ')+(i+1))).trim();}
function snapshotOf(source){
 var clone=source.cloneNode(true),original=[source].concat([].slice.call(source.querySelectorAll('*'))),copies=[clone].concat([].slice.call(clone.querySelectorAll('*'))),ids={};
 original.forEach(function(e,i){var c=copies[i];if(e.id)ids[e.id]='v3-copy-'+i+'-'+e.id;
  if(source.tagName.toLowerCase()==='svg'){var cs=getComputedStyle(e);['font-family','font-size','font-weight','font-style','fill','fill-opacity','stroke','stroke-width','stroke-opacity','stroke-dasharray','text-anchor','paint-order'].forEach(function(k){c.style.setProperty(k,cs.getPropertyValue(k));});}
 });
 copies.forEach(function(e){if(e.id)e.id=ids[e.id];if(e.getAttribute('role')==='button'){e.removeAttribute('role');e.removeAttribute('tabindex');e.style.cursor='default';}[].slice.call(e.attributes).forEach(function(a){var value=a.value.replace(/url\(["']?#([^)'"\s]+)["']?\)/g,function(m,id){return 'url(#'+(ids[id]||id)+')';});
  if(a.name==='href'||a.name==='xlink:href')value=value.replace(/^#(.+)$/,function(m,id){return '#'+(ids[id]||id);});
  if(a.name==='aria-labelledby'||a.name==='aria-describedby')value=value.split(/\s+/).map(function(id){return ids[id]||id;}).join(' ');e.setAttribute(a.name,value);});
 });
 if(source.tagName.toLowerCase()==='svg'){var box=source.viewBox.baseVal;clone.setAttribute('xmlns','http://www.w3.org/2000/svg');clone.setAttribute('width',box.width);clone.setAttribute('height',box.height);clone.style.background='white';}
 else{var caption=clone.querySelector('caption');if(caption){caption.classList.remove('v3-sr');caption.removeAttribute('style');}}
 return clone;
}
function resize(){sheet.style.width=Math.max(640,canvas.clientWidth)*Number(zoom.value)/100+'px';dialog.querySelector('output').textContent=zoom.value+'%';}
function render(){sheet.replaceChildren();snapshot=snapshotOf(items[Number(select.value)]);sheet.appendChild(snapshot);var isSVG=snapshot.tagName.toLowerCase()==='svg';svgButton.disabled=!isSVG;pngButton.disabled=!isSVG;note.textContent=isSVG?'현재 그림의 상태입니다. SVG는 벡터 원본이며, PNG는 가로·세로 중 긴 변을 3,840픽셀로 저장합니다.':'현재 표의 상태입니다. 표의 제목·행·열 머리글과 값을 크게 읽거나 복사할 수 있습니다.';resize();}
opener.onclick=function(){items=activeItems();if(!items.length)return;select.replaceChildren();items.forEach(function(e,i){var option=document.createElement('option');option.value=i;option.textContent=label(e,i);select.appendChild(option);});zoom.value='100';dialog.showModal();render();select.focus();};
function cleanup(){sheet.replaceChildren();snapshot=null;opener.focus();}
function closeViewer(){dialog.close();cleanup();}
select.onchange=render;zoom.oninput=resize;dialog.querySelector('#v3-visual-close').onclick=function(){closeViewer();};
document.addEventListener('keydown',function(e){if(dialog.open&&!dialog.contains(e.target)){e.stopImmediatePropagation();if(e.key==='Escape'){e.preventDefault();closeViewer();}else{if(['Tab','ArrowRight','ArrowLeft','PageDown','PageUp'].indexOf(e.key)>=0)e.preventDefault();select.focus();}}},true);
dialog.addEventListener('keydown',function(e){e.stopPropagation();if(e.key==='Tab'){var focusable=[].slice.call(dialog.querySelectorAll('button:not(:disabled),select:not(:disabled),input:not(:disabled),[tabindex="0"]')),first=focusable[0],last=focusable[focusable.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}if(e.key==='Escape'){e.preventDefault();closeViewer();}});
dialog.addEventListener('close',function(){if(!dialog.open&&snapshot)cleanup();});
function download(blob,suffix,index){var url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=document.title.replace(/[\\/:*?"<>|]/g,'-')+'-figure-'+(index==null?Number(select.value)+1:index)+suffix;a.click();setTimeout(function(){URL.revokeObjectURL(url);},1500);}
function xml(){return new XMLSerializer().serializeToString(snapshot);}
svgButton.onclick=function(){if(snapshot)download(new Blob([xml()],{type:'image/svg+xml;charset=utf-8'}),'.svg');};
pngButton.onclick=function(){if(!snapshot||busy)return;busy=true;pngButton.disabled=true;select.focus();var exportIndex=Number(select.value)+1,saved=snapshot.cloneNode(true),box=saved.viewBox.baseVal,scale=3840/Math.max(box.width,box.height),width=Math.round(box.width*scale),height=Math.round(box.height*scale);saved.setAttribute('width',width);saved.setAttribute('height',height);var url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(saved)],{type:'image/svg+xml;charset=utf-8'})),img=new Image();
 img.onload=function(){var out=document.createElement('canvas');out.width=width;out.height=height;var context=out.getContext('2d');context.fillStyle='white';context.fillRect(0,0,width,height);context.drawImage(img,0,0,width,height);out.toBlob(function(blob){if(blob)download(blob,'.png',exportIndex);note.textContent='PNG '+width+' × '+height+'픽셀을 저장했습니다.';busy=false;pngButton.disabled=!(snapshot&&snapshot.tagName.toLowerCase()==='svg');URL.revokeObjectURL(url);},'image/png');};
 img.onerror=function(){URL.revokeObjectURL(url);busy=false;pngButton.disabled=false;note.textContent='PNG를 만들지 못했습니다. SVG 저장을 이용해 주세요.';};img.src=url;
};
new MutationObserver(update).observe(vp,{subtree:true,attributes:true,attributeFilter:['class']});update();
})();
