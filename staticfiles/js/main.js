// ── Modal helpers ──────────────────────────────────────────────────────────
function openModal(id) {
  document.getElementById(id).classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
  document.body.style.overflow = '';
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => {
      m.classList.remove('open');
      document.body.style.overflow = '';
    });
  }
});

// ── Copy public link ───────────────────────────────────────────────────────
function copyLink(url) {
  navigator.clipboard.writeText(url).then(() => {
    showToast('Link kopiert! 📋');
  });
}

function showToast(msg) {
  const toast = document.createElement('div');
  toast.className = 'message';
  toast.textContent = msg;
  toast.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;animation:slideIn .2s ease;';
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2500);
}

// ── Drag & Drop Upload ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const zone   = document.getElementById('drop-zone');
  const input  = document.getElementById('file-input');
  const preview = document.getElementById('file-preview');
  const btn    = document.getElementById('upload-btn');

  if (!zone) return;

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
    return (bytes / 1073741824).toFixed(1) + ' GB';
  }

  function renderPreview(files) {
    preview.innerHTML = '';
    if (!files.length) { btn.disabled = true; return; }
    files.forEach(f => {
      const item = document.createElement('div');
      item.className = 'preview-item';
      item.innerHTML = `<span class="preview-item-name">📄 ${f.name}</span>
                        <span class="preview-item-size mono">${formatSize(f.size)}</span>`;
      preview.appendChild(item);
    });
    btn.disabled = false;
  }

  input.addEventListener('change', () => renderPreview(Array.from(input.files)));

  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const dt = new DataTransfer();
    Array.from(e.dataTransfer.files).forEach(f => dt.items.add(f));
    input.files = dt.files;
    renderPreview(Array.from(dt.files));
  });

  // Auto-dismiss messages
  setTimeout(() => {
    document.querySelectorAll('.messages-container .message').forEach(m => {
      m.style.transition = 'opacity .4s';
      m.style.opacity = '0';
      setTimeout(() => m.remove(), 400);
    });
  }, 3500);
});
