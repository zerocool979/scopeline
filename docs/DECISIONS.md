# Catatan Keputusan Proyek (ADR)

Dokumen ini mencatat keputusan penting agar keputusan bisnis, implementasi, dan konsekuensinya mudah ditelusuri.

## ADR-001 — SCOPELINE berfokus pada manajemen dan pelaporan
- **Status:** Disetujui
- **Keputusan:** SCOPELINE mengelola engagement, scope/RoE, temuan, bukti, review, retest, dan laporan. Produk bukan scanner, exploit framework, atau attack automation.
- **Konsekuensi:** Pengujian teknis dilakukan oleh personel berwenang; aplikasi mencatat proses dan hasilnya.

## ADR-002 — Lima jabatan organisasi dipetakan ke lima role aplikasi
- **Status:** Disetujui
- **Keputusan:** Admin System → Admin; Project Management → Lead; Engineer-Head Offensive Security → Reviewer; Engineer-Lead of Technical Writer → Technical Writer; Engineer-Red Team → Tester.
- **Konsekuensi:** Pemetaan nomenklatur tidak mengubah permission. Reviewer tidak otomatis memperoleh hak pengelolaan engagement milik Lead.
- **Rujukan:** [Matriks peran dan izin](PERAN-DAN-IZIN.md).

## ADR-003 — CVSS v4.0 menjadi kalkulator aktif
- **Status:** Diimplementasikan pada main melalui PR #9
- **Keputusan:** Kalkulator aktif memakai FIRST CVSS v4.0. Perhitungan dilakukan di server dari vector metric yang dipilih pengguna.
- **Konsekuensi:** API, UI, validasi, model, template, laporan, migrasi, dan test mengikuti v4.0.
- **Pelestarian data:** Penilaian v3.1 yang telah tersimpan tidak dihitung ulang atau dilabel ulang. Ketika temuan lama dinilai ulang, assessment v3.1 disimpan dalam histori.
- **Rujukan:** [FIRST CVSS v4.0 Specification](https://www.first.org/cvss/v4.0/specification-document), [PR #9](https://github.com/zerocool979/scopeline/pull/9).

## ADR-004 — PostgreSQL untuk production, SQLite untuk pengembangan/test
- **Status:** Diimplementasikan
- **Keputusan:** PostgreSQL persisten digunakan pada Vercel/production; SQLite tetap tersedia untuk pengembangan dan test.
- **Konsekuensi:** Migrasi harus diuji pada kedua database. SQLite bukan target penyimpanan production Vercel.

## ADR-005 — DOCX sebagai format laporan utama pada Vercel
- **Status:** Diimplementasikan
- **Keputusan:** Laporan DOCX didukung; PDF memerlukan LibreOffice dan dinonaktifkan pada Vercel.
- **Konsekuensi:** Acceptance deployment Vercel menguji DOCX; PDF hanya diuji di lingkungan yang menyediakan LibreOffice.

## ADR-006 — Source code dan test adalah acuan perilaku implementasi
- **Status:** Disetujui
- **Keputusan:** Jika dokumen analisis lama berbeda dari source dan test pada commit yang disebut, source dan test menjadi acuan untuk klaim as-built. Proposal tetap menjadi acuan visi dan rencana.
- **Konsekuensi:** README, baseline, changelog, PMP, dan deployment status diperbarui saat perilaku produk berubah.

## ADR-007 — Deployment READY bukan production acceptance
- **Status:** Disetujui
- **Keputusan:** Build/deployment state READY tidak boleh ditafsirkan sebagai bukti health check, keamanan, backup/restore, atau acceptance runtime.
- **Konsekuensi:** Setiap rilis harus melampirkan deployment ID, commit SHA, smoke test, acceptance evidence, dan rollback plan.


## ADR-008 — Persetujuan ganda RoE dan laporan; pembatasan raw evidence
- **Status:** Diimplementasikan pada branch `feature/dual-approvals-evidence-rbac`; menunggu CI dan rilis.
- **Keputusan:** RoE harus disetujui Project Manager (role `lead`) dan Engineer-Head Offensive Security (role `reviewer`). Laporan final pretest/retest juga memerlukan persetujuan kedua role tersebut.
- **Validitas persetujuan laporan:** Approval terikat pada fingerprint data engagement, finding yang disetujui, ronde retest, metadata evidence, dan template aktif. Perubahan materi menghasilkan fingerprint baru dan memerlukan approval ulang.
- **Raw evidence:** Admin tidak memiliki akses melihat atau mengunduh bukti mentah serta tidak dapat mengunggah/menghapus evidence.
- **Konsekuensi:** Migrasi `0004` menambahkan status persetujuan terpisah dan tabel `report_approvals`; persetujuan RoE lama direset agar tidak dianggap memenuhi persyaratan dua pihak.
