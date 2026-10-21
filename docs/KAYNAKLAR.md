# Kaynak envanteri ve araştırma bulguları (Set 18)

Araştırma tarihi: 2026-10-20 (canlı yama 18.4 / 18.4b). Plan: [PLAN.md](PLAN.md) bölüm 2–3.

Bu belge kaynakların gerçekten açılıp okunmasıyla hazırlandı. Okunamayan veya doğrulanamayan her şey "doğrulanamadı" bölümünde ayrıca listelendi.

**Öncelik sırası:**
1. Resmi yama notu
2. Oyun içi gözlem
3. Oyun dosyası (CommunityDragon)
4. Data Dragon
5. Wiki ve istatistik siteleri

Çelişkiler birleştirilmez; iki değer de kaynağıyla birlikte saklanır.

---

## 1. Resmi Riot kaynakları

### 1.1 Yama notları

| Yama | Tarih | URL | Sistem değişiklikleri |
|---|---|---|---|
| 18.1 | 2026-08-26 | https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/teamfight-tactics-patch-18-1 | Wisp'ler: 7 kategori, her iki shop'ta bir, 5. aşamadan sonra her ikinci Wisp Combat Wisp. Carousel geri döndü. Augment Cycling kaldırıldı. Yaklaşık 40 augment çıktı, 23 augment geri döndü. Kontrol etkisinden çıkan birim hedef değiştirmiyor. B-yamaları: 27, 28, 31 Ağustos ve 1 Eylül |
| Set özeti | — | https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/enchanted-wilds-overview/ | Wisp: tur başına bir alım. Blossom eşikleri Wisp kurallarını değiştiriyor |
| 18.2 | 2026-09-09 | …/teamfight-tactics-patch-18-2 | **XP 7→8: 60→56. 8→9 ve 9→10: 68→64, sonra 14 Eylül ara yamasında tekrar 68.** Bloodthirster, Edge of Night ve Hand of Justice değişti. Wisp maliyetleri düşürüldü |
| 18.3 | 2026-09-22 | …/teamfight-tactics-patch-18-3 | Wisp nerf'leri. Yaklaşık 15 augment ayarı, 4 augment geçici olarak kapatıldı. Inferno yanma oranı 1/1/3,5/4,5% → 1/1/3/4%. Greater Polymorph kapatıldı. 18.3B: 24 Eylül |
| 18.4 | 2026-10-06 | …/teamfight-tactics-patch-18-4 | Augment altın ve XP değerleri değişti. Combat arrival ve departure 1'er sn kısaldı. Wisp değişiklikleri: 0 maliyetli Wisp'ler (Drizzle, Grove Armor, Returning Friend, Room for a Shroom) sadece altın 10'un altındayken çıkıyor. Blossom AD/AP 12/30/50/55%. Riftbeast(7) %6. B-yaması: 7 Ekim |
| 18.5 | 2026-10-21 (planlanan) | …/teamfight-tactics-patch-18-5 | **20 Ekim'de yayımlanmamıştı (404).** Resmi olmayan önizleme (https://topmeta.gg/en/update/tft-patch-18-5/): oyun başına en fazla bir Destiny ailesi ve bir unique-item ailesi augment'i |

18.1–18.4 notlarının hiçbirinde shop olasılığı değişikliği yok.

### 1.2 Data Dragon (resmi, kısıtlı)

- Sürüm listesi: https://ddragon.leagueoflegends.com/api/versions.json. 20 Ekim'de en yenisi `16.20.1`.
- `/cdn/16.20.1/data/en_US/tft-champion.json`: Set 18 şampiyonları var, örneğin `DA_Gromp18_AP`. Alanlar: `id`, `name`, `tier`, `cost`, `image`.
- `tft-trait.json`: Set 18 trait'leri var (`DA_18_Adaptor`, `DA_18_Brawler`, `DA_Riftbeast18` …), sadece `id`, `name`, `image`.
- `tft-augments.json`: `id`, `name`, `description`, `image`. Set 18 kapsamı **doğrulanamadı** (dosyanın yalnızca bir kısmı okundu).
- İstatistik, yetenek değeri, tarif ve trait eşiği **yok**.
- Riot'a göre güncelleme elle yapılıyor ve gecikebiliyor. Hangi kaydın hangi sete ait olduğu sadece isimden anlaşılıyor.

### 1.3 Riot API `tft-match-v1`

https://developer.riotgames.com/api-details/tft-match-v1

- `ParticipantDto`: companion, gold_left, last_round, level, placement, players_eliminated, puuid, riotIdGameName, riotIdTagline, time_eliminated, total_damage_to_players, traits, units, win.
- `UnitDto`: items, character_id, itemNames, chosen, name, rarity, tier.
- **Augment alanı yok.** Kasım 2024'te kaldırıldı ([Overwolf, 29 Kasım 2024](https://blog.overwolf.com/developers-november-newsletter-user-reviews/)). Güncel şemada da yok ([riotapi-schema](https://www.mingweisamuel.com/riotapi-schema/openapi-3.0.0.json)).

### 1.4 Riot TFT geliştirici politikası

Kaynaklar:
- https://support-developer.riotgames.com/hc/en-us/articles/22698732381587-Teamfight-Tactics (son güncelleme 2025-03-07; Zendesk API ile okundu)
- https://developer.riotgames.com/docs/tft

Alıntılar:

- Onaylı (production anahtarı ve RSO ile): *"Game overlays that provide static data that is available prior to the game."*
- Onaysız:
  - *"Scouting - tracking the champions opponents have on their boards."*
  - *"Apps that provide dynamic, real-time information."*
  - *"Apps that dictate player decisions."*
- *"Having a static recommendation for a player pre-game is acceptable, even if that same recommendation is available to you the entire game. Issues arise when the recommendations adjust in real time based on the player's actions in game and give direct prescriptions of what to do."*
- *"An app cannot make suggestions based on the player's current game state as that information is dynamic and not readily available prior to the game start."*
- *"Apps and overlays during the game may not include any real-time data that would improve a player's performance immediately by altering player behavior …"*
- *"Products cannot display win rates for Legends and Legend-based Augments."*
- *"If your product serves players, you must register it with us."*

**Plan için anlamı:** Bilgi altyapısı ve maç sonrası analiz uygun. Maç sırasında anlık duruma göre öneri, politikanın açıkça onaylamadığı kullanım. Bu konu MVP'den sonra ayrıca karara bağlanacak (PLAN bölüm 0).

---

## 2. Oyun dosyası verisi (CommunityDragon)

**Ana dosya:** https://raw.communitydragon.org/latest/cdragon/tft/en_us.json (yaklaşık 23 MB).
- Canlı sürüm `16.20.8248524`, 2026-10-19. Sürüm klasörleri `/16.19/` ve `/16.20/` saklanıyor.
- `/pbe/` = `16.21.8289811`, muhtemelen 18.5.
- **16.20 = 18.4 eşlemesi tarihten çıkarıldı; kaynakta yazmıyor.**

**Yapı:**
- `setData[]` içinde `mutator: "TFTSet18"`, `number: 18` olan kayıt: 91 şampiyon, 36 trait, 776 item, 592 augment. Mod varyantları (`_PAIRS`, `_TURBO` …) ayrı kayıtlarda.
- `sets["18"]`: `champions`, `traits`. Buradaki `name` alanı "Set10", eskiden kalmış bir etiket.
- `items[]`: item'lar, augment'ler ve Wisp'ler aynı düz listede. Alanlar: `apiName`, `composition`, `effects`, `desc`, `isAugment`, `tags`, `associatedTraits`, `incompatibleTraits`, `unique`, `icon`.

**Set 18 ad önekleri:**
- `DA_` ve `DA_18_` (TFT18_ değil).
- Augment havuzu karışık: yaklaşık 209 `DA_*`, 33 `DA_18_*`, 217 geri dönen `TFT_Augment_*` ve eski set önekleri.

**Örnek şampiyon:**
```json
{"apiName":"DA_18_Sett","cost":4,"traits":["Blossom","Brawler"],"role":null,
 "stats":{"armor":60.0,"attackSpeed":0.65,"critChance":0.25,"critMultiplier":1.4,"damage":80.0,
          "hp":1200.0,"initialMana":60.0,"magicResist":60.0,"mana":135.0,"range":1.0},
 "ability":{"name":"Haymaker","desc":"...healing for @HealthCalc1@ ... @PhysicalDamageCalc1@ physical damage...","variables":[]}}
```

**Örnek augment:**
```json
{"apiName":"DA_18_BigGrabBag","isAugment":true,"name":"Big Grab Bag",
 "desc":"Gain 3 random components, @Gold@ gold, and 1 Reforger.","effects":{"Gold":2.0},"tags":["{ce1fd21c}"]}
```

**Örnek tarif:** `TFT_Item_InfinityEdge` → `composition: ["TFT_Item_BFSword","TFT_Item_SparringGloves"]`.

**Önemli bulgu (2026-10-20): oyun dosyası sayıları resmi notların gerisinde kalabiliyor.**
- 16.20 dışa aktarımında 18.4'te **eklenenler** var: yeni Wisp'ler, Min-Max'ın 4 altını, Small Furry Friend %45.
- Ama 18.4'teki **sayısal ayarlamaların çoğu yok:** Level Up! 6 XP (notta 10), Future Focused 8 altın (notta 5), Backrow Star %85 (notta %100).
- Muhtemel sebep: denge ayarlarının sunucu tarafında yapılması.
- **Kural:** Değişen değerlerde resmi not esastır. Bu değerler `curated/overrides/<yama>.json` içine işlenir; her kayıt dosyadaki eski değeri kontrol eder.
- **Set 18 item'ları (`DA_`):** Dışa aktarımda istatistik ve açıklama **boş**. Aynı item'ların eski set kopyaları (`TFT_Item_*`) eski değerleri taşıyor; örneğin Bloodthirster 18.2 öncesi değerlerle duruyor. Set 18 değeri olarak kullanılmaz.

**tactics.tools bilgi sayfaları (`/info/items`, `/info/augments`) da eski:**
- Sayfa "Set 18" diyor, ama değerler 18.2 durumunda:
  - 18.2 Bloodthirster değişikliği var.
  - 18.3'teki Collector, Statikk Shiv ve Upward Mobility değişiklikleri yok.
  - 18.4'teki Crownguard, Spirit Visage, Level Up! ve Chosen of the Sun değişiklikleri de yok.
- Elle aktarımda kaynağın yaması 18.2 olarak kaydedildi; 18.3 ve 18.4 değişiklikleri resmi notlardan işlendi (`tools/curate_item_stats.py`, `tools/curate_augment_tiers.py`).
- **Aktarımın doğrulaması:** 103 item'ın 84'ü eski oyun dosyası kopyalarıyla istatistik olarak birebir aynı. Farklar ya yamalarla değişen item'larda ya da başka setlerden gelen artifact'larda.

**Bilinen boşluklar:**
- **Yetenek değişkenleri:** 74 `DA_` şampiyonun sadece 2'sinde `ability.variables` dolu. Eski setlerde yıldız başına 7 değerlik diziler vardı.
- **Trait değişken adları hash'li.** Örnek `DA_18_Brawler`: `{"{da2472a7}":120.0,"{f1ed73eb}":0.25}`. Açıklamadaki adlar (`@BrawlerTeamHealth@`) aday olarak kullanılabilir.
- **Augment tier'ı** (silver/gold/prismatic) sadece hash'li `tags` içinde.

**Oyun dosyası (`map22.bin.json`):** https://raw.communitydragon.org/latest/game/data/maps/shipping/map22/map22.bin.json
- `Maps/Shipping/Map22/Sets/TFTSet18` → `DropRateTables.Shop = "{1ee21754}"`, `ScriptData.NumAugmentRerollsPerPlayer: 1`.
- Shop olasılıkları (1/2/3/4/5 maliyet):

| Level | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 3 | .75 | .25 | | | |
| 4 | .55 | .30 | .15 | | |
| 5 | .45 | .33 | .20 | .02 | |
| 6 | .30 | .40 | .25 | .05 | |
| **7** | **.19** | **.30** | **.40** | **.10** | **.01** |
| 8 | .15 | .20 | .32 | .30 | .03 |
| 9 | .10 | .17 | .25 | .33 | .15 |
| 10 | .05 | .10 | .20 | .40 | .25 |
| 11 | .01 | .02 | .12 | .50 | .35 |

- TFT XP tablosu ve havuz boyutları bu dosyada **bulunamadı**.

**Lisans:** *"CommunityDragon was created under Riot Games' 'Legal Jibber Jabber' policy … Riot Games does not endorse or sponsor this project."* Resmi değil ve bir hizmet garantisi (SLA) yok.

---

### Set 18 yetenek sayıları: oyun dosyalarında yok (2026-10-21)

- `cdragon/tft/en_us.json` (16.20): 74 şampiyon kaydının 72'sinde `ability.variables` boş (sadece Alune ve Kobuko'da var).
- `game/data/characters/da_18_<ad>/` klasörlerinde (ör. `da_18_ahri/`) sadece `animations/` ve `skins/` var; şampiyonun ana `.bin.json` veri dosyası yok.
- `map22.bin.json` içinde Set 18 için sadece shop kayıtları var (`Sets/TFTSet18/Shop/DA_18_Ahri`); yetenek (spell) verisi yok.
- Sonuç: Yetenek hasarı, kalkan ve iyileştirme değerleri `unknown` kalıyor. Sadece savaş hesabında gerekli (B6 ve sonrası). Gerekirse ana carry'ler için MetaTFT'den veya oyundan elle alınır.
- Hasar türü (AD/AP) yetenek açıklamasındaki ikonlardan okunuyor (`%i:scaleAD%`, `%i:scaleAP%`). 65 şampiyonun hepsinde açıklama var.
- Roller (Tank, Fighter ...) dışa aktarımda sadece 2 şampiyonda var (Alune `APCaster`, Kobuko `APTank`). Diğerleri `curated/champion_roles.json` ile elle girilecek.

## 3. Mekanik değerleri: repo ile karşılaştırma

| Konu | Değer | Kaynak | Tür | Repo ile |
|---|---|---|---|---|
| Shop olasılıkları | yukarıdaki tablo; seviye 7 hariç | map22.bin | oyun dosyası | aynı |
| Seviye 7 | 16/30/43/10/1 | **oyun içi tooltip** (sahibin ekran görüntüsü, 18.4b, 2026-10-20); siteler de (esportstales, tftflow, noxutft, mobalytics) | oyun içi gözlem | repo bunu kullanıyor |
| Seviye 7, çelişen değer | 19/30/40/10/1 | map22.bin (dosyadaki tek shop tablosu) ve resmi 17.1 notu (2026-04-14). 18.1 notu olasılıklardan söz etmiyor | oyun dosyası + resmi geçmiş | çelişki kaydı. Gerçek roll'ların hangisine uyduğu kanıtlanmadı |
| Havuz | 30/25/18/10/9 kopya | seemeta (PBE sayfası "istemciden" diyor), tftflow, metabot | topluluk | aynı |
| Şampiyon sayısı | 14/13/14/14/10 = 65 (Lux'un 9 formu ayrı) | https://tactics.tools/info/units | topluluk | aynı |
| XP tablosu | 2/2/6/10/20/36/56/68/68 | resmi 18.2 farkları + tftflow | resmi + topluluk | aynı |
| XP alımı, pasif XP, reroll | 4 altın = 4 XP; tur başına 2 XP; reroll 2 altın | noxutft; sahibin oyun içi kontrolü (18.4b) | oyun içi gözlem | aynı, `verified` |
| Max level | 10 (11 sadece augment'le?) | kaynak yok | — | bilinmiyor |
| Temel gelir | 2/2/3/4 (1-2…2-1), sonra 5 | op.gg, wiki TFT:Gold | topluluk | aynı |
| Faiz | 10 altın başına 1, en fazla 5 | op.gg, wiki | topluluk | aynı |
| PvP galibiyeti | +1 | op.gg, wiki | topluluk | aynı |
| Seri | 2–4 → +1, 5 → +2, 6+ → +3 | op.gg (Set 18), resmi 14.8 | topluluk + resmi geçmiş | aynı. Çelişki: wiki 3–4, bunnymuffins 2–3/4/5+ |
| Reroll | 2 altın | resmi kaynak yok | — | doğrulanmadı |
| Satış | 1 yıldız veya 1 maliyetli birim tam iade; diğerleri −1 (ör. 2★ 2 maliyetli = 5) | wiki TFT:Gold, TFT:Champion | topluluk | repoda yok. Wiki kendi örneğiyle çelişiyor (3★ 1 maliyetli) |
| Sahne hasarı | 0/2/5/8/10/12/17/150 + hayatta kalan rakip birim başına 1 | op.gg, tft.ninja, lolchess. Resmi 14.8: 0/2/5/7/9/11/17/150 | topluluk | repoda yok. Çelişki: tftflow 2/6/7/10/12/17 |
| Kötü şans koruması | Set 18 için kaynak yok | — | — | bilinmiyor |
| Augment aşamaları | 2-1, 3-2, 4-2. İlk augment yaklaşık Gold %65 / Silver %26 / Prismatic %9 | tftflow | topluluk | repoda yok |
| Augment sayısı | 69 silver / 112 gold / 68 prismatic = 249 | tactics.tools | topluluk | repoda yok |
| Tahta | 7×4 yarı tahta | topluluk ve eski setler | topluluk | — |
| Mana | Saldırı başına 10 (Assassin/Marksman/Fighter), 7 (Caster), 5 (Tank). Tank'lar hasardan mana alır: ön-azaltma %1 + son-azaltma %3, en fazla 42,5. Büyü sonrası 1 sn kilit | wiki TFT:Mana | topluluk | çelişki: %3 mü %7 mi |

**Set 18 mekanikleri** (wiki: https://wiki.leagueoflegends.com/en-us/TFT:Enchanted_Wilds; Wisp listesi: https://tftenchantedwilds.wiki/tools/wisp-reference/):
- **Wisp:** Her iki shop'tan birinin en sağ slotunda çıkıyor. Tur başına 1 alınabiliyor (Blossom 9'da 2), sadece planlama aşamasında. Alınınca arkasındaki birim görünüyor. Toplam yaklaşık 201 Wisp var (op.gg sayısı).
- **Blossom:** 3'te Wisp'ler güçlenir; 5'te her shop'ta Wisp; 7'de Wisp alınca +4 altın; 9'da tur başına 2 Wisp; 11'de "overflow".
- **Inferno:**
  - 3'te, savaştan sonra Inferno şampiyonu olmayan 1 shop slotu tutuşur ve bir üst maliyetten birim getirir.
  - 5'te 2 slot, 7'de 4 slot tutuşur.
  - Yanma oranı 1/1/3/4%.
- **Riftbeast:** 3'te Alpha Mark; 5'te her 3 savaşta bir sonraki shop Riftbeast'lerle dolar; 7'de her 5 sn büyüme (%6); 10'da +2 takım boyutu. Elder Dragon 2 slot kaplar ve trait'e +2 sayılır.

---

## 4. Meta ve istatistik siteleri

| Site | İçerik | Set 18 | API / şartlar | Augment istatistiği |
|---|---|---|---|---|
| [tactics.tools](https://tactics.tools/team-compositions) | Komp: oynanma, ortalama sıra, ilk 4, kazanma; birimler, item'lar, trait'ler; Diamond+ filtresi | 18.4b | API yok. [Şartlar](https://tactics.tools/terms) metninde kazıma maddesi yok, ama erişimi sonlandırma hakları var. Veri istenirse yazılı izin | Sütunlar var ama satırlar görünmedi, doğrulanamadı |
| [op.gg TFT](https://op.gg/tft/meta-trends/comps) | Komp: ortalama sıra, 1. olma, ilk 4, seçilme; "son 24 saatte 2.352.688 oyun" | 18.4 | Şartlar okunamadı | Görülmedi |
| [tftacademy](https://tftacademy.com/tierlist/comps) | Elle hazırlanmış S/A/B/C tier listesi (sayı yok) | 18.4b | Okunmadı | — |
| [tftactics.gg](https://tftactics.gg/tierlist/team-comps) | Tier listesi, oyun stili (Fast 8, Slow Roll) | 18.4b | Okunmadı | Yok |
| MetaTFT | Sayfa JavaScript gerektirdiği için okunamadı. Overwolf uygulaması tur tur kayıt tutuyor | ? | API yok | 2023'ten beri gösterilmiyor (kendi açıklaması) |
| seemeta | Augment harf notları. Kendi açıklaması: "maç verisinde augment yok, bu yüzden sayı yok" | 18.3 | — | Yok |
| mobalytics, blitz, metasrc, lolchess | 403 veya boş döndü | ? | ? | ? |

**Dikkat:** op.gg'nin sayıları "kompu tamamlayan oyuncular" üzerinden; tactics.tools'tan çok daha iyimser (aynı komp için 2,73 ve yaklaşık 4,3). Siteler arası sayılar doğrudan karşılaştırılmaz. Her meta kaydına site, rank filtresi, yama ve tanım yazılır.

---

## 5. Açık kaynak projeler

| Repo | Dil | Lisans | Son push | Ne alınabilir |
|---|---|---|---|---|
| [tacticians-academy/academy-library](https://github.com/tacticians-academy/academy-library) | TS | ISC | 2024-03 | CDragon'dan tipli set verisine dönüşüm (şema fikri; kod lisanslı) |
| [tacticians-academy/teamfight-simulator](https://github.com/tacticians-academy/teamfight-simulator) | TS | yok | 2024-03 | Dövüş motoru fikirleri (sadece fikir) |
| [CommunityDragon/CDTB](https://github.com/CommunityDragon/CDTB) | Python | LGPL-3.0 | 2026-10 | Ham BIN/WAD çözümleme, hash yöntemi |
| [Borcioo/tft-scout](https://github.com/Borcioo/tft-scout) | TS/PHP | yok | 2026-04 | BIN'deki büyü formüllerini çözme fikri (yetenek değerleri için) |
| [damian-kim/tft-roll-calc](https://github.com/damian-kim/tft-roll-calc) | JS | yok | 2026-08 | Bağımsız olasılık kontrolü (sadece sonuç karşılaştırması) |
| [HenryVu27/TFT-Rolling-Calculator](https://github.com/HenryVu27/TFT-Rolling-Calculator) | JS | MIT | 2025-08 | Olasılık kontrolü |
| [Fletch777/TFT-Roll-Down-Calculator](https://github.com/Fletch777/TFT-Roll-Down-Calculator) | Python | yok | 2026-07 | Markov fikri |
| [Remus3/Amberstone](https://github.com/Remus3/Amberstone) | Python | Apache-2.0 | 2026-10 | Belirlenimli matematik motoru yaklaşımı |
| [MielPopsssssss/TFT_GOAT](https://github.com/MielPopsssssss/TFT_GOAT) | Python | belirsiz | 2026-06 | 8 oyunculu ortam ve RL (ileride referans) |

**Kaçınılacaklar:** Oyunu otomatik oynayan veya gizlenen araçlar (TFT-OCR-BOT, otomatik alım yapan araçlar, "undetected overlay" repoları). Bunlar politikaya aykırı.

---

## 6. Doğrulanamayanlar (20 Ekim itibarıyla)

- 18.5 resmi notları (henüz yayımlanmadı).
- Data Dragon `tft-augments.json` dosyasında Set 18 kapsamı.
- Set 18 yetenek sayıları (CommunityDragon JSON'unda boş).
- Trait değişkenleri ve augment tier'ları için hash → ad eşlemesi.
- Oyun dosyasında XP tablosu ve havuz boyutları.
- LoL sürümü ↔ TFT yaması eşlemesi (16.20 = 18.4, çıkarım).
- Reroll maliyeti, XP alım oranı ve pasif XP için resmi kaynak.
- Max level ve level 11'e nasıl çıkıldığı.
- Kötü şans koruması.
- Augment tier kombinasyonlarının olasılıkları.
- Wisp'in arkasında 5. bir şampiyon olup olmadığı. Kaynaklarda sadece "arkasındaki birim görünür" ifadesi var.
- Hedefleme kuralları (resmi açıklama yok).
- MetaTFT, lolchess, mobalytics, blitz ve metasrc sayfaları ve şartları.
