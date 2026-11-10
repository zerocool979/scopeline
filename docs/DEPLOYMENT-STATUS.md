# Status Implementasi dan Deployment SCOPELINE

Tanggal pemeriksaan: 10 November 2026

## GitHub

- Target repository: `https://github.com/zerocool979/scopeline`
- Status: repository belum dibuat dan belum ada remote Git yang terhubung.
- Source baseline: SCOPELINE 1.1.0 + konfigurasi Vercel pada root project.

## Vercel

- Project: `scopeline`
- Project ID: `prj_2klzYjPraT5VYpIpBcZmS4XR49B7`
- Framework: FastAPI
- Team: `zerocool979's projects` (Hobby)
- Region function: belum ditetapkan atau terverifikasi melalui project settings; jangan diasumsikan `sin1`.
- Alias otomatis: `scopeline-six.vercel.app` (domain terverifikasi pada project, tetapi belum ada deployment)
- Project status: `live=false`, `latestDeployment=null`
- Deployment history: belum ada deployment untuk project ini.
- SSO protection: aktif untuk seluruh deployment URL non-custom-domain.

## Environment variables yang sudah dipasang

| Key | Nilai/non-secret | Environment |
|---|---|---|
| `DATA_DIR` | `/tmp/scopeline` | Production, Preview, Development |
| `EVIDENCE_IN_DB` | `1` | Production, Preview, Development |
| `ENABLE_PDF` | `0` | Production, Preview, Development |
| `MAX_UPLOAD_MB` | `4` | Production, Preview, Development |
| `ENABLE_DOCS` | `0` | Production, Preview, Development |

## Environment variables yang belum tersedia

- `DATABASE_URL` — PostgreSQL persisten khusus SCOPELINE.
- `SECRET_KEY` — secret minimal 32 karakter.
- `ADMIN_PASSWORD` — password awal admin minimal 12 karakter.

Project belum memiliki koneksi database Marketplace. Vercel tidak menyediakan lagi Vercel Postgres native; PostgreSQL baru dipasang melalui provider Vercel Marketplace. Tanpa ketiga variabel wajib, aplikasi menolak start.

## Domain

- `scopeline.vercel.app`: penambahan ke project `scopeline` ditolak Vercel dengan `owned-on-other-team`.
- `scopelline.vercel.app`: pemeriksaan ketersediaan mengembalikan `available=false`.
- Alias fallback `scopeline-six.vercel.app` tersedia pada project, tetapi belum memiliki deployment dan masih mengikuti proteksi SSO project.

## Kesimpulan status

Source code dan konfigurasi Vercel telah disiapkan. Repository GitHub belum dibuat; database PostgreSQL belum diprovisikan; tiga variabel rahasia/connection belum dipasang; dan belum ada deployment yang dapat diuji. Karena itu aplikasi belum boleh dinyatakan live/production-ready.
