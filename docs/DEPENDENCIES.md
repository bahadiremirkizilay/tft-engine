# Bağımlılık politikası

- **Python:** 3.11 ve üstü. Windows 10/11 üzerinde çalışması birincil hedef.
- **Çalışma zamanı bağımlılıkları** (şu an): `numpy`. Yeni bir bağımlılık ancak şu üç soru yazılı cevaplandıktan sonra eklenir: neden gerekli, Windows'ta sorunsuz kuruluyor mu, olmadan ne kadar zor.
- **Geliştirme bağımlılıkları:** `pytest`, `hypothesis`, `ruff`.
- **Planlanmış ama henüz eklenmemiş:** `scikit-learn` (M4), `duckdb` veya `pyarrow` (M2). Kendi milestone'ları başladığında, ölçüm gerekçesiyle eklenecekler.
- **Eklenmeyecekler (şimdilik):** GPU kütüphaneleri, derin öğrenme çerçeveleri, veritabanı sunucuları. Bir benchmark anlamlı fayda göstermedikçe.
- Çekirdek paket (`tft_engine` altındaki gamedata, state, rules, prob, models, decision) ağ kütüphanesi içe aktarmaz. Riot API istemcisi ayrı bir pakette olacak (M2).
