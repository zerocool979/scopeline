# SCOPELINE

[![CI](https://github.com/zerocool979/scopeline/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/zerocool979/scopeline/actions/workflows/ci.yml) [![License: not specified](https://img.shields.io/badge/license-not%20specified-lightgrey.svg)](#license)

> Platform manajemen engagement dan pelaporan penetration testing berbasis web.


**Proyek akademik — STMIK Tazkia**  
Status implementasi: CVSS v4.0 sudah digabung ke `main`; verifikasi CI pada commit merge sedang berjalan.

**SCOPELINE adalah sistem manajemen dan dokumentasi**, bukan vulnerability scanner, exploit framework, atau alat otomasi serangan. Seluruh data demo/pengujian harus fiktif atau digunakan dengan izin tertulis.

## Navigasi proyek

- [Rencana Manajemen Proyek (PM)](docs/PROJECT-MANAGEMENT-PLAN.md) — charter, ruang lingkup, jadwal baseline, stakeholder, RACI, risiko, mutu, dan penerimaan.
- [Program Analysis & System Design (PA)](docs/PROGRAM-ANALYSIS-DESIGN.md) — proses bisnis, FR/NFR, arsitektur, data, RBAC, CVSS, keamanan, dan acceptance test.
- [Catatan keputusan](docs/DECISIONS.md) · [Checklist rilis](docs/RELEASE-CHECKLIST.md).
- [Panduan kontribusi](CONTRIBUTING.md) · [Kebijakan keamanan](SECURITY.md) · [Kode etik](CODE_OF_CONDUCT.md) · [Changelog](CHANGELOG.md).

## Dokumen acuan

- [Baseline realitas proyek berdasarkan source code](docs/PROJECT-REALITY-BASELINE.md) — definisi produk, alur bisnis, model data, role, keamanan, batas lingkungan, bukti CI, dan ketidaksesuaian versi lama.
- [Tindak lanjut 12 komentar Bilal](docs/REVISI-KOMENTAR-BILAL.md) — keputusan revisi, rumusan FR/NFR, dan gap yang masih memerlukan persetujuan atau perubahan kode.
- [Status implementasi dan deployment](docs/DEPLOYMENT-STATUS.md) — commit, CI, Vercel, konfigurasi environment tanpa nilai rahasia, dan checklist runtime.
- [Matriks peran dan izin](docs/PERAN-DAN-IZIN.md).
- [Pemeriksaan mandiri OWASP ASVS Level 1](docs/ASVS-L1-checklist.md).

Dokumen PA dan PM di atas adalah dokumen kerja berbasis Markdown di repository. Untuk klaim *as-built*, **source code dan test pada commit yang disebut adalah acuan perilaku implementasi**; dokumen proposal tetap acuan visi dan rencana, bukan bukti fitur selesai.

## Fitur implementasi

| Area | Fitur |
|---|---|
| Autentikasi & pengguna | Argon2, JWT, pencabutan token, MFA TOTP opsional, lockout login, RBAC |
| Engagement | Scope, periode, RoE, anggota, status; pengujian terkunci sampai RoE disetujui |
| Temuan | Pencatatan, pustaka template, CVSS v4.0 server-side (CVSS-B), dengan preservasi penilaian historis v3.1, bukti |
| Review | Draft → In Review → Approved / Changes Requested; aturan empat mata |
| Retest | Ronde per temuan, hasil dan bukti, perbandingan pretest/retest |
| Laporan | DOCX pretest/retest, template DOCX berversi; laporan final hanya memuat temuan approved |
| Catatan | Catatan tim/pribadi Markdown, template, versi, deteksi konflik |
| Operasional | Dashboard, audit log, impor CSV |

### Role

Admin, Lead, Penguji (tester), Peninjau (reviewer), dan Technical Writer (writer). Project Manager (`lead`) dan Engineer-Head Offensive Security (`reviewer`) wajib menyetujui RoE dan laporan final. Admin tidak memiliki akses ke raw evidence. Engineer-Lead Technical Writer (`writer`) tidak dapat mengakses raw evidence atau mengubah CVSS/status teknis.

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

CVSS v4.0 telah digabung ke `main` melalui PR #9. CI branch PR telah lulus seluruh job; deployment Production otomatis terhubung ke `main`. Status deployment terbaru, CI, dan runtime acceptance dicatat pada [docs/DEPLOYMENT-STATUS.md](docs/DEPLOYMENT-STATUS.md). Deployment READY tidak dengan sendirinya membuktikan seluruh alur bisnis telah diterima.

## Batasan yang diketahui

- Email reminder tenggat remediasi belum diimplementasikan.
- MFA TOTP tersedia tetapi opt-in.
- Rate limit IP in-memory per proses; bukan distributed.
- Enkripsi at-rest bukti bergantung konfigurasi provider database.
- PDF hanya dapat diekspor di lingkungan yang menyediakan LibreOffice; nonaktif di Vercel.
- Backup, restore, retensi, dan verifikasi runtime produksi perlu prosedur dan bukti tersendiri.


### Versi CVSS

Kalkulator aktif menggunakan CVSS v4.0 (CVSS-B) melalui pustaka Python `cvss` 3.6 yang mendukung CVSS4. Vektor wajib menyertakan 11 Base metrics sesuai urutan FIRST; metrik Threat/Environmental/Supplemental opsional yang disediakan dipertahankan dan diproses kalkulator. Skor ditampilkan bersama vector dan nomenklatur yang mencerminkan kelompok metrik yang digunakan.

Migrasi database menandai temuan lama sebagai CVSS v3.1 tanpa menghitung ulang skor. Saat temuan lama dinilai ulang, vector/score/severity v3.1 disalin ke kolom riwayat sebelum nilai aktif diganti v4.0. Laporan DOCX menampilkan versi dan vector yang sesuai. Sumber: [FIRST CVSS v4.0 Specification](https://www.first.org/cvss/v4.0/specification-document).


## License

Lisensi repository belum ditetapkan. Sampai file `LICENSE` ditambahkan oleh pemilik proyek, jangan mengasumsikan kode ini tersedia di bawah lisensi open-source tertentu.

## Kontribusi dan keamanan

Baca [CONTRIBUTING.md](CONTRIBUTING.md) sebelum mengajukan perubahan. Untuk pelaporan kerentanan, ikuti [SECURITY.md](SECURITY.md); jangan memublikasikan detail eksploit atau data sensitif pada issue publik.
