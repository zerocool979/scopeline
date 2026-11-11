# Matriks peran dan izin (v1.1)

✅ boleh · — tidak boleh · 🔸 dengan syarat (lihat catatan). "Ditugaskan" = menjadi anggota engagement tersebut.\n\n**Pemetaan nama jabatan organisasi untuk dokumen proyek:** Admin System = Admin; Project Management = Lead; Engineer-Head Offensive Security = Peninjau (Reviewer); Engineer-Lead of Technical Writer = Technical Writer; Engineer-Red Team = Penguji (Tester). Pemetaan ini hanya menyelaraskan nomenklatur. Hak akses tetap mengikuti kolom matriks dan kode role aplikasi. Khususnya, Peninjau tidak memperoleh hak pengelolaan engagement/anggota/RoE milik Lead.

| Kemampuan | Admin | Lead | Penguji | Peninjau | Tech. Writer |
|---|---|---|---|---|---|
| Kelola pengguna (buat, ubah peran, nonaktifkan, reset sandi) | ✅ | — | — | — | — |
| Lihat engagement | semua | semua | 🔸 ditugaskan | 🔸 ditugaskan | 🔸 ditugaskan |
| Buat/ubah engagement, tetapkan anggota, ubah status | ✅ | ✅ | — | — | — |
| Setujui RoE | ✅ | ✅ | — | — | — |
| Buat temuan, ubah CVSS/tenggat, unggah bukti, impor CSV | ✅ | ✅ | ✅ (engagement aktif) | — | — |
| Sunting **teks** temuan (judul, deskripsi, dampak, rekomendasi) | ✅ | ✅ | ✅ | — | ✅ (aktif **atau selesai**) |
| Lihat/unduh **bukti mentah** | ✅ | ✅ | ✅ | ✅ | — |
| Tandai diperbaiki / buka kembali | ✅ | ✅ | ✅ | — | — |
| Catat ronde retest + bukti retest | ✅ | ✅ | ✅ | — | — |
| Ajukan review temuan | ✅ | ✅ | ✅ | — | ✅ |
| Setujui / minta perubahan | ✅ 🔸 | ✅ 🔸 | — | ✅ | — |
| Hapus temuan | ✅ | ✅ | — | — | — |
| Ekspor laporan DOCX/PDF (pretest/retest) | ✅ | ✅ | ✅ | ✅ | ✅ 🔸 tanpa bukti mentah |
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
