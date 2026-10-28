(function () {
  'use strict';

  var cards = Array.from(document.querySelectorAll('.course-card'));
  var catalog = cards.map(function (card) {
    var title = card.querySelector('.cttl').textContent.trim();
    return {
      id: card.dataset.course, title: title, card: card,
      details: card.querySelector('details'), count: card.querySelector('.module-count'),
      modules: Array.from(card.querySelectorAll('.m')).map(function (row) {
        var link = row.querySelector('.module-link');
        var name = row.querySelector('.module-title');
        return { id: link.dataset.module, title: name.textContent, name: name, row: row, href: link.getAttribute('href'), keywords: row.dataset.keywords || '' };
      })
    };
  });
  var allModules = catalog.flatMap(function (course) {
    return course.modules.map(function (module) { return Object.assign({ course: course }, module); });
  });

  /* Store the module ID only. The destination always comes from the page catalog. */
  var HISTORY_KEY = 'ax:last-opened-module:v1';
  var startLink = document.getElementById('start-link');
  var clearHistory = document.getElementById('history-clear');
  function savedModule() {
    try {
      var record = JSON.parse(localStorage.getItem(HISTORY_KEY));
      return record && allModules.find(function (m) { return m.id === record.id; });
    } catch (error) { return null; }
  }
  function renderStart() {
    var recent = savedModule();
    var module = recent || allModules[0];
    document.getElementById('start-eyebrow').textContent = recent ? '최근 열어 본 모듈' : '처음이라면 여기서부터';
    document.getElementById('start-module').textContent = 'COURSE 0' + module.course.id + ' · ' + module.id;
    document.getElementById('start-title').textContent = module.title;
    document.getElementById('start-description').textContent = recent ? '이 브라우저에서 마지막으로 연 모듈입니다.' : '데이터로 무엇을 할 수 있을지, 첫 질문부터 시작해요.';
    document.getElementById('start-action').textContent = recent ? '모듈 다시 열기' : '첫 모듈 시작하기';
    startLink.setAttribute('href', module.href);
    startLink.dataset.module = module.id;
    clearHistory.hidden = !recent;
  }
  function remember(event) {
    if (event.type === 'auxclick' && event.button !== 1) return;
    var link = event.target.closest('a[data-module]');
    if (!link || !allModules.some(function (m) { return m.id === link.dataset.module; })) return;
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify({ id: link.dataset.module })); } catch (error) { /* Navigation still works if storage is unavailable. */ }
    renderStart();
  }
  document.addEventListener('click', remember);
  document.addEventListener('auxclick', remember);
  clearHistory.addEventListener('click', function () {
    try { localStorage.removeItem(HISTORY_KEY); } catch (error) { /* No storage dependency. */ }
    renderStart();
    startLink.focus();
  });
  window.addEventListener('pageshow', renderStart);
  window.addEventListener('storage', function (event) { if (!event.key || event.key === HISTORY_KEY) renderStart(); });
  renderStart();

  var search = document.getElementById('module-search');
  var filters = Array.from(document.querySelectorAll('.filter'));
  var clearSearch = document.getElementById('clear-search');
  var resetButton = document.getElementById('reset-filters');
  var selectedCourse = 'all';
  var beforeFiltering = null;
  var composing = false;
  search.maxLength = 120;

  function normalize(value) {
    return value.normalize('NFKC').toLocaleLowerCase('ko-KR').replace(/[\s·_\-‐–—]/g, '');
  }
  function highlight(module, terms) {
    var original = module.title;
    var lower = original.toLocaleLowerCase('ko-KR');
    var ranges = [];
    terms.forEach(function (term) {
      var needle = term.toLocaleLowerCase('ko-KR');
      if (!needle) return;
      var offset = lower.indexOf(needle);
      while (offset !== -1) {
        ranges.push([offset, offset + needle.length]);
        offset = lower.indexOf(needle, offset + needle.length);
      }
    });
    ranges.sort(function (a, b) { return a[0] - b[0]; });
    var merged = [];
    ranges.forEach(function (range) {
      var last = merged[merged.length - 1];
      if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]);
      else merged.push(range.slice());
    });
    module.name.replaceChildren();
    var at = 0;
    merged.forEach(function (range) {
      module.name.appendChild(document.createTextNode(original.slice(at, range[0])));
      var mark = document.createElement('mark');
      mark.textContent = original.slice(range[0], range[1]);
      module.name.appendChild(mark);
      at = range[1];
    });
    module.name.appendChild(document.createTextNode(original.slice(at)));
  }
  function updateURL() {
    var url = new URL(location.href);
    if (search.value.trim()) url.searchParams.set('q', search.value.trim());
    else url.searchParams.delete('q');
    if (selectedCourse !== 'all') url.searchParams.set('course', selectedCourse);
    else url.searchParams.delete('course');
    try { history.replaceState(null, '', url); } catch (error) { /* file:// and restricted embeds can still filter locally. */ }
  }
  function readURL() {
    var params = new URLSearchParams(location.search);
    search.value = (params.get('q') || '').slice(0, 120);
    var course = params.get('course');
    selectedCourse = catalog.some(function (c) { return c.id === course; }) ? course : 'all';
  }
  function render(writeURL) {
    var terms = search.value.trim().split(/\s+/).filter(Boolean);
    var needles = terms.map(normalize).filter(Boolean);
    var active = !!search.value.trim() || selectedCourse !== 'all';
    if (active && !beforeFiltering) beforeFiltering = catalog.map(function (c) { return c.details.open; });
    var moduleCount = 0, courseCount = 0;
    catalog.forEach(function (course, index) {
      var count = 0;
      course.modules.forEach(function (module) {
        var haystack = normalize(course.title + ' ' + module.id + ' ' + module.title + ' ' + module.keywords);
        var matches = (selectedCourse === 'all' || course.id === selectedCourse) && needles.every(function (term) { return haystack.includes(term); });
        module.row.hidden = !matches;
        if (matches) count++;
        highlight(module, terms);
      });
      course.card.hidden = count === 0;
      course.count.textContent = count === course.modules.length ? String(count) : count + ' / ' + course.modules.length;
      if (active && count) course.details.open = true;
      else if (!active && beforeFiltering) course.details.open = beforeFiltering[index];
      if (count) courseCount++;
      moduleCount += count;
    });
    if (!active) beforeFiltering = null;
    filters.forEach(function (filter) { filter.setAttribute('aria-pressed', String(filter.dataset.course === selectedCourse)); });
    document.getElementById('result-count').textContent = (active ? '' : '전체 ') + courseCount + '개 과정 · ' + moduleCount + '개 모듈';
    document.getElementById('empty-results').hidden = moduleCount !== 0;
    clearSearch.hidden = !search.value;
    resetButton.hidden = !active;
    if (writeURL) updateURL();
  }
  search.addEventListener('compositionstart', function () { composing = true; });
  search.addEventListener('compositionend', function () { composing = false; render(true); });
  search.addEventListener('input', function () { if (!composing) render(true); });
  search.addEventListener('keydown', function (event) { if (event.key === 'Enter') event.preventDefault(); });
  filters.forEach(function (filter) {
    filter.addEventListener('click', function () { selectedCourse = filter.dataset.course; render(true); });
  });
  clearSearch.addEventListener('click', function () { search.value = ''; render(true); search.focus(); });
  function reset() { search.value = ''; selectedCourse = 'all'; render(true); search.focus(); }
  resetButton.addEventListener('click', reset);
  document.getElementById('empty-reset').addEventListener('click', reset);
  document.addEventListener('keydown', function (event) {
    var editing = event.target.closest('input, textarea, select, [contenteditable="true"]');
    if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !editing && !document.getElementById('fb-panel').open) {
      event.preventDefault(); search.focus(); search.scrollIntoView({ block: 'center' });
    }
  });
  window.addEventListener('popstate', function () { readURL(); render(false); });
  readURL(); render(false);
  document.getElementById('tools').hidden = false;

  /* Preserve the existing feedback destination; requests only follow a form submission. */
  var ENDPOINT = 'https://formsubmit.co/ajax/79b92ae2a3da8777fbe7574b72cd538e';
  var btn = document.getElementById('fb-btn');
  var panel = document.getElementById('fb-panel');
  var form = panel.querySelector('form');
  var msg = form.elements.message;
  var contact = form.elements.contact;
  var count = document.getElementById('feedback-count');
  var status = document.getElementById('feedback-status');
  var send = form.querySelector('.send');
  var courseSelect = form.elements.course, moduleSelect = form.elements.module;
  function fillSelect(select, placeholder, items) {
    select.replaceChildren();
    var head = document.createElement('option'); head.value = ''; head.textContent = placeholder; select.appendChild(head);
    items.forEach(function (item) {
      var option = document.createElement('option'); option.value = item.value; option.textContent = item.text; select.appendChild(option);
    });
  }
  fillSelect(courseSelect, '선택 안 함', catalog.map(function (course) { return { value: course.title, text: '0' + course.id + ' · ' + course.title }; }));
  function syncModules() {
    var course = catalog.find(function (c) { return c.title === courseSelect.value; });
    fillSelect(moduleSelect, course ? '선택 안 함' : '과정을 먼저 선택하세요', course ? course.modules.map(function (m) { return { value: m.id, text: m.id + ' · ' + m.title }; }) : []);
    moduleSelect.disabled = !course;
  }
  syncModules();
  courseSelect.addEventListener('change', syncModules);
  btn.hidden = false;
  btn.addEventListener('click', function () {
    panel.showModal(); btn.setAttribute('aria-expanded', 'true');
    (courseSelect.value ? msg : courseSelect).focus();
  });
  panel.querySelectorAll('.cancel, .fb-close').forEach(function (close) { close.addEventListener('click', function () { panel.close(); }); });
  panel.addEventListener('close', function () { btn.setAttribute('aria-expanded', 'false'); btn.focus({ preventScroll: true }); });
  panel.addEventListener('click', function (event) {
    var bounds = panel.getBoundingClientRect();
    if (event.target === panel && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) panel.close();
  });
  msg.addEventListener('input', function () { count.textContent = msg.value.length + ' / 1000'; msg.removeAttribute('aria-invalid'); });
  contact.addEventListener('input', function () { contact.removeAttribute('aria-invalid'); });
  function say(kind, text) { status.className = 'st' + (kind ? ' ' + kind : ''); status.textContent = text; }
  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    if (send.disabled || form.elements._honey.value) return;
    var text = msg.value.trim();
    if (text.length < 2) { say('err', '의견을 2자 이상 입력해 주세요.'); msg.setAttribute('aria-invalid', 'true'); msg.focus(); return; }
    if (contact.value && !contact.validity.valid) { say('err', '이메일 주소를 확인해 주세요.'); contact.setAttribute('aria-invalid', 'true'); contact.focus(); return; }
    var course = courseSelect.value, module = moduleSelect.value;
    var payload = {
      message: text, course: course || '선택 안 함', module: module || '선택 안 함',
      contact: contact.value.trim() || '익명', page: location.href, ua: navigator.userAgent,
      _subject: '[인공지능 기본교육] ' + course + (module ? ' ' + module : '') + ' 의견', _template: 'table'
    };
    send.disabled = true; form.setAttribute('aria-busy', 'true'); say('', '의견을 보내는 중입니다…');
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 15000);
    try {
      var response = await fetch(ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }, body: JSON.stringify(payload), signal: controller.signal });
      var data = await response.json();
      var flag = data && (data.success !== undefined ? data.success : data.ok);
      if (!response.ok || String(flag) !== 'true') {
        if (data && /activation/i.test(data.message || '')) say('err', '수신 설정이 아직 완료되지 않아 접수를 확인할 수 없습니다. 잠시 후 다시 시도해 주세요.');
        else say('err', '접수를 확인하지 못했습니다. 입력한 내용은 남겨 두었습니다. 잠시 후 다시 시도해 주세요.');
        return;
      }
      form.reset(); syncModules(); count.textContent = '0 / 1000'; say('ok', '의견이 접수되었습니다. 감사합니다.');
    } catch (error) {
      say('err', error.name === 'AbortError' ? '응답이 늦어 접수 여부를 확인할 수 없습니다. 입력한 내용은 남겨 두었습니다.' : '전송하지 못했습니다. 입력한 내용은 남겨 두었습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
      clearTimeout(timer); send.disabled = false; form.removeAttribute('aria-busy');
    }
  });
})();
