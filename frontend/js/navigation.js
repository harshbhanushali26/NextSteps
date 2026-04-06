/* ═══════════════════════════════════════════════
   NextSteps — Navigation
   Sidebar, page switching, URL checks, modals
═══════════════════════════════════════════════ */

const TD = {
  upload:    { t: 'Upload & Parse',   s: 'Phase 1 — CV + Job Description' },
  match:     { t: 'Skill Match',      s: 'Phase 2 — Gap Analysis' },
  tailor:    { t: 'Resume & Cover',   s: 'Phase 3 — Application Package' },
  interview: { t: 'Interview Prep',   s: 'Phase 4 — Mock Interview Simulator' },
};
const PM = { upload: 0, match: 1, tailor: 2, interview: 3 };

// ── Sidebar toggle ────────────────────────────────────────────────────────────
function toggleSB() {
  const sb = document.getElementById('sb');
  sb.classList.toggle('col');
  localStorage.setItem('ns_sb_collapsed', sb.classList.contains('col') ? '1' : '0');
}

function restoreSBState() {
  const collapsed = localStorage.getItem('ns_sb_collapsed');
  if (collapsed === '1') {
    document.getElementById('sb').classList.add('col');
  }
}

// Keyboard shortcut: Ctrl+B
document.addEventListener('keydown', function(e) {
  if (e.ctrlKey && e.key === 'b') {
    e.preventDefault();
    toggleSB();
  }
});

// ── Start Fresh ───────────────────────────────────────────────────────────────
function startFresh() {
  if (!confirm('Clear all session data and start over?')) return;
  localStorage.removeItem('ns_dashboard');
  localStorage.removeItem('nextsteps_session');
  Object.assign(S, {
    cvFile: null, parsed: false, matched: false, tailored: false,
    profile: null, jd: null, company_ctx: '', gap_report: null,
    tailored_bullets: [], cover_letter: '', ats: null
  });
  document.getElementById('sess-job').textContent = 'No job loaded';
  document.getElementById('sess-co').textContent = '';
  updBar(0); updPP(0);
  resetParse();
  document.getElementById('me').style.display = 'none';
  document.getElementById('mm').style.display = 'block';
  document.getElementById('mr').style.display = 'none';
  document.getElementById('mld').style.display = 'none';
  document.getElementById('merr').style.display = 'none';
  document.getElementById('mbtn').disabled = false;
  ['mc1', 'mc2', 'mc3', 'mc4'].forEach(function(id) {
    const e = document.getElementById(id);
    if (e) e.textContent = '—';
  });
  document.getElementById('dscore').textContent = '0%';
  document.getElementById('te').style.display = 'none';
  document.getElementById('tm').style.display = 'block';
  document.getElementById('tr').style.display = 'none';
  document.getElementById('tld').style.display = 'none';
  document.getElementById('tbtn').disabled = false;
  setTag('Awaiting input', false);
  go('upload', document.querySelectorAll('.ni')[0]);
}

// ── Page navigation ───────────────────────────────────────────────────────────
function go(id, el) {
  document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
  document.querySelectorAll('.ni').forEach(function(n) { n.classList.remove('active'); });
  document.getElementById('page-' + id).classList.add('active');
  if (el) el.classList.add('active');
  const d = TD[id] || {};
  document.getElementById('tn-t').textContent = d.t || '';
  document.getElementById('tn-s').textContent = d.s || '';
  ['pt1', 'pt2', 'pt3', 'pt4'].forEach(function(pid, i) {
    const e = document.getElementById(pid);
    if (!e) return;
    e.classList.remove('active', 'done');
    if (i < PM[id]) e.classList.add('done');
    else if (i === PM[id]) e.classList.add('active');
  });
  if (id === 'upload') {
  document.getElementById('inp-step').style.display = S.parsed ? 'none' : 'block';
  document.getElementById('res-step').style.display = S.parsed ? 'block' : 'none';
  }
  if (id === 'match') {
    document.getElementById('me').style.display = S.parsed ? 'none' : 'block';
    document.getElementById('mm').style.display = S.parsed ? 'block' : 'none';
  }
  if (id === 'tailor') {
    document.getElementById('te').style.display = S.matched ? 'none' : 'block';
    document.getElementById('tm').style.display = S.matched ? 'block' : 'none';
  }
  if (id === 'interview') ivInit();
}

function goTo(id) {
  go(id, document.querySelectorAll('.ni')[PM[id]]);
}

// ── URL validation ────────────────────────────────────────────────────────────
function checkUrl(inp) {
  const url = inp.value.trim();
  const warn = document.getElementById('url-warn');
  
  if (!url) {
    warn.style.display = 'none';
    inp.classList.remove('warn', 'ok');
    return;
  }

  // Format check
  try {
    const parsed = new URL(url);
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      warn.textContent = '⚠ URL must start with http:// or https://';
      warn.style.display = 'block';
      inp.classList.add('warn');
      inp.classList.remove('ok');
      return;
    }
  } catch (e) {
    warn.textContent = '⚠ Invalid URL format — check for typos';
    warn.style.display = 'block';
    inp.classList.add('warn');
    inp.classList.remove('ok');
    return;
  }

  // Blocked domain check
  const lower = url.toLowerCase();
  const blocked = BLOCKED_DOMAINS.some(function(d) { return lower.includes(d); });
  if (blocked) {
    warn.textContent = '⚠ This site blocks automated fetching. Use the "Paste JD" option below, or try a direct company career page URL.';
    warn.style.display = 'block';
    inp.classList.add('warn');
    inp.classList.remove('ok');
    // Auto-show paste area
    const pa = document.getElementById('paste-area');
    if (pa) pa.classList.add('show');
    return;
  }

  // HTTPS suggestion
  if (url.startsWith('http://')) {
    warn.textContent = '⚡ Consider using HTTPS — most job boards require it';
    warn.style.display = 'block';
    inp.classList.remove('warn');
    inp.classList.remove('ok');
    return;
  }

  // Valid URL
  warn.style.display = 'none';
  inp.classList.remove('warn');
  inp.classList.add('ok');
}

// ── Paste JD toggle ───────────────────────────────────────────────────────────
function togglePasteJD() {
  const area = document.getElementById('paste-area');
  area.classList.toggle('show');
  const toggle = document.getElementById('paste-jd-toggle');
  if (area.classList.contains('show')) {
    toggle.textContent = '▾ Hide paste area';
  } else {
    toggle.textContent = '▸ Or paste job description manually';
  }
}

// ── Modals ────────────────────────────────────────────────────────────────────
function openModal(id) {
  document.getElementById(id).classList.add('show');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('show');
}

// Close modal on overlay click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('show');
  }
});

// Close modal on Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.show').forEach(function(m) {
      m.classList.remove('show');
    });
  }
});

// ── Session restore on load ───────────────────────────────────────────────────
function initDashboard() {
  restoreSBState();

  const restored = loadSession();
  if (restored) {
    if (S.parsed) {
      renderParseResults();
      document.getElementById('sess-job').textContent = S.jd?.title || 'Job loaded';
      document.getElementById('sess-co').textContent = '@ ' + (S.jd?.company || '');
    }
    if (S.matched) {
      renderMatchResults();
    }
    if (S.tailored) {
      renderTailorResults();
    }
    // Navigate to the furthest completed phase
    if (S.tailored) {
      go('tailor', document.querySelectorAll('.ni')[2]);
    } else if (S.matched) {
      go('match', document.querySelectorAll('.ni')[1]);
    } else if (S.parsed) {
      go('upload', document.querySelectorAll('.ni')[0]);
    }
  } else {
    go('upload', document.querySelectorAll('.ni')[0]);
  }
  updBar(0); updPP(0);
}
