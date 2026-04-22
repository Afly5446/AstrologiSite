const compatibilityForm = document.getElementById("compatibilityForm");
const loaderSection = document.getElementById("loaderSection");
const resultSection = document.getElementById("resultSection");
const progressBar = document.getElementById("progressBar");
const resultTitle = document.getElementById("resultTitle");
const resultSubtitle = document.getElementById("resultSubtitle");
const westernText = document.getElementById("westernText");
const chineseText = document.getElementById("chineseText");
const numerologyText = document.getElementById("numerologyText");
const bonusText = document.getElementById("bonusText");
const strengthsList = document.getElementById("strengthsList");
const growthList = document.getElementById("growthList");
const weeklyAdvice = document.getElementById("weeklyAdvice");
const conflictTip = document.getElementById("conflictTip");
const forecastTip = document.getElementById("forecastTip");
const funTip = document.getElementById("funTip");
const aspectsText = document.getElementById("aspectsText");
const vectorText = document.getElementById("vectorText");
const timelineText = document.getElementById("timelineText");
const dynamicsText = document.getElementById("dynamicsText");
const greenFlagsList = document.getElementById("greenFlagsList");
const redFlagsList = document.getElementById("redFlagsList");
const areasText = document.getElementById("areasText");
const bestDaysList = document.getElementById("bestDaysList");
const energyTrendChart = document.getElementById("energyTrendChart");
const shareBtn = document.getElementById("shareBtn");
const copyLinkBtn = document.getElementById("copyLinkBtn");
const printPdfBtn = document.getElementById("printPdfBtn");
const downloadPngBtn = document.getElementById("downloadPngBtn");
const expertBtn = document.getElementById("expertBtn");
const crmForm = document.getElementById("crmForm");
const crmStatus = document.getElementById("crmStatus");
const themeToggle = document.getElementById("themeToggle");

let chart;
let trendChart;
let latestResult;

const GEO_SEARCH_URL = "https://geocoding-api.open-meteo.com/v1/search";

function expandMinimalCompatibilityResult(r) {
  if (r.advanced?.aspects?.mercury) {
    return r;
  }
  const elDyn =
    r.western?.element1 && r.western?.element2
      ? `Стихии ${r.western.element1} и ${r.western.element2}: смотрите полный расчёт на сервере с Swiss Ephemeris.`
      : "";
  const place = {
    moon1: "—",
    moon2: "—",
    moonAspect: "—",
    ...r.bonus,
  };
  return {
    ...r,
    western: {
      sign1: r.western?.sign1 || "—",
      sign2: r.western?.sign2 || "—",
      element1: r.western?.element1 || "",
      element2: r.western?.element2 || "",
      venusAspect: r.western?.venusAspect || "н/д",
      marsAspect: r.western?.marsAspect || "н/д",
      mercuryAspect: r.western?.mercuryAspect || "н/д",
      jupiterAspect: r.western?.jupiterAspect || "н/д",
      saturnAspect: r.western?.saturnAspect || "н/д",
      elementDynamics: r.western?.elementDynamics || elDyn,
    },
    bonus: place,
    birthMeta: r.birthMeta || {
      city1: "",
      city2: "",
      timezone1: "UTC",
      timezone2: "UTC",
    },
    numerology: {
      lifePath1: r.numerology?.lifePath1 ?? 0,
      lifePath2: r.numerology?.lifePath2 ?? 0,
      destiny1: r.numerology?.destiny1,
      destiny2: r.numerology?.destiny2,
      personalYear1: r.numerology?.personalYear1 ?? "—",
      personalYear2: r.numerology?.personalYear2 ?? "—",
    },
    advanced: {
      chineseDynamics:
        r.advanced?.chineseDynamics ||
        "Полная китайская динамика доступна при расчёте на основном сервере.",
      pairFlags: r.advanced?.pairFlags || {
        green: ["Упрощённый режим CDN: укажите backend с полным API для деталей."],
        red: [],
      },
      areaScores: r.advanced?.areaScores || {
        быт: 50,
        секс: 50,
        деньги: 50,
        коммуникация: 50,
        цели: 50,
      },
      bestDays: r.advanced?.bestDays || [],
      energyTrend: r.advanced?.energyTrend || [],
      aspects: {
        venus: { name: "н/д", orb: 0 },
        mars: { name: "н/д", orb: 0 },
        moon: { name: "н/д", orb: 0 },
        mercury: { name: "н/д", orb: 0 },
        jupiter: { name: "н/д", orb: 0 },
        saturn: { name: "н/д", orb: 0 },
        ...r.advanced?.aspects,
      },
      planetPositions: r.advanced?.planetPositions || {
        first: {},
        second: {},
      },
      compatibilityVector: r.advanced?.compatibilityVector || {
        emotional: 50,
        communication: 50,
        passion: 50,
        stability: 50,
      },
      timeline: r.advanced?.timeline || {
        m3: "",
        m6: "",
        m12: "",
      },
    },
    insights: {
      strengths: r.insights?.strengths || [],
      growth: r.insights?.growth || [],
      weeklyAdvice: r.insights?.weeklyAdvice || "",
      conflictTip: r.insights?.conflictTip || "",
      forecastTip: r.insights?.forecastTip || "",
      funTip: r.insights?.funTip || "",
    },
  };
}

/** Поля формы в query string; остальные параметры URL сохраняются при «Поделиться» и replaceState. */
const COMPAT_FORM_QUERY_KEYS = [
  "name1",
  "name2",
  "birth1",
  "birth2",
  "birthTime1",
  "birthTime2",
  "city1",
  "city2",
  "timezone1",
  "timezone2",
  "relationshipType",
];

const COMPAT_FORM_QUERY_KEY_SET = new Set(COMPAT_FORM_QUERY_KEYS);

function buildFormQueryString() {
  const params = new URLSearchParams();
  COMPAT_FORM_QUERY_KEYS.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    const v = el.value != null ? String(el.value).trim() : "";
    if (v) params.set(id, v);
  });
  return params.toString();
}

function applyQueryToForm(params) {
  COMPAT_FORM_QUERY_KEYS.forEach((id) => {
    const el = document.getElementById(id);
    if (!el || !params.has(id)) return;
    el.value = params.get(id);
  });
}

function getShareUrlWithParams() {
  const params = new URLSearchParams(buildFormQueryString());
  const fromUrl = new URLSearchParams(window.location.search);
  for (const [key, value] of fromUrl.entries()) {
    if (!COMPAT_FORM_QUERY_KEY_SET.has(key)) {
      params.set(key, value);
    }
  }
  const base = `${window.location.origin}${window.location.pathname}`;
  const q = params.toString();
  return q ? `${base}?${q}` : base;
}

let geoTimer1;
let geoTimer2;

function setupGeoSuggest(cityInputId, listId, tzInputId) {
  const input = document.getElementById(cityInputId);
  const list = document.getElementById(listId);
  const tzInput = document.getElementById(tzInputId);
  if (!input || !list || !tzInput) return;

  const hide = () => {
    list.classList.add("hidden");
    list.innerHTML = "";
  };

  input.addEventListener("blur", () => {
    setTimeout(hide, 200);
  });

  input.addEventListener("input", () => {
    const timerRef = cityInputId === "city1" ? geoTimer1 : geoTimer2;
    clearTimeout(timerRef);
    const q = input.value.trim();
    if (q.length < 2) {
      hide();
      return;
    }
    const run = async () => {
      try {
        const url = `${GEO_SEARCH_URL}?name=${encodeURIComponent(q)}&count=6&language=ru`;
        const res = await fetch(url);
        const data = await res.json();
        const results = data.results || [];
        list.innerHTML = "";
        if (!results.length) {
          hide();
          return;
        }
        results.forEach((place) => {
          const li = document.createElement("li");
          const label = place.name + (place.admin1 ? `, ${place.admin1}` : "") + ` — ${place.country}`;
          li.textContent = label;
          li.setAttribute("role", "option");
          li.addEventListener("mousedown", (e) => {
            e.preventDefault();
            input.value = place.name;
            if (place.timezone) {
              tzInput.value = place.timezone;
            }
            hide();
          });
          list.appendChild(li);
        });
        list.classList.remove("hidden");
      } catch {
        hide();
      }
    };
    if (cityInputId === "city1") {
      geoTimer1 = setTimeout(run, 280);
    } else {
      geoTimer2 = setTimeout(run, 280);
    }
  });
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("compat-theme", theme);
  if (window.tsParticlesInstance) {
    const colors = theme === "light" 
      ? ["#7c3aed", "#db2777", "#059669"]
      : ["#a78bfa", "#f472b6", "#34d399"];
    window.tsParticlesInstance.options.particles.color.value = colors;
    window.tsParticlesInstance.refresh();
  }
}

function initTheme() {
  const saved = localStorage.getItem("compat-theme");
  const prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
  setTheme(saved || (prefersLight ? "light" : "dark"));
}

function listItems(target, items) {
  target.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    target.appendChild(li);
  });
}

function drawChart(score) {
  if (chart) chart.destroy();
  const ctx = document.getElementById("scoreChart");
  chart = new Chart(ctx, {
    type: "doughnut",
    data: {
      datasets: [
        {
          data: [score, 100 - score],
          backgroundColor: ["#8a6bff", "rgba(255,255,255,0.15)"],
          borderWidth: 0,
        },
      ],
    },
    options: {
      cutout: "72%",
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });
}

function drawEnergyTrend(trend, bestDays = []) {
  if (!energyTrendChart || !Array.isArray(trend)) return;
  if (trendChart) trendChart.destroy();

  const labels = trend.map((item) => item.date.slice(5));
  const values = trend.map((item) => item.score);
  const bestDayDates = new Set(bestDays.map((day) => day.date));
  const markerValues = trend.map((item) =>
    bestDayDates.has(item.date) ? item.score : null
  );

  trendChart = new Chart(energyTrendChart, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Энергия пары",
          data: values,
          borderColor: "#8a6bff",
          backgroundColor: "rgba(138,107,255,0.2)",
          tension: 0.35,
          fill: true,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "Топ-5 дней",
          data: markerValues,
          showLine: false,
          pointRadius: 5,
          pointHoverRadius: 6,
          pointBackgroundColor: "#ff5db1",
          pointBorderColor: "#ffffff",
          pointBorderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
      scales: {
        x: { ticks: { maxTicksLimit: 6, color: "#8b92be" }, grid: { display: false } },
        y: { ticks: { maxTicksLimit: 4, color: "#8b92be" }, grid: { color: "rgba(255,255,255,0.08)" } },
      },
    },
  });
}

async function showLoading() {
  loaderSection.classList.remove("hidden");
  resultSection.classList.add("hidden");
  progressBar.style.width = "0%";
  const steps = 36;
  for (let i = 1; i <= steps; i += 1) {
    progressBar.style.width = `${Math.round((i / steps) * 100)}%`;
    await new Promise((resolve) => setTimeout(resolve, 170));
  }
}

function renderResult(result, person1, person2) {
  result = expandMinimalCompatibilityResult(result);
  const title1 = person1 || "Вы";
  const title2 = person2 || "Партнер";
  resultTitle.textContent = `💕 Совместимость: ${result.total}/100`;
  resultSubtitle.textContent = `${title1} + ${title2} | ${result.relationProfile.label}`;

  westernText.textContent = `${result.western.sign1} + ${result.western.sign2}: стихии ${result.western.element1} и ${result.western.element2}. Венера: ${result.western.venusAspect}, Марс: ${result.western.marsAspect}. Меркурий: ${result.western.mercuryAspect}, Юпитер: ${result.western.jupiterAspect}, Сатурн: ${result.western.saturnAspect}.`;
  chineseText.textContent = `${result.chinese.first.animal} (${result.chinese.first.element}) + ${result.chinese.second.animal} (${result.chinese.second.element}): ${result.advanced.chineseDynamics}`;
  numerologyText.textContent = `ЧЖП: ${result.numerology.lifePath1} + ${result.numerology.lifePath2}. ${
    result.numerology.destiny1 && result.numerology.destiny2
      ? `Число судьбы по именам: ${result.numerology.destiny1} и ${result.numerology.destiny2}. `
      : ""
  }Личный год: ${result.numerology.personalYear1} / ${result.numerology.personalYear2}.`;
  const cityLine =
    result.birthMeta?.city1 || result.birthMeta?.city2
      ? ` Гео: ${result.birthMeta?.city1 || "не указано"} / ${result.birthMeta?.city2 || "не указано"}.`
      : "";
  bonusText.textContent = `Луна ${title1}: ${result.bonus.moon1}, Луна ${title2}: ${result.bonus.moon2}. Между ними: ${result.bonus.moonAspect}. Часовые пояса: ${result.birthMeta?.timezone1 || "UTC"} и ${result.birthMeta?.timezone2 || "UTC"}.${cityLine}`;
  aspectsText.textContent = `Венера: ${result.advanced.aspects.venus.name} (${result.advanced.aspects.venus.orb}°), Марс: ${result.advanced.aspects.mars.name} (${result.advanced.aspects.mars.orb}°), Луна: ${result.advanced.aspects.moon.name} (${result.advanced.aspects.moon.orb}°). Меркурий: ${result.advanced.aspects.mercury.name} (${result.advanced.aspects.mercury.orb}°), Юпитер: ${result.advanced.aspects.jupiter.name} (${result.advanced.aspects.jupiter.orb}°), Сатурн: ${result.advanced.aspects.saturn.name} (${result.advanced.aspects.saturn.orb}°).`;
  vectorText.textContent = `Эмоции ${result.advanced.compatibilityVector.emotional}/100, Коммуникация ${result.advanced.compatibilityVector.communication}/100, Страсть ${result.advanced.compatibilityVector.passion}/100, Стабильность ${result.advanced.compatibilityVector.stability}/100.`;
  timelineText.textContent = `${result.advanced.timeline.m3} ${result.advanced.timeline.m6} ${result.advanced.timeline.m12}`;
  dynamicsText.textContent = `${result.western.elementDynamics} Позиции Солнца: ${result.advanced.planetPositions.first.sun}° / ${result.advanced.planetPositions.second.sun}°.`;
  listItems(greenFlagsList, result.advanced.pairFlags.green);
  listItems(redFlagsList, result.advanced.pairFlags.red);
  areasText.textContent = `Быт ${result.advanced.areaScores["быт"]}/100, Секс ${result.advanced.areaScores["секс"]}/100, Деньги ${result.advanced.areaScores["деньги"]}/100, Коммуникация ${result.advanced.areaScores["коммуникация"]}/100, Цели ${result.advanced.areaScores["цели"]}/100.`;
  listItems(
    bestDaysList,
    result.advanced.bestDays.map(
      (day) => `${day.date}: ${day.phase}. ${day.reason}`
    )
  );
  drawEnergyTrend(result.advanced.energyTrend, result.advanced.bestDays);

  listItems(strengthsList, result.insights.strengths);
  listItems(growthList, result.insights.growth);
  weeklyAdvice.textContent = result.insights.weeklyAdvice;
  conflictTip.textContent = result.insights.conflictTip;
  forecastTip.textContent = result.insights.forecastTip;
  funTip.textContent = result.insights.funTip;

  drawChart(result.total);
  loaderSection.classList.add("hidden");
  resultSection.classList.remove("hidden");
}

async function requestCompatibility(payload) {
  const response = await fetch("/api/compatibility", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Ошибка расчета");
  }
  return data;
}

compatibilityForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    name1: document.getElementById("name1").value.trim(),
    name2: document.getElementById("name2").value.trim(),
    birth1: document.getElementById("birth1").value,
    birth2: document.getElementById("birth2").value,
    birthTime1: document.getElementById("birthTime1").value,
    birthTime2: document.getElementById("birthTime2").value,
    city1: document.getElementById("city1").value.trim(),
    city2: document.getElementById("city2").value.trim(),
    timezone1: document.getElementById("timezone1").value.trim() || "UTC",
    timezone2: document.getElementById("timezone2").value.trim() || "UTC",
    relationshipType: document.getElementById("relationshipType").value,
  };
  if (!payload.birth1 || !payload.birth2) return;

  try {
    await showLoading();
    latestResult = await requestCompatibility(payload);
    latestResult.shareNames = [payload.name1, payload.name2];
    renderResult(latestResult, payload.name1, payload.name2);
    const shareUrl = getShareUrlWithParams();
    window.history.replaceState({}, "", shareUrl || window.location.pathname);
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    loaderSection.classList.add("hidden");
    alert(error.message || "Не удалось рассчитать совместимость.");
  }
});

shareBtn.addEventListener("click", async () => {
  if (!latestResult) return;
  const shareUrl = getShareUrlWithParams();
  const shareText = `Наша совместимость: ${latestResult.total}/100. Расчёт калькулятора ✨`;
  try {
    if (navigator.share) {
      await navigator.share({
        title: "Калькулятор совместимости",
        text: shareText,
        url: shareUrl,
      });
      return;
    }
    await navigator.clipboard.writeText(`${shareText}\n${shareUrl}`);
    alert("Текст и ссылка скопированы в буфер обмена.");
  } catch (_error) {
    alert("Не удалось поделиться. Используйте «Копировать ссылку».");
  }
});

if (copyLinkBtn) {
  copyLinkBtn.addEventListener("click", async () => {
    const url = getShareUrlWithParams();
    try {
      await navigator.clipboard.writeText(url);
      alert("Ссылка скопирована — при открытии подставятся даты расчёта.");
    } catch {
      prompt("Скопируйте ссылку:", url);
    }
  });
}

if (printPdfBtn) {
  printPdfBtn.addEventListener("click", () => {
    if (!latestResult) return;
    window.print();
  });
}

downloadPngBtn.addEventListener("click", async () => {
  if (!latestResult) return;
  const node = document.getElementById("resultSection");
  const canvas = await html2canvas(node, {
    backgroundColor: null,
    useCORS: true,
    scale: 2,
  });
  const link = document.createElement("a");
  link.download = `compatibility-${latestResult.total}.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
});

expertBtn.addEventListener("click", () => {
  document.getElementById("crmName").focus();
  crmForm.scrollIntoView({ behavior: "smooth", block: "center" });
});

crmForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  crmStatus.className = "status-text";
  crmStatus.textContent = "Отправляем заявку...";
  const payload = {
    name: document.getElementById("crmName").value.trim(),
    contact: document.getElementById("crmContact").value.trim(),
    message: document.getElementById("crmMessage").value.trim(),
    context: latestResult
      ? {
          score: latestResult.total,
          relationType: latestResult.relationProfile.label,
          timezone1: latestResult.birthMeta?.timezone1,
          timezone2: latestResult.birthMeta?.timezone2,
          city1: latestResult.birthMeta?.city1,
          city2: latestResult.birthMeta?.city2,
        }
      : {},
  };
  try {
    const response = await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Не удалось отправить заявку");
    }
    crmStatus.className = "status-text success";
    crmStatus.textContent = "Заявка отправлена. Мы свяжемся с вами в ближайшее время.";
    crmForm.reset();
  } catch (error) {
    crmStatus.className = "status-text error";
    crmStatus.textContent = error.message || "Ошибка отправки.";
  }
});

themeToggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  setTheme(current === "dark" ? "light" : "dark");
});

initTheme();

setupGeoSuggest("city1", "geoSuggest1", "timezone1");
setupGeoSuggest("city2", "geoSuggest2", "timezone2");

(() => {
  const params = new URLSearchParams(window.location.search);
  // Параметры _ym* добавляет Метрика (проверка счётчика, отладка). Автоотправка формы даёт replaceState и лишнюю нагрузку до загрузки tag.js.
  if ([...params.keys()].some((k) => k.startsWith("_ym"))) return;
  if (!params.has("birth1") || !params.has("birth2")) return;
  applyQueryToForm(params);
  if (typeof compatibilityForm.requestSubmit === "function") {
    compatibilityForm.requestSubmit();
  } else {
    compatibilityForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
  }
})();

window.tsParticlesInstance = null;

tsParticles.load("particles", {
  options: {
    background: { color: "transparent" },
    fpsLimit: 60,
    particles: {
      number: { value: 34 },
      color: { value: ["#a78bfa", "#f472b6", "#34d399"] },
      shape: { type: "circle" },
      opacity: { value: { min: 0.15, max: 0.45 } },
      size: { value: { min: 1, max: 3 } },
      move: { enable: true, speed: 1.2, outModes: { default: "out" } },
      links: {
        enable: true,
        distance: 140,
        color: { value: "inherit" },
        opacity: { value: 0.2 },
      },
    },
  },
}).then((container) => {
  window.tsParticlesInstance = container;
});

const decorStars = document.getElementById("decorStars");
if (decorStars) {
  for (let i = 0; i < 50; i++) {
    const star = document.createElement("div");
    star.className = "star";
    const size = Math.random() * 2 + 1;
    star.style.width = size + "px";
    star.style.height = size + "px";
    star.style.left = Math.random() * 100 + "%";
    star.style.top = Math.random() * 100 + "%";
    star.style.animationDelay = Math.random() * 3 + "s";
    star.style.animationDuration = (Math.random() * 2 + 2) + "s";
    decorStars.appendChild(star);
  }
}

const chatToggle = document.getElementById("chatToggle");
const chatPanel = document.getElementById("chatPanel");
const chatClose = document.getElementById("chatClose");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");

let chatSessionId = localStorage.getItem("chat-session") || crypto.randomUUID();
localStorage.setItem("chat-session", chatSessionId);

let chatInitialized = localStorage.getItem("chat-initialized") === "true";

function initChat() {
  if (!chatInitialized) {
    addMessage(
      "Привет! Я коуч по отношениям — отвечу бесплатно, без регистрации. Переписку не показываем другим. Расскажите, что хотите разобрать.",
      "assistant",
    );
    chatInitialized = true;
    localStorage.setItem("chat-initialized", "true");
  }
}

if (chatToggle && chatPanel) {
  chatToggle.onclick = function() {
    chatPanel.classList.remove("hidden");
    chatToggle.style.display = "none";
    chatInput.focus();
    initChat();
  };
}

if (chatClose && chatPanel && chatToggle) {
  chatClose.onclick = function() {
    chatPanel.classList.add("hidden");
    chatToggle.style.display = "";
  };
}

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `chat-message ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping() {
  const div = document.createElement("div");
  div.className = "chat-message typing typing-indicator";
  div.id = "typingIndicator";
  div.setAttribute("aria-live", "polite");
  div.innerHTML =
    '<span class="typing-label">Эксперт отвечает</span><span class="typing-dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>';
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

function hideTyping() {
  const typing = document.getElementById("typingIndicator");
  typing?.remove();
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  const sendBtn = chatForm.querySelector(".chat-send");
  if (sendBtn) sendBtn.disabled = true;
  chatInput.disabled = true;

  addMessage(message, "user");
  chatInput.value = "";

  const typing = showTyping();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: chatSessionId }),
    });
    const data = await response.json();
    typing.remove();
    if (!response.ok) {
      addMessage(data.error || "Не удалось получить ответ", "assistant");
      return;
    }
    addMessage(data.reply, "assistant");
  } catch (error) {
    typing.remove();
    addMessage("Ошибка соединения. Попробуйте ещё раз.", "assistant");
  } finally {
    if (sendBtn) sendBtn.disabled = false;
    chatInput.disabled = false;
    chatInput.focus();
  }
});
