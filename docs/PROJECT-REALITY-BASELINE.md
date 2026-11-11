# Baseline Realitas Proyek SCOPELINE (berdasarkan source code)

**Versi acuan:** branch main, commit f49736200295fc33e63030d178dfb85e35bbd25c (11 November 2026).  
**Sumber utama:** implementasi pada backend/app/, backend/tests/, e2e/, konfigurasi deployment, serta hasil CI. README dan dokumen analisis lama bukan pengganti pemeriksaan source code.

## 1. Definisi produk dan batas lingkup

SCOPELINE adalah aplikasi web untuk mengelola administrasi dan dokumentasi engagement penetration testing: otorisasi, ruang lingkup, Rules of Engagement (RoE), temuan, bukti, penilaian CVSS, review, retest, catatan teknis, dan laporan.

SCOPELINE **bukan** alat pemindai kerentanan, eksploitasi, atau otomasi serangan. Aplikasi tidak menjalankan pengujian ofensif terhadap target. Pengujian dilakukan oleh personel yang berwenang; SCOPELINE mencatat proses dan hasilnya. Data demo/pengujian harus fiktif atau digunakan dengan izin tertulis.

### Kapabilitas yang benar-benar terdapat di source

| Area | Implementasi |
|---|---|
| Akun dan autentikasi | CRUD pengguna oleh Admin; login; perubahan/reset kata sandi; Argon2; JWT HS256; pencabutan token melalui token_version; MFA TOTP opsional per akun; penguncian akun setelah kegagalan login |
| Otorisasi | Lima role: Admin, Lead, Tester/Penguji, Reviewer/Peninjau, Technical Writer/Writer; pemeriksaan role dan keanggotaan engagement di server |
| Engagement | Nama, klien, scope, tanggal mulai/selesai, RoE, anggota, status draft/active/completed |
| Gate RoE | Engagement tidak dapat diaktifkan sebelum scope dan RoE disetujui; perubahan scope/RoE membatalkan persetujuan dan mengembalikan engagement aktif ke draft |
| Temuan | Nomor temuan per engagement, deskripsi, dampak, rekomendasi, CVSS v3.1 dan severity yang dihitung server, status perbaikan, tenggat |
| Bukti | Upload, validasi ekstensi dan signature/isi, batas ukuran, nama penyimpanan acak, unduh dan hapus; bukti retest ditautkan ke ronde |
| Review | Draft → In Review → Approved / Changes Requested; aturan empat mata mencegah pembuat menyetujui temuan sendiri |
| Retest | Ronde berurutan dengan hasil passed/failed/partial, tanggal, penguji, catatan, dan bukti |
| Laporan | DOCX pretest/retest, templat DOCX berversi, validasi placeholder, aktivasi/arsip dan aktivasi ulang versi lama; laporan final hanya memuat temuan approved secara default |
| Perbandingan | Perbandingan pretest/retest: closed, still open, unverified, new |
| Catatan | Catatan tim dan pribadi berbasis Markdown, templat, pratinjau aman, versi dan deteksi konflik versi |
| Operasional | Dasbor, log audit, pustaka templat temuan, impor CSV |

**Keputusan versi CVSS:** implementasi saat ini secara eksplisit memvalidasi prefiks `CVSS:3.1` dan menghitung Base Score CVSS v3.1 dalam fungsi terpisah di `backend/app/cvss.py`; endpoint kalkulasi `POST /api/cvss/calc` dan pembuatan/perubahan temuan memakai fungsi tersebut. Karena itu dokumen *as-built* harus menyebut v3.1, bukan mengklaim v4.0. Alasan mempertahankan v3.1 untuk baseline ini adalah kesesuaian langsung dengan format vektor, rumus, severity mapping, data uji, dan laporan yang sudah diimplementasikan. CVSS v4.0 adalah kandidat peningkatan terencana; migrasi memerlukan parser, rumus, skema input, UI, fixture/test pembanding, dan label versi di laporan yang konsisten. Jangan mengganti label versi menjadi 4.0 hanya pada dokumen.

Rincian implementasi dapat dilacak pada backend/app/models.py, backend/app/routers/, backend/app/reporting.py, backend/app/notes_service.py, dan pengujian terkait.

## 2. Alur bisnis aktual

1. Admin membuat akun dan menetapkan role.
2. Admin/Lead membuat engagement, mengisi scope dan RoE, lalu menetapkan anggota.
3. Admin/Lead menyetujui RoE. Hanya setelah itu engagement dapat berpindah dari draft ke active.
4. Tester membuat temuan; skor CVSS dihitung di backend. Tester mengunggah bukti dan mencatat perubahan perbaikan.
5. Pembuat mengajukan temuan untuk review. Reviewer, Lead, atau Admin yang bukan pembuat dapat menyetujui atau meminta perubahan.
6. Perubahan isi temuan yang sudah diajukan/disetujui mengembalikan status review ke draft agar ditinjau ulang.
7. Tester mencatat ronde retest; hanya hasil retest passed yang menghasilkan status retest_passed.
8. Pengguna yang berhak menghasilkan laporan DOCX pretest atau retest. Laporan final menyertakan temuan approved; opsi menyertakan temuan lain menandai dokumen sebagai DRAF.

Perubahan scope/RoE setelah disetujui adalah perubahan kontrol penting: persetujuan dihapus dan engagement aktif dijeda. Ini harus dijelaskan sebagai kontrol tata kelola, bukan sekadar perubahan status UI.

## 3. Role dan batas akses

Lima role pada source adalah role aplikasi yang benar-benar diberlakukan oleh backend. Istilah organisasi pada rancangan Bilal dapat dipakai sebagai label/tanggung jawab proyek, tetapi jangan mengubah nama role di dokumen tanpa menyelaraskan matriks izin dan kode. Pemetaan kerja yang paling dekat adalah: Admin System → Admin; Project Management → Lead; Engineer-Red Team → Tester/Penguji; Engineer-Lead of Technical Writer → Technical Writer; Engineer-Head Offensive Security → Reviewer hanya jika tanggung jawab utamanya adalah quality gate/review. Pemetaan terakhir ini adalah usulan interpretasi, bukan nama role atau struktur organisasi yang sudah dibuktikan oleh kode. Jika Head Offensive Security perlu kewenangan mengelola engagement, peran Reviewer tidak ekuivalen dengan Lead dan matriks izin harus diputuskan ulang.


| Role kode | Nama di UI/dokumen | Tanggung jawab dan batas penting |
|---|---|---|
| admin | Admin | Pengguna, seluruh kewenangan Lead, template laporan/catatan, audit |
| lead | Lead | Engagement, scope/RoE, anggota, templat, review, audit |
| tester | Penguji | Temuan, CVSS, bukti, CSV, perbaikan, retest, catatan; hanya engagement yang ditugaskan |
| reviewer | Peninjau | Review temuan dan akses baca sesuai engagement yang ditugaskan |
| writer | Technical Writer | Menyunting teks narasi temuan dan template laporan; tidak dapat mengubah CVSS/status/bukti dan tidak dapat melihat/mengunduh bukti mentah |

Catatan: kode role di database adalah writer, bukan technical_writer. Istilah yang konsisten untuk dokumen dan UI adalah **Technical Writer**. Reviewer/Lead/Admin tunduk pada aturan empat mata untuk persetujuan temuan.

Matriks izin rinci tetap berada di [PERAN-DAN-IZIN.md](PERAN-DAN-IZIN.md).

### Dasbor dan kontrol akses

Route dasbor tersedia untuk kelima role. Dokumen kebutuhan boleh menetapkan FR dasbor sebagai Must karena merupakan kebutuhan produk, tetapi kriteria penerimaannya perlu memeriksa bukan hanya respons 401/403, melainkan juga bahwa data/aksi yang ditampilkan mengikuti role dan keanggotaan engagement. Matriks rinci ada di [PERAN-DAN-IZIN.md](PERAN-DAN-IZIN.md).

## 4. Arsitektur dan teknologi aktual

- **Backend:** Python 3.12, FastAPI, Pydantic, SQLAlchemy.
- **Frontend:** HTML, CSS, JavaScript vanilla tanpa framework dan tanpa build step; frontend statis dilayani aplikasi FastAPI.
- **Data:** PostgreSQL pada deployment Vercel/produksi; SQLite untuk pengembangan dan pengujian lokal.
- **Migrasi:** Alembic, dijalankan pada startup. Migrasi PostgreSQL memakai advisory lock untuk menghindari migrasi serentak saat cold start.
- **Autentikasi:** Argon2 password hashing; JWT HS256 melalui header Bearer; token memiliki masa berlaku dan versi pencabutan.
- **MFA:** TOTP dapat diaktifkan oleh pengguna; MFA tidak dipaksakan otomatis untuk seluruh akun.
- **Laporan:** python-docx untuk DOCX; konversi PDF menggunakan LibreOffice/soffice bila tersedia.
- **Deployment:** Vercel Python/FastAPI runtime; Docker Compose untuk pengembangan/hosting mandiri.
- **CI:** GitHub Actions menjalankan Ruff, Bandit, pip-audit, pytest dengan coverage gate 70%, pytest terhadap PostgreSQL, E2E UI, dan Docker build.

### Model data yang benar-benar digunakan

Model SQLAlchemy mencakup users, engagements, engagement_members, findings, evidence, retests, finding_templates, audit_log, note_templates, notes, note_versions, dan report_templates. Relasi anggota, bukti, ronde retest, catatan, serta template bukan lagi array JSON seperti rancangan v1.0. Bukti dan dokumen template dapat disimpan sebagai BLOB di database ketika EVIDENCE_IN_DB=1.

## 5. Keamanan dan batasan yang harus dinyatakan

Kontrol yang tampak di kode:
- Argon2 untuk hash kata sandi; kebijakan minimum 10 karakter pada skema API.
- JWT HS256, expiry, dan invalidasi token saat password/role/status akun berubah.
- MFA TOTP opsional.
- Penguncian akun setelah lima kegagalan secara default; rate limit IP juga diterapkan dalam memori per proses.
- RBAC dan pemeriksaan akses objek berdasarkan keanggotaan engagement.
- Validasi Pydantic, CVSS server-side, ORM SQLAlchemy, dan sanitasi/render Markdown tanpa HTML mentah.
- CSP, X-Frame-Options, nosniff, Referrer-Policy, serta no-store untuk endpoint API.
- Upload allowlist, validasi isi dasar, ukuran, dan nama acak.
- Audit event untuk aktivitas penting.

Batasan/risiko yang tetap perlu diungkap:
- Rate limit IP disimpan dalam memori proses; tidak terdistribusi lintas worker/instance. Penguncian akun disimpan di database.
- MFA TOTP tersedia tetapi bersifat opt-in; kebijakan organisasi perlu menentukan apakah wajib.
- Tidak ada bukti enkripsi aplikasi end-to-end/field-level untuk BLOB bukti; perlindungan at-rest bergantung pada konfigurasi dan fitur penyedia PostgreSQL/penyimpanan.
- TLS bergantung pada terminasi TLS di platform/proxy deployment dan tetap harus diverifikasi pada domain aktif.
- Checklist ASVS adalah self-assessment, bukan sertifikasi atau audit independen. Pemeriksaan manual yang ditandai perlu verifikasi tidak boleh diklaim selesai.
- Notifikasi email tenggat remediasi belum diimplementasikan.

## 6. Perbedaan lingkungan lokal dan Vercel

| Aspek | Lokal/Docker | Vercel |
|---|---|---|
| Database | SQLite default untuk dev; PostgreSQL didukung | PostgreSQL persisten wajib; aplikasi gagal startup bila DATABASE_URL kosong/SQLite |
| Penyimpanan bukti | Volume/direktori data bila EVIDENCE_IN_DB=0; dapat memakai DB | EVIDENCE_IN_DB=1 wajib agar tidak bergantung pada filesystem sementara |
| Batas upload bukti | Default 5 MB | Maksimum dikonfigurasi 4 MB |
| PDF | Dapat diaktifkan bila LibreOffice tersedia | Dinonaktifkan (ENABLE_PDF=0); DOCX tetap tersedia |
| Data directory | Direktori data persisten sesuai deployment | /tmp/scopeline hanya untuk file sementara, bukan data persisten |

## 7. Status pengujian dan deployment yang dapat dibuktikan

Pada commit f49736200295fc33e63030d178dfb85e35bbd25c, GitHub Actions CI run #59 berstatus **success** pada 11 November 2026. Workflow yang berhasil mencakup:
- Ruff, Bandit, pip-audit;
- pytest SQLite dengan --cov-fail-under=70;
- pytest menggunakan PostgreSQL 16;
- E2E UI;
- Docker Compose build.

Ini membuktikan gerbang CI pada commit tersebut lulus; bukan bukti bahwa semua kontrol ASVS telah diaudit manual atau bahwa deployment produksi telah menjalani uji penerimaan end-to-end.

Metadata Vercel menunjukkan deployment Production berstatus **READY**, terhubung ke branch main pada commit yang sama, dengan alias scopeline-six.vercel.app. Metadata environment Vercel menunjukkan DATABASE_URL tersedia untuk Production dan EVIDENCE_IN_DB=1, ENABLE_PDF=0, MAX_UPLOAD_MB=4 dikonfigurasi. Nilai rahasia tidak dicantumkan dalam dokumentasi.

Status READY hanya menunjukkan proses deployment selesai. Pemeriksaan runtime /api/health, login, alur engagement, upload bukti, review, retest, dan ekspor DOCX harus dicatat sebagai terverifikasi hanya setelah pengujian langsung dilakukan. Pada pemeriksaan ini tidak ditemukan log runtime dalam jendela 50 menit terakhir; hal itu tidak membuktikan aplikasi gagal maupun berhasil.

Lihat [DEPLOYMENT-STATUS.md](DEPLOYMENT-STATUS.md) untuk catatan deployment.

## 8. Penyesuaian terhadap rencana PM

Proposal awal dan rencana 24 minggu/6 sprint adalah **baseline perencanaan**, bukan bukti durasi aktual. Laporan status proyek harus membedakan:
- **Direncanakan:** target, prioritas MoSCoW, estimasi, anggaran, dan milestone dalam proposal.
- **Diimplementasikan:** fitur yang dapat ditelusuri pada source code.
- **Lulus CI:** fitur/kontrol yang tercakup pada test suite yang lulus.
- **Terverifikasi di produksi:** hanya alur yang sudah diuji terhadap deployment dan database produksi.

Prioritas MoSCoW awal tetap berguna sebagai keputusan pengendalian lingkup, tetapi label prioritas bukan status implementasi. Saat ini beberapa fitur yang dahulu direncanakan sebagai Should/Could (review, retest, dashboard, audit, impor CSV, template, catatan, Technical Writer) telah menjadi bagian source. Notifikasi email masih belum tersedia. PDF tersedia hanya pada lingkungan yang memiliki LibreOffice, bukan pada runtime Vercel.

Peran **Project Manager** berfokus pada nilai produk, ruang lingkup, prioritas, jadwal, risiko, koordinasi, kriteria penerimaan, dan pelaporan status. Peran **Analis Program** berfokus pada kebutuhan teknis, arsitektur, model data, API, implementasi, dan bukti uji. Makalah PM harus menjelaskan keputusan pengelolaan dan dampaknya; jangan menyalin makalah teknis Analis Program sebagai narasi PM.

## 9. Ketidaksesuaian versi lama yang perlu dianggap superseded

- SQLite + relasi JSON sebagai database utama → sudah digantikan model SQLAlchemy relasional; SQLite hanya dev/test, PostgreSQL untuk produksi.
- Token HMAC-SHA256/scrypt → implementasi saat ini memakai JWT HS256 dan Argon2.
- Empat role → implementasi saat ini memiliki lima role termasuk Technical Writer.
- MFA belum ada → TOTP tersedia, tetapi opsional.
- Retest/dashboard/audit hanya rencana → modul dan route tersedia serta tercakup dalam test.
- Tidak ada endpoint unduh bukti → GET /api/evidence/{id}/download tersedia; Technical Writer ditolak.
- DOCX/PDF selalu dianggap tersedia → DOCX disiapkan; PDF bergantung LibreOffice dan dinonaktifkan di Vercel.
- Database produksi belum terhubung (catatan 10 November) → sudah ada variabel DATABASE_URL di environment Production per pemeriksaan 11 November; koneksi runtime tetap harus diuji.
- Target coverage 70% belum tercapai → workflow CI sekarang memiliki gate 70% dan run terbaru sukses.

Dokumen Program Analysis v1.1 DOCX/PDF yang tersimpan di repository perlu ditinjau dan diterbitkan ulang bila narasinya belum mencerminkan baseline ini. Jangan menyebut dokumen biner tersebut sebagai status terkini sebelum sinkronisasi dilakukan.
