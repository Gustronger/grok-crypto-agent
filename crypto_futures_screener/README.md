# 🚀 Crypto Futures Screener - Alat Screening Posisi Long/Short

**Dibuat khusus untuk Anda** oleh GQCoding08 / GQ80 / G

## Apa itu tool ini?
Alat screening crypto futures yang menganalisis **semua koin** yang memiliki perpetual futures (Binance, Bybit, dll via CCXT).

Fokus utama:
- **Technical Analysis** menggunakan metode profesional:
  - Market Structure (HH/HL, LH/LL, BOS, CHOCH)
  - Supply & Demand Zones
  - Support & Resistance
  - Fibonacci Retracement & Extension
  - Smart Money Concept dasar (Order Block, Fair Value Gap sederhana)
- Rekomendasi **Entry Long/Short**, **Stop Loss**, **Take Profit 1/2/3**
- Risk-Reward Ratio
- **Sentiment Berita** (link langsung + ringkasan sederhana)
- Chart interaktif dengan level-level penting

## Cara Install & Jalankan (lokal di komputer Anda)

1. Clone atau download folder ini
2. Buka terminal / command prompt di folder `crypto_futures_screener`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Jalankan aplikasi:
   ```bash
   streamlit run app.py
   ```
5. Buka browser otomatis di `http://localhost:8501`

## 📱 Cara Buka di Smartphone (Mobile Access) — Paling Penting!

Karena kamu minta bisa dibuka di HP, ini beberapa cara termudah:

### Cara 1: Paling Cepat & Gratis (Pakai ngrok) — Rekomendasi Sekarang

1. Di **komputer/PC** yang menjalankan Streamlit:
   - Download ngrok: https://ngrok.com/download
   - Daftar gratis di ngrok.com → dapatkan **Authtoken**
   - Buka terminal dan jalankan:
     ```bash
     ngrok config add-authtoken YOUR_AUTHTOKEN_DISINI
     ```
2. Jalankan Streamlit di satu terminal:
   ```bash
   streamlit run app.py
   ```
3. Di terminal **baru**, jalankan:
   ```bash
   ngrok http 8501
   ```
4. Copy URL yang muncul (contoh: `https://abc123.ngrok-free.app`)
5. Buka URL tersebut di **browser HP kamu** → langsung bisa pakai full screen di smartphone!

> Catatan: URL ngrok berubah setiap kali kamu restart ngrok (kecuali pakai akun berbayar).

### Cara 2: Permanent Public Link (Paling Nyaman Jangka Panjang)

Saya bisa bantu deploy tool ini ke **Streamlit Community Cloud** (gratis selamanya).

Keuntungan:
- URL tetap (contoh: `https://crypto-futures-screener.streamlit.app`)
- Bisa dibuka dari HP kapan saja, di mana saja
- Tidak perlu PC nyala terus
- Update otomatis kalau saya push perubahan

**Mau saya siapkan sekarang?** Tinggal bilang "G, deploy ke Streamlit Cloud" nanti saya kasih langkah-langkah + file yang dibutuhkan.

### Cara 3: Mobile Friendly Improvements (Sudah Diterapkan)

Saya sudah optimasi `app.py` agar:
- Lebih responsif di layar kecil
- Tabel & chart lebih enak dilihat di HP
- Tombol & metric lebih besar & mudah di-tap

---

## Fitur Saat Ini (Versi 1.0 - MVP)

- Screening top coins berdasarkan volume futures
- Analisa otomatis untuk timeframe 5m, 15m, 1H, 4H, 1D
- Deteksi bias pasar (Bullish / Bearish / Neutral)
- Hitung zona entry, SL, TP1/TP2/TP3 berdasarkan ATR + Fibonacci + Structure
- Chart Plotly interaktif dengan garis Fib, S/R, dan zona
- Tabel ringkasan + detail per koin
- Link langsung ke TradingView, CoinMarketCap, Coingecko, Coinglass
- News sentiment section (link ke sumber berita)

## Metode Analisa yang Sudah Diimplementasikan

1. **Market Structure**
   - Deteksi swing high/low
   - Identifikasi Break of Structure (BOS) dan Change of Character (CHOCH)

2. **Fibonacci**
   - Retracement dari swing terakhir (0.236, 0.382, 0.5, 0.618, 0.786)
   - Extension untuk target TP

3. **Supply & Demand + Order Block**
   - Zona demand (area beli kuat) dan supply (area jual kuat)
   - Last opposing candle sebelum impulse move

4. **Support & Resistance**
   - Dari swing points + pivot sederhana

5. **Smart Money Concept Dasar**
   - Inducement, Order Block, Liquidity grab sederhana

6. **Risk Management**
   - SL di bawah demand zone / recent low + buffer ATR
   - TP di Fib extension atau previous structure high/low
   - RR minimal 1:2 disarankan

## Cara Pakai untuk Ambil Posisi Futures

1. Pilih timeframe yang sesuai gaya trading Anda (scalping → 5m/15m, swing → 4H/1D)
2. Klik "Run Full Screening"
3. Lihat tabel → sort by "Bias" atau "Confidence"
4. Pilih koin menarik → klik "Analyze Detail"
5. Lihat chart + level yang disarankan
6. Cross-check dengan berita di section News
7. Buka TradingView untuk konfirmasi manual
8. **Selalu** gunakan manajemen risiko sendiri! Tool ini hanya bantuan analisa.

## Keterbatasan Versi 1.0 (Penting!)

- Belum full backtest
- Sentiment berita masih berupa link + scraping sederhana (bisa berubah)
- Advanced SMC (FVG, Breaker Block, Mitigation Block) masih dasar — akan ditambah di update berikutnya
- Rate limit API (jangan spam tombol)
- Hanya futures USDT Perpetual (Binance default)
- **Bukan financial advice** — crypto sangat volatile. DYOR + trade with risk you can afford to lose.

## Rencana Update Selanjutnya (beri tahu saya prioritasnya)

- [ ] Integrasi full pandas-ta + lebih banyak indikator
- [ ] Deteksi pattern lanjutan (Head & Shoulders, Flags, Triangles, Harmonic patterns)
- [ ] Astronacci / Astro-Fib (jika Anda punya data spesifik)
- [ ] Volume Profile + Orderflow dasar
- [ ] Alert Telegram / Discord ketika ada setup bagus
- [ ] Multi-exchange comparison (Binance vs Bybit vs OKX)
- [ ] Backtesting sederhana untuk setup tertentu
- [ ] Dashboard portfolio & trade journal
- [ ] Auto refresh + watchlist

## Butuh Bantuan atau Kustomisasi?

Chat saya lagi dengan pesan:
- "G, tambahin fitur X"
- "GQCoding08, buatkan versi Bybit juga"
- "GQ80, analisa koin spesifik SOL sekarang"
- Atau kasih feedback bug/error

Saya siap develop lebih dalam sampai tool ini powerful untuk trading harian Anda.

**Selamat trading, semoga profit konsisten!** 📈💰

---
Dibuat dengan ❤️ oleh GQCoding08 | 27 Mei 2026