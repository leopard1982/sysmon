# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id-ID/1.1.0/).

## [1.15.0]
### Ditambahkan
- **Tooltip hover di semua chart** (dashboard dan widget desktop):
  - grafik garis: garis penanda + nilai tiap seri pada titik itu dan "x detik lalu";
  - donut/pie: irisan yang di-hover menebal dan menampilkan nama, nilai, dan persen;
  - bar, meteran, petak statistik, legenda, dan baris layanan: nama lengkap dan nilai (berguna untuk teks yang terpotong);
  - strip ketersediaan layanan: status dan latensi tiap sampel.

## [1.14.1]
### Diperbaiki
- Donut **Penyimpanan** di Ringkasan dashboard menampilkan persen terlalu tinggi (47% padahal `df` 45%): blok cadangan root ikut dihitung terpakai. Persen kini `terpakai / (terpakai + tersedia)` seperti `df`, dan ada irisan **Cadangan root** supaya total cocok.
- Donut menyesuaikan ukuran agar legenda tidak terpotong di jendela yang pendek.

## [1.14.0]
### Diubah
- **Tampilan awal kini dashboard** (dengan tab), bukan widget kecil. Widget desktop jadi opsional: menu **Tampilkan widget di desktop** (bawaan mati; pengguna lama perlu mencentangnya kalau masih ingin widget).
- Klik kiri ikon tray menyembunyikan/menampilkan dashboard. Ukuran jendela dashboard menyesuaikan layar.

## [1.13.0]
### Ditambahkan
- Tombol **Login root…** saat SMART ditolak (di widget, menu klik kanan, dan tab NVMe dashboard): masukkan password root, izin baca SMART diberikan lewat `su` + `desktop-htop-smart-setup`, lalu SMART langsung dimuat ulang. Password hanya dikirim ke `su`, tidak disimpan.
- `desktop-htop-smart-setup --user NAMA` (dipanggil sebagai root); nama user divalidasi.

## [1.12.0]
### Ditambahkan
- **Dashboard** (menu klik kanan / tray → *Buka Dashboard*): tab **Ringkasan** berisi pie/donut, bar, grafik garis, dan meteran (CPU, memori, penyimpanan, jaringan, status layanan, suhu, kesehatan, Docker).
- Tab detail per layanan, bernama sesuai layanannya: **CPU, Memori, Jaringan, NVMe, Baterai, Sistem, PostgreSQL, MariaDB, MongoDB, Redis, Nginx, Apache, UFW, Docker**. Tiap tab layanan punya status, grafik latensi, uptime, dan riwayat ketersediaan. Tab layanan yang disembunyikan atau tidak terpasang ikut disembunyikan.
- Dashboard mengikuti tema dan bahasa yang dipilih.
### Diubah
- Folder `dist/` (berisi `.deb`) kini ikut di-commit supaya paket bisa langsung diunduh dari repo; `make clean` tidak lagi menghapusnya.

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
