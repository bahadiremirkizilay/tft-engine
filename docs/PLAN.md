# TFT Engine — Set 18 Bilgi Altyapısı: Teknik Plan (v0.5)

Tarih: 2026-10-20 · Kapsam: Set 18 (18.4 canlı, 18.5 21 Ekim) · Durum: **Onaylandı (2026-10-20)**
Önceki sürüm: [PLAN_v0.4.md](PLAN_v0.4.md) (değiştirilmeden saklandı; v0.4'ün M4–M9 ve veri bölümleri ileriki aşamalar için referans olarak geçerli)
Kaynak ayrıntıları: [KAYNAKLAR.md](KAYNAKLAR.md) · Veri kaynakları, erişim ve izin raporu: [VERI_KAYNAKLARI.md](VERI_KAYNAKLARI.md)

## Kararlar ve ekler (2026-10-20, VERI_KAYNAKLARI.md sonrası)

- **Amaç:** Kişisel kullanım. Hedef sahibin gelişimi ve pro arenada oynaması. Ticari ürün yok.
- **Otomatik veri sadece izinli kaynaklardan gelir:** CommunityDragon, Data Dragon, resmi notlar, ileride Riot API. MetaTFT, tactics.tools, TFT Academy, op.gg ve lolchess sadece elle ve kaynaklı not olarak kullanılır. İzin e-postası gönderilmeyecek.
- **Meta rank filtresi:** Master+ (Master, GM, Challenger). Örneklem azsa Diamond ve Emerald.
- **G0′:** Riot API kişisel anahtarı MVP'den sonra. Kendi meta istatistiğimiz için izinli tek otomatik yol bu.
- **B1'e ek:** `sources.json` kayıtlarında `site_patch`, `filters` ve `collected_by` alanları. Eski veri korumaları (VERI_KAYNAKLARI bölüm 9): farklı yamanın meta kaydı reddedilir, bilinen eski değerler uyarı verir, erişim tarihi yama tarihinden önceyse kayıt o yamaya atanmaz.
- **B5'e ek:** Meta kaydı şablonu (zorunlu `filters`, `sample`, `metric_definition`). Birim yıldız dağılımı ve item üçlüleri tactics.tools'tan. Komp şablonları ve dizilimler TFT Academy'den, kendi cümlelerimizle.
- **Yama başına elle iş bütçesi:** İlk yeni yamada belirlenecek.

## Neden bu plan

Projede M0, M1a ve P1 bitti (120 test geçiyor). P1, karar mimarisinin çalıştığını gösterdi. Ama motor şampiyonları, trait'leri, item'ları ve augment'leri tanımıyor. `data/sets/set18/base.json` içinde sadece ekonomi ve shop parametreleri var. Augment etkileri de P1'de düz alanlardan oluşuyor (`gold_now`, `xp_now` …), yani bir augment XP maliyetini değiştiremiyor.

Yeni öncelik maç kaydı ve ML değil. Önce oyun bilgisini doğru, bağlantılı, sürümlü ve sonraki setlere taşınabilir biçimde kuran bir **bilgi altyapısı** geliyor. Bu plan o altyapının kapsamını, kaynaklarını, şemasını, mekanik etkileşim mimarisini, yama stratejisini, doğrulamasını ve yol haritasını tanımlıyor.

---

## 0. Mevcut planla ilişki

**Korunanlar** (doğru ve değerli, değişmiyor):
- `Param(value, status, source, note)` ve `UnknownMechanicError`: bilinmeyen değer kullanılamaz (`src/tft_engine/gamedata/schema.py`).
- Yama katmanı: `base.json` + `patches/<p>.json` değişiklik kayıtları, `not_reviewed` uyarısı (`gamedata/loader.py`).
- `Rules`: her sayıyı veriden okuyor ve hangi parametreye dayandığını `used` içinde kaydediyor (`rules/economy.py`). Augment modifier sistemi bunun üzerine kurulacak.
- `ShopModel` protokolü, kesin çözücü ve Monte Carlo (`prob/`).
- Üç güven sınıfı, seed'li tekrar üretilebilirlik, P1 senaryoları (regresyon testi olarak).

**Değişen veya ertelenenler:**

| Eski plan | Yeni durum |
|---|---|
| M1b (Set 18 ayrıntıları) | Ekonomi ve shop kısmı **B2**'ye, Wisp/Inferno/Riftbeast **B3**'e girer. Kayıtlarla doğrulama ertelenir |
| G0, M2 (Riot API veri hattı) | Ertelendi (talimat bölüm 14) |
| M3 (taksonomi ve meta) | Önce elle kurulan komp şablonları (**B5**). Veriden kümeleme M2'den sonra |
| `decision/effects.py` `Effect` | Genel modifier sistemiyle değiştirilecek (**B3**). P1 aynı sonucu vermeye devam etmeli |
| PLAN 8.4 etki arayüzü | B3'teki modifier şemasıyla genişler |

**Çelişki ve tekrarlar:**
- PLAN.md bölüm 8.5'te aynı cümle iki kez geçiyor. P1_SONUC yolu `repo/docs/...` olarak yazılmış. Bunlar v0.5'te düzeltilecek.
- **Canlı öneri konusu:** Sahibi canlı (maç sırasında, kendi bilgisayarında) öneri istediğini söyledi. Bilgi altyapısı talimatı ise onu şimdilik kapsam dışı bırakıyor. Bu plan talimatı izliyor.
  - Riot'un TFT politikası (2025-03-07 güncellemesi) açıkça şöyle diyor: *"An app cannot make suggestions based on the player's current game state"* ve *"Apps that dictate player decisions"* onaylanmıyor.
  - Bilgi altyapısı ne canlı ne çevrimdışı moda bağlı. İki kullanım şekli de buna dayanır. Canlı mod kararı, MVP'den sonra hesap riski açıkça yazılarak ayrıca verilecek.

---

## 1. Kapsam haritası

**Modellenecek sistemler** (oklar "kullanır" anlamında):

```
Kaynak kaydı ─► tüm veriler (her kayıt bir source_id taşır)

Set/Yama tanımı ─► Şampiyon, Trait, Item, Augment, Wisp, Ekonomi, Shop
Şampiyon ◄─► Trait                  (üyelik, eşikler)
Item (bileşen → tamamlanmış tarif grafı) ─► Şampiyon uyumu (rol, istatistik)
Augment / Wisp / Item / Trait etkileri ─► Modifier katmanı ─► Ekonomi, XP, Shop, Savaş istatistikleri
Ekonomi + XP + Shop + Havuz ─► Olasılık motoru (prob)
Komp şablonu ─► Şampiyon, Trait, Item, Augment, level planı
Meta istatistiği (ayrı) ─► Komp şablonu   (bağlantı var, birleştirme yok)
Savaş/Dizilim arayüzü ─► Şampiyon istatistikleri, yetenek profili, tahta koordinatı
Doğrulama kaydı ─► her varlık ve parametre
```

**Bu aşamada modellenmeyenler:** dövüş sonucu hesabı, rakip davranışı, maç kayıtları, ML.

---

## 2. Kaynak envanteri (2026-10-20'de gerçekten açıldı)

| # | Kaynak | Ne sağlıyor | Güvenilir olduğu alan | Güncellik | Kısıt |
|---|---|---|---|---|---|
| R1 | **Resmi yama notları** 18.1–18.4 ([18.1](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/teamfight-tactics-patch-18-1), 18-2, 18-3, 18-4) + [Set özeti](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/enchanted-wilds-overview/) | Değişiklikler (XP 7→8 60→56; 8→9 ve 9→10 68→64→68; Wisp, augment, item ayarları) | Değişiklikler için en üst seviye | 18.5 henüz yayımlanmadı (404) | Tam değer tablosu vermez, sadece farkları verir |
| R2 | **CommunityDragon** `raw.communitydragon.org/<sürüm>/cdragon/tft/en_us.json` (canlı 16.20, 2026-10-19; PBE 16.21) | `setData` mutator `TFTSet18`: 91 şampiyon kaydı (74 `DA_` oynanabilir veya varyant), 36 trait (eşik ve değişkenler), 776 item, 592 augment. Item tarifleri (`composition`), augment `effects` sayıları, `incompatibleTraits`, `unique`, Wisp'ler | Maliyet, trait üyeliği, temel istatistikler, tarifler, augment ve trait sayıları | Her LoL sürümünde. Sürüm klasörleri saklanıyor | Resmi değil ("Legal Jibber Jabber"). **Set 18 yetenek değişkenleri boş** (74'ün 2'sinde var). Trait değişken adları ve augment tier'ları **hash'li** |
| R3 | **CommunityDragon oyun dosyası** `game/data/maps/shipping/map22/map22.bin.json` | Set 18 shop olasılık tablosu (seviye 1–11). **Seviye 7 = .19/.30/.40/.10/.01**. Augment yeniden çevirme hakkı 1 | Shop olasılıkları | Canlıyla aynı | XP tablosu ve havuz boyutları burada bulunamadı |
| R4 | **Data Dragon** `ddragon.leagueoflegends.com/cdn/16.20.1/data/en_US/tft-*.json` | Ad, maliyet, ikon (resmi). Set 18 şampiyon ve trait'leri var | Ad ve ikon | Riot'a göre elle ve gecikmeli güncelleniyor | İstatistik, tarif ve eşik yok. Augment dosyasındaki Set 18 kapsamı doğrulanmadı |
| R5 | **Riot TFT geliştirici politikası** (Zendesk 22698732381587, 2025-03-07) + [developer.riotgames.com/docs/tft](https://developer.riotgames.com/docs/tft) | Neyin yasak olduğu | Politika | 2025-03 | Canlı öneri, scouting ve Legend win rate yasak |
| R6 | **Riot tft-match-v1** | Maç sonu tahtaları ve item'lar | Meta istatistiği (ileride) | Canlı | **Augment alanı yok** (2024 sonundan beri) |
| R7 | **LoL wiki** (wiki.leagueoflegends.com TFT:Gold, TFT:Enchanted_Wilds, TFT:Mana) | Satış kuralı, mana kuralları, trait açıklamaları | Kural açıklamaları | Değişken; bazı satırlar eski | Topluluk kaynağı. Seri ve mana değerlerinde çelişkiler var |
| R8 | **tactics.tools** (/info/units, /team-compositions, /augments) | Birim listesi (14/13/14/14/10), komp istatistikleri (Diamond+, 18.4b), augment sayıları (69/112/68) | Liste ve istatistik | 18.4b | API yok. Sadece elle kıyaslama |
| R9 | **op.gg, tftacademy, tftactics.gg** | Komp ve tier listeleri (op.gg 2,35 milyon oyun/24 saat, "tamamlanan komp" yanlılığı) | Meta tablosu | 18.4/18.4b | Elle kullanım. ToS okunamadı |
| R10 | **seemeta, tftflow, metabot, topmeta** | Havuz 30/25/18/10/9, XP tablosu, augment teklif olasılıkları, 18.5 önizlemesi | Çapraz kontrol | Eylül–Ekim 2026 | Bir kısmı eski tabloları kopyalıyor (seviye 7 = 16/30/43 olan siteler) |
| R11 | **Açık kaynak** | academy-library (ISC: CDragon → tipli set verisi), CDTB (LGPL), tft-scout (formül çözme fikri), roll hesaplayıcıları (damian-kim, HenryVu27 MIT) | Şema ve doğrulama fikirleri | — | Lisanssız olanlardan sadece fikir alınır, kod alınmaz |
| R12 | **Oyun içi gözlem (sen)** | Tooltip ve shop sayımı | Nihai doğrulama | — | Elle; kontrol listesiyle yapılır |

**Kural:** Öncelik sırası R1 > R12 > R3/R2 > R4 > R7–R10. Çelişki sessizce birleştirilmez, `conflicts` alanında iki değer ve kaynakları yazılır.

---

## 3. Eksiklik ve risk raporu

| Bilgi | Durum | Zorluk |
|---|---|---|
| Şampiyon adı, maliyet, trait, temel istatistik | R2 + R4 + R8 çapraz kontrol. 65 oynanabilir şampiyon (14/13/14/14/10), Lux formları ayrı | Kolay |
| **Yetenek sayıları (yıldız başına)** | **R2'de Set 18 için boş.** Sadece metin şablonu var (`@HealthCalc1@`) | **Zor.** Ham `.bin` dosyalarından çözmek veya elle girmek gerekir. B4'te araştırılır; bulunamazsa `unknown` kalır |
| Trait eşikleri ve değerleri | R2'de var ama anahtarlar hash'li (`{da2472a7}`) | Orta. CommunityDragon'un hash yöntemiyle aday adlar (açıklamadaki `@BrawlerTeamHealth@`) hash'lenip eşlenir; eşlenemeyen hash'li kalır |
| Item tarifleri ve istatistikleri | R2'de `composition` ve `effects` var | Kolay–orta |
| Augment metni ve sayıları | R2'de 548/592 `effects` dolu. Set 18 havuzu `DA_`, `DA_18_` ve geri dönen `TFT_Augment_` karışık | Orta. **Hangi augment'in Set 18'de aktif olduğu** ayrı doğrulanmalı (R8 sayıları: 249) |
| Augment tier'ı | Hash'li `tags` içinde | Orta. Hash çözümü veya R8 ile elle eşleme |
| Augment etkisinin mekanik modeli | Metin → modifier dönüşümü elle yapılır | **Zor ve uzun.** Önce ekonomi, XP ve shop augment'leri |
| Augment teklif olasılıkları, tier kombinasyonları | Sadece topluluk (tftflow) | Zor, `third_party_unverified` |
| Shop olasılıkları | R3 (oyun dosyası) + resmi 17.1 geçmişi | **Seviye 7 çelişkisi oyun dosyasıyla çözülüyor** (19/30/40/10/1). Oyun içi tooltip ile son kontrol |
| XP tablosu | R1 farkları + R10 tablo | Kolay. 2/2/6/10/20/36/56/68/68 resmi farklarla tutarlı |
| Havuz boyutları | Sadece R10 | Orta. Oyun dosyasında aranır, yoksa `third_party_unverified` |
| Satış değeri, seri, sahne hasarı | Çelişkili kaynaklar | Oyun içi kontrol gerekli |
| Kötü şans koruması | Kaynak yok | `unknown` |
| Hedefleme ve savaş kuralları | Resmi kaynak yok, mana kurallarında çelişki var | Zor. Sadece arayüz kurulur |
| Meta istatistikleri | Sadece site arayüzleri, API yok | Elle ve küçük ölçekli |

**Riskler:**
- **Set 18'in kısa ömrü:** Set 19 1 Aralık'ta başlıyor. Yatırımın asıl değeri importer ve şemada; Set 19'a veri değişerek taşınır.
- **LoL sürümü ↔ TFT yaması eşlemesi** (16.20 = 18.4) çıkarımla bulundu. Her snapshot'ta tarihle doğrulanır.
- **Elle girilen augment modelleri ölçeklenmez:** Kapsam raporu ve öncelik sırası tutulur.
- **Kapsam büyümesi:** 600 augment ve 200 Wisp var. MVP sınırı (bölüm 9) buna karşı.

---

## 4. Veri şeması önerisi

**Seçim:** Git içinde JSON dosyaları + Python dataclass yükleyici. Veritabanı yok. Neden:
- Küçük bir solo projede diff'lenebilir ve gözden geçirilebilir.
- Mevcut yükleyiciyle uyumlu.
- Gerekirse sonra SQLite'a dönüştürülebilir.

İki katman var:
- **Üretilen katman** (importer yazar, elle düzenlenmez).
- **Elle katman** (düzeltmeler, doğrulamalar, modeller; importer asla ezmez).

```
data/
  sources.json                         kaynak kaydı (id, url, tür, erişim tarihi, sürüm, sha256)
  raw/ (gitignore)                     ham CommunityDragon indirmeleri
  snapshots/cdragon-16.20.manifest.json   ham dosyanın sha256'sı, tarih, eşlenen TFT yaması
  sets/set18/
    base.json                          (mevcut) ekonomi ve shop parametreleri
    patches/<p>.json                   (mevcut) değişiklik kayıtları; artık varlıkları da hedefleyebilir
    generated/<patch>/                 importer çıktısı: champions.json traits.json items.json augments.json wisps.json
    curated/                           elle katman
      overrides.json                   düzeltme kayıtları (alan, yeni değer, kaynak, neden)
      verifications.jsonl              oyun içi doğrulama kayıtları
      effects/augments.json            augment → modifier modelleri
      effects/items.json  effects/traits.json  effects/wisps.json
      comps/<patch>.json               komp şablonları
      meta/<patch>/<kaynak>.json       meta istatistikleri (ayrı)
      hash_names.json                  çözülmüş hash → ad eşlemesi
```

**Ortak alanlar** (her varlıkta): `id` (oyun apiName'i, setler arası kalıcı), `set`, `valid_from`, `valid_to`, `status`, `source_ids[]`, `conflicts[]`, `note`. `status` kümesi mevcut `STATUSES` ile aynı.

**Örnek: şampiyon** (generated + curated birleşimi):
```json
{"id":"DA_18_Sett","name":"Sett","cost":4,"traits":["DA_18_Blossom","DA_18_Brawler"],
 "stats":{"hp":[1200,2160,3888],"armor":60,"mr":60,"ad":80,"as":0.65,"range":1,"mana":135,"mana_start":60},
 "roles":{"value":["tank","frontline"],"status":"unverified","source_ids":["manual"]},
 "ability":{"name":"Haymaker","text":"...","damage_type":"physical","effects":["heal","damage"],
            "values":{"status":"unknown","source_ids":["cdragon-16.20"],"note":"Set 18 ability variables empty in CDragon"}},
 "pool_copies":{"value":10,"status":"third_party_unverified","source_ids":["seemeta-2026-10-18"]},
 "status":"community_extracted","source_ids":["cdragon-16.20","ddragon-16.20.1"]}
```
Yıldız başına can 1/1.8/3.24 çarpanı bir kuraldır, veri değildir. Bu yüzden `base.json` içinde `star_multipliers` parametresi olarak (kaynaklı) durur ve hesapla üretilir.

**Örnek: trait:**
```json
{"id":"DA_18_Brawler","name":"Brawler","units":["DA_18_Sett", "..."],
 "breakpoints":[{"min":2,"max":3,"vars":{"BrawlerHealthPercent":0.25,"BrawlerTeamHealth":120}},
                {"min":4,"vars":{"BrawlerHealthPercent":0.40}}],
 "unresolved_hashes":[], "modifiers_ref":"effects/traits.json#DA_18_Brawler"}
```

**Örnek: item:**
```json
{"id":"TFT_Item_InfinityEdge","kind":"completed","recipe":["TFT_Item_BFSword","TFT_Item_SparringGloves"],
 "stats":{"ad":0.35,"crit":0.35}, "unique":false, "tags":["damage","crit"], "effect_text":"..."}
```
`kind` değerleri: `component | completed | artifact | radiant | emblem | support | set_special`.

**Örnek: augment:**
```json
{"id":"DA_18_BigGrabBag","name":"Big Grab Bag","tier":{"value":"silver","status":"third_party_unverified"},
 "offered_at":["2-1","3-2","4-2"], "text":"Gain 3 random components, 2 gold, and 1 Reforger.",
 "raw_effects":{"Gold":2}, "families":[], "incompatible_traits":[],
 "categories":["economy","item"], "model_status":"modelled",   // modelled | partial | text_only
 "active_in_set":{"value":true,"status":"third_party_unverified"}}
```

**Örnek: komp şablonu:**
```json
{"id":"set18-18.4-riftbeast-elder","name":"Riftbeast Elder Dragon","patch":"18.4",
 "core":["DA_18_ElderDragon","..."],"flex":[{"slot":"frontline","options":["..."]}],
 "carries":[{"unit":"...","items":{"best":["..."],"alternatives":[["..."]]}}],
 "tanks":[...], "target_traits":[{"trait":"DA_Riftbeast18","min":5}],
 "augments":{"tags":["combat","riftbeast"],"specific":["..."]},
 "level_plan":[{"stage":"4-1","level":8,"action":"roll_to"}], "style":"fast8",
 "phases":{"early":"...","mid":"...","late":"..."},
 "entry_conditions":["2 Riftbeast units by 3-2"], "contest_sensitivity":"high",
 "strong_when":["..."], "weak_when":["..."], "pivots":["set18-18.4-..."],
 "source_ids":["tactics.tools-2026-10-20","tftacademy-2026-10-19"], "status":"third_party_unverified",
 "last_reviewed":"2026-10-20"}
```

**Örnek: meta istatistiği** (komptan ayrı):
```json
{"comp_ref":"set18-18.4-riftbeast-elder","source_id":"tactics.tools-2026-10-20",
 "patch":"18.4b","rank_filter":"Diamond+","region":"all","window":"patch",
 "games":null,"avg_place":3.65,"top4":null,"definition":"site clustering; not ours",
 "collected_by":"manual","collected_at":"2026-10-20"}
```

---

## 5. Mekanik etkileşim mimarisi

**Tek doğruluk kaynağı ilkesi:**
- Her oyun kuralı `GameData` içinde bir parametredir (`xp_purchase`, `reroll_cost`, `shop_odds`, `interest_cap` …).
- Kurallar (`Rules`, `ShopModel`) sabit sayı içermez; değerleri her zaman `effective(param, ctx)` ile okur.

**Modifier** (augment, item, trait, Wisp, yama: hepsi aynı şema):
```json
{"id":"aug:DA_X:xp_discount","source_entity":"DA_X","target":"params.xp_purchase.gold",
 "op":"set","value":3,"when":{"from_stage":"2-1"},"duration":"rest_of_game",
 "priority":0,"status":"third_party_unverified","source_ids":["cdragon-16.20"]}
```
- **`op`:** `set | add | mul | min | max | table_patch` (tabloda tek hücre).
- **`when` koşulları:** aşama, level, trait aktif, altın aralığı, HP aralığı. Bunlar küçük ve sabit bir koşul dilinden seçilir; serbest kod yok.
- **Sıra:** `set` → `add` → `mul` → `min/max`. Aynı adımda `priority`, sonra `id`. Böylece belirlenimli ve test edilebilir.

**Olay tetikleyicileri** (parametreyle ifade edilemeyenler):
```json
{"on":"round_end|reroll|level_up|buy_unit|combat_win|stage_start","do":{"gain_gold":2}, "limit":{"times":3}}
```
- Eylemler sabit bir kütüphaneden: `gain_gold`, `gain_xp`, `free_rerolls`, `gain_component`, `gain_unit`, `gain_item` vb.
- Kütüphanede olmayan bir etki `model_status: text_only` olur. Motor o etkiyi değerlendirdiğini iddia etmez.

**`GameContext`:**
- `GameState` + aktif modifier listesi. `effective()` sonucu, hangi modifier'ların uygulandığını kaydeder (`Rules.used` genişletilir).
- Örnek: XP maliyeti 3'e düşünce `buy_xp`, level maliyeti, "level mi roll mu" karşılaştırması ve P1 adayları otomatik tutarlı olur, çünkü hepsi aynı `effective("xp_purchase")` değerini okur.

**Augment–augment etkileşimleri:**
- Tüm kombinasyonlar elle yazılmaz (592² mümkün değil). Kurallı sistem şöyle:
  - (a) Modifier'lar sıralı ve birleşebilir olduğu için kombinasyonlar kendiliğinden çıkar.
  - (b) Açık dışlamalar veriden gelir: `unique`, `families` (18.5'te "bir Destiny ve bir unique-item augment'i" sınırı), `incompatible_traits`.
  - (c) Sıraya bağlı çiftler (ör. iki `mul`) için özellik testleri yazılır.
  - (d) Bilinen özel etkileşimler `curated/effects/interactions.json` içinde, kaynaklı tutulur.

**Shop'a dokunan kurallar** (Wisp slotu, Inferno, Riftbeast, Blossom 5): `ShopModel` takılabilir varyantları olarak eklenir; modifier'lar hangi varyantın açık olduğunu seçer. Doğrulanmamış kural varsayılan olarak kapalı başlar ve "açık/kapalı farkı" raporlanır (mevcut ilke).

**Savaş istatistiği modifier'ları** (AS +%10, kalkan): aynı şemayla `target: unit.stats.as` olarak saklanır. Şimdilik sadece tahta özelliği olarak toplanır; savaş hesabı yok.

---

## 6. Yama ve set güncelleme stratejisi

1. **Snapshot al:** `tools/import_cdragon.py --version 16.21` ham dosyayı indirir, sha256 ile manifest yazar, `generated/<patch>/` üretir.
2. **Diff raporu:** `tft-engine data diff 18.4 18.5`. Varlık ve alan bazında eklenen, silinen ve değişen kayıtları listeler.
3. **Etkilenenler:** Değişen her varlığa bağlı modifier, komp şablonu ve meta kaydı "yeniden gözden geçir" olarak işaretlenir. Ekonomi parametresi değiştiyse ilgili testler ve P1 senaryoları yeniden koşulur.
4. **Yama dosyası:** Resmi nota göre `patches/18.5.json` doldurulur. Snapshot diff'i ile yama notu arasındaki uyuşmazlıklar ("notta yok ama veride değişmiş" sessiz değişiklikleri) rapora girer.
5. **Eski sürümler korunur:** `generated/18.4/` silinmez. `load_gamedata(set, patch)` her zaman o yamanın dosyalarını okur.
6. **Set 19:** Yeni `data/sets/set19/` klasörü açılır; importer ve şema aynıdır.
   - Set'e özel mekanikler (Wisp gibi) `shop_rules` ve modifier ile ifade edildiği sürece kod değişmez.
   - Yeni mekanik bir tür gerektirirse bu açık bir kod değişikliğidir ve test ister.
   - **Prova:** Set 19 PBE verisi CommunityDragon `/pbe/`'ye düştüğünde (tahminen Kasım ortası) importer onunla denenir.

---

## 7. Doğrulama planı

| Modül | Doğrulama | Kabul kriteri |
|---|---|---|
| Şampiyonlar | R2, R4 ve R8 çapraz kontrol | 65 oynanabilir şampiyon; maliyet dağılımı 14/13/14/14/10 ile `champions_per_cost` aynı; her trait üyeliği iki yönde tutarlı |
| Trait'ler | Eşikler R2 ↔ tooltip (en az 5 trait elle örneklem) | Örneklemde %100 uyum; çözülemeyen hash sayısı raporlanır |
| Item tarifleri | Graf testi | Her tamamlanmış item'ın 2 bileşeni var ve bileşenler `component`; bileşen çiftlerinden tarif tablosu eksiksiz ve tekrarsız (bileşen sayısı Set 18 verisinden gelir, varsayılmaz); 5 tarif oyunda elle kontrol |
| Ekonomi ve XP | Referans testleri: resmi yama farkları (18.2 XP) + örnek tur geçişleri | Resmi değerlerle %100 uyum. Her parametrenin durumu raporda; `unverified` sayısı izlenir |
| Shop olasılıkları | R3 tablosu ↔ resmi geçmiş ↔ tooltip | Her seviyenin satırı 100'e toplanır; seviye 7 tooltip ile `verified` olur; damian-kim hesaplayıcısıyla 5 senaryoda olasılık karşılaştırması (±0,5 puan) |
| Havuz | Korunum özellik testleri (mevcut) + değerin kaynağı | Değer oyun dosyası veya oyunla doğrulanana kadar `third_party_unverified` |
| Modifier sistemi | Birim testleri + özellik testleri | "XP 3 altın" augment'iyle `buy_xp`, level maliyeti ve P1 adayları birlikte değişir. Augment yokken P1 çıktısı bit bit aynı. Sıra testi geçer |
| Augment modelleri | Her `modelled` augment için en az bir test (metindeki sayı ↔ `raw_effects` ↔ modifier) | Kapsam raporu: modelled / partial / text_only sayıları. Ekonomi, XP ve shop augment'lerinin ≥ %90'ı modelled |
| Yama katmanı | 18.4 ve 18.5 yan yana yüklenir; diff testi | Eski yamanın değerleri değişmez (regresyon fikstürü); diff, notlardaki değişiklikleri yakalar |
| Komp şablonları | Şema testleri: her birim, trait ve item id'si o yamada var; trait hedefi birimlerle sağlanabiliyor | %100 referans bütünlüğü; her şablonda kaynak ve tarih |

**Oyun içi kontrol listesi** (`templates/oyun_ici_kontrol.md`, senin için tek maçlık):
- Seviye 7 tooltip
- Reroll ve XP maliyeti
- Seri altını
- 2 yıldızlı birimin satış değeri
- Sahne hasarı
- 5 trait eşiği
- 5 tarif

---

## 8. Aşamalı yol haritası

Boyutlar: S küçük, M orta, L büyük. Her aşamada teknik kabul + hedefe katkı var. Ortak şart: pytest, ruff ve P1 regresyonu geçer.

| Aşama | Kapsam | Bağımlılık | Kabul kriteri | Hedefe katkı |
|---|---|---|---|---|
| **B0 · S** Belgeler | Bu planı `docs/PLAN.md` v0.5 yap; `CLAUDE.md` ve `DURUM.md` güncelle; `docs/KAYNAKLAR.md` (bölüm 2) | — | Senin onayın | Tek ve güncel yön |
| **B1 · M** Kaynak kaydı + CommunityDragon importer | `sources.json`, snapshot manifest, `generated/18.4/` (şampiyon, trait, item, augment, Wisp), hash çözücü, şema doğrulayıcı, `data diff` | B0 | Bölüm 7'deki şampiyon, trait ve item satırları; aynı snapshot'tan iki kez üretim bit bit aynı | Motor ilk kez şampiyon, trait ve item'ları tanıyor |
| **B2 · S** Ekonomi ve shop'u tamamlama | 18.2–18.4 yama kayıtları; seviye 7 için oyun dosyası kaynağı; satış, sahne hasarı ve seri değerleri (çelişki kayıtlı); oyun içi kontrol listesi | B0 | Ekonomi ve shop satırları (bölüm 7) | P1'in kesin kısmı Set 18 ile uyumlu ve kaynaklı |
| **B3 · M** Modifier ve olay sistemi | `effects.py` yerine modifier katmanı; `Rules.effective()`; Wisp, Inferno, Riftbeast ve Blossom shop varyantları; ekonomi, XP ve shop augment'lerinin modellenmesi | B1, B2 | Modifier satırları (bölüm 7); P1 regresyonu aynı | Augment etkisi tüm kararlara tutarlı yansıyor |
| **B4 · M** Item ve trait yapısı | Tarif grafı, item istatistik modifier'ları, trait eşik değerleri, rol etiketleri, yetenek sayılarının araştırması (ham bin), item–şampiyon uyumu (kural tabanlı ve açıklanabilir) | B1 | Item ve trait satırları; yetenek değerleri bulunduysa kaynaklı, bulunamadıysa `unknown` raporlu | Komp ve item soruları yapılandırılmış veriyle cevaplanıyor |
| **B5 · M** Komp şablonları ve meta | 18.5'in ilk 10–15 kompu elle (tactics.tools, tftacademy, op.gg) şablona; meta kayıtları ayrı; pivot grafı; augment önerileri tip ve güven sınıfıyla | B1, B4 | Referans bütünlüğü %100; her kompta kaynak ve tarih; senin gözden geçirmen | "Bu durumda hangi kompular mantıklı" sorusunun veri tabanı |
| **B6 · S** Savaş ve dizilim arayüzü | Hex koordinatları (7×4 yarı tahta), `UnitCombatProfile`, `AbilityProfile` (hedefleme, alan, hasar tipi), `Board`, `CombatEvaluator` protokolü (ilk sürüm "hesaplanamaz" döner) | B1, B4 | Şema testleri; R2 verisinden 65 profil üretimi | İleride dövüş ve dizilim motoru takılabilir |
| **B7 · S** Yama döngüsü + Set 19 provası | 18.5 snapshot'ı ve diff raporu; Set 19 PBE importer denemesi | B1–B5 | 18.5 diff raporu yama notuyla karşılaştırılmış; Set 19 PBE yüklenebiliyor veya eksikler listelenmiş | Setler arası taşınabilirlik kanıtlanır |

**Sıra:** B0 → (B1 ∥ B2) → B3 → B4 → B5 → B6 → B7. 18.5 yarın çıktığı için B1, 16.20 (18.4) ile kurulur ve hemen 18.5 ile tekrarlanır.

---

## 9. MVP sınırı

**MVP'de** (tek yama, 18.5): B0–B5.
- Kaynaklı şampiyon, trait, item ve augment verisi
- Tamamlanmış ekonomi ve shop
- Modifier sistemi ve modellenmiş ekonomi, XP ve shop augment'leri
- 10–15 elle girilmiş komp şablonu ve ayrı meta kayıtları
- Diff aracı

**Bilinçli olarak ertelenenler:**
- Dövüş simülatörü ve dizilim değerlendirmesi (B6 sadece arayüz)
- Savaş augment'lerinin değeri
- Yetenek sayıları bulunamazsa onların modeli
- Riot API veri toplama (G0/M2)
- ML (tahta gücü, augment değeri)
- Maç kayıtları ve otomatik analiz
- Rakip modeli
- Canlı oyun içi kullanım (bölüm 0'daki politika notu)

---

## 10. ML ve diğer yöntemlerin rolü

| Problem | Yöntem | Gerekli veri ve etiket |
|---|---|---|
| Ekonomi, XP, tarif, eşik | Deterministik kural + veri | Kaynaklı parametreler |
| Shop ve roll | Kesin DP / Markov + Monte Carlo (mevcut) | Olasılık tablosu, havuz |
| Komp ve meta | İstatistik (güven aralığı, örnek sayısı) | Maç sonu tahtaları (Riot API, ileride) |
| Tahta gücü, item katkısı | ML (Plackett-Luce + GBDT), M4 | Yama etiketli on binlerce tahta; etiket = sıralama |
| Augment değeri | API'de augment yok → kural modeli + simülasyon; ML ancak kendi kayıtlarınla ve düşük güvenle | Augment teklifi ve seçim kayıtları |
| Karar karşılaştırma | Simülasyon + arama (M6/M7) | Kalibre simülatör |

---

## Uygulama sırasında değişecek dosyalar

- **Yeni:**
  - `docs/KAYNAKLAR.md`
  - `data/sources.json`
  - `data/sets/set18/{generated,curated}/`
  - `tools/import_cdragon.py`
  - `src/tft_engine/gamedata/entities.py`
  - `src/tft_engine/gamedata/hashes.py`
  - `src/tft_engine/rules/modifiers.py`
  - `src/tft_engine/combat/` (sadece arayüz)
  - `templates/oyun_ici_kontrol.md`
- **Değişecek:**
  - `docs/PLAN.md`, `docs/DURUM.md`, `CLAUDE.md`
  - `gamedata/loader.py`: varlık gruplarını ve yama kayıtlarını yükleyecek
  - `rules/economy.py`: `effective()` kullanacak
  - `prob/shop_model.py`: varyantlar eklenecek
  - `decision/effects.py`: modifier'lara geçecek
  - `data/sets/set18/patches/18.2–18.4.json`
- **Ağ erişimi:** Sadece `tools/` içindeki importer'da olur. Çekirdek katmanlar ağsız kalır.

## Doğrulama (uçtan uca)

- `.\.venv\Scripts\python.exe -m pytest`, `ruff check .`, `ruff format --check .`
- `tft-engine data diff 18.4 18.5` raporu yama notlarıyla elle karşılaştırılır.
- P1 senaryoları (`tft-engine decide scenarios/p1/*.json`) her aşamada aynı sonucu verir; değişirse gerekçesi yazılır.
- Oyun içi kontrol listesi bir maçta doldurulur ve `verifications.jsonl` dosyasına işlenir.
