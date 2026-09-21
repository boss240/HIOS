(() => {
  const file=document.querySelector('#manualActualsFile'), button=document.querySelector('#commitManualActuals'), status=document.querySelector('#manualActualsStatus');
  if(!file||!button||!status)return;
  button.addEventListener('click',async()=>{if(!file.files[0]){status.textContent='Оберіть CSV-файл.';return;} status.textContent='Збереження…'; try{const r=await fetch('/dashboard/actuals/manual-import/commit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({csvText:await file.files[0].text(),confirmPersist:true})});if(!r.ok)throw new Error();const d=(await r.json()).data;status.textContent=`Збережено: ${d.inserted}; дублікати: ${d.duplicates}.`;}catch{status.textContent='Не вдалося зберегти файл.';}});
})();
