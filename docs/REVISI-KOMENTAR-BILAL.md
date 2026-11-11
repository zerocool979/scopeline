# Tindak Lanjut 12 Komentar Bilal — SCOPELINE

**Tujuan:** mencatat keputusan revisi dokumen berdasarkan 12 komentar Bilal dan membedakan kebutuhan yang sudah ada di source code dari usulan yang masih memerlukan perubahan implementasi.

**Acuan perilaku:** branch `main` setelah PR #9 digabung (merge commit `bca1d52479aa7537df025c4a3dc84d2807453705`) dan dokumentasi PA/PM yang diselaraskan pada 11 November 2026. Source code dan test pada `main` adalah acuan perilaku implementasi.

## Keputusan final baseline dokumentasi

Keputusan kerja untuk penyelarasan dokumen akademik ditetapkan sebagai berikut:

1. **Lima jabatan organisasi dipetakan ke lima role aplikasi** tanpa mengubah kode role dan izin backend:
   - Admin System → Admin (`admin`)
   - Project Management → Lead (`lead`)
   - Engineer-Head Offensive Security → Peninjau / Reviewer (`reviewer`)
   - Engineer-Lead of Technical Writer → Technical Writer (`writer`)
   - Engineer-Red Team → Penguji / Tester (`tester`)

   Pemetaan ini adalah keputusan nomenklatur proyek untuk dokumen, bukan klaim bahwa setiap jabatan memiliki kewenangan identik di luar matriks aplikasi. Secara khusus, Reviewer tidak otomatis memiliki hak mengelola engagement, anggota, scope, atau RoE seperti Lead. Bila Head Offensive Security memerlukan kewenangan tersebut, perubahan RBAC harus dibuat terpisah dan diuji; pemetaan nama saja tidak memberikan izin tambahan.

2. **Keputusan dan implementasi branch ini:** CVSS v4.0 menjadi kalkulator aktif. Branch migrasi memakai pustaka `cvss` 3.6 (CVSS4), validasi vector, UI 11 Base metrics, penyimpanan versi, dan tampilan laporan. Temuan lama v3.1 dipertahankan; ketika dinilai ulang, assessment lama disalin ke kolom `cvss_legacy_*` sebelum nilai aktif diganti v4.0. Status merge/rilis menunggu CI dan review pull request.

3. **Mode perhitungan skor yang berlaku adalah kalkulasi sistem/server dari vektor CVSS.** Input skor numerik manual belum menjadi fitur aktif. Jika kebutuhan manual dimaksudkan sebagai pemilihan metrik vektor secara manual di UI, hal tersebut tetap dapat mempertahankan kalkulasi server-side; jika dimaksudkan sebagai input skor akhir, perlu kontrol audit dan validasi tersendiri.

4. **FR-08 ditetapkan Must pada baseline kebutuhan** dengan kriteria akses berbasis role dan engagement. Data dasbor harus mengikuti hak akses, bukan sekadar menyembunyikan elemen antarmuka.

5. **SAWALA bukan dataset default.** Penggunaannya memerlukan izin dan sanitasi; data sintetis tetap menjadi dataset demonstrasi sampai izin tersebut tersedia.

## Keputusan per komentar

| No. | Topik | Keputusan revisi dokumentasi | Status terhadap implementasi |
|---:|---|---|---|
| 1 | Stack pada abstrak | Ganti deskripsi SQLite/HMAC-SHA256 dengan Python 3.12, FastAPI, SQLAlchemy, PostgreSQL untuk Vercel/produksi, SQLite hanya lokal/test, HTML/CSS/JS vanilla, Argon2 + JWT HS256. Sebut Docker Compose hanya untuk lokal/hosting mandiri. | Sudah sesuai source |
| 2 | Fase berikutnya / kontrak API | Pisahkan demo lokal dari target deployment. REST API FastAPI tetap menjadi kontrak backend; target Vercel bukan lagi sekadar fase berikutnya karena deployment Production berstatus READY. Namun runtime acceptance tetap perlu pengujian langsung. | Deployment metadata READY; runtime acceptance belum dibuktikan |
| 3 | Data uji fiktif atau SAWALA | Pertahankan data sintetis sebagai default. Dataset UAS SAWALA hanya boleh dipakai setelah ada izin pemilik data/dosen, penghapusan identitas dan rahasia, serta konfirmasi bahwa scope dan bukti boleh digunakan. SCOPELINE tidak boleh dipakai untuk menguji target tanpa otorisasi tertulis. | Keputusan tata kelola; belum ada bukti dataset SAWALA disetujui/diintegrasikan |
| 4 | Versi CVSS | CVSS v4.0 disetujui sebagai kalkulator aktif; branch migrasi menerapkan parser, scoring, UI, API, penyimpanan versi, dan laporan. Temuan historis v3.1 tidak dihitung ulang. | CVSS v4.0 aktif pada `main`; v3.1 tetap disimpan untuk histori |
| 5 | FR-01 dan FR-08, lima peran | Rinci autentikasi/pengelolaan pengguna dan dasbor per role. Gunakan pemetaan final nomenklatur proyek: Admin System → Admin; Project Management → Lead; Engineer-Head Offensive Security → Peninjau/Reviewer; Engineer-Lead of Technical Writer → Technical Writer; Engineer-Red Team → Penguji/Tester. Kode role dan izin backend tetap dipertahankan. | Lima role dan dasbor ada; kesetaraan nama organisasi perlu keputusan |
| 6 | Kalkulator CVSS di tabel FR | Rumuskan sebagai “Kalkulator CVSS v4.0 (server-side; CVSS-B untuk Base metrics)”; dokumen harus menyatakan temuan historis v3.1 tetap terpelihara. | CVSS v4.0 telah di-merge ke `main` melalui PR #9; CI branch PR lulus |
| 7 | Fungsi khusus perhitungan vektor | Jelaskan kalkulasi dipisahkan dalam modul `backend/app/cvss.py`, divalidasi, lalu dipakai oleh endpoint kalkulasi dan alur create/update finding. Kriteria uji harus menguji vektor valid/tidak valid, skor, severity, dan konsistensi endpoint dengan penyimpanan temuan. | Sudah diimplementasikan |
| 8 | Tabel NFR | Susun NFR sebagai tabel tersendiri dengan ID, kebutuhan, prioritas, kriteria uji, dan status/bukti. Bedakan kontrol teruji otomatis dari hal yang masih perlu verifikasi manual. | Perlu perapian dokumen kebutuhan; kontrol ada dengan batasan yang dicatat di ASVS checklist |
| 9 | Docker Compose / Vercel | Ubah NFR deployment menjadi deployment Vercel dengan PostgreSQL persisten, konfigurasi environment, penyimpanan bukti di DB, dan batasan PDF. Docker Compose dipertahankan sebagai jalur dev/lokal, bukan kriteria deployment produksi. | Deployment Production terbaru yang diperiksa berstatus READY; runtime acceptance bisnis tetap belum dibuktikan |
| 10 | Opsi hitung manual atau sistem | Dokumentasi *as-built* menyatakan skor dihitung backend dari vektor CVSS; tidak ada mode input skor manual yang terverifikasi di source. Opsi manual dapat dicatat sebagai usulan perubahan, dengan aturan validasi, audit, dan penandaan sumber skor sebelum diimplementasikan. | Belum diimplementasikan; jangan didokumentasikan sebagai fitur aktif |
| 11 | Subbab tech stack | Susun ulang stack berdasarkan runtime Vercel dan pemisahan lokal/produksi sebagaimana bagian arsitektur pada baseline. Sertakan alasan pemilihan, trade-off, dan batasan PDF/filesystem serverless. | Sudah sesuai source; narasi dokumen akademik perlu diselaraskan |
| 12 | Kesimpulan dan deployment | Kesimpulan menyatakan target deployment Vercel dan PostgreSQL; Docker Compose disebut sebagai sarana lokal. Bedakan status deployment READY dengan penerimaan runtime yang belum diverifikasi. | Metadata deployment READY; uji penerimaan runtime belum dibuktikan |

## Rincian kebutuhan yang disarankan untuk makalah

Tabel berikut adalah rumusan kebutuhan yang dapat dipakai untuk memperbarui makalah. Prioritas Must adalah rekomendasi kebutuhan produk; kolom status menyatakan apakah perilaku tersebut sudah ada di implementasi.

### Kebutuhan fungsional

| ID | Kebutuhan | Prioritas | Kriteria penerimaan yang disarankan | Status source |
|---|---|---|---|---|
| FR-01 | Autentikasi, pengelolaan akun, dan RBAC untuk lima role aplikasi: Admin, Lead, Penguji, Peninjau, Technical Writer. | Must | Request tanpa token ke endpoint terlindungi menghasilkan 401; role yang tidak berwenang menghasilkan 403; Admin dapat membuat/mengubah/nonaktifkan akun dan reset kata sandi; perubahan role/status/password membatalkan token lama. | Ada; uji per endpoint/role perlu dirujuk |
| FR-08 | Dasbor menyajikan ringkasan sesuai role dan engagement yang dapat diakses pengguna. | Must (usulan prioritas) | Tanpa token 401; role/anggota tidak berhak tidak dapat mengakses data engagement; data yang ditampilkan tidak membocorkan engagement di luar hak akses; verifikasi tampilan per kelima role. | Dasbor dan pembatasan engagement tersedia; matriks acceptance dashboard per role perlu dilengkapi |
| FR-05 | Kalkulasi Base Score dan rating/severity CVSS v4.0 dari vektor yang tervalidasi di server. | Must | Vektor v4.0 valid menghasilkan skor/rating sesuai test vector resmi; vektor tidak lengkap/salah versi ditolak; endpoint kalkulasi dan create/update finding menghasilkan nilai identik; temuan v3.1 lama tetap dapat dibaca/ditandai versinya. | Diimplementasikan pada branch migrasi; menunggu CI/review |

**Catatan pemetaan role organisasi:** nama jabatan organisasi adalah label bisnis, bukan kode role source. Pemetaan dokumen yang dipakai: Admin System → Admin; Project Management → Lead; Engineer-Head Offensive Security → Peninjau; Engineer-Lead of Technical Writer → Technical Writer; Engineer-Red Team → Penguji. Pemetaan ini tidak mengubah izin. Peninjau tidak memiliki hak Lead untuk membuat/mengubah engagement, mengelola anggota, atau menyetujui RoE. Jika kewenangan Head Offensive Security harus mencakup fungsi tersebut, RBAC backend harus direvisi dan diuji sebelum klaim tersebut dicantumkan.

### Kebutuhan non-fungsional

| ID | Kebutuhan | Prioritas | Kriteria penerimaan / bukti | Batasan yang harus dinyatakan |
|---|---|---|---|---|
| NFR-01 | Otorisasi berbasis role dan akses objek engagement. | Must | Uji 401 untuk tanpa token, 403 untuk role tidak sesuai, serta penolakan akses ke engagement yang bukan anggota. | Uji harus mencakup endpoint dan data dashboard, bukan hanya halaman UI. |
| NFR-02 | Perlindungan kredensial dan sesi. | Must | Password di-hash Argon2; JWT memiliki expiry; perubahan kredensial/role/status menginvalidasi token lama. | MFA TOTP tersedia tetapi opt-in, belum wajib semua akun. |
| NFR-03 | Perlindungan percobaan login. | Must | Uji account lockout setelah ambang gagal; uji rate limit. | IP rate limiter in-memory per proses, bukan distributed lintas instance. |
| NFR-04 | Validasi input dan unggahan. | Must | Validasi skema, vektor CVSS, tipe/isi file, ukuran maksimum, serta akses unduh bukti berdasarkan izin. | Limit upload lokal default 5 MB; Vercel dikonfigurasi 4 MB. |
| NFR-05 | Auditabilitas aktivitas penting. | Must | Perubahan engagement/RoE, temuan, review, retest, dan ekspor menghasilkan audit event yang dapat ditelusuri. | Retensi/backup audit perlu kebijakan operasional. |
| NFR-06 | Deployment dan persistensi data pada Vercel. | Must | Aplikasi tersambung ke PostgreSQL persisten; migrasi berjalan; bukti disimpan di DB (`EVIDENCE_IN_DB=1`); uji restart/cold start dan alur CRUD. | Status READY bukan bukti acceptance runtime. |
| NFR-07 | Ketersediaan ekspor laporan. | Should | DOCX dapat dibuat dan divalidasi; PDF hanya dinyatakan tersedia bila LibreOffice terpasang. | PDF dinonaktifkan pada runtime Vercel. |
| NFR-08 | Kemudahan pengembangan lokal. | Should | Docker Compose dapat membangun dan menjalankan stack lokal. | Bukan kriteria deployment produksi Vercel. |

## Keputusan lanjutan yang masih memerlukan perubahan atau bukti

1. **Hak Engineer-Head Offensive Security:** konfirmasi apakah role Peninjau cukup atau perlu kewenangan tambahan setara Lead. Dokumen saat ini memakai Peninjau dan tidak memperluas izin.
2. **Migrasi CVSS v4.0:** implementasi tersedia pada branch `feature/cvss-v4-migration`; jalankan CI dan review sebelum merge. Data lama v3.1 dipertahankan sebagai histori.
3. **Mode hitung manual:** definisikan apakah yang dimaksud input metrik vektor manual atau input skor numerik akhir. Mode aktif saat ini adalah kalkulasi server-side.
4. **Dataset SAWALA:** dapatkan izin dan lakukan sanitasi sebelum dipakai.
5. **Penerimaan deployment:** lakukan uji langsung terhadap runtime Vercel dan simpan bukti hasilnya.

## Batas klaim deployment dan pengujian

- CI branch PR #9 (`43030825984`) lulus; itu bukan bukti seluruh acceptance test produksi selesai.
- Metadata Vercel menunjukkan deployment Production terbaru yang diperiksa berstatus READY pada commit `f2bc3637`. Pemeriksaan login, dashboard kelima role, database, unggah/unduh bukti, review, retest, dan ekspor DOCX tetap harus dicatat dengan tanggal, akun uji, hasil, dan bukti.
- Jangan menyebut PDF tersedia pada Vercel; konfigurasi yang diperiksa menonaktifkannya.
- Jangan menyebut opsi hitung skor manual atau dataset SAWALA sebagai fitur yang telah diterapkan tanpa perubahan kode/bukti.

## Rujukan source

- `backend/app/models.py` — lima kode role dan model data.
- `backend/app/cvss.py` — parser dan kalkulasi CVSS v4.0; migrasi `0003_cvss_v4.py` mempertahankan assessment v3.1.
- `backend/app/routers/findings.py` — kalkulasi server-side, endpoint `/api/cvss/calc`, create/update temuan.
- `backend/app/routers/users.py` — pengelolaan akun oleh Admin.
- `backend/app/routers/engagements.py` dan `backend/app/deps.py` — akses engagement dan role.
- `docs/PERAN-DAN-IZIN.md` — matriks izin.
- `docs/ASVS-L1-checklist.md` dan `docs/DEPLOYMENT-STATUS.md` — bukti kontrol, CI, dan status deployment.
