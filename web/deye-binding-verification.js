(() => {
  const plant=document.querySelector('#deyeBindingPlant'), station=document.querySelector('#deyeBindingStation'),
    run=document.querySelector('#verifyDeyeBinding'), status=document.querySelector('#deyeBindingStatus');
  if(!plant||!station||!run||!status)return;
  let generation=0;
  function clear(){generation++;status.textContent='Оберіть СЕС і введіть її ID або посилання Deye Cloud.';
    run.disabled=!(plant.value&&station.value.trim());}
  plant.addEventListener('change',clear);station.addEventListener('input',clear);run.disabled=true;
  run.addEventListener('click',async()=>{
    if(!plant.value||!station.value.trim())return;
    const epoch=++generation,id=plant.value,reference=station.value.trim();
    run.disabled=true;status.textContent='Перевіряємо доступ до станції та її інверторів…';
    try{
      const response=await fetch(`/dashboard/plants/${encodeURIComponent(id)}/deye-binding/verify`,{
        method:'POST',cache:'no-store',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({stationReference:reference,confirmReadOnly:true})});
      if(epoch!==generation)return;
      if(!response.ok){
        status.textContent=response.status===502?'Deye не підтвердив доступ. Прив’язка залишається непідтвердженою.':
          response.status===403?'Доступ до СЕС або станції не підтверджено.':
          response.status===401?'Потрібен вхід у дашборд.':'Перевірте ID станції та серверне налаштування Deye.';
        return;
      }
      const body=await response.json();if(epoch!==generation)return;
      if(body.data?.status!=='verified'||body.data?.readOnly!==true||!Number.isInteger(body.data?.deviceCount))
        throw Error('invalid evidence');
      status.textContent=`Доступ підтверджено. Інверторів: ${body.data.deviceCount}. Керування обладнанням не виконується. Збір історії налаштовується окремо.`;
    }catch(error){if(epoch===generation)status.textContent='Перевірку не завершено. Результат підключення не підтверджено.';}
    finally{if(epoch===generation)run.disabled=false;}
  });
  const initial=generation;
  fetch('/dashboard/plants',{cache:'no-store'}).then(async response=>{
    if(!response.ok)throw Error('access');const body=await response.json();
    if(initial!==generation)return;
    if(!Array.isArray(body.data))throw Error('invalid plants');
    body.data.forEach(p=>plant.add(new Option(p.name,p.id)));
    clear();
  }).catch(()=>{if(initial===generation)status.textContent='Не вдалося прочитати перелік СЕС. Перевірте вхід у дашборд.';});
})();
