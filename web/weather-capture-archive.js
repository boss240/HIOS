(() => {
  const select = document.querySelector('#weatherCapturePlant');
  const refresh = document.querySelector('#refreshWeatherCaptures');
  const status = document.querySelector('#weatherCaptureStatus');
  const container = document.querySelector('#weatherCaptureRows');
  if (!select || !refresh || !status || !container) return;
  let generation = 0;
  const names = {google_weather: 'Google Weather', solcast: 'Solcast', open_meteo: 'Open-Meteo'};
  async function request(path) {
    const response = await fetch(path, {cache: 'no-store'});
    if (!response.ok) throw new Error('Не вдалося прочитати архів. Перевірте доступ і повторіть оновлення.');
    const body = await response.json();
    if (!Array.isArray(body.data)) throw new Error('Архів повернув неочікувану відповідь.');
    return body.data;
  }
  const formatDate = value => {
    const date = new Date(value);
    return Number.isFinite(date.getTime()) ? date.toLocaleString('uk-UA', {timeZone: 'Europe/Kyiv'}) + ' (Київ)' : 'Час не підтверджено';
  };
  async function loadCaptures() {
    const epoch = ++generation, id = select.value;
    container.replaceChildren();
    if (!id) { status.textContent = 'Оберіть СЕС, щоб переглянути її архів.'; return; }
    status.textContent = 'Читаємо збережені прогнози…';
    try {
      const rows = await request(`/dashboard/plants/${encodeURIComponent(id)}/weather-captures`);
      if (epoch !== generation) return;
      if (!rows.length) { status.textContent = 'Для цього об’єкта прогнозів у сховищі ще немає.'; return; }
      const latest = new Map();
      rows.forEach(row => { if (!latest.has(row.provider)) latest.set(row.provider, row); });
      latest.forEach(row => {
        const card = document.createElement('article'); card.className = 'readiness-item';
        const heading = document.createElement('strong'); heading.textContent = names[row.provider] || 'Інше джерело';
        const received = document.createElement('p'); received.textContent = 'Останнє отримання: ' + formatDate(row.capturedAtUtc);
        const count = document.createElement('p'); count.textContent = 'Інтервалів: ' + row.intervalCount;
        const issued = document.createElement('p'); issued.textContent = row.providerIssuedAtUtc ? 'Випуск провайдера: ' + formatDate(row.providerIssuedAtUtc) : 'Час випуску провайдером не підтверджено.';
        card.append(heading, received, count, issued); container.append(card);
      });
      status.textContent = `Показано останні дані ${latest.size} джерел; переглянуто ${rows.length} знімків (до 100 останніх). Час отримання не є часом випуску провайдера.`;
    } catch (error) { if (epoch === generation) status.textContent = error.message; }
  }
  async function loadPlants() {
    const epoch = ++generation;
    select.disabled = true; refresh.disabled = true; container.replaceChildren();
    status.textContent = 'Читаємо перелік СЕС…';
    try {
      const plants = await request('/dashboard/plants');
      if (epoch !== generation) return;
      select.replaceChildren(new Option('Оберіть об’єкт', ''));
      plants.forEach(plant => select.add(new Option(plant.name, plant.id)));
      status.textContent = plants.length ? 'Оберіть СЕС, щоб переглянути її архів.' : 'Додайте першу СЕС.';
    } catch (error) { if (epoch === generation) status.textContent = error.message; }
    finally { select.disabled = false; refresh.disabled = false; }
  }
  select.addEventListener('change', loadCaptures);
  refresh.addEventListener('click', () => select.value ? loadCaptures() : loadPlants());
  loadPlants();
})();
