# Pemeriksaan mandiri OWASP ASVS Level 1

**Status dokumen:** self-assessment teknis, bukan sertifikasi atau audit keamanan independen.  
**Baseline kode:** branch `main`, setelah merge CVSS v4.0 pada commit `bca1d52479aa7537df025c4a3dc84d2807453705` (11 November 2026).

Legenda: ✅ kontrol tampak diimplementasikan dan tercakup dalam pengujian otomatis; 🔎 perlu verifikasi manual/lingkungan; ⚠️ keterbatasan atau risiko tersisa.

| Area | Kontrol / kondisi implementasi | Status | Bukti / catatan |
|---|---|---|---|
| Autentikasi | Argon2 password hashing; password minimum 10 karakter pada skema API; pesan login gagal seragam | ✅ | security.py, schemas.py, routers/auth.py |
| Autentikasi | Penguncian akun setelah 5 kegagalan (default 15 menit) dan rate limit IP 20/menit (default) | ✅ / ⚠️ | Penguncian akun tersimpan di DB; limiter IP in-memory per proses, bukan distributed |
| Autentikasi | MFA TOTP | ⚠️ | Fitur setup/enable/disable dan validasi OTP tersedia; opt-in, belum dipaksa untuk semua akun |
| Sesi | JWT HS256 bertanda tangan dan expiry; token_version membatalkan sesi setelah password/peran/status akun berubah | ✅ | security.py, deps.py, test auth |
| Akses | RBAC per endpoint dan pemeriksaan akses objek berdasarkan anggota engagement | ✅ | deps.py, test_object_level_access |
| Akses | Aturan empat mata; Technical Writer tidak memperoleh bukti mentah | ✅ | routers/findings.py, test_wave1.py |
| Validasi | Pydantic, validasi tanggal dan panjang field, CVSS dihitung di server | ✅ | schemas.py, cvss.py, test CVSS |
| Input/output | SQLAlchemy ORM; DOM frontend menggunakan mekanisme teks aman; Markdown diparse tanpa HTML mentah | ✅ | models.py, static/app.js, E2E anti-XSS |
| Unggahan | Allowlist PNG/JPG/JPEG/GIF/PDF/TXT/LOG, cek magic bytes/isi dasar, nama acak, batas upload | ✅ | routers/findings.py; 5 MB default lokal, maksimal 4 MB di Vercel |
| Bukti | Download attachment dengan nosniff; akses sesuai engagement; Technical Writer ditolak | ✅ | GET /api/evidence/{id}/download |
| Data at-rest | Bukti dapat disimpan sebagai BLOB PostgreSQL dengan EVIDENCE_IN_DB=1 | ⚠️ | Tidak ada bukti enkripsi field-level pada aplikasi; enkripsi at-rest bergantung provider/konfigurasi |
| Audit | Login, perubahan engagement/RoE, temuan, retest, ekspor, dan aksi penting dicatat | ✅ | audit.py, routers/* |
| Komunikasi | HTTPS/TLS pada deployment publik | 🔎 | Verifikasi sertifikat, domain, dan konfigurasi TLS pada domain aktif |
| Berkas | DOCX dibuka dan divalidasi; PDF memakai LibreOffice dengan argumen tetap tanpa shell | ✅ / 🔎 | PDF dinonaktifkan pada Vercel; hanya lingkungan yang menyediakan LibreOffice |
| Konfigurasi | CSP, X-Frame-Options, nosniff, Referrer-Policy, no-store API; docs API nonaktif default | ✅ | main.py |
| Dependensi | Ruff, Bandit, pip-audit di CI | ✅ | GitHub Actions CI branch PR #9 run `43030825984` completed/success |
| Pengujian | Coverage gate 70%, pytest SQLite dan PostgreSQL, E2E UI, Docker build | ✅ | Workflow .github/workflows/ci.yml; run `43030825984` success pada branch PR #9 |
| Migrasi | Alembic dan pengujian migrasi/model; FK SQLite ditegakkan | ✅ | migrate.py, database.py, test_migrations_match_models |
| CSRF | Token dikirim lewat header Bearer, bukan cookie | ✅ | deps.py, frontend |

## Batas interpretasi

1. Lulus CI berarti test dan pemeriksaan otomatis pada commit yang disebut berhasil; itu tidak sama dengan audit ASVS penuh.
2. TOTP adalah kemampuan yang tersedia, bukan kebijakan wajib untuk seluruh pengguna.
3. Rate limit IP in-memory tidak berbagi state antar-instance/worker.
4. Enkripsi bukti at-rest tidak boleh diklaim sebagai enkripsi aplikasi; pastikan konfigurasi enkripsi dan backup provider database.
5. TLS, backup/restore, retensi, pemantauan, dan pembatasan akses database perlu bukti dari lingkungan deployment.
6. Upload lokal default 5 MB, tetapi Vercel dikonfigurasi 4 MB; dokumentasi dan acceptance test harus menyebut konteks lingkungan.
7. Pada Vercel, PDF nonaktif karena runtime tidak menyediakan LibreOffice; DOCX tetap format ekspor yang disiapkan.

## Pemeriksaan manual sebelum klaim keamanan

- [ ] Verifikasi TLS pada domain produksi dan konfigurasi header di respons aktual.
- [ ] Verifikasi backup dan uji restore PostgreSQL.
- [ ] Verifikasi kebijakan retensi serta kontrol akses database.
- [ ] Putuskan apakah MFA harus diwajibkan bagi role tertentu.
- [ ] Evaluasi rate limit lintas-instance jika aplikasi diskalakan.
- [ ] Jalankan review ASVS manual dan dokumentasikan temuan, pengecualian, serta persetujuan risiko.
