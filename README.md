# tft-engine

Çevrimdışı bir TFT strateji araştırma ve karar motoru. Sadece maç sonrası analiz ve bağımsız simülasyon içindir: oyun istemcisini okumaz, canlı maç sırasında çalışmaz, çekirdek katmanlar ağ çağrısı yapmaz.

Plan ve gerekçeler: proje dosyalarındaki `PLAN.md` (v0.4). Şu anki durum: **M0 (iskelet)**.

## Kurulum (Windows, PowerShell)

Python 3.11 veya üstü gerekir (`py --version` ile kontrol et).

```powershell
cd tft-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

PowerShell betik çalıştırmayı engellerse, sadece o oturum için: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

macOS / Linux için aynı adımlar: `python3 -m venv .venv`, `source .venv/bin/activate`.

## Doğrulama

```powershell
python -m pytest
ruff check .
```

## Deney kaydı

Her deney `runs/runs.jsonl` dosyasına bir satır olarak eklenir: ad, config, config hash'i, seed, veri sürümü, git commit'i, metrikler, süre ve ortam bilgisi.

```powershell
tft-engine run toy_dice_mean --config configs/example.json --seed 1
tft-engine replay runs/runs.jsonl
```

`replay`, kayıttaki her deneyi aynı config ve seed ile yeniden çalıştırır ve sonuç aynı değilse `MISMATCH` yazar. `toy_dice_mean` sadece altyapıyı test eden bir oyuncaktır; TFT mekaniği içermez.

## Tekrarlanabilirlik kuralları

- Her rastgele akış `make_rng(seed, "akış-adı")` ile üretilir. Yeni bir akış eklemek mevcut akışların sayılarını değiştirmez.
- Seed türetme SHA-256 tabanlıdır; her makinede ve Python sürümünde aynı sonucu verir (`tests/test_seeds.py` sabit değerleri kontrol eder).
- Deney karşılaştırmalarında zaman damgası, çalıştırma kimliği ve ortam bilgisi karşılaştırılmaz; ad, config, seed, veri sürümü ve metrikler karşılaştırılır.

Bağımlılık politikası: [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md).

## Olasılık sorgusu (M1a)

Örnek: level 8, 50 altın, 4 maliyetli `Ahri`'den 2 kopya lazım, masada (sende veya rakiplerde) 3 kopyası görünüyor:

```powershell
tft-engine odds --set set18 --patch 18.4 --level 8 --gold 50 --target Ahri:4:2 --taken Ahri:3
```

- `--target birim:maliyet:kopya` birden fazla verilebilir. Sırayla satın alınır.
- `--floor 20` altın 20'nin altına inecekse roll'u durdurur.
- `--wisp` her iki shop'ta bir Wisp'in bir şampiyon yerini kapladığını varsayar (doğrulanmadı).
- Çıktı, hesabın dayandığı varsayımları ve gözden geçirilmemiş yamaları her zaman yazar.

## Karar prototipi (P1)

```powershell
tft-engine decide scenarios/p1/o1_one_copy_from_3star.json
```

Senaryo dosyaları `scenarios/p1/` altında. Çıktı her aday için olasılıkları, altını, HP kaybını, her sayının güven sınıfını ve kararı en çok değiştiren varsayımları gösterir. Sonuçlar ve bulgular: [docs/P1_SONUC.md](docs/P1_SONUC.md).

## Yama verisi

Her set için `data/sets/<set>/base.json` ve her yama için `data/sets/<set>/patches/<yama>.json` vardır. Yama dosyası sadece değişiklikleri (buff, nerf vb.) kaynağıyla birlikte içerir. Dosyası olmayan bir yama yüklenmez.

## Oyun içinde doğrulanması gerekenler (Set 18)

Aşağıdaki değerler veride var ama internetten veya oyuncu anlatımından geliyor. Oyunda kontrol edilince durumları `verified` yapılır:

1. Shop olasılıkları. **Seviye 7'de iki kaynak çelişiyor:** 16/30/43/10/1 ile 19/30/40/10/1. Şimdilik ikincisi kullanılıyor.
2. Level başına gereken XP. 8'den 9'a ve 9'dan 10'a ikisinin de 68 olması kontrol edilmeli.
3. Tur başına 2 pasif XP ve normalde ulaşılan en yüksek level (10).
4. Seri altını (kazanma ve kaybetme serisinde aynı: 2-4 seride +1, 5'te +2, 6 ve üstünde +3), PvP galibiyet altını (+1) ve temel gelir (1-2 ve 1-3: 2, 1-4: 3, 2-1: 4, sonra 5).
5. Wisp'li shop'ta 4 şampiyon olması. Varsayılan olarak açık, `--no-wisp` ile kapatılır.

Hâlâ bilinmeyenler: maliyet başına havuz boyutları (üçüncü taraf kaynaktan), satış değerleri.
