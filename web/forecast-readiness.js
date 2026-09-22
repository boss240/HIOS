(() => {
  const target = document.getElementById("forecastReadinessList");
  if (!target) return;
  const labels = {
    awaiting_cloud_authorization: "Очікується read-only підтвердження",
    awaiting_actuals: "Очікуються фактичні дані",
    calibration_pending: "Дані збираються для кореляції",
    calibrated: "Мікс джерел відкалібровано"
  };
  const text = (value) => document.createTextNode(value);
  const row = (item) => {
    const article = document.createElement("article");
    article.className = "readiness-item " + item.state;
    const title = document.createElement("strong");
    title.append(text(item.plantName));
    const state = document.createElement("span");
    state.append(text(labels[item.state] || "Статус уточнюється"));
    const details = document.createElement("p");
    details.append(text(`Фактів: ${item.actualIntervalCount}; погодних каналів: ${item.configuredProviderCount}; відкалібровано: ${item.calibratedProviderCount}.`));
    article.append(title, state, details);
    return article;
  };
  fetch("/dashboard/forecast-readiness", {credentials: "same-origin"})
    .then((response) => response.ok ? response.json() : Promise.reject())
    .then((payload) => {
      target.replaceChildren();
      if (!payload.data.length) target.append(text("Додайте СЕС — вона автоматично з’явиться тут."));
      payload.data.forEach((item) => target.append(row(item)));
    })
    .catch(() => { target.textContent = "Статус з’явиться після входу в захищений дашборд."; });
})();

