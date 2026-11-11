## Ringkasan
<!-- Apa yang berubah dan mengapa? -->

## Kategori
- [ ] Bug fix
- [ ] Feature
- [ ] Refactor
- [ ] Documentation
- [ ] Security
- [ ] Database migration

## Issue / requirement terkait
<!-- Tautkan issue atau Change Request. -->

## Acceptance criteria
- [ ] Kriteria penerimaan ditulis dan terpenuhi.
- [ ] Akses role terkait diuji (termasuk 401/403 bila relevan).
- [ ] Histori/data lama tetap aman.

## Verifikasi
- [ ] Ruff
- [ ] Bandit
- [ ] pip-audit
- [ ] Pytest + coverage gate >=70%
- [ ] PostgreSQL tests (bila relevan)
- [ ] E2E (bila relevan)
- [ ] Docker Compose build
- [ ] CI GitHub Actions lulus

## Risiko, migrasi, dan rollback
<!-- Dampak database/API/security, migrasi, rencana rollback. -->

## Dokumentasi
- [ ] README / docs / CHANGELOG diperbarui bila relevan.
- [ ] Tidak ada secret, data klien, atau bukti sensitif dalam diff.
