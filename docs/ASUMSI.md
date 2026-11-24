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
- `Stack.pop()` dan `Stack.peek()` melempar `IndexError` saat kosong; operasi
  baca/hapus Queue dan Linked List mengembalikan `None` jika tidak ada elemen.
- `PriorityAwareQueue` menjaga FIFO pada tiap lajur dan selalu mengeluarkan
  antrean prioritas sebelum antrean reguler.
- Graph adalah berarah; bobot edge wajib positif dan berhingga. Edge ganda
  dengan arah sama serta edge ke diri sendiri ditolak.
- Node keputusan memakai kondisi biner `feature/operator/threshold` dengan dua
  cabang dan daun yang memiliki vonis. Evaluasi mengembalikan jejak kondisi;
  konfigurasi ambang untuk produk akan ditambahkan pada fase diagnosis.

## Fase 4

- SQLite tidak menyediakan `SELECT FOR UPDATE`. Klaim sampel menggunakan satu
  pernyataan `UPDATE ... WHERE id = (SELECT ... ORDER BY ... LIMIT 1) AND
  status='menunggu' RETURNING id`; pemilihan dan perubahan status terjadi atomik
  di satu statement. Penulis SQLite diserialisasi dan `busy_timeout=5000`
  memberi waktu menunggu lock. Predicate status mencegah klaim ulang. Tes
  paralel memakai koneksi/thread terpisah untuk memastikan dua petugas tidak
  menerima ID yang sama.
- Pada MySQL, baris kandidat dikunci memakai `SELECT ... FOR UPDATE`, lalu
  statusnya diubah dan transaksi di-commit.
- Struktur antrean dibangun ulang dari database per request; instance Queue
  bukan sumber kebenaran. Role admin dapat membuka endpoint operasional petugas.

## Fase 5

- `app/config/thresholds.py` memuat nilai demonstrasi saja dan menandainya
  `CONTOH, ISI DARI DOKUMEN RESMI`. Nilai ini bukan hasil verifikasi regulasi;
  `REGULATION_SOURCE` sengaja kosong dan UI memberi label nilai contoh.
- Pohon screening contoh menggolongkan pH di luar rentang contoh sebagai
  `TIDAK_LAYAK`; kekeruhan atau TDS di atas contoh sebagai `WASPADA`; nilai
  lainnya sebagai `BERSIH`. Ini hanya contoh alur keputusan, bukan keputusan
  kepatuhan terhadap baku mutu resmi.
- Rentang fisik untuk validasi masukan pH, kekeruhan, dan TDS mengikuti batas
  validasi simulasi PRD dan tidak dipakai sebagai ambang kelayakan.
- Pengukuran wizard disimpan sementara di sesi, lalu seluruh hasil, perubahan
  status sampel/sumber, dan aksi undo dipersistenkan dalam satu transaksi DB.
- Penyimpanan hasil memakai conditional update pada sampel `diproses` di SQLite
  dan `SELECT FOR UPDATE` di MySQL. Unique constraint satu hasil per sampel
  menjadi perlindungan tambahan; undo menghapus hasil itu sebelum sampel
  dikembalikan ke antrean.
