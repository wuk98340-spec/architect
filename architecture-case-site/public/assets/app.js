(function () {
  const search = document.querySelector('#caseSearch');
  const headerSearchForm = document.querySelector('#headerSearchForm');
  const researchStatus = document.querySelector('#researchStatus');
  const cards = Array.from(document.querySelectorAll('.case-card'));
  const sortSelect = document.querySelector('#sortSelect');
  const empty = document.querySelector('#emptyState');
  const activeFilters = document.querySelector('#activeFilters');
  const resultCount = document.querySelector('#resultCount');
  const filterButtons = Array.from(document.querySelectorAll('[data-filter]'));
  const grid = document.querySelector('#caseGrid');
  const state = { type: 'all', region: 'all', status: 'all', q: '', sort: 'year-desc' };
  const validSorts = new Set(['year-desc', 'year-asc', 'title-asc', 'architect-asc']);
  const validTypes = new Set(filterButtons.filter((button) => button.dataset.filter === 'type').map((button) => button.dataset.value));
  const validRegions = new Set(filterButtons.filter((button) => button.dataset.filter === 'region').map((button) => button.dataset.value));
  const validStatuses = new Set(filterButtons.filter((button) => button.dataset.filter === 'status').map((button) => button.dataset.value));

  function readParams() {
    const params = new URLSearchParams(window.location.search);
    state.q = params.get('q') || '';
    state.type = validTypes.has(params.get('type')) ? params.get('type') : 'all';
    state.region = validRegions.has(params.get('region')) ? params.get('region') : 'all';
    state.status = validStatuses.has(params.get('status')) ? params.get('status') : 'all';
    state.sort = validSorts.has(params.get('sort')) ? params.get('sort') : 'year-desc';
    if (search) search.value = state.q;
    if (sortSelect) sortSelect.value = state.sort;
  }

  function writeParams() {
    const params = new URLSearchParams();
    if (state.q) params.set('q', state.q);
    if (state.type !== 'all') params.set('type', state.type);
    if (state.region !== 'all') params.set('region', state.region);
    if (state.status !== 'all') params.set('status', state.status);
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

  function paintFilterSummary() {
    if (!activeFilters) return;
    const chips = [];
    if (state.q) chips.push('搜索：' + state.q);
    if (state.type !== 'all') chips.push('类型：' + state.type);
    if (state.region !== 'all') chips.push('地区：' + state.region);
    if (state.status !== 'all') chips.push('状态：' + state.status);
    activeFilters.innerHTML = chips.map((item) => '<span>' + item + '</span>').join('')
      + (chips.length ? '<button type="button" class="clear-filters" data-clear-filters>清除筛选</button>' : '');
  }

  function apply() {
    const q = state.q.trim().toLowerCase();
    const visible = [];
    cards.forEach((card) => {
      const matchQuery = !q || (card.dataset.text || '').includes(q);
      const matchType = state.type === 'all' || card.dataset.type === state.type;
      const matchRegion = state.region === 'all' || card.dataset.region === state.region;
      const matchStatus = state.status === 'all' || card.dataset.status === state.status;
      const show = matchQuery && matchType && matchRegion && matchStatus;
      card.hidden = !show;
      if (show) visible.push(card);
    });
    sortCards(visible).forEach((card) => grid && grid.appendChild(card));
    if (empty) empty.hidden = visible.length !== 0;
    if (resultCount) resultCount.textContent = '显示 ' + visible.length + ' 个案例';
    paintButtons();
    paintFilterSummary();
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
  const apiBase = (window.ARCHITECT_API_BASE || (window.location.port === '8765' ? 'http://127.0.0.1:8000' : window.location.origin)).replace(/\/$/, '');

  function setResearchStatus(message, tone = 'neutral') {
    if (!researchStatus) return;
    researchStatus.hidden = !message;
    researchStatus.className = `research-status is-${tone}`;
    researchStatus.replaceChildren();
    if (typeof message === 'string') researchStatus.textContent = message;
    else researchStatus.append(message);
  }

  function requestApi(path, options = {}) {
    return fetch(`${apiBase}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    }).then(async (response) => {
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload?.error?.message || '本地研究服务暂时不可用。');
      return payload;
    });
  }

  function showCandidates(job) {
    const panel = document.createElement('div');
    const heading = document.createElement('p');
    heading.textContent = '未在当前案例库中找到匹配项。请选择要继续研究的项目：';
    panel.append(heading);
    const candidates = document.createElement('div');
    candidates.className = 'research-candidates';
    (job.disambiguation?.candidates || []).forEach((candidate) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'research-candidate';
      button.textContent = `${candidate.project_name} · ${candidate.location} · ${candidate.year}`;
      button.addEventListener('click', async () => {
        candidates.querySelectorAll('button').forEach((item) => { item.disabled = true; });
        setResearchStatus('正在研究、生成案例并校验来源，请稍候。', 'working');
        try {
          const confirmed = await requestApi(`/api/jobs/${job.job_id}/confirm`, {
            method: 'POST', body: JSON.stringify({ candidate_id: candidate.candidate_id }),
          });
          const result = await requestApi(`/api/jobs/${job.job_id}/result`);
          if (confirmed.status === 'awaiting_review' && result.case_json) {
            window.location.assign(`preview.html?job_id=${encodeURIComponent(job.job_id)}`);
            return;
          }
          setResearchStatus('案例已生成，可在稍后打开预览。', 'neutral');
        } catch (error) {
          // Recover when the HTTP response loses a race with a completed worker.
          try {
            const recovered = await requestApi(`/api/jobs/${job.job_id}/result`);
            if (recovered.validation?.passed_for_review && recovered.case_json) {
              window.location.assign(`preview.html?job_id=${encodeURIComponent(job.job_id)}`);
              return;
            }
          } catch (_) {
            // There is no completed result to recover.
          }
          setResearchStatus(error.message || '研究任务未完成，请稍后在 Job 状态中查看。', 'error');
        }
      });
      candidates.append(button);
    });
    panel.append(candidates);
    setResearchStatus(panel, 'neutral');
  }

  headerSearchForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const query = search?.value.trim() || '';
    if (!query) {
      setResearchStatus('请输入项目、建筑师、地点或年份。', 'error');
      search?.focus();
      return;
    }
    state.q = query;
    apply();
    const matchingCards = cards.filter((card) => !card.hidden);
    if (matchingCards.length) {
      setResearchStatus(`已在案例库中找到 ${matchingCards.length} 个匹配案例。`, 'success');
      const library = document.querySelector('#cases');
      if (library) window.scrollTo({ top: library.getBoundingClientRect().top + window.scrollY - 88, behavior: 'smooth' });
      return;
    }
    setResearchStatus('案例库中暂无匹配项，正在进行项目消歧。', 'working');
    try {
      const job = await requestApi('/api/jobs', { method: 'POST', body: JSON.stringify({ query }) });
      showCandidates(job);
    } catch (error) {
      setResearchStatus(error.message || '无法创建研究任务。请确认本地后端已启动。', 'error');
    }
  });
  if (sortSelect) sortSelect.addEventListener('change', () => { state.sort = sortSelect.value; apply(); });
  activeFilters?.addEventListener('click', (event) => {
    if (!event.target.closest('[data-clear-filters]')) return;
    state.type = 'all';
    state.region = 'all';
    state.status = 'all';
    state.q = '';
    state.sort = 'year-desc';
    if (search) search.value = '';
    if (sortSelect) sortSelect.value = state.sort;
    apply();
  });
  if (cards.length) apply();

  const libraryPanel = document.querySelector('#libraryPanel');
  const menuToggle = document.querySelector('[data-library-menu-toggle]');
  const menuClose = document.querySelector('[data-library-menu-close]');
  const libraryBackdrop = document.createElement('button');
  libraryBackdrop.type = 'button';
  libraryBackdrop.className = 'library-backdrop';
  libraryBackdrop.setAttribute('aria-label', '关闭搜索与筛选');
  libraryBackdrop.hidden = true;
  if (libraryPanel) document.body.appendChild(libraryBackdrop);
  const compactLibrary = window.matchMedia('(max-width: 800px)');
  function setLibraryPanel(open) {
    if (!libraryPanel || !menuToggle) return;
    if (!compactLibrary.matches) {
      libraryPanel.hidden = false;
      libraryBackdrop.hidden = true;
      menuToggle.classList.remove('is-open');
      menuToggle.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('has-library-panel');
      return;
    }
    libraryPanel.hidden = !open;
    libraryBackdrop.hidden = !open;
    menuToggle.classList.toggle('is-open', open);
    menuToggle.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('has-library-panel', open);
    if (open) window.setTimeout(() => search?.focus(), 0);
  }
  setLibraryPanel(false);
  compactLibrary.addEventListener?.('change', () => setLibraryPanel(false));
  menuToggle?.addEventListener('click', () => setLibraryPanel(libraryPanel?.hidden));
  menuClose?.addEventListener('click', () => setLibraryPanel(false));
  libraryBackdrop.addEventListener('click', () => setLibraryPanel(false));
  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setLibraryPanel(false);
  });

  const homeHeader = document.querySelector('.home-header');
  const cover = document.querySelector('.hero--cover');
  const darkSections = Array.from(document.querySelectorAll('#featured, #timeline'));
  function updateHeaderContrast() {
    if (!homeHeader || !cover) return;
    const headerHeight = homeHeader.offsetHeight || 72;
    const coverIsUnderHeader = window.scrollY < cover.offsetHeight - headerHeight;
    const darkSectionIsUnderHeader = darkSections.some((section) => {
      const rect = section.getBoundingClientRect();
      return rect.top < headerHeight && rect.bottom > 0;
    });
    homeHeader.classList.toggle('is-on-cover', coverIsUnderHeader);
    homeHeader.classList.toggle('is-on-dark', darkSectionIsUnderHeader);
  }
  updateHeaderContrast();
  window.addEventListener('scroll', updateHeaderContrast, { passive: true });
})();

(function () {
  const deck = document.querySelector('[data-case-deck]');
  if (!deck) return;

  const slides = Array.from(deck.querySelectorAll('[data-slide]'));
  const stage = deck.querySelector('.deck-stage');
  const controls = deck.querySelector('.deck-controls');
  if (!stage || !slides.length) return;

  const containsBrokenText = (value) => /[?？]{3,}/.test(value || '');

  document.body.classList.add('case-reader-page');
  deck.classList.add('case-reader');
  if (controls) controls.hidden = true;

  const tocItems = [];
  slides.forEach((slide, index) => {
    const label = index === 0 ? '项目概览' : (slide.dataset.slideLabel || `章节 ${index + 1}`);
    const id = `case-section-${index + 1}`;
    const heading = slide.querySelector('h1');
    const media = slide.querySelector('.slide-media');
    slide.id = id;
    slide.classList.remove('is-active');
    slide.classList.add('case-section');
    slide.setAttribute('aria-hidden', 'false');
    slide.setAttribute('tabindex', '-1');
    if (heading) heading.id = `${id}-title`;
    if (media) slide.classList.add('case-section--with-media');
    if (index === 0) slide.classList.add('case-reader-cover');
    const isDrawingFile = (image) => {
      const source = image?.currentSrc || image?.src || '';
      const fileName = source.split('?')[0].split('/').pop() || '';
      return /(?:plan|section|elevation|drawing|diagram|analysis)/i.test(fileName);
    };
    const image = media?.querySelector('img');
    if (isDrawingFile(image)) {
      media.classList.add('is-drawing');
    }
    slide.querySelectorAll('.slide-media').forEach((figure) => {
      const figureImage = figure.querySelector('img');
      if (isDrawingFile(figureImage)) {
        figure.classList.add('is-drawing');
      }
    });
    tocItems.push(`<li><a href="#${id}"><span>${String(index + 1).padStart(2, '0')}</span>${label}</a></li>`);
  });

  const toc = document.createElement('aside');
  toc.className = 'case-reader-toc';
  toc.setAttribute('aria-label', '案例章节目录');
  toc.innerHTML = `<p>CASE RECORD</p><h2>阅读目录</h2><nav><ol>${tocItems.join('')}</ol></nav>`;
  deck.insertBefore(toc, stage);

  const tocLinks = Array.from(toc.querySelectorAll('a'));
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        tocLinks.forEach((link) => link.classList.toggle('is-current', link.getAttribute('href') === `#${entry.target.id}`));
      });
    }, { rootMargin: '-18% 0px -68% 0px', threshold: 0.01 });
    slides.forEach((slide) => observer.observe(slide));
  }

  function setMediaState(figure, state, message) {
    figure.classList.remove('is-loading', 'is-media-missing');
    if (state) figure.classList.add(state);
    figure.setAttribute('aria-busy', state === 'is-loading' ? 'true' : 'false');
    let status = figure.querySelector('.media-status');
    if (!message) {
      status?.remove();
      return;
    }
    if (!status) {
      status = document.createElement('span');
      status.className = 'media-status';
      figure.appendChild(status);
    }
    status.textContent = message;
  }

  slides.forEach((slide) => {
    const lead = slide.querySelector('.slide-lead');
    if (lead && containsBrokenText(lead.textContent)) lead.hidden = true;
    const tags = slide.querySelector('.detail-tags');
    if (tags) {
      Array.from(tags.children).forEach((tag) => {
        if (containsBrokenText(tag.textContent)) tag.hidden = true;
      });
      if (!Array.from(tags.children).some((tag) => !tag.hidden)) tags.hidden = true;
    }
    slide.querySelectorAll('.compact-source-list li').forEach((item) => {
      if (containsBrokenText(item.textContent)) item.hidden = true;
    });
    const figure = slide.querySelector('.slide-media');
    const image = figure?.querySelector('img');
    if (!figure) return;
    if (!image) {
      figure.classList.add('is-media-missing');
      figure.setAttribute('aria-label', '图片资料待补充');
      return;
    }
    setMediaState(figure, 'is-loading', '图片加载中');
    const loaded = () => setMediaState(figure, '', '');
    const failed = () => {
      image.hidden = true;
      setMediaState(figure, 'is-media-missing', '图片暂时无法显示');
    };
    image.addEventListener('load', loaded, { once: true });
    image.addEventListener('error', failed, { once: true });
    if (image.complete) {
      if (image.naturalWidth > 0) loaded();
      else failed();
    }
    Array.from(slide.querySelectorAll('.slide-media')).slice(1).forEach((extraFigure) => {
      const extraImage = extraFigure.querySelector('img');
      if (!extraImage) return;
      setMediaState(extraFigure, 'is-loading', '正在加载图片');
      const extraLoaded = () => setMediaState(extraFigure, '', '');
      const extraFailed = () => {
        extraImage.hidden = true;
        setMediaState(extraFigure, 'is-media-missing', '图片暂时无法显示');
      };
      extraImage.addEventListener('load', extraLoaded, { once: true });
      extraImage.addEventListener('error', extraFailed, { once: true });
      if (extraImage.complete) {
        if (extraImage.naturalWidth > 0) extraLoaded();
        else extraFailed();
      }
    });
  });
})();

(function () {
  const media = Array.from(document.querySelectorAll('[data-media-state]'));
  media.forEach((figure) => {
    const image = figure.querySelector('img');
    const status = figure.querySelector('.media-status');
    const setState = (state, message) => {
      figure.classList.remove('is-ready', 'is-loading', 'is-media-missing');
      figure.classList.add(state);
      if (status && message) status.textContent = message;
      figure.setAttribute('aria-busy', state === 'is-loading' ? 'true' : 'false');
    };
    if (!image) {
      setState('is-media-missing', '图片资料待补充');
      return;
    }
    setState('is-loading', '图片加载中');
    const loaded = () => setState('is-ready', '');
    const failed = () => {
      image.hidden = true;
      setState('is-media-missing', '图片暂时无法显示');
    };
    image.addEventListener('load', loaded, { once: true });
    image.addEventListener('error', failed, { once: true });
    if (image.complete) {
      if (image.naturalWidth > 0) loaded();
      else failed();
    }
  });
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
