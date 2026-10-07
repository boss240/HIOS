const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../web/weather-capture-archive.js'), 'utf8');
class Element {
  constructor() { this.children = []; this.events = {}; this.value = ''; this.textContent = ''; }
  replaceChildren(...items) { this.children = items; }
  append(...items) { this.children.push(...items); }
  add(item) { this.children.push(item); }
  addEventListener(name, handler) { this.events[name] = handler; }
  set innerHTML(value) { throw new Error('Unsafe HTML rendering'); }
}
const tick = () => new Promise(resolve => setImmediate(resolve));
function setup(fetch) {
  const ids = Object.fromEntries(['weatherCapturePlant','refreshWeatherCaptures','weatherCaptureStatus','weatherCaptureRows','captureGoogleWeather','captureSolcastWeather'].map(id=>[id,new Element()]));
  vm.runInNewContext(source, {document:{querySelector:s=>ids[s.slice(1)],createElement:()=>new Element()},fetch,
    Option:class {constructor(label,value){this.textContent=label;this.value=value;}},Map,Date,Number});
  return ids;
}
function response(data) { return {ok:true,json:async()=>({data})}; }
const capture = {provider:'google_weather',capturedAtUtc:'2026-10-04T10:00:00Z',providerIssuedAtUtc:null,intervalCount:23};

test('explicit capture persists selected source and refreshes the selected plant archive', async()=>{
  const calls=[];
  const ids=setup(async(url,options)=>{
    calls.push([url,options]);
    if(options.method==='POST')return {ok:true,json:async()=>({data:{captureId:'saved',provider:'google_weather'}})};
    return response(url==='/dashboard/plants'?[{id:'owned',name:'Plant'}]:[capture]);
  });
  await tick();ids.weatherCapturePlant.value='owned';await ids.weatherCapturePlant.events.change();
  await ids.captureGoogleWeather.events.click();
  const posts=calls.filter(([,options])=>options.method==='POST');
  assert.equal(posts.length,1);
  assert.equal(posts[0][0],'/dashboard/plants/owned/weather-captures');
  assert.deepEqual(JSON.parse(posts[0][1].body),{provider:'google_weather',confirm:'CAPTURE_FORECAST'});
  assert.equal(ids.weatherCaptureRows.children.length,1);
});

test('plan rejection keeps archive and does not display provider body', async()=>{
  const ids=setup(async(url,options)=>options.method==='POST'?{ok:false,status:502,json:async()=>({error:{code:'WEATHER_PROVIDER_PLAN_LIMIT'},message:'private-key'})}:response(url==='/dashboard/plants'?[{id:'owned',name:'Plant'}]:[capture]));
  await tick();ids.weatherCapturePlant.value='owned';await ids.weatherCapturePlant.events.change();
  await ids.captureSolcastWeather.events.click();
  assert.match(ids.weatherCaptureStatus.textContent,/тарифним планом/);
  assert.ok(!ids.weatherCaptureStatus.textContent.includes('private-key'));
  assert.equal(ids.weatherCaptureRows.children.length,1);
});

test('pending capture cannot be duplicated or overwrite another plant status', async()=>{
  let release, posts=0;
  const ids=setup(async(url,options)=>{
    if(options.method==='POST'){posts++;return new Promise(resolve=>{release=resolve;});}
    return response(url==='/dashboard/plants'?[{id:'a',name:'A'},{id:'b',name:'B'}]:[]);
  });
  await tick();ids.weatherCapturePlant.value='a';await ids.weatherCapturePlant.events.change();
  const pending=ids.captureSolcastWeather.events.click();
  await ids.captureSolcastWeather.events.click();
  ids.weatherCapturePlant.value='b';await ids.weatherCapturePlant.events.change();
  release({ok:false,status:502,json:async()=>({error:{code:'WEATHER_PROVIDER_PLAN_LIMIT'}})});await pending;
  assert.equal(posts,1);
  assert.equal(ids.weatherCaptureStatus.textContent,'Для цього об’єкта прогнозів у сховищі ще немає.');
});
test('archive is read-only and does not treat receipt as provider issue time', async()=>{
  const calls=[];
  const ids=setup(async(url,options)=>{calls.push([url,options]);return response(url==='/dashboard/plants'?[{id:'owned',name:'<img onerror=evil>'}]:[capture]);});
  await tick();
  assert.equal(ids.weatherCapturePlant.children[1].textContent,'<img onerror=evil>');
  ids.weatherCapturePlant.value='owned'; await ids.weatherCapturePlant.events.change();
  assert.equal(ids.weatherCaptureRows.children.length,1);
  assert.equal(ids.weatherCaptureRows.children[0].children[3].textContent,'Час випуску провайдером не підтверджено.');
  assert.equal(calls.length,2);
  assert.ok(calls.every(([,options])=>!options.method && options.cache==='no-store'));
});
test('late response for previous plant cannot replace selected plant archive', async()=>{
  let release;
  const ids=setup(async url=>url==='/dashboard/plants'?response([{id:'a',name:'A'},{id:'b',name:'B'}]):url.includes('/a/')?new Promise(resolve=>{release=resolve;}):response([]));
  await tick();ids.weatherCapturePlant.value='a';const previous=ids.weatherCapturePlant.events.change();
  ids.weatherCapturePlant.value='b';await ids.weatherCapturePlant.events.change();
  release(response([capture]));await previous;
  assert.equal(ids.weatherCaptureRows.children.length,0);
  assert.equal(ids.weatherCaptureStatus.textContent,'Для цього об’єкта прогнозів у сховищі ще немає.');
});
test('unauthorized response shows error without stale archive', async()=>{
  const ids=setup(async url=>url==='/dashboard/plants'?response([{id:'a',name:'A'}]):{ok:false});
  await tick();ids.weatherCaptureRows.append(new Element());
  ids.weatherCapturePlant.value='a';await ids.weatherCapturePlant.events.change();
  assert.equal(ids.weatherCaptureRows.children.length,0);
  assert.match(ids.weatherCaptureStatus.textContent,/Перевірте доступ/);
});

