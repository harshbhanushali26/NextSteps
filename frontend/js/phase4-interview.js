/* ═══════════════════════════════════════════════
   NextSteps — Phase 4: Interview
   Mock interview simulator
═══════════════════════════════════════════════ */

let ivQuestions = [], ivCurrentQ = 0, ivScored = [], ivSubmitting = false, ivIsEarly = false;

function ivShowSub(name) {
  ['iv-not-ready', 'iv-start', 'iv-loading', 'iv-chat-view', 'iv-scorecard'].forEach(function(id) {
    document.getElementById(id).style.display = 'none';
  });
  document.getElementById(name).style.display = 'block';
}

function ivInit() {
  if (!S.gap_report || !S.jd) { ivShowSub('iv-not-ready'); return; }
  var jd = S.jd;
  var gaps = (S.gap_report.gaps || []).map(function(g) { return g.skill; }).slice(0, 5);
  document.getElementById('iv-prev-role').textContent = (jd.title || '—') + ' @ ' + (jd.company || '—');
  document.getElementById('iv-prev-gaps').textContent = gaps.length ? gaps.join(', ') : 'None detected';
  if (document.getElementById('iv-scorecard').style.display === 'block') return;
  if (document.getElementById('iv-chat-view').style.display === 'block') return;
  ivShowSub('iv-start');
}

async function ivStart() {
  ivShowSub('iv-loading');
  document.getElementById('iv-ldr-txt').textContent = 'Generating questions from your gap report…';
  document.getElementById('iv-btn-start').disabled = true;
  try {
    var res = await fetch(API + '/interview/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jd: S.jd, gap_report: S.gap_report, n_questions: 10 }),
    });
    if (!res.ok) throw new Error('API ' + res.status);
    var data = await res.json();
    ivQuestions = data.questions;
    if (!ivQuestions || !ivQuestions.length) throw new Error('No questions returned');
  } catch (e) {
    ivShowSub('iv-start');
    document.getElementById('iv-btn-start').disabled = false;
    var err = document.createElement('div');
    err.className = 'callout cr2';
    err.style.marginTop = '14px';
    err.textContent = '❌ Failed to load questions: ' + e.message;
    document.querySelector('.start-card').appendChild(err);
    return;
  }
  document.getElementById('iv-q-count').textContent = ivQuestions.length + ' questions';
  ivShowSub('iv-chat-view');
  await ivAskQuestion(0);
}

async function ivAskQuestion(idx) {
  ivCurrentQ = idx;
  ivUpdateProgress(idx);
  document.getElementById('iv-btn-early').disabled = ivScored.length === 0;
  ivShowTyping(true);
  await ivDelay(600);
  ivShowTyping(false);
  ivAddBubble('int-ai', '<strong>Q' + (idx + 1) + '.</strong> ' + ivQuestions[idx]);
  document.getElementById('iv-ans-input').value = '';
  ivUpdCnt();
  document.getElementById('iv-ans-input').focus();
}

async function ivEarlyExit() {
  if (ivScored.length === 0) return;
  if (!confirm('Get results now? You\'ve answered ' + ivScored.length + ' of ' + ivQuestions.length + ' questions.')) return;
  ivIsEarly = true;
  await ivFinish();
}

async function ivSkip() {
  if (ivSubmitting) return;
  ivScored.push({
    question: ivQuestions[ivCurrentQ], answer: '[Skipped]',
    scores: { relevance: 0, depth: 0, clarity: 0 },
    feedback: 'Question skipped.', question_index: ivCurrentQ,
  });
  ivAddBubble('user', '<em style="color:var(--muted)">[Skipped]</em>');
  document.getElementById('iv-btn-early').disabled = false;
  await ivDelay(300);
  if (ivCurrentQ + 1 < ivQuestions.length) await ivAskQuestion(ivCurrentQ + 1);
  else await ivFinish();
}

async function ivSubmitAnswer() {
  if (ivSubmitting) return;
  var input = document.getElementById('iv-ans-input');
  var answer = input.value.trim();
  if (!answer) return;

  ivSubmitting = true;
  document.getElementById('iv-btn-sub').disabled = true;
  document.getElementById('iv-btn-skip').disabled = true;
  document.getElementById('iv-btn-early').disabled = true;

  ivAddBubble('user', answer);
  input.value = '';
  ivUpdCnt();
  ivShowTyping(true);

  try {
    var res = await fetch(API + '/interview/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: S.jd?.job_id || 'session',
        question: ivQuestions[ivCurrentQ],
        answer: answer,
        question_index: ivCurrentQ,
      }),
    });
    ivShowTyping(false);
    var data = res.ok
      ? await res.json()
      : { scores: { relevance: 0.5, depth: 0.4, clarity: 0.5 }, feedback: 'Could not score — continuing.', question_index: ivCurrentQ };
    ivScored.push({
      question: ivQuestions[ivCurrentQ], answer: answer,
      scores: data.scores, feedback: data.feedback,
      question_index: ivCurrentQ,
    });
    ivAddScoreBubble(data.scores, data.feedback);
  } catch (e) {
    ivShowTyping(false);
    ivScored.push({
      question: ivQuestions[ivCurrentQ], answer: answer,
      scores: { relevance: 0.5, depth: 0.4, clarity: 0.5 },
      feedback: 'Scoring unavailable.',
      question_index: ivCurrentQ,
    });
    ivAddScoreBubble({ relevance: 0.5, depth: 0.4, clarity: 0.5 }, 'Scoring failed — continuing.');
  }

  document.getElementById('iv-btn-early').disabled = false;
  await ivDelay(500);
  if (ivCurrentQ + 1 < ivQuestions.length) await ivAskQuestion(ivCurrentQ + 1);
  else { ivIsEarly = false; await ivFinish(); }

  ivSubmitting = false;
  document.getElementById('iv-btn-sub').disabled = false;
  document.getElementById('iv-btn-skip').disabled = false;
}

async function ivFinish() {
  ivShowSub('iv-loading');
  document.getElementById('iv-ldr-txt').textContent = 'Building your score report…';
  try {
    var res = await fetch(API + '/interview/summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: S.jd?.job_id || 'session', scored_answers: ivScored }),
    });
    if (!res.ok) throw new Error();
    ivRenderScorecard(await res.json());
  } catch (e) {
    var axes = ['relevance', 'depth', 'clarity'];
    var avgs = {};
    var answered = ivScored.filter(function(a) { return a.answer !== '[Skipped]'; });
    axes.forEach(function(a) {
      avgs[a] = answered.length
        ? answered.reduce(function(s, sa) { return s + (sa.scores?.[a] || 0); }, 0) / answered.length
        : 0;
    });
    var overall = axes.reduce(function(s, a) { return s + (avgs[a] || 0); }, 0) / axes.length;
    ivRenderScorecard({
      overall_score: overall,
      axis_averages: avgs,
      strengths: answered.length ? ['Answered ' + answered.length + ' question' + (answered.length !== 1 ? 's' : '')] : ['Started the interview'],
      improvements: ['Review feedback in the chat', 'Focus on your identified gap skills'],
    });
  }
}

function ivRenderScorecard(summary) {
  ivShowSub('iv-scorecard');
  if (ivIsEarly && ivScored.length < ivQuestions.length) {
    document.getElementById('iv-partial-banner').style.display = 'block';
    document.getElementById('iv-partial-count').textContent = ivScored.length;
    document.getElementById('iv-partial-total').textContent = ivQuestions.length;
    document.getElementById('iv-sc-label').textContent = 'Partial';
    document.getElementById('iv-sc-sub').textContent = 'Scored on ' + ivScored.length + ' of ' + ivQuestions.length + ' questions';
  } else {
    document.getElementById('iv-sc-label').textContent = 'Complete';
    document.getElementById('iv-sc-sub').textContent = 'Scored on all ' + ivScored.length + ' question' + (ivScored.length !== 1 ? 's' : '');
  }

  var overall = Math.round((summary.overall_score || 0) * 100);
  setTimeout(function() {
    var arc = document.getElementById('iv-circ-arc');
    var circ = 2 * Math.PI * 56;
    var color = overall >= 70 ? '#1de980' : overall >= 50 ? '#fbbf24' : '#f87171';
    arc.style.stroke = color;
    arc.style.strokeDashoffset = circ * (1 - overall / 100);
    document.getElementById('iv-circ-pct').textContent = overall + '%';
    document.getElementById('iv-circ-pct').style.color = color;
  }, 100);

  var ax = summary.axis_averages || {};
  [['relevance', 'iv-ax-rel', 'iv-pct-rel'], ['depth', 'iv-ax-dep', 'iv-pct-dep'], ['clarity', 'iv-ax-acc', 'iv-pct-acc']].forEach(function(item) {
    var k = item[0], barId = item[1], pctId = item[2];
    var p = Math.round((ax[k] || 0) * 100);
    setTimeout(function() {
      document.getElementById(barId).style.width = p + '%';
      document.getElementById(pctId).textContent = p + '%';
    }, 300);
  });

  document.getElementById('iv-si-str').innerHTML = (summary.strengths || []).map(function(s) {
    return '<li class="si-item">' + s + '</li>';
  }).join('');
  document.getElementById('iv-si-imp').innerHTML = (summary.improvements || []).map(function(s) {
    return '<li class="si-item">' + s + '</li>';
  }).join('');

  updBar(4); updPP(4);
}

function ivReset() {
  ivQuestions = []; ivCurrentQ = 0; ivScored = []; ivSubmitting = false; ivIsEarly = false;
  document.getElementById('iv-chat-win').innerHTML =
    '<div class="typing-ind" id="iv-typing"><div class="td"></div><div class="td"></div><div class="td"></div></div>';
  document.getElementById('iv-partial-banner').style.display = 'none';
  document.getElementById('iv-btn-early').disabled = true;
  document.querySelectorAll('.start-card .callout').forEach(function(e) { e.remove(); });
  document.getElementById('iv-btn-start').disabled = false;
  ivShowSub('iv-start');
}

// ── Chat helpers ──────────────────────────────────────────────────────────────
function ivAddBubble(role, html) {
  var win = document.getElementById('iv-chat-win');
  var d = document.createElement('div');
  d.className = 'bw ' + role;
  d.innerHTML = '<div class="bav">' + (role === 'user' ? 'You' : 'AI') + '</div><div class="bb2">' + html + '</div>';
  win.insertBefore(d, document.getElementById('iv-typing'));
  win.scrollTop = win.scrollHeight;
}

function ivAddScoreBubble(scores, feedback) {
  var axisMap = { relevance: 'Relevance', depth: 'Depth', clarity: 'Clarity', accuracy: 'Clarity' };
  var chips = Object.entries(scores).map(function(entry) {
    var k = entry[0], v = entry[1];
    var p = Math.round(v * 100);
    var cls = p >= 70 ? 'hi' : p >= 50 ? 'md2' : 'lo';
    return '<span class="sc-chip ' + cls + '">' + (axisMap[k] || k) + ' ' + p + '%</span>';
  }).join('');
  var win = document.getElementById('iv-chat-win');
  var d = document.createElement('div');
  d.className = 'bw int-ai';
  d.innerHTML = '<div class="bav">AI</div><div class="bb2"><div class="score-row">' + chips + '</div><div class="fb-txt">' + feedback + '</div></div>';
  win.insertBefore(d, document.getElementById('iv-typing'));
  win.scrollTop = win.scrollHeight;
}

function ivShowTyping(show) {
  var t = document.getElementById('iv-typing');
  if (t) t.style.display = show ? 'flex' : 'none';
}

function ivUpdateProgress(idx) {
  var total = ivQuestions.length;
  document.getElementById('iv-prog-fill').style.width = total ? (idx / total * 100) + '%' : '0%';
  document.getElementById('iv-prog-lbl').textContent = idx + ' / ' + total;
}

function ivUpdCnt() {
  document.getElementById('iv-ans-cnt').textContent = document.getElementById('iv-ans-input').value.length + ' chars';
}

function ivDelay(ms) { return new Promise(function(r) { setTimeout(r, ms); }); }

// Enter to submit in interview
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey && document.getElementById('iv-chat-view').style.display === 'block') {
    e.preventDefault();
    ivSubmitAnswer();
  }
});
