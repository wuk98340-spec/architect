
(function () {
  const search = document.querySelector('#caseSearch');
  const cards = Array.from(document.querySelectorAll('.case-card'));
  const filters = Array.from(document.querySelectorAll('.filter'));
  const empty = document.querySelector('#emptyState');
  let activeType = 'all';

  function applyFilters() {
    const query = search ? search.value.trim().toLowerCase() : '';
    let visible = 0;
    cards.forEach((card) => {
      const matchType = activeType === 'all' || card.dataset.type === activeType;
      const matchText = !query || (card.dataset.text || '').includes(query);
      const show = matchType && matchText;
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
  }

  filters.forEach((button) => {
    button.addEventListener('click', () => {
      activeType = button.dataset.type || 'all';
      filters.forEach((item) => item.classList.toggle('active', item === button));
      applyFilters();
    });
  });

  if (search) search.addEventListener('input', applyFilters);
})();
