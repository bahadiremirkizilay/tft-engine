# tft-engine

Çevrimdışı bir TFT strateji araştırma ve karar motoru. Sadece maç sonrası analiz ve bağımsız simülasyon içindir: oyun istemcisini okumaz, canlı maç sırasında çalışmaz, çekirdek katmanlar ağ çağrısı yapmaz.

Plan ve gerekçeler: [docs/PLAN.md](docs/PLAN.md). Şu anki durum ve sıradaki işler: [docs/DURUM.md](docs/DURUM.md).

## Kurulum (Windows, PowerShell)

Python 3.11 veya üstü ve Git gerekir (`py --version`, `git --version` ile kontrol et).

```powershell
git clone https://github.com/bahadiremirkizilay/tft-engine
cd tft-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

PowerShell betik çalıştırmayı engellerse, sadece o oturum için: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

macOS / Linux için aynı adımlar: `python3 -m venv .venv`, `source .venv/bin/activate`.

## Doğrulama

Her şey tek komutta (testler, ruff, proje denetimi):

```powershell
python tools/verify.py          # hepsi (~1,5 dk)
python tools/verify.py --quick  # testler hariç
tft-engine audit                # sadece denetim; bilinen borçları da listeler
```

Klonladıktan sonra bir kez: `git config core.hooksPath .githooks`. Bundan sonra her commit'ten önce `tools/verify.py` otomatik çalışır ve bir şey bozuksa commit'i durdurur. Denetimin kabul listesi ve bilinen borçlar: `audit.toml`.

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
- `--wisp-prob 0.5` bir shop'ta Wisp çıkma olasılığı (o shop'ta 4 şampiyon olur). Varsayılan set verisinden: Set 18'de her iki shop'ta bir (18.1 notu; sıklık ölçülmedi).
- `--buy-wisp` o turun Wisp'i alınmış demek: altındaki şampiyon açılır ve sonraki shop'larda 5 şampiyon görünür (sahibin gözlemi, 18.4b).
- Çıktı, hesabın dayandığı varsayımları ve gözden geçirilmemiş yamaları her zaman yazar.

## Karar prototipi (P1)

```powershell
tft-engine decide scenarios/p1/o1_one_copy_from_3star.json
```

Senaryo dosyaları `scenarios/p1/` altında. Çıktı her aday için olasılıkları, altını, HP kaybını, her sayının güven sınıfını ve kararı en çok değiştiren varsayımları gösterir. Sonuçlar ve bulgular: [docs/P1_SONUC.md](docs/P1_SONUC.md).

Augment'ler ve shop kuralları (B3):

- Augment teklifi gerçek id ile: `"augment_offers": [{"augment": "DA_LevelUp"}, {"augment": "DA_TradeSector"}]`. Motor her teklifi seçilmiş sayıp en iyi adayı bulur; modellenemeyen kısımları not olarak yazar.
- Daha önce seçilmiş augment'ler `state.augments` içine yazılır (ör. `["DA_UpwardMobility"]`) ve bütün adayların kurallarını değiştirir. Bedava reroll'lar `state.free_rerolls`, aktif trait'ler `active_traits` (ör. `{"DA_18_Blossom": 5}`).
- Roll adayları Wisp almadan ve "önce Wisp al" olarak iki kez hesaplanır, iyisi gösterilir.

```powershell
tft-engine data augments --set set18 --patch 18.4 --list   # hangi augment ne kadar modellendi
```

## Bilgi tabanı (B1): şampiyon, trait, item, augment, Wisp

Set verisi CommunityDragon'un oyun dosyası dışa aktarımından otomatik üretilir (resmi değil; ayrıntı [docs/KAYNAKLAR.md](docs/KAYNAKLAR.md)).

```powershell
python tools/cdragon_fetch.py 16.20                  # data/raw/cdragon/16.20/ altına indirir (git'e girmez)
python tools/import_cdragon.py set18 16.20           # data/sets/set18/generated/18.4/ dosyalarını üretir
tft-engine data check --set set18 --patch 18.4       # bağlantıları, tarifleri, kaynakları ve yama atamasını kontrol eder
tft-engine data diff --set set18 18.4 18.5           # iki yama arasındaki farklar
```

- `generated/<yama>/`: Sadece importer yazar, elle düzenlenmez. Aynı girdiden her zaman aynı bayt üretilir.
- `curated/`: Elle hazırlanan kurallar ve düzeltmeler. İlk dosya `cdragon_rules.json`: hangi kayıtların oynanabilir şampiyon olduğu ve item türlerinin nasıl ayrıldığı, kanıtlarıyla.
- `data/sources.json`: Her kaynağın adresi, alınma tarihi ve (dosyalar için) sha256'sı. Importer, dosya kayıttaki hash'ten farklıysa çalışmaz.
- `data/sets/<set>/calendar.json`: Yama notlarının tarihleri ve CommunityDragon sürümü ↔ yama eşlemesi. Başka bir yamanın döneminde alınmış veri o yamaya atanırsa kontrol uyarı verir.

## Item ve trait sorguları (B4)

```powershell
tft-engine items --set set18 --patch 18.4 --have "B.F. Sword,B.F. Sword,Recurve Bow"   # bileşenlerle ne yapılır
tft-engine traits --set set18 --patch 18.4 --board "Ahri,Sett,Lux (Blossom)" --emblem "Ornn:Blossom Emblem"
tft-engine items-for Ahri --set set18 --patch 18.4                                       # kurala göre uygun item'lar
```

Item istatistikleri üçüncü taraf kaynaklı (tactics.tools, MetaTFT). Item uyumu bir kural tahminidir (varsayım), oyuncu istatistiği değildir.

## Komplar ve item üçlüleri (B5)

```powershell
tft-engine comps --set set18 --patch 18.4 --units "Krug,Pebbles" --have "Needlessly Large Rod,Recurve Bow"
tft-engine trio Pebbles --set set18 --patch 18.4 --have "Needlessly Large Rod,Recurve Bow" --items "Void Staff"
```

Komp puanı bir varsayımdır (sahip olunan birimler ve bileşenlerin uyumu). Site istatistikleri puana karışmaz; site, yama ve rank filtresiyle yanında yazılır.

## Yama verisi

Her set için `data/sets/<set>/base.json` ve her yama için `data/sets/<set>/patches/<yama>.json` vardır. Yama dosyası sadece değişiklikleri (buff, nerf vb.) kaynağıyla birlikte içerir. Dosyası olmayan bir yama yüklenmez.

## Oyun içinde doğrulanması gerekenler (Set 18)

Liste ve form: [templates/oyun_ici_kontrol.md](templates/oyun_ici_kontrol.md). Kısaca:

1. Shop olasılıkları ve havuz boyutları oyun dosyasından okunuyor. Seviye 7 oyun içi tooltip'ten (16/30/43/10/1, 2026-10-20); oyun dosyası ve 17.1 notu 19/30/40/10/1 diyor (çelişki kaydı).
2. XP tablosu resmi 18.2 notlarıyla tutarlı (7→8 = 56, 8→9 ve 9→10 = 68). XP alım oranı (4 altın = 4 XP), tur başına 2 XP ve en yüksek level (10) kontrol edilmeli.
3. Oyunda kontrol edildi (18.4b): reroll 2, faiz, temel gelir 5, PvP galibiyeti +1, seri altını (2-4: +1, 5: +2, 6+: +3; kayıp serisi aynı).
4. Satış değerleri (wiki kuralından türetildi, wiki kendi örneğiyle çelişiyor) ve oyuncu hasarı.
5. Wisp: Wisp çıkan shop'ta 4 şampiyon var; turda 1 Wisp alınabiliyor, alınca o turun shop'larında 5 şampiyon görünüyor (sahip, 18.4b). Wisp çıkma sıklığı ölçülmedi; karar motoru Wisp alarak ve almayarak iki roll'u da hesaplıyor.

Data Dragon çapraz kontrolü: `python tools/ddragon_check.py set18 18.4 16.20.1 --set-path TFTSet18` (74 kaydın hepsi ad ve maliyet olarak aynı).
