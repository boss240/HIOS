const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync('web/solar-history-dashboard.js','utf8');
class Element {
  constructor(){this.children=[];this.events={};this.style={};this.value='';this.attributes={};}
  replaceChildren(...v){this.children=v;} append(...v){this.children.push(...v);} add(v){this.children.push(v);}
  addEventListener(k,v){this.events[k]=v;} setAttribute(k,v){this.attributes[k]=v;}
  set innerHTML(v){throw Error('unsafe HTML');}
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const response=data=>({ok:true,json:async()=>({data})});
function setup(fetch){
  const ids=Object.fromEntries(['solarHistoryPlant','solarHistoryDate','refreshSolarHistory','solarHistoryStatus','solarHistoryRows'].map(k=>[k,new Element()]));
  vm.runInNewContext(source,{document:{querySelector:s=>ids[s.slice(1)],createElement:()=>new Element(),createElementNS:()=>new Element()},
    fetch,Option:class{constructor(label,value){this.textContent=label;this.value=value;}},Date,Number,Math});return ids;
}
const capture={scope:'device_only',dayUtc:'2026-10-03',sampleCount:290,hours:Array.from({length:24},(_,h)=>({hourUtc:`2026-10-03T${String(h).padStart(2,'0')}:00:00Z`,derivedEnergyKwh:h===0?null:1,coveredSeconds:h===0?0:h===1?3000:3600,complete:h>1}))};
test('read-only rendering distinguishes missing and partial energy with safe plant labels',async()=>{
  const calls=[];const ids=setup(async(url,options)=>{calls.push([url,options]);return response(url==='/dashboard/plants'?[{id:'a',name:'<script>bad</script>'}]:[capture]);});
  await tick();assert.equal(ids.solarHistoryPlant.children[1].textContent,'<script>bad</script>');
  ids.solarHistoryPlant.value='a';ids.solarHistoryDate.value='2026-10-03';await ids.solarHistoryPlant.events.change();
  const card=ids.solarHistoryRows.children[0],table=card.children[2].children[0];
  assert.equal(table.children.length,25);
  assert.equal(table.children[1].children[1].textContent,'—');
  assert.equal(table.children[2].children[3].textContent,'Часткова година');
  assert.equal(table.children[3].children[3].textContent,'Повна година');
  assert.ok(calls.every(([,o])=>!o.method && o.cache==='no-store'));
});
test('previous plant response cannot overwrite current selection',async()=>{
  let release;const ids=setup(async url=>url==='/dashboard/plants'?response([{id:'a',name:'A'},{id:'b',name:'B'}]):url.includes('/a/')?new Promise(r=>release=r):response([]));
  await tick();ids.solarHistoryDate.value='2026-10-03';ids.solarHistoryPlant.value='a';const old=ids.solarHistoryPlant.events.change();
  ids.solarHistoryPlant.value='b';await ids.solarHistoryPlant.events.change();release(response([capture]));await old;
  assert.equal(ids.solarHistoryRows.children.length,0);assert.match(ids.solarHistoryStatus.textContent,/даних немає/);
});
test('denied response clears stale measurements',async()=>{
  const ids=setup(async url=>url==='/dashboard/plants'?response([{id:'a',name:'A'}]):{ok:false});
  await tick();ids.solarHistoryRows.append(new Element());ids.solarHistoryPlant.value='a';ids.solarHistoryDate.value='2026-10-03';
  await ids.solarHistoryPlant.events.change();assert.equal(ids.solarHistoryRows.children.length,0);assert.match(ids.solarHistoryStatus.textContent,/Перевірте доступ/);
});
