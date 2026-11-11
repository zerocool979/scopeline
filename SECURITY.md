# Kebijakan Keamanan

## Lingkup

Kebijakan ini berlaku untuk source code dan deployment SCOPELINE pada repository ini. SCOPELINE menangani informasi sensitif engagement penetration testing; perlakukan temuan, bukti, identitas klien, kredensial, dan log sebagai data terbatas.

## Melaporkan kerentanan

**Jangan** membuka issue publik untuk kerentanan yang belum diperbaiki, kredensial, data pribadi, bukti target, atau detail eksploit.

Gunakan fitur **Private vulnerability reporting** GitHub pada halaman Security repository apabila fitur tersebut tersedia. Jika tidak tersedia, hubungi pemilik/maintainer repository melalui kanal privat yang disepakati tim. Sertakan:
- ringkasan dampak dan komponen terdampak;
- versi/commit dan konfigurasi relevan tanpa secret;
- langkah reproduksi minimal pada lingkungan yang dimiliki/diizinkan;
- bukti yang sudah disanitasi;
- mitigasi sementara jika diketahui.

Jangan menguji target pihak ketiga atau melakukan akses di luar otorisasi. Beri maintainer waktu yang wajar untuk triage dan koordinasi perbaikan sebelum disclosure publik.

## Praktik keamanan untuk kontributor

- Simpan secret hanya di secret manager/environment lokal; jangan commit file `.env`.
- Rotasi kredensial yang terungkap dan segera beri tahu maintainer.
- Gunakan data sintetis; data nyata wajib memiliki izin dan sanitasi.
- Jangan menambahkan endpoint atau fitur yang mengeksekusi scanning/exploitation/attack automation.
- Perubahan autentikasi, RBAC, evidence, migrasi, dan CVSS wajib memiliki tes regresi.
- CI menjalankan Bandit, pip-audit, test suite, coverage gate, dan E2E; hasil CI bukan pengganti security review manual.

## Batas jaminan

Checklist OWASP ASVS L1 di repository adalah self-assessment, bukan sertifikasi independen. TLS, enkripsi at-rest, backup, retensi, dan kontrol akses database juga bergantung pada konfigurasi platform/provider dan harus diverifikasi terpisah.
