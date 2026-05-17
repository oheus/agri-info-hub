const DATA_URL = window.location.pathname.includes("/web/")
  ? "../data/items.json"
  : "./data/items.json";

const state = {
  items: [],
  stats: {},
  run: {},
  category: "all",
  query: "",
  sort: "latest",
  view: "home",
};

const categoryLabels = {
  news: "뉴스",
  plant_reviews: "식물 리뷰",
  support: "지원사업",
};

const categoryColors = {
  news: "#416f92",
  plant_reviews: "#2f7d57",
  support: "#c58b2b",
};

const categoryImages = {
  news: "./assets/images/plant2.jpg",
  plant_reviews: "./assets/images/plant1.jpg",
  support: "./assets/images/plant3.jpg",
};

const elements = {
  lastUpdated: document.querySelector("#lastUpdated"),
  metricTotal: document.querySelector("#metricTotal"),
  metricNews: document.querySelector("#metricNews"),
  metricPlant: document.querySelector("#metricPlant"),
  metricSupport: document.querySelector("#metricSupport"),
  homeNewCount: document.querySelector("#homeNewCount"),
  homeLeadCategory: document.querySelector("#homeLeadCategory"),
  homeTopKeyword: document.querySelector("#homeTopKeyword"),
  keywordTotal: document.querySelector("#keywordTotal"),
  homeLatestList: document.querySelector("#homeLatestList"),
  categoryBars: document.querySelector("#categoryBars"),
  keywordCloud: document.querySelector("#keywordCloud"),
  itemsList: document.querySelector("#itemsList"),
  resultCount: document.querySelector("#resultCount"),
  sourceList: document.querySelector("#sourceList"),
  errorList: document.querySelector("#errorList"),
  runStatus: document.querySelector("#runStatus"),
  newItems: document.querySelector("#newItems"),
  searchInput: document.querySelector("#searchInput"),
  homeLink: document.querySelector("[data-home-link]"),
  navButtons: document.querySelectorAll(".nav-button"),
  viewJumps: document.querySelectorAll("[data-view-jump]"),
  metricLinks: document.querySelectorAll("[data-feed-category]"),
  views: document.querySelectorAll(".view"),
  categoryTabs: document.querySelectorAll(".category-tab"),
  sortTabs: document.querySelectorAll(".sort-tab"),
};

function formatDate(value) {
  if (!value) return "날짜 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "날짜 없음";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function normalize(value) {
  return String(value || "").toLowerCase();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function safeUrl(value) {
  if (/\s/.test(String(value || ""))) return "";
  try {
    const url = new URL(value, window.location.href);
    if (url.protocol === "http:" || url.protocol === "https:") return url.href;
  } catch (error) {
    return "";
  }
  return "";
}

function switchView(view) {
  state.view = view;
  elements.views.forEach((section) => {
    section.classList.toggle("active", section.id === `${view}View`);
  });
  elements.navButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
}

function setCategory(category) {
  state.category = category;
  elements.categoryTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.category === category);
  });
  renderItems();
}

function setSort(sort) {
  state.sort = sort;
  elements.sortTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.sort === sort);
  });
  renderItems();
}

function openFeedCategory(category) {
  state.query = "";
  elements.searchInput.value = "";
  setCategory(category);
  switchView("feed");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function itemTime(item) {
  const date = new Date(item.published_at || item.collected_at || 0);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function deadlineTime(item) {
  if (!item.deadline_date) return Number.POSITIVE_INFINITY;
  const date = new Date(item.deadline_date);
  return Number.isNaN(date.getTime()) ? Number.POSITIVE_INFINITY : date.getTime();
}

function filteredItems() {
  const query = normalize(state.query);
  const items = state.items.filter((item) => {
    const categoryMatch = state.category === "all" || item.category === state.category;
    const queryText = normalize([
      item.title,
      item.summary,
      item.source,
      item.region,
      item.deadline_text,
      ...(item.keywords || []),
    ].join(" "));
    return categoryMatch && (!query || queryText.includes(query));
  });

  return items.sort((a, b) => {
    if (state.sort === "importance") {
      return (b.importance || 0) - (a.importance || 0) || itemTime(b) - itemTime(a);
    }
    if (state.sort === "support") {
      return Number(b.category === "support") - Number(a.category === "support")
        || (b.importance || 0) - (a.importance || 0)
        || itemTime(b) - itemTime(a);
    }
    if (state.sort === "deadline") {
      return deadlineTime(a) - deadlineTime(b)
        || Number(b.category === "support") - Number(a.category === "support")
        || (b.importance || 0) - (a.importance || 0);
    }
    return itemTime(b) - itemTime(a);
  });
}

function renderMetrics() {
  const counts = state.stats.category_counts || {};
  const leadCategory = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .find(([, count]) => count > 0);
  const topKeyword = state.stats.top_keywords?.[0]?.keyword;

  elements.metricTotal.textContent = state.stats.total || 0;
  elements.metricNews.textContent = counts.news || 0;
  elements.metricPlant.textContent = counts.plant_reviews || 0;
  elements.metricSupport.textContent = counts.support || 0;
  elements.runStatus.textContent = state.run.status || "not_run";
  elements.homeNewCount.textContent = `${state.run.new_items || 0}건`;
  elements.homeLeadCategory.textContent = leadCategory ? categoryLabels[leadCategory[0]] : "-";
  elements.homeTopKeyword.textContent = topKeyword || "-";
  elements.newItems.textContent = `${state.run.new_items || 0}건 신규`;
  elements.lastUpdated.textContent = state.generated_at ? formatDate(state.generated_at) : "대기 중";
}

function renderBars() {
  const counts = state.stats.category_counts || {};
  const max = Math.max(1, ...Object.values(counts));
  elements.categoryBars.innerHTML = Object.entries(categoryLabels).map(([key, label]) => {
    const count = counts[key] || 0;
    const width = Math.max(4, Math.round((count / max) * 100));
    return `
      <div class="bar-row">
        <span>${escapeHtml(label)}</span>
        <div class="bar-track" aria-hidden="true">
          <div class="bar-fill" style="width:${width}%; background:${categoryColors[key]}"></div>
        </div>
        <strong>${count}</strong>
      </div>
    `;
  }).join("");
}

function renderKeywords() {
  const keywords = state.stats.top_keywords || [];
  elements.keywordTotal.textContent = `${keywords.length}개`;
  if (!keywords.length) {
    elements.keywordCloud.innerHTML = `<div class="empty-state">수집기가 실행되면 키워드가 채워집니다.</div>`;
    return;
  }
  elements.keywordCloud.innerHTML = keywords.map((item) => (
    `<span class="keyword">${escapeHtml(item.keyword)} ${item.count}</span>`
  )).join("");
}

function itemMarkup(item, compact = false) {
  const date = item.published_at || item.collected_at;
  const keywords = (item.keywords || []).slice(0, compact ? 3 : 5).map((keyword) => (
    `<span class="mini-keyword">#${escapeHtml(keyword)}</span>`
  )).join("");
  const title = escapeHtml(item.title);
  const summary = escapeHtml(item.summary || item.title);
  const source = escapeHtml(item.source);
  const url = safeUrl(item.url);
  const categoryLabel = escapeHtml(categoryLabels[item.category] || item.category);
  const categoryClass = Object.hasOwn(categoryLabels, item.category) ? item.category : "news";
  const region = item.region ? `<span class="info-chip">${escapeHtml(item.region)}</span>` : "";
  const deadline = item.deadline_text ? `<span class="info-chip deadline">${escapeHtml(item.deadline_text)}</span>` : "";
  const titleMarkup = url
    ? `<a href="${url}">${title}</a>`
    : `<span>${title}</span>`;
  const sourceLink = url
    ? `<a class="open-link" href="${url}">원문 보기</a>`
    : `<span class="open-link disabled">링크 없음</span>`;
  const visual = compact
    ? `<div class="compact-image" style="background-image: url('${categoryImages[categoryClass]}')"></div>`
    : "";

  return `
    <article class="item-card ${compact ? "compact-card" : ""}">
      ${visual}
      <div class="item-top">
        <span class="badge ${categoryClass}">${categoryLabel}</span>
        <span class="importance">중요도 ${item.importance}</span>
      </div>
      <h3>${titleMarkup}</h3>
      ${region || deadline ? `<div class="item-signals">${region}${deadline}</div>` : ""}
      ${compact ? "" : `<p class="item-summary">${summary}</p>`}
      <div class="item-footer">
        <div class="item-meta">${source} · ${formatDate(date)}</div>
        <div class="item-actions">
          <div class="item-keywords">${keywords}</div>
          ${sourceLink}
        </div>
      </div>
    </article>
  `;
}

function renderHomeLatest() {
  const latest = [...state.items]
    .sort((a, b) => (b.importance || 0) - (a.importance || 0))
    .slice(0, 4);

  if (!latest.length) {
    elements.homeLatestList.innerHTML = `<div class="empty-state">아직 표시할 정보가 없습니다.</div>`;
    return;
  }

  elements.homeLatestList.innerHTML = latest.map((item) => itemMarkup(item, true)).join("");
}

function renderItems() {
  const items = filteredItems();
  elements.resultCount.textContent = `${items.length}건`;

  if (!items.length) {
    elements.itemsList.innerHTML = `<div class="empty-state">아직 표시할 정보가 없습니다.</div>`;
    return;
  }

  elements.itemsList.innerHTML = items.map((item) => itemMarkup(item)).join("");
}

function renderSources() {
  const sources = state.stats.top_sources || [];
  if (!sources.length) {
    elements.sourceList.innerHTML = `<div class="empty-state">출처 없음</div>`;
    return;
  }
  elements.sourceList.innerHTML = sources.map((item) => `
    <div class="source-row">
      <span>${escapeHtml(item.source)}</span>
      <strong>${item.count}</strong>
    </div>
  `).join("");
}

function renderErrors() {
  const errors = state.run.errors || [];
  if (!errors.length) {
    elements.errorList.innerHTML = `<div class="status-row"><span>정상</span></div>`;
    return;
  }
  elements.errorList.innerHTML = errors.map((error) => `
    <div class="status-row">
      <span>${escapeHtml(error.source)}: ${escapeHtml(error.error)}</span>
    </div>
  `).join("");
}

function render() {
  renderMetrics();
  renderBars();
  renderKeywords();
  renderHomeLatest();
  renderItems();
  renderSources();
  renderErrors();
}

async function loadData() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.items = payload.items || [];
    state.stats = payload.stats || {};
    state.run = payload.run || {};
    state.generated_at = payload.generated_at;
  } catch (error) {
    state.run = {
      status: "load_failed",
      new_items: 0,
      errors: [{ source: "dashboard", error: error.message }],
    };
  }
  render();
}

elements.searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderItems();
});

elements.homeLink.addEventListener("click", () => {
  switchView("home");
  window.scrollTo({ top: 0, behavior: "smooth" });
});

elements.navButtons.forEach((button) => {
  button.addEventListener("click", () => {
    switchView(button.dataset.view);
  });
});

elements.viewJumps.forEach((button) => {
  button.addEventListener("click", () => {
    switchView(button.dataset.viewJump);
  });
});

elements.metricLinks.forEach((card) => {
  card.addEventListener("click", () => {
    openFeedCategory(card.dataset.feedCategory);
  });
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openFeedCategory(card.dataset.feedCategory);
    }
  });
});

elements.categoryTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    setCategory(tab.dataset.category);
  });
});

elements.sortTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    setSort(tab.dataset.sort);
  });
});

loadData();
