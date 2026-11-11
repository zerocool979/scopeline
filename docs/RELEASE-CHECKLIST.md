# Checklist Rilis SCOPELINE

Gunakan checklist ini untuk setiap rilis ke production. Tandai item hanya jika ada bukti yang dapat ditautkan.

## 1. Sebelum merge
- [ ] Issue/requirement dan acceptance criteria tersedia.
- [ ] PR memiliki ringkasan, risiko, migrasi, dan rollback plan.
- [ ] Review selesai sesuai aturan repository.
- [ ] Ruff lulus.
- [ ] Bandit lulus.
- [ ] pip-audit lulus.
- [ ] SQLite tests dan coverage gate ≥70% lulus.
- [ ] PostgreSQL migration/relationship tests lulus.
- [ ] E2E UI lulus.
- [ ] Docker Compose build lulus.
- [ ] Tidak ada secret atau data sensitif di diff.
- [ ] Dokumentasi dan CHANGELOG diperbarui.

## 2. Database dan data
- [ ] Backup database sebelum migration/rollout.
- [ ] Alembic migration diuji pada PostgreSQL.
- [ ] Histori CVSS v3.1 tetap terbaca dan tidak dihitung ulang otomatis.
- [ ] Upload evidence tersimpan secara persisten.
- [ ] Prosedur rollback dan restore diuji atau didokumentasikan dengan owner.

## 3. Deployment
- [ ] Commit SHA dan deployment ID dicatat.
- [ ] Environment Production diverifikasi tanpa menampilkan secret.
- [ ] DATABASE_URL mengarah ke PostgreSQL persisten.
- [ ] EVIDENCE_IN_DB=1.
- [ ] ENABLE_PDF=0 pada Vercel.
- [ ] MAX_UPLOAD_MB sesuai batas platform.
- [ ] Health endpoint HTTP 200.
- [ ] TLS dan akses database diverifikasi.

## 4. Smoke test dan acceptance
- [ ] Login Admin dan rotasi password awal.
- [ ] Login/permission lima role.
- [ ] Negative access tests menghasilkan 401/403 sesuai kondisi.
- [ ] Engagement membutuhkan approval scope/RoE.
- [ ] Finding create/update menghitung CVSS v4.0 di server.
- [ ] Histori CVSS v3.1 tampil untuk temuan lama.
- [ ] Evidence upload/download sesuai role.
- [ ] Review empat mata.
- [ ] Retest dan perbandingan pretest/retest.
- [ ] DOCX pretest/retest berhasil diunduh.
- [ ] Laporan final hanya berisi temuan Approved secara default.
- [ ] Audit log mencatat aktivitas penting.
- [ ] Technical Writer tidak dapat mengakses bukti mentah.

## 5. Sign-off dan komunikasi
- [ ] Defect kritis/tinggi ditutup atau diterima secara formal.
- [ ] Backup/restore, retensi, dan monitoring memiliki owner.
- [ ] Acceptance evidence disimpan.
- [ ] Stakeholder menyetujui rilis.
- [ ] CHANGELOG dan status deployment diperbarui.
- [ ] Release/tag dibuat bila versi rilis ditetapkan.
- [ ] Rollback contact dan prosedur diketahui tim.

**Penting:** Jangan menyatakan production-ready hanya berdasarkan status Vercel READY atau CI lulus. Runtime acceptance dan kontrol operasional harus memiliki bukti terpisah.
