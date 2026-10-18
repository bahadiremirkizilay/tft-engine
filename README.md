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
