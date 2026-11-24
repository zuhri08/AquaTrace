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

## Fase 6

- Riwayat ditampilkan dari hasil uji pada database dalam urutan waktu naik dan
  dimuat ke `LinkedList` per request; database tetap menjadi sumber kebenaran.
- Koreksi nilai menjalankan ulang pohon keputusan contoh dan memperbarui vonis
  serta jejak, tanpa mengubah tanggal uji. Penghapusan hasil mengembalikan
  sampel ke `menunggu`; status sumber lab dihitung ulang dari hasil terbaru,
  atau `belum_diuji` bila tidak ada yang tersisa.
- Riwayat warga dapat dibaca untuk sumber mana pun, sesuai akses riwayat publik
  pada PRD. Halaman tidak menampilkan email atau identitas pengaju/penguji.
- Dashboard wilayah menyimpan hitungan sumber tercemar langsung pada simpul
  pohon; hitungan dikalkulasi rekursif dari `water_sources.status_terakhir`,
  bukan dari indikator sensor.

## Fase 7

- Jaringan selalu dibangun ulang dari `water_sources` dan `river_edges` pada
  request; tidak ada cache graph yang dapat menjadi stale.
- Dampak hilir adalah semua node yang dapat dicapai melalui edge berarah, lalu
  diurutkan menurut jarak km terpendek hasil Dijkstra; rute terpilih ditampilkan
  bersama jarak.
- Pencarian sumber terdekat hanya mempertimbangkan sumber yang status hasil
  lab-nya `BERSIH`, bukan status sensor, dan harus memiliki jalur berarah dari
  sumber asal. Jika tidak ada jalur, hasilnya kosong dengan pesan.
- Edge adalah berarah hulu-ke-hilir, jarak finite dan positif, tidak boleh
  menuju diri sendiri atau mengulang pasangan terarah yang sama. Validasi ada
  di service dan constraint database.

## Fase 7B

- `sensor_readings.ts_sensor` menyimpan timestamp perangkat opsional untuk
  idempotensi; unique index pada `(device_id, ts_sensor)` menolak timestamp
  ganda, sedangkan `NULL` menandakan perangkat tidak mengirim timestamp.
  `seed.py` menambahkan kedua kolom IoT dan index secara aditif ketika seed
  dijalankan pada database SQLite/MySQL lama.
- Rate limit dihitung dari waktu penerimaan server, satu bacaan per 2 detik.
  `iot_devices.last_ingested_at` adalah kolom tambahan agar pemeriksaan dan
  reservasi rate limit atomik. SQLite memakai conditional `UPDATE ... RETURNING`
  dan timeout penulis; MySQL mengunci baris perangkat dengan `SELECT FOR UPDATE`.
- Status pembacaan `diproses` berarti telah dievaluasi; `diproses_at` dan vonis
  terisi. Proses memakai Queue manual yang dibangun dari bacaan `antri` berurutan
  waktu/id. Klaim bersyarat mencegah worker ganda memproses bacaan yang sama.
- Perubahan status sensor dan pembuatan sampel prioritas IoT berada dalam satu
  transaksi. Sebelum pengecekan sampel terbuka pada SQLite, penulisan sumber
  dalam transaksi mengambil lock writer SQLite; MySQL memakai lock baris sumber.
- API key perangkat dibuat acak, hanya hash SHA-256 disimpan, dan key plaintext
  dikirim sekali pada response HTML pendaftaran (tidak ditaruh di cookie sesi).
- `IOT_AUTO_PROSES` memproses antrean setelah ingest secara default; untuk demo
  manual set `false`. Sensor dianggap offline bila bacaan terakhir lebih lama
  dari lima menit. Nilai ini adalah batas operasional aplikasi, bukan regulasi.
- Pembacaan sensor memakai pohon screening fase 5 dan ambang yang sama, tetap
  bernilai contoh. Modul simulator dan contoh ESP32 mengirim data simulasi atau
  placeholder; contoh perangkat keras secara eksplisit belum diuji.

## Fase 8

- API visualisasi menggunakan envelope `{data, last_operation, complexity}` dan
  menyusun payload dari struktur data manual serta database, bukan array contoh.
- Endpoint staf dibatasi `@role_required` sesuai data dan fungsi; endpoint data
  publik terpisah hanya mengembalikan informasi sensor/jaringan yang memang
  tampil di halaman publik, tanpa data pengaju/penguji.
- Warga hanya menerima item antrean sampel miliknya; posisi berasal dari Queue
  penuh di server. Endpoint stack/decision tree dibatasi ke petugas/admin dan
  tree wilayah hanya admin.
- Feed menautkan sampel IoT berdasarkan sumber dan waktu pembuatan setelah
  bacaan diterima; skema yang tersedia tidak memiliki foreign key langsung dari
  bacaan ke sampel pemicu.

## Fase 9

- Halaman `/publik` dan endpoint `/api/public/...` hanya menampilkan ringkasan,
  jaringan, kode perangkat, bacaan, status, dan waktu; identitas pengguna tidak
  ikut ditampilkan. Statistik halaman dihitung dari baris sumber yang ada.
- `/styleguide` hanya dapat diakses role `admin`, agar seluruh contoh visual
  memakai endpoint API yang memang mensyaratkan role staf/admin.
- Visualisasi utama dirender dari envelope API. Nilai status/hasil yang sudah
  menjadi bagian alur kerja tetap dapat ditampilkan server-side sebagai teks;
  mode tanpa JavaScript pada dashboard wilayah juga memiliki fallback berbasis
  data database.
- Grafik sensor memakai urutan sampel dari API dan skala otomatis berdasarkan
  rentang nilai yang diterima; tidak ada nilai ambang resmi atau garis baku
  mutu yang ditambahkan.
- Brief `AQUATRACE_PROMPT_DESAIN_META.md` tidak tersedia sebagai file di
  workspace, tetapi arahan visual yang diberikan pengguna diterapkan:
  Montserrat, JetBrains Mono untuk angka, Material Symbols Outlined, tombol
  pil, kartu datar membulat, fokus keyboard, ikon dan teks untuk status,
  kobalt sebagai aksi utama, serta ungu khusus telemetri. Nilai warna dan
  perhitungan kontras didokumentasikan di `docs/desain/design-system.md`.
- Berkas tata letak referensi `docs/desain/referensi/index.html` tidak tersedia.
  UI memakai kerangka responsif staf/sidebar dan warga/navigasi bawah; struktur
  ini adalah adaptasi baru, bukan klaim menyalin tata letak referensi.
- Sumber font, ikon, dan Tailwind dimuat dari CDN eksternal; saat offline
  browser menggunakan fallback font dan CSS lokal, tetapi utility Tailwind,
  font, dan ikon eksternal tidak dijamin tersedia.
