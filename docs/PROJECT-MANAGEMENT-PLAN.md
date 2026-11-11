# Rencana Manajemen Proyek SCOPELINE

**Dokumen:** Project Management Plan (PMP)  
**Versi:** 1.1  
**Tanggal acuan:** 11 November 2026  
**Status:** Baseline manajemen proyek; diselaraskan dengan source code dan dokumentasi pada branch `main` per 11 November 2026  
**Produk:** Platform Manajemen Engagement dan Pelaporan Penetration Testing Berbasis Web  
**Konteks:** Proyek akademik STMIK Tazkia

---

Dokumen analisis teknis terkait: [Program Analysis & System Design](PROGRAM-ANALYSIS-DESIGN.md). Status deployment dan batas klaim: [Deployment Status](DEPLOYMENT-STATUS.md).\n\n## 1. Ringkasan eksekutif

SCOPELINE adalah aplikasi web untuk mengelola administrasi dan dokumentasi engagement penetration testing: otorisasi, scope, Rules of Engagement (RoE), anggota, temuan, bukti, penilaian risiko, review, retest, catatan teknis, dan laporan. Aplikasi mendukung proses kerja tim; SCOPELINE bukan vulnerability scanner, exploit framework, atau alat otomasi serangan.

Rencana awal proyek menggunakan horizon 24 minggu dalam enam sprint. Prioritas fitur memakai MoSCoW dan kapasitas perencanaan menyediakan buffer 20%. Horizon dan pembagian sprint tersebut adalah baseline proposal; tanggal aktual, velocity, dan capaian sprint perlu dikonfirmasi melalui catatan sprint/rapat, sehingga dokumen ini tidak mengarang tanggal realisasi.

Pada 11 November 2026, CVSS v4.0 telah digabung ke branch `main` melalui PR #9. CI branch PR #9 lulus pada run `43030825984`. Deployment Vercel Production yang diperiksa terakhir berstatus READY pada commit dokumentasi `f2bc363779888d88c134c49787c2b74427bcc942`; deployment otomatis mengikuti commit GitHub. Pemeriksaan error runtime 24 jam tidak menemukan error, tetapi log rinci tidak tersedia pada retensi paket Hobby. Health check dan acceptance alur bisnis production tetap harus dicatat sebelum klaim penerimaan.

## 2. Tujuan dan ukuran keberhasilan

| Tujuan | Ukuran keberhasilan / kriteria |
|---|---|
| Memusatkan administrasi engagement | Engagement, scope, RoE, anggota, dan status dikelola dalam aplikasi |
| Mengelola temuan secara tertelusur | Temuan memiliki identitas, deskripsi, dampak, rekomendasi, status, tenggat, bukti, dan histori |
| Menilai risiko secara konsisten | Kalkulator aktif CVSS v4.0 (CVSS-B) menghitung skor di server; penilaian historis v3.1 tetap terlacak |
| Menjaga kualitas review | Alur Draft → In Review → Approved / Changes Requested dan aturan empat mata |
| Mendukung verifikasi perbaikan | Retest tersimpan per ronde beserta hasil, catatan, dan bukti |
| Menghasilkan laporan | Laporan DOCX pretest/retest dapat dibuat; laporan final secara default hanya memuat temuan yang disetujui |
| Menjaga kualitas engineering | CI meliputi lint, security/dependency checks, tes SQLite/PostgreSQL, E2E, coverage gate ≥70%, dan Docker build |
| Menyiapkan deployment | Konfigurasi Vercel menggunakan PostgreSQL persisten; acceptance runtime harus dibuktikan terpisah dari status build READY |

## 3. Ruang lingkup

### 3.1 Dalam ruang lingkup

- Autentikasi, pengelolaan pengguna, dan lima role aplikasi.
- Pengelolaan engagement, scope, RoE, anggota, dan persetujuan.
- Pencatatan temuan, bukti, CVSS v4.0, status, tenggat, dan review.
- Retest per ronde, hasil, bukti, dan perbandingan pretest/retest.
- Dashboard, audit log, template temuan, impor CSV, catatan tim/pribadi.
- Template laporan DOCX berversi dan ekspor laporan.
- Pengujian, dokumentasi, deployment, dan verifikasi penerimaan.

### 3.2 Di luar ruang lingkup

- Pemindaian kerentanan otomatis.
- Eksploitasi, eksekusi payload, atau otomasi serangan.
- AI untuk menghasilkan atau menilai temuan.
- Aplikasi mobile native.
- Multi-tenant SaaS.
- Pengiriman email pengingat tenggat (belum diimplementasikan pada baseline).
- PDF pada Vercel (dinonaktifkan karena LibreOffice tidak tersedia di runtime tersebut).

### 3.3 Prioritas MoSCoW dari proposal

| Prioritas | Fitur |
|---|---|
| Must | Autentikasi/user/role; engagement/scope/RoE; temuan/bukti; CVSS; laporan DOCX/PDF sesuai kemampuan lingkungan |
| Should | Retest; dashboard; audit log |
| Could | Impor CSV; pengingat email |
| Won't (rilis ini) | Scanning, exploitation, attack automation, AI, mobile app, multi-tenant |

Catatan: status implementasi aktual harus dibaca dari baseline source code dan status deployment, bukan hanya daftar rencana.

## 4. Organisasi proyek dan pemangku kepentingan

### 4.1 Pemetaan lima jabatan

Pemetaan berikut telah disetujui sebagai nomenklatur organisasi terhadap lima role internal aplikasi. Pemetaan ini **tidak otomatis mengubah permission** pada kode.

| Jabatan organisasi | Role aplikasi | Kode role | Fokus tanggung jawab |
|---|---|---|---|
| Admin System | Admin | `admin` | Administrasi akun, konfigurasi, dan pengawasan sistem |
| Project Management | Lead | `lead` | Pengelolaan engagement, scope/RoE, anggota, koordinasi dan status proyek |
| Engineer-Head Offensive Security | Peninjau (Reviewer) | `reviewer` | Review/approval temuan sesuai mekanisme empat mata dan pengawasan teknis |
| Engineer-Lead of Technical Writer | Technical Writer | `writer` | Narasi temuan, template, dan penyusunan laporan; tanpa akses bukti mentah |
| Engineer-Red Team | Penguji (Tester) | `tester` | Pelaksanaan pengujian berizin dan pencatatan temuan/bukti/retest |

**Batas RBAC penting:** Reviewer tidak mewarisi hak Lead untuk mengelola engagement, anggota, scope, atau RoE. Jika organisasi menghendaki Head Offensive Security memiliki hak tersebut, perubahan RBAC dan pengujian permission harus diajukan sebagai perubahan lingkup tersendiri.

### 4.2 Peran tata kelola proyek

- **Project Manager (PM):** menjaga baseline scope, jadwal, risiko, stakeholder, keputusan, komunikasi, change control, dan acceptance evidence. PM tidak diasumsikan sebagai Program Analyst.
- **Program Analyst:** menerjemahkan kebutuhan ke analisis proses, requirement, data, API, desain teknis, dan dokumentasi analisis.
- **Tim pengembang/teknis:** mengimplementasikan backend, frontend, database, testing, CI, dan deployment sesuai pembagian tim aktual.
- **Stakeholder/pemberi masukan:** memberikan kebutuhan, review, persetujuan, dan penerimaan sesuai kewenangan.

Nama individu, kapasitas, dan alokasi tugas per sprint perlu dicatat pada roster tim proyek; tidak diasumsikan dalam dokumen ini.

## 5. Deliverables dan kriteria selesai

| Deliverable | Kriteria selesai |
|---|---|
| Aplikasi web SCOPELINE | Fitur dalam baseline berjalan sesuai acceptance test; role/permission tervalidasi |
| Database dan migrasi | Migrasi Alembic dapat diterapkan pada SQLite test dan PostgreSQL |
| Kalkulator CVSS | v4.0 aktif; input vector divalidasi; skor server-side; histori v3.1 tidak hilang |
| Alur review dan retest | Transisi status, aturan empat mata, ronde retest, dan bukti dapat diuji |
| Laporan DOCX | Template tervalidasi; versi CVSS dan histori tampil; laporan final memuat temuan approved |
| CI dan deployment | CI lulus pada commit rilis; deployment production diverifikasi; health dan acceptance runtime dibuktikan |
| Dokumentasi proyek | README, baseline implementasi, deployment status, matriks role, changelog, panduan kontribusi, keamanan, dan PMP konsisten |
| Paket akademik PM | Makalah/PMP dan presentasi mencerminkan status aktual, keputusan, risiko, dan bukti penerimaan |

## 6. Jadwal dan pengendalian waktu

### 6.1 Baseline jadwal proposal

- Durasi rencana: **24 minggu**.
- Struktur: **6 sprint**.
- Buffer kapasitas: **20%** untuk risiko, rework, integrasi, dan acceptance.
- Prioritas: Must dikerjakan sebelum Should; Could hanya jika kapasitas dan risiko memungkinkan.

Tanggal mulai/akhir tiap sprint tidak tercantum dalam sumber baseline yang diperiksa. PM harus mengisi tanggal aktual berdasarkan kalender akademik dan menyimpan sprint plan/review sebagai bukti.

### 6.2 Gate per sprint

1. Sprint planning: tujuan sprint, backlog terpilih, kapasitas, dependensi, dan risiko.
2. Daily coordination: hambatan, perubahan prioritas, dan eskalasi.
3. Sprint review: demo berdasarkan acceptance criteria, bukan klaim verbal.
4. Sprint retrospective: tindakan perbaikan dengan owner dan tenggat.
5. Update baseline: progres, risiko, keputusan, dan perubahan disimpan dalam log proyek.

### 6.3 Aturan status

- **Not started:** belum ada pekerjaan terverifikasi.
- **In progress:** pekerjaan berlangsung, belum memenuhi seluruh acceptance.
- **Blocked:** dependensi/risiko menghambat; wajib ada owner dan rencana mitigasi.
- **Done:** acceptance criteria lulus dan bukti tersedia.
- **Accepted:** stakeholder yang berwenang menyetujui deliverable.

## 7. RACI ringkas

R = Responsible, A = Accountable, C = Consulted, I = Informed. RACI berikut adalah usulan tata kelola; nama orang harus diisi pada project roster.

| Aktivitas | PM | Program Analyst | Tim teknis | Stakeholder |
|---|---:|---:|---:|---:|
| Baseline scope/jadwal/risiko | A/R | C | C | I |
| Elicitation dan analisis kebutuhan | A | R | C | C |
| Desain proses/data/API | I | A/R | R/C | C |
| Implementasi aplikasi | I | C | A/R | I |
| Pengujian teknis dan perbaikan defect | I | C | A/R | C |
| Pengendalian perubahan | A/R | C | C | C |
| Demo dan review deliverable | A/R | C | R | C |
| Acceptance akhir | R | C | C | A |
| Laporan status dan komunikasi | A/R | C | C | I |

## 8. Pengelolaan kebutuhan dan perubahan

1. Setiap kebutuhan dicatat dengan ID, deskripsi, prioritas MoSCoW, alasan bisnis, owner, acceptance criteria, dependensi, dan status.
2. Perubahan diajukan melalui issue/Change Request yang menyebutkan alasan, dampak scope, jadwal, biaya/kapasitas, risiko, keamanan, data, dan dokumentasi.
3. PM menilai dampak dan meminta persetujuan stakeholder berwenang sebelum baseline berubah.
4. Perubahan teknis yang menyentuh autentikasi, RBAC, data historis, migrasi, atau kalkulasi CVSS wajib memiliki test regression dan rencana rollback.
5. Perubahan tidak dianggap selesai hanya karena merge; CI, deployment, dan acceptance yang relevan harus diverifikasi.

### Keputusan CVSS

CVSS v4.0 diputuskan sebagai kalkulator aktif dan telah diimplementasikan serta digabung ke `main` melalui PR #9. v3.1 dipertahankan sebagai histori. Vector v4.0 dinilai oleh kalkulator server-side; pengguna memilih metrik, bukan memasukkan skor final sembarang. Rujukan normatif: [FIRST CVSS v4.0 Specification](https://www.first.org/cvss/v4.0/specification-document).

## 9. Rencana mutu dan acceptance

### 9.1 Quality gates

- Ruff lint lulus.
- Bandit static security check lulus.
- pip-audit tidak melaporkan dependency issue yang memblokir pipeline.
- Tes backend SQLite lulus dan coverage minimal 70%.
- Tes migrasi/relasi PostgreSQL lulus.
- E2E UI lulus.
- Docker Compose build lulus.
- Manual review security dan OWASP ASVS L1 checklist dilakukan; checklist adalah self-assessment, bukan sertifikasi independen.

### 9.2 Acceptance produk

- User tanpa autentikasi menerima 401; role tidak berwenang menerima 403.
- Akses setiap role dibatasi sesuai matriks RBAC.
- Engagement tidak aktif sebelum scope/RoE disetujui.
- Perubahan scope/RoE membatalkan persetujuan terkait.
- Skor CVSS v4.0 dihitung server; vector invalid ditolak.
- Penilaian historis v3.1 tidak hilang ketika migrasi atau reassessment.
- Pembuat temuan tidak dapat menyetujui temuannya sendiri.
- Laporan final hanya memuat temuan approved secara default.
- Technical Writer tidak dapat mengakses bukti mentah.
- Bukti upload/download, audit log, retest, dan DOCX diuji pada lingkungan target.

### 9.3 Acceptance deployment

Deployment berstatus READY bukan bukti runtime sehat. Sebelum sign-off, lampirkan bukti:
- Health endpoint HTTP 200.
- Login dan rotasi kredensial awal.
- Uji role/permission dan alur engagement.
- Uji create/update finding dengan CVSS v4.0.
- Upload/download evidence dan persistensi PostgreSQL.
- DOCX report dan audit log.
- TLS, backup/restore, retensi, serta konfigurasi akses database.
- Catatan deployment ID, commit SHA, waktu, tester, hasil, dan bukti.

## 10. Register risiko

Skala probabilitas dan dampak: Rendah / Sedang / Tinggi. Nilai awal adalah penilaian manajemen untuk dipantau, bukan hasil pengukuran statistik.

| ID | Risiko | Prob. | Dampak | Mitigasi / respons | Owner |
|---|---|---|---|---|---|
| R-01 | Perubahan kebutuhan memperluas scope | Sedang | Tinggi | Change Request, MoSCoW, persetujuan PM/stakeholder, lindungi Must | PM |
| R-02 | Jadwal akademik dan kapasitas tim bergeser | Sedang | Tinggi | Buffer 20%, sprint review, reforecast, eskalasi blocker | PM |
| R-03 | Salah konfigurasi RBAC atau akses bukti | Sedang | Tinggi | Matriks permission, tes 401/403 per role, negative tests | Tim teknis |
| R-04 | Migrasi CVSS merusak penilaian historis | Sedang | Tinggi | Snapshot v3.1, migrasi reversible/backup, regression test | Tim teknis |
| R-05 | Hasil kalkulasi CVSS tidak konsisten | Rendah/Sedang | Tinggi | Library teruji, vector test vectors, server-side scoring | Tim teknis |
| R-06 | Runtime Vercel gagal meski build READY | Sedang | Tinggi | Health check, acceptance checklist, log dan rollback | Tim teknis |
| R-07 | Kehilangan bukti/attachment | Sedang | Tinggi | PostgreSQL persisten, backup/restore test, retensi dan akses | Admin System |
| R-08 | Data target nyata dipakai tanpa izin | Rendah/Sedang | Tinggi | Data sintetis default; izin tertulis; sanitasi data | PM/Lead |
| R-09 | Temuan sensitif bocor melalui laporan/role | Sedang | Tinggi | Review laporan, RBAC, pembatasan bukti, audit log | Reviewer |
| R-10 | Ketergantungan layanan gratis berubah | Sedang | Sedang | Pantau limit, dokumentasi alternatif, rencana migrasi | PM/Lead |
| R-11 | Dokumentasi berbeda dari source code | Sedang | Sedang | Update changelog/baseline setiap release, source + tests sebagai acuan as-built | PM/Program Analyst |

Risiko harus ditinjau minimal setiap sprint review dan saat perubahan mayor/deployment. Risiko tinggi memerlukan owner, tanggal tindak lanjut, dan status mitigasi.

## 11. Komunikasi dan pelaporan

| Forum/artefak | Frekuensi | Isi minimum | Owner |
|---|---|---|---|
| Koordinasi tim | Harian/menyesuaikan ritme tim | Kemarin, hari ini, blocker | PM fasilitator |
| Sprint planning | Awal sprint | Goal, backlog, kapasitas, risiko | PM + tim |
| Sprint review | Akhir sprint | Demo, acceptance, defect, keputusan | PM |
| Retrospective | Akhir sprint | Yang berjalan/terhambat, action item | PM |
| Status report | Mingguan | Scope, jadwal, risiko, issue, keputusan, next step | PM |
| Change log | Setiap perubahan | Request, analisis dampak, approval, implementasi | PM |
| Release record | Setiap rilis | Commit, CI, deployment, smoke test, rollback | Tim teknis |

Keputusan penting dicatat dengan tanggal, konteks, alternatif, keputusan, approver, dampak, dan tautan bukti.

## 12. Pengadaan, dependensi, dan asumsi

- Deployment mengandalkan GitHub Actions dan Vercel; PostgreSQL persisten diperlukan untuk production.
- Vercel Production menggunakan batas runtime yang membuat PDF nonaktif; DOCX adalah jalur laporan yang disiapkan.
- Dependensi pihak ketiga harus dipin/diatur rentang versinya dan diaudit melalui CI.
- Data pengujian default adalah data sintetis. Kasus SAWALA hanya boleh dipakai setelah izin dan sanitasi dipastikan.
- Lisensi repository belum ditetapkan; jangan mengasumsikan penggunaan ulang kode di bawah lisensi open-source sebelum file LICENSE disetujui pemilik proyek.

## 13. Status, keputusan, dan tindak lanjut pada 11 November 2026

### Selesai/terverifikasi
- Pemetaan lima jabatan ke lima role aplikasi disetujui sebagai nomenklatur; permission tetap mengikuti matriks kode.
- CVSS v4.0 telah diimplementasikan dan PR #9 digabung ke `main`.
- CI branch PR #9 lulus untuk SQLite, PostgreSQL, E2E, lint, security/dependency checks, coverage gate, dan Docker Compose build.
- README, changelog, baseline implementasi, dan deployment status diselaraskan dengan merge.

### Belum boleh diklaim selesai
- CI pada commit merge `bca1d52479aa7537df025c4a3dc84d2807453705` masih berjalan pada pemeriksaan terakhir.
- Deployment Vercel untuk commit aplikasi CVSS v4.0 telah berstatus READY; deployment dokumentasi yang lebih baru mengikuti auto-deploy GitHub dan harus dicek pada status deployment terbaru. Runtime acceptance bisnis masih belum diverifikasi.
- Runtime acceptance production, backup/restore, TLS, retensi, dan health check belum memiliki bukti sign-off.
- Tanggal realisasi sprint, actual effort, dan acceptance stakeholder belum disediakan; PM perlu mengisi dari catatan proyek.

### Tindak lanjut prioritas
1. Pastikan CI pasca-merge lulus.
2. Verifikasi deployment Vercel pada commit merge dan jalankan smoke/acceptance tests.
3. Lengkapi bukti acceptance per role dan per alur bisnis.
4. Sinkronkan makalah akademik dan presentasi PM dengan baseline ini.
5. Tetapkan lisensi, aturan branch protection/review, dan jadwal release bersama pemilik repository.

## 14. Persetujuan

| Peran | Nama | Tanggal | Persetujuan |
|---|---|---|---|
| Project Manager | Diisi tim | — | — |
| Program Analyst | Diisi tim | — | — |
| Perwakilan teknis | Diisi tim | — | — |
| Stakeholder/pembimbing | Diisi tim | — | — |

---

**Catatan penggunaan:** dokumen ini adalah rencana dan baseline manajemen proyek, bukan bukti bahwa semua target telah diterima. Perbarui status, owner, tanggal, keputusan, dan bukti setiap kali sprint/release selesai.
