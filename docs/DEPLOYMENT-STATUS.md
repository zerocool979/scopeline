# Status Implementasi dan Deployment SCOPELINE

Tanggal pemeriksaan: 10 November 2026

## GitHub

- Repository: `https://github.com/zerocool979/scopeline`
- Status: **terhubung ke project Vercel** melalui Git integration.
- Branch Production: `main`
- Baseline commit: `6d0cc1236a1c78b4c121cb03e82a7bab09c251cf` (`chore: initial SCOPELINE v1.1`)

## Vercel

- Project: `scopeline`
- Project ID: `prj_2klzYjPraT5VYpIpBcZmS4XR49B7`
- Framework: FastAPI
- Team: `zerocool979's projects` (Hobby)
- Git repository: `zerocool979/scopeline`
- Function region pada deployment pertama: `sin1` (Singapore)
- Deployment pertama: `dpl_Gnq2nZoYJkRqEvqiwqNRMW6AwgH6`
- Deployment URL: `https://scopeline-7kp8wr739-zerocool979s-projects.vercel.app`
- Deployment target: Production; build state: **READY**
- Alias project: `scopeline-six.vercel.app`
- SSO protection: Preview saja; Production disiapkan agar dapat diakses melalui autentikasi aplikasi SCOPELINE.

**Catatan:** Status READY hanya membuktikan build dan provisioning deployment selesai. Belum membuktikan function dapat menjalankan aplikasi karena PostgreSQL production belum terhubung.

## Environment variables

### Sudah tersedia pada Production, Preview, dan Development

| Key | Nilai/non-secret |
|---|---|
| `DATA_DIR` | `/tmp/scopeline` |
| `EVIDENCE_IN_DB` | `1` |
| `ENABLE_PDF` | `0` |
| `MAX_UPLOAD_MB` | `4` |
| `ENABLE_DOCS` | `0` |
| `SECRET_KEY` | Ada; nilai disimpan sebagai sensitive |
| `ADMIN_PASSWORD` | Ada; nilai disimpan sebagai sensitive |

`ADMIN_USERNAME` memakai nilai default `admin`.

### Belum tersedia

- `DATABASE_URL` — koneksi PostgreSQL persisten khusus SCOPELINE.

## Database Marketplace

- Integrasi Neon sudah terpasang pada team Vercel.
- Daftar project yang terhubung ke resource Neon masih kosong.
- Belum ada resource PostgreSQL yang dikaitkan ke project SCOPELINE.
- Karena `backend/app/config.py` mewajibkan `DATABASE_URL` di Vercel, aplikasi menolak startup hingga koneksi PostgreSQL valid tersedia.

Provisioning resource Neon harus diselesaikan melalui Vercel Marketplace Dashboard. Setelah database dibuat dan terhubung ke project, verifikasi bahwa `DATABASE_URL` tersedia di Production, Preview, dan Development sesuai kebutuhan.

## Domain

- `scopeline.vercel.app`: penambahan ke project ditolak Vercel dengan `owned-on-other-team`.
- `scopelline.vercel.app`: pemeriksaan ketersediaan mengembalikan `available=false`.
- Alias fallback project: `scopeline-six.vercel.app`.

## Status dan langkah berikutnya

1. **Selesai:** repository GitHub terhubung ke project Vercel.
2. **Selesai:** build deployment pertama berhasil dan state deployment `READY`.
3. **Selesai:** `SECRET_KEY` dan `ADMIN_PASSWORD` disimpan sebagai sensitive environment variables.
4. **Belum selesai:** provision PostgreSQL melalui Vercel Marketplace Neon dan hubungkan ke project SCOPELINE.
5. **Belum selesai:** redeploy setelah `DATABASE_URL` tersedia.
6. **Belum selesai:** verifikasi `/api/health`, login admin, engagement, finding, evidence, review, retest, dan ekspor DOCX.

SCOPELINE **belum boleh dinyatakan live/production-ready** sebelum database terhubung, runtime health check berhasil, dan alur inti lulus pengujian.

PDF export tetap nonaktif pada Vercel (`ENABLE_PDF=0`); ekspor DOCX adalah jalur yang disiapkan untuk deployment ini.