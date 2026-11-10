# Pemeriksaan mandiri OWASP ASVS Level 1 (draf untuk Sprint 6)

Status: ✅ diimplementasikan & diuji otomatis · 🔎 perlu verifikasi manual/pembimbing · ⚠️ keterbatasan diketahui

| Area ASVS | Kontrol | Status | Bukti |
|---|---|---|---|
| V2 Autentikasi | Hash Argon2id; kata sandi ≥10 karakter; pembatasan percobaan (kunci akun 15 mnt + batas per IP); pesan galat seragam; MFA TOTP | ✅ | `security.py`, `routers/auth.py`, `test_login_lockout_and_generic_error`, `test_mfa_flow` |
| V3 Sesi | Token bertanda tangan, kedaluwarsa, dicabut saat ganti sandi/peran/nonaktif | ✅ | `test_password_change_invalidates_token` |
| V4 Kontrol akses | RBAC pada setiap endpoint; akses objek (penguji hanya engagement tugasnya → 404) | ✅ | `deps.py`, `test_object_level_access` |
| V5 Validasi | Skema Pydantic (panjang/tipe/tanggal), vektor CVSS divalidasi ketat, ORM berparameter (anti SQLi), DOM via `textContent` (anti XSS), CSV dibatasi | ✅ | `schemas.py`, `cvss.py` |
| V5 Unggahan | Whitelist ekstensi, cek magic bytes, batas 5 MB, nama acak di disk, unduh `attachment` + `nosniff` | ✅ | `test_evidence_upload_rules` |
| V7 Log | Audit login gagal/berhasil, RoE, temuan, ekspor, perubahan pengguna | ✅ | `audit.py`, `test_dashboard_and_audit` |
| V8 Data | Rahasia via variabel lingkungan; `secret.key` 0600 bila dibuat otomatis | ✅ | `config.py` |
| V8 Data | Enkripsi bukti at-rest | ⚠️ mengandalkan enkripsi volume/disk host | — |
| V9 Komunikasi | TLS | 🔎 diterminasi di reverse proxy (Let's Encrypt) — wajib pada staging | — |
| V12 Berkas | Tidak ada eksekusi berkas unggahan; konversi PDF memakai argumen tetap tanpa shell | ✅ | `reporting.py` |
| V14 Konfigurasi | CSP ketat, X-Frame-Options, nosniff, no-store pada API; docs API nonaktif default; kontainer non-root; SAST (Bandit) & pip-audit di CI | ✅ | `main.py`, `Dockerfile`, `.github/workflows/ci.yml` |
| — | CSRF | ✅ token di header (bukan cookie) | README |
| — | Rate limit login in-memory per proses | ⚠️ tidak dibagi antar-worker; kunci akun berbasis DB tetap berlaku | `routers/auth.py` |
| V5 Keluaran | Markdown catatan dirender node-demi-node (tanpa innerHTML); tautan hanya http(s) dengan `noopener`; HTML mentah tampil sebagai teks | ✅ | `e2e/ui.test.js` (langkah "Catatan Markdown") |
| V4 Kontrol akses | Technical Writer tanpa bukti mentah; catatan pribadi hanya pemilik/Lead/Admin; empat mata pada review | ✅ | `tests/test_wave1.py` |
| V5 Unggahan | Templat laporan (.docx divalidasi dibuka, ≤5 MB) dan templat catatan (.md UTF-8, ≤200 KB) | ✅ | `routers/templates.py`, `routers/notes.py` |
| V14 Konfigurasi | Skema berversi (Alembic) dan diuji identik dengan model; FK ditegakkan juga pada SQLite | ✅ | `test_migrations_match_models` |
