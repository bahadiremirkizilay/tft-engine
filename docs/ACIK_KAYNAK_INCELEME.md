# Açık kaynak TFT projeleri: teknik inceleme ve öneriler

Tarih: 2026-10-18 · Hazırlayan: Claude · İlgili plan: [PLAN.md](PLAN.md) (v0.2)
Kapsam: Kod kopyalanmadı, bağımlılık eklenmedi. İki depo salt okunur klonlandı, kodları okundu ve testleri izole bir ortamda çalıştırıldı.

| Proje | İncelenen commit | Dil | Boyut |
|---|---|---|---|
| [kiwoongk1m/tft_analyzer](https://github.com/kiwoongk1m/tft_analyzer) | `f2a2d8b` (15 Haziran 2026, tek commit) | Python 3.11 | ~3.100 satır kod + test |
| [tacticians-academy/teamfight-simulator](https://github.com/tacticians-academy/teamfight-simulator) | `a3faa9e` (15 Mart 2024, son commit) | TypeScript + Vue 3 | ~11.000 satır, 956 commit |
| (simülatörün veri bağımlılığı) [tacticians-academy/academy-library](https://github.com/tacticians-academy/academy-library) | son commit 20 Mart 2024, npm `0.33.0` | TypeScript | Set 1-11 verisi |

Referans tarih: Bugün canlıda **Set 18, yama 18.4** var; 18.5 21 Ekim'de, Set 19 1 Aralık 2026'da bekleniyor ([seemeta yama takvimi](https://seemeta.com/en/tft/set-18/release-dates)).

---

## 0. Kısa sonuç

1. **İki projeden de kod almamalıyız, ama ikisinden de önemli dersler var.** `tft_analyzer`'ın lisansı yok (yani yeniden kullanım hakkı yok). `teamfight-simulator` ISC lisanslı ama bizim kapsam dışı bıraktığımız şeyi (dövüş simülasyonu) yapıyor ve 2024'ten beri güncel değil.
2. **M0 + M1 için en değerli bulgu simülatörden değil, onun veri kütüphanesinden çıktı:** oyun dosyalarında shop için bir **"bad luck protection" (kötü şans koruması)** parametre bloğu var. Bu aktifse shop'lar birbirinden bağımsız değildir ve M1'deki kesin olasılık hesabının temel varsayımı yanlış olur. Planımızda bu yok. M1'e "doğrula ve gerekirse modelle" maddesi eklenmeli.
3. Aynı kaynak, shop oranlarının, havuz boyutlarının ve seri altınının oyun dosyasından (`map22.bin`) **otomatik çıkarılabildiğini** gösteriyor. M1'deki elle veri girişini azaltabilir, yama notuyla çapraz kontrol şartıyla.
4. `tft_analyzer` M2 için iyi bir **mimari şablon** (ham JSON'u önce diske yazmak, çok pencereli rate limiter, DuckDB'de normalize tablolar). Ama istatistik tarafı bizim hedefimiz için zayıf: güven aralığı yok, yama ayrımı yok, lobi/rekabet analizi hiç yok, gizlilik planımızla uyumsuz.
5. Rakip rekabetini analiz etmek için gereken hiçbir şey (lobi bazlı tablo, aynı kompozisyonu oynayan kişi sayısı, havuz çakışması, yama trendi) iki projede de yok. Bunlar zaten planımızın M3-M5'inde; projeler bu işi kısaltmıyor.

---

## 1. tft_analyzer

### 1.1 Genel durum

- **Tek commit**, tek yazar, 15 Haziran 2026. Geçmiş veya katkıcı yok; bakımının süreceğine dair bir işaret yok.
- **Lisans dosyası yok**, `pyproject.toml`'da lisans alanı yok. Varsayılan durum "tüm hakları saklı": kod okunabilir, ama kopyalanamaz veya türev eser yapılamaz.
- Bağımlılıklar: `httpx`, `duckdb`, `python-dotenv`; opsiyonel `PySide6` (overlay).
- Testler: Çevrimdışı test paketi bu ortamda temiz geçti (**21 geçti, 1 atlandı**, canlı API testleri anahtar olmadığı için çalıştırılmadı). Testler gerçek veriyle değil, elle hazırlanmış bir Set 14 fikstürü ve sentetik verilerle yapılıyor.
- README "Set 17 (2026) doğrulandı" diyor; bunu kanıtlayan bir veri veya fikstür depoda yok. Bugün canlı olan Set 18'e özel bir şey yok; kod set bağımsız yazılmış (ID'ler string olarak saklanıyor), bu iyi.

### 1.2 Veri nasıl toplanıyor

Akış (`ingest.py`, `client.py`):

```
tft-league-v1 (challenger, grandmaster, master)  → seed PUUID listesi
tft-match-v1 /by-puuid/{puuid}/ids?count=20      → maç ID'leri
dedup (diskteki dosya adlarına göre)             → /matches/{id}
ham JSON → data/raw/{match_id}.json
```

İyi tarafları:
- **Platform → bölge yönlendirmesi** doğru (`na1 → americas`, `tr1 → europe` vb.; `config.py`).
- **Çok pencereli rate limiter** (`ratelimit.py`): 20/1 sn ve 95/120 sn pencerelerini aynı anda uyguluyor, thread-safe. `429`'da `Retry-After` başlığına uyuyor, `5xx` ve ağ hatasında üstel bekleme, `401/403`'te "dev anahtarı 24 saatte bir yenilenir" uyarısı.
- **Ham veri önce diske yazılıyor**, parse ayrı adım. Şema değişince API bütçesi harcamadan yeniden parse edilebiliyor. Bu bizim M2 kabul kriterimizle ("ham veriden işlenmiş veri tek komutla yeniden üretilebilir") birebir aynı fikir.
- Tarama sırasında veritabanı kilitli tutulmuyor; analiz aynı anda okuyabiliyor.

Zayıf tarafları:
- **Kuyruk filtresi tarama anında yok.** Normal, Hyper Roll, Double Up maçları da indiriliyor; ranked filtresi (`queue_id = 1100`) sadece analizde uygulanıyor. Kısıtlı API bütçesi boşa gidiyor.
- **Örnekleme yanlılığı:** Seed'ler sadece Master+; her seed'in son 20 maçı alınıyor. Aynı Challenger oyuncuları birçok lobide tekrar ediyor, veri seti onların tercihlerine kayıyor. Örneklem tasarımı veya elo dengesi yok.
- **Zaman ve yama filtresi yok.** `startTime`/`endTime` kullanılmıyor; eski yama maçları da geliyor.
- Dedup sadece dosya adına göre; bozuk veya yarım yazılmış dosya tespiti yok.
- Tek thread, sırayla. Dev anahtarı için yeterli, production için değil.

### 1.3 Nasıl normalize ediliyor ve saklanıyor

`parse.py` ham JSON'u beş tabloya düzleştiriyor; `storage.py` bunları gömülü **DuckDB** dosyasına (`data/tft.duckdb`) yazıyor:

| Tablo | Satır | Önemli sütunlar |
|---|---|---|
| `matches` | maç | `match_id` (PK), `game_version`, `patch` (regex ile "14.23"), `set_number`, `queue_id`, `game_datetime` |
| `participants` | oyuncu × maç | `placement`, `level`, `gold_left`, `last_round`, `time_eliminated`, **`puuid`, `riot_id_game_name`, `riot_id_tagline`** |
| `participant_units` | birim × oyuncu × maç | `character_id`, `tier` (yıldız), `rarity`, `items_json` |
| `participant_traits` | trait × oyuncu × maç | `trait_id`, `style`, `tier_current`, `num_units` |
| `participant_augments` | augment × oyuncu × maç | `slot`, `stage` (sıraya göre 2-1/3-2/4-2 tahmini) |

İsimler ve ikonlar CommunityDragon'dan (`raw.communitydragon.org/latest/...`) çözülüyor.

Değerlendirme:
- Tablo ayrımı mantıklı ve bizim M2 şemamız için iyi bir başlangıç noktası.
- **Gizlilik planımızla çelişiyor:** PUUID düz metin, Riot ID de saklanıyor. Planımız PUUID'yi hash'lemeyi ve Riot ID'yi analiz setine almamayı şart koşuyor.
- **Veri sürümü ve şema doğrulaması yok.** `data_version` saklanıyor ama kontrol edilmiyor; geçersiz kayıt ayrı bir dosyaya düşmüyor (bizim M2 kabul kriterimiz bunu istiyor).
- Item'lar JSON string olarak saklanıyor; sorgularda Python'da tekrar açılıyor.
- Augment tablosu artık boş kalıyor (Set 13'ten beri API'de yok); "slot sırası = aşama" varsayımı zaten doğrulanmamış bir sezgisel kural.
- CommunityDragon `latest` kullanılıyor; eski yama verisi analiz edilirken isimler ve maliyetler yanlış eşleşebilir. Yama sabitlenmiyor.

### 1.4 Kompozisyon istatistikleri nasıl hesaplanıyor

`modules/comps.py` ve `web.py`:

1. Oyuncunun aktif trait'leri `style` (bronz=1, gümüş=2, ...) sırasına göre diziliyor.
2. **"Taşıyıcı" (carry)** = en çok item taşıyan birim (eşitlikte yıldız, sonra nadirlik).
3. **Kompozisyon imzası** = (gümüş ve üstü ilk 3 trait, taşıyıcı) veya web'de (taşıyıcı, ana trait). Kümeleme yok, sabit kural.
4. Her imza için `avg_place`, `top4_rate`, `win_rate`, `play_rate` hesaplanıyor; en az 15 oyun şartı; ortalama sıralamaya göre diziliyor.
5. Web görünümü ek olarak birim sıklığı, en çok kullanılan item'lar, item bileşenlerinin dağılımı (CommunityDragon reçetesinden) ve level dağılımını gösteriyor. "Hex tahta" görünümü konumsal veri olmadığı için ön/arka sıra tahmini.

Diğer modüller: `carries.py` (taşıyıcı ve item tier listesi, tam item build'leri), `coach.py` (bir oyuncunun trait bazında ortalaması ile genel ortalama farkı, alt 4'te kalan altın).

Bizim hedefimiz açısından eksikler:
- **Güven aralığı yok.** 15 oyunluk bir imzanın ortalama sıralaması çok gürültülü (8'li sıralamada standart sapma ~2.3; 15 oyunda ortalamanın standart hatası ~0.6 sıra). Liste bu gürültüye göre sıralanıyor.
- **Yama ayrımı yok;** analiz set bazında. Set içi yama değişiklikleri karışıyor.
- **İmza kırılgan:** Taşıyıcı "en çok item" olarak seçildiği için item dağılımı değişince aynı kompozisyon farklı imzalara bölünüyor; kararlılık ölçülmüyor.
- **Popülerlik ve güç karışıyor;** iyi oyuncuların seçimi düzeltilmiyor (planımız bunu açıkça not ediyor).
- **Lobi düzeyi hiçbir analiz yok:** aynı lobide kaç kişinin aynı kompozisyonu oynadığı, havuz çakışması, eleme sırası, elenme aşamasına göre tahta gücü yok.
- Train/test ayrımı, tahmin modeli veya kalibrasyon yok; sadece betimsel tablolar.

### 1.5 Politika notu

Depoda PySide6 ile "her zaman üstte duran, istemcinin üzerine konabilen" bir overlay var (`overlay.py`). Canlı oyun durumunu okumuyor, ama oyun sırasında ekranda meta listesi göstermek, Riot'un TFT politikasının hassas olduğu alana yakın. Planımızın kapsam sınırı (canlı oyunda araç yok) bunu zaten dışarıda bırakıyor; bu kısım bizim için ilgisiz.

---

## 2. teamfight-simulator

### 2.1 Genel durum

- 956 commit, neredeyse tamamı tek geliştirici (Kyle Coburn). **Son commit 15 Mart 2024**; 19 aydır hareket yok.
- Tarayıcıda çalışan bir Vue 3 uygulaması ([tftsim.netlify.app](https://tftsim.netlify.app)). Başsız (headless) çalışma README'de "gelecek fikri" olarak duruyor.
- Testler: Bu ortamda `vitest` çalıştı, **2 test geçti** (Set 6 ve 6.5'te tek bir şampiyon yeteneğinin zamanlaması). Dövüş motorunun geneli için test yok.
- Lisans: `package.json`'da **ISC**; depoda ayrı bir LICENSE dosyası yok. Veri kütüphanesi `academy-library`'nin LICENSE dosyası var: "ISC, Copyright 2022 Kyle Coburn".

### 2.2 Veri kaynağı

Tüm şampiyon, trait, item, augment istatistikleri ve shop parametreleri `@tacticians-academy/academy-library` paketinden geliyor. Bu paket CommunityDragon üzerinden **oyun istemcisinin dosyalarını** (`map22.bin.json`, set JSON'ları) çekip TypeScript'e dönüştürüyor (`build/etl/*`).

- Kütüphanedeki en yeni veri **Set 11** (Mart 2024). Set 12-18 hiç yok.
- ETL, oyun dosyasındaki bazı alanları **hash anahtarlarıyla** buluyor (örneğin bad luck protection bloğu `'{8844d784}'`). Riot iç yapıyı değiştirdiğinde sessizce kırılabilir.

### 2.3 Hangi mekanikleri modelliyor

Motor (`sim/loop.ts`, `sim/ChampionUnit.ts`, `sim/effects/*`):

| Mekanik | Durum |
|---|---|
| Oyun döngüsü | 30 tick/sn sabit adım ("Confirmed" notuyla) |
| Tahta | 7×8 hex, iki takım |
| Hedef seçimi ve yol bulma | Var; en yakın hedef, menzile girene kadar hareket |
| Suikastçıların arka sıraya atlaması | Var |
| Normal saldırı, saldırı hızı, mermi uçuşu | Var |
| Mana kazanımı | Var: verilen ham hasarın %1'i + alınan hasarın %7'si, üst sınır 42.5 (kod içinde "doğrula" notuyla) |
| Mana kilidi, yetenek kullanımı, kullanım süresi | Var; varsayılan kullanım ve mermi süresi 0.25 sn tahmini |
| Kritik vuruş | Rastgele (`Math.random()`) |
| Kaçınma (dodge) | Rastgele değil, **beklenen değer** olarak hasardan düşülüyor |
| Kalkan, iyileşme, kanama, durum etkileri (sersemletme, silahsızlandırma vb.) | Var |
| Trait, item, augment etkileri | **Sadece Set 6 ve 6.5** için kodlanmış |
| Şampiyon yetenekleri | **Sadece Set 6 ve 6.5**; Set 7+ için boş |
| Aşama bazlı ölçekleme | Var (bazı birimler için) |
| Uzatma (overtime) sınırı | Yok; 30 sn'de hata fırlatıyor |
| Shop / rolldown modu | Var (aşağıda) |
| 8 oyunculu oyun, ekonomi turları, rakip değişimi, can | **Yok** (README'de açıkça kapsam dışı) |

### 2.4 Nerelerde yaklaşık sonuç veriyor

Kodda **94 adet `TODO`** var; çoğu "deneysel olarak belirle" veya "doğrula" notu. Başlıcaları:

- Hareket kilidi süreleri (yakın dövüş 1000 ms, atlayıcılar 600 ms), varsayılan kullanım ve mermi süreleri, saldırı ön hazırlığı (saldırı aralığının 1/4'ü), birçok yetenekte hız ve yarıçap sabitleri tahmini.
- Bazı item'lar kritik vuruş yerine her saldırıda tetikleniyor ("kritikler ortalandığı için").
- Yakın dövüş saldırıları anlık kabul ediliyor.
- Dodge beklenen değer; kritik rastgele. Tutarlı bir rastlantısallık modeli yok.
- Yol bulma 4 hex ile sınırlı; boş hex seçimi deterministik ("random" TODO'su).
- **Rastgele sayı üreteci tohumlanamıyor** (`Math.random()` her yerde). Aynı dövüş tekrarlanamaz; ortak rastgele sayılar (CRN) ile karşılaştırma yapılamaz.
- Durum global Vue store'unda tutuluyor ve döngü `window.requestAnimationFrame`'e bağlı. Paralel, toplu ve başsız çalıştırma için yeniden yazım gerekir.

### 2.5 Rolldown (shop) modu: M1 için asıl ilgi çekici kısım

`ui/components/RolldownShop.vue`:

- Level'a göre maliyet olasılıkları (`dropRates['Shop'][level]`) ile önce maliyet seçiliyor.
- Sonra o maliyetteki birim, **havuzda kalan kopya sayısıyla orantılı** ağırlıkla seçiliyor. Satın alma ve satma havuzu güncelliyor.
- Set 10 "Headliner" mekaniği (yıldızlı birim, sıklık parametresi, maliyete göre tekrar sınırı, son trait'leri tekrar etmeme) ayrıca modellenmiş.
- XP 4 altın, reroll 2 altın; birim birleştirme var.
- **Bad luck protection uygulanmıyor:** Kütüphane bu parametreleri oyun dosyasından çıkarıyor, ama simülatör kodu hiç kullanmıyor.

Kütüphanenin Set 11 verisinde (`dist/set11/map.ts`) çıkarılan parametreler:

```
shopBadLuckProtection: ForceFunctionMax 30, ForceFunctionDivisor 2,
  Tier1StopForce 15 ... Tier5StopForce 5,
  BeginTrackingTier{2..5}AtThisLevel 3/5/7/9, StopTrackingTier{1,2}AtThisLevel 7/9
dropRates.Shop: level 1-11 için maliyet olasılıkları
tierBags: maliyet başına havuz boyutları (Set 11: 1 maliyet 22, 2 maliyet 20, ...)
winStreaks / lossStreaks: seri uzunluğu → ek altın
```

Parametre isimleri, belirli bir maliyetteki birimi uzun süre görmeyen oyuncu için shop'un o maliyete doğru "zorlandığını" düşündürüyor. **Bu bir çıkarım;** mekaniğin tam formülü ve Set 18'de aktif olup olmadığı doğrulanmadı [KAYNAK GEREKLİ].

---

## 3. Lisans ve yeniden kullanım tablosu

| Bileşen | Lisans | Yeniden kullanım | Not |
|---|---|---|---|
| `tft_analyzer` kodu | **Yok** (tüm hakları saklı) | **Kopyalanamaz.** Fikir ve mimari, kendi kodumuzla yeniden yazılabilir | İstenirse yazardan lisans eklemesi rica edilebilir |
| `teamfight-simulator` kodu | ISC (`package.json`), LICENSE dosyası yok | Hukuken izin verici (telif ve izin metni korunarak) | Lisans metni dosya olarak yok; kullanmadan önce yazarın niyeti teyit edilmeli |
| `academy-library` kodu (ETL) | ISC, Copyright 2022 Kyle Coburn | İzin verici | TypeScript; bizim Python çekirdeğimize doğrudan uymaz |
| `academy-library` içindeki **veri** (istatistikler, oranlar, ikonlar) | ISC'nin kapsamı değil; Riot oyun dosyalarından türetilmiş | Riot'un fikri mülkiyeti. Planımızdaki CommunityDragon kuralı geçerli: "community-extracted" etiketi, yama notuyla çapraz kontrol | Set 11'de kaldı; zaten güncel değil |
| CommunityDragon | Lisans belirtilmemiş, Riot onaylı değil | Planımızdaki "dikkatli kullan" kararı aynen geçerli | |

Kısa özet: **Lisans açısından kullanılabilecek tek kod tacticians-academy'ninki (ISC); ama o kod da bizim için ya kapsam dışı (dövüş) ya da güncel değil (Set 11 verisi).** Yeniden kullanım kod değil, fikir düzeyinde olmalı.

---

## 4. Bizim hedefimiz açısından karşılaştırma

### 4.1 Hangi bileşenleri yeniden kullanmak mantıklı (fikir olarak, kendi kodumuzla)

| Fikir | Kaynak | Nereye | Neden |
|---|---|---|---|
| Ham JSON'u önce diske yaz, parse'ı ayrı ve tekrarlanabilir tut | tft_analyzer `ingest.py` | M2 `ingest` | Planla zaten uyumlu; uygulama şablonu hazır |
| Çok pencereli, thread-safe rate limiter + `Retry-After` + 401/403 mesajı | tft_analyzer `ratelimit.py`, `client.py` | M2 `ingest` | Küçük, iyi düşünülmüş; ~40 satırlık bir şey, kendimiz yazarız |
| Platform → bölge yönlendirme tablosu | tft_analyzer `config.py` | M2 | Riot dokümanından da alınabilen basit tablo |
| Beş tablolu normalize şema (maç / oyuncu / birim / trait) | tft_analyzer `storage.py` | M2 `datasets` | Başlangıç şeması; gizlilik ve doğrulama sütunları eklenerek |
| Gömülü DuckDB | tft_analyzer | M2 | "Veritabanı sunucusu yok" kuralımızla uyumlu; Parquet ile birlikte değerlendirilebilir |
| Oyun dosyasından shop oranı, havuz boyutu, seri altını, bad luck protection çıkarma | academy-library `build/etl/transformMap.ts` | **M1 `gamedata`** | Elle girişi azaltır; her alan `source=community-extracted` olur |
| Kalan kopya sayısıyla orantılı birim seçimi | teamfight-simulator `RolldownShop.vue` | M1 `prob.sampler` | Bizim varsayımımızla aynı; bağımsız bir ikinci uygulama olarak kontrol noktası |
| Set'e özel shop kuralları için kanca (Headliner gibi) | teamfight-simulator | M1 şeması | Set 18'de de böyle bir sistem olabilir; şema esnek olmalı |

### 4.2 Hangi kısımlar güncel değil veya güvenilir değil

| Kısım | Sorun |
|---|---|
| teamfight-simulator dövüş motoru | Yetenek, trait, item, augment etkileri sadece Set 6/6.5 (2022). 94 tahmini sabit. Tohumlanamayan RNG. Tarayıcıya bağlı. Set 18 için kullanılamaz |
| academy-library verisi | Set 11'de kaldı (Mart 2024). Hash anahtarlarına bağlı ETL, yeni oyun dosyalarında kırılabilir |
| tft_analyzer kompozisyon imzası | Sabit kural, kararlılık ölçülmüyor, item dağılımına duyarlı |
| tft_analyzer istatistikleri | Güven aralığı yok, yama ayrımı yok, seçilim ve örnekleme yanlılığı düzeltilmiyor |
| tft_analyzer augment modülü | API'de veri yok; aşama eşleştirmesi doğrulanmamış |
| tft_analyzer "Set 17 doğrulandı" iddiası | Depoda kanıt yok; testler sentetik Set 14 fikstürüyle |
| tft_analyzer `latest` CommunityDragon | Eski yamaların isim ve maliyetleri yanlış eşleşebilir |

### 4.3 Rakip rekabetini ve strateji değişimlerini analiz etmek için neler eksik

İki projede de olmayan, bizim planda karşılığı olan şeyler:

1. **Lobi düzeyi veri modeli:** Her maç için 8 tahtanın birlikte tutulduğu bir görünüm; "bu lobide aynı arketipi kaç kişi oynadı" (M3, M5).
2. **Havuz çakışması:** Aynı birimleri tutan rakip sayısının, o birimi yükseltme olasılığına etkisi. Bunun için M1 olasılık motoru + `PoolBelief` gerekiyor; hiçbir projede yok.
3. **Rekabet etkisi ölçümü:** n kişi aynı kompozisyondayken ortalama sıralama farkı, güven aralığıyla (M5).
4. **Kararlı arketip taksonomisi:** Kümeleme + bootstrap kararlılığı (M3). tft_analyzer'ın sabit imzası bunun yerini tutmaz.
5. **Yama bazlı trend:** Arketip paylarının ve gücünün yamadan yamaya değişimi, yama kayması testleri.
6. **Aşamaya göre tahta gücü:** Elenen oyuncuların tahtalarının `last_round` ile analizi ve seçilim yanlılığının düzeltilmesi (M4).
7. **Tahmin ve doğrulama altyapısı:** Zaman bölmeli train/test, aynı maçın 8 oyuncusunun aynı bölmede kalması, kalibrasyon.
8. **8 oyunculu makro simülasyon ve rakip politikaları:** teamfight-simulator sadece iki takım arasında tek bir dövüş yapıyor (M6).
9. **Örneklem tasarımı:** Elo dilimlerine göre dengeli örnekleme ve tekrar eden oyuncuların ağırlıklandırılması.

Sonuç: Bu projeler M3-M7'deki işi kısaltmıyor. Planın "rakip ve rekabet" bölümü bu açıdan özgün kalıyor.

---

## 5. M0 + M1 kapsamına etkisi

### 5.1 Önerilen değişiklikler

**M0 (iskelet):** Değişiklik gerekmiyor. Sadece öneri: M2'de DuckDB kullanılacaksa (bkz. 4.1) M0'da bağımlılık politikası belirlenirken bu not edilebilir. Kod veya bağımlılık eklemiyoruz.

**M1 (ekonomi ve shop olasılık çekirdeği):** Üç ekleme öneriyorum.

1. **Bad luck protection doğrulaması (yeni, öncelikli).**
   - Görev: Set 18 oyun dosyalarında (CommunityDragon `map22.bin.json`) bu parametrelerin hâlâ olup olmadığını ve resmi bir açıklama (yama notu, geliştirici yazısı) olup olmadığını kontrol et. Bu sandbox'tan CommunityDragon erişimi daha önce engelliydi; senin bilgisayarından veya başka bir yoldan bakmak gerekebilir.
   - Aktifse: Shop'lar bağımsız değildir. `prob.exact` durumuna "maliyet başına son görülmeden beri geçen shop sayısı" sayaçları eklenmeli; `prob.sampler` aynı kuralı uygulamalı. Kesin hesap ve Monte Carlo karşılaştırma testleri (30 senaryo) hem koruma açık hem kapalı varyantlarda çalışmalı.
   - Formül oyun dosyasından tam çıkarılamazsa: Koruma `status=unknown` olarak işaretlenir, M1 iki modeli (bağımsız / korumalı tahmini) yan yana raporlar ve fark hassasiyet analizi olarak gösterilir.
   - Tasarım sonucu: `prob` modülünde shop modeli **takılabilir** olmalı (bağımsız shop, korumalı shop, set'e özel kurallar).

2. **Oyun dosyasından otomatik `gamedata` çıkarıcı (opsiyonel, M1 kapsamına küçük ekleme).**
   - Shop oranları, havuz boyutları, seri altını ve (varsa) koruma parametreleri için kendi küçük çıkarıcımız. Her alan `source=community-extracted`, `status=unverified`; yama notu veya oyun içi tooltip ile eşleşen alanlar `verified` olur.
   - Şema doğrulayıcı kabul kriteri aynen kalır (kaynaksız alan reddedilir).
   - Kod kopyalanmaz; academy-library'nin hangi alanları nereden okuduğu sadece referans olarak kullanılır. Hash anahtarlarına bağımlılık bir risk olarak not edilir.

3. **Set'e özel shop kuralları için şema kancası.**
   - Headliner gibi set mekanikleri (ör. yıldızlı birim, özel olasılık tablosu, tekrar sınırları) için `gamedata` şemasında opsiyonel bir "shop modifier" bölümü. Set 18'de böyle bir sistem var mı, ayrıca kontrol edilmeli [KAYNAK GEREKLİ].

### 5.2 Değişmeyenler

- **Dövüş simülatörü yapmama kararı geçerli.** teamfight-simulator, gerçek TFT'ye yakın bir dövüş motorunun ne kadar pahalı olduğunu (956 commit, iki yarım set, 94 tahmini sabit, 19 aydır bakımsız) somut olarak gösteriyor. M4'teki veriden öğrenilen tahta gücü yaklaşımı daha gerçekçi.
- **M1'in API'ye ihtiyacı yok**; bu projeler bunu değiştirmiyor.
- M1 kabul kriterleri aynı kalıyor; bad luck protection aktifse kesin hesap/Monte Carlo testleri iki varyantla tekrarlanıyor.

### 5.3 M2'ye etkisi (bilgi için)

tft_analyzer, M2'nin iskeletini hızlandıracak net bir şablon. Bizim versiyonumuzda farklı olması gerekenler: PUUID hash'leme ve Riot ID'yi atma, ranked ve yama filtresinin tarama anında uygulanması, `startTime` ile zaman penceresi, şema doğrulama ve geçersiz kayıt dosyası, yama sabitlenmiş statik veri, elo dengeli örnekleme, zaman bölmeli veri setleri.

---

## 6. Önerilen sonraki adımlar

1. PLAN.md'nin sahibi olan oturumun M1 bölümüne yukarıdaki üç maddeyi eklemesi (bu raporu yazan oturum PLAN.md'yi değiştirmedi).
2. Bad luck protection'ın Set 18'deki durumunu doğrulamak. En hızlı yol: Set 18 `map22.bin.json` dosyasında ilgili bloğa bakmak ve resmi bir açıklama aramak.
3. İstersen `tft_analyzer` yazarına lisans eklemesini rica etmek. Ama gerekli değil; fikirleri zaten kendimiz yazabiliriz.

---

## Kaynaklar

- tft_analyzer: https://github.com/kiwoongk1m/tft_analyzer (commit `f2a2d8b`). İncelenen dosyalar: `src/tft/{config,ratelimit,client,ingest,parse,storage,static_data,web,cli}.py`, `src/tft/modules/*.py`, `tests/*`
- teamfight-simulator: https://github.com/tacticians-academy/teamfight-simulator (commit `a3faa9e`). İncelenen dosyalar: `src/sim/loop.ts`, `src/sim/ChampionUnit.ts`, `src/sim/helpers/{constants,calculate}.ts`, `src/sim/data/imports.ts`, `src/ui/components/RolldownShop.vue`, `src/store/store.ts`, `package.json`
- academy-library: https://github.com/tacticians-academy/academy-library. İncelenen dosyalar: `LICENSE`, `build/etl/{extract,transformMap}.ts`, `dist/set11/map.ts`; npm sürüm geçmişi (`0.33.0`, 9 Mart 2024)
- Canlı tftsim: https://tftsim.netlify.app
- Set 18 ve yama takvimi: https://seemeta.com/en/tft/set-18/release-dates · https://esports.gg/news/teamfight-tactics/tft-patch-schedule-2026/
