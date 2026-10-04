(() => {
  const plant = document.querySelector('#solarHistoryPlant');
  const day = document.querySelector('#solarHistoryDate');
  const refresh = document.querySelector('#refreshSolarHistory');
  const status = document.querySelector('#solarHistoryStatus');
  const rows = document.querySelector('#solarHistoryRows');
  const exportLink = document.querySelector('#exportSolarHistory');
  if (!plant || !day || !refresh || !status || !rows) return;
  let generation = 0;
  day.value = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
  function element(tag, text) {
    const node = document.createElement(tag); if (text !== undefined) node.textContent = text; return node;
  }
  async function request(url) {
    const response = await fetch(url, {cache:'no-store'});
    if (!response.ok) throw new Error('Не вдалося прочитати архів. Перевірте доступ і дату.');
    const body = await response.json();
    if (!Array.isArray(body.data)) throw new Error('Неочікувана відповідь архіву.');
    return body.data;
  }
  function chart(hours) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 720 190'); svg.setAttribute('width', '100%');
    svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', 'Погодинна розрахована PV-енергія, кВт·год; точні значення в таблиці нижче');
    const peak = Math.max(1, ...hours.map(h => Number.isFinite(h.derivedEnergyKwh) ? h.derivedEnergyKwh : 0));
    hours.forEach((h, index) => {
      if (h.derivedEnergyKwh === null) return;
      const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      const height = 160 * h.derivedEnergyKwh / peak;
      Object.entries({x:index*30+3,y:170-height,width:24,height,fill:h.complete?'#67dbc0':'#ffbd39'}).forEach(([k,v])=>bar.setAttribute(k,String(v)));
      const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.textContent = `${h.hourUtc}: ${h.derivedEnergyKwh.toFixed(3)} кВт·год, покриття ${h.coveredSeconds}/3600 с`;
      bar.append(title); svg.append(bar);
    });
    return svg;
  }
  async function load() {
    const epoch = ++generation; rows.replaceChildren();
    if (exportLink) {exportLink.hidden=true;exportLink.removeAttribute('href');}
    if (!plant.value || !/^\d{4}-\d{2}-\d{2}$/.test(day.value)) {status.textContent='Оберіть СЕС і дату.';return;}
    status.textContent='Читаємо фактичні дані зі сховища…';
    try {
      const captures = await request(`/dashboard/plants/${encodeURIComponent(plant.value)}/solar-history?start=${day.value}&end=${day.value}`);
      if (epoch !== generation) return;
      if (!captures.length) {status.textContent='За цю дату даних немає. Оберіть іншу дату.';return;}
      captures.forEach((capture,index) => {
        if (capture.scope !== 'device_only' || !Array.isArray(capture.hours) || capture.hours.length !== 24) throw new Error('Непідтверджена структура погодинних даних.');
        const card = element('article'); card.className='readiness-item';
        card.append(element('h3',`Інвертор ${index+1} · ${capture.dayUtc} · ${capture.sampleCount} записів`));
        card.append(chart(capture.hours));
        const wrapper=element('div'); wrapper.style.overflowX='auto';
        const table=element('table'); table.style.width='100%';
        const head=element('tr'); ['Година UTC','PV-енергія, кВт·год','Покриття','Статус'].forEach(text=>head.append(element('th',text))); table.append(head);
        capture.hours.forEach(h=>{
          const row=element('tr');
          [h.hourUtc.slice(11,16),h.derivedEnergyKwh===null?'—':h.derivedEnergyKwh.toFixed(3),`${h.coveredSeconds}/3600 с`,h.complete?'Повна година':h.coveredSeconds?'Часткова година':'Немає даних'].forEach(text=>row.append(element('td',text)));
          table.append(row);
        });
        wrapper.append(table);card.append(wrapper);rows.append(card);
      });
      status.textContent=`Архів: ${captures.length} інвертор(и). Часткові години не є повним фактом генерації.`;
      if (exportLink) {
        exportLink.href=`/dashboard/plants/${encodeURIComponent(plant.value)}/solar-history.xlsx?start=${day.value}&end=${day.value}`;
        exportLink.hidden=false;
      }
    } catch (error) {if(epoch===generation){rows.replaceChildren();status.textContent=error.message;}}
  }
  async function init() {
    const epoch=++generation;
    try {
      const plants=await request('/dashboard/plants'); if(epoch!==generation)return;
      plant.replaceChildren(new Option('Оберіть об’єкт',''));
      plants.forEach(p=>plant.add(new Option(p.name,p.id)));
      status.textContent='Оберіть СЕС і дату для перегляду.';
    } catch(error){if(epoch===generation)status.textContent=error.message;}
  }
  plant.addEventListener('change',load); day.addEventListener('change',load);
  refresh.addEventListener('click',()=>plant.value?load():init()); init();
})();
