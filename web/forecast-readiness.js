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
  const sourceLabel = (channel) => `${channel.name}: ${channel.role} · ${channel.status}`;
  const scoreLabel = (score) => {
    const weight = Math.round(score.weight * 1000) / 10;
    const mae = Math.round(score.maeKw * 100) / 100;
    return `${score.id}: вага ${weight}%; MAE ${mae} кВт; пар ${score.pairCount}`;
  };
  const list = (className, values, formatter, emptyText) => {
    const element = document.createElement("ul");
    element.className = className;
    if (!values.length) {
      const entry = document.createElement("li");
      entry.append(text(emptyText));
      element.append(entry);
      return element;
    }
    values.forEach((value) => {
      const entry = document.createElement("li");
      entry.append(text(formatter(value)));
      element.append(entry);
    });
    return element;
  };
  const row = (item) => {
    const article = document.createElement("article");
    article.className = "readiness-item " + item.state;
    const title = document.createElement("strong");
    title.append(text(item.plantName));
    const state = document.createElement("span");
    state.append(text(labels[item.state] || "Статус уточнюється"));
    const details = document.createElement("p");
    details.append(text(`Фактів: ${item.actualIntervalCount}; погодних каналів: ${item.configuredProviderCount}; відкалібровано: ${item.calibratedProviderCount}.`));
    const channels = list("readiness-sources", item.weatherChannels || [], sourceLabel,
      "Погодні канали ще не додано.");
    const scores = list("readiness-scores", item.providerScores || [], scoreLabel,
      "Ваги з’являться після перевірених прогнозів і фактичної генерації.");
    article.append(title, state, details, channels, scores);
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

