# Telemetri IoT AquaTrace

## Arsitektur

Perangkat mengirim JSON lewat HTTP `POST /api/iot/ingest` dengan API key
perangkat pada header `X-API-Key`. Nilai key mentah hanya diberikan satu kali
saat admin mendaftarkan perangkat; database menyimpan SHA-256 hash. HTTPS wajib
dipakai pada deployment jaringan nyata.
Admin membuat perangkat di `/admin/telemetri/perangkat`. API key plaintext hanya
ditampilkan satu kali pada response HTML setelah pembuatan dan tidak disimpan di
cookie sesi atau database; salin key sebelum meninggalkan halaman.

Bacaan divalidasi pada endpoint, disimpan berstatus `antri`, lalu diproses FIFO
oleh Queue manual. Evaluasi menggunakan pohon keputusan yang sama dengan wizard
petugas. Hasil memperbarui `status_sensor`; vonis `TIDAK_LAYAK` membuat sampel
prioritas ber-asal `iot` jika belum ada sampel `menunggu` atau `diproses` untuk
sumber tersebut. Data sensor adalah indikator, bukan hasil lab otoritatif.

`IOT_AUTO_PROSES=true` memproses antrean segera setelah ingest (nilai default).
Untuk mendemonstrasikan antrean, atur `IOT_AUTO_PROSES=false`, kemudian petugas
atau admin menekan tombol proses pada `/petugas/telemetri`.

## Payload

```json
{
  "kode": "SENSOR-01",
  "ph": 7.2,
  "kekeruhan_ntu": 1.8,
  "tds_mgl": 145,
  "ts": "2026-11-24T12:00:00+00:00"
}
```

`ts` opsional dan harus ISO-8601 bila diberikan. Timestamp duplikat untuk
perangkat yang sama ditolak dengan HTTP 422. Rentang fisik untuk validasi:
pH 0–14, kekeruhan 0–1000 NTU, dan TDS 0–5000 mg/L. Ini rentang validasi
simulasi, bukan ambang baku mutu. Laju dibatasi satu bacaan per 2 detik per
perangkat (HTTP 429); key salah atau perangkat nonaktif menghasilkan HTTP 401.

## Simulator

Jalankan `python seed.py`, kemudian mulai server dengan `python run.py`, lalu:

```powershell
python iot_simulator.py --base-url http://127.0.0.1:5000 --kode SENSOR-01 --api-key demo-sensor-01-key --interval 2 --skenario normal --jumlah 5
python iot_simulator.py --base-url http://127.0.0.1:5000 --kode SENSOR-01 --api-key demo-sensor-01-key --interval 2 --skenario tercemar --jumlah 1
```

Skenario `normal` mengirim bacaan contoh normal; `tercemar` menghasilkan bacaan
yang berada di luar rentang pH contoh agar cabang `TIDAK_LAYAK` dan verifikasi
prioritas dapat didemonstrasikan; `drift` menaikkan pembacaan bertahap. Label
keputusan tetap nilai contoh, bukan penilaian baku mutu resmi.

## Hal yang perlu diperhatikan

- Semua data seed/simulator adalah data simulasi; jangan mengirim data pribadi.
- Nilai pohon keputusan harus diverifikasi dan diisi manusia dari dokumen resmi
  sebelum dipakai untuk keperluan operasional.
- Gunakan TLS, simpan API key di secret store, dan rotasi/nonaktifkan key jika
  perangkat hilang.
- Halaman publik hanya menampilkan kode sensor, nama sumber, bacaan, status,
  dan waktu; tidak ada identitas pengaju sampel.
