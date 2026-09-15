(() => {
  const button = document.querySelector('#discoverDeyeStations');
  const choices = document.querySelector('#deyeStationChoices');
  const input = document.querySelector('#quickExternalId');
  if (!button || !choices || !input) return;
  button.addEventListener('click', async () => {
    button.disabled = true;
    choices.textContent = 'Перевіряємо read-only доступ до Deye…';
    try {
      const response = await fetch('/dashboard/deye/stations/discover', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({confirmReadOnly: true})
      });
      if (!response.ok) throw new Error();
      const rows = (await response.json()).data;
      if (!rows.length) { choices.textContent = 'Доступних СЕС не знайдено.'; return; }
      choices.replaceChildren(...rows.map(row => {
        const option = document.createElement('button');
        option.type = 'button'; option.className = 'text-button';
        option.textContent = `${row.name} · ID ${row.id}`;
        option.addEventListener('click', () => { input.value = row.id; input.focus(); choices.textContent = 'ID вибрано. Натисніть «Додати СЕС».'; });
        return option;
      }));
    } catch { choices.textContent = 'Список недоступний: перевірте серверне read-only підключення Deye.'; }
    finally { button.disabled = false; }
  });
})();
