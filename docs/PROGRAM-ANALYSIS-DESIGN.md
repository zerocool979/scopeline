# Dokumen Program Analysis dan Perancangan Sistem SCOPELINE

**Dokumen:** Program Analysis (PA) — Analisis Kebutuhan dan Perancangan Sistem  
**Versi:** 1.1  
**Tanggal acuan:** 11 November 2026  
**Status:** Dokumen analisis yang diselaraskan dengan implementasi pada branch `main`; bukan sertifikat keamanan atau bukti seluruh acceptance test produksi telah lulus.  
**Produk:** Platform Manajemen Engagement dan Pelaporan Penetration Testing Berbasis Web  
**Repository:** https://github.com/zerocool979/scopeline  
**Deployment:** https://scopeline-six.vercel.app

---

## 1. Pendahuluan

### 1.1 Latar belakang

Kegiatan penetration testing memerlukan pengelolaan otorisasi, ruang lingkup, Rules of Engagement (RoE), personel, temuan, bukti, penilaian risiko, review, retest, dan laporan. Jika artefak tersebut tersebar, tim berisiko kehilangan keterlacakan perubahan, ketepatan status perbaikan, dan konsistensi laporan.

SCOPELINE dirancang sebagai aplikasi web untuk memusatkan administrasi engagement dan dokumentasi hasil penetration testing. Aplikasi mendukung alur kerja tim, bukan menggantikan keahlian penguji.

### 1.2 Tujuan sistem

1. Mencatat engagement dan otorisasi pengujian.
2. Mengendalikan scope, RoE, anggota, dan status engagement.
3. Mencatat temuan, bukti, dampak, rekomendasi, dan tenggat.
4. Menilai risiko menggunakan kalkulator CVSS v4.0 di sisi server.
5. Menyediakan alur review dengan prinsip empat mata.
6. Mencatat retest dan membandingkan hasil sebelum/sesudah perbaikan.
7. Menghasilkan laporan DOCX yang dapat ditelusuri.
8. Menyediakan dashboard, audit log, dan dukungan dokumentasi tim.

### 1.3 Batas sistem

SCOPELINE adalah sistem manajemen dan pelaporan. SCOPELINE **bukan** vulnerability scanner, exploit framework, attack automation, atau alat untuk menjalankan payload terhadap target. Pengujian dilakukan oleh personel yang memiliki otorisasi tertulis; aplikasi mencatat proses dan hasilnya.

### 1.4 Pengguna dan pemangku kepentingan

- Admin System — role aplikasi Admin.
- Project Management — role aplikasi Lead.
- Engineer-Head Offensive Security — role aplikasi Reviewer/Peninjau.
- Engineer-Lead of Technical Writer — role aplikasi Technical Writer/Writer.
- Engineer-Red Team — role aplikasi Tester/Penguji.
- Project Manager — tata kelola scope, jadwal, risiko, stakeholder, perubahan, komunikasi, dan acceptance.
- Program Analyst — analisis proses, kebutuhan, model data, kontrak API, dan dokumentasi rancangan.
- Tim teknis — implementasi, pengujian, CI, dan deployment.
- Stakeholder akademik/pemilik data — pemberi masukan dan persetujuan sesuai kewenangannya.

Pemetaan jabatan ke role adalah pemetaan nomenklatur. Hak akses tetap mengikuti kode role dan implementasi RBAC. Reviewer tidak otomatis memiliki kewenangan Lead untuk mengelola engagement, anggota, scope, atau RoE.

## 2. Analisis proses bisnis

### 2.1 Alur utama engagement

1. Admin menyiapkan akun dan role pengguna.
2. Lead membuat engagement, menetapkan scope, periode, RoE, dan anggota.
3. Scope dan RoE harus disetujui sebelum engagement diaktifkan.
4. Tester yang ditugaskan melakukan pengujian di luar aplikasi sesuai otorisasi, lalu mencatat temuan dan bukti ke SCOPELINE.
5. Sistem memvalidasi data dan menghitung CVSS v4.0 dari vector yang dipilih.
6. Temuan diajukan untuk review.
7. Reviewer melakukan approval atau meminta perubahan. Pembuat temuan tidak dapat menyetujui temuannya sendiri.
8. Setelah perbaikan, Tester mencatat ronde retest dan bukti hasilnya.
9. Tim menghasilkan laporan DOCX. Laporan final secara default hanya berisi temuan yang disetujui.
10. Aktivitas penting dicatat pada audit log.

### 2.2 Aturan proses utama

- Engagement tidak dapat aktif sebelum scope dan RoE disetujui.
- Perubahan scope atau RoE membatalkan persetujuan terkait dan mengembalikan engagement aktif ke status draft.
- Alur review: Draft → In Review → Approved atau Changes Requested.
- Pembuat temuan tidak dapat menyetujui temuan sendiri (four-eyes principle).
- Perubahan pada temuan yang telah diajukan/disetujui mengembalikan status review ke Draft.
- Laporan final hanya menyertakan temuan Approved; opsi menyertakan temuan belum disetujui harus menandai dokumen sebagai DRAFT.
- Technical Writer dapat mengelola narasi dan template laporan, tetapi tidak memiliki akses ke bukti mentah.

## 3. Kebutuhan fungsional

Prioritas Must/Should/Could/Won't adalah baseline kebutuhan. Kolom status membedakan fungsi yang ada di source dari kriteria yang masih perlu dibuktikan melalui acceptance test.

| ID | Kebutuhan | Prioritas | Kriteria penerimaan | Status implementasi |
|---|---|---|---|---|
| FR-01 | Autentikasi, pengelolaan akun, dan RBAC untuk Admin, Lead, Tester, Reviewer, dan Technical Writer. | Must | Request tanpa token pada endpoint terlindungi menghasilkan 401; role tanpa izin menghasilkan 403; Admin dapat mengelola akun; token lama tidak berlaku setelah perubahan kredensial/role/status. | Login, Argon2, JWT, token version, dan lima role ada. Matriks uji endpoint/role perlu dipastikan lengkap. |
| FR-02 | Pengelolaan engagement, scope, RoE, anggota, periode, dan status. | Must | Engagement tidak aktif sebelum scope/RoE disetujui; perubahan scope/RoE membatalkan approval. | Ada di backend. |
| FR-03 | Pencatatan temuan dan bukti. | Must | Temuan tersimpan dengan deskripsi, dampak, rekomendasi, status, tenggat, serta bukti yang tervalidasi dan dibatasi aksesnya. | Ada di backend dan UI. |
| FR-04 | Workflow review temuan. | Must | Draft dapat diajukan; Reviewer dapat approve/request changes; pembuat tidak dapat approve sendiri; perubahan temuan mereset review. | Ada; prinsip empat mata diterapkan. |
| FR-05 | Kalkulasi CVSS v4.0 (CVSS-B) dari vector yang divalidasi di server. | Must | Vector valid dihitung sesuai spesifikasi FIRST; vector invalid/salah versi ditolak; hasil kalkulasi konsisten antara endpoint kalkulasi dan penyimpanan temuan; histori v3.1 tidak hilang. | CVSS v4.0 aktif di main; v3.1 dipertahankan sebagai histori. |
| FR-06 | Pencatatan retest per ronde. | Should | Setiap ronde memiliki hasil, catatan, waktu, dan bukti yang dapat ditelusuri; hasil pretest/retest dapat dibandingkan. | Ada di backend/UI. |
| FR-07 | Pembuatan laporan DOCX. | Must | Template tervalidasi; laporan pretest/retest dibuat; laporan final hanya berisi temuan Approved; metadata CVSS sesuai versi assessment. | DOCX tersedia; PDF membutuhkan LibreOffice dan nonaktif di Vercel. |
| FR-08 | Dashboard sesuai role dan engagement yang dapat diakses. | Must | Tanpa token menghasilkan 401; pengguna tanpa hak/keanggotaan tidak dapat melihat data; ringkasan tidak membocorkan engagement lain; tampilan diuji untuk kelima role. | Dashboard dan pembatasan akses tersedia; bukti uji dashboard lengkap per lima role harus dicatat. |
| FR-09 | Audit log aktivitas penting. | Should | Perubahan penting dapat ditelusuri berdasarkan aktor, waktu, objek, dan aksi. | Ada. |
| FR-10 | Impor data temuan melalui CSV. | Could | File tervalidasi dan hasil impor dilaporkan tanpa melewati validasi server. | Ada. |
| FR-11 | Catatan tim/pribadi dan version history. | Could | Catatan tersimpan sesuai akses; konflik edit dapat terdeteksi. | Ada. |
| FR-12 | Template laporan dan pustaka template temuan. | Should | Template berversi, placeholder divalidasi, dan rollback/aktivasi dibatasi role. | Ada. |

### 3.1 Catatan keputusan input CVSS

Pengguna memilih nilai metrik pada vector CVSS; server menghitung score dan severity. Tidak ada mode input angka skor final manual yang didokumentasikan sebagai fitur aktif. Jika kelak dibutuhkan penilaian manual, perubahan harus mendefinisikan sumber skor, audit trail, validasi, label laporan, serta dampak terhadap komparabilitas dan harus melalui change control.

### 3.2 Data uji

Data sintetis/fiktif adalah dataset default. Dataset UAS Pengujian Keamanan (SAWALA) hanya dapat digunakan setelah izin pemilik data/dosen, sanitasi identitas dan rahasia, dan persetujuan penggunaan artefak. Tidak ada klaim bahwa dataset SAWALA telah disetujui atau diintegrasikan.

## 4. Kebutuhan non-fungsional

| ID | Kebutuhan | Prioritas | Kriteria penerimaan / bukti | Batasan dan status |
|---|---|---|---|---|
| NFR-01 | Otorisasi role dan objek engagement. | Must | 401 tanpa token; 403 role tidak berhak; akses objek lintas engagement ditolak; uji API dan dashboard. | RBAC server-side tersedia; acceptance dashboard per role perlu dibuktikan. |
| NFR-02 | Perlindungan kredensial dan sesi. | Must | Password di-hash Argon2; JWT memiliki expiry; token diinvalidasi setelah perubahan kredensial/role/status. | Implementasi tersedia; MFA TOTP opt-in, bukan wajib. |
| NFR-03 | Pembatasan percobaan login. | Must | Uji lockout akun dan rate limit. | Lockout persisten; rate limit IP in-memory per proses, tidak terdistribusi. |
| NFR-04 | Validasi input dan unggahan bukti. | Must | Validasi schema, CVSS vector, signature/isi file, ukuran, dan hak unduh. | Allowlist PNG/JPG/JPEG/GIF/PDF/TXT/LOG; 5 MB default lokal, 4 MB pada Vercel. |
| NFR-05 | Auditabilitas. | Must | Aksi penting memiliki actor, timestamp, objek, dan jenis aksi. | Audit log tersedia; retensi operasional perlu kebijakan tersendiri. |
| NFR-06 | Persistensi data production. | Must | PostgreSQL persisten; migrasi berhasil; bukti disimpan di DB; data tetap ada setelah Function restart/cold start. | PostgreSQL dan EVIDENCE_IN_DB dikonfigurasi; runtime acceptance perlu dibuktikan. |
| NFR-07 | Ekspor laporan. | Must | DOCX dapat dibuat dan dibuka; isi laporan mengikuti status approval dan versi CVSS. | DOCX adalah format target Vercel; PDF nonaktif karena LibreOffice tidak tersedia. |
| NFR-08 | Kemudahan pengembangan lokal. | Should | Docker Compose membangun dan menjalankan aplikasi lokal. | Jalur lokal/dev, bukan kriteria deployment production. |
| NFR-09 | Kualitas kode dan pengujian. | Must | CI menjalankan lint, security/dependency checks, SQLite/PostgreSQL tests, E2E, coverage gate ≥70%, dan Docker build. | Workflow tersedia; hasil harus diverifikasi untuk commit rilis yang tepat. |
| NFR-10 | Transport dan perlindungan data. | Must | TLS aktif pada domain production; akses DB dibatasi; backup/restore dan retensi diuji. | TLS bergantung platform/proxy; enkripsi at-rest dan backup bergantung provider serta perlu bukti operasional. |

## 5. Arsitektur dan tech stack

### 5.1 Arsitektur logis

Sistem menggunakan arsitektur web client-server:

- **Presentation layer:** HTML, CSS, dan JavaScript vanilla.
- **Application/API layer:** Python 3.12 dan FastAPI; validasi request memakai Pydantic.
- **Persistence layer:** SQLAlchemy ORM dan Alembic migration.
- **Production database:** PostgreSQL persisten.
- **Development/test database:** SQLite.
- **Authentication:** Argon2 untuk password hashing; JWT HS256 untuk sesi; token version untuk invalidasi; TOTP MFA opsional.
- **Document generation:** python-docx untuk laporan DOCX.
- **Deployment:** Vercel Functions untuk aplikasi dan PostgreSQL sebagai database persisten.

### 5.2 Alasan dan trade-off

| Teknologi | Alasan pemilihan | Trade-off/batasan |
|---|---|---|
| Python 3.12 + FastAPI | API typed, validasi Pydantic, ekosistem Python. | Perlu pengelolaan dependency dan konfigurasi runtime. |
| SQLAlchemy + Alembic | ORM relasional dan migrasi skema yang terlacak. | Migrasi harus diuji pada SQLite dan PostgreSQL. |
| PostgreSQL | Penyimpanan persisten untuk production/serverless dan relasi data. | Membutuhkan database provider, kredensial, backup, dan pengaturan akses. |
| SQLite | Praktis untuk development dan test lokal. | Tidak digunakan sebagai database production Vercel. |
| HTML/CSS/vanilla JS | Tidak memerlukan frontend build step. | Interaksi dan struktur frontend dikelola tanpa framework komponen. |
| Argon2 + JWT | Password hashing dan autentikasi token. | Token dan secret harus dikelola aman; MFA masih opsional. |
| python-docx | Pembuatan laporan DOCX. | PDF memerlukan LibreOffice; tidak aktif pada Vercel. |
| Vercel | Deployment terhubung ke GitHub dan deployment otomatis dari branch production. | Filesystem Function bersifat sementara; data persisten harus di DB; batas ukuran request berlaku. |

### 5.3 Konfigurasi deployment

Variabel konfigurasi penting (nama saja; nilai rahasia tidak dicatat dalam dokumen):

- DATABASE_URL — PostgreSQL persisten.
- SECRET_KEY — secret aplikasi.
- ADMIN_PASSWORD — password awal Admin.
- EVIDENCE_IN_DB=1 — penyimpanan bukti sebagai BLOB di PostgreSQL.
- ENABLE_PDF=0 — PDF nonaktif di Vercel.
- MAX_UPLOAD_MB=4 — batas upload production.
- DATA_DIR=/tmp/scopeline — direktori sementara.
- ENABLE_DOCS=0 — dokumentasi API nonaktif secara default.

Docker Compose dipertahankan untuk pengembangan/lokal. Target deployment production adalah Vercel dengan PostgreSQL.

## 6. Model data konseptual

Entitas utama yang teridentifikasi pada implementasi:

| Entitas | Fungsi |
|---|---|
| users | Identitas pengguna, password hash, role, status akun, token version, dan konfigurasi MFA. |
| engagements | Data engagement, klien, periode, scope, RoE, status, dan approval. |
| engagement_members | Relasi pengguna dengan engagement dan penugasan. |
| findings | Temuan, deskripsi, dampak, rekomendasi, CVSS, status, tenggat, dan review. |
| evidence | Metadata dan isi bukti yang terhubung dengan temuan/retetst. |
| retests | Ronde retest, hasil, catatan, dan status perbaikan. |
| audit_log | Jejak aksi penting. |
| finding_templates | Pustaka template temuan. |
| report_templates | Template DOCX berversi dan placeholder. |
| notes, note_versions, note_templates | Catatan tim/pribadi, riwayat versi, dan template catatan. |

Relasi tingkat tinggi: satu engagement memiliki banyak anggota dan temuan; satu temuan dapat memiliki banyak evidence dan retest; satu ronde retest dapat memiliki evidence; user membuat aksi yang dicatat pada audit log. Detail constraint, cardinality, dan indeks harus dirujuk ke model SQLAlchemy dan migration pada commit yang dirilis.

## 7. Role dan kontrol akses

| Jabatan organisasi | Role aplikasi | Kode | Batas kewenangan utama |
|---|---|---|---|
| Admin System | Admin | admin | Administrasi akun dan akses sistem. |
| Project Management | Lead | lead | Pengelolaan engagement, scope/RoE, anggota, dan koordinasi. |
| Engineer-Head Offensive Security | Reviewer/Peninjau | reviewer | Review dan approval temuan sesuai four-eyes. |
| Engineer-Lead of Technical Writer | Technical Writer | writer | Narasi temuan dan template laporan; tidak dapat mengakses bukti mentah. |
| Engineer-Red Team | Tester/Penguji | tester | Pengujian berizin, pencatatan temuan, bukti, dan retest. |

Matriks izin rinci berada pada [docs/PERAN-DAN-IZIN.md](PERAN-DAN-IZIN.md). Pemetaan jabatan tidak memberi hak tambahan. Jika kewenangan Head Offensive Security harus setara Lead, diperlukan perubahan RBAC eksplisit, test 401/403, dan persetujuan stakeholder.

## 8. Desain CVSS

Kalkulator aktif menggunakan FIRST CVSS v4.0. Pengguna memilih metrik vector; server melakukan parsing, validasi, scoring, dan penentuan severity. CVSS-B digunakan untuk Base metrics. Penilaian v3.1 yang tersimpan sebelum migrasi dipertahankan sebagai histori dan tidak dihitung ulang atau diberi label v4.0.

Saat temuan v3.1 dinilai ulang, assessment historis disimpan sebelum assessment aktif diganti. Versi dan vector yang sesuai harus tampil pada laporan.

Rujukan normatif: https://www.first.org/cvss/v4.0/specification-document

## 9. Keamanan dan privasi

Kontrol yang teridentifikasi:
- Password hashing Argon2 dan JWT HS256.
- Pemeriksaan role dan keanggotaan engagement di server.
- TOTP MFA tersedia secara opt-in.
- Lockout akun dan rate limit IP in-memory.
- Validasi file berdasarkan allowlist, signature/isi, ukuran, dan nama penyimpanan acak.
- Akses download bukti dibatasi berdasarkan role; Technical Writer tidak memiliki akses bukti mentah.
- Audit log dan prinsip four-eyes pada review temuan.

Batasan yang harus dinyatakan:
- MFA belum diwajibkan seluruh akun.
- IP rate limit in-memory tidak terdistribusi antar instance.
- Enkripsi at-rest bukti bergantung pada konfigurasi provider/database; tidak diklaim sebagai enkripsi field-level aplikasi.
- TLS bergantung konfigurasi domain/platform dan harus diverifikasi.
- Backup, restore, retensi, dan disaster recovery memerlukan bukti operasional.
- Checklist ASVS adalah self-assessment, bukan sertifikasi atau audit independen.

## 10. Strategi pengujian dan acceptance

### 10.1 Pengujian otomatis

Workflow CI repository mencakup:
1. Ruff lint.
2. Bandit static security checks.
3. pip-audit dependency audit.
4. Pytest SQLite dengan coverage gate minimal 70%.
5. Pytest PostgreSQL 16 untuk migrasi/relasi.
6. E2E UI.
7. Docker Compose build.

Status tiap run harus diperiksa pada commit yang menjadi kandidat rilis. Kelulusan CI branch PR tidak otomatis membuktikan deployment production diterima.

### 10.2 Acceptance test minimum

| ID | Skenario | Hasil yang diharapkan |
|---|---|---|
| AT-01 | Akses endpoint terlindungi tanpa token | HTTP 401. |
| AT-02 | Role tidak berhak memanggil endpoint | HTTP 403. |
| AT-03 | Pengguna mengakses engagement di luar penugasannya | Akses ditolak; tidak ada kebocoran data. |
| AT-04 | Dashboard lima role | Data dan aksi sesuai permission; tidak menampilkan engagement yang tidak berhak dilihat. |
| AT-05 | Aktivasi engagement tanpa approval scope/RoE | Ditolak. |
| AT-06 | Perubahan scope/RoE setelah approval | Approval dibatalkan; engagement kembali ke draft. |
| AT-07 | Vector CVSS v4.0 valid dan invalid | Vector valid menghasilkan skor sesuai spesifikasi; invalid ditolak. |
| AT-08 | Menilai ulang temuan historis v3.1 | Assessment v3.1 tetap tersedia sebagai histori. |
| AT-09 | Pembuat temuan mencoba menyetujui temuan sendiri | Ditolak. |
| AT-10 | Perubahan temuan setelah diajukan/disetujui | Status review kembali ke Draft. |
| AT-11 | Upload/download bukti | Tipe, ukuran, dan permission tervalidasi; Writer tidak dapat mengunduh bukti mentah. |
| AT-12 | Retest dan laporan | Ronde retest tercatat; DOCX dapat dibuat; laporan final hanya berisi temuan Approved. |
| AT-13 | Persistensi di Vercel | Data dan evidence tetap ada setelah Function restart/cold start. |
| AT-14 | Health dan runtime | Endpoint health berhasil, log/error dipantau, dan smoke test dicatat dengan commit/deployment ID. |

## 11. Batasan, asumsi, dan pekerjaan lanjutan

1. Uji acceptance dashboard per lima role harus direkam sebagai bukti, tidak cukup hanya menyatakan UI tersedia.
2. Uji health dan alur bisnis di Vercel perlu dilakukan terhadap deployment production yang tepat.
3. Backup/restore, retensi, TLS, dan konfigurasi enkripsi provider harus dibuktikan.
4. MFA TOTP masih opsional; kebijakan apakah harus diwajibkan adalah keputusan stakeholder.
5. Rate limit IP in-memory perlu dievaluasi jika aplikasi digunakan pada beberapa instance.
6. PDF tidak tersedia pada Vercel; DOCX adalah format laporan production.
7. Dataset SAWALA belum dianggap disetujui; gunakan data sintetis sampai izin didapat.
8. Mode input skor CVSS manual bukan bagian dari implementasi aktif.
9. Lisensi repository belum ditetapkan.

## 12. Referensi dokumentasi dan source

- [Baseline realitas implementasi](PROJECT-REALITY-BASELINE.md)
- [Matriks role dan izin](PERAN-DAN-IZIN.md)
- [Keputusan arsitektur (ADR)](DECISIONS.md)
- [Status deployment](DEPLOYMENT-STATUS.md)
- [Checklist rilis dan acceptance](RELEASE-CHECKLIST.md)
- [Checklist self-assessment OWASP ASVS L1](ASVS-L1-checklist.md)
- [FIRST CVSS v4.0 Specification](https://www.first.org/cvss/v4.0/specification-document)
- Source utama: `backend/app/`, `backend/tests/`, `e2e/`, konfigurasi root, dan workflow GitHub Actions.
