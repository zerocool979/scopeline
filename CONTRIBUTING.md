# Panduan Kontribusi

Terima kasih telah membantu mengembangkan SCOPELINE. Repository ini adalah proyek akademik untuk manajemen engagement dan pelaporan penetration testing.

## Prinsip kontribusi

- Jaga batas produk: SCOPELINE mendokumentasikan pekerjaan pengujian berizin; bukan scanner, exploit framework, atau attack automation.
- Jangan commit secret, password, token, connection string, data klien, atau bukti pengujian sensitif.
- Gunakan data sintetis kecuali ada izin tertulis dan sanitasi yang sesuai.
- Perubahan harus disertai pengujian, dokumentasi, dan catatan dampak.

## Alur kerja

1. Buka issue untuk bug, enhancement, atau perubahan requirement; jelaskan konteks dan acceptance criteria.
2. Buat branch dari `main` dengan nama ringkas, misalnya `feat/cvss-export`, `fix/rbac-reviewer`, atau `docs/release-guide`.
3. Buat perubahan kecil dan fokus. Hindari menggabungkan refactor besar dengan perubahan perilaku.
4. Jalankan pemeriksaan lokal:

   ```bash
   cd backend
   pip install -r requirements-dev.txt
   ruff check app tests
   bandit -q -r app
   pip-audit -r requirements.txt
   pytest --cov=app --cov-fail-under=70
   ```

   Jalankan tes PostgreSQL dengan `TEST_DATABASE_URL` dan E2E dari folder `e2e` bila perubahan menyentuh database atau UI.

5. Perbarui README, changelog, baseline, atau dokumentasi deployment jika perilaku/konfigurasi berubah.
6. Buka Pull Request ke `main`, tautkan issue, jelaskan risiko, migrasi, rencana rollback, dan bukti tes.
7. Jangan merge sebelum seluruh CI wajib lulus dan perubahan ditinjau sesuai aturan tim.

## Aturan khusus

- **Database:** sertakan Alembic migration; uji SQLite dan PostgreSQL. Jangan menghapus/menulis ulang histori tanpa migration plan.
- **RBAC:** uji akses positif dan negatif (401/403) untuk role terkait. Nama jabatan organisasi tidak otomatis mengubah permission.
- **CVSS:** kalkulasi dilakukan di server. Perubahan algoritme/vector harus merujuk FIRST, mencakup test vector, API, UI, laporan, dan histori versi.
- **Evidence:** pertahankan allowlist, validasi konten, batas ukuran, kontrol akses, dan audit trail.
- **Laporan:** pastikan status draft/final dan hak akses bukti tidak bocor.
- **Deployment:** status build READY bukan bukti runtime acceptance.

## Format commit

Gunakan pola sederhana: `type: imperative summary`, misalnya `fix: enforce reviewer access boundary`, `feat: add finding export`, `docs: clarify deployment acceptance`.

## Definition of Done

- Acceptance criteria issue terpenuhi.
- Lint, security/dependency checks, unit/API, dan tes relevan lulus.
- Coverage gate 70% tetap terpenuhi.
- Migration diuji pada SQLite dan PostgreSQL bila relevan.
- Dokumentasi/changelog diperbarui.
- Tidak ada secret atau data sensitif dalam diff.
- CI Pull Request lulus dan review selesai.
