(() => {
  const list = document.querySelector('#assetList');
  if (!list) return;
  async function loadRows() {
    const response = await fetch('/dashboard/plants');
    if (!response.ok) throw new Error();
    return (await response.json()).data;
  }
  async function addDeleteButtons() {
    let rows;
    try { rows = await loadRows(); } catch { return; }
    const byName = new Map(rows.map(row => [row.name, row]));
    list.querySelectorAll('.asset-item').forEach(card => {
      if (card.querySelector('.delete-asset')) return;
      const name = card.querySelector('strong')?.textContent || '';
      const row = byName.get(name);
      if (!row) return;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'delete-asset'; button.textContent = 'Видалити об’єкт';
      button.addEventListener('click', async () => {
        if (!window.confirm(`Видалити «${row.name}»? Будуть безповоротно видалені дані СЕС, прогнози та інтеграції.`)) return;
        const typed = window.prompt(`Для підтвердження введіть точну назву: ${row.name}`);
        if (typed === null) return;
        if (typed !== row.name) { window.alert('Назва не збігається. Видалення скасовано.'); return; }
        button.disabled = true; button.textContent = 'Видалення…';
        try {
          const response = await fetch(`/dashboard/plants/${encodeURIComponent(row.id)}`, {
            method: 'DELETE', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({confirmationName: typed})
          });
          if (!response.ok) throw new Error();
          card.remove();
        } catch {
          button.disabled = false; button.textContent = 'Видалити об’єкт';
          window.alert('Не вдалося видалити об’єкт. Дані не змінено.');
        }
      });
      card.append(button);
    });
  }
  new MutationObserver(() => { void addDeleteButtons(); }).observe(list, {childList: true});
  void addDeleteButtons();
})();
