'use strict';
const SEV = {critical: 'Kritis', high: 'Tinggi', medium: 'Sedang', low: 'Rendah', none: 'Info'};
const FSTAT = {open: 'Terbuka', fixed: 'Diperbaiki', retest_passed: 'Lulus retest'};
const ESTAT = {draft: 'Draf', active: 'Aktif', completed: 'Selesai'};
const ROLE = {admin: 'Admin', lead: 'Project Manager', tester: 'Engineer-Red Team', reviewer: 'Engineer-Head Offensive Security', writer: 'Engineer-Lead Technical Writer'};
const CVSS_METRICS = [
  ['AV', 'Attack Vector', {N: 'Network', A: 'Adjacent', L: 'Local', P: 'Physical'}],
  ['AC', 'Attack Complexity', {L: 'Low', H: 'High'}],
  ['AT', 'Attack Requirements', {N: 'None', P: 'Present'}],
  ['PR', 'Privileges Required', {N: 'None', L: 'Low', H: 'High'}],
  ['UI', 'User Interaction', {N: 'None', P: 'Passive', A: 'Active'}],
  ['VC', 'Vulnerable System Confidentiality', {H: 'High', L: 'Low', N: 'None'}],
  ['VI', 'Vulnerable System Integrity', {H: 'High', L: 'Low', N: 'None'}],
  ['VA', 'Vulnerable System Availability', {H: 'High', L: 'Low', N: 'None'}],
  ['SC', 'Subsequent System Confidentiality', {H: 'High', L: 'Low', N: 'None'}],
  ['SI', 'Subsequent System Integrity', {H: 'High', L: 'Low', N: 'None'}],
  ['SA', 'Subsequent System Availability', {H: 'High', L: 'Low', N: 'None'}],
];
const DEFAULT_VECTOR = 'CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:N/SI:N/SA:N';
const state = {token: sessionStorage.getItem('scopeline_token'), user: null};
const $app = document.getElementById('app');

// ---------- util (seluruh DOM dibangun dengan textContent: aman dari XSS) ----------
function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'value') el.value = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
function toast(msg, isErr) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'show' + (isErr ? ' err' : '');
  clearTimeout(toast.t); toast.t = setTimeout(() => { t.className = ''; }, 4500);
}
async function api(path, {method = 'GET', body, form, raw} = {}) {
  const headers = {};
  if (state.token) headers.Authorization = 'Bearer ' + state.token;
  let data;
  if (form) data = form;
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; data = JSON.stringify(body); }
  const res = await fetch('/api' + path, {method, headers, body: data});
  if (res.status === 401 && state.token && path !== '/auth/login') { logout(); throw new Error('Sesi berakhir, silakan masuk kembali'); }
  if (!res.ok) {
    let msg = 'Terjadi kesalahan (' + res.status + ')';
    try {
      const j = await res.json();
      if (typeof j.detail === 'string') msg = j.detail;
      else if (Array.isArray(j.detail)) msg = j.detail.map(d => (d.loc ? d.loc.slice(1).join('.') + ': ' : '') + d.msg).join('; ');
    } catch (_) { /* abaikan */ }
    throw new Error(msg);
  }
  if (raw) return res;
  return res.status === 204 ? null : res.json();
}
async function download(path, filename) {
  const res = await api(path, {raw: true});
  const url = URL.createObjectURL(await res.blob());
  const a = h('a', {href: url, download: filename});
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
const act = fn => async (ev) => {
  const b = ev && ev.currentTarget; if (b) b.disabled = true;
  try { await fn(ev); } catch (e) { toast(e.message, true); } finally { if (b) b.disabled = false; }
};
const sevBadge = s => h('span', {class: 'badge ' + s}, SEV[s] || s);
const fmtDate = d => d ? String(d).slice(0, 10) : '-';
const isStaff = () => state.user.role === 'lead';
const canWrite = () => ['admin', 'lead', 'tester'].includes(state.user.role);
const field = (label, input) => h('div', {}, h('label', {}, label), input);
const opts = (map, sel) => Object.entries(map).map(([k, v]) => h('option', {value: k, selected: k === sel}, v));
function logout() { sessionStorage.removeItem('scopeline_token'); state.token = null; state.user = null; location.hash = ''; route(); }

// ---------- layout ----------
function layout(active, ...content) {
  const link = (href, text, key) => h('a', {href: '#/' + href, class: active === key ? 'on' : ''}, text);
  return [
    h('nav', {}, h('span', {class: 'logo'}, 'SCOPE', h('b', {}, 'LINE')),
      link('', 'Dasbor', 'dash'), link('engagements', 'Engagement', 'eng'),
      ['admin', 'lead', 'writer'].includes(state.user.role) && link('templates', 'Templat', 'tpl'), ['admin', 'lead'].includes(state.user.role) && link('audit', 'Log Audit', 'audit'),
      state.user.role === 'admin' && link('users', 'Pengguna', 'users'),
      h('span', {class: 'sp'}), h('span', {class: 'who'}, `${state.user.full_name} (${ROLE[state.user.role]})`),
      link('account', 'Akun', 'acc'), h('a', {href: '#', onclick: e => { e.preventDefault(); logout(); }}, 'Keluar')),
    h('main', {}, ...content)];
}
function mount(nodes) { $app.replaceChildren(...[].concat(nodes)); }

// ---------- login ----------
function renderLogin() {
  const u = h('input', {id: 'u', autocomplete: 'username', required: true});
  const p = h('input', {id: 'p', type: 'password', autocomplete: 'current-password', required: true});
  const o = h('input', {id: 'o', inputmode: 'numeric', autocomplete: 'one-time-code', maxlength: '8'});
  const form = h('form', {class: 'card', onsubmit: act(async (e) => {
    e.preventDefault();
    const r = await api('/auth/login', {method: 'POST', body: {username: u.value, password: p.value, otp: o.value || null}});
    state.token = r.access_token; state.user = r.user; sessionStorage.setItem('scopeline_token', r.access_token);
    location.hash = '#/'; route();
  })}, field('Nama pengguna', u), field('Kata sandi', p), field('Kode MFA (bila diaktifkan)', o),
  h('div', {class: 'actions'}, h('button', {type: 'submit'}, 'Masuk')));
  mount(h('div', {class: 'login'}, h('h1', {}, 'SCOPE', h('b', {}, 'LINE')),
    h('p', {class: 'muted', style: null}, 'Platform manajemen engagement & pelaporan penetration testing.'), form));
}

// ---------- dasbor ----------
function bars(data, labels, cls) {
  const max = Math.max(1, ...Object.values(data));
  return Object.entries(data).map(([k, v]) => {
    const fill = h('div', {class: 'fill ' + (cls ? k : '')}); fill.style.width = (v / max * 100) + '%';
    return h('div', {class: 'bar'}, h('span', {class: 'n'}, labels ? (labels[k] || k) : k), h('div', {class: 'track'}, fill), h('b', {}, v));
  });
}
async function viewDashboard() {
  const d = await api('/dashboard');
  const stat = (n, l) => h('div', {class: 'stat'}, h('b', {}, n), h('span', {class: 'muted'}, l));
  mount(layout('dash', h('h1', {}, 'Dasbor'),
    h('div', {class: 'stats'}, stat(d.engagements, 'Engagement'), stat(d.findings, 'Total temuan'),
      stat(d.open_critical_high, 'Kritis/Tinggi terbuka'), stat(d.overdue, 'Lewat tenggat perbaikan'), stat(d.pending_review, 'Menunggu review')),
    h('div', {class: 'row'},
      h('div', {class: 'card'}, h('h2', {}, 'Temuan per tingkat keparahan'), bars(d.by_severity, SEV, true)),
      h('div', {class: 'card'}, h('h2', {}, 'Status perbaikan'), bars(d.by_status, FSTAT)),
      h('div', {class: 'card'}, h('h2', {}, 'Status engagement'), bars(d.engagements_by_status, ESTAT))),
    h('div', {class: 'card'}, h('h2', {}, 'Tren temuan baru (6 bulan)'), bars(d.findings_per_month))));
}

// ---------- engagement ----------
async function viewEngagements() {
  const list = await api('/engagements');
  const name = h('input', {required: true, maxlength: '200'}), client = h('input', {required: true, maxlength: '200'});
  const s = h('input', {type: 'date', required: true}), e = h('input', {type: 'date', required: true});
  const form = isStaff() && h('form', {class: 'card', onsubmit: act(async (ev) => {
    ev.preventDefault();
    const r = await api('/engagements', {method: 'POST', body: {name: name.value, client: client.value, start_date: s.value, end_date: e.value}});
    location.hash = '#/engagements/' + r.id;
  })}, h('h2', {}, 'Engagement baru'), h('div', {class: 'row'}, field('Nama', name), field('Klien', client), field('Mulai', s), field('Selesai', e)),
  h('div', {class: 'actions'}, h('button', {type: 'submit'}, 'Buat')));
  mount(layout('eng', h('h1', {}, 'Engagement'), form,
    h('div', {class: 'card'}, list.length ? h('table', {}, h('thead', {}, h('tr', {}, ['Nama', 'Klien', 'Periode', 'Status', 'RoE', 'Temuan'].map(t => h('th', {}, t)))),
      h('tbody', {}, list.map(x => h('tr', {class: 'link', onclick: () => { location.hash = '#/engagements/' + x.id; }},
        h('td', {}, x.name), h('td', {}, x.client), h('td', {}, fmtDate(x.start_date) + ' – ' + fmtDate(x.end_date)),
        h('td', {}, h('span', {class: 'badge ' + x.status}, ESTAT[x.status])),
        h('td', {}, h('span', {class: 'badge ' + (x.roe_approved ? 'ok' : 'warn')}, x.roe_approved ? 'Disetujui' : 'Belum')),
        h('td', {}, x.finding_count))))) : h('p', {class: 'muted'}, 'Belum ada engagement.'))));
}

async function viewEngagement(id) {
  const [e, findings, users, notes, noteTpls, activeTpl, cmp] = await Promise.all([api('/engagements/' + id), api('/engagements/' + id + '/findings'),
    isStaff() ? api('/users') : Promise.resolve([]), canSeeNotes() ? api(`/engagements/${id}/notes`) : Promise.resolve([]),
    canSeeNotes() ? api('/note-templates') : Promise.resolve({templates: []}), api('/report-templates/active'),
    api(`/engagements/${id}/comparison?include_unapproved=true`)]);
  const reload = () => viewEngagement(id).catch(x => toast(x.message, true));
  const ta = (v, ro) => h('textarea', {value: v, readonly: ro, maxlength: '20000'});
  const name = h('input', {value: e.name}), client = h('input', {value: e.client});
  const s = h('input', {type: 'date', value: fmtDate(e.start_date)}), en = h('input', {type: 'date', value: fmtDate(e.end_date)});
  const scope = ta(e.scope, !isStaff()), roe = ta(e.roe_text, !isStaff());
  [name, client, s, en].forEach(i => { if (!isStaff()) i.setAttribute('readonly', ''); });
  const memberIds = new Set(e.members.map(m => m.id));
  const checks = users.filter(u => u.is_active && u.role !== 'admin').map(u => {
    const c = h('input', {type: 'checkbox', checked: memberIds.has(u.id)}); c.checked = memberIds.has(u.id); c.dataset.id = u.id;
    return h('label', {}, c, ` ${u.full_name} (${ROLE[u.role]})`);
  });
  const fileCsv = h('input', {type: 'file', accept: '.csv'});
  const statusBtns = isStaff() ? {draft: [], active: ['completed', 'draft'], completed: ['active']}[e.status].map(st =>
    h('button', {class: 'sec', onclick: act(async () => { await api(`/engagements/${id}/status`, {method: 'POST', body: {status: st}}); toast('Status diubah'); reload(); })},
      '→ ' + ESTAT[st])) : [];
  if (isStaff() && e.status === 'draft') statusBtns.push(h('button', {disabled: !e.roe_approved, title: e.roe_approved ? '' : 'RoE belum disetujui',
    onclick: act(async () => { await api(`/engagements/${id}/status`, {method: 'POST', body: {status: 'active'}}); reload(); })}, 'Mulai pengujian'));
  mount(layout('eng',
    h('div', {class: 'between'}, h('h1', {}, e.name), h('div', {}, h('span', {class: 'badge ' + e.status}, ESTAT[e.status]), ' ',
      !e.in_window && h('span', {class: 'badge warn'}, 'Di luar jendela waktu'))),
    h('div', {class: 'card'}, h('h2', {}, 'Informasi & ruang lingkup'),
      h('div', {class: 'row'}, field('Nama', name), field('Klien', client), field('Mulai', s), field('Selesai', en)),
      field('Ruang lingkup (target yang diizinkan)', scope),
      isStaff() && h('div', {class: 'actions'}, h('button', {onclick: act(async () => {
        await api('/engagements/' + id, {method: 'PATCH', body: {name: name.value, client: client.value, start_date: s.value, end_date: en.value, scope: scope.value}});
        toast('Disimpan'); reload();
      })}, 'Simpan'))),
    h('div', {class: 'card'}, h('div', {class: 'between'}, h('h2', {}, 'Rules of Engagement (RoE)'),
      h('span', {class: 'badge ' + (e.roe_approved ? 'ok' : 'warn')}, e.roe_approved ? `Disetujui oleh ${e.roe_approved_by}` : 'Belum disetujui')),
      roe, h('p', {class: 'muted'}, `Persetujuan Project Manager: ${e.roe_approvals?.project_manager?.approved ? 'Disetujui' : 'Menunggu'} · Engineer-Head Offensive Security: ${e.roe_approvals?.engineer_head_offensive_security?.approved ? 'Disetujui' : 'Menunggu'}`),
      ['lead', 'reviewer'].includes(state.user.role) && h('div', {class: 'actions'},
        isStaff() && h('button', {class: 'sec', onclick: act(async () => { await api('/engagements/' + id, {method: 'PATCH', body: {roe_text: roe.value}}); toast('RoE disimpan (persetujuan direset bila berubah)'); reload(); })}, 'Simpan RoE'),
        h('button', {disabled: state.user.role === 'lead' ? e.roe_approvals?.project_manager?.approved : e.roe_approvals?.engineer_head_offensive_security?.approved, onclick: act(async () => { await api(`/engagements/${id}/roe/approve`, {method: 'POST'}); toast('Persetujuan RoE dicatat'); reload(); })}, 'Setujui RoE'),
        isStaff() ? statusBtns : null),
      h('p', {class: 'muted'}, 'Engagement hanya dapat diaktifkan setelah Project Manager dan Engineer-Head Offensive Security menyetujui RoE. Perubahan scope/RoE membatalkan kedua persetujuan.')),
    isStaff() && h('div', {class: 'card'}, h('h2', {}, 'Anggota tim'), h('div', {class: 'row'}, checks),
      h('div', {class: 'actions'}, h('button', {class: 'sec', onclick: act(async (ev) => {
        const ids = [...ev.currentTarget.closest('.card').querySelectorAll('input[type=checkbox]')].filter(c => c.checked).map(c => +c.dataset.id);
        await api(`/engagements/${id}/members`, {method: 'PUT', body: {user_ids: ids}}); toast('Anggota disimpan'); reload();
      })}, 'Simpan anggota'))),
    h('div', {class: 'card'}, h('div', {class: 'between'}, h('h2', {}, `Temuan (${findings.length})`),
      h('div', {class: 'actions'},
        canWrite() && h('button', {disabled: e.status !== 'active', onclick: () => { location.hash = `#/engagements/${id}/findings/new`; }}, '+ Temuan'),
        null)),
      findings.length ? h('table', {}, h('thead', {}, h('tr', {}, ['ID', 'Judul', 'CVSS (versi)', 'Keparahan', 'Review', 'Status', 'Tenggat'].map(t => h('th', {}, t)))),
        h('tbody', {}, findings.map(f => h('tr', {class: 'link', onclick: () => { location.hash = '#/findings/' + f.id; }},
          h('td', {}, f.code), h('td', {}, f.title), h('td', {}, f.cvss_score + ' (v' + f.cvss_version + ')'), h('td', {}, sevBadge(f.severity)),
          h('td', {}, h('span', {class: 'badge ' + f.review_status}, REVIEW[f.review_status])),
          h('td', {}, h('span', {class: 'badge ' + f.status}, FSTAT[f.status])), h('td', {}, fmtDate(f.due_date)))))) : h('p', {class: 'muted'}, 'Belum ada temuan.'),
      canWrite() && e.status === 'active' && h('div', {class: 'actions'}, h('label', {}, 'Impor CSV (title, description, impact, recommendation, cvss_vector):'), fileCsv,
        h('button', {class: 'sec', onclick: act(async () => {
          if (!fileCsv.files[0]) throw new Error('Pilih berkas CSV');
          const fd = new FormData(); fd.append('file', fileCsv.files[0]);
          const r = await api(`/engagements/${id}/findings/import`, {method: 'POST', form: fd});
          toast(`${r.created} temuan diimpor, ${r.errors.length} gagal`, r.errors.length > 0); reload();
        })}, 'Impor'))),
    reportCard(id, activeTpl), comparisonCard(cmp), notesCard(id, notes, noteTpls)));
}

// ---------- temuan ----------
function cvssEditor(initial, onChange) {
  const m = {}, baseKeys = new Set(CVSS_METRICS.map(([k]) => k));
  (initial || DEFAULT_VECTOR).split('/').slice(1).forEach(p => { const [k, v] = p.split(':'); m[k] = v; });
  let extras = Object.entries(m).filter(([k]) => !baseKeys.has(k));
  const out = h('span', {class: 'score'}, '–'), sev = h('span', {}), nom = h('span', {class: 'muted'}, 'CVSS-B'), vec = h('code', {});
  const selects = {};
  const vector = () => 'CVSS:4.0/' + CVSS_METRICS.map(([k]) => `${k}:${selects[k].value}`).join('/') + extras.map(([k, v]) => `/${k}:${v}`).join('');
  let seq = 0;
  const recalc = async () => {
    const v = vector(), mine = ++seq; vec.textContent = v;
    try {
      const r = await api('/cvss/calc', {method: 'POST', body: {vector: v}});
      if (mine !== seq) return;
      out.textContent = r.score; sev.replaceChildren(sevBadge(r.severity)); nom.textContent = r.nomenclature;
    } catch (_) { if (mine === seq) out.textContent = '?'; }
    onChange && onChange(v);
  };
  const grid = CVSS_METRICS.map(([k, label, o]) => {
    selects[k] = h('select', {onchange: recalc}, opts(o, m[k] || Object.keys(o)[0]));
    return field(label, selects[k]);
  });
  const root = h('div', {}, h('div', {class: 'row'}, grid),
    extras.length ? h('p', {class: 'muted'}, 'Metrik Threat/Environmental yang sudah ada dipertahankan pada vector; pengeditan metrik opsional dilakukan melalui vector/API.') : null,
    h('div', {class: 'between'}, h('div', {}, out, ' ', sev, ' ', nom), vec));
  const setVector = value => {
    const parsed = {};
    (value || DEFAULT_VECTOR).split('/').slice(1).forEach(p => { const [k, v] = p.split(':'); parsed[k] = v; });
    extras = Object.entries(parsed).filter(([k]) => !baseKeys.has(k));
    CVSS_METRICS.forEach(([k]) => { if (parsed[k]) selects[k].value = parsed[k]; });
    recalc();
  };
  recalc();
  return {root, vector, setVector};
}
async function viewFinding(fid, eid) {
  const [f, tpls] = await Promise.all([fid ? api('/findings/' + fid) : Promise.resolve(null), api('/finding-templates')]);
  const engId = f ? f.engagement_id : eid;
  const e = await api('/engagements/' + engId);
  const role = state.user.role;
  const fullEdit = canWrite() && e.status === 'active';
  const reportable = e.roe_approved && ['active', 'completed'].includes(e.status);
  const textEdit = role === 'writer' ? reportable : fullEdit;
  const reload = () => viewFinding(fid).catch(x => toast(x.message, true));
  const back = () => { location.hash = '#/engagements/' + engId; };
  const title = h('input', {id: 'f-title', value: f ? f.title : '', maxlength: '200', readonly: !textEdit});
  const desc = h('textarea', {id: 'f-desc', value: f ? f.description : '', readonly: !textEdit});
  const imp = h('textarea', {id: 'f-impact', value: f ? f.impact : '', readonly: !textEdit});
  const rec = h('textarea', {id: 'f-rec', value: f ? f.recommendation : '', readonly: !textEdit});
  const due = h('input', {type: 'date', id: 'f-due', value: f && f.due_date ? f.due_date : '', disabled: !fullEdit});
  const legacyCvss = !!f && f.cvss_version !== '4.0';
  let reassessLegacy = !legacyCvss;
  const cv = cvssEditor(f && !legacyCvss ? f.cvss_vector : null);
  const legacyBlock = legacyCvss ? h('div', {class: 'card'},
    h('b', {}, 'Penilaian historis CVSS v3.1 — tidak diubah otomatis'),
    h('p', {}, 'Skor: ' + f.cvss_score + ' (' + (SEV[f.severity] || f.severity) + ')'),
    h('code', {}, f.cvss_vector),
    fullEdit && h('button', {class: 'sec', onclick: () => {
      reassessLegacy = true; cv.root.hidden = false;
      toast('Isi metrik CVSS v4.0, lalu simpan untuk menambahkan penilaian baru. Skor historis v3.1 akan tetap tersimpan.');
    }}, 'Nilai ulang dengan CVSS v4.0')) : null;
  if (legacyCvss) cv.root.hidden = true;
  if (!fullEdit) cv.root.querySelectorAll('select').forEach(s => { s.disabled = true; });
  const tplSel = h('select', {onchange: () => {
    const t = tpls.find(x => String(x.id) === tplSel.value); if (!t) return;
    title.value = t.title; desc.value = t.description; imp.value = t.impact; rec.value = t.recommendation;
    if (t.cvss_version === '4.0') cv.setVector(t.cvss_vector);
    else toast('Template ini memakai CVSS v3.1; vector lama tidak diterapkan ke kalkulator v4.0. Lakukan penilaian ulang.');
  }}, h('option', {value: ''}, '— pilih templat —'), tpls.map(t => h('option', {value: t.id}, t.title + (t.cvss_version === '4.0' ? '' : ' (CVSS v3.1)'))));
  const body = () => {
    const b = {title: title.value, description: desc.value, impact: imp.value, recommendation: rec.value};
    if (fullEdit) {
      if (!legacyCvss || reassessLegacy) b.cvss_vector = cv.vector();
      b.due_date = due.value || null;
    }
    return b;
  };
  const parts = [h('div', {class: 'between'}, h('h1', {}, f ? `${f.code} — ${f.title}` : 'Temuan baru'), h('button', {class: 'sec', onclick: back}, '← Kembali')),
    !f && fullEdit && h('div', {class: 'card'}, field('Pustaka templat temuan umum', tplSel)),
    h('div', {class: 'card'}, role === 'writer' && h('p', {class: 'muted'}, 'Sebagai Technical Writer Anda dapat menyunting teks temuan (judul, deskripsi, dampak, rekomendasi). CVSS, tenggat, status, dan bukti dikelola penguji.'),
      field('Judul', title), field('Deskripsi', desc), field('Dampak', imp), field('Rekomendasi', rec),
      field('Tenggat perbaikan', due),
      f && f.cvss_legacy_vector && h('p', {class: 'muted'}, 'Riwayat ' + f.cvss_legacy_version + ': ' + f.cvss_legacy_score + ' (' + (SEV[f.cvss_legacy_severity] || f.cvss_legacy_severity) + ') — ' + f.cvss_legacy_vector),
      legacyBlock, h('h2', {}, 'Penilaian CVSS v4.0'), cv.root,
      textEdit && h('div', {class: 'actions'}, h('button', {id: 'f-save', onclick: act(async () => {
        if (f) { await api('/findings/' + fid, {method: 'PATCH', body: body()}); toast('Temuan disimpan'); reload(); }
        else { const r = await api(`/engagements/${eid}/findings`, {method: 'POST', body: body()}); toast('Temuan dibuat'); location.hash = '#/findings/' + r.id; }
      })}, 'Simpan'), f && isStaff() && fullEdit && h('button', {class: 'warn', onclick: act(async () => {
        if (!confirm('Hapus temuan ini beserta buktinya?')) return;
        await api('/findings/' + fid, {method: 'DELETE'}); back();
      })}, 'Hapus')))];
  if (f) {
    // --- review ---
    const isAuthor = ['admin', 'lead', 'tester', 'writer'].includes(role), isReviewer = ['admin', 'lead', 'reviewer'].includes(role);
    const canSubmit = reportable && isAuthor && ['draft', 'changes_requested'].includes(f.review_status);
    const canReview = reportable && isReviewer && f.review_status === 'in_review';
    const rnote = h('textarea', {id: 'review-note', placeholder: canReview ? 'Catatan review (wajib saat meminta perubahan)' : 'Catatan untuk peninjau (opsional)', maxlength: '5000'});
    const review = action => act(async () => {
      await api(`/findings/${fid}/review`, {method: 'POST', body: {action, note: rnote.value}}); toast('Status review diperbarui'); reload();
    });
    parts.push(h('div', {class: 'card', id: 'review'}, h('div', {class: 'between'}, h('h2', {}, 'Review'),
      h('span', {class: 'badge ' + f.review_status, id: 'review-badge'}, REVIEW[f.review_status])),
    f.review_note && h('p', {}, h('b', {}, 'Catatan terakhir: '), f.review_note),
    (canSubmit || canReview) && rnote,
    h('div', {class: 'actions'}, canSubmit && h('button', {onclick: review('submit')}, 'Ajukan review'),
      canReview && f.created_by_id !== state.user.id && h('button', {onclick: review('approve')}, 'Setujui'),
      canReview && h('button', {class: 'warn', onclick: review('request_changes')}, 'Minta perubahan')),
    canReview && f.created_by_id === state.user.id && h('p', {class: 'muted'}, 'Anda pembuat temuan ini; persetujuan harus dari orang lain (empat mata).'),
    h('p', {class: 'muted'}, 'Mengubah isi temuan yang sudah diajukan/disetujui mengembalikannya ke Draf. Laporan final hanya memuat temuan Disetujui.')));

    // --- perbaikan ---
    const notes = h('textarea', {placeholder: 'Catatan perbaikan', maxlength: '5000'}); notes.value = f.retest_notes || '';
    const setStatus = st => act(async () => { await api(`/findings/${fid}/status`, {method: 'POST', body: {status: st, notes: notes.value}}); toast('Status diperbarui'); reload(); });
    parts.push(h('div', {class: 'card'}, h('div', {class: 'between'}, h('h2', {}, 'Status perbaikan'), h('span', {class: 'badge ' + f.status, id: 'fix-badge'}, FSTAT[f.status])),
      fullEdit && notes, fullEdit && h('div', {class: 'actions'}, h('button', {class: 'sec', onclick: setStatus('open')}, 'Buka kembali'),
        h('button', {onclick: setStatus('fixed')}, 'Tandai diperbaiki')),
      h('p', {class: 'muted'}, '“Lulus retest” hanya dihasilkan oleh ronde retest di bawah.')));

    // --- ronde retest ---
    const roundBlock = r => {
      const file = h('input', {type: 'file', accept: '.png,.jpg,.jpeg,.gif,.pdf,.txt,.log'});
      return h('div', {class: 'round'}, h('div', {class: 'between'}, h('b', {}, `Ronde ${r.round_no} — ${fmtDate(r.tested_at)}`),
        h('span', {class: 'badge ' + r.result}, RESULT[r.result])), h('p', {class: 'muted'}, `Penguji: ${r.tester || '-'}`),
      r.notes && h('pre', {}, r.notes),
      r.evidence.map(ev => h('div', {class: 'actions'}, h('span', {}, ev.filename), h('button', {class: 'sec', onclick: act(() => download(`/evidence/${ev.id}/download`, ev.filename))}, 'Unduh'))),
      fullEdit && h('div', {class: 'actions'}, file, h('button', {class: 'sec', onclick: act(async () => {
        if (!file.files[0]) throw new Error('Pilih berkas terlebih dahulu');
        const fd = new FormData(); fd.append('file', file.files[0]);
        await api(`/retests/${r.id}/evidence`, {method: 'POST', form: fd}); toast('Bukti retest diunggah'); reload();
      })}, 'Unggah bukti retest')));
    };
    const rres = h('select', {id: 'rt-result'}, opts(RESULT, 'passed')), rdate = h('input', {type: 'date', id: 'rt-date'}), rtn = h('textarea', {id: 'rt-notes', maxlength: '5000'});
    parts.push(h('div', {class: 'card', id: 'retests'}, h('h2', {}, `Ronde retest (${f.retests.length})`),
      f.retests.length ? f.retests.map(roundBlock) : h('p', {class: 'muted'}, 'Belum ada retest.'),
      fullEdit && h('div', {}, h('h2', {}, 'Catat ronde baru'), h('div', {class: 'row'}, field('Hasil', rres), field('Tanggal (default hari ini)', rdate)), field('Catatan', rtn),
        h('div', {class: 'actions'}, h('button', {id: 'rt-save', onclick: act(async () => {
          await api(`/findings/${fid}/retests`, {method: 'POST', body: {result: rres.value, tested_at: rdate.value || null, notes: rtn.value}});
          toast('Ronde retest dicatat'); reload();
        })}, 'Catat retest')))));

    // --- bukti (tidak untuk Admin dan Technical Writer) ---
    if (!["writer", "admin"].includes(role)) {
      const file = h('input', {type: 'file', accept: '.png,.jpg,.jpeg,.gif,.pdf,.txt,.log'});
      parts.push(h('div', {class: 'card', id: 'evidence'}, h('h2', {}, 'Bukti'),
        f.evidence.length ? h('table', {}, f.evidence.map(ev => h('tr', {}, h('td', {}, ev.filename), h('td', {class: 'muted'}, Math.ceil(ev.size / 1024) + ' KB'),
          h('td', {}, h('button', {class: 'sec', onclick: act(() => download(`/evidence/${ev.id}/download`, ev.filename))}, 'Unduh'), ' ',
            fullEdit && h('button', {class: 'warn', onclick: act(async () => { await api('/evidence/' + ev.id, {method: 'DELETE'}); reload(); })}, 'Hapus'))))) : h('p', {class: 'muted'}, 'Belum ada bukti.'),
        fullEdit && h('div', {class: 'actions'}, file, h('button', {onclick: act(async () => {
          if (!file.files[0]) throw new Error('Pilih berkas terlebih dahulu');
          const fd = new FormData(); fd.append('file', file.files[0]);
          await api(`/findings/${fid}/evidence`, {method: 'POST', form: fd}); toast('Bukti diunggah'); reload();
        })}, 'Unggah')), h('p', {class: 'muted'}, 'Format: png, jpg, gif, pdf, txt, log. Maks. 5 MB. Gunakan data fiktif.')));
    }
    const hist = await api(`/findings/${fid}/history`);
    parts.push(h('div', {class: 'card'}, h('h2', {}, 'Riwayat'), hist.length ? h('table', {}, hist.map(r => h('tr', {},
      h('td', {class: 'muted'}, String(r.created_at).replace('T', ' ').slice(0, 16)), h('td', {}, r.username), h('td', {}, r.action), h('td', {}, r.detail)))) : h('p', {class: 'muted'}, '-')));
  }
  mount(layout('eng', ...parts));
}

// ---------- templat ----------
let lastValidation = null;
function validationBox(v) {
  if (!v) return null;
  return h('div', {class: 'card', id: 'validation'}, h('h2', {}, 'Hasil validasi templat'),
    h('p', {}, 'Placeholder dikenali: ', v.placeholders.filter(p => !v.unknown.includes(p)).map(p => `{{${p}}}`).join(', ') || '(tidak ada)'),
    v.unknown.length ? h('p', {class: 'err'}, 'Tidak dikenal (dibiarkan apa adanya): ' + v.unknown.map(p => `{{${p}}}`).join(', ')) : h('p', {class: 'muted'}, 'Tidak ada placeholder yang tidak dikenal.'),
    h('p', {class: 'muted'}, v.has_content_marker ? 'Penanda {{content}} ada: isi laporan disisipkan di posisinya.' : 'Tanpa {{content}}: isi laporan ditambahkan di akhir dokumen.'));
}

async function viewTemplates() {
  const staff = isStaff();
  const [reportTpls, ntpls, tpls] = await Promise.all([api('/report-templates'),
    staff ? api('/note-templates') : Promise.resolve({templates: []}), staff ? api('/finding-templates') : Promise.resolve([])]);
  const reload = () => viewTemplates().catch(x => toast(x.message, true));
  const KIND = {pretest: 'Pretest (laporan awal)', retest: 'Retest (verifikasi)'};

  // --- templat laporan berversi ---
  const kindCard = kind => {
    const list = reportTpls.filter(t => t.kind === kind);
    return h('div', {class: 'card', id: 'tpl-' + kind}, h('h2', {}, 'Templat laporan — ' + KIND[kind]),
      list.length ? h('table', {}, h('thead', {}, h('tr', {}, ['Versi', 'Status', 'Berkas', 'Catatan', 'Pengunggah', ''].map(t => h('th', {}, t)))),
        h('tbody', {}, list.map(t => h('tr', {}, h('td', {}, 'v' + t.version), h('td', {}, h('span', {class: 'badge ' + (t.status === 'archived' ? 'none' : t.status)}, TSTAT[t.status])),
          h('td', {}, t.filename), h('td', {class: 'muted'}, t.notes || '-'), h('td', {class: 'muted'}, t.created_by || '-'),
          h('td', {}, h('div', {class: 'actions'},
            h('button', {class: 'sec', onclick: act(() => download(`/report-templates/${t.id}/download`, `${kind}-v${t.version}.docx`))}, 'Unduh'),
            h('button', {class: 'sec', onclick: act(async () => { lastValidation = await api(`/report-templates/${t.id}/validate`); reload(); })}, 'Validasi'),
            t.status !== 'active' && h('button', {onclick: act(async () => { await api(`/report-templates/${t.id}/activate`, {method: 'POST'}); toast(`${kind} v${t.version} diaktifkan`); reload(); })},
              t.status === 'archived' ? 'Rollback ke versi ini' : 'Aktifkan'),
            t.status === 'draft' && h('button', {class: 'warn', onclick: act(async () => { await api('/report-templates/' + t.id, {method: 'DELETE'}); reload(); })}, 'Hapus'))))))) : h('p', {class: 'muted'}, 'Belum ada templat kustom; laporan memakai templat bawaan.'));
  };
  const upKind = h('select', {id: 'up-kind'}, opts(KIND, 'pretest')), upNotes = h('input', {id: 'up-notes', maxlength: '500', placeholder: 'Catatan versi (mis. perubahan logo)'});
  const upFile = h('input', {type: 'file', id: 'up-file', accept: '.docx'});
  const uploadCard = h('div', {class: 'card'}, h('h2', {}, 'Unggah versi baru templat laporan'),
    h('div', {class: 'row'}, field('Jenis', upKind), field('Catatan versi', upNotes), field('Berkas .docx', upFile)),
    h('div', {class: 'actions'}, h('button', {id: 'up-btn', onclick: act(async () => {
      if (!upFile.files[0]) throw new Error('Pilih berkas .docx');
      const fd = new FormData(); fd.append('kind', upKind.value); fd.append('notes', upNotes.value); fd.append('file', upFile.files[0]);
      const r = await api('/report-templates', {method: 'POST', form: fd});
      lastValidation = r.validation; toast(`Versi ${r.version} dibuat sebagai draf. Periksa validasi, lalu aktifkan.`); reload();
    })}, 'Unggah sebagai draf')),
    h('p', {class: 'muted'}, 'Placeholder: {{client}}, {{engagement}}, {{period}}, {{date}}, {{report_type}}, {{template_version}}, {{status}} (juga di header/footer/tabel). '
      + 'Letakkan {{content}} sendirian pada satu paragraf untuk menentukan posisi isi laporan. Versi lama tetap tersimpan dan dapat di-rollback.'));
  const parts = [h('h1', {}, 'Templat'), kindCard('pretest'), kindCard('retest'), uploadCard, validationBox(lastValidation)];
  lastValidation = null;

  if (staff) {
    // --- templat catatan (.md) ---
    const nFile = h('input', {type: 'file', id: 'nt-file', accept: '.md,.markdown'}), nName = h('input', {id: 'nt-name', maxlength: '120', placeholder: 'Nama (default: nama berkas)'});
    const nDef = h('input', {type: 'checkbox', id: 'nt-default'});
    const editor = h('div', {id: 'nt-editor'});
    const openEditor = async t => {
      const full = await api('/note-templates/' + t.id);
      const name = h('input', {value: full.name, maxlength: '120'}), ta = h('textarea', {class: 'mono', value: full.content, maxlength: '200000'});
      editor.replaceChildren(h('div', {class: 'card'}, h('h2', {}, 'Edit templat catatan'), field('Nama', name), field('Isi (Markdown)', ta),
        h('div', {class: 'actions'}, h('button', {onclick: act(async () => { await api('/note-templates/' + t.id, {method: 'PUT', body: {name: name.value, content: ta.value}}); toast('Templat disimpan'); reload(); })}, 'Simpan'),
          h('button', {class: 'sec', onclick: () => editor.replaceChildren()}, 'Tutup'))));
    };
    parts.push(h('div', {class: 'card', id: 'note-templates'}, h('h2', {}, 'Templat catatan pentester (.md)'),
      h('p', {class: 'muted'}, 'Templat default disalin ke catatan tim saat engagement dibuat dan ke catatan pribadi saat penguji ditugaskan.'),
      ntpls.templates.length ? h('table', {}, h('tbody', {}, ntpls.templates.map(t => h('tr', {}, h('td', {}, t.name, ' ', t.is_default && h('span', {class: 'badge ok'}, 'Default')),
        h('td', {class: 'muted'}, Math.ceil(t.size / 1024) + ' KB'), h('td', {}, h('div', {class: 'actions'},
          h('button', {class: 'sec', onclick: act(() => openEditor(t))}, 'Edit'),
          !t.is_default && h('button', {class: 'sec', onclick: act(async () => { await api(`/note-templates/${t.id}/default`, {method: 'POST'}); reload(); })}, 'Jadikan default'),
          h('button', {class: 'warn', onclick: act(async () => { await api('/note-templates/' + t.id, {method: 'DELETE'}); reload(); })}, 'Hapus'))))))) : h('p', {class: 'muted'}, 'Belum ada templat kustom; memakai templat bawaan.'),
      h('div', {class: 'row'}, field('Berkas .md', nFile), field('Nama', nName), h('div', {}, h('label', {}, nDef, ' Jadikan default'))),
      h('div', {class: 'actions'}, h('button', {id: 'nt-up', onclick: act(async () => {
        if (!nFile.files[0]) throw new Error('Pilih berkas .md');
        const fd = new FormData(); fd.append('file', nFile.files[0]); fd.append('name', nName.value); fd.append('make_default', nDef.checked ? 'true' : 'false');
        await api('/note-templates/upload', {method: 'POST', form: fd}); toast('Templat catatan diunggah'); reload();
      })}, 'Unggah templat'), h('button', {class: 'sec', onclick: act(async () => {
        const b = await api('/note-templates/builtin'); const a = h('a', {href: URL.createObjectURL(new Blob([b.content], {type: 'text/markdown'})), download: 'templat-catatan-bawaan.md'});
        document.body.append(a); a.click(); a.remove();
      })}, 'Unduh templat bawaan sebagai contoh'))), editor);

    // --- templat temuan ---
    const t = h('input', {maxlength: '200'}), d = h('textarea', {}), i = h('textarea', {}), r = h('textarea', {});
    const cv = cvssEditor(null);
    parts.push(h('div', {class: 'card'}, h('h2', {}, 'Pustaka templat temuan'),
      tpls.length ? h('table', {}, tpls.map(x => h('tr', {}, h('td', {}, x.title), h('td', {class: 'muted'}, x.cvss_vector),
        h('td', {}, h('button', {class: 'warn', onclick: act(async () => { await api('/finding-templates/' + x.id, {method: 'DELETE'}); reload(); })}, 'Hapus'))))) : h('p', {class: 'muted'}, 'Belum ada templat.')),
    h('div', {class: 'card'}, h('h2', {}, 'Templat temuan baru'), field('Judul', t), field('Deskripsi', d), field('Dampak', i), field('Rekomendasi', r), cv.root,
      h('div', {class: 'actions'}, h('button', {onclick: act(async () => {
        await api('/finding-templates', {method: 'POST', body: {title: t.value, description: d.value, impact: i.value, recommendation: r.value, cvss_vector: cv.vector()}});
        toast('Templat ditambahkan'); reload();
      })}, 'Tambah'))));
  }
  mount(layout('tpl', ...parts));
}

// ---------- kartu engagement (laporan, perbandingan, catatan) ----------
const REVIEW = {draft: 'Draf', in_review: 'Menunggu review', approved: 'Disetujui', changes_requested: 'Perlu perubahan'};
const RESULT = {passed: 'Lulus', failed: 'Gagal', partial: 'Sebagian'};
const TSTAT = {draft: 'Draf', active: 'Aktif', archived: 'Arsip'};
const canSeeNotes = () => ['admin', 'lead', 'tester', 'reviewer'].includes(state.user.role);
const canCreateNote = () => ['admin', 'lead', 'tester'].includes(state.user.role);
const canManageReportTemplates = () => ['admin', 'lead', 'writer'].includes(state.user.role);

function reportCard(id, activeTpl) {
  const kind = h('select', {id: 'rep-kind'}, h('option', {value: 'pretest'}, 'Pretest (laporan awal)'), h('option', {value: 'retest'}, 'Retest (verifikasi)'));
  const draft = h('input', {type: 'checkbox', id: 'rep-draft'});
  const info = h('p', {class: 'muted', id: 'rep-info'});
  const approvals = h('p', {class: 'muted'});
  const actions = h('div', {class: 'actions'});
  const refresh = async () => {
    const t = activeTpl[kind.value];
    info.textContent = t ? `Templat aktif: ${kind.value} v${t.version}` : 'Templat aktif: bawaan (belum ada templat kustom)';
    const a = await api(`/engagements/${id}/reports/${kind.value}/approvals`);
    approvals.textContent = `Persetujuan Project Manager: ${a.project_manager.approved ? 'Disetujui' : 'Menunggu'} · Engineer-Head Offensive Security: ${a.engineer_head_offensive_security.approved ? 'Disetujui' : 'Menunggu'}`;
  };
  kind.addEventListener('change', () => refresh().catch(x => toast(x.message, true)));
  const dl = fmt => act(() => download(`/engagements/${id}/report?format=${fmt}&kind=${kind.value}&include_unapproved=${draft.checked}`,
    `laporan-${kind.value}${draft.checked ? '-draf' : ''}.${fmt}`));
  if (['lead', 'reviewer'].includes(state.user.role)) {
    actions.append(h('button', {class: 'sec', onclick: act(async () => {
      await api(`/engagements/${id}/reports/${kind.value}/approve`, {method: 'POST'});
      await refresh(); toast('Persetujuan laporan dicatat');
    })}, 'Setujui laporan'));
  }
  actions.append(h('button', {onclick: dl('docx')}, 'Unduh DOCX'), h('button', {class: 'sec', onclick: dl('pdf')}, 'Unduh PDF'));
  refresh().catch(x => { approvals.textContent = x.message; });
  return h('div', {class: 'card'}, h('h2', {}, 'Laporan'),
    h('div', {class: 'row'}, field('Jenis laporan', kind), h('div', {}, h('label', {}, draft, ' Sertakan temuan belum disetujui (ditandai DRAF)'))),
    info, approvals, actions,
    h('p', {class: 'muted'}, 'Laporan final hanya dapat diunduh setelah disetujui Project Manager dan Engineer-Head Offensive Security. Persetujuan mengikuti versi data dan template saat disetujui.'));
}

function comparisonCard(cmp) {
  const total = Object.values(cmp.counts).reduce((a, b) => a + b, 0);
  const rows = Object.entries(cmp.buckets).flatMap(([k, items]) => items.map(f =>
    h('tr', {class: 'link', onclick: () => { location.hash = '#/findings/' + f.id; }}, h('td', {}, cmp.labels[k]), h('td', {}, f.code),
      h('td', {}, f.title), h('td', {}, sevBadge(f.severity)), h('td', {}, f.rounds))));
  return h('div', {class: 'card', id: 'comparison'}, h('h2', {}, 'Perbandingan pretest vs retest'),
    h('div', {class: 'stats'}, Object.entries(cmp.counts).map(([k, n]) => h('div', {class: 'stat'}, h('b', {}, n), h('span', {class: 'muted'}, cmp.labels[k])))),
    total ? h('table', {}, h('thead', {}, h('tr', {}, ['Kategori', 'ID', 'Judul', 'Keparahan', 'Ronde'].map(t => h('th', {}, t)))), h('tbody', {}, rows))
      : h('p', {class: 'muted'}, 'Belum ada temuan.'));
}

function notesCard(id, notes, noteTpls) {
  if (!canSeeNotes()) return null;
  const title = h('input', {maxlength: '200', placeholder: 'Judul catatan pribadi'});
  const tpl = h('select', {}, h('option', {value: ''}, '— templat default —'), noteTpls.templates.map(t => h('option', {value: t.id}, t.name)));
  return h('div', {class: 'card', id: 'notes'}, h('h2', {}, 'Catatan pentester (Markdown)'),
    notes.length ? h('table', {}, h('thead', {}, h('tr', {}, ['Judul', 'Jenis', 'Versi', 'Diubah'].map(t => h('th', {}, t)))),
      h('tbody', {}, notes.map(n => h('tr', {class: 'link', onclick: () => { location.hash = '#/notes/' + n.id; }}, h('td', {}, n.title),
        h('td', {}, n.scope === 'team' ? 'Tim' : 'Pribadi' + (n.owner ? ` (${n.owner})` : '')), h('td', {}, 'v' + n.version),
        h('td', {class: 'muted'}, String(n.updated_at).replace('T', ' ').slice(0, 16)))))) : h('p', {class: 'muted'}, 'Belum ada catatan.'),
    canCreateNote() && h('div', {class: 'row'}, field('Catatan pribadi baru', title), field('Templat', tpl),
      h('div', {}, h('label', {}, '\u00a0'), h('button', {onclick: act(async () => {
        const r = await api(`/engagements/${id}/notes`, {method: 'POST', body: {title: title.value || 'Catatan baru', template_id: tpl.value ? +tpl.value : null}});
        location.hash = '#/notes/' + r.id;
      })}, '+ Catatan pribadi'))));
}

// ---------- Markdown aman (DOM dibangun node demi node; tanpa innerHTML, HTML mentah ditampilkan sebagai teks) ----------
function mdInline(text) {
  const frag = document.createDocumentFragment();
  const re = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*\s][^*]*\*)|(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\))/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) frag.append(text.slice(last, m.index));
    if (m[1]) frag.append(h('code', {}, m[1].slice(1, -1)));
    else if (m[2]) frag.append(h('strong', {}, m[2].slice(2, -2)));
    else if (m[3]) frag.append(h('em', {}, m[3].slice(1, -1)));
    else frag.append(h('a', {href: m[6], target: '_blank', rel: 'noopener noreferrer'}, m[5]));
    last = m.index + m[0].length;
  }
  if (last < text.length) frag.append(text.slice(last));
  return frag;
}
function renderMarkdown(src) {
  const root = h('div', {class: 'md'});
  const lines = String(src).replace(/\r\n/g, '\n').split('\n');
  const listRe = /^\s*(?:[-*]|\d+\.)\s+/, rowRe = /^\s*\|.*\|\s*$/, sepRe = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/;
  const starts = l => /^(#{1,6}\s|```|>|\s*(?:[-*]|\d+\.)\s+)/.test(l) || rowRe.test(l) || /^(-{3,}|\*{3,})\s*$/.test(l);
  const cells = l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    let m;
    if (/^\s*$/.test(line)) { i++; continue; }
    if (/^```/.test(line)) {
      const buf = []; i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++; root.append(h('pre', {class: 'code'}, h('code', {}, buf.join('\n')))); continue;
    }
    if ((m = /^(#{1,6})\s+(.*)$/.exec(line))) { root.append(h('h' + m[1].length, {class: 'mdh'}, mdInline(m[2]))); i++; continue; }
    if (/^(-{3,}|\*{3,})\s*$/.test(line)) { root.append(h('hr')); i++; continue; }
    if (/^>/.test(line)) {
      const buf = [];
      while (i < lines.length && /^>/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, ''));
      root.append(h('blockquote', {}, mdInline(buf.join(' ')))); continue;
    }
    if (rowRe.test(line) && i + 1 < lines.length && sepRe.test(lines[i + 1])) {
      const head = cells(line); i += 2; const rows = [];
      while (i < lines.length && rowRe.test(lines[i])) rows.push(cells(lines[i++]));
      root.append(h('table', {}, h('thead', {}, h('tr', {}, head.map(c => h('th', {}, mdInline(c))))),
        h('tbody', {}, rows.map(r => h('tr', {}, r.map(c => h('td', {}, mdInline(c))))))));
      continue;
    }
    if (listRe.test(line)) {
      const ordered = /^\s*\d+\./.test(line), items = [];
      while (i < lines.length && listRe.test(lines[i])) {
        let text = lines[i++].replace(listRe, ''), box = null;
        const c = /^\[( |x|X)\]\s+(.*)$/.exec(text);
        if (c) { box = h('input', {type: 'checkbox', disabled: true, checked: c[1] !== ' '}); text = c[2]; }
        items.push(h('li', {}, box, box ? ' ' : null, mdInline(text)));
      }
      root.append(h(ordered ? 'ol' : 'ul', {}, items)); continue;
    }
    const buf = [];
    while (i < lines.length && !/^\s*$/.test(lines[i]) && (buf.length === 0 || !starts(lines[i]))) buf.push(lines[i++]);
    root.append(h('p', {}, mdInline(buf.join(' '))));
  }
  return root;
}

// ---------- catatan ----------
async function viewNote(id) {
  const [n, versions] = await Promise.all([api('/notes/' + id), api(`/notes/${id}/versions`)]);
  const title = h('input', {id: 'note-title', value: n.title, maxlength: '200', readonly: !n.writable});
  const ta = h('textarea', {id: 'note-content', class: 'mono', value: n.content, readonly: !n.writable, maxlength: '200000', spellcheck: 'false'});
  const preview = h('div', {id: 'note-preview'});
  const refresh = () => preview.replaceChildren(renderMarkdown(ta.value));
  ta.addEventListener('input', refresh); refresh();
  const canDelete = n.scope === 'personal' && (n.owner_id === state.user.id || isStaff());
  mount(layout('eng',
    h('div', {class: 'between'}, h('h1', {}, n.title), h('button', {class: 'sec', onclick: () => { location.hash = '#/engagements/' + n.engagement_id; }}, '← Kembali')),
    h('p', {class: 'muted'}, `${n.scope === 'team' ? 'Catatan tim' : 'Catatan pribadi' + (n.owner ? ' — ' + n.owner : '')} • versi ${n.version}` + (n.writable ? '' : ' • hanya baca')),
    h('div', {class: 'row'},
      h('div', {class: 'card'}, field('Judul', title), field('Isi (Markdown)', ta),
        h('div', {class: 'actions'}, n.writable && h('button', {id: 'note-save', onclick: act(async () => {
          const r = await api('/notes/' + id, {method: 'PUT', body: {content: ta.value, title: title.value, base_version: n.version}});
          toast(`Catatan disimpan (v${r.version})`); viewNote(id).catch(x => toast(x.message, true));
        })}, 'Simpan'), h('button', {class: 'sec', onclick: act(() => download(`/notes/${id}/export`, 'catatan.md'))}, 'Ekspor .md'),
        canDelete && h('button', {class: 'warn', onclick: act(async () => {
          if (!confirm('Hapus catatan pribadi ini?')) return;
          await api('/notes/' + id, {method: 'DELETE'}); location.hash = '#/engagements/' + n.engagement_id;
        })}, 'Hapus'))),
      h('div', {class: 'card'}, h('h2', {}, 'Pratinjau'), preview)),
    h('div', {class: 'card'}, h('h2', {}, 'Riwayat versi'), h('table', {}, h('tbody', {}, versions.map(v => h('tr', {},
      h('td', {}, 'v' + v.version), h('td', {}, v.edited_by || '-'), h('td', {class: 'muted'}, String(v.created_at).replace('T', ' ').slice(0, 16)),
      h('td', {class: 'muted'}, Math.ceil(v.size / 1024 * 10) / 10 + ' KB'),
      h('td', {}, n.writable && v.version !== n.version && h('button', {class: 'sec', onclick: act(async () => {
        const old = await api(`/notes/${id}/versions/${v.version}`); ta.value = old.content; refresh();
        toast(`Versi ${v.version} dimuat di editor. Simpan untuk menjadikannya versi terbaru.`);
      })}, 'Muat ke editor')))))))));
}

// ---------- log audit ----------
async function viewAudit() {
  const rows = await api('/audit?limit=300');
  mount(layout('audit', h('h1', {}, 'Log Audit'), h('div', {class: 'card'}, h('table', {}, h('thead', {}, h('tr', {}, ['Waktu (UTC)', 'Pengguna', 'Aksi', 'Objek', 'Detail'].map(x => h('th', {}, x)))),
    h('tbody', {}, rows.map(r => h('tr', {}, h('td', {class: 'muted'}, String(r.created_at).replace('T', ' ').slice(0, 19)), h('td', {}, r.username), h('td', {}, r.action),
      h('td', {}, r.entity ? `${r.entity}#${r.entity_id ?? ''}` : ''), h('td', {}, r.detail))))))));
}

// ---------- pengguna ----------
async function viewUsers() {
  const users = await api('/users');
  const un = h('input', {maxlength: '64'}), fn = h('input', {maxlength: '120'}), pw = h('input', {type: 'password', autocomplete: 'new-password'});
  const role = h('select', {}, opts(ROLE, 'tester'));
  const upd = (u, body, msg) => act(async () => { await api('/users/' + u.id, {method: 'PATCH', body}); toast(msg); viewUsers(); });
  mount(layout('users', h('h1', {}, 'Manajemen Pengguna'),
    h('div', {class: 'card'}, h('table', {}, h('thead', {}, h('tr', {}, ['Pengguna', 'Nama', 'Peran', 'MFA', 'Status', ''].map(x => h('th', {}, x)))),
      h('tbody', {}, users.map(u => {
        const rs = h('select', {}, opts(ROLE, u.role));
        rs.onchange = act(async () => { await api('/users/' + u.id, {method: 'PATCH', body: {role: rs.value}}); toast('Peran diubah'); viewUsers(); });
        return h('tr', {}, h('td', {}, u.username), h('td', {}, u.full_name), h('td', {}, u.id === state.user.id ? ROLE[u.role] : rs),
          h('td', {}, u.totp_enabled ? 'Aktif' : '-'), h('td', {}, h('span', {class: 'badge ' + (u.is_active ? 'ok' : 'none')}, u.is_active ? 'Aktif' : 'Nonaktif')),
          h('td', {}, u.id !== state.user.id && [h('button', {class: 'sec', onclick: upd(u, {is_active: !u.is_active}, 'Status diubah')}, u.is_active ? 'Nonaktifkan' : 'Aktifkan'), ' ',
            h('button', {class: 'sec', onclick: act(async () => { const p = prompt('Kata sandi baru (min. 10 karakter):'); if (!p) return; await api('/users/' + u.id, {method: 'PATCH', body: {password: p}}); toast('Kata sandi direset'); })}, 'Reset sandi')]));
      })))),
    h('div', {class: 'card'}, h('h2', {}, 'Pengguna baru'), h('div', {class: 'row'}, field('Nama pengguna', un), field('Nama lengkap', fn), field('Kata sandi (min. 10)', pw), field('Peran', role)),
      h('div', {class: 'actions'}, h('button', {onclick: act(async () => {
        await api('/users', {method: 'POST', body: {username: un.value, full_name: fn.value, password: pw.value, role: role.value}}); toast('Pengguna dibuat'); viewUsers();
      })}, 'Buat')))));
}

// ---------- akun ----------
async function viewAccount() {
  const cur = h('input', {type: 'password', autocomplete: 'current-password'}), nw = h('input', {type: 'password', autocomplete: 'new-password'});
  const mfaBox = h('div', {});
  const renderMfa = () => {
    mfaBox.replaceChildren();
    if (state.user.totp_enabled) {
      const p = h('input', {type: 'password', placeholder: 'Kata sandi'});
      mfaBox.append(h('p', {}, 'MFA aktif.'), p, h('div', {class: 'actions'}, h('button', {class: 'warn', onclick: act(async () => {
        await api('/auth/mfa/disable', {method: 'POST', body: {password: p.value}}); state.user = await api('/auth/me'); renderMfa(); toast('MFA dinonaktifkan');
      })}, 'Nonaktifkan MFA')));
    } else {
      mfaBox.append(h('button', {onclick: act(async () => {
        const r = await api('/auth/mfa/setup', {method: 'POST'}); const code = h('input', {placeholder: 'Kode 6 digit', inputmode: 'numeric', maxlength: '8'});
        mfaBox.replaceChildren(h('p', {}, 'Tambahkan ke aplikasi autentikator (TOTP) dengan kunci berikut, lalu masukkan kodenya:'), h('pre', {}, r.secret), h('p', {class: 'muted'}, r.uri), code,
          h('div', {class: 'actions'}, h('button', {onclick: act(async () => { await api('/auth/mfa/enable', {method: 'POST', body: {code: code.value}}); state.user = await api('/auth/me'); renderMfa(); toast('MFA aktif'); })}, 'Aktifkan')));
      })}, 'Siapkan MFA (TOTP)'));
    }
  };
  renderMfa();
  mount(layout('acc', h('h1', {}, 'Akun'), h('div', {class: 'card'}, h('h2', {}, 'Ganti kata sandi'), field('Kata sandi saat ini', cur), field('Kata sandi baru (min. 10)', nw),
    h('div', {class: 'actions'}, h('button', {onclick: act(async () => { await api('/auth/change-password', {method: 'POST', body: {current_password: cur.value, new_password: nw.value}}); toast('Kata sandi diubah'); logout(); })}, 'Simpan'))),
  h('div', {class: 'card'}, h('h2', {}, 'Autentikasi multi-faktor'), mfaBox)));
}

// ---------- router ----------
async function route() {
  if (!state.token) return renderLogin();
  try {
    if (!state.user) state.user = await api('/auth/me');
    const p = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean);
    if (!p.length) return await viewDashboard();
    if (p[0] === 'engagements' && !p[1]) return await viewEngagements();
    if (p[0] === 'engagements' && p[2] === 'findings' && p[3] === 'new') return await viewFinding(null, +p[1]);
    if (p[0] === 'engagements') return await viewEngagement(+p[1]);
    if (p[0] === 'findings') return await viewFinding(+p[1]);
    if (p[0] === 'templates' && canManageReportTemplates()) return await viewTemplates();
    if (p[0] === 'notes' && canSeeNotes()) return await viewNote(+p[1]);
    if (p[0] === 'audit' && isStaff()) return await viewAudit();
    if (p[0] === 'users' && state.user.role === 'admin') return await viewUsers();
    if (p[0] === 'account') return await viewAccount();
    location.hash = '#/';
  } catch (err) {
    if (state.token) { toast(err.message, true); if (!state.user) logout(); }
  }
}
window.addEventListener('hashchange', route);
route();
