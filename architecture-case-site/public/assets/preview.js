(function () {
  const root = document.querySelector('#casePreview');
  if (!root) return;
  document.querySelector('.library-backdrop')?.remove();

  const jobId = new URLSearchParams(window.location.search).get('job_id');
  const apiBase = (window.ARCHITECT_API_BASE || (window.location.port === '8765' ? 'http://127.0.0.1:8000' : window.location.origin)).replace(/\/$/, '');

  function previewAssetUrl(path) {
    if (!String(path).startsWith('images/')) return path;
    return `${apiBase}/api/jobs/${encodeURIComponent(jobId)}/assets/${path.split('/').map(encodeURIComponent).join('/')}`;
  }

  function api(path, options = {}) {
    return fetch(`${apiBase}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    }).then(async (response) => {
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload?.error?.message || '无法读取案例预览。');
      return payload;
    });
  }

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function appendInline(node, value) {
    const pattern = /(!?\[([^\]]+)\]\(([^\s)]+)(?:\s+"[^"]*")?\)|\*\*([^*]+)\*\*)/g;
    let cursor = 0;
    for (const match of String(value).matchAll(pattern)) {
      if (match.index > cursor) node.append(document.createTextNode(value.slice(cursor, match.index)));
      if (match[4]) {
        node.append(element('strong', match[4]));
      } else if (match[1].startsWith('!')) {
        const figure = document.createElement('figure');
        const image = document.createElement('img');
        image.src = previewAssetUrl(match[3]);
        image.alt = match[2];
        figure.append(image, element('figcaption', match[2]));
        node.append(figure);
      } else {
        const link = element('a', match[2]);
        link.href = match[3];
        link.target = '_blank';
        link.rel = 'noreferrer';
        node.append(link);
      }
      cursor = match.index + match[0].length;
    }
    if (cursor < value.length) node.append(document.createTextNode(value.slice(cursor)));
  }

  function renderMarkdown(markdown) {
    const fragment = document.createDocumentFragment();
    const lines = String(markdown || '').split(/\r?\n/);
    let index = 0;
    while (index < lines.length) {
      const line = lines[index].trim();
      if (!line) { index += 1; continue; }
      const heading = line.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        fragment.append(element(`h${heading[1].length + 1}`, heading[2]));
        index += 1;
        continue;
      }
      if (/^-\s+/.test(line)) {
        const list = document.createElement('ul');
        while (index < lines.length && /^-\s+/.test(lines[index].trim())) {
          const item = element('li');
          appendInline(item, lines[index].trim().replace(/^-\s+/, ''));
          list.append(item);
          index += 1;
        }
        fragment.append(list);
        continue;
      }
      if (/^\|.+\|$/.test(line)) {
        const table = document.createElement('table');
        const body = document.createElement('tbody');
        let rowIndex = 0;
        while (index < lines.length && /^\|.+\|$/.test(lines[index].trim())) {
          const cells = lines[index].trim().slice(1, -1).split('|').map((cell) => cell.trim());
          if (cells.every((cell) => /^:?-{3,}:?$/.test(cell))) { index += 1; continue; }
          const row = document.createElement('tr');
          cells.forEach((cell) => {
            const cellNode = document.createElement(rowIndex === 0 ? 'th' : 'td');
            appendInline(cellNode, cell);
            row.append(cellNode);
          });
          body.append(row);
          rowIndex += 1;
          index += 1;
        }
        table.append(body);
        fragment.append(table);
        continue;
      }
      const paragraph = [];
      while (index < lines.length && lines[index].trim() && !/^(#{1,3})\s+|^-\s+/.test(lines[index].trim())) {
        paragraph.push(lines[index].trim());
        index += 1;
      }
      const node = element('p');
      appendInline(node, paragraph.join(' '));
      fragment.append(node);
    }
    return fragment;
  }

  function render(result) {
    const caseJson = result.case_json || {};
    document.title = `${caseJson.project_name || '案例'} · ARCHITECT`;
    root.replaceChildren();
    document.body.classList.add('case-reader-page');
    root.className = 'case-deck case-reader preview-reader';
    const stage = document.createElement('section');
    stage.className = 'deck-stage';
    const hero = document.createElement('article');
    hero.className = 'deck-slide case-section case-reader-cover preview-hero';
    hero.append(element('p', 'PRIVATE CASE PREVIEW', 'eyebrow'));
    hero.append(element('h1', caseJson.project_name || '未命名案例'));
    hero.append(element('p', '这是一份尚未保存到案例库的完整研究预览。是否保存，由你决定。', 'preview-lead'));
    const facts = document.createElement('dl');
    facts.className = 'preview-facts';
    [['建筑师', (caseJson.architects || []).join(' / ')], ['地点', caseJson.location], ['年份', caseJson.year], ['类型', caseJson.case_type || caseJson.program]].forEach(([label, value]) => {
      if (!value) return;
      facts.append(element('dt', label), element('dd', value));
    });
    hero.append(facts);
    const heroGrid = document.createElement('div');
    heroGrid.className = 'slide-grid';
    const heroCopy = document.createElement('div');
    heroCopy.className = 'slide-copy';
    while (hero.firstChild) heroCopy.append(hero.firstChild);
    heroGrid.append(heroCopy);
    hero.append(heroGrid);
    stage.append(hero);

    const article = document.createElement('article');
    article.className = 'deck-slide case-section preview-document';
    const articleGrid = document.createElement('div');
    articleGrid.className = 'slide-grid';
    const articleCopy = document.createElement('div');
    articleCopy.className = 'slide-copy';
    articleCopy.append(renderMarkdown(result.case_md));
    articleGrid.append(articleCopy);
    article.append(articleGrid);
    stage.append(article);
    root.append(stage);

    const actions = document.createElement('section');
    actions.className = 'preview-save';
    actions.append(element('p', '生成内容已通过现有校验。保存后将写入正式案例库并更新列表。'));
    const save = element('button', '保存到案例库');
    save.type = 'button';
    save.addEventListener('click', async () => {
      save.disabled = true;
      save.textContent = '正在保存并更新案例库…';
      try {
        const response = await api(`/api/jobs/${jobId}/save`, { method: 'POST', body: '{}' });
        actions.replaceChildren(element('p', `已保存为 ${response.saved.package_slug}，案例库已更新。`, 'preview-saved'));
        const libraryLink = element('a', '返回案例库查看');
        libraryLink.href = 'index.html';
        actions.append(libraryLink);
      } catch (error) {
        save.disabled = false;
        save.textContent = '保存到案例库';
        actions.append(element('p', error.message || '保存失败，请重试。', 'preview-error'));
      }
    });
    actions.append(save);
    root.append(actions);
  }

  if (!jobId) {
    root.replaceChildren(element('p', '缺少 Job ID，无法打开预览。', 'preview-error'));
    return;
  }
  api(`/api/jobs/${jobId}/result`).then(render).catch((error) => {
    root.replaceChildren(element('p', error.message || '案例预览暂不可用。', 'preview-error'));
  });
})();
