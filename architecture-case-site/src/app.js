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

  const libraryPanel = document.querySelector('#libraryPanel');
  const menuToggle = document.querySelector('[data-library-menu-toggle]');
  const menuClose = document.querySelector('[data-library-menu-close]');
  function setLibraryPanel(open) {
    if (!libraryPanel || !menuToggle) return;
    libraryPanel.hidden = !open;
    menuToggle.classList.toggle('is-open', open);
    menuToggle.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('has-library-panel', open);
    if (open) window.setTimeout(() => search?.focus(), 0);
  }
  menuToggle?.addEventListener('click', () => setLibraryPanel(libraryPanel?.hidden));
  menuClose?.addEventListener('click', () => setLibraryPanel(false));
  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setLibraryPanel(false);
  });

  const homeHeader = document.querySelector('.home-header');
  const cover = document.querySelector('.hero--cover');
  function updateHeaderContrast() {
    if (!homeHeader || !cover) return;
    homeHeader.classList.toggle('is-on-cover', window.scrollY < cover.offsetHeight - 72);
  }
  updateHeaderContrast();
  window.addEventListener('scroll', updateHeaderContrast, { passive: true });
})();

(function () {
  const deck = document.querySelector('[data-case-deck]');
  if (!deck) return;

  const slides = Array.from(deck.querySelectorAll('[data-slide]'));
  const prev = deck.querySelector('[data-slide-prev]');
  const next = deck.querySelector('[data-slide-next]');
  const currentLabel = deck.querySelector('[data-slide-label-current]');
  const currentIndex = deck.querySelector('[data-slide-index]');
  const storageKey = 'caseDeck:' + window.location.pathname;
  let index = Number(window.localStorage.getItem(storageKey) || 0);

  function clamp(value) {
    return Math.max(0, Math.min(slides.length - 1, value));
  }

  function show(nextIndex) {
    index = clamp(nextIndex);
    slides.forEach((slide, slideIndex) => {
      slide.classList.toggle('is-active', slideIndex === index);
      slide.setAttribute('aria-hidden', slideIndex === index ? 'false' : 'true');
    });
    if (currentLabel) currentLabel.textContent = slides[index]?.dataset.slideLabel || '';
    if (currentIndex) currentIndex.textContent = String(index + 1).padStart(2, '0');
    if (prev) prev.disabled = index === 0;
    if (next) next.disabled = index === slides.length - 1;
    window.localStorage.setItem(storageKey, String(index));
  }

  if (prev) prev.addEventListener('click', () => show(index - 1));
  if (next) next.addEventListener('click', () => show(index + 1));
  window.addEventListener('keydown', (event) => {
    if (event.target instanceof HTMLElement && event.target.closest('a, button, input, select, textarea')) return;
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      show(index + 1);
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      show(index - 1);
    }
  });

  show(index);
})();

(function () {
  const storageKey = 'architectureCaseAnnotations:' + window.location.pathname;
  const state = { active: false, selected: null, notes: readNotes() };
  const ui = document.createElement('aside');
  ui.className = 'annotation-tool';
  ui.innerHTML = `
    <button class="annotation-toggle" type="button" aria-pressed="false">批注模式</button>
    <section class="annotation-panel" aria-label="页面批注" hidden>
      <div class="annotation-panel-head">
        <div><p>LOCAL REVIEW</p><h2>页面批注</h2></div>
        <button type="button" class="annotation-close" aria-label="关闭批注">×</button>
      </div>
      <p class="annotation-help">开启后点击页面中的任意内容；填写意见并保存。批注仅保存在这台设备的浏览器中。</p>
      <div class="annotation-target" aria-live="polite">尚未选择元素</div>
      <label class="annotation-field">修改意见
        <textarea class="annotation-input" rows="4" placeholder="例如：图片改成两列，减少顶部留白。" disabled></textarea>
      </label>
      <div class="annotation-actions">
        <button class="annotation-save" type="button" disabled>保存批注</button>
        <button class="annotation-export" type="button">导出 JSON</button>
      </div>
      <div class="annotation-list" aria-live="polite"></div>
      <button class="annotation-clear" type="button">清空本页批注</button>
    </section>`;
  document.body.appendChild(ui);

  const toggle = ui.querySelector('.annotation-toggle');
  const panel = ui.querySelector('.annotation-panel');
  const close = ui.querySelector('.annotation-close');
  const target = ui.querySelector('.annotation-target');
  const input = ui.querySelector('.annotation-input');
  const save = ui.querySelector('.annotation-save');
  const exportButton = ui.querySelector('.annotation-export');
  const clear = ui.querySelector('.annotation-clear');
  const list = ui.querySelector('.annotation-list');

  function readNotes() {
    try {
      const value = JSON.parse(window.localStorage.getItem(storageKey) || '[]');
      return Array.isArray(value) ? value : [];
    } catch (_) {
      return [];
    }
  }

  function persist() {
    window.localStorage.setItem(storageKey, JSON.stringify(state.notes));
  }

  function selectorFor(element) {
    if (element.id) return '#' + CSS.escape(element.id);
    const labeled = element.closest('[data-screen-label]');
    if (labeled) return '[data-screen-label="' + labeled.dataset.screenLabel.replace(/"/g, '\\"') + '"]';
    const named = element.closest('main, header, footer, section, article, figure, .project-card');
    if (!named) return element.tagName.toLowerCase();
    const siblings = Array.from(named.parentElement ? named.parentElement.children : []).filter((node) => node.tagName === named.tagName);
    const position = siblings.indexOf(named) + 1;
    const className = Array.from(named.classList).find((name) => /^(hero|section|case|slide|project|deck|detail)/.test(name));
    return named.tagName.toLowerCase() + (className ? '.' + className : '') + ':nth-of-type(' + position + ')';
  }

  function labelFor(element) {
    const heading = element.querySelector?.('h1, h2, h3, figcaption') || element.closest('article, section, figure')?.querySelector('h1, h2, h3, figcaption');
    const text = (heading?.textContent || element.getAttribute('alt') || element.textContent || element.tagName).trim().replace(/\s+/g, ' ');
    return text.slice(0, 72) || element.tagName.toLowerCase();
  }

  function clearSelection() {
    state.selected?.classList.remove('is-annotation-selected');
    state.selected = null;
    input.value = '';
    input.disabled = true;
    save.disabled = true;
    target.textContent = '尚未选择元素';
  }

  function selectElement(element) {
    clearSelection();
    state.selected = element;
    element.classList.add('is-annotation-selected');
    target.innerHTML = '<strong>已选择</strong><span>' + escapeHtml(labelFor(element)) + '</span><code>' + escapeHtml(selectorFor(element)) + '</code>';
    input.disabled = false;
    save.disabled = false;
    input.focus();
  }

  function escapeHtml(value) {
    const node = document.createElement('span');
    node.textContent = value;
    return node.innerHTML;
  }

  function renderNotes() {
    list.innerHTML = state.notes.length
      ? state.notes.map((note, index) => `<article class="annotation-note"><div><b>${String(index + 1).padStart(2, '0')}</b><span>${escapeHtml(note.target)}</span></div><p>${escapeHtml(note.comment)}</p><code>${escapeHtml(note.selector)}</code></article>`).join('')
      : '<p class="annotation-empty">本页还没有批注。</p>';
  }

  function setActive(active) {
    state.active = active;
    document.body.classList.toggle('is-annotation-mode', active);
    toggle.classList.toggle('is-active', active);
    toggle.setAttribute('aria-pressed', String(active));
    toggle.textContent = active ? '退出批注' : '批注模式';
    panel.hidden = false;
    if (!active) clearSelection();
  }

  toggle.addEventListener('click', () => setActive(!state.active));
  close.addEventListener('click', () => { setActive(false); panel.hidden = true; });
  save.addEventListener('click', () => {
    const comment = input.value.trim();
    if (!state.selected || !comment) return;
    state.notes.push({
      page: window.location.pathname,
      selector: selectorFor(state.selected),
      target: labelFor(state.selected),
      comment,
      created_at: new Date().toISOString()
    });
    persist();
    renderNotes();
    clearSelection();
  });
  clear.addEventListener('click', () => {
    if (!state.notes.length || !window.confirm('确定清空当前页面的全部批注吗？')) return;
    state.notes = [];
    persist();
    renderNotes();
  });
  exportButton.addEventListener('click', () => {
    const payload = { exported_at: new Date().toISOString(), page: window.location.href, annotations: state.notes };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'architecture-case-annotations.json';
    link.click();
    URL.revokeObjectURL(link.href);
  });
  document.addEventListener('click', (event) => {
    if (!state.active || ui.contains(event.target)) return;
    const element = event.target instanceof Element ? event.target.closest('main, header, footer, section, article, figure, img, p, h1, h2, h3, li, table') : null;
    if (!element) return;
    event.preventDefault();
    event.stopPropagation();
    selectElement(element);
  }, true);
  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && state.active) clearSelection();
  });
  renderNotes();
})();
