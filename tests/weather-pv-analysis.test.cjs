const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
class Element {
  constructor(){this.children=[];this.events={};this.value='';}
  replaceChildren(...v){this.children=v;}append(...v){this.children.push(...v);}add(v){this.children.push(v);}
  addEventListener(k,v){this.events[k]=v;}
  set innerHTML(v){throw Error('unsafe HTML');}
}
const tick=()=>new Promise(r=>setImmediate(r));
const response=data=>({ok:true,json:async()=>({data})});
const weather=[{captureId:'g',provider:'google_weather',capturedAtUtc:'2026-10-03T06:00:00Z',intervalCount:23},
  {captureId:'s',provider:'solcast',capturedAtUtc:'2026-10-03T06:01:00Z',intervalCount:46}];
function setup(fetch){
  const ids=Object.fromEntries(['Plant','Day','Google','Solcast','Solar','Load','Run','Status','Result'].map(k=>['pvAnalysis'+k,new Element()]));
  vm.runInNewContext(fs.readFileSync('web/weather-pv-analysis.js','utf8'),{
    document:{querySelector:s=>ids[s.slice(1)],createElement:()=>new Element()},fetch,Date,Math,Number,JSON,
    Option:class{constructor(label,value){this.textContent=label;this.value=value;}}});return ids;
}
async function select(ids){await tick();ids.pvAnalysisPlant.value='a';ids.pvAnalysisDay.value='2026-10-03';
  await ids.pvAnalysisLoad.events.click();ids.pvAnalysisGoogle.value='g';ids.pvAnalysisSolcast.value='s';
  ids.pvAnalysisSolar.value='pv';ids.pvAnalysisSolar.events.change();}
test('explicit capture selection posts only the server contract and distinguishes readiness from accuracy',async()=>{
  let payload;const ids=setup(async(url,options)=>{
    if(url==='/dashboard/plants')return response([{id:'a',name:'<script>plant</script>'}]);
    if(url.endsWith('weather-captures'))return response(weather);
    if(url.includes('solar-history'))return response([{captureId:'pv',dayUtc:'2026-10-03',sampleCount:290}]);
    payload=JSON.parse(options.body);return response({pairs:[],excludedCounts:{not_closed:0,actual_missing:19,actual_partial:4}});
  });await select(ids);
  assert.equal(ids.pvAnalysisPlant.children[0].textContent,'<script>plant</script>');
  await ids.pvAnalysisRun.events.click();
  assert.deepEqual(payload,{weatherCaptureIds:['g','s'],solarCaptureId:'pv',forecastOriginUtc:'2026-10-03T06:01:00.000Z'});
  assert.match(ids.pvAnalysisResult.children[0].textContent,/0$/);
  assert.match(ids.pvAnalysisResult.children[4].textContent,/не оцінена/);
});
test('plant change clears selected evidence and suppresses a late analysis response',async()=>{
  let release;const ids=setup(async(url,options)=>{
    if(url==='/dashboard/plants')return response([]);
    if(options.method)return new Promise(r=>release=r);
    return response(url.endsWith('weather-captures')?weather:[{captureId:'pv',dayUtc:'2026-10-03',sampleCount:290}]);
  });await select(ids);const pending=ids.pvAnalysisRun.events.click();
  ids.pvAnalysisPlant.value='';await ids.pvAnalysisPlant.events.change();
  release(response({pairs:[{}],excludedCounts:{not_closed:0,actual_missing:0,actual_partial:0}}));await pending;
  assert.equal(ids.pvAnalysisResult.children.length,0);assert.equal(ids.pvAnalysisRun.disabled,true);
});
