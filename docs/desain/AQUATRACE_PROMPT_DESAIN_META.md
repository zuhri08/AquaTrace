# Aturan desain AquaTrace (bahasa visual terinspirasi sistem desain Meta)

Prioritas: file ini menggantikan token warna, tipografi, bentuk, dan komponen di PRD
Bagian 9. Fitur, alur, struktur data, dan IoT tidak berubah.

## Prinsip
1. Kanvas putih bersih, tipografi tegas, bentuk bulat besar.
2. Semua tombol, chip, tab, badge berbentuk pil (radius 100px). Tidak pernah persegi.
3. Kartu utama radius 32px, kartu ikon/fitur 16px, input 8px.
4. Judul bobot 500, subjudul editorial bobot 300 (28px), isi bobot 400, letter-spacing
   isi sedikit negatif (-0.16px untuk 16px, -0.14px untuk 14px).
5. Datar: tanpa bayangan pada kartu biasa. Bayangan 0 1px 4px rgba(20,22,26,.3) hanya
   untuk panel lengket (panel samping wizard, bilah aksi bawah di mobile).
6. Biru kobalt langka: satu aksi inti per layar (Ajukan Sampel, Proses Berikutnya,
   Simpan Hasil, Kalkulasi Rute, Tambah Edge). Tombol utama umum (landing, /publik,
   informasi) berwarna hitam. Tombol sekunder: outline 2px ink-deep.
7. Tidak ada aksen warna lain selain kobalt dan ungu (ungu hanya penanda IoT).

## Token warna
canvas #ffffff; surface-soft #f1f4f7; ink-deep #0a1317; ink #1c1e21; charcoal #444950;
slate #4b4c4f; steel #5d6c7b; stone #8595a4 (hanya dekoratif/disabled, JANGAN untuk
teks informasi); hairline #ced0d4; hairline-soft #dee3e9; disabled-text #bcc0c4;
ink-button #000000; primary #0064e0; primary-deep #0457cb (ditekan); primary-soft
#0091ff; fb-blue #1876f2 (cincin fokus); selected-border #0143b5; oculus-purple #a121ce
(khusus IoT); success #31a24c (BERSIH); warning #f7b928 (WASPADA); attention #f2a918;
critical #e41e3f (TIDAK_LAYAK/error); critical-strong #f0284a (border/label error).

Kontras (hitung ulang dan catat tabelnya di design-system.md): putih di atas success
~3,3:1 dan di atas attention ~2:1 GAGAL untuk teks kecil; badge hijau/amber pakai teks
ink-deep. Putih di atas critical ~4,6:1 lolos. Koreksi semua pasangan di bawah 4,5:1
(teks normal) atau 3:1 (teks besar/ikon). Status selalu ikon + label teks + warna.

## Tipografi
Font utama Montserrat (Google Fonts, versi dipin), fallback Helvetica, Arial, Noto Sans.
Optimistic VF proprietary: jangan di-embed. Angka ukur dan nilai sensor: JetBrains Mono.
hero 64/1.16/500 (hanya landing dan /publik); display 48/1.17/500; h-lg 36/1.28/500
(judul halaman dashboard); h-md 28/1.21/300; h-sm 24/1.25/500 (judul kartu); sub 18/1.44;
body 16/1.5/400; body-sm 14/1.43; label tombol/tab 14/700; caption/badge 12/1.33.
Tinggi baris body tidak boleh di bawah 1.5. Mobile: hero 64 -> 36px (<768) -> 24px (<480).

## Bentuk, spasi, elevasi
Radius: xs 2, sm 4, md 6, lg 8, xl 16, xxl 24, xxxl 32, feature 40, full 100px, circle 50%.
Spasi kelipatan 4px (4,8,10,12,16,20,24,32,40,48,64,80,120). Kontainer maks ~1280px.
Padding kartu 32px (24px di area dashboard padat). Jarak antarbagian dashboard 32-48px.
Breakpoint: <480, 480-767, 768-1023, 1024-1359, >=1360. Target sentuh min 44px.

## Komponen
- Tombol utama: hitam, teks putih, pil, padding 14px 30px, 14px/700; ditekan charcoal;
  nonaktif disabled-text. Tombol aksi inti: primary, ditekan primary-deep.
- Tombol ghost: border 2px rgba(10,19,23,.12), padding 10px 22px. Tombol ikon bulat 40px
  (44px di mobile).
- Pill tab: nonaktif putih + border 1px hairline; aktif latar ink-deep teks putih.
- Kartu: putih, border 1px hairline-soft, radius 32 (utama) / 16 (ikon). Kartu lembut:
  surface-soft. Kartu promo: latar ink-deep teks putih.
- Input: tinggi 44px, border 1px hairline, radius 8; fokus border 2px fb-blue; error
  border critical-strong + label error. Search pill: surface-soft, radius 100, tinggi 40.
- Opsi radio: border 1px rgba(10,19,23,.12), radius 8, padding 20; terpilih 2px
  selected-border.
- Badge: pil, padding 4px 10px, caption-bold. Banner info: latar ink-deep (atau warning
  dengan teks ink-deep), 14px/700.
- Aksordeon: radius 16, padding 24, border hairline-soft, chevron steel.
- Navigasi: staf = sidebar kiri 256px putih, item pil (aktif ink-deep); warga = pill tab
  atas + bottom navigation 4 item di mobile.
- Cincin fokus 2px fb-blue (offset 2px) di semua elemen interaktif. Tanpa mode gelap.

## Adaptasi untuk aplikasi data
- Tanpa fotografi. Hero memakai panel radius 32 berlatar gradasi ink-deep ke biru gelap
  atau ilustrasi SVG buatan sendiri. Dilarang memakai logo, nama, foto, atau font milik Meta.
- Ungu oculus-purple hanya untuk penanda IoT/telemetri (lencana "dari sensor", garis
  sparkline).
- Visualisasi struktur data: wadah radius 16 + border hairline-soft; node graph lingkaran
  berwarna status dengan cincin putih 2px; label FRONT/REAR/TOP/HEAD/TAIL badge pil
  ink-deep; angka font mono; animasi 150-250ms ease-out; hormati prefers-reduced-motion.
- Jalur Dijkstra dan jalur pohon keputusan tersorot memakai kobalt.
