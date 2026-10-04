(() => {
  const select = document.querySelector('#weatherCapturePlant');
  const refresh = document.querySelector('#refreshWeatherCaptures');
  const status = document.querySelector('#weatherCaptureStatus');
  const container = document.querySelector('#weatherCaptureRows');
  if (!select || !refresh || !status || !container) return;
  let generation = 0;
  let collecting = false;
  const captureButtons = [
    [document.querySelector('#captureGoogleWeather'), 'google_weather'],
    [document.querySelector('#captureSolcastWeather'), 'solcast'],
  ];
  function updateButtons() {
    captureButtons.forEach(([button]) => { if (button) button.disabled = collecting || !select.value; });
  }
  const failureMessages = {
    WEATHER_PROVIDER_PLAN_LIMIT: 'Провайдер обмежив доступ за тарифним планом або лімітом. Перевірте план у його кабінеті.',
    WEATHER_PROVIDER_AUTHENTICATION_FAILED: 'Провайдер не прийняв серверний ключ. Потрібна перевірка налаштувань доступу.',
    WEATHER_PROVIDER_ACCESS_DENIED: 'Поточний ключ не має доступу до цього погодного продукту.',
    WEATHER_PROVIDER_RATE_LIMIT: 'Провайдер тимчасово обмежив частоту запитів. Новий прогноз не збережено.',
    WEATHER_KEY_NOT_CONFIGURED: 'Серверний ключ цього провайдера ще не налаштований.',
  };
  async function collect(provider) {
    if (collecting || !select.value) return;
    const id = select.value, epoch = ++generation;
    collecting = true; updateButtons();
    status.textContent = 'Отримуємо новий прогноз…';
    try {
      const response = await fetch(`/dashboard/plants/${encodeURIComponent(id)}/weather-captures`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({provider, confirm: 'CAPTURE_FORECAST'}),
      });
      const body = await response.json();
      if (epoch !== generation) return;
      if (!response.ok) {
        status.textContent = response.status === 401 ? 'Увійдіть, щоб отримати прогноз.' :
          response.status === 403 ? 'Немає доступу до обраної СЕС.' :
          failureMessages[body.error?.code] || 'Новий прогноз не збережено. Перевірте доступ до провайдера.';
        return;
      }
      if (!body.data?.captureId || body.data.provider !== provider) throw new Error('invalid capture');
      await loadCaptures();
    } catch (_) {
      if (epoch === generation) status.textContent = 'Не вдалося підтвердити результат запиту. Оновіть архів перед повторним отриманням.';
    } finally { collecting = false; updateButtons(); }
  }
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
    updateButtons();
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
  captureButtons.forEach(([button, provider]) => { if (button) button.addEventListener('click', () => collect(provider)); });
  refresh.addEventListener('click', () => select.value ? loadCaptures() : loadPlants());
  loadPlants();
})();
