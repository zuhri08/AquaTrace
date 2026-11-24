# Asumsi dan Keputusan

Dokumen ini mencatat keputusan yang diperlukan karena workspace awal tidak
menyediakan implementasi atau data proyek.

## Fase 0

- Workspace `D:\web\AquaTrace` kosong dan belum memiliki repositori Git. Repositori
  lokal diinisialisasi agar perubahan dapat dipisah sesuai fase.
- Python 3.12.5, `pip`, `pytest`, dan SQLite tersedia. Perintah `mysql` tidak
  ditemukan, sehingga pengembangan dan pengujian memakai SQLite. MySQL tetap
  menjadi opsi produksi melalui URL database di `.env`.
- File referensi `docs/desain/referensi/index.html` tidak tersedia di workspace.
  Tidak ada tata letak spesifik yang diasumsikan dari referensi yang tidak ada.
- `AQUATRACE_PRD_AGENT (1).md` dan `AQUATRACE_PROMPT_DESAIN_META.md` yang diberikan
  pengguna menjadi sumber kebutuhan. Prompt Meta mengatur visual bila fase UI
  dikerjakan; PRD mengatur fitur, data, database, dan IoT.
- Ambang baku mutu resmi tidak akan diisi tanpa verifikasi manusia terhadap
  dokumen regulasi. Fase 0–3 tidak menetapkan ambang.

## Fase 1–3

- Primary key dibuat integer auto-increment untuk kemudahan relasi, sementara
  tipe boolean dan timestamp dimodelkan secara portabel melalui SQLAlchemy.
- SQLite in-memory/file digunakan untuk tes; SQLite foreign key diaktifkan per
  koneksi. MySQL memakai driver PyMySQL dan mendukung transaksi SQLAlchemy.
- Pembuatan API key demo memperlihatkan key mentah hanya saat seed berjalan;
  basis data hanya menyimpan hash SHA-256. Kredensial seed bersifat lokal/demo,
  bukan untuk lingkungan publik.
