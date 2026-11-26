# AquaTrace — Design System

## Sumber dan batas

`AQUATRACE_PROMPT_DESAIN_META.md` adalah aturan visual kanonis dan disimpan
sesuai teks yang diberikan pengguna. Pengguna meminta mengabaikan
`docs/desain/referensi/index.html`; karena itu implementasi mempertahankan
kerangka sidebar staf, header, tab warga, dan navigasi bawah yang telah ada,
tanpa mengacu pada atau mengklaim menyalin file referensi.

Tidak ada logo, nama, foto, atau font proprietary Meta yang digunakan.

## Token warna

| Token | Nilai | Aturan penggunaan |
|---|---|---|
| `canvas` | `#ffffff` | Latar utama |
| `surface-soft` | `#f1f4f7` | Permukaan lembut |
| `ink-deep` | `#0a1317` | Teks/badge gelap, banner informasi |
| `ink` | `#1c1e21` | Teks isi |
| `charcoal` | `#444950` | Hover tombol hitam |
| `slate` | `#4b4c4f` | Teks sekunder |
| `steel` | `#5d6c7b` | Navigasi/label sekunder |
| `stone` | `#8595a4` | Dekoratif/disabled saja, bukan teks informasi |
| `hairline` | `#ced0d4` | Batas input dan pemisah |
| `hairline-soft` | `#dee3e9` | Batas kartu |
| `disabled-text` | `#bcc0c4` | Teks kontrol nonaktif |
| `ink-button` | `#000000` | Tombol umum |
| `primary` | `#0064e0` | Aksi inti; sorotan jalur |
| `primary-deep` | `#0457cb` | State ditekan |
| `primary-soft` | `#0091ff` | Aksen dekoratif, bukan teks kecil |
| `fb-blue` | `#1876f2` | Cincin fokus |
| `selected-border` | `#0143b5` | Batas opsi terpilih |
| `oculus-purple` | `#a121ce` | IoT/telemetri saja |
| `success` | `#31a24c` | Status BERSIH; teks badge ink-deep |
| `warning` | `#f7b928` | Status WASPADA; teks badge ink-deep |
| `attention` | `#f2a918` | Perhatian; teks ink-deep |
| `critical` | `#e41e3f` | Status/error; teks putih hanya saat kontras lulus |
| `critical-strong` | `#f0284a` | Batas/outline error, bukan teks isi |

Komponen juga memakai tint permukaan yang sangat ringan untuk state visual:
`success-soft #e7f5eb`, `warning-soft #fff4d6`, `critical-soft #ffeaed`, dan
`telemetry-soft #f8e9fc`. Tint ini bukan warna status tambahan.

## Kontras WCAG 2.x

Rasio di bawah dihitung dengan luminans relatif sRGB. Target teks normal adalah
4.5:1; ikon/batas visual non-teks adalah 3:1. State yang gagal untuk teks tidak
digunakan sebagai teks; badge status menggunakan pasangan foreground/background
yang lulus.

| Foreground | Background | Rasio | Penggunaan / keputusan |
|---|---|---:|---|
| Putih `#fff` | Hitam `#000` | 21.00:1 | Lulus; tombol umum |
| Putih `#fff` | Ink deep `#0a1317` | 18.78:1 | Lulus; banner/pil gelap |
| Ink deep `#0a1317` | Putih `#fff` | 18.78:1 | Lulus; teks utama |
| Slate `#4b4c4f` | Surface soft `#f1f4f7` | 7.78:1 | Lulus; teks sekunder |
| Steel `#5d6c7b` | Surface soft `#f1f4f7` | 4.88:1 | Lulus; label |
| Putih `#fff` | Primary `#0064e0` | 5.39:1 | Lulus; aksi inti |
| Putih `#fff` | Primary deep `#0457cb` | 6.50:1 | Lulus; aksi ditekan |
| Kobalt `#0064e0` | Putih `#fff` | 5.39:1 | Lulus; link/fokus visual |
| Focus `#1876f2` | Putih `#fff` | 4.27:1 | Lulus untuk outline non-teks (>=3:1) |
| Focus `#1876f2` | Surface soft `#f1f4f7` | 3.87:1 | Lulus untuk outline non-teks |
| Selected `#0143b5` | Putih `#fff` | 8.50:1 | Lulus; batas terpilih |
| Oculus purple `#a121ce` | Putih `#fff` | 5.79:1 | Lulus; label IoT |
| Oculus purple `#a121ce` | Telemetry soft `#f8e9fc` | 4.98:1 | Lulus; aksen dan sparkline |
| Ink deep `#0a1317` | Success `#31a24c` | 5.73:1 | Lulus; badge BERSIH |
| Putih `#fff` | Success `#31a24c` | 3.28:1 | **Gagal** untuk teks normal; tidak dipakai di badge |
| Ink deep `#0a1317` | Warning `#f7b928` | 10.66:1 | Lulus; badge WASPADA |
| Putih `#fff` | Warning `#f7b928` | 1.76:1 | **Gagal**; tidak dipakai |
| Ink deep `#0a1317` | Attention `#f2a918` | 9.36:1 | Lulus; banner perhatian |
| Putih `#fff` | Critical `#e41e3f` | 4.61:1 | Lulus; badge dan tombol/error kritis |
| Critical `#e41e3f` | Critical soft `#ffeaed` | 4.00:1 | **Gagal** untuk teks normal; gunakan ink-deep |
| Ink deep `#0a1317` | Critical soft `#ffeaed` | 16.31:1 | Lulus; teks notifikasi/error |
| Ink deep `#0a1317` | Critical strong `#f0284a` | 4.57:1 | Lulus; foreground jika diperlukan |
| Critical strong `#f0284a` | Putih `#fff` | 4.11:1 | **Gagal** untuk teks normal; hanya border/outline |
| Putih `#fff` | Primary soft `#0091ff` | 3.23:1 | Hanya elemen besar/non-teks; tidak digunakan untuk teks kecil |
| Stone `#8595a4` | Putih `#fff` | 3.07:1 | Ikon dekoratif saja, bukan informasi |
| Disabled text `#bcc0c4` | Putih `#fff` | 1.83:1 | Nonaktif saja; tidak menyampaikan informasi aktif |

## Tipografi

- Montserrat v31 untuk antarmuka (300, 400, 500, 700); fallback Helvetica,
  Arial, Noto Sans.
- JetBrains Mono v24 untuk angka ukur, nilai sensor, dan data teknis.
- Material Symbols Outlined v387 untuk ikon; ikon status selalu didampingi teks.
- Semua font di-host lokal pada `app/static/fonts/`; lisensi disertakan. Tidak
  ada Optimistic VF atau aset Meta.
- Skala: hero 64/1.16/500; display 48/1.17/500; h-lg 36/1.28/500;
  h-md 28/1.21/300; h-sm 24/1.25/500; sub 18/1.44; body 16/1.5/400;
  body-sm 14/1.43; tombol/tab 14/700; caption 12/1.33.
- Body letter spacing: -0.16px pada 16px dan -0.14px pada 14px. Line-height
  body tetap minimal 1.5.
- Hero landing dan publik turun menjadi 36px di bawah 768px, lalu 24px di
  bawah 480px.

## Bentuk, spasi, elevasi

- Radius: xs 2px, sm 4px, md 6px, lg 8px, xl 16px, xxl 24px, xxxl 32px,
  feature 40px, full 100px, circle 50%.
- Tombol, tab, chip, dan badge selalu pil. Kartu utama 32px, kartu fitur dan
  visualisasi 16px, input 8px.
- Spasi mengikuti skala 4px (4–120px). Kontainer maksimal 1280px; kartu utama
  ber-padding 32px dan area padat dashboard 24px.
- Tidak ada bayangan pada kartu reguler atau navigasi bawah. Token
  `0 1px 4px rgba(20,22,26,.3)` hanya disediakan untuk panel aksi yang lengket
  (misalnya panel samping wizard atau bilah aksi bawah bila ditambahkan).
- Breakpoint CSS: <480, 480–767, 768–1023, 1024–1359, >=1360; target sentuh
  minimal 44px.
- Fokus: outline 2px `#1876f2`, offset 2px. Tidak ada mode gelap.

## Komponen dan adaptasi data

- Tombol umum berwarna hitam, sekunder outline 2px ink-deep; satu aksi inti
  per layar menggunakan kobalt. Landing memakai tombol putih di atas hero gelap
  agar tombol hitam/teks putih tidak kehilangan kontras.
- Header dan sidebar staf memakai navigasi pil, sidebar 256px; warga memakai
  tab atas dan bottom navigation empat item di mobile.
- Input tinggi 44px, radius 8px, fokus biru 2px; badge status menampilkan ikon,
  label, dan warna. Teks di badge success/warning adalah ink-deep.
- Tanpa fotografi. Hero landing/publik memakai gradasi ink-deep ke biru gelap.
- Ungu `#a121ce` hanya untuk status/lencana IoT dan sparkline.
- Wadah visualisasi radius 16px. Marker FRONT/REAR/TOP/HEAD/TAIL berbentuk pil
  ink-deep; angka memakai JetBrains Mono. Node graph berstatus success/warning/
  critical dengan ring putih 2px; jalur Dijkstra dan cabang evaluasi tersorot
  memakai kobalt.
- Animasi memakai transisi 150–250ms ease-out dan menghormati
  `prefers-reduced-motion`.
- Semua isi visual berasal dari API. Loading/error/kosong ditampilkan; rendering
  nilai memakai `textContent`.

## Tailwind dan operasi offline

Tailwind CDN dihapus: runtime memakai CSS/JavaScript lokal sehingga demo tetap
berfungsi tanpa internet. `app/static/js/tailwind-config.js` menyimpan padanan
token (warna, radius, tipografi, spasi, breakpoint, elevasi) untuk pipeline
Tailwind bila dibutuhkan; file ini tidak memuat runtime Tailwind.
