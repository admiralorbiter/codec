// Codec — Tactical UI & Workspace Controller

let speechRecognition = null;
let isRecording = false;
let currentProposal = null;

document.addEventListener('DOMContentLoaded', () => {
  // Global Esc key listener
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeDrawer();
      closeAllModals();
    }
  });

  initSpeechRecognition();
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
  stopSpeechRecognition();
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
  if (modal) {
    modal.style.display = 'flex';
    const textarea = document.getElementById('capture-transcript-box');
    if (textarea) textarea.focus();
  }
}

function closeUniversalCaptureModal() {
  const modal = document.getElementById('universal-capture-modal');
  if (modal) modal.style.display = 'none';
  stopSpeechRecognition();
}

function openNewThreadModal() {
  const modal = document.getElementById('new-thread-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNewThreadModal() {
  const modal = document.getElementById('new-thread-modal');
  if (modal) modal.style.display = 'none';
}

function openSurfaceModal(threadId) {
  const modal = document.getElementById('surface-modal');
  const form = document.getElementById('surface-form');
  if (modal && form) {
    form.action = `/threads/${threadId}/surfaces`;
    modal.style.display = 'flex';
  }
}

function closeSurfaceModal() {
  const modal = document.getElementById('surface-modal');
  if (modal) modal.style.display = 'none';
}

function openFrictionModal() {
  const modal = document.getElementById('friction-modal');
  if (modal) {
    modal.style.display = 'flex';
    const textarea = document.getElementById('friction-note-box');
    if (textarea) textarea.focus();
  }
}

function closeFrictionModal() {
  const modal = document.getElementById('friction-modal');
  if (modal) modal.style.display = 'none';
}

function toggleDrawerParkForm() {
  const box = document.getElementById('drawer-park-box');
  if (box) {
    box.style.display = box.style.display === 'none' ? 'block' : 'none';
  }
}

function toggleDrawerReworkForm() {
  const box = document.getElementById('drawer-rework-box');
  if (box) {
    box.style.display = box.style.display === 'none' ? 'block' : 'none';
  }
}

// -------------------------------------------------------------
// Web Speech API Voice Dictation
// -------------------------------------------------------------
function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = true;
    speechRecognition.interimResults = true;
    speechRecognition.lang = 'en-US';

    speechRecognition.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      const textarea = document.getElementById('capture-transcript-box');
      if (textarea && finalTranscript) {
        textarea.value = (textarea.value ? textarea.value + ' ' : '') + finalTranscript.trim();
        fetchCapturePreview();
      }
    };

    speechRecognition.onerror = (event) => {
      console.warn('Speech recognition error:', event.error);
      stopSpeechRecognition();
    };

    speechRecognition.onend = () => {
      isRecording = false;
      updateSpeechBtnState();
    };
  }
}

function toggleSpeechRecognition() {
  if (!speechRecognition) {
    alert('Web Speech API is not supported in this browser. You can type or use OS dictation.');
    return;
  }

  if (isRecording) {
    stopSpeechRecognition();
  } else {
    startSpeechRecognition();
  }
}

function startSpeechRecognition() {
  if (speechRecognition && !isRecording) {
    try {
      speechRecognition.start();
      isRecording = true;
      updateSpeechBtnState();
    } catch (err) {
      console.warn(err);
    }
  }
}

function stopSpeechRecognition() {
  if (speechRecognition && isRecording) {
    try {
      speechRecognition.stop();
    } catch (err) {}
    isRecording = false;
    updateSpeechBtnState();
  }
}

function updateSpeechBtnState() {
  const btnLabel = document.getElementById('speech-btn-label');
  const btn = document.getElementById('btn-toggle-speech');
  if (btnLabel && btn) {
    if (isRecording) {
      btnLabel.textContent = 'Recording... (Click to Stop)';
      btn.style.color = '#ef4444';
      btn.style.borderColor = '#ef4444';
    } else {
      btnLabel.textContent = 'Start Dictation';
      btn.style.color = '';
      btn.style.borderColor = '';
    }
  }
}

// -------------------------------------------------------------
// Universal Capture Preview & Commit
// -------------------------------------------------------------
async function fetchCapturePreview() {
  const textarea = document.getElementById('capture-transcript-box');
  if (!textarea || !textarea.value.trim()) return;

  try {
    const res = await fetch('/capture/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript: textarea.value.trim() })
    });
    if (res.ok) {
      const data = await res.json();
      currentProposal = data;
      renderCaptureProposal(data);
    }
  } catch (err) {
    console.error('Failed to preview capture:', err);
  }
}

function renderCaptureProposal(data) {
  const preview = document.getElementById('capture-proposal');
  if (!preview) return;

  document.getElementById('proposal-thread-name').textContent = data.thread_name + (data.is_new_thread ? ' (New Thread)' : '');
  document.getElementById('proposal-state').textContent = data.proposed_state || 'ACTIVE';
  document.getElementById('proposal-frontier').textContent = data.proposed_frontier || '—';
  document.getElementById('proposal-next').textContent = data.proposed_next_action || '—';
  preview.style.display = 'flex';
}

async function submitCaptureCommit() {
  const textarea = document.getElementById('capture-transcript-box');
  const transcript = textarea ? textarea.value.trim() : '';
  if (!transcript) return;

  const payload = currentProposal || { transcript: transcript };
  payload.transcript = transcript;

  try {
    const res = await fetch('/capture/commit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const data = await res.json();
      closeUniversalCaptureModal();
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      } else {
        window.location.reload();
      }
    }
  } catch (err) {
    console.error('Failed to commit capture:', err);
  }
}

// -------------------------------------------------------------
// Friction Telemetry Logger
// -------------------------------------------------------------
async function submitFrictionLog(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  formData.append('page_url', window.location.href);

  try {
    const res = await fetch('/friction', {
      method: 'POST',
      body: formData
    });
    if (res.ok) {
      closeFrictionModal();
      form.reset();
      alert('Friction observation logged. Thank you for the telemetry.');
    }
  } catch (err) {
    console.error('Failed to record friction:', err);
  }
}

function simulateVoiceMemo(form) {
  const textarea = form.querySelector('textarea');
  if (textarea) {
    textarea.value = "🎙 [Dictated Voice Memo] Finished parser handler conversion. Verified event streams under 5ms latency. Moving to storage schema.";
    textarea.focus();
  }
}

// Hot-swap thread into a specific parallel channel pane via HTMX
function fetchChannelThread(channelNum, threadId) {
  const targetId = `#channel-pane-${channelNum}`;
  const url = `/channels/${channelNum}/thread/${threadId}`;
  if (window.htmx) {
    htmx.ajax('GET', url, { target: targetId, swap: 'outerHTML' });
  } else {
    window.location.href = url;
  }
}


