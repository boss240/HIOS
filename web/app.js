const plants = {
  pohreby: {name:'Погреби', energy:53.1, peak:8.9, factor:1, color:'#f5b942', baseline:[0,0,0,0,0,0,0,.2,1.4,3.9,6.8,8.5,8.9,8.1,6.3,3.7,1.2,.2,0,0,0,0,0,0]},
  borshchiv: {name:'Борщів', energy:47.7, peak:8.7, factor:.9, color:'#9b8cff', baseline:[0,0,0,0,0,0,0,.1,1.1,3.1,6.2,8.2,8.7,7.8,5.7,3.3,1,.1,0,0,0,0,0,0]},
  portfolio: {name:'Портфель', energy:100.8, peak:17.6, factor:1.9, color:'#69d7b7', baseline:[0,0,0,0,0,0,0,.3,2.5,7,13,16.7,17.6,15.9,12,7,2.2,.3,0,0,0,0,0,0]}
};
const catalog = {
  google_weather:{name:'Google Weather', detail:'температура, хмари, вітер', state:'candidate', dot:'#69d7b7'},
  solcast:{name:'Solcast', detail:'GHI · DNI · DHI', state:'live', dot:'#f5b942'},
  open_meteo:{name:'Open-Meteo Ensemble', detail:'ансамблеві сценарії для benchmark', state:'research', dot:'#9b8cff'},
  meteoblue:{name:'meteoblue', detail:'ML multimodel challenger', state:'research', dot:'#5ebce8'},
  meteomatics:{name:'Meteomatics', detail:'висока просторова роздільність', state:'research', dot:'#fa936d'},
  eosda_weather:{name:'EOSDA Weather', detail:'український геопросторовий канал', state:'research', dot:'#6ec2de'},
  local_partner:{name:'Локальний погодний партнер', detail:'контрактний локальний канал', state:'research', dot:'#f5907c'}
};
let state = {plant:'pohreby', hours:24, channels:[]};
const $ = (s) => document.querySelector(s);
function hours(){return Array.from({length:state.hours},(_,i)=>String(i).padStart(2,'0')+':00')}
function pointList(values, left, top, width, height, max){return values.map((v,i)=>`${left+i/(values.length-1)*width},${top+height-(v/max)*height}`).join(' ')}
function renderChart(){
  const data=plants[state.plant]; const values=Array.from({length:state.hours},(_,i)=>data.baseline[i%24]*(i>=24?.82:1));
  const max=Math.max(10,Math.ceil(Math.max(...values)/2)*2); const svg=$('#forecastChart'); const W=1040,H=345,L=48,R=18,T=18,B=38,w=W-L-R,h=H-T-B;
  const grids=Array.from({length:6},(_,i)=>{const y=T+h-(i/5*h);return `<line x1="${L}" y1="${y}" x2="${W-R}" y2="${y}" stroke="#29434b" stroke-width="1"/><text x="0" y="${y+4}" fill="#76918d" font-size="11">${(max*i/5).toFixed(0)}</text>`}).join('');
  const xlabels=hours().map((v,i)=> i%Math.ceil(state.hours/8)===0?`<text x="${L+i/(state.hours-1)*w}" y="${H-10}" fill="#76918d" font-size="11" text-anchor="middle">${v}</text>`:'').join('');
  const line=pointList(values,L,T,w,h,max); const upper=values.map(v=>Math.min(max,v*1.18+.25)); const lower=values.map(v=>Math.max(0,v*.79-.12));
  const lowerPoints=lower.map((v,i)=>`${L+i/(lower.length-1)*w},${T+h-(v/max)*h}`).reverse().join(' '); const area=`${pointList(upper,L,T,w,h,max)} ${lowerPoints}`;
  const bars=values.map((v,i)=>{let x=L+i/(state.hours-1)*w;return `<line class="hit" data-index="${i}" x1="${x}" y1="${T}" x2="${x}" y2="${T+h}" stroke="transparent" stroke-width="${Math.max(12,w/state.hours)}"/>`}).join('');
  svg.innerHTML=`${grids}<polyline points="${area}" fill="#4a9b8a2e" stroke="none"/><polyline points="${line}" fill="none" stroke="${data.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${xlabels}${bars}`;
  svg.querySelectorAll('.hit').forEach(el=>el.addEventListener('mousemove',event=>showTip(event,values[Number(el.dataset.index)],Number(el.dataset.index),data))); svg.addEventListener('mouseleave',()=>$('#tooltip').hidden=true);
  $('#chartTitle').textContent=`${data.name} · прогноз на ${state.hours} годин`; $('#energyValue').innerHTML=`${(data.energy*(state.hours/24)).toFixed(1)} <small>kWh</small>`; $('#peakValue').innerHTML=`${data.peak.toFixed(1)} <small>kW</small>`; $('#providersValue').innerHTML=`${state.channels.filter(c=>catalog[c].state==='live').length} <small>live</small>`;
}
function showTip(event,value,index,data){const tip=$('#tooltip'), wrap=$('#chartWrap').getBoundingClientRect();tip.hidden=false;tip.innerHTML=`<b>${String(index).padStart(2,'0')}:00</b><br>${value.toFixed(1)} kW · ${data.name}`;tip.style.left=`${Math.min(event.clientX-wrap.left+12,wrap.width-135)}px`;tip.style.top=`${Math.max(event.clientY-wrap.top-55,8)}px`;$('#chartCaption').textContent=`${String(index).padStart(2,'0')}:00 — сценарій ${Math.max(0,value*.79-.12).toFixed(1)}–${Math.min(value*1.18+.25,99).toFixed(1)} kW`}
function renderProviders(){const list=$('#providerList');list.innerHTML=state.channels.map(id=>{const p=catalog[id];return `<div class="provider"><i class="dot" style="background:${p.dot}"></i><div><strong>${p.name}</strong><small>${p.detail}</small></div><span class="tag ${p.state==='research'?'research':''}">${p.state==='live'?'live':'research'}</span></div>`}).join('');const available=Object.keys(catalog).filter(id=>!state.channels.includes(id));$('#providerSelect').innerHTML=available.map(id=>`<option value="${id}">${catalog[id].name}</option>`).join('');$('#showProviderForm').hidden=available.length===0;}
function selectPlant(){document.querySelectorAll('.plant').forEach(b=>b.classList.toggle('active',b.dataset.plant===state.plant));renderChart()}
document.querySelectorAll('.plant').forEach(b=>b.addEventListener('click',()=>{state.plant=b.dataset.plant;selectPlant()}));
document.querySelectorAll('.horizon button').forEach(b=>b.addEventListener('click',()=>{state.hours=Number(b.dataset.hours);document.querySelectorAll('.horizon button').forEach(x=>x.classList.toggle('active',x===b));renderChart()}));
$('#showProviderForm').addEventListener('click',()=>{$('#providerForm').hidden=!$('#providerForm').hidden});
$('#providerForm').addEventListener('submit',async e=>{e.preventDefault();const id=$('#providerSelect').value;if(!id)return;try{const response=await fetch('/dashboard/weather-providers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:id,role:$('#roleSelect').value})});if(!response.ok)throw new Error();await loadProviders();$('#providerForm').hidden=true;}catch{$('#providerForm').querySelector('p').textContent='�� ������� �������� �����. �������� ����������.';}});
async function loadProviders(){try{const response=await fetch('/dashboard/weather-providers');if(!response.ok)throw new Error();const rows=(await response.json()).data;rows.forEach(row=>{if(catalog[row.id])catalog[row.id].state=row.status==='configured'?'live':row.role;});state.channels=rows.map(row=>row.id);renderProviders();renderChart();}catch{renderProviders();renderChart();}}
$('#themeToggle').addEventListener('click',()=>document.body.classList.toggle('bright'));
loadProviders();

const assetForm = $('#assetForm');
const assetList = $('#assetList');
function displayAssets(items){
  assetList.innerHTML = items.length ? items.map(item => `<article class="asset-item"><strong>${escapeHtml(item.name)}</strong><span>${item.capacityKw == null ? 'Потужність уточнюється' : item.capacityKw + ' кВт DC'}</span></article>`).join('') : '<p class="empty-state">Поки що немає доданих об’єктів.</p>';
}
function escapeHtml(value){return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));}
async function loadAssets(){
  try { const response = await fetch('/dashboard/plants'); if (!response.ok) throw new Error(); displayAssets((await response.json()).data); }
  catch { assetList.innerHTML = '<p class="empty-state">Реєстр стане доступним після підключення сховища даних.</p>'; }
}
function optionalNumber(form, field){const value=new FormData(form).get(field);return value === '' ? undefined : Number(value)}
$('#showAssetForm').addEventListener('click',()=>{assetForm.hidden=!assetForm.hidden; if(!assetForm.hidden) assetForm.querySelector('[name=name]').focus();});
assetForm.addEventListener('submit', async event => {
  event.preventDefault(); const status=$('#assetFormStatus'); status.textContent='Збереження…';
  const form=new FormData(assetForm); const payload={name:form.get('name'), timezone:'Europe/Kyiv'};
  ['capacityKw','latitude','longitude','capacityAcKw','tiltDeg','azimuthDeg'].forEach(key=>{const value=optionalNumber(assetForm,key);if(value!==undefined)payload[key]=value});
  ['meterBoundary','operatorNotes'].forEach(key=>{const value=String(form.get(key)||'').trim();if(value)payload[key]=value});
  try { const response=await fetch('/dashboard/plants',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); if(!response.ok) throw new Error(); assetForm.reset();assetForm.hidden=true;status.textContent='Об’єкт створено.';await loadAssets(); }
  catch { status.textContent='Не вдалося зберегти. Перевірте підключення та значення.'; }
});
loadAssets();

function renderAssetCards(items){
  assetList.innerHTML=items.length?items.map(item=>`<article class="asset-item"><strong>${escapeHtml(item.name)}</strong><span>${item.capacityKw==null?'Потужність уточнюється':item.capacityKw+' кВт DC'}</span><button class="connect-cloud" data-plant-id="${escapeHtml(item.id)}">Підключити хмару інвертора</button></article>`).join(''):'<p class="empty-state">Поки що немає доданих об’єктів.</p>';
  document.querySelectorAll('.connect-cloud').forEach(button=>button.addEventListener('click',()=>{ $('#cloudPlantId').value=button.dataset.plantId; $('#cloudForm').hidden=false; $('#cloudProvider').focus(); }));
}
const originalDisplayAssets=displayAssets;
displayAssets=renderAssetCards;
$('#cloudForm').addEventListener('submit',async event=>{event.preventDefault();const status=$('#cloudFormStatus');status.textContent='Створення запиту…';try{const id=$('#cloudPlantId').value;const response=await fetch(`/dashboard/plants/${encodeURIComponent(id)}/cloud-requests`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:$('#cloudProvider').value})});if(!response.ok)throw new Error();status.textContent='Запит створено. Система очікує захищеного підтвердження доступу.';}catch{status.textContent='Не вдалося створити запит.';}});
