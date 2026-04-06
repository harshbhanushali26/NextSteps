/* ═══════════════════════════════════════════════
   NextSteps — State Management
   Session state, API config, save/restore
═══════════════════════════════════════════════ */

const API = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:8000'
  : 'https://nextsteps-kmi2.onrender.com';

const BLOCKED_DOMAINS = [
  'linkedin.com','indeed.com','naukri.com','glassdoor.com',
  'monster.com','shine.com','timesjobs.com'
];

const S = {
  cvFile: null,
  parsed: false,
  matched: false,
  tailored: false,
  profile: null,
  jd: null,
  company_ctx: '',
  gap_report: null,
  tailored_bullets: [],
  cover_letter: '',
  ats: null,
};

function saveSession() {
  try {
    localStorage.setItem('nextsteps_session', JSON.stringify({
      profile: S.profile,
      jd: S.jd,
      company_ctx: S.company_ctx,
      gap_report: S.gap_report,
      tailored_bullets: S.tailored_bullets,
      cover_letter: S.cover_letter,
      ats: S.ats,
      parsed: S.parsed,
      matched: S.matched,
      tailored: S.tailored,
    }));
  } catch (e) {
    console.warn('Session save failed', e);
  }
}

function loadSession() {
  try {
    const raw = localStorage.getItem('nextsteps_session');
    if (!raw) return false;
    const data = JSON.parse(raw);
    if (!data.profile || !data.jd) return false;

    S.profile = data.profile;
    S.jd = data.jd;
    S.company_ctx = data.company_ctx || '';
    S.gap_report = data.gap_report;
    S.tailored_bullets = data.tailored_bullets || [];
    S.cover_letter = data.cover_letter || '';
    S.ats = data.ats || null;
    S.parsed = !!data.parsed;
    S.matched = !!data.matched;
    S.tailored = !!data.tailored;
    return true;
  } catch (e) {
    console.warn('Session restore failed', e);
    return false;
  }
}
