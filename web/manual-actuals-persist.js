(() => {
  const file = document.querySelector('#manualActualsFile');
  const preview = document.querySelector('#previewManualActuals');
  const commit = document.querySelector('#commitManualActuals');
  const status = document.querySelector('#manualActualsStatus');
  if (!file || !preview || !commit || !status) return;

  async function requestPayload() {
    const selected = file.files[0];
    if (!selected) throw new Error('missing-file');
    if (!/\.xlsx$/i.test(selected.name)) return { csvText: await selected.text() };
    const bytes = new Uint8Array(await selected.arrayBuffer());
    let text = '';
    for (let index = 0; index < bytes.length; index += 0x8000) {
      text += String.fromCharCode(...bytes.subarray(index, index + 0x8000));
    }
    return { xlsxBase64: btoa(text) };
  }

  async function verify(event) {
    event.stopImmediatePropagation();
    if (!file.files[0]) { status.textContent = '\u041e\u0431\u0435\u0440\u0456\u0442\u044c CSV \u0430\u0431\u043e XLSX-\u0444\u0430\u0439\u043b.'; return; }
    status.textContent = '\u041f\u0435\u0440\u0435\u0432\u0456\u0440\u043a\u0430\u2026';
    try {
      const response = await fetch('/dashboard/actuals/manual-import/file-preview', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(await requestPayload())
      });
      if (!response.ok) throw new Error('invalid-file');
      const data = (await response.json()).data;
      status.textContent = `\u041f\u0435\u0440\u0435\u0432\u0456\u0440\u0435\u043d\u043e \u0440\u044f\u0434\u043a\u0456\u0432: ${data.rows}. \u041f\u043e\u0433\u0440\u0435\u0431\u0438: ${data.byPilot['deye-pilot-pohreby']}; \u0411\u043e\u0440\u0449\u0456\u0432: ${data.byPilot['deye-pilot-borshchiv']}. \u0414\u0430\u043d\u0456 \u0449\u0435 \u043d\u0435 \u0437\u0431\u0435\u0440\u0435\u0436\u0435\u043d\u043e.`;
    } catch { status.textContent = '\u0424\u0430\u0439\u043b \u043d\u0435 \u0432\u0456\u0434\u043f\u043e\u0432\u0456\u0434\u0430\u0454 \u0448\u0430\u0431\u043b\u043e\u043d\u0443 \u0430\u0431\u043e \u043c\u0456\u0441\u0442\u0438\u0442\u044c \u043d\u0435\u043a\u043e\u0440\u0435\u043a\u0442\u043d\u0456 \u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f.'; }
  }

  preview.addEventListener('click', verify, true);
  commit.addEventListener('click', async () => {
    if (!file.files[0]) { status.textContent = '\u041e\u0431\u0435\u0440\u0456\u0442\u044c CSV \u0430\u0431\u043e XLSX-\u0444\u0430\u0439\u043b.'; return; }
    status.textContent = '\u0417\u0431\u0435\u0440\u0435\u0436\u0435\u043d\u043d\u044f\u2026';
    try {
      const payload = await requestPayload();
      payload.confirmPersist = true;
      const response = await fetch('/dashboard/actuals/manual-import/file-commit', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error('save-failed');
      const data = (await response.json()).data;
      status.textContent = `\u0417\u0431\u0435\u0440\u0435\u0436\u0435\u043d\u043e: ${data.inserted}; \u0434\u0443\u0431\u043b\u0456\u043a\u0430\u0442\u0438: ${data.duplicates}.`;
    } catch { status.textContent = '\u041d\u0435 \u0432\u0434\u0430\u043b\u043e\u0441\u044f \u0437\u0431\u0435\u0440\u0435\u0433\u0442\u0438 \u0444\u0430\u0439\u043b.'; }
  });
})();
