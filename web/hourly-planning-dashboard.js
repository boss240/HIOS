(() => {
  const $ = (selector) => document.querySelector(selector);
  const plant = $('#planPlant'), run = $('#planRun'), consumption = $('#planConsumption');
  const price = $('#planRdnPrice'), scenario = $('#planRdnScenario'), scenarioName = $('#planScenarioName');
  const status = $('#planStatus'), table = $('#planTable'), summary = $('#planSummary');
  const exportButton = $('#exportHourlyPlan'), saveScenarioButton = $('#saveRdnScenario');
  let lastPayload = null, lastRows = [];

  const values = (textarea, label) => {
    const raw = textarea.value.trim();
    if (!raw) return null;
    const result = raw.split(/\r?\n/).map((line) => Number(line.trim()));
    if (result.some((value) => !Number.isFinite(value) || value < 0)) throw new Error(`${label}: введіть невід'ємні числа, по одному на рядок.`);
    return result;
  };
  const request = async (url, options = {}) => {
    const response = await fetch(url, {credentials: 'same-origin', ...options});
    if (!response.ok) throw new Error(response.status === 401 ? 'Потрібен вхід до HIOS Forecast.' : 'Запит не виконано. Перевірте вибрані дані.');
    return response;
  };
  const setStatus = (message) => { status.textContent = message; };
  const payload = () => {
    const data = {consumptionKwh: values(consumption, 'Споживання')};
    if (scenario.value) data.rdnScenarioId = scenario.value; else data.rdnPriceUahPerKwh = values(price, 'Ціна РДН');
    return data;
  };
  const refreshScenarios = async (selected = '') => {
    const data = await (await request('/dashboard/rdn-scenarios')).json();
    scenario.innerHTML = '<option value="">Ввести вручну</option>';
    data.data.forEach((item) => { const option = document.createElement('option'); option.value = item.id; option.textContent = `${item.name} · ${item.pointCount} інтервалів`; scenario.append(option); });
    scenario.value = selected;
  };
  const refreshRuns = async () => {
    run.innerHTML = '<option value="">Завантаження прогнозів…</option>'; run.disabled = true; exportButton.disabled = true;
    if (!plant.value) { run.innerHTML = '<option value="">Спочатку оберіть СЕС</option>'; return; }
    try {
      const data = await (await request(`/dashboard/plants/${encodeURIComponent(plant.value)}/forecast-runs`)).json();
      run.innerHTML = '<option value="">Оберіть forecast run</option>';
      data.data.forEach((item) => { const option = document.createElement('option'); option.value = item.id; option.textContent = `${new Date(item.forecastOriginUtc).toLocaleString('uk-UA')} · ${item.pointCount} год. · ${item.status}`; run.append(option); });
      run.disabled = false;
      if (!data.data.length) setStatus('Для цієї СЕС ще немає зафіксованого прогнозу для планування.');
    } catch (error) { setStatus(error.message); run.innerHTML = '<option value="">Прогнози недоступні</option>'; }
  };
  const render = (rows) => {
    lastRows = rows;
    const totals = rows.reduce((result, item) => ({generation: result.generation + item.predictedGenerationKwh, consumption: result.consumption + (item.consumptionKwh || 0), importCost: result.importCost + (item.estimatedImportCostUah || 0), exportValue: result.exportValue + (item.estimatedExportValueUah || 0)}), {generation: 0, consumption: 0, importCost: 0, exportValue: 0});
    summary.hidden = false; summary.textContent = `Генерація ${totals.generation.toFixed(1)} кВт·год · Споживання ${totals.consumption.toFixed(1)} кВт·год · Оцінка імпорту ${totals.importCost.toFixed(2)} грн · Надлишок ${totals.exportValue.toFixed(2)} грн`;
    const body = table.querySelector('tbody'); body.replaceChildren();
    rows.forEach((item) => { const row = document.createElement('tr'); [new Date(item.intervalStartUtc).toLocaleString('uk-UA', {hour:'2-digit', minute:'2-digit', timeZone:'UTC'}), item.predictedGenerationKwh, item.consumptionKwh, item.netGridKwh, item.rdnPriceUahPerKwh, item.estimatedImportCostUah].forEach((value) => { const cell = document.createElement('td'); cell.textContent = value == null ? '—' : Number.isFinite(value) ? value.toFixed(2) : value; row.append(cell); }); body.append(row); });
    table.hidden = false;
  };
  const build = async () => {
    if (!run.value) throw new Error('Оберіть forecast run.');
    const data = payload(); setStatus('Розрахунок…');
    const response = await request(`/dashboard/forecast-runs/${encodeURIComponent(run.value)}/hourly-plan`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    lastPayload = data; render((await response.json()).data); exportButton.disabled = false; saveScenarioButton.disabled = Boolean(scenario.value); setStatus('План готовий.');
  };
  plant.addEventListener('change', refreshRuns);
  scenario.addEventListener('change', () => { price.disabled = Boolean(scenario.value); if (scenario.value) price.value = ''; saveScenarioButton.disabled = Boolean(scenario.value) || !lastRows.length; });
  $('#buildHourlyPlan').addEventListener('click', () => build().catch((error) => setStatus(error.message)));
  saveScenarioButton.addEventListener('click', async () => {
    try {
      if (!scenarioName.value.trim()) throw new Error('Вкажіть назву сценарію РДН.');
      const manualPrices = values(price, 'Ціна РДН');
      if (!manualPrices || !lastRows.length || manualPrices.length !== lastRows.length) throw new Error('Спершу розрахуйте план з повним ручним рядом цін.');
      setStatus('Зберігаємо сценарій…');
      const response = await request('/dashboard/rdn-scenarios', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name: scenarioName.value.trim(), sourceReference:'operator-entered RDN scenario', points:lastRows.map((item, index) => ({intervalStartUtc:item.intervalStartUtc, priceUahPerKwh:manualPrices[index]}))})});
      const created = await response.json(); await refreshScenarios(created.data.id); scenarioName.value = ''; price.disabled = true; saveScenarioButton.disabled = true; setStatus('Сценарій РДН збережено.');
    } catch (error) { setStatus(error.message); }
  });
  exportButton.addEventListener('click', async () => { try { const data = {...(lastPayload || payload()), format:'xlsx'}; setStatus('Готуємо Excel…'); const response = await request(`/dashboard/forecast-runs/${encodeURIComponent(run.value)}/hourly-plan/export`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}); const blob = await response.blob(), link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'hios-hourly-plan.xlsx'; link.click(); URL.revokeObjectURL(link.href); setStatus('Excel завантажено.'); } catch (error) { setStatus(error.message); } });
  request('/dashboard/plants').then((response) => response.json()).then(({data}) => { data.forEach((item) => { const option = document.createElement('option'); option.value = item.id; option.textContent = item.name; plant.append(option); }); return refreshScenarios(); }).catch((error) => setStatus(error.message));
})();
