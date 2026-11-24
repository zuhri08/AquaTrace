# AquaTrace — Design System

## Kredit dan sumber

Arahan visual mengikuti brief proyek `AQUATRACE_PROMPT_DESAIN_META.md` yang
diberikan pengguna. Brief tersebut tidak tersedia sebagai file di workspace.
`docs/desain/referensi/index.html` juga tidak tersedia, sehingga layout di bawah
merupakan adaptasi responsif, bukan reproduksi referensi.

Font Montserrat dan JetBrains Mono serta Material Symbols Outlined dimuat dari
Google Fonts. Tailwind CSS v3.4.17 dan token utilitas dikonfigurasi melalui
CDN. CSS lokal tetap bertanggung jawab atas komponen khusus, states, responsif,
dan fallback jika CDN tidak terjangkau.

## Token

| Token | Nilai | Pemakaian |
|---|---|---|
| `--canvas` | `#FFFFFF` | Latar utama |
| `--surface-soft` | `#F1F4F7` | Latar sekunder / lane antrean |
| `--ink-deep` | `#0A1317` | Judul dan teks utama |
| `--ink` | `#1C1E21` | Teks isi |
| `--steel` | `#5D6C7B` | Teks sekunder |
| `--hairline` | `#CED0D4` | Batas input dan separator |
| `--hairline-soft` | `#DEE3E9` | Batas kartu |
| `--primary` | `#0064E0` | Aksi utama dan fokus |
| `--critical` | `#E41E3F` | Status kritis / aksi destruktif |
| `--telemetry` | `#6A3DE8` | Aksen khusus IoT |

Font antarmuka adalah Montserrat. JetBrains Mono dikhususkan untuk angka,
pengukuran, dan nilai teknis. Material Symbols Outlined dipakai untuk ikon
antarmuka; ikon status selalu didampingi teks, tidak pernah berdiri sendiri.

## Kontras

Rasio dihitung dengan rumus luminans relatif WCAG 2.x. Rasio teks normal yang
ditampilkan di sini memenuhi target WCAG AA (4.5:1):

| Teks | Latar | Rasio |
|---|---|---:|
| Kobalt `#0064E0` | Putih `#FFFFFF` | 5.39:1 |
| Steel `#5D6C7B` | Putih `#FFFFFF` | 5.39:1 |
| Bersih `#164A30` | Latar `#D7EDDF` | 8.30:1 |
| Waspada `#483600` | Latar `#F4E7B5` | 9.40:1 |
| Kritis `#8D1830` | Latar `#FFE3E8` | 7.55:1 |
| Netral `#39434C` | Latar `#EDF1F5` | 8.89:1 |
| Info `#12487F` | Latar `#DCEEFF` | 7.84:1 |
| Telemetri `#6A3DE8` | Putih `#FFFFFF` | 6.09:1 |
| Telemetri `#6A3DE8` | Latar `#F0EBFF` | 5.23:1 |

Kontras batas/dekorasi tidak ditujukan untuk menyampaikan status tanpa teks.
Fokus keyboard menggunakan outline kobalt dengan offset agar tampak pada
permukaan putih maupun lembut.

## Bentuk dan komponen

- Tombol, tab, status, dan chip berbentuk pil; kartu datar dengan sudut besar
  membulat dan tanpa bayangan dekoratif.
- Satu aksi utama kobalt per area/form; aksi sekunder memakai outline netral.
- Status: Bersih, Waspada, Tidak layak, belum diuji, menunggu, diproses, dan
  online/offline memakai ikon serta label teks.
- Queue menampilkan lajur prioritas/reguler dan posisi FRONT.
- Stack menandai TOP; linked list menandai HEAD/TAIL; tree menampilkan cabang
  bertingkat; graph menyediakan pan/zoom, arah edge, legenda status, dan rute.
- Feed dan sparkline sensor memakai ungu khusus telemetri. Grafik hanya
  menampilkan bacaan API; tidak menetapkan batas baku mutu.
- Loading, error dengan tombol coba lagi, dan state kosong disediakan pada
  visualisasi. Motion menghormati `prefers-reduced-motion`.
- Form memakai label eksplisit, indikator fokus, pesan notifikasi dengan
  semantik status/alert, dan tombol berukuran minimum 44 piksel.

## Layout responsif

- Staf/admin: sidebar pada layar lebar, menu samping yang dapat dibuka di ponsel.
- Warga: tab pada layar lebar, navigasi bawah pada ponsel.
- Breakpoint utama komponen navigasi: 680 piksel; breakpoint intermediate
  sidebar: 900 piksel.
- Kartu metrik dan konten menyesuaikan lebar; antrean dan sparkline menjadi satu
  kolom pada layar sempit. Graf mempertahankan area scroll agar label tidak
  bertumpuk.

## Do / Don't

**Do**

- Ambil setiap data visual dari API, render nilai memakai `textContent`, dan
  tampilkan loading/error/kosong secara eksplisit.
- Beri label teks dan ikon pada status; gunakan format angka teknis mono.
- Pertahankan kobalt untuk aksi utama dan ungu hanya untuk telemetri.
- Pertahankan caveat bahwa data dan ambang adalah simulasi.

**Don't**

- Jangan hardcode isi antrean, hasil uji, simpul jaringan, atau bacaan grafik.
- Jangan menampilkan status hanya dengan warna atau ikon tanpa label.
- Jangan menyamakan data sensor dengan hasil laboratorium atau mengarang
  ambang baku mutu resmi.
- Jangan menggunakan ungu sebagai warna aksi umum atau mengganti fokus
  keyboard dengan hover saja.
