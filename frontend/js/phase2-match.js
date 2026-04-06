/* ═══════════════════════════════════════════════
   NextSteps — Phase 2: Skill Match
═══════════════════════════════════════════════ */

async function runMatch() {
  document.getElementById('mbtn').disabled = true;
  document.getElementById('mld').style.display = 'block';
  document.getElementById('mr').style.display = 'none';
  document.getElementById('merr').style.display = 'none';
  setTag('Matching…', false);

  const stepAnim = animSteps('mb', [
    [20, 'm0'], [44, 'm1'], [66, 'm2'], [84, 'm3'], [100, 'm4']
  ], 800);

  try {
    const res = await fetch(API + '/match', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile: S.profile, jd: S.jd }),
    });
    await stepAnim;

    if (!res.ok) {
      const err = await res.json().catch(function() { return { detail: 'HTTP ' + res.status }; });
      throw new Error(err.detail || 'HTTP ' + res.status);
    }

    S.gap_report = await res.json();
    S.matched = true;
    renderMatchResults();
  } catch (err) {
    document.getElementById('mld').style.display = 'none';
    document.getElementById('merr').style.display = 'block';
    document.getElementById('merr').textContent = '❌ Match failed: ' + err.message;
  }
  document.getElementById('mbtn').disabled = false;
}

function renderMatchResults() {
  document.getElementById('mld').style.display = 'none';
  document.getElementById('mr').style.display = 'block';
  const r = S.gap_report;
  const pct = r.overall_match_pct || 0;
  const matched = r.matched || [];
  const gaps = r.gaps || [];
  const strong = matched.filter(function(s) { return !s.is_gap && s.score >= 0.7; });
  const weak   = matched.filter(function(s) { return !s.is_gap && s.score < 0.7; });

  document.getElementById('match-no-skills').style.display =
    (S.profile && (S.profile.skills || []).length === 0) ? 'block' : 'none';

  countUp('mc1', pct, 1100, '%');
  countUp('mc2', strong.length, 800);
  countUp('mc3', weak.length, 800);
  countUp('mc4', gaps.length, 800);

  setTimeout(function() {
    const arc = document.getElementById('darc');
    arc.style.strokeDashoffset = 220 - (pct / 100) * 220;
    countUp('dscore', pct, 1300, '%');
  }, 120);

  if (matched.length + gaps.length === 0) {
    document.getElementById('msum').innerHTML =
      '<span style="color:var(--yellow)">No skills were detected in the job description.</span> Try a different job URL.';
    document.getElementById('match-no-skills').style.display = 'block';
  } else {
  document.getElementById('msum').innerHTML =
    'You match <strong style="color:var(--text)">' + strong.length + '</strong> of ' +
    (matched.length + gaps.length) + ' required skills. ' +
    (weak.length ? '<span style="color:var(--yellow)">' + weak.length + ' partial</span> · ' : '') +
    '<span style="color:var(--red)">' + gaps.length + ' gap' +
    (gaps.length !== 1 ? 's' : '') + ' to address.</span>';
  }

  document.getElementById('gap-chips').innerHTML = gaps.map(function(g) {
    return '<span class="chip cr" style="font-size:0.57rem">' + g.skill + '</span>';
  }).join('');

  function bldRows(arr) {
    if (!arr.length) return '<div style="color:var(--muted);font-size:0.7rem;padding:12px">None in this category.</div>';
    return arr.map(function(s, i) {
      var pctBar = Math.round((s.score || 0) * 100);
      var cls, icon, badgeCls, badgeTxt;
      if (s.is_gap) { cls = 'ga'; icon = '✗'; badgeCls = 'bga'; badgeTxt = 'gap'; }
      else if (s.score >= 0.7) { cls = 'ma'; icon = '✓'; badgeCls = 'bm'; badgeTxt = 'match'; }
      else { cls = 'wk'; icon = '~'; badgeCls = 'bwk'; badgeTxt = 'weak'; }
      return '<div class="skr ' + cls + '"><span class="sk-ic">' + icon +
        '</span><span class="sk-nm">' + s.skill +
        '</span><div class="sk-br"><div class="sk-fl" style="width:' + pctBar +
        '%;transition-delay:' + (i * 0.055) + 's"></div></div><span class="sk-sc">' +
        pctBar + '%</span><span class="sk-bg ' + badgeCls + '">' + badgeTxt + '</span></div>';
    }).join('');
  }

  document.getElementById('t-ma').innerHTML = bldRows(strong);
  document.getElementById('t-wk').innerHTML = bldRows(weak);
  document.getElementById('t-ga').innerHTML = bldRows(gaps);
  document.getElementById('t-al').innerHTML = bldRows([].concat(strong, weak, gaps));

  // "Leverage These" block: skills scoring ≥ 0.70
  const leverage = strong.filter(function(s) { return s.score >= 0.70; });
  const leverageEl = document.getElementById('leverage-block');
  if (leverageEl) {
    if (leverage.length > 0) {
      const chips = leverage.map(function(s) {
        return '<span class="chip cg2" style="font-size:0.6rem">' + s.skill + '</span>';
      }).join('');
      leverageEl.innerHTML =
        '<div style="font-size:0.62rem;color:var(--green);letter-spacing:2px;' +
        'text-transform:uppercase;margin-bottom:8px">💡 Lead With These</div>' +
        '<div style="font-size:0.7rem;color:var(--muted2);margin-bottom:10px">' +
        'Your strongest signals for this role — put these in your resume headline, ' +
        'cover letter opener, and interview answers.</div>' +
        chips;
      leverageEl.style.display = 'block';
    } else {
      leverageEl.style.display = 'none';
    }
  }

  updBar(2); updPP(2); setTag(Math.round(pct) + '% match ✓', true); saveSession();
  // recolour Phase 1 CV chips now that we have real match data
  if (typeof applyMatchColoursToCV === 'function') {
    applyMatchColoursToCV(S.gap_report.matched || [], S.gap_report.gaps || []);
  }
}

function swTab(el, tid, tabsId) {
  document.querySelectorAll('#' + tabsId + ' .tab').forEach(function(t) {
    t.classList.remove('active');
  });
  document.querySelectorAll('#page-match .tp').forEach(function(p) {
    p.classList.remove('active');
  });
  el.classList.add('active');
  document.getElementById(tid).classList.add('active');
}
