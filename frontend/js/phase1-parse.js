/* ═══════════════════════════════════════════════
   NextSteps — Phase 1: Parse
   File upload, PDF validation, parse API call
═══════════════════════════════════════════════ */

// ── File handling ─────────────────────────────────────────────────────────────
function onfs(inp) { if (inp.files[0]) setF(inp.files[0]); }

function hdrop(e) {
  e.preventDefault();
  document.getElementById('dz').classList.remove('drag');
  const f = e.dataTransfer.files[0];
  if (f) setF(f);
}

function setF(f) {
  S.cvFile = f;
  document.getElementById('dz').classList.add('done');
  document.getElementById('uz-ic').textContent = '✅';
  document.getElementById('uz-ttl').textContent = f.name;
  document.getElementById('uz-sub').textContent = (f.size / 1024).toFixed(1) + ' KB';
  const fn = document.getElementById('uz-fn');
  fn.style.display = 'block';
  fn.textContent = 'Ready to parse';
}

// ── Parse ─────────────────────────────────────────────────────────────────────
async function runParse() {
  const jobUrl = document.getElementById('jurl').value.trim();
  const rawJD = document.getElementById('paste-ta')?.value.trim() || '';
  const hasUrl = !!jobUrl;
  const hasPaste = rawJD.length > 50;

  if (!S.cvFile) { alert('Please upload your CV PDF first.'); return; }
  if (!hasUrl && !hasPaste) {
    alert('Please enter a job listing URL or paste the job description text.');
    return;
  }

  document.getElementById('inp-step').style.display = 'none';
  document.getElementById('ld-step').style.display = 'block';
  document.getElementById('err-step').style.display = 'none';
  setTag('Parsing…', false);

  const stepAnim = animSteps('pb', [
    [15, 'l0'], [30, 'l1'], [50, 'l2'], [68, 'l3'], [84, 'l4'], [95, 'l5']
  ], 900);

  try {
    const form = new FormData();
    form.append('cv', S.cvFile);
    form.append('job_url', hasUrl ? jobUrl : 'https://paste.nextsteps.local/manual');
    if (hasPaste) form.append('raw_jd_text', rawJD);
    const userCo = document.getElementById('co').value.trim();
    if (userCo) form.append('company_name', userCo);

    const res = await fetch(API + '/parse', { method: 'POST', body: form });
    await stepAnim;

    if (!res.ok) {
      const err = await res.json().catch(function() { return { detail: 'HTTP ' + res.status }; });
      throw new Error(err.detail || 'HTTP ' + res.status);
    }

    const data = await res.json();
    S.profile = data.profile;
    S.jd = data.jd;
    S.company_ctx = data.company_ctx || '';
    S.parsed = true;
    renderParseResults();
  } catch (err) {
    document.getElementById('ld-step').style.display = 'none';
    document.getElementById('err-step').style.display = 'block';
    document.getElementById('err-msg').textContent = '❌ Parse failed: ' + err.message;
    document.getElementById('inp-step').style.display = 'block';
    setTag('Error', false);
  }
}

// ── Render parse results ──────────────────────────────────────────────────────
function renderParseResults() {
  document.getElementById('ld-step').style.display = 'none';
  document.getElementById('res-step').style.display = 'block';
  setTag('Parsed ✓', true);

  const p = S.profile;
  const jd = S.jd;
  const jdSkillSet = new Set([...(jd.required_skills || []), ...(jd.nice_to_have || [])]);
  const cvSkillSet = new Set(p.skills || []);
  const cvSkills = p.skills || [];

  document.getElementById('no-skills-warn').style.display = cvSkills.length === 0 ? 'block' : 'none';
  // ADD — show JD skills warning too if empty
  const jdSkills = (jd.required_skills || []);
  const jdWarn = document.getElementById('jd-no-skills-warn');
  if (jdWarn) {
    jdWarn.style.display = jdSkills.length === 0 ? 'block' : 'none';
  }

  const jdSkillLower = new Set(
    [...(jd.required_skills || []), ...(jd.nice_to_have || [])].map(function(s) {
      return s.toLowerCase();
    })
  );

  document.getElementById('cv-sk').innerHTML = cvSkills.length
    ? cvSkills.map(function(sk) {
        return '<span class="chip ' + (jdSkillLower.has(sk.toLowerCase()) ? 'cg2' : 'cm') + '">' + sk + '</span>';
      }).join('')
    : '<span style="font-size:0.68rem;color:var(--red)">No skills extracted — try a single-column PDF</span>';

  const cvSkillLower = new Set((p.skills || []).map(function(s) {
    return s.toLowerCase();
  }));

  document.getElementById('jd-sk').innerHTML = (jd.required_skills || []).map(function(sk) {
    const matched = cvSkillLower.has(sk.toLowerCase());
    return '<span class="chip ' + (matched ? 'cb2' : 'cr') + '">' + sk + '</span>';
  }).join('');

  const expSnap = (p.experience || []).map(function(e) {
    return e.role + ' @ ' + e.company + ' (' + (e.duration || '') + ')';
  }).join(' · ');

  document.getElementById('exp-snap').textContent = expSnap || 'No experience extracted';
  document.getElementById('co-ctx').textContent = S.company_ctx || 'No company context found.';
  document.getElementById('jid').textContent = jd.job_id || '—';
  document.getElementById('jrole').textContent = jd.title || '—';
  document.getElementById('jco').textContent = jd.company || '—';
  document.getElementById('jskc').textContent = cvSkills.length + ' skills';
  document.getElementById('jjdc').textContent = (jd.required_skills || []).length + ' required';
  document.getElementById('sess-job').textContent = jd.title || 'Job loaded';
  document.getElementById('sess-co').textContent = '@ ' + (jd.company || '');
  updBar(1); updPP(1); saveSession();
}

// ── Reset parse ───────────────────────────────────────────────────────────────
function resetParse() {
  S.parsed = false; S.profile = null; S.jd = null; S.company_ctx = '';
  document.getElementById('inp-step').style.display = 'block';
  document.getElementById('ld-step').style.display = 'none';
  document.getElementById('res-step').style.display = 'none';
  document.getElementById('err-step').style.display = 'none';
  document.getElementById('dz').classList.remove('done');
  document.getElementById('uz-ic').textContent = '📄';
  document.getElementById('uz-ttl').textContent = 'Drag & drop your PDF here';
  document.getElementById('uz-sub').textContent = 'or click to browse · Single-column PDF only';
  document.getElementById('uz-fn').style.display = 'none';
  document.getElementById('jurl').value = '';
  document.getElementById('url-warn').style.display = 'none';
  document.getElementById('cvi').value = '';
  var pasteTa = document.getElementById('paste-ta');
  if (pasteTa) pasteTa.value = '';
  S.cvFile = null;
  setTag('Awaiting input', false);
}

  function applyMatchColoursToCV(matchedSkills, gapSkills) {
    const matchedLower = new Set(matchedSkills.map(function(s) {
      return s.skill.toLowerCase();
    }));
    const gapLower = new Set(gapSkills.map(function(s) {
      return s.skill.toLowerCase();
    }));

    document.querySelectorAll('#cv-sk .chip').forEach(function(chip) {
      const text = chip.textContent.toLowerCase();
      chip.classList.remove('cg2', 'cm', 'cr');
      if (matchedLower.has(text)) {
        chip.classList.add('cg2');          // green — confirmed match
      } else if (gapLower.has(text)) {
        chip.classList.add('cr');           // red — confirmed gap
      } else {
        chip.classList.add('cm');           // grey — not in JD
      }
    });
  }