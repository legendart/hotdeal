const SITE_LABELS = { ppomppu: '뽐뿌', clien: '클리앙', ruliweb: '루리웹' };
const FILTERS = [
  { id: 'all',      label: '🔥 전체' },
  { id: 'ppomppu',  label: '🛒 뽐뿌' },
  { id: 'clien',    label: '💻 클리앙' },
  { id: 'ruliweb',  label: '🎮 루리웹' },
];

let allDeals = [];
let currentFilter = 'all';

const grid       = document.getElementById('grid');
const statusDot  = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const filterTabs = document.getElementById('filterTabs');

function setStatus(type, msg) {
  statusDot.className = 'status-dot ' + type;
  statusText.textContent = msg;
}

function timeAgo(isoStr) {
  if (!isoStr) return '';
  const sec = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000);
  if (sec < 60)    return `${sec}초 전`;
  if (sec < 3600)  return `${Math.floor(sec / 60)}분 전`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}시간 전`;
  return `${Math.floor(sec / 86400)}일 전`;
}

function thumbHtml(item) {
  if (item.thumb) {
    return `<div class="card-thumb">
      <img src="${item.thumb}" alt="" loading="lazy"
        onerror="this.parentElement.classList.add('card-thumb--empty');this.remove()">
    </div>`;
  }
  return `<div class="card-thumb card-thumb--empty"></div>`;
}

function scoreHtml(item) {
  const s = item.score ?? 0;
  if (!s) return '';
  return `<span class="card-score">👍 ${s.toLocaleString()}</span>`;
}

function renderCards(deals) {
  if (!deals.length) {
    grid.innerHTML = '<div class="empty-msg">핫딜을 찾을 수 없습니다.</div>';
    return;
  }
  grid.innerHTML = deals.map(item => `
    <a class="card" href="${item.url}" target="_blank" rel="noopener noreferrer">
      ${thumbHtml(item)}
      <div class="card-body">
        <div class="card-meta">
          <span class="card-source card-source--${item.site}">${SITE_LABELS[item.site] || item.site}</span>
          ${scoreHtml(item)}
        </div>
        <div class="card-title">${item.title}</div>
        <div class="card-date">${timeAgo(item.crawled_at)}</div>
      </div>
    </a>
  `).join('');
}

function renderTabs() {
  filterTabs.innerHTML = FILTERS.map(f => `
    <button class="filter-tab${f.id === currentFilter ? ' active' : ''}" data-id="${f.id}">
      ${f.label}
    </button>
  `).join('');
  filterTabs.querySelectorAll('.filter-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      currentFilter = btn.dataset.id;
      renderTabs();
      applyFilter();
    });
  });
}

function applyFilter() {
  const filtered = currentFilter === 'all'
    ? allDeals
    : allDeals.filter(d => d.site === currentFilter);
  renderCards(filtered);
  setStatus('ok', `${filtered.length}개 핫딜`);
}

async function loadDeals() {
  setStatus('loading', '핫딜 불러오는 중...');
  grid.innerHTML = '<div class="loading-wrap"><div class="spinner"></div></div>';
  try {
    const res = await fetch('./data/deals.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    allDeals = await res.json();
    renderTabs();
    applyFilter();
  } catch (e) {
    setStatus('error', '로드 실패');
    grid.innerHTML = '<div class="empty-msg">핫딜을 불러오지 못했습니다.</div>';
  }
}

renderTabs();
loadDeals();
