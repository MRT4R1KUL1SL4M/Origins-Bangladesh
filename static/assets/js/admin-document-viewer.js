(() => {
  const cfg = window.__DOC_VIEWER__ || {};
  const listEl = document.getElementById('doc-list');
  const titleEl = document.getElementById('viewer-title');
  const activeTitleEl = document.getElementById('doc-active-title');
  const activeMetaEl = document.getElementById('doc-active-meta');
  const stageEl = document.getElementById('doc-stage');
  const searchEl = document.getElementById('doc-search');
  const controlsEl = document.getElementById('image-controls');
  let docs = [];
  let activeId = null;
  let zoom = 1;

  async function fetchPayload() {
    const res = await fetch(`/api/admin/documents/${cfg.kind}/${cfg.recordId}`, { credentials: 'same-origin' });
    const raw = await res.text();
    let data = {};
    try { data = raw ? JSON.parse(raw) : {}; } catch (_) {}
    if (!res.ok || data.ok === false) throw new Error(data.error || data.message || raw || 'viewer_load_failed');
    return data;
  }

  function renderList(items) {
    const q = (searchEl.value || '').trim().toLowerCase();
    const filtered = items.filter(d => !q || `${d.label} ${d.meta}`.toLowerCase().includes(q));
    listEl.innerHTML = filtered.length ? filtered.map(doc => `
      <button data-id="${doc.id}" class="doc-item w-full text-left p-4 rounded-2xl border transition-all ${doc.id === activeId ? 'bg-white border-[#C27803]/40 shadow-sm' : 'bg-[#FAF8F5] border-[#E8E3DB] hover:bg-white'}">
        <div class="flex items-start gap-3">
          <div class="mt-0.5 w-10 h-10 rounded-2xl flex items-center justify-center ${doc.kind === 'image' ? 'bg-amber-50 text-[#C27803]' : doc.kind === 'pdf' ? 'bg-red-50 text-red-600' : 'bg-slate-50 text-slate-600'}">
            <span class="text-[11px] font-bold uppercase">${doc.kind}</span>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-semibold text-[#1A1614] truncate">${doc.label}</div>
            <div class="text-[11px] text-[#A39A8E] mt-1 line-clamp-2">${doc.meta || 'No extra metadata'}</div>
          </div>
        </div>
      </button>`).join('') : `<div class="p-6 text-[13px] text-[#A39A8E]">No matching documents.</div>`;

    listEl.querySelectorAll('.doc-item').forEach(btn => {
      btn.addEventListener('click', () => setActive(Number(btn.dataset.id)));
    });
  }

  function renderStage(doc) {
    if (!doc) {
      stageEl.innerHTML = `<div class="h-full flex items-center justify-center text-[#A39A8E]">Select a document to preview.</div>`;
      controlsEl.classList.add('hidden');
      controlsEl.classList.remove('flex');
      return;
    }
    activeTitleEl.textContent = doc.label || 'Document';
    activeMetaEl.textContent = doc.meta || '';

    if (doc.kind === 'image' && doc.url && doc.url !== '#') {
      controlsEl.classList.remove('hidden');
      controlsEl.classList.add('flex');
      stageEl.innerHTML = `<div class="min-h-full flex items-center justify-center"><img id="stage-image" src="${doc.url}" alt="${doc.label}" style="transform: scale(${zoom}); transform-origin: center center; max-width:100%; height:auto; transition:transform .15s ease;" class="rounded-3xl border border-[#E8E3DB] bg-white shadow-sm"></div>`;
      return;
    }

    controlsEl.classList.add('hidden');
    controlsEl.classList.remove('flex');
    zoom = 1;

    if ((doc.kind === 'pdf' || doc.kind === 'file') && doc.url && doc.url !== '#') {
      const buttonLabel = doc.kind === 'pdf' ? 'Open PDF' : 'Open Document';
      stageEl.innerHTML = `<div class="min-h-[65vh] flex items-center justify-center">
        <div class="max-w-2xl w-full bg-white border border-[#E8E3DB] rounded-[28px] p-8 shadow-sm">
          <div class="text-[11px] uppercase tracking-[0.18em] text-[#A39A8E] font-semibold mb-3">${doc.kind === 'pdf' ? 'PDF Document' : 'Attached Document'}</div>
          <h3 class="font-serif text-3xl text-[#1A1614]">${doc.label || 'Document'}</h3>
          <p class="text-[13px] text-[#6B635A] mt-3">Open the original file in a new tab. This avoids broken inline previews and keeps the admin viewer clean.</p>
          ${doc.meta ? `<div class="mt-4 text-[12px] text-[#8B7F72]">${doc.meta}</div>` : ''}
          <div class="mt-6 flex flex-wrap gap-3">
            <a href="${doc.url}" target="_blank" rel="noopener noreferrer" class="px-5 py-3 rounded-full bg-[#1A1614] text-white text-[13px] font-medium hover:bg-[#C27803] transition-colors">${buttonLabel}</a>
          </div>
        </div>
      </div>`;
      return;
    }

    if (doc.kind === 'text') {
      const content = (doc.text_content || 'No text preview available.').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
      stageEl.innerHTML = `<pre class="whitespace-pre-wrap break-words text-[13px] leading-6 bg-white border border-[#E8E3DB] rounded-3xl p-6 min-h-[65vh]">${content}</pre>`;
      return;
    }

    if (doc.url && doc.url !== '#') {
      stageEl.innerHTML = `<div class="h-full flex items-center justify-center"><a href="${doc.url}" target="_blank" class="px-6 py-3 rounded-full bg-[#1A1614] text-white text-[13px] font-medium hover:bg-[#C27803] transition-colors">Open Document</a></div>`;
      return;
    }

    stageEl.innerHTML = `<div class="h-full flex items-center justify-center text-[#A39A8E]">Preview unavailable for this document.</div>`;
  }

  function setActive(id) {
    activeId = id;
    renderList(docs);
    renderStage(docs.find(d => Number(d.id) === Number(id)));
  }

  document.querySelectorAll('[data-zoom]').forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.zoom;
      if (action === 'in') zoom = Math.min(3, zoom + 0.2);
      if (action === 'out') zoom = Math.max(0.4, zoom - 0.2);
      if (action === 'reset') zoom = 1;
      renderStage(docs.find(d => Number(d.id) === Number(activeId)));
    });
  });

  searchEl.addEventListener('input', () => renderList(docs));

  fetchPayload().then(data => {
    titleEl.textContent = data.title || 'Document Viewer';
    docs = data.documents || [];
    renderList(docs);
    if (docs.length) setActive(docs[0].id);
    else renderStage(null);
  }).catch(err => {
    titleEl.textContent = 'Document Viewer';
    stageEl.innerHTML = `<div class="h-full flex items-center justify-center text-red-600">${err.message || 'Failed to load documents.'}</div>`;
  });
})();
