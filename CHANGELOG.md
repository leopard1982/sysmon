# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id-ID/1.1.0/).

## [1.11.0]
### Ditambahkan
- **SMART NVMe** (kesehatan, cadangan, keausan, data ditulis/dibaca, jam nyala, siklus daya, shutdown tak aman) lewat `smartctl`. `smartmontools` menjadi paket rekomendasi; `sudo desktop-htop-smart-setup` memberi izin baca SMART tanpa password (opt-in).
- **Model & firmware SSD NVMe** ditampilkan jelas.
- **Kesehatan baterai** (kapasitas penuh vs desain, siklus, daya, model).
- **Usia instalasi Linux** (dari folder installer / pembuatan filesystem root).
- Monitor **Nginx**, **Apache**, dan **UFW** (disembunyikan otomatis kalau tidak terpasang).
- Opsi **Tampilkan di atas** (selalu di depan window lain).
### Diubah
- "Tema tulisan" menjadi **Tema**: tiap tema membawa warna background dan teks yang serasi (Default, Hitam, Biru, Hijau Matrix, Amber, Ungu, Merah, Terang). Tema lama `Gelap` menjadi `Terang`, `Putih` menjadi `Default`.
- Tata letak 4 kolom (NVMe, SMART, baterai, sistem di kolom ke-3; Docker di kolom ke-4). Baterai pindah dari daftar sensor ke bagian sendiri.

## [1.10.0]
### Ditambahkan
- Pilihan bahasa **Indonesia / English** dari menu klik kanan (bahasa awal mengikuti locale sistem).

## [1.9.0]
### Ditambahkan
- Monitor **Redis** (PING + INFO, mendukung server ber-password).
- Pengaturan per layanan (PostgreSQL, MariaDB, MongoDB, Redis): tampilkan/sembunyikan dan ubah port. Docker bisa ditampilkan/disembunyikan.
- Logo petir di judul widget.
### Diubah
- Nama ikon menjadi `desktop-htop` (PNG 16–256 px + SVG) agar tidak bentrok dengan tema ikon.

## [1.8.0]
### Ditambahkan
- Efek visual: kartu gradasi, garis judul memudar, grafik dan bar dengan glow, halo pada titik status, fade-in. Bisa dimatikan.

## [1.7.0]
### Ditambahkan
- Monitor **Docker** (container dan image, lewat unix socket) dan **MongoDB**.
- Tema tulisan (Default, Putih, Gelap, Hijau Matrix, Amber, Ungu) dan pilihan font.
### Diperbaiki
- Background tetap hitam saat disembunyikan: efek bayangan Qt membuat window transparan dirender hitam di X11. Diganti bayangan manual.

## [1.6.0]
### Ditambahkan
- Opsi **hilangkan background** (teks diberi bayangan tipis agar terbaca di atas wallpaper).

## [1.5.0]
### Ditambahkan
- Monitor jaringan: status internet + latensi, SSID dan sinyal WiFi, kecepatan download/upload.

## [1.4.0]
### Ditambahkan
- Pilihan interval update: 1 detik, 5 detik, 30 detik, 1 menit.

## [1.3.0]
### Ditambahkan
- Pengaturan autostart (on/off) di menu; ikon petir.

## [1.2.0]
### Ditambahkan
- Monitor PostgreSQL, MariaDB, status dan kapasitas NVMe, swap file.
- Ikon system tray, mode satu instance, autostart saat login.
- Nama "System Monitoring".

## [1.1.0]
### Ditambahkan
- Indikator warna (hijau bagus, kuning hati-hati, merah tinggi) dan legenda.

## [1.0.0]
### Ditambahkan
- Rilis awal: CPU per core, RAM, dan sensor di atas wallpaper; drag untuk memindahkan, menu klik kanan.
