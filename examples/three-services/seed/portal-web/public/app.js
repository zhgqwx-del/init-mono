const endpoint = '/ops/api/v1/campaigns';
const statusLabels = { DRAFT: '草稿', ACTIVE: '进行中', ENDED: '已结束' };
const form = document.querySelector('#filters');
const pageSize = document.querySelector('#page-size');
const rows = document.querySelector('#results');
const summary = document.querySelector('#summary');
const message = document.querySelector('#message');
const previous = document.querySelector('#previous');
const next = document.querySelector('#next');
const position = document.querySelector('#position');

let applied = { keyword: '', status: '' };
let requestedPage = 1;
let activeRequest = 0;

function renderRows(items) {
  rows.replaceChildren(...items.map(item => {
    const row = document.createElement('tr');
    const idCell = row.insertCell();
    idCell.className = 'activity-id';
    idCell.textContent = item.id;
    row.insertCell().textContent = item.name;
    const statusPill = document.createElement('span');
    statusPill.className = 'status-pill';
    statusPill.dataset.status = item.status;
    statusPill.textContent = statusLabels[item.status] ?? item.status;
    row.insertCell().append(statusPill);
    return row;
  }));
}

async function load(page) {
  requestedPage = page;
  const currentRequest = ++activeRequest;
  const limit = Number(pageSize.value);
  const params = new URLSearchParams({ page: String(page), pageSize: String(limit) });
  if (applied.keyword) params.set('keyword', applied.keyword);
  if (applied.status) params.set('status', applied.status);
  previous.disabled = next.disabled = true;
  summary.textContent = '查询中…';
  message.hidden = true;
  try {
    const response = await fetch(endpoint + '?' + params);
    if (!response.ok) throw new Error('List query failed');
    const { items, total } = await response.json();
    if (currentRequest !== activeRequest) return;
    renderRows(items);
    summary.textContent = '共 ' + total + ' 条';
    const pages = Math.max(1, Math.ceil(total / limit));
    position.textContent = '第 ' + page + ' / ' + pages + ' 页';
    previous.disabled = page <= 1;
    next.disabled = page >= pages;
    if (items.length === 0) {
      message.textContent = '暂无匹配的活动';
      message.hidden = false;
    }
  } catch {
    if (currentRequest !== activeRequest) return;
    renderRows([]);
    summary.textContent = '查询失败';
    message.textContent = '加载失败，请重新查询。';
    message.hidden = false;
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  const inputs = new FormData(form);
  applied = { keyword: inputs.get('keyword').trim(), status: inputs.get('status') };
  load(1);
});
pageSize.addEventListener('change', () => load(1));
previous.addEventListener('click', () => load(requestedPage - 1));
next.addEventListener('click', () => load(requestedPage + 1));
load(1);
