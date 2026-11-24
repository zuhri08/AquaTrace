# AquaTrace

AquaTrace adalah aplikasi simulasi untuk pelaporan sumber, antrean dan diagnosis
sampel, riwayat uji, pelacakan jaringan air, dan pemantauan sensor IoT. Seluruh
data demo adalah simulasi.

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

Ubah `SECRET_KEY` pada `.env` sebelum penggunaan selain demo lokal. Seed dapat
dijalankan berulang kali tanpa menggandakan data.

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

## Kredit desain visual

Arahan visual mengikuti brief proyek `AQUATRACE_PROMPT_DESAIN_META.md` yang
diberikan pengguna; file brief tersebut tidak disertakan di repositori ini.
Pemetaan implementasi dan batasan tata letak dicatat dalam
`docs/desain/design-system.md`. Montserrat, JetBrains Mono, dan Material Symbols
Outlines dimuat melalui Google Fonts; konfigurasi Tailwind memakai CDN v3.4.17.
Koneksi eksternal diperlukan untuk font, ikon, dan utility Tailwind dari CDN.

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

Seluruh data yang di-seed adalah data simulasi tanpa identitas atau alamat asli.
Angka pengukuran seed bukan klaim baku mutu. Ambang resmi belum diisi dan harus
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
