const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
class Element {
  constructor(){this.value='';this.children=[];this.events={};}
  add(v){this.children.push(v);}addEventListener(k,v){this.events[k]=v;}
  set innerHTML(v){throw Error('unsafe HTML');}
}
const tick=()=>new Promise(r=>setImmediate(r));
const response=(data,status=200)=>({ok:status===200,status,json:async()=>({data})});
function setup(fetch){const ids=Object.fromEntries(['deyeBindingPlant','deyeBindingStation','verifyDeyeBinding','deyeBindingStatus'].map(k=>[k,new Element()]));
  vm.runInNewContext(fs.readFileSync('web/deye-binding-verification.js','utf8'),{
    document:{querySelector:s=>ids[s.slice(1)]},fetch,JSON,Number,
    Option:class{constructor(label,value){this.textContent=label;this.value=value;}}});return ids;}
async function select(ids){await tick();ids.deyeBindingPlant.value='a';ids.deyeBindingStation.value='7';ids.deyeBindingStation.events.input();}
test('binding is checked only on explicit click with no client credentials',async()=>{
  const calls=[];const ids=setup(async(url,options)=>{calls.push([url,options]);return response(url==='/dashboard/plants'?[{id:'a',name:'<script>plant</script>'}]:{status:'verified',readOnly:true,deviceCount:4});});
  await select(ids);assert.equal(calls.length,1);assert.equal(ids.deyeBindingPlant.children[0].textContent,'<script>plant</script>');
  await ids.verifyDeyeBinding.events.click();assert.deepEqual(JSON.parse(calls[1][1].body),{stationReference:'7',confirmReadOnly:true});
  assert.match(ids.deyeBindingStatus.textContent,/Доступ підтверджено/);
});
test('provider rejection never appears as verified',async()=>{
  const ids=setup(async url=>url==='/dashboard/plants'?response([]):response({},502));
  await select(ids);await ids.verifyDeyeBinding.events.click();assert.match(ids.deyeBindingStatus.textContent,/непідтвердженою/);
});
test('changed plant invalidates late successful verification',async()=>{
  let release;const ids=setup(async url=>url==='/dashboard/plants'?response([]):new Promise(r=>release=r));
  await select(ids);const pending=ids.verifyDeyeBinding.events.click();ids.deyeBindingPlant.value='b';ids.deyeBindingPlant.events.change();
  release(response({status:'verified',readOnly:true,deviceCount:4}));await pending;
  assert.doesNotMatch(ids.deyeBindingStatus.textContent,/Доступ підтверджено/);
});
test('typing station reference while plants load does not discard the plant list',async()=>{
  let release;const ids=setup(()=>new Promise(r=>release=r));
  ids.deyeBindingStation.value='7';ids.deyeBindingStation.events.input();
  release(response([{id:'a',name:'Plant A'}]));await tick();
  assert.equal(ids.deyeBindingPlant.children.length,1);
  assert.equal(ids.deyeBindingStation.value,'7');
  ids.deyeBindingPlant.value='a';ids.deyeBindingPlant.events.change();
  assert.equal(ids.verifyDeyeBinding.disabled,false);
});
