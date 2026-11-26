# AquaTrace

AquaTrace adalah aplikasi untuk pelaporan sumber, antrean dan diagnosis sampel,
riwayat uji, pelacakan jaringan air, dan pemantauan sensor IoT. Pengukuran,
sampel, dan telemetri demo adalah simulasi; geometri sungai dan hierarki wilayah
memakai snapshot data nyata yang mencantumkan sumbernya.

## Persyaratan

- Python 3.12 atau lebih baru
- SQLite untuk pengembangan dan pengujian lokal
- MySQL 8+ opsional untuk penggunaan multi-user; koneksi dikonfigurasi melalui
  `DATABASE_URL`

## Instalasi awal

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python seed.py
python run.py
pytest
```

**Peringatan keamanan:** `SECRET_KEY` bawaan pada `config.py` hanya untuk
pengembangan. Sebelum deploy atau penggunaan di luar lingkungan lokal, wajib
tetapkan `SECRET_KEY` acak dan rahasia di `.env`/secret manager; jangan gunakan
nilai bawaan atau commit rahasia ke Git. Seed dapat dijalankan berulang kali
tanpa menggandakan data.

Untuk mensimulasikan sensor, gunakan contoh perintah pada
[docs/iot/README.md](./docs/iot/README.md). Nilai ambang saat ini hanya contoh.

## Fitur saat ini

- Akun demo tiga role, akses role di server, dan CSRF pada form.
- Warga dapat melaporkan sumber, mengajukan sampel, dan melihat antrean/status.
- Petugas dapat mengambil sampel FIFO prioritas, menjalankan wizard diagnosis,
  mengurungkan hasil, serta mengoreksi/menghapus riwayat.
- Admin dapat melihat hitungan tercemar per wilayah dan mengelola edge jaringan.
- IoT menerima telemetri ber-API-key, memproses antrean, membentuk sampel
  prioritas untuk hasil sensor `TIDAK_LAYAK`, dan menyediakan simulator.
- UI responsif tersedia untuk warga, petugas, admin, dan publik; visualisasi
  struktur data mengambil payload dari API role-aware.
- `/publik` menampilkan ringkasan terbatas data publik; `/styleguide` hanya
  tersedia bagi admin.

Lihat [docs/iot/README.md](./docs/iot/README.md) untuk protokol IoT dan simulator.
Lihat [docs/desain/design-system.md](./docs/desain/design-system.md) untuk
token visual, komponen, dan pedoman aksesibilitas.

## Sumber dan Kredit

- Geometri Kali Surabaya, Kali Jagir, dan Kali Mas diambil dari OpenStreetMap
  API/Overpass; jarak edge dihitung mengikuti urutan node way OSM. Arah way
  `waterway=river` mengikuti konvensi OSM dari hulu ke hilir
  ([dokumentasi OSM](https://wiki.openstreetmap.org/wiki/Tag:waterway%3Driver)).
  Kredit: **© OpenStreetMap contributors**. Data tersedia di bawah
  [ODbL 1.0](https://www.openstreetmap.org/copyright).
- Hierarki Provinsi Jawa Timur, kabupaten/kota, dan kecamatan bersumber dari
  [BPS WebGIS Kode Relasi Wilayah](https://sig.bps.go.id/kode-relasi), periode
  BPS 2024 dan Kemendagri 2025.
- Snapshot dan referensi sumber ada di `data/nyata/`. Titik geometri OSM bukan
  klaim lokasi bendung, intake PDAM, atau stasiun pantau. Titik yang belum
  terverifikasi dibiarkan `NULL` dan dicatat sebagai TODO. Hubungan ke kecamatan
  juga tidak diisi tanpa batas administratif resmi untuk spatial join.
- Belum ada hasil uji publikasi yang dimasukkan. Isi `data/nyata/hasil_uji.csv`
  hanya dari publikasi terverifikasi, lalu jalankan
  `python scripts/import_data_nyata.py --import-results`. Hasil publikasi
  disimpan tanpa vonis dari ambang contoh AquaTrace.
- Hasil laboratorium seed, sampel warga, pembacaan sensor, dan wilayah berlabel
  simulasi tetap merupakan data demo; tidak ditempatkan pada titik intake PDAM.

## Kredit desain visual

Aturan visual proyek dicatat di
[docs/desain/AQUATRACE_PROMPT_DESAIN_META.md](./docs/desain/AQUATRACE_PROMPT_DESAIN_META.md);
implementasi dan rasio kontras ada di [docs/desain/design-system.md](./docs/desain/design-system.md).
Font Montserrat v31, JetBrains Mono v24, dan Material Symbols Outlined v387
dihost lokal di `app/static/fonts/` untuk demo offline. Lisensi OFL dan Apache-2.0
disertakan bersama aset. CSS dan JavaScript lokal menyediakan semua komponen;
Tailwind CDN tidak digunakan. `tailwind-config.js` menyimpan padanan token untuk
alat build Tailwind bila diperlukan, tetapi tidak dibutuhkan aplikasi runtime.
Tanpa internet, font/icon/font stack cadangan lokal/system tetap tersedia.

## Konfigurasi MySQL

Buat database dan akun MySQL secara manual, lalu isi `.env`:

```dotenv
DATABASE_URL=mysql+pymysql://aquatrace:password@localhost:3306/aquatrace?charset=utf8mb4
```

`PyMySQL` sudah dicantumkan sebagai driver. Jangan gunakan kredensial contoh di
lingkungan publik.

## Autentikasi dan multi-user

Pendaftaran publik membuat akun dengan role `warga`; akun staf dibuat melalui
seed atau nantinya dikelola admin. Kata sandi disimpan sebagai hash Werkzeug,
formulir POST dilindungi CSRF, dan akses role diperiksa di server. Request
mengambil data akun dari sesi dan database, bukan state antrean global dalam
memori. Operasi antrean lintas petugas harus dilakukan dalam transaksi database
dengan penguncian baris (`SELECT ... FOR UPDATE`) agar satu sampel tidak diambil
dua kali; SQLite menserialisasi penulisan, sedangkan locking baris berlaku pada
MySQL.

## Akun demo

Semua akun demo memakai kata sandi `AquaTraceDemo123!`:

- `admin@aquatrace.test`
- `petugas@aquatrace.test`
- `warga@aquatrace.test`

API key demo (khusus data simulasi lokal; seed hanya menyimpan hash):

| Perangkat | API key |
|---|---|
| SENSOR-01 | `demo-sensor-01-key` |
| SENSOR-02 | `demo-sensor-02-key` |
| SENSOR-03 | `demo-sensor-03-key` |
| SENSOR-04 | `demo-sensor-04-key` |

## Data dan batasan

Hanya geometri sungai dan hierarki administratif yang bersumber dari data nyata.
Sampel, hasil uji seed, dan telemetri adalah data simulasi tanpa identitas warga
atau klaim alamat sampling nyata. Angka pengukuran seed bukan klaim baku mutu.
Ambang resmi belum diisi dan harus
diverifikasi manusia dari regulasi yang berlaku sebelum dipakai untuk keputusan.
Sistem ditujukan untuk screening, bukan pengganti pengujian laboratorium lengkap.
`app/config/thresholds.py` berisi nilai contoh untuk mendemonstrasikan cabang
pohon keputusan. Nilai tersebut bukan angka baku mutu resmi dan ditandai
`CONTOH, ISI DARI DOKUMEN RESMI`.

## Penggunaan AI

Implementasi awal dikerjakan dengan bantuan AI assistant menggunakan Copilot SDK
di VS Code. Peran AI adalah membantu membaca spesifikasi, menulis kode dan tes,
serta menjalankan validasi yang tercantum pada laporan pengerjaan. Kebijakan dan
pengungkapan penggunaan AI perlu dikonfirmasi kepada dosen pengampu.
