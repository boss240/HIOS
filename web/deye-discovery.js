(() => {
  const button = document.querySelector('#discoverDeyeStations');
  const choices = document.querySelector('#deyeStationChoices');
  const input = document.querySelector('#quickExternalId');
  const audit = document.querySelector('#deyeTelemetryAudit');
  const auditStation = document.querySelector('#deyeAuditStation');
  const auditDate = document.querySelector('#deyeAuditDate');
  const auditButton = document.querySelector('#auditDeyeTelemetry');
  const auditStatus = document.querySelector('#deyeAuditStatus');
  if (!button || !choices || !input || !audit || !auditStation || !auditDate || !auditButton || !auditStatus) return;
  let selectedStation = null;
  const yesterday = new Date();
  yesterday.setUTCDate(yesterday.getUTCDate() - 1);
  auditDate.max = yesterday.toISOString().slice(0, 10);
  auditDate.value = auditDate.max;

  async function messageFrom(response, fallback) {
    try {
      const body = await response.json();
      return body?.error?.message || body?.detail || fallback;
    } catch {
      return fallback;
    }
  }

  button.addEventListener('click', async () => {
    button.disabled = true;
    choices.textContent = 'Перевіряємо read-only доступ до Deye…';
    audit.hidden = true;
    selectedStation = null;
    try {
      const response = await fetch('/dashboard/deye/stations/discover', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({confirmReadOnly: true})
      });
      if (!response.ok) throw new Error(await messageFrom(response, 'Deye Cloud не повернув список СЕС.'));
      const rows = (await response.json()).data;
      if (!rows.length) { choices.textContent = 'Доступних СЕС не знайдено.'; return; }
      choices.replaceChildren(...rows.map(row => {
        const option = document.createElement('button');
        option.type = 'button'; option.className = 'text-button';
        option.textContent = `${row.name} · ID ${row.id}`;
        option.addEventListener('click', () => {
          selectedStation = row;
          input.value = row.id;
          input.focus();
          auditStation.textContent = `Обрано: ${row.name}. Native ID: ${row.id}.`;
          auditStatus.textContent = 'Перевірка не створює фактичних даних і не надсилає команд інвертору.';
          audit.hidden = false;
        });
        return option;
      }));
    } catch (error) { choices.textContent = error.message || 'Список недоступний: перевірте серверне read-only підключення Deye.'; }
    finally { button.disabled = false; }
  });

  auditButton.addEventListener('click', async () => {
    if (!selectedStation || !auditDate.value) return;
    auditButton.disabled = true;
    auditStatus.textContent = 'Перевіряємо лише історичну якість даних…';
    try {
      const response = await fetch(`/dashboard/deye/stations/${encodeURIComponent(selectedStation.id)}/telemetry-audit`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({confirmReadOnly: true, dateUtc: auditDate.value})
      });
      if (!response.ok) throw new Error(await messageFrom(response, 'Deye Cloud не повернув історичні дані.'));
      const data = (await response.json()).data;
      const cadence = data.cadence_seconds?.length ? `${data.cadence_seconds.join(', ')} с` : 'не визначено';
      const flags = data.flags?.length ? ` Попередження: ${data.flags.join(', ')}.` : ' Без попереджень форми даних.';
      auditStatus.textContent = `Рядків: ${data.sample_count}; часових міток: ${data.valid_timestamp_count}; інтервал: ${cadence}.${flags}`;
    } catch (error) { auditStatus.textContent = error.message || 'Перевірка історичних даних недоступна.'; }
    finally { auditButton.disabled = false; }
  });
})();
