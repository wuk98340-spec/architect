
(function () {
  const search = document.querySelector('#caseSearch');
  const cards = Array.from(document.querySelectorAll('.case-card'));
  const sortSelect = document.querySelector('#sortSelect');
  const empty = document.querySelector('#emptyState');
  const activeFilters = document.querySelector('#activeFilters');
  const filterButtons = Array.from(document.querySelectorAll('[data-filter]'));
  const grid = document.querySelector('#caseGrid');
  const state = { type: 'all', region: 'all', q: '', sort: 'year-desc' };

  function readParams() {
    const params = new URLSearchParams(window.location.search);
    state.q = params.get('q') || '';
    state.type = params.get('type') || 'all';
    state.region = params.get('region') || 'all';
    state.sort = params.get('sort') || 'year-desc';
    if (search) search.value = state.q;
    if (sortSelect) sortSelect.value = state.sort;
  }

  function writeParams() {
    const params = new URLSearchParams();
    if (state.q) params.set('q', state.q);
    if (state.type !== 'all') params.set('type', state.type);
    if (state.region !== 'all') params.set('region', state.region);
    if (state.sort !== 'year-desc') params.set('sort', state.sort);
    const next = params.toString() ? '?' + params.toString() : window.location.pathname;
    window.history.replaceState(null, '', next);
  }

  function sortCards(items) {
    return items.sort((a, b) => {
      if (state.sort === 'year-asc') return Number(a.dataset.year) - Number(b.dataset.year);
      if (state.sort === 'title-asc') return a.dataset.title.localeCompare(b.dataset.title);
      if (state.sort === 'architect-asc') return a.dataset.architect.localeCompare(b.dataset.architect);
      return Number(b.dataset.year) - Number(a.dataset.year);
    });
  }

  function paintButtons() {
    filterButtons.forEach((button) => {
      const key = button.dataset.filter;
      button.classList.toggle('is-active', state[key] === button.dataset.value);
    });
  }

  function paintFilterSummary(count) {
    if (!activeFilters) return;
    const chips = [];
    if (state.q) chips.push('搜索：' + state.q);
    if (state.type !== 'all') chips.push('类型：' + state.type);
    if (state.region !== 'all') chips.push('地区：' + state.region);
    chips.push(count + ' 个结果');
    activeFilters.innerHTML = chips.map((item) => '<span>' + item + '</span>').join('');
  }

  function apply() {
    const q = state.q.trim().toLowerCase();
    const visible = [];
    cards.forEach((card) => {
      const matchQuery = !q || (card.dataset.text || '').includes(q);
      const matchType = state.type === 'all' || card.dataset.type === state.type;
      const matchRegion = state.region === 'all' || card.dataset.region === state.region;
      const show = matchQuery && matchType && matchRegion;
      card.hidden = !show;
      if (show) visible.push(card);
    });
    sortCards(visible).forEach((card) => grid && grid.appendChild(card));
    if (empty) empty.hidden = visible.length !== 0;
    paintButtons();
    paintFilterSummary(visible.length);
    writeParams();
  }

  readParams();
  filterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      state[button.dataset.filter] = button.dataset.value;
      apply();
    });
  });
  if (search) search.addEventListener('input', () => { state.q = search.value; apply(); });
  if (sortSelect) sortSelect.addEventListener('change', () => { state.sort = sortSelect.value; apply(); });
  if (cards.length) apply();
})();
