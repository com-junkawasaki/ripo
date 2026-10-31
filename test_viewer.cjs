// Runtime smoke check with a minimal DOM shim. This is NOT browser visual QA.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('viewer.html','utf8');
const code=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements={};
class Element {
 constructor(){this.value='';this.textContent='';this.innerHTML='';this.clientWidth=736;this.listeners={};}
 append(x){} addEventListener(n,f){this.listeners[n]=f;}
}
for(const id of ['ripo-case','ripo-scale','ripo-layout','ripo-time','ripo-time-value',
 'ripo-readout','ripo-network','ripo-lineage','ripo-evidence'])elements[id]=new Element();
elements['ripo-layout'].value='grid';elements['ripo-time'].value='3';
const root={querySelector:s=>elements[s.slice(1)]};
const ctx={document:{getElementById:id=>root,createElement:()=>new Element()},
 ResizeObserver:class{constructor(f){}observe(el){}},console};
vm.runInNewContext(code,ctx);
let checks=0;
for(const w of [320,736])for(let s=0;s<6;s++)for(const tau of ['0.1','0.3','1','3','10'])for(let t=0;t<6;t++){
 elements['ripo-case'].value=String(s);elements['ripo-scale'].value=tau;
 elements['ripo-time'].value=String(t);elements['ripo-network'].clientWidth=w;
 elements['ripo-lineage'].clientWidth=w;
 let baseline;
 for(const layout of ['grid','circle']){
  elements['ripo-layout'].value=layout;
  elements['ripo-layout'].listeners.input();
  const svg=elements['ripo-network'].innerHTML;
  assert(svg.includes('<svg'));assert(!/NaN|undefined|Infinity/.test(svg));
  assert.strictEqual((svg.match(/<circle /g)||[]).length,8);
  const result=elements['ripo-readout'].textContent;
  if(baseline)assert.strictEqual(result,baseline);else baseline=result;
  assert(!/undefined|NaN/.test(elements['ripo-evidence'].textContent));
  checks++;
 }
}
console.log(JSON.stringify({ui_states_checked:checks,widths:[320,736],
 checks:'scenario/scale/time/layout; finite geometry; 8 observations; layout-invariant result',
 limitation:'DOM shim only; no browser layout or pixel inspection'}));

