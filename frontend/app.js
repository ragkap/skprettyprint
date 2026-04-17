const base = window.location.origin;
const snippets = {
  'api-base': base,
  'curl-primer': `curl -L -o primer.pdf \\\n  "${base}/api/primer?ticker=DBS%20SP"`,
  'curl-primer-oj': `curl -LOJ "${base}/api/primer?ticker=DBS%20SP"`,
  'curl-search': `curl -s "${base}/api/search?q=DBS"`,
};
Object.entries(snippets).forEach(([id, text]) => {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
});

document.querySelectorAll('.copy-btn').forEach((btn) => {
  btn.addEventListener('click', async () => {
    const target = document.getElementById(btn.dataset.copy);
    if (!target) return;
    try {
      await navigator.clipboard.writeText(target.textContent);
      const original = btn.textContent;
      btn.textContent = 'Copied';
      btn.classList.add('is-copied');
      setTimeout(() => {
        btn.textContent = original;
        btn.classList.remove('is-copied');
      }, 1400);
    } catch {
      btn.textContent = 'Failed';
    }
  });
});

const tabs = document.querySelectorAll('.tab');
const panels = {
  primer: document.getElementById('panel-primer'),
  insight: document.getElementById('panel-insight'),
  ebook: document.getElementById('panel-ebook'),
};

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    tabs.forEach((t) => t.classList.remove('is-active'));
    Object.values(panels).forEach((p) => p.classList.remove('is-active'));
    tab.classList.add('is-active');
    panels[tab.dataset.tab].classList.add('is-active');
  });
});

const form = document.getElementById('primer-form');
const searchInput = document.getElementById('search');
const tickerHidden = document.getElementById('ticker');
const results = document.getElementById('search-results');
const combobox = results.parentElement;
const btn = document.getElementById('submit-btn');
const status = document.getElementById('status');

function setStatus(msg, kind = '') {
  status.textContent = msg;
  status.className = 'status' + (kind ? ' is-' + kind : '');
}

let activeIdx = -1;
let currentResults = [];
let debounceTimer = null;
let currentReq = 0;

function closeDropdown() {
  results.hidden = true;
  combobox.setAttribute('aria-expanded', 'false');
  activeIdx = -1;
}

function openDropdown() {
  results.hidden = false;
  combobox.setAttribute('aria-expanded', 'true');
}

function renderResults(items) {
  currentResults = items;
  results.innerHTML = '';
  if (!items.length) {
    const li = document.createElement('li');
    li.className = 'res-empty';
    li.textContent = 'No matches';
    results.appendChild(li);
    openDropdown();
    return;
  }
  items.forEach((item, i) => {
    const li = document.createElement('li');
    li.setAttribute('role', 'option');
    li.dataset.index = i;
    const name = document.createElement('span');
    name.className = 'res-name';
    name.textContent = item.name;
    const tk = document.createElement('span');
    tk.className = 'res-ticker';
    tk.textContent = item.ticker;
    li.appendChild(name);
    li.appendChild(tk);
    li.addEventListener('mousedown', (e) => {
      e.preventDefault();
      selectItem(i);
    });
    results.appendChild(li);
  });
  openDropdown();
}

function highlight(idx) {
  [...results.children].forEach((el, i) =>
    el.classList.toggle('is-active', i === idx)
  );
  activeIdx = idx;
}

function selectItem(i) {
  const item = currentResults[i];
  if (!item) return;
  searchInput.value = `${item.name} — ${item.ticker}`;
  tickerHidden.value = item.ticker;
  closeDropdown();
}

async function runSearch(q) {
  const reqId = ++currentReq;
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    if (!res.ok) {
      if (reqId === currentReq) closeDropdown();
      return;
    }
    const { results: items } = await res.json();
    if (reqId !== currentReq) return;
    renderResults(items);
  } catch {
    if (reqId === currentReq) closeDropdown();
  }
}

searchInput.addEventListener('input', () => {
  tickerHidden.value = '';
  const q = searchInput.value.trim();
  clearTimeout(debounceTimer);
  if (q.length < 2) {
    closeDropdown();
    return;
  }
  debounceTimer = setTimeout(() => runSearch(q), 180);
});

searchInput.addEventListener('keydown', (e) => {
  if (results.hidden || !currentResults.length) return;
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    highlight((activeIdx + 1) % currentResults.length);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    highlight((activeIdx - 1 + currentResults.length) % currentResults.length);
  } else if (e.key === 'Enter') {
    if (activeIdx >= 0) {
      e.preventDefault();
      selectItem(activeIdx);
    }
  } else if (e.key === 'Escape') {
    closeDropdown();
  }
});

searchInput.addEventListener('blur', () => {
  setTimeout(closeDropdown, 120);
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  let ticker = tickerHidden.value.trim();
  if (!ticker) {
    const raw = searchInput.value.trim();
    const m = /—\s*([A-Z0-9.\- ]+)\s*$/i.exec(raw);
    ticker = m ? m[1].trim() : raw;
  }
  if (!ticker) {
    setStatus('Select a company or enter a Bloomberg ticker.', 'error');
    return;
  }

  btn.disabled = true;
  setStatus('Generating PDF — this may take 10–20 seconds…');

  try {
    const res = await fetch(`/api/primer?ticker=${encodeURIComponent(ticker)}`);
    if (!res.ok) {
      let msg = `Error ${res.status}`;
      try {
        const err = await res.json();
        if (err.detail) msg = err.detail;
      } catch (_) {}
      setStatus(msg, 'error');
      return;
    }

    const blob = await res.blob();
    const disposition = res.headers.get('Content-Disposition') || '';
    const match = /filename="([^"]+)"/.exec(disposition);
    const filename = match ? decodeURIComponent(match[1]) : `${ticker}.pdf`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    setStatus(`Downloaded: ${filename}`, 'success');
  } catch (err) {
    setStatus(err.message || 'Network error', 'error');
  } finally {
    btn.disabled = false;
  }
});
