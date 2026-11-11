# Status Implementasi dan Deployment SCOPELINE

**Pemeriksaan:** 11 November 2026  
**Repository:** https://github.com/zerocool979/scopeline  
**Branch produksi:** `main`  
**Project Vercel:** `scopeline` — terhubung ke `zerocool979/scopeline`  
**Alias produksi:** https://scopeline-six.vercel.app

## Ringkasan status

| Area | Status | Bukti / batas klaim |
|---|---|---|
| CVSS v4.0 | Merged ke main | PR #9, merge commit `bca1d52479aa7537df025c4a3dc84d2807453705` |
| CI branch PR #9 | Success | Run [43030825984](https://github.com/zerocool979/scopeline/actions/runs/43030825984) |
| CI untuk dokumentasi commit terbaru | Belum diverifikasi | Jangan disimpulkan dari CI PR #9 |
| Vercel Git integration | Terhubung | Project `scopeline`, repo `zerocool979/scopeline`, branch `main` |
| Deployment Production terakhir yang sudah READY saat pemeriksaan | READY | Commit `f2bc363779888d88c134c49787c2b74427bcc942`, deployment `dpl_7KXgGKFhkrEBa8QBTXDqD5ZbdnCV` |
| Commit dokumentasi sesudah deployment READY tersebut | QUEUED/BUILDING saat pemeriksaan | Commit dokumentasi PA/PM dan sinkronisasi komentar; tidak mengubah source aplikasi |
| Error runtime 24 jam | Tidak ditemukan | Vercel error aggregation mengembalikan no runtime errors |
| Log runtime detail | Tidak tersedia untuk jendela 24 jam | Retensi log pada paket Hobby lebih pendek; query 24 jam ditolak API |
| Health check dan acceptance bisnis production | Belum diverifikasi | Deployment READY dan tidak adanya error cluster bukan pengganti uji alur bisnis |

## GitHub dan perubahan aplikasi

- Repository: https://github.com/zerocool979/scopeline
- Branch: `main`.
- CVSS v4.0 telah digabung melalui [PR #9](https://github.com/zerocool979/scopeline/pull/9).
- Merge commit: `bca1d52479aa7537df025c4a3dc84d2807453705`.
- CI branch PR #9: run [43030825984](https://github.com/zerocool979/scopeline/actions/runs/43030825984), completed/success, mencakup Ruff, Bandit, pip-audit, SQLite tests dengan coverage gate, PostgreSQL tests, E2E UI, dan Docker Compose build.
- CI PR yang lulus tidak membuktikan semua acceptance test Production telah selesai.
- Perubahan dokumentasi PA/PM setelah commit aplikasi tidak mengubah source runtime; status CI untuk commit dokumentasi terbaru tetap perlu diperiksa terpisah.

## Vercel

Project Vercel terhubung ke GitHub repository dan branch `main`. Pemeriksaan deployment Production terakhir yang sudah berstatus READY:

- Deployment ID: `dpl_7KXgGKFhkrEBa8QBTXDqD5ZbdnCV`
- Deployment URL: https://scopeline-q6c8toa8g-zerocool979s-projects.vercel.app
- Alias: https://scopeline-six.vercel.app
- Commit: `f2bc363779888d88c134c49787c2b74427bcc942`
- State: **READY**
- Region: `sin1`

Sesudah deployment tersebut, GitHub menerima commit dokumentasi PA/PM dan sinkronisasi keputusan. Vercel membuat deployment Production otomatis untuk commit dokumentasi itu; pada saat pemeriksaan terakhir deployment terbaru berada pada status QUEUED/BUILDING. Karena itu, jangan menyebut commit dokumentasi terbaru sudah ter-deploy sampai status READY dikonfirmasi.

### Konfigurasi environment

Metadata project menunjukkan konfigurasi Production berikut (hanya nama dan nilai nonrahasia; secret tidak dicantumkan):

| Variabel | Status/konfigurasi |
|---|---|
| DATABASE_URL | Ada; PostgreSQL persisten |
| SECRET_KEY | Ada; sensitive |
| ADMIN_PASSWORD | Ada; sensitive |
| DATA_DIR | `/tmp/scopeline` |
| EVIDENCE_IN_DB | `1` |
| ENABLE_PDF | `0` |
| MAX_UPLOAD_MB | `4` |
| ENABLE_DOCS | `0` |

Jangan memasukkan nilai DATABASE_URL, SECRET_KEY, password, token, atau kredensial lain ke GitHub, issue, screenshot publik, atau laporan.

### Batas runtime Vercel

- PostgreSQL persisten wajib untuk data production; SQLite hanya untuk pengembangan dan test.
- Evidence disimpan sebagai BLOB di PostgreSQL saat `EVIDENCE_IN_DB=1`; filesystem Function bersifat sementara.
- PDF dinonaktifkan pada Vercel karena LibreOffice tidak tersedia; DOCX adalah format laporan production.
- Upload dibatasi 4 MB.
- `/tmp/scopeline` hanya untuk data sementara.
- Backup, restore, retensi, point-in-time recovery, dan enkripsi at-rest perlu ditetapkan/diverifikasi di sisi provider.
- MFA TOTP tersedia tetapi opt-in.
- IP rate limit masih in-memory per proses, bukan distributed.

## Runtime verification dan acceptance

Pemeriksaan error aggregation Vercel untuk 24 jam terakhir tidak menemukan runtime error. Query runtime logs 24 jam ditolak karena retensi log paket Hobby tidak mencakup rentang tersebut. Ini bukan bukti bahwa seluruh endpoint dan proses bisnis lulus.

Checklist yang harus dijalankan terhadap deployment Production terbaru:

- [ ] GET endpoint health mengembalikan HTTP 200 dan status sehat.
- [ ] Login Admin berhasil; kredensial awal telah dirotasi.
- [ ] Uji 401 untuk akses tanpa token.
- [ ] Uji 403 untuk role yang tidak berwenang.
- [ ] Uji dashboard untuk kelima role dan pastikan tidak ada kebocoran lintas engagement.
- [ ] Engagement tidak dapat diaktifkan sebelum scope dan RoE disetujui.
- [ ] Perubahan scope/RoE membatalkan approval.
- [ ] Temuan baru memakai CVSS v4.0; score dihitung server-side.
- [ ] Penilaian historis v3.1 tetap dapat ditelusuri.
- [ ] Upload, unduh, dan hapus bukti berhasil; Technical Writer tidak dapat mengunduh bukti mentah.
- [ ] Review four-eyes berjalan dan perubahan temuan mereset review.
- [ ] Retest tersimpan per ronde.
- [ ] DOCX dapat diunduh; laporan final hanya berisi temuan Approved.
- [ ] Audit log mencatat aktivitas penting.
- [ ] TLS, backup/restore, retensi, dan kontrol akses database diverifikasi.
- [ ] Catat tanggal, commit SHA, deployment ID, akun uji/role, hasil, dan bukti untuk setiap acceptance test.

## Kesimpulan

CVSS v4.0 telah digabung ke `main`, dan CI branch PR #9 lulus. Vercel terhubung ke repository; deployment Production sebelumnya berstatus READY, sedangkan deployment dokumentasi yang lebih baru sedang diproses saat pemeriksaan. Error aggregation 24 jam tidak menemukan error, tetapi log detail 24 jam tidak tersedia pada paket Hobby. **Status yang dapat diklaim: aplikasi terhubung ke Vercel; deployment terbaru menunggu konfirmasi READY; runtime acceptance bisnis belum diverifikasi.**
