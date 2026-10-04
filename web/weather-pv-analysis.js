(() => {
  const get = id => document.querySelector('#' + id);
  const plant=get('pvAnalysisPlant'), day=get('pvAnalysisDay'), google=get('pvAnalysisGoogle'),
    solcast=get('pvAnalysisSolcast'), solar=get('pvAnalysisSolar'), load=get('pvAnalysisLoad'),
    run=get('pvAnalysisRun'), status=get('pvAnalysisStatus'), result=get('pvAnalysisResult');
  if (![plant,day,google,solcast,solar,load,run,status,result].every(Boolean)) return;
  let generation=0, captures=[];
  day.value=new Date(Date.now()-86400000).toISOString().slice(0,10);
  function clear() {generation++;captures=[];result.replaceChildren();run.disabled=true;
    [google,solcast,solar].forEach(s=>s.replaceChildren(new Option('Оберіть запис','')));}
  async function request(url, options={}) {
    const response=await fetch(url,{cache:'no-store',...options});
    if(!response.ok) throw Error('Не вдалося перевірити дані. Перевірте доступ, вибрані записи та дату.');
    return (await response.json()).data;
  }
  function changed() {result.replaceChildren();generation++;
    run.disabled=!(google.value && solcast.value && solar.value);}
  async function loadEvidence() {
    clear();const epoch=generation, id=plant.value;
    if(!id || !/^\d{4}-\d{2}-\d{2}$/.test(day.value)){status.textContent='Оберіть СЕС і дату факту.';return;}
    status.textContent='Читаємо збережені джерела…';
    try {
      const [weather,actual]=await Promise.all([
        request(`/dashboard/plants/${encodeURIComponent(id)}/weather-captures`),
        request(`/dashboard/plants/${encodeURIComponent(id)}/solar-history?start=${day.value}&end=${day.value}`)]);
      if(epoch!==generation)return;
      if(!Array.isArray(weather)||!Array.isArray(actual))throw Error('Некоректна відповідь архіву.');
      captures=weather;
      weather.forEach(c=>{
        const select=c.provider==='google_weather'?google:c.provider==='solcast'?solcast:null;
        if(select)select.add(new Option(`${c.capturedAtUtc} · ${c.intervalCount} інтервалів · ${c.captureId}`,c.captureId));
      });
      actual.forEach(c=>solar.add(new Option(`${c.dayUtc} · ${c.sampleCount} вимірів · ${c.captureId}`,c.captureId)));
      status.textContent='Оберіть знімки Google Weather, Solcast і факту. Час початку прогнозу — пізніше отримання двох знімків. Час випуску провайдером може бути невідомий.';
    } catch(error){if(epoch===generation){clear();status.textContent=error.message;}}
  }
  async function analyze() {
    changed();if(run.disabled)return;
    const epoch=generation,id=plant.value;
    const selected=[google.value,solcast.value].map(value=>captures.find(c=>c.captureId===value));
    if(selected.some(c=>!c))return;
    const times=selected.map(c=>Date.parse(c.capturedAtUtc));
    if(times.some(t=>!Number.isFinite(t))){status.textContent='Час отримання не підтверджено.';return;}
    run.disabled=true;status.textContent='Перевіряємо погодинний збіг…';
    try {
      const data=await request(`/dashboard/plants/${encodeURIComponent(id)}/weather-pv-analysis`,{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
          weatherCaptureIds:selected.map(c=>c.captureId),solarCaptureId:solar.value,
          forecastOriginUtc:new Date(Math.max(...times)).toISOString()})});
      if(epoch!==generation)return;
      const lines=[`Годин для зіставлення: ${data.pairs.length}`,
        `Ще не завершені: ${data.excludedCounts.not_closed}`,
        `Без факту: ${data.excludedCounts.actual_missing}`,
        `Неповний факт: ${data.excludedCounts.actual_partial}`,
        'Точність генерації не оцінена. PV-енергія інвертора і сонячне опромінення мають різні одиниці; це підготовка даних, а не показник точності станції.'];
      lines.forEach(text=>{const p=document.createElement('p');p.textContent=text;result.append(p);});
      status.textContent='Перевірку завершено. Дані не змінено.';
    } catch(error){if(epoch===generation)status.textContent=error.message;}
    finally{if(epoch===generation)run.disabled=false;}
  }
  plant.addEventListener('change',loadEvidence);day.addEventListener('change',loadEvidence);
  load.addEventListener('click',loadEvidence);run.addEventListener('click',analyze);
  [google,solcast,solar].forEach(s=>s.addEventListener('change',changed));clear();
  const epoch=generation;
  request('/dashboard/plants').then(rows=>{if(epoch!==generation)return;
    rows.forEach(p=>plant.add(new Option(p.name,p.id)));status.textContent='Оберіть СЕС і дату факту.';
  }).catch(()=>{status.textContent='Не вдалося прочитати перелік СЕС.';});
})();
