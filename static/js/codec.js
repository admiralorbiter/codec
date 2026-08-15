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
  updateAudioBtnIcon();
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

function openDecisionGateModal() {
  const modal = document.getElementById('decision-gate-modal');
  if (modal) modal.style.display = 'flex';
}

function closeDecisionGateModal() {
  const modal = document.getElementById('decision-gate-modal');
  if (modal) modal.style.display = 'none';
}

function openRelationModal() {
  const modal = document.getElementById('relation-modal');
  if (modal) modal.style.display = 'flex';
}

function closeRelationModal() {
  const modal = document.getElementById('relation-modal');
  if (modal) modal.style.display = 'none';
}

function openGitCommitModal(threadId) {
  const modal = document.getElementById('git-commit-modal');
  if (modal) {
    modal.style.display = 'flex';
    const input = document.getElementById('git-commit-message-input');
    if (input) {
      input.focus();
      input.select();
    }
  }
}

function closeGitCommitModal() {
  const modal = document.getElementById('git-commit-modal');
  if (modal) modal.style.display = 'none';
}

function openWorkPacketModal() {
  const modal = document.getElementById('work-packet-modal');
  if (modal) modal.style.display = 'flex';
}

function closeWorkPacketModal() {
  const modal = document.getElementById('work-packet-modal');
  if (modal) modal.style.display = 'none';
}

function openReworkModal(packetId) {
  const modal = document.getElementById('rework-modal');
  const form = document.getElementById('rework-form');
  if (modal && form) {
    form.action = `/work-packets/${packetId}/rework`;
    modal.style.display = 'flex';
  }
}

function closeReworkModal() {
  const modal = document.getElementById('rework-modal');
  if (modal) modal.style.display = 'none';
}

function addStopConditionPreset(text) {
  const input = document.getElementById('wp-stop-conditions-input');
  if (input) {
    if (input.value && input.value.trim().length > 0) {
      input.value += '; ' + text;
    } else {
      input.value = text;
    }
  }
}

async function autoGenerateCommitMessage(threadId) {
  try {
    const input = document.getElementById('git-commit-message-input');
    if (input) {
      input.value = "Synthesizing commit message from Activity Braid...";
    }
    const res = await fetch(`/threads/${threadId}/generate-commit-message`);
    if (res.ok) {
      const data = await res.json();
      if (data.commit_message && input) {
        input.value = data.commit_message;
        playAlertSound();
        showTacticalToast("🪄 Commit message synthesized from latest braid events!");
      }
    }
  } catch (err) {
    console.error("Failed to auto-generate commit message:", err);
  }
}

async function copyContextPacket(threadId) {
  try {
    const res = await fetch(`/threads/${threadId}/context-packet`);
    if (res.ok) {
      const data = await res.json();
      if (data.packet) {
        await navigator.clipboard.writeText(data.packet);
        playCodecRing();
        showTacticalToast(`📋 Context Packet for '${data.thread_name}' copied to clipboard! Ready to paste into ChatGPT, Claude, or Agent.`);
      }
    }
  } catch (err) {
    console.error('Failed to copy context packet:', err);
    alert('Failed to copy context packet to clipboard.');
  }
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
// Metal Gear Solid Tactical Sound Synthesizer (Web Audio API)
// -------------------------------------------------------------
let audioCtx = null;
let audioEnabled = localStorage.getItem('codec_audio_enabled') !== 'false';

function getAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

function playTone(freq, type, startTime, duration, gainVal = 0.12) {
  const ctx = getAudioContext();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, startTime);
  
  gain.gain.setValueAtTime(gainVal, startTime);
  gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);
  
  osc.connect(gain);
  gain.connect(ctx.destination);
  
  osc.start(startTime);
  osc.stop(startTime + duration);
}

// Authentic Codec Ring Chime (Beep-Beep... Beep-Beep)
function playCodecRing() {
  if (!audioEnabled) return;
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;
    
    // First pulse pair
    playTone(987.77, 'sine', now, 0.07, 0.12);        // B5
    playTone(783.99, 'sine', now + 0.08, 0.07, 0.12);  // G5
    
    // Second pulse pair
    playTone(987.77, 'sine', now + 0.22, 0.07, 0.12); // B5
    playTone(783.99, 'sine', now + 0.30, 0.07, 0.12); // G5
  } catch (e) {}
}

// Iconic Metal Gear Alert "!" sound
function playAlertSound() {
  if (!audioEnabled) return;
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(550, now);
    osc.frequency.exponentialRampToValueAtTime(1400, now + 0.12);
    
    gain.gain.setValueAtTime(0.18, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    
    osc.start(now);
    osc.stop(now + 0.22);
  } catch (e) {}
}

function toggleAudio() {
  audioEnabled = !audioEnabled;
  localStorage.setItem('codec_audio_enabled', audioEnabled);
  updateAudioBtnIcon();
  if (audioEnabled) playCodecRing();
}

function updateAudioBtnIcon() {
  const btn = document.getElementById('btn-toggle-sound');
  if (btn) {
    btn.textContent = audioEnabled ? '🔊' : '🔇';
    btn.title = audioEnabled ? 'Sound Effects Active (Click to Mute)' : 'Sound Effects Muted (Click to Enable)';
  }
}

// -------------------------------------------------------------
// Mei Ling Proverb Generator [FREQ 140.96]
// -------------------------------------------------------------
const MEI_LING_PROVERBS = [
  "“A strong man doesn't need to read the future. He makes his own.” — Solid Snake",
  "“A journey of a thousand miles begins with a single step.” — Mei Ling [FREQ 140.96]",
  "“Do not worry about being unrecognized; seek to be worthy of recognition.” — Confucius",
  "“To know what is right and not do it is the worst cowardice.” — Mei Ling [FREQ 140.96]",
  "“Be prepared for whatever the mission throws at you. Don't forget to save!” — Mei Ling",
  "“The wise adapt themselves to circumstances, as water moulds itself to the pitcher.” — Chinese Proverb"
];

function getRandomMeiLingProverb() {
  return MEI_LING_PROVERBS[Math.floor(Math.random() * MEI_LING_PROVERBS.length)];
}

function showTacticalToast(message, isMeiLing = false) {
  let toast = document.getElementById('codec-tactical-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'codec-tactical-toast';
    toast.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: rgba(6, 10, 8, 0.95);
      border: 1px solid var(--codec-green);
      color: var(--codec-green);
      font-family: var(--font-mono);
      font-size: 0.78rem;
      padding: 12px 18px;
      border-radius: 4px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.8), 0 0 15px var(--codec-green-glow);
      z-index: 9999;
      max-width: 380px;
      line-height: 1.4;
      animation: fadeIn 0.2s ease-in;
    `;
    document.body.appendChild(toast);
  }
  
  toast.textContent = '';
  const headerDiv = document.createElement('div');
  headerDiv.style.fontSize = '0.7rem';
  headerDiv.style.marginBottom = '4px';
  if (isMeiLing) {
    headerDiv.style.color = 'var(--amber-alert)';
    headerDiv.textContent = '📻 MEI LING // FREQ 140.96';
  } else {
    headerDiv.style.color = 'var(--text-dim)';
    headerDiv.textContent = '⚡ CODEC // FREQ 140.85';
  }
  toast.appendChild(headerDiv);

  const msgDiv = document.createElement('div');
  msgDiv.textContent = message;
  toast.appendChild(msgDiv);
  
  toast.style.display = 'block';
  setTimeout(() => {
    if (toast) toast.style.display = 'none';
  }, 4500);
}

// -------------------------------------------------------------
// Konami Code Easter Egg (↑ ↑ ↓ ↓ ← → ← → B A)
// -------------------------------------------------------------
const konamiPattern = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
let konamiPosition = 0;

document.addEventListener('keydown', (e) => {
  const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  const expected = konamiPattern[konamiPosition].toLowerCase();

  if (key === expected) {
    konamiPosition++;
    if (konamiPosition === konamiPattern.length) {
      konamiPosition = 0;
      activateKonamiMode();
    }
  } else {
    konamiPosition = 0;
  }

  // Press 'c' outside inputs to trigger Codec call sound
  if (key === 'c' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
    playCodecRing();
    showTacticalToast("TRANSMITTING ON FREQ 140.85... ALL CHANNELS ACTIVE");
  }
});

function activateKonamiMode() {
  document.body.classList.toggle('solid-snake-hud-boost');
  playCodecRing();
  const isActive = document.body.classList.contains('solid-snake-hud-boost');
  showTacticalToast(
    isActive ? "⚡ SOLID SNAKE TACTICAL PHOSPHOR BOOST ACTIVE // FREQ 140.85" : "TACTICAL HUD RETURNED TO STANDARD PROFILE",
    false
  );
}

// Trigger Codec sound when opening Universal Capture
const origOpenCapture = openUniversalCaptureModal;
openUniversalCaptureModal = function() {
  playCodecRing();
  origOpenCapture();
};

// Friction Telemetry with Mei Ling Proverb Toast
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
      playCodecRing();
      showTacticalToast(getRandomMeiLingProverb(), true);
    }
  } catch (err) {
    console.error('Failed to record friction:', err);
  }
}

// Hot-swap thread into a specific parallel channel pane via HTMX
function fetchChannelThread(channelNum, threadId) {
  playCodecRing();
  const targetId = `#channel-pane-${channelNum}`;
  const url = `/channels/${channelNum}/thread/${threadId}`;
  if (window.htmx) {
    htmx.ajax('GET', url, { target: targetId, swap: 'outerHTML' });
  } else {
    window.location.href = url;
  }
}

// -------------------------------------------------------------
// Horizon 3: Live Real-Time Telemetry & Surgical Event Streaming
// -------------------------------------------------------------
let globalEventSource = null;

function appendBraidEventDOM(eventData) {
  const timeline = document.querySelector('.braid-timeline');
  if (!timeline) return;

  const node = document.createElement('div');
  node.className = 'braid-node';
  node.style.animation = 'pulseGlow 1.5s ease';
  
  const icon = document.createElement('div');
  icon.className = 'braid-node-icon';
  icon.textContent = '⚡';
  
  const content = document.createElement('div');
  content.className = 'braid-node-content';
  
  const header = document.createElement('div');
  header.className = 'braid-node-header';
  
  const actorSpan = document.createElement('span');
  actorSpan.className = 'braid-actor';
  actorSpan.textContent = eventData.actor || 'SYSTEM';
  
  const typeSpan = document.createElement('span');
  typeSpan.className = 'braid-type';
  typeSpan.textContent = eventData.event_type || 'EVENT';
  
  const timeSpan = document.createElement('span');
  timeSpan.className = 'braid-time';
  timeSpan.textContent = 'just now';
  
  header.appendChild(actorSpan);
  header.appendChild(typeSpan);
  header.appendChild(timeSpan);
  
  const summaryDiv = document.createElement('div');
  summaryDiv.className = 'braid-node-summary';
  summaryDiv.textContent = eventData.summary || '';
  
  content.appendChild(header);
  content.appendChild(summaryDiv);
  node.appendChild(icon);
  node.appendChild(content);

  const frontier = timeline.querySelector('.braid-node-frontier');
  if (frontier) {
    timeline.insertBefore(node, frontier);
  } else {
    timeline.appendChild(node);
  }
}

function updateFrontierDOM(frontierData) {
  const frontierText = document.querySelector('.frontier-node-text, .card-frontier-text');
  if (frontierText && frontierData.frontier) {
    frontierText.textContent = frontierData.frontier;
    frontierText.style.transition = 'all 0.5s ease';
    frontierText.style.color = 'var(--codec-green)';
  }
  const nextMoveText = document.querySelector('.first-move-text, .card-first-move');
  if (nextMoveText && frontierData.next_action) {
    nextMoveText.textContent = frontierData.next_action;
  }
}

function updateAgentTelemetryDOM(payload) {
  const telemetryBox = document.getElementById('agent-telemetry-status');
  if (!telemetryBox) return;

  telemetryBox.textContent = '';
  const statusRow = document.createElement('div');
  statusRow.style.display = 'flex';
  statusRow.style.alignItems = 'center';
  statusRow.style.gap = '8px';
  statusRow.style.fontSize = '0.75rem';
  statusRow.style.color = 'var(--codec-green)';

  const pulse = document.createElement('span');
  pulse.className = 'running-pulse-indicator';

  const strong = document.createElement('strong');
  strong.textContent = payload.actor_name || 'Antigravity';

  const stepText = document.createElement('span');
  stepText.textContent = ` [Step ${payload.step_index}/${payload.total_steps}]: ${payload.step_name}`;

  statusRow.appendChild(pulse);
  statusRow.appendChild(strong);
  statusRow.appendChild(stepText);
  telemetryBox.appendChild(statusRow);

  if (payload.log_snippet) {
    const pre = document.createElement('pre');
    pre.style.cssText = 'font-size: 0.68rem; color: var(--text-dim); margin-top: 4px; max-height: 80px; overflow-y: auto;';
    pre.textContent = payload.log_snippet;
    telemetryBox.appendChild(pre);
  }
  telemetryBox.style.display = 'block';
}

function initLiveStream(threadId) {
  const url = threadId ? `/threads/${threadId}/stream` : '/api/stream';
  if (globalEventSource) {
    globalEventSource.close();
  }

  try {
    globalEventSource = new EventSource(url);

    globalEventSource.addEventListener('CONNECTED', () => {
      const badge = document.getElementById('live-stream-badge');
      if (badge) {
        badge.textContent = '🟢 LIVE STREAMING';
        badge.style.color = 'var(--codec-green)';
        badge.style.borderColor = 'var(--codec-green)';
      }
    });

    globalEventSource.addEventListener('EVENT_APPENDED', (e) => {
      const data = JSON.parse(e.data);
      playAlertSound();
      showTacticalToast(`📡 Live Event: ${data.payload.summary}`);
      appendBraidEventDOM(data.payload);
    });

    globalEventSource.addEventListener('FRONTIER_UPDATED', (e) => {
      const data = JSON.parse(e.data);
      showTacticalToast(`🎯 Frontier Advanced: ${data.payload.frontier ? data.payload.frontier.substring(0, 50) : 'Updated'}`);
      updateFrontierDOM(data.payload);
    });

    globalEventSource.addEventListener('AGENT_TELEMETRY', (e) => {
      const data = JSON.parse(e.data);
      const payload = data.payload;
      updateAgentTelemetryDOM(payload);
      showTacticalToast(`🤖 ${payload.actor_name || 'Agent'} [Step ${payload.step_index}/${payload.total_steps}]: ${payload.step_name}`);
    });

    globalEventSource.addEventListener('RESULT_DELIVERED', (e) => {
      playCodecRing();
      showTacticalToast('📦 Result Delivered! Human Review Required (NEEDS YOU)', true);
      updateFrontierDOM(e.data ? JSON.parse(e.data).payload : {});
    });

    globalEventSource.onerror = () => {
      const badge = document.getElementById('live-stream-badge');
      if (badge) {
        badge.textContent = '🟡 RECONNECTING...';
        badge.style.color = 'var(--amber-alert)';
        badge.style.borderColor = 'var(--amber-alert)';
      }
    };
  } catch (err) {
    console.error('Failed to initialize SSE stream:', err);
  }
}





