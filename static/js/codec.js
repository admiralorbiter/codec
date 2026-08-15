// Codec — Tactical UI & Workspace Controller

document.addEventListener('DOMContentLoaded', () => {
  // Global Esc key listener
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeDrawer();
      closeAllModals();
    }
  });
});

function openDrawer() {
  const layout = document.querySelector('.cockpit-layout');
  const drawer = document.getElementById('thread-drawer');
  if (layout && drawer) {
    layout.classList.add('drawer-open');
    drawer.style.display = 'flex';
  }
}

function closeDrawer() {
  const layout = document.querySelector('.cockpit-layout');
  const drawer = document.getElementById('thread-drawer');
  if (layout && drawer) {
    layout.classList.remove('drawer-open');
    drawer.style.display = 'none';
    drawer.innerHTML = '';
  }
  document.querySelectorAll('.thread-card').forEach(card => card.classList.remove('selected'));
}

// HTMX event hooks
document.addEventListener('htmx:afterSwap', (evt) => {
  if (evt.detail.target.id === 'thread-drawer') {
    openDrawer();
  }
});

// Modal Management
function closeAllModals() {
  const modals = document.querySelectorAll('.codec-modal');
  modals.forEach(m => m.style.display = 'none');
}

function openParkModal(threadId) {
  const modal = document.getElementById('park-modal');
  if (modal) modal.style.display = 'flex';
}

function closeParkModal() {
  const modal = document.getElementById('park-modal');
  if (modal) modal.style.display = 'none';
}

function openThinkAloudModal(threadId) {
  const modal = document.getElementById('think-aloud-modal');
  if (modal) modal.style.display = 'flex';
}

function closeThinkAloudModal() {
  const modal = document.getElementById('think-aloud-modal');
  if (modal) modal.style.display = 'none';
}

function openUniversalCaptureModal() {
  const modal = document.getElementById('universal-capture-modal');
  if (modal) modal.style.display = 'flex';
}

function closeUniversalCaptureModal() {
  const modal = document.getElementById('universal-capture-modal');
  if (modal) modal.style.display = 'none';
}

function openNewThreadModal() {
  const modal = document.getElementById('new-thread-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNewThreadModal() {
  const modal = document.getElementById('new-thread-modal');
  if (modal) modal.style.display = 'none';
}

function simulateCaptureParse() {
  const preview = document.getElementById('capture-proposal');
  if (preview) {
    preview.style.display = 'flex';
  }
}

function confirmCaptureAction() {
  alert('Capture parsed & transition appended! Updating cognitive radar...');
  closeUniversalCaptureModal();
  window.location.reload();
}

function simulateVoiceMemo(form) {
  const textarea = form.querySelector('textarea');
  if (textarea) {
    textarea.value = "🎙 [Dictated Voice Memo] Finished parser handler conversion. Verified event streams under 5ms latency. Moving to storage schema.";
    textarea.focus();
  }
}
