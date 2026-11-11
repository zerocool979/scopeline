'use strict';
// Uji end-to-end: halaman + app.js asli dijalankan di jsdom terhadap server sungguhan.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:8099';
const PW = 'Password-Uji-12345';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function waitFor(fn, what, timeout = 10000) {
  const t0 = Date.now(); let last;
  while (Date.now() - t0 < timeout) {
    try { const v = fn(); if (v) return v; } catch (e) { last = e; }
    await sleep(25);
  }
  throw new Error('Timeout menunggu: ' + what + (last ? ' (' + last.message + ')' : ''));
}

class Session {
  constructor(dom) { this.dom = dom; this.win = dom.window; this.doc = dom.window.document; }
  static async open() {
    const dom = await JSDOM.fromURL(BASE + '/', {
      runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true,
      beforeParse(w) { w.fetch = (u, o) => fetch(new URL(u, BASE), o); },
    });
    const s = new Session(dom);
    await waitFor(() => s.doc.querySelector('#app')?.children.length, 'aplikasi termuat');
    return s;
  }
  text() { return this.doc.body.textContent; }
  q(sel, root) { return (root || this.doc).querySelector(sel); }
  qa(sel, root) { return [...(root || this.doc).querySelectorAll(sel)]; }
  has(str) { return this.text().includes(str); }
  async see(str, what) { await waitFor(() => this.has(str), what || `teks "${str}"`); }
  toast() { return this.doc.getElementById('toast').textContent; }
  async seeToast(str) { await waitFor(() => this.toast().includes(str), `toast "${str}" (sekarang: "${this.toast()}")`); }
  find(selector, text, root) {
    return this.qa(selector, root).find(e => e.textContent.trim() === text);
  }
  button(text, root) { return this.find('button', text, root); }
  async click(text, root) { const b = await waitFor(() => this.button(text, root), `tombol "${text}"`); b.click(); return b; }
  label(text, root) {
    const l = this.qa('label', root).find(e => e.textContent.trim() === text);
    return l && l.nextElementSibling;
  }
  card(heading) {
    const h2 = this.qa('h2').find(e => e.textContent.trim().startsWith(heading));
    return h2 && h2.closest('.card');
  }
  set(el, value) {
    el.value = value;
    el.dispatchEvent(new this.win.Event('input', {bubbles: true}));
    el.dispatchEvent(new this.win.Event('change', {bubbles: true}));
  }
  go(hash) { this.win.location.hash = hash; }
  async login(username, password = PW) {
    await waitFor(() => this.q('#u'), 'form login');
    this.set(this.q('#u'), username); this.set(this.q('#p'), password);
    await this.click('Masuk');
    await waitFor(() => this.q('nav'), 'navigasi setelah login');
  }
  navLinks() { return this.qa('nav a').map(a => a.textContent.trim()); }
  close() { this.win.close(); }
}

async function api(path, {method = 'GET', body, token, form} = {}) {
  const headers = token ? {Authorization: 'Bearer ' + token} : {};
  if (body) headers['Content-Type'] = 'application/json';
  const r = await fetch(BASE + '/api' + path, {method, headers, body: form || (body ? JSON.stringify(body) : undefined)});
  if (!r.ok) throw new Error(`${method} ${path} -> ${r.status} ${await r.text()}`);
  return r.status === 204 ? null : r.json();
}

let passed = 0;
async function step(name, fn) {
  try { await fn(); passed++; console.log('  ✓ ' + name); }
  catch (e) { console.error('  ✗ ' + name + '\n    ' + (e.stack || e).toString().split('\n').slice(0, 6).join('\n    ')); process.exitCode = 1; throw e; }
}

(async () => {
  const open = async (user) => { const s = await Session.open(); if (user) await s.login(user); return s; };
  const ctx = {};
  console.log('SCOPELINE UI end-to-end');

  await step('seed: admin membuat pengguna semua peran', async () => {
    const admin = (await api('/auth/login', {method: 'POST', body: {username: 'admin', password: 'Admin-Password-123'}})).access_token;
    for (const [u, role] of [['lead', 'lead'], ['tester', 'tester'], ['reviewer', 'reviewer'], ['writer', 'writer']]) {
      await api('/users', {method: 'POST', token: admin, body: {username: u, full_name: u[0].toUpperCase() + u.slice(1), password: PW, role}});
    }
    ctx.admin = admin;
  });

  await step('login: kredensial salah ditolak, benar masuk', async () => {
    const s = await open();
    await waitFor(() => s.q('#u'), 'form');
    s.set(s.q('#u'), 'lead'); s.set(s.q('#p'), 'salah-salah-salah'); await s.click('Masuk');
    await s.seeToast('Kredensial tidak valid');
    await s.login('lead', PW);
    await s.see('Dasbor'); await s.see('Menunggu review');
    assert.deepEqual(s.navLinks().filter(x => ['Templat', 'Log Audit', 'Pengguna'].includes(x)), ['Templat', 'Log Audit']);
    ctx.lead = s;  // sesi dipakai ulang pada langkah berikutnya
  });

  await step('Lead: buat engagement, isi RoE, setujui, tugaskan tim, mulai pengujian', async () => {
    const s = ctx.lead;
    s.go('#/engagements'); await s.see('Engagement baru');
    const form = s.card('Engagement baru');
    s.set(s.label('Nama', form), 'UI E2E Engagement'); s.set(s.label('Klien', form), 'Klien Fiktif');
    s.set(s.label('Mulai', form), '2026-01-01'); s.set(s.label('Selesai', form), '2030-12-31');
    await s.click('Buat'); await waitFor(() => s.q('h1')?.textContent === 'UI E2E Engagement', 'detail engagement');
    ctx.engHash = s.win.location.hash;
    s.set(s.label('Ruang lingkup (target yang diizinkan)'), 'app.klien.example'); await s.click('Simpan'); await s.seeToast('Disimpan');
    const roe = s.card('Rules of Engagement');
    await waitFor(() => s.card('Rules of Engagement'), 'kartu RoE');
    s.set(s.card('Rules of Engagement').querySelector('textarea'), 'Hanya jam kerja, tanpa DoS.');
    await s.click('Simpan RoE'); await s.seeToast('RoE disimpan');
    assert.ok(s.button('Mulai pengujian').disabled, 'mulai pengujian terkunci sebelum RoE disetujui');
    await s.click('Setujui RoE'); await s.see('Disetujui oleh lead');
    const members = s.card('Anggota tim');
    for (const lbl of ['Tester (Penguji)', 'Reviewer (Peninjau)', 'Writer (Technical Writer)']) {
      const box = s.qa('label', members).find(l => l.textContent.trim() === lbl);
      assert.ok(box, 'checkbox ' + lbl); box.querySelector('input').checked = true;
    }
    await s.click('Simpan anggota', members); await s.seeToast('Anggota disimpan');
    await waitFor(() => !s.button('Mulai pengujian').disabled, 'tombol mulai aktif');
    await s.click('Mulai pengujian'); await waitFor(() => s.q('h1 + div .badge.active, .between .badge.active'), 'status aktif');
    await s.see('Catatan pentester (Markdown)'); await s.see('Catatan tim'); await s.see('Catatan Tester');
  });

  await step('Penguji: buat temuan dengan CVSS, ajukan review', async () => {
    const s = await open('tester'); ctx.tester = s;
    assert.ok(!s.navLinks().includes('Templat') && !s.navLinks().includes('Log Audit'));
    s.go('#/engagements'); await s.see('UI E2E Engagement');
    s.find('td', 'UI E2E Engagement').closest('tr').click();
    await s.click('+ Temuan'); await waitFor(() => s.q('#f-title'), 'form temuan');
    s.set(s.q('#f-title'), 'SQL Injection pada login'); s.set(s.q('#f-desc'), 'Parameter username tidak disanitasi');
    s.set(s.q('#f-impact'), 'Pengambilalihan akun'); s.set(s.q('#f-rec'), 'Gunakan parameterized query');
    const selects = s.qa('select', s.q('#f-title').closest('.card'));
    assert.equal(selects.length, 11, '11 Base metrics CVSS v4.0');
    for (const i of [5, 6, 7]) s.set(selects[i], 'H');
    await waitFor(() => s.q('.score')?.textContent === '9.9', 'skor CVSS 9.9');
    await s.click('Simpan'); await waitFor(() => s.q('h1')?.textContent.startsWith('F-001'), 'halaman temuan');
    ctx.findingHash = s.win.location.hash;
    assert.equal(s.q('#review-badge').textContent, 'Draf');
    await s.click('Ajukan review'); await s.seeToast('Status review diperbarui');
    await waitFor(() => s.q('#review-badge')?.textContent === 'Menunggu review', 'badge menunggu review');
    assert.ok(!s.button('Setujui'), 'penguji tidak melihat tombol setujui');
  });

  await step('Peninjau: catatan wajib saat minta perubahan, lalu minta perubahan', async () => {
    const s = await open('reviewer'); ctx.reviewer = s;
    s.go(ctx.findingHash); await waitFor(() => s.q('#review-badge')?.textContent === 'Menunggu review', 'halaman temuan (menunggu review)');
    assert.ok(s.button('Setujui') && s.button('Minta perubahan'));
    await s.click('Minta perubahan'); await s.seeToast('Catatan wajib');
    s.set(s.q('#review-note'), 'Perjelas langkah reproduksi'); await s.click('Minta perubahan');
    await waitFor(() => s.q('#review-badge')?.textContent === 'Perlu perubahan', 'badge perlu perubahan');
    await s.see('Perjelas langkah reproduksi');
  });

  await step('Technical Writer: hanya teks; tanpa bukti; ajukan ulang', async () => {
    const s = await open('writer'); ctx.writer = s;
    s.go(ctx.findingHash); await s.see('Technical Writer Anda dapat menyunting');
    assert.ok(!s.q('#evidence'), 'kartu bukti tersembunyi');
    assert.ok(s.qa('select', s.q('#f-title').closest('.card')).every(x => x.disabled), 'CVSS terkunci');
    assert.ok(s.q('#f-due').disabled && !s.q('#f-desc').readOnly);
    s.set(s.q('#f-desc'), 'Parameter username disisipkan langsung ke query SQL. Langkah: 1) buka /login 2) isi username dengan payload'); await s.click('Simpan');
    await s.seeToast('Temuan disimpan');
    await s.click('Ajukan review'); await waitFor(() => s.q('#review-badge')?.textContent === 'Menunggu review', 'diajukan ulang');
    assert.ok(!s.button('Hapus') && !s.button('Tandai diperbaiki'));
    s.go('#/templates'); await s.see('Templat laporan — Pretest');
    assert.ok(!s.has('Templat catatan pentester'), 'writer tidak melihat templat catatan');
    assert.ok(!s.navLinks().includes('Log Audit'));
  });

  await step('Peninjau menyetujui temuan (aturan empat mata diuji di tes API)', async () => {
    const s = ctx.reviewer; s.go('#/'); await s.see('Dasbor'); s.go(ctx.findingHash);
    await waitFor(() => s.q('#review-badge')?.textContent === 'Menunggu review', 'halaman temuan (menunggu review)'); await s.click('Setujui');
    await waitFor(() => s.q('#review-badge')?.textContent === 'Disetujui', 'disetujui');
  });

  await step('Penguji: tandai diperbaiki, catat retest lulus, perbandingan terisi', async () => {
    const s = ctx.tester; s.go(ctx.findingHash); await s.see('Status perbaikan');
    await s.click('Tandai diperbaiki'); await waitFor(() => s.q('#fix-badge')?.textContent === 'Diperbaiki', 'status diperbaiki');
    s.set(s.q('#rt-result'), 'passed'); s.set(s.q('#rt-notes'), 'Payload ditolak');
    await s.click('Catat retest'); await s.seeToast('Ronde retest dicatat');
    await waitFor(() => s.q('#fix-badge')?.textContent === 'Lulus retest', 'lulus retest');
    await s.see('Ronde 1'); await s.see('Payload ditolak');
    s.go(ctx.engHash); await s.see('Perbandingan pretest vs retest');
    const stats = s.qa('.stat', s.q('#comparison')).map(x => [x.querySelector('span').textContent, x.querySelector('b').textContent]);
    assert.deepEqual(stats.find(x => x[0].startsWith('Tertutup')), ['Tertutup (lulus retest)', '1']);
    assert.ok(s.q('#rep-kind') && s.button('Unduh DOCX') && s.has('Templat aktif: bawaan'));
  });

  await step('Catatan Markdown: render aman (anti-XSS), versi, muat versi lama', async () => {
    const s = ctx.tester; s.go(ctx.engHash); await s.see('Catatan pentester (Markdown)');
    s.find('td', 'Catatan Tester').closest('tr').click();
    await waitFor(() => s.q('#note-content'), 'editor catatan');
    const original = s.q('#note-content').value;
    assert.ok(original.startsWith('# Catatan Pentester'), 'berasal dari templat bawaan');
    await waitFor(() => s.q('#note-preview h1'), 'pratinjau');
    s.win.__pwned = undefined;
    const md = '# Hasil recon\n\n- [x] port scan selesai\n- [ ] enumerasi\n\n**tebal** `kode` [aman](https://example.com) [jahat](javascript:alert(1))\n\n' +
      '<img src=x onerror="window.__pwned=1">\n\n<script>window.__pwned=2</script>\n\n| Host | Port |\n|---|---|\n| 10.0.0.1 | 22 |\n\n```\nnmap -sV <host>\n```\n';
    s.set(s.q('#note-content'), md);
    const pv = s.q('#note-preview');
    assert.equal(pv.querySelector('h1').textContent, 'Hasil recon');
    assert.equal(pv.querySelectorAll('input[type=checkbox]').length, 2);
    assert.equal(pv.querySelectorAll('input[type=checkbox]:checked').length, 1);
    assert.equal(pv.querySelector('strong').textContent, 'tebal');
    assert.equal(pv.querySelector('table td').textContent, '10.0.0.1');
    const links = [...pv.querySelectorAll('a')];
    assert.equal(links.length, 1, 'hanya tautan http(s)'); assert.match(links[0].rel, /noopener/);
    assert.equal(pv.querySelectorAll('img, script').length, 0, 'tidak ada elemen berbahaya');
    assert.ok(pv.textContent.includes('<img src=x onerror='), 'HTML mentah tampil sebagai teks');
    assert.equal(s.win.__pwned, undefined, 'tidak ada skrip yang dieksekusi');
    await s.click('Simpan'); await s.seeToast('Catatan disimpan (v2)');
    await s.see('versi 2');
    await s.click('Muat ke editor'); await s.seeToast('Versi 1 dimuat');
    assert.equal(s.q('#note-content').value, original);
  });

  await step('Peninjau: catatan tim hanya baca; catatan pribadi penguji tidak terlihat', async () => {
    const s = ctx.reviewer; s.go(ctx.engHash); await s.see('Catatan pentester (Markdown)');
    assert.ok(s.has('Catatan tim') && !s.has('Catatan Tester'));
    s.find('td', 'Catatan tim').closest('tr').click();
    await waitFor(() => s.q('#note-content'), 'editor');
    assert.ok(s.q('#note-content').readOnly && !s.q('#note-save') && s.has('hanya baca'));
  });

  await step('XSS: judul temuan berisi HTML tampil sebagai teks', async () => {
    const tok = (await api('/auth/login', {method: 'POST', body: {username: 'tester', password: PW}})).access_token;
    const eid = ctx.engHash.split('/').pop();
    await api(`/engagements/${eid}/findings`, {method: 'POST', token: tok, body: {
      title: '<img src=x onerror="window.__pwned=3">', cvss_vector: 'CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N'}});
    const s = ctx.tester; s.win.__pwned = undefined; s.go('#/'); await s.see('Dasbor'); s.go(ctx.engHash);
    await s.see('<img src=x onerror=');
    assert.equal(s.qa('table img').length, 0); assert.equal(s.win.__pwned, undefined);
  });

  await step('Lead: templat laporan berversi (aktifkan, validasi) & templat catatan', async () => {
    const lead = (await api('/auth/login', {method: 'POST', body: {username: 'lead', password: PW}})).access_token;
    const fd = new FormData(); fd.append('kind', 'retest'); fd.append('notes', 'uji e2e');
    fd.append('file', new Blob([fs.readFileSync(process.env.SAMPLE_DOCX)]), 'sample.docx');
    const up = await api('/report-templates', {method: 'POST', token: lead, form: fd});
    assert.deepEqual(up.validation.unknown, ['unknown_field']);
    const s = ctx.lead; s.go('#/templates'); await s.see('Templat laporan — Retest');
    const card = await waitFor(() => s.q('#tpl-retest'), 'kartu retest');
    await waitFor(() => s.has('uji e2e'), 'baris versi');
    await s.click('Validasi', card); await waitFor(() => s.q('#validation'), 'hasil validasi');
    await s.see('{{unknown_field}}'); await s.see('Penanda {{content}} ada');
    await s.click('Aktifkan', s.q('#tpl-retest')); await s.seeToast('retest v1 diaktifkan');
    await waitFor(() => s.q('#tpl-retest .badge.active'), 'badge aktif');
    assert.ok(s.has('Templat catatan pentester (.md)') && s.has('Pustaka templat temuan'));
    s.go(ctx.engHash); await s.see('Laporan');
    s.set(s.q('#rep-kind'), 'retest'); await waitFor(() => s.q('#rep-info').textContent === 'Templat aktif: retest v1', 'info templat aktif');
  });

  await step('Kontrol akses UI: penguji diarahkan dari halaman templat; Lead melihat antrean review', async () => {
    const s = ctx.tester; s.go('#/templates'); await waitFor(() => s.q('h1')?.textContent === 'Dasbor', 'kembali ke dasbor');
    const lead = ctx.lead; lead.go('#/'); await lead.see('Menunggu review');
    lead.go(ctx.engHash); await lead.see('Perbandingan pretest vs retest');
    assert.ok(lead.button('Simpan anggota'));
  });

  console.log(`\n${passed} langkah lulus`);
  process.exit(process.exitCode || 0);  // jendela jsdom tidak ditutup: hindari galat dari permintaan yang masih berjalan
})().catch(e => { console.error('\nGAGAL: ' + e.message); process.exitCode = 1; setTimeout(() => process.exit(1), 100); });
