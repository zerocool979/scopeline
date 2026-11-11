# Status Implementasi dan Deployment SCOPELINE

**Pemeriksaan terakhir:** 11 November 2026  
**Repository branch:** main  
**Commit yang diperiksa:** f49736200295fc33e63030d178dfb85e35bbd25c

## Ringkasan status

| Area | Status | Dasar bukti |
|---|---|---|
| Source code v1.1 | Tersedia | Branch main, commit di atas |
| GitHub Actions CI | Lulus | Run #59, conclusion success, 11 Nov 2026 |
| Vercel Production deployment | READY | Deployment scopeline-gs24s7r06-zerocool979s-projects.vercel.app |
| Alias produksi | Terpasang | https://scopeline-six.vercel.app |
| PostgreSQL Production env | Terkonfigurasi | DATABASE_URL terdaftar pada environment Production |
| Bukti disimpan di database | Terkonfigurasi | EVIDENCE_IN_DB=1 |
| PDF di Vercel | Dinonaktifkan | ENABLE_PDF=0 |
| Runtime health & alur aplikasi | Belum diverifikasi dalam pemeriksaan ini | Metadata READY bukan health check; tidak ada log runtime pada jendela 50 menit yang diperiksa |

## GitHub

- Repository: https://github.com/zerocool979/scopeline
- Branch Production: main
- Commit: f49736200295fc33e63030d178dfb85e35bbd25c
- Commit message: chore(ci): bump actions/setup-node to v7

## GitHub Actions

- Workflow: [CI](https://github.com/zerocool979/scopeline/actions)
- Run terbaru yang diperiksa: [Run #59](https://github.com/zerocool979/scopeline/actions/runs/42992002978)
- Status: **completed / success**
- Waktu: 11 November 2026, 09:03:49–09:05:57 UTC.

Workflow pada commit tersebut menjalankan:
1. Ruff lint.
2. Bandit static security checks.
3. pip-audit dependency audit.
4. Pytest pada SQLite dengan coverage gate --cov-fail-under=70.
5. Pytest pada PostgreSQL 16 untuk migrasi dan relasi.
6. E2E UI dengan Node/jsdom dan server aplikasi.
7. Docker Compose build.

Kesimpulan: gerbang CI pada commit tersebut lulus. Ini bukan pengganti verifikasi manual OWASP ASVS atau uji penerimaan runtime di deployment Production.

## Vercel

- Project: scopeline
- Project ID: prj_2klzYjPraT5VYpIpBcZmS4XR49B7
- Team: zerocool979s-projects (Hobby)
- Framework: FastAPI
- Repository: zerocool979/scopeline
- Branch: main
- Commit: f49736200295fc33e63030d178dfb85e35bbd25c
- Deployment ID: dpl_6bTYboJCq8Xcg3BRrLk3GoZGRn2g
- Deployment URL: https://scopeline-gs24s7r06-zerocool979s-projects.vercel.app
- Alias: https://scopeline-six.vercel.app
- Target: Production
- State: **READY**
- Region: sin1 (Singapore)

### Environment variables (nama dan status saja)

Pemeriksaan metadata environment Vercel menunjukkan variabel berikut ditargetkan ke Production. Nilai rahasia tidak boleh disalin ke repository atau dokumen:

| Variabel | Status/konfigurasi |
|---|---|
| DATABASE_URL | Ada; disediakan integrasi PostgreSQL |
| SECRET_KEY | Ada; sensitive |
| ADMIN_PASSWORD | Ada; sensitive; tidak dicantumkan nilainya |
| DATA_DIR | /tmp/scopeline |
| EVIDENCE_IN_DB | 1 |
| ENABLE_PDF | 0 |
| MAX_UPLOAD_MB | 4 |
| ENABLE_DOCS | 0 |
| ADMIN_PASSWORD_RESET_ONCE | Variabel reset satu kali telah dinonaktifkan setelah rotasi awal dikonfirmasi melalui log |

Jangan menampilkan nilai DATABASE_URL, SECRET_KEY, password, token, atau kredensial lain dalam issue, commit, screenshot publik, maupun laporan.

### Batasan runtime Vercel

- PostgreSQL persisten wajib. backend/app/config.py menolak startup jika DATABASE_URL kosong atau menunjuk SQLite.
- EVIDENCE_IN_DB=1 wajib agar bukti tersimpan sebagai BLOB di PostgreSQL, bukan di filesystem Function yang sementara.
- ENABLE_PDF=0 wajib karena LibreOffice tidak dibundel pada Python runtime Vercel. DOCX adalah format laporan yang disiapkan untuk Vercel.
- Upload dibatasi hingga 4 MB untuk menyesuaikan batas request body Function.
- /tmp/scopeline hanya untuk data sementara; database menyimpan data aplikasi, bukti, dan template.
- Backup, retensi, point-in-time recovery, enkripsi at-rest, pemantauan, dan pembatasan akses database harus ditetapkan pada sisi provider sebelum data operasional nyata digunakan.

## Verifikasi yang masih harus dilakukan terhadap Production

Deployment READY dan environment variable yang tersedia belum membuktikan koneksi database atau alur bisnis berhasil pada runtime. Sebelum menyatakan production-ready, lakukan dan catat bukti berikut:

- [ ] GET /api/health mengembalikan HTTP 200 dan status ok.
- [ ] Login Admin berhasil; kata sandi awal telah dirotasi dan MFA sesuai kebijakan organisasi.
- [ ] Admin membuat akun dan setiap role hanya melihat/melakukan aksi yang diizinkan.
- [ ] Engagement tidak dapat diaktifkan sebelum RoE disetujui.
- [ ] Perubahan scope/RoE membatalkan approval dan menjeda engagement.
- [ ] Tester dapat membuat temuan; CVSS dihitung server.
- [ ] Upload, unduh, dan hapus bukti berjalan; file tersimpan di PostgreSQL.
- [ ] Review empat mata berjalan; temuan yang berubah kembali ke Draft.
- [ ] Ronde retest dan perbandingan pretest/retest berjalan.
- [ ] DOCX pretest/retest dapat diunduh; laporan final hanya berisi temuan Approved.
- [ ] Technical Writer tidak dapat melihat atau mengunduh bukti mentah.
- [ ] Audit log mencatat aktivitas penting.
- [ ] TLS, backup/restore, retensi, dan kontrol database diverifikasi.

Pada pemeriksaan ini, pembacaan log runtime Vercel untuk 50 menit terakhir tidak mengembalikan entri. Hal tersebut hanya berarti tidak ada log yang tersedia pada rentang/filter tersebut; bukan bukti bahwa aplikasi gagal atau berhasil. Endpoint health dan alur di atas belum diklaim lulus dari pemeriksaan ini.

## Catatan perubahan terhadap status 10 November

Catatan sebelumnya menyebut DATABASE_URL belum tersedia dan PostgreSQL belum terhubung. Status tersebut sudah kedaluwarsa: pada pemeriksaan 11 November, metadata environment Production menunjukkan DATABASE_URL sudah ada dan deployment terbaru berstatus READY. Namun, status verifikasi runtime tetap harus dibedakan dari provisioning environment dan build deployment.

## Kesimpulan

SCOPELINE telah memiliki source v1.1, CI yang lulus pada commit Production, environment PostgreSQL Production yang terkonfigurasi, dan deployment Vercel berstatus READY. Status yang akurat adalah **ter-deploy/build-ready, runtime acceptance belum diverifikasi dalam pemeriksaan ini**. Jangan menggunakan istilah “seluruh sistem telah teruji di produksi” atau “production-ready” sebelum checklist verifikasi di atas dilengkapi bukti.
