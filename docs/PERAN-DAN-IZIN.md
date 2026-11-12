# Matriks peran dan izin (v1.1)

✅ boleh · — tidak boleh · 🔸 dengan syarat (lihat catatan). "Ditugaskan" = menjadi anggota engagement tersebut.\n\n**Pemetaan nama jabatan organisasi untuk dokumen proyek:** Admin System = Admin; Project Management = Lead; Engineer-Head Offensive Security = Peninjau (Reviewer); Engineer-Lead of Technical Writer = Technical Writer; Engineer-Red Team = Penguji (Tester). Pemetaan ini hanya menyelaraskan nomenklatur. Hak akses tetap mengikuti kolom matriks dan kode role aplikasi. Khususnya, Peninjau tidak memperoleh hak pengelolaan engagement/anggota/RoE milik Lead.

| Kemampuan | Admin | Lead | Penguji | Peninjau | Tech. Writer |
|---|---|---|---|---|---|
| Kelola pengguna (buat, ubah peran, nonaktifkan, reset sandi) | ✅ | — | — | — | — |
| Lihat engagement | semua | semua | 🔸 ditugaskan | 🔸 ditugaskan | 🔸 ditugaskan |
| Buat/ubah engagement, tetapkan anggota, ubah status | ✅ | ✅ | — | — | — |
| Setujui RoE | — | ✅ (Project Manager) | — | ✅ (Engineer-Head) | — |
| Buat temuan, ubah CVSS/tenggat, unggah bukti, impor CSV | ✅ | ✅ | ✅ (engagement aktif) | — | — |
| Sunting **teks** temuan (judul, deskripsi, dampak, rekomendasi) | ✅ | ✅ | ✅ | — | ✅ (aktif **atau selesai**) |
| Lihat/unduh **bukti mentah** | — | ✅ | ✅ | ✅ | — |
| Tandai diperbaiki / buka kembali | ✅ | ✅ | ✅ | — | — |
| Catat ronde retest + bukti retest | ✅ | ✅ | ✅ | — | — |
| Ajukan review temuan | ✅ | ✅ | ✅ | — | ✅ |
| Setujui / minta perubahan | — | ✅ 🔸 | — | ✅ 🔸 | — |
| Hapus temuan | ✅ | ✅ | — | — | — |
| Ekspor laporan DOCX/PDF (pretest/retest) | sesuai izin, tanpa bukti mentah | ✅ 🔸 perlu persetujuan dua pihak | ✅ 🔸 perlu persetujuan dua pihak | ✅ 🔸 tanpa bukti mentah | ✅ 🔸 tanpa bukti mentah |
| Unggah / aktifkan / rollback **templat laporan** | ✅ | ✅ | — | — | ✅ |
| Kelola **templat catatan (.md)** | ✅ | ✅ | — | — | — |
| Pakai templat catatan untuk catatan pribadi | ✅ | ✅ | ✅ | — | — |
| Kelola pustaka templat temuan | ✅ | ✅ | — | — | — |
| Baca/tulis **catatan tim** | ✅ / ✅ | ✅ / ✅ | ✅ / ✅ | ✅ / — | — / — |
| Catatan **pribadi** | baca semua, tulis miliknya | baca semua, tulis miliknya | miliknya | — | — |
| Log audit | ✅ | ✅ | — | — | — |
| Dasbor | ✅ | ✅ | ✅ | ✅ | ✅ |

Catatan:
- 🔸 **Empat mata**: pembuat temuan tidak dapat menyetujui temuannya sendiri, termasuk Lead/Admin.
- 🔸 **Technical Writer** tidak melihat bukti (tidak ada di UI, API mengosongkan daftar bukti dan menolak unduhan, dan laporan yang ia ekspor tidak menyertakan gambar bukti).
- Review dan penyuntingan teks laporan diperbolehkan pada engagement **aktif atau selesai**; perubahan data teknis (CVSS, bukti, retest) hanya saat **aktif**.
- Mengubah isi temuan yang berstatus *Menunggu review/Disetujui* mengembalikannya ke *Draf*.
- Laporan **final** hanya memuat temuan *Disetujui*; opsi "sertakan belum disetujui" menandai dokumen **DRAF**.


## Keputusan persetujuan terbaru

- **RoE:** wajib disetujui oleh Project Manager (role aplikasi `lead`) dan Engineer-Head Offensive Security (role aplikasi `reviewer`). Engagement tidak dapat diaktifkan sebelum kedua persetujuan tercatat. Perubahan scope atau RoE menghapus kedua persetujuan.
- **Laporan final:** wajib memperoleh persetujuan Project Manager dan Engineer-Head Offensive Security. Persetujuan terikat pada sidik versi data engagement, finding, retest, dan template; perubahan data membuat persetujuan lama tidak berlaku untuk versi terbaru.
- **Raw evidence:** Admin tidak memiliki akses unduh maupun akses bukti mentah melalui respons finding/laporan. Admin tidak dapat mengunggah atau menghapus evidence. Akses operasional evidence diberikan kepada Lead dan Tester sesuai penugasan; Reviewer dapat mengakses untuk keperluan review.
