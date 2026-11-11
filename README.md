# SCOPELINE

Platform manajemen engagement dan pelaporan penetration testing berbasis web (STMIK Tazkia).

**SCOPELINE adalah sistem manajemen dan dokumentasi**, bukan vulnerability scanner, exploit framework, atau alat otomasi serangan. Seluruh data demo/pengujian harus fiktif atau digunakan dengan izin tertulis.

## Dokumen acuan

- [Baseline realitas proyek berdasarkan source code](docs/PROJECT-REALITY-BASELINE.md) — definisi produk, alur bisnis, model data, role, keamanan, batas lingkungan, bukti CI, dan ketidaksesuaian versi lama.
- [Status implementasi dan deployment](docs/DEPLOYMENT-STATUS.md) — commit, CI, Vercel, konfigurasi environment tanpa nilai rahasia, dan checklist runtime.
- [Matriks peran dan izin](docs/PERAN-DAN-IZIN.md).
- [Pemeriksaan mandiri OWASP ASVS Level 1](docs/ASVS-L1-checklist.md).

Dokumen Program Analysis DOCX/PDF v1.1 di folder docs/ adalah dokumen teknis yang perlu disinkronkan terhadap baseline kode terbaru sebelum dianggap sebagai dokumentasi terkini. Bila ada perbedaan, **source code dan test pada commit yang disebut adalah acuan perilaku implementasi**; dokumen proposal tetap acuan untuk visi dan rencana, bukan bukti fitur selesai.

## Fitur implementasi

| Area | Fitur |
|---|---|
| Autentikasi & pengguna | Argon2, JWT, pencabutan token, MFA TOTP opsional, lockout login, RBAC |
| Engagement | Scope, periode, RoE, anggota, status; pengujian terkunci sampai RoE disetujui |
| Temuan | Pencatatan, pustaka template, CVSS v3.1 server-side, bukti |
| Review | Draft → In Review → Approved / Changes Requested; aturan empat mata |
| Retest | Ronde per temuan, hasil dan bukti, perbandingan pretest/retest |
| Laporan | DOCX pretest/retest, template DOCX berversi; laporan final hanya memuat temuan approved |
| Catatan | Catatan tim/pribadi Markdown, template, versi, deteksi konflik |
| Operasional | Dashboard, audit log, impor CSV |

### Role

Admin, Lead, Penguji (tester), Peninjau (reviewer), dan Technical Writer (writer). Technical Writer hanya dapat menyunting narasi temuan dan template laporan; tidak dapat mengakses bukti mentah atau mengubah CVSS/status teknis.

## Stack dan data

- Python 3.12, FastAPI, Pydantic, SQLAlchemy.
- HTML/CSS/JavaScript vanilla tanpa build step.
- PostgreSQL untuk Vercel/produksi; SQLite untuk pengembangan dan pengujian lokal.
- Alembic untuk migrasi.
- Argon2 + JWT HS256; TOTP opsional.
- python-docx untuk laporan DOCX; PDF memerlukan LibreOffice.

Model data relasional meliputi users, engagements, engagement_members, findings, evidence, retests, finding_templates, audit_log, note_templates, notes, note_versions, dan report_templates.

## Menjalankan lokal dengan Docker

    docker compose up -d --build

Buka http://127.0.0.1:8000. Kredensial awal harus dikelola secara aman dan segera dirotasi setelah login. Jangan menyalin kredensial awal atau secret ke dokumentasi, issue, atau commit.

### Pengembangan dan pengujian

    cd backend
    pip install -r requirements-dev.txt
    SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))") ADMIN_PASSWORD='Ganti-Ini-123' uvicorn app.main:app --reload
    pytest --cov=app --cov-fail-under=70
    TEST_DATABASE_URL='postgresql+psycopg://user:pw@localhost/db' pytest
    ruff check app tests && bandit -q -r app && pip-audit -r requirements.txt
    cd ../e2e && npm test

## Vercel

Production menggunakan PostgreSQL persisten. SQLite tidak didukung untuk data production pada Vercel. Variabel yang relevan (nilai disimpan di Vercel, bukan Git):

- DATABASE_URL: PostgreSQL persisten.
- SECRET_KEY: secret acak minimal 32 karakter.
- ADMIN_PASSWORD: password awal minimal 12 karakter.
- EVIDENCE_IN_DB=1: bukti disimpan sebagai BLOB di PostgreSQL.
- ENABLE_PDF=0: PDF nonaktif pada Vercel; gunakan DOCX.
- MAX_UPLOAD_MB=4: batas upload disesuaikan dengan batas request Function.
- DATA_DIR=/tmp/scopeline: hanya untuk data sementara.
- ENABLE_DOCS=0: dokumentasi API nonaktif secara default.

Aplikasi menolak startup jika konfigurasi wajib untuk lingkungan Vercel tidak terpenuhi. Jangan pernah memasukkan nilai secret ke Git.

### Status deployment

Alias produksi: https://scopeline-six.vercel.app

Deployment Production terbaru yang diperiksa berstatus **READY** pada commit f49736200295fc33e63030d178dfb85e35bbd25c. GitHub Actions CI pada commit yang sama lulus, termasuk coverage gate 70%, PostgreSQL tests, E2E, dan Docker build. Namun, status deployment READY bukan bukti health check atau acceptance test runtime telah lulus. Lihat [docs/DEPLOYMENT-STATUS.md](docs/DEPLOYMENT-STATUS.md) untuk batas klaim dan langkah verifikasi.

## Batasan yang diketahui

- Email reminder tenggat remediasi belum diimplementasikan.
- MFA TOTP tersedia tetapi opt-in.
- Rate limit IP in-memory per proses; bukan distributed.
- Enkripsi at-rest bukti bergantung konfigurasi provider database.
- PDF hanya dapat diekspor di lingkungan yang menyediakan LibreOffice; nonaktif di Vercel.
- Backup, restore, retensi, dan verifikasi runtime produksi perlu prosedur dan bukti tersendiri.
