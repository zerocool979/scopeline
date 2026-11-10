# SCOPELINE

Platform manajemen engagement dan pelaporan penetration testing berbasis web (STMIK Tazkia).

Dokumen teknis Program Analysis berbasis implementasi v1.1: [`docs/Program-Analysis-SCOPELINE-v1.1.pdf`](docs/Program-Analysis-SCOPELINE-v1.1.pdf) dan [`docs/Program-Analysis-SCOPELINE-v1.1.docx`](docs/Program-Analysis-SCOPELINE-v1.1.docx). Status deployment aktual: [`docs/DEPLOYMENT-STATUS.md`](docs/DEPLOYMENT-STATUS.md).
SCOPELINE **hanya** alat manajemen & pelaporan: tidak memindai, tidak mengeksploitasi, tidak menjalankan serangan.
Seluruh pengembangan dan pengujian memakai **data fiktif**.

## Menjalankan (satu perintah)

```bash
docker compose up -d --build
docker compose logs app | grep ADMIN      # kata sandi admin awal (bila ADMIN_PASSWORD tidak diatur)
```

Buka <http://127.0.0.1:8000>, masuk sebagai `admin`, lalu ganti kata sandi (menu *Akun*) dan aktifkan MFA.
Untuk staging, letakkan reverse proxy TLS (Caddy/Nginx + Let's Encrypt) di depan aplikasi dan atur `BIND_ADDR`/`PORT`
(lihat `.env.example`). `SECRET_KEY` dibuat otomatis dan disimpan pada volume `/data` bila tidak diisi.

### Pengembangan lokal (tanpa Docker)

```bash
cd backend
pip install -r requirements-dev.txt
SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))") ADMIN_PASSWORD='Ganti-Ini-123' \
  uvicorn app.main:app --reload          # SQLite di ./data; PDF butuh LibreOffice (soffice)
pytest --cov=app                          # suite unit/API (SQLite)
TEST_DATABASE_URL=postgresql+psycopg://user:pw@localhost/db pytest   # suite yang sama di PostgreSQL
cd ../e2e && npm test                     # uji UI end-to-end (jsdom + server sungguhan), butuh Node ≥ 18
ruff check app tests && bandit -r app && pip-audit -r requirements.txt
```

## Peran & izin

Matriks lengkap: [`docs/PERAN-DAN-IZIN.md`](docs/PERAN-DAN-IZIN.md).

| Peran | Kegunaan | Hak utama |
|---|---|---|
| Admin | Pengelola sistem | Kelola pengguna; seluruh hak Lead; boleh mengunggah templat laporan & catatan |
| Lead | Pemimpin tim pentest | Buat/ubah engagement, tetapkan anggota, **setujui RoE**, kelola templat (laporan, catatan, temuan), log audit, hapus temuan |
| Penguji | Pelaksana pengujian | Catat temuan, bukti, **ronde retest**, impor CSV, catatan Markdown — hanya pada engagement yang ditugaskan |
| Peninjau | Reviewer / QA | **Setujui atau minta perubahan** atas temuan; baca temuan, catatan tim, dan ekspor laporan |
| Technical Writer | Penyusun laporan | Sunting **teks** temuan, kelola templat laporan pretest/retest; **tanpa** akses bukti mentah, CVSS, dan catatan pentester |

## Pemetaan ke proposal

| Fitur proposal | Status |
|---|---|
| Must: autentikasi, pengguna, peran (RBAC); hash Argon2, pembatasan percobaan, MFA TOTP | ✅ |
| Must: engagement (klien, ruang lingkup, jendela waktu, RoE, status); pengujian hanya setelah RoE disetujui | ✅ (mengubah ruang lingkup/RoE membatalkan persetujuan & menjeda pengujian) |
| Must: temuan + bukti unggahan + pustaka templat temuan | ✅ |
| Must: kalkulator CVSS v3.1 (dihitung server dari vektor) | ✅ (diuji terhadap skor referensi FIRST) |
| Must: ekspor DOCX & PDF dari templat yang dapat diganti Lead | ✅ DOCX; PDF hanya pada lingkungan yang menyediakan LibreOffice. PDF dinonaktifkan pada Vercel |
| Should: pelacakan perbaikan & retest, dasbor, log audit | ✅ |
| Could: impor CSV | ✅ |
| Could: notifikasi email tenggat remediasi | ⏳ belum (tenggat tersimpan & ditandai "lewat tenggat" di dasbor) |
| Won't: pemindaian, eksploitasi, AI | — sengaja tidak ada |

## Gelombang 1 (v1.1)

| Fitur | Ringkasan |
|---|---|
| **Migrasi Alembic** | Skema berversi; database PostgreSQL lama (v1.0) diadopsi melalui migrasi tanpa kehilangan data |
| **Templat laporan pretest & retest berversi** | Unggah DOCX per jenis → versi draf → validasi placeholder → aktifkan; rollback ke versi lama; laporan mencatat versi templat. Penanda `{{content}}` menentukan posisi isi laporan |
| **Templat catatan pentester (.md)** | Admin/Lead unggah templat Markdown (ada default); otomatis menjadi catatan tim per engagement dan catatan pribadi per penguji |
| **Editor catatan Markdown** | Pratinjau aman (tanpa HTML mentah), riwayat versi (maks. 100) + muat versi lama, deteksi konflik penyuntingan, ekspor `.md` |
| **Alur review temuan** | Draf → Menunggu review → Disetujui / Perlu perubahan, aturan empat mata; mengubah isi mereset ke Draf; **laporan final hanya memuat temuan Disetujui** (opsi "draf" ditandai DRAF) |
| **Ronde retest** | Retest #1, #2, … lengkap dengan tanggal, penguji, hasil (lulus/gagal/sebagian), catatan, dan bukti per ronde; "lulus retest" hanya dihasilkan ronde retest |
| **Perbandingan pretest vs retest** | Tertutup / masih terbuka / diperbaiki-belum-diverifikasi / baru; ditampilkan di UI dan menjadi isi **laporan retest** |
| **Peran Technical Writer** | Lihat tabel peran |
| **Uji end-to-end UI** | `e2e/`: 13 langkah lintas peran, termasuk anti-XSS pada Markdown dan judul temuan |

**Upgrade dari v1.0:** migrasi Alembic berjalan saat aplikasi dimulai. Temuan lama ditandai *Disetujui* agar laporan lama tidak berubah;
templat laporan tunggal v1.0 (bila ada di disk) diimpor sebagai *pretest v1 aktif*. Buat backup database sebelum melakukan upgrade.
Templat laporan, catatan, dan bukti (saat `EVIDENCE_IN_DB=1`) disimpan **di database**, sehingga tidak bergantung pada filesystem instance.

## Catatan desain

- Backend FastAPI + SQLAlchemy; PostgreSQL (Compose) atau SQLite (dev/tes). Frontend: JavaScript tanpa framework & tanpa build step
  (DOM dibangun dengan `textContent`; CSP ketat tanpa skrip/gaya inline). Proposal mengizinkan penyesuaian tumpukan teknologi.
- Token Bearer (JWT) di `sessionStorage` dan dikirim lewat header `Authorization`, bukan cookie → tidak rentan CSRF; token dicabut saat sandi/peran berubah.
- Skema dikelola **Alembic** (`backend/app/migrations`); migrasi dijalankan otomatis saat aplikasi start. Perubahan skema baru: `cd backend && alembic revision --autogenerate -m "..."`.
- Pada Docker lokal, bukti dapat disimpan pada volume `/data/evidence` dengan nama acak. Untuk Vercel, `EVIDENCE_IN_DB=1` menyimpan bukti sebagai BLOB di PostgreSQL; **enkripsi at-rest, backup dan retensi mengikuti konfigurasi provider database**.
- Lihat `docs/ASVS-L1-checklist.md` untuk pemeriksaan mandiri keamanan.


## Deploy di Vercel (FastAPI)

Project menggunakan satu aplikasi FastAPI untuk melayani API dan static frontend HTML/JavaScript dari `backend/app/static/`.
Vercel mendeteksi FastAPI melalui Python runtime; entrypoint khusus ditetapkan di `pyproject.toml` sebagai `backend.app.main:app`.

**Database production:** aplikasi memerlukan PostgreSQL persisten. SQLite hanya untuk pengembangan dan pengujian lokal; jangan gunakan SQLite di Vercel.
Vercel Postgres lama sudah digantikan oleh integrasi database melalui Vercel Marketplace. Provision database PostgreSQL dari Marketplace Vercel dan hubungkan ke project SCOPELINE.

### Environment Variables

Atur variabel berikut pada Vercel Project Settings → Environment Variables. Jangan menyimpan nilainya ke Git.

| Variable | Ketentuan |
|---|---|
| `DATABASE_URL` | Connection string PostgreSQL persisten khusus SCOPELINE |
| `SECRET_KEY` | Secret acak minimal 32 karakter; sama untuk semua environment yang berbagi sesi |
| `ADMIN_USERNAME` | Username admin bootstrap (default `admin`) |
| `ADMIN_PASSWORD` | Password awal minimal 12 karakter |
| `DATA_DIR` | `/tmp/scopeline` (sementara, bukan penyimpanan persisten) |
| `EVIDENCE_IN_DB` | `1` agar bukti disimpan sebagai BLOB di PostgreSQL |
| `ENABLE_PDF` | `0` di Vercel; LibreOffice tidak disediakan oleh Python runtime |
| `MAX_UPLOAD_MB` | Maksimal `4` untuk mengantisipasi batas body Function 4.5 MB |
| `ENABLE_DOCS` | `0` secara default; aktifkan hanya untuk debugging terkontrol |

Aplikasi akan **gagal tertutup** bila `DATABASE_URL` kosong/SQLite, `SECRET_KEY` terlalu pendek, `ADMIN_PASSWORD` tidak memenuhi syarat,
`EVIDENCE_IN_DB` bukan `1`, atau `ENABLE_PDF` masih aktif. Ini disengaja agar aplikasi tidak berjalan dengan penyimpanan yang tidak persisten.

Migrasi Alembic dijalankan saat startup dan dilindungi PostgreSQL advisory lock untuk mencegah migrasi serentak ketika beberapa Function melakukan cold start.
Jangan hubungkan database production OLION atau database milik aplikasi lain.

### Alur deployment

1. Buat repository GitHub `zerocool979/scopeline` dari source tree ini.
2. Import repository tersebut ke Vercel sebagai project `scopeline` (framework FastAPI; root directory `/`).
3. Provision PostgreSQL dari Vercel Marketplace dan hubungkan ke project.
4. Pasang environment variables di atas pada Production dan Preview sesuai kebijakan.
5. Jalankan deployment, lalu periksa `GET /api/health`, login admin, MFA, RoE, temuan, bukti, retest, dan ekspor DOCX.
6. Aktifkan domain yang tersedia. Alias `*.vercel.app` yang dimiliki project akan dibuat otomatis.

### Batasan deployment Vercel

- Request body/response body Function dibatasi 4.5 MB; upload bukti diturunkan ke 4 MB.
- PDF tidak diaktifkan pada runtime Vercel; DOCX tetap tersedia. PDF memerlukan lingkungan dengan LibreOffice.
- Filesystem `/tmp` bersifat sementara. Bukti dan template tidak boleh disimpan hanya di filesystem.
- Backup, retensi, point-in-time recovery, pemantauan, dan pembatasan akses database harus ditetapkan sebelum data operasional nyata digunakan.
- Semua data demo/pengujian harus fiktif. SCOPELINE bukan scanner dan tidak melakukan eksploitasi.

Status project Vercel yang telah disiapkan dan hambatan deployment aktual dicatat pada `docs/DEPLOYMENT-STATUS.md`.
