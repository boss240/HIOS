(() => {
  const select = document.querySelector('#passportPlant');
  const form = document.querySelector('#passportForm');
  const status = document.querySelector('#passportStatus');
  if (!select || !form) return;
  const fields = [...form.querySelectorAll('[name]')];
  let baseline = {}, loadedId = '', generation = 0;
  async function request(path, options) {
    const response = await fetch(path, options);
    if (!response.ok) throw new Error('Не вдалося виконати запит. Перевірте доступ і введені дані.');
    return response.json();
  }
  async function refresh() {
    generation++; loadedId = ''; form.hidden = true; select.disabled = true;
    try {
      const {data} = await request('/dashboard/plants');
      select.replaceChildren(new Option('Оберіть об’єкт', ''));
      data.forEach(plant => select.add(new Option(plant.name, plant.id)));
      status.textContent = '';
    } catch (error) { status.textContent = error.message; }
    finally { select.disabled = false; }
  }
  select.addEventListener('change', async () => {
    const epoch = ++generation, id = select.value;
    loadedId = ''; form.hidden = true;
    if (!id) return;
    status.textContent = 'Завантаження паспорта…';
    try {
      const {data} = await request(`/dashboard/plants/${encodeURIComponent(id)}/profile`);
      if (epoch !== generation) return;
      baseline = {};
      fields.forEach(field => { field.value = data[field.name] ?? ''; baseline[field.name] = field.value; });
      loadedId = id; form.hidden = false; status.textContent = '';
    } catch (error) { if (epoch === generation) status.textContent = error.message; }
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!loadedId || loadedId !== select.value) return;
    const changes = {};
    fields.forEach(field => {
      if (field.value !== baseline[field.name]) changes[field.name] = field.value === '' ? null :
        field.type === 'number' ? Number(field.value) : field.value.trim();
    });
    if (!Object.keys(changes).length) { status.textContent = 'Змін немає.'; return; }
    const button = form.querySelector('button');
    button.disabled = true; select.disabled = true;
    try {
      await request(`/dashboard/plants/${encodeURIComponent(loadedId)}/profile`, {
        method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(changes),
      });
      fields.forEach(field => { baseline[field.name] = field.value; });
      status.textContent = 'Паспорт збережено.';
    } catch (error) { status.textContent = error.message; }
    finally { button.disabled = false; select.disabled = false; }
  });
  document.querySelector('#refreshPassportPlants').addEventListener('click', refresh);
  refresh();
})();
