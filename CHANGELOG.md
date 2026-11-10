# Changelog

## 1.1.0 — Gelombang 1
- **Baru:** migrasi Alembic (baseline 0001 = skema v1.0, 0002 = Gelombang 1); adopsi otomatis database lama.
- **Baru:** templat laporan DOCX berversi untuk **pretest** dan **retest** (draf → aktif → arsip, rollback, validasi placeholder, penanda `{{content}}`), disimpan di database.
- **Baru:** templat catatan pentester (.md) dan editor catatan Markdown (catatan tim + pribadi, riwayat versi, deteksi konflik, ekspor).
- **Baru:** alur review temuan (empat mata); laporan final hanya memuat temuan disetujui.
- **Baru:** ronde retest (tanggal, penguji, hasil, bukti per ronde); perbandingan pretest vs retest dan laporan retest.
- **Baru:** peran *Technical Writer*.
- **Perubahan perilaku:** "lulus retest" tidak lagi dapat diset manual, hanya melalui ronde retest. Endpoint `/api/report-template` diganti `/api/report-templates`.
- **Perbaikan:** respons CVSS usang dapat menimpa skor terbaru di UI saat metrik diubah beruntun.
- **Perbaikan:** SQLite kini menegakkan foreign key seperti PostgreSQL; kolom `review_status` dibuat cukup panjang (terdeteksi saat uji di PostgreSQL).
- **Uji:** 43 tes backend (SQLite & PostgreSQL), 13 langkah e2e UI.

## 1.0.0
Rilis awal sesuai proposal v0.1 (fitur Must/Should + impor CSV).
