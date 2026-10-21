# Proje durumu

Son güncelleme: 2026-10-21. Plan: [PLAN.md](PLAN.md) (v0.5, bilgi altyapısı; kararlar en üstte). Kaynaklar: [KAYNAKLAR.md](KAYNAKLAR.md). Veri erişim ve izin raporu: [VERI_KAYNAKLARI.md](VERI_KAYNAKLARI.md). Önceki plan: [PLAN_v0.4.md](PLAN_v0.4.md).

## Neredeyiz

| Aşama | Durum |
|---|---|
| M0: proje iskeleti | Bitti |
| M1a: mekanik çekirdek (ekonomi, shop olasılıkları, yama katmanı) | Bitti |
| P1: ilk karar prototipi | İlk sürüm bitti ([P1_SONUC.md](P1_SONUC.md)). Artık regresyon testi olarak kullanılıyor |
| **B0: plan v0.5 ve belgeler** | **Bitti (2026-10-20)** |
| **B1: kaynak kaydı + CommunityDragon importer** | **Bitti (2026-10-20)**, 18.4 için. Ayrıntı aşağıda |
| **B2: ekonomi ve shop'u tamamlama** | **Bitti (2026-10-20).** Ayrıntı aşağıda |
| **B3: modifier ve olay sistemi** | **Bitti (2026-10-21).** Ayrıntı aşağıda |
| **B4: item ve trait yapısı** | **Bitti (2026-10-21).** Ayrıntı aşağıda; roller senden bekleniyor |
| **B5: komp şablonları ve meta** | **Altyapı bitti (2026-10-21)**, 18.4 test verisiyle. 18.5 kompları ve istatistikleri veri oturunca (2–3 gün) girilecek |
| B6: savaş ve dizilim arayüzü | Sıradaki |
| B7: yama döngüsü + Set 19 provası | Başlamadı |
| Ertelenenler: G0/M2 (Riot API), M4+ (ML), maç kayıtları, canlı kullanım | PLAN bölüm 9 |

## B1 sonucu (18.4, CommunityDragon 16.20)

- **65 şampiyon** (14/13/14/14/10) + Lux'un 9 formu. Sayılar `champions_per_cost` parametresiyle ve tactics.tools listesiyle aynı.
- **36 trait:** Eşikler ve değerler var. Değer adlarının hash'leri açıklamadaki adlarla çözüldü; sadece Elderwood'da 2 değer adı çözülemedi.
- **427 item:**
  - Tür dağılımı: 20 bileşen, 78 tamamlanmış, 80 artifact, 72 radiant, 21 amblem, 16 destek, 58 tüketilebilir, 82 diğer.
  - Tarif kontrolü temiz.
  - Bileşenlerden 10'u Set 18'in `DA_` ailesinden, 10'u eski `TFT_` ailesinden.
- **592 augment kaydı** (407 farklı ad, varyantlarla). Tier bilgisi oyun dosyasında hash'li, şimdilik `unknown`. Hangi augment'lerin bu yamada gerçekten teklif edildiği doğrulanmadı.
- **349 Wisp kaydı** (165 farklı ad, yükseltilmiş sürümleriyle). Oyun dosyasında "Charm" adıyla geçiyorlar.
- **Eksik:** 74 şampiyon kaydının 72'sinde yetenek sayıları yok. B4'te araştırılacak.
- **16.20 = 18.4 eşlemesi doğrulanmadı.** Kanıt: 16.20 klasörü 7 Ekim'de, 18.4 notlarından bir gün sonra oluşturulmuş.
## B2 sonucu

- **Shop olasılıkları ve havuz boyutları oyun dosyasından** (map22.bin.json, 16.20): kopya sayısı 30/25/18/10/9, havuzda 14/13/14/14/10 şampiyon (Lux tek kayıt). Durum `community_extracted`. **Seviye 7 oyun içi tooltip'ten: 16/30/43/10/1** (sahibin ekran görüntüsü, 18.4b). Oyun dosyası ve 17.1 notu 19/30/40/10/1 diyor; bu değer çelişki kaydı olarak duruyor.
- **Oyunda doğrulananlar (2026-10-20, 18.4b):** reroll 2 altın, XP alımı 4 altın = 4 XP, tur başına 2 XP (`verified`). Seviye 8/9 olasılıkları ve XP 56/68/68 oyunda da aynı. Faiz 10 altın başına 1 (`verified`). PvP galibiyeti +1 (sahibin gözlemi). **Seri altını:** adım adım okunan bir turda 6 galibiyet serisi +3 verdi (14 → galibiyet 15 → satışla 20 → tur başı 30 = 5 + 2 faiz + 3 seri). 2'lik seri de +1 veriyor (0 altın, 2. galibiyet: toplam +7 = 1 galibiyet + 5 temel + 1 seri). Kayıp serisi galibiyet serisiyle aynı ödüyor. Tablo: 2-4: +1, 5: +2, 6+: +3 (op.gg, tft.ninja; wiki'nin 3'ten başlayan tablosu çelişki kaydı). Seri kesilince bonus sıfırlanıyor (6 seriden sonra kayıp, 30 altın: +8).
- **Yama kayıtları:** 18.2 (XP 7→8 60→56, 8→9 ve 9→10 68→64), 18.2b (14 Eylül, 8→9 ve 9→10 tekrar 68), 18.3 ve 18.4 (temel ekonomi değişikliği yok). Hepsi resmi notlardan okundu, `reviewed`.
- **Düzeltme:** `base.json` 18.1 itibarıyla 18.2'nin XP değerini içeriyordu; 18.1 değeri (60) geri kondu, değişiklik yama kaydına taşındı.
- **Yeni parametreler:** `sell_value` (satış değeri tablosu) ve `player_damage` (aşama hasarı + hayatta kalan birim başına 1). İkisi de üçüncü taraf, çelişkiler notta.
- **Yeni kurallar:** `Rules.sell_value`, `Rules.sell_unit`, `Rules.player_damage`.
- **Her parametre kaynak kaydına bağlı** (`source_ids`). Çelişkiler `conflicts` alanında. `data check` kaynakları ve "eski değer" durumunu da denetliyor.
- **Data Dragon (Riot resmi):** 74 Set 18 kaydının hepsi ad ve maliyet olarak aynı.
- **Oyun içi kontrol formu:** [templates/oyun_ici_kontrol.md](../templates/oyun_ici_kontrol.md).
- P1 senaryolarının tercihleri değişmedi.
- Bulunamayanlar: TFT XP tablosu, reroll ve XP maliyeti oyun dosyasında yok (oyun içi kontrol). Kötü şans koruması için alan bulunamadı ama bazı alanlar hash'li, yani yokluğu kanıtlanmadı.

## Elle katman (2026-10-20, B2'ye ek)

- **Item istatistikleri:** 103 item (36 temel, 36 Radiant, 31 Artifact) `curated/item_stats/18.4.json` içinde.
  - Kaynak: tactics.tools, elle aktarım. Sayfa 18.2 durumunda; 18.3 ve 18.4 değişiklikleri resmi notlardan işlendi.
  - 84 item eski oyun dosyası kopyasıyla birebir aynı. 17 farkı inceleme sayfası gösteriyor.
  - Sahibin 36 temel item görüntüsü (2026-10-20) bir istatistik sitesinden. 17'si aynı. 19'unda site bazı istatistikleri göstermiyor (Damage Amp hiç yok, bazılarında can yok, 9'unda istatistik satırı yok); eski oyun dosyası kopyaları sayfa değerlerini tutuyor, görüntü değerleri çelişki kaydı. Aynı sebeple 3 Radiant düzeltmesi geri alındı (sayfa değerleri geçerli, görüntü çelişki kaydı).
  - MetaTFT (18.4 durumunda: Crownguard 20 AP, Spirit Visage %10) bu 19 item ve Crownguard'ın tüm istatistiklerinde sayfa değerleriyle aynı; kaynak olarak eklendi. Tek fark: Adaptive Helm tank/dövüşçü bonusu MetaTFT'de 80 (eski oyun dosyası kopyasında Radiant değeri), bizde 30; çelişki kaydı. 18.2 notu Radiant Bloodthirster AD/AP %40 diyor, sayfa değeri doğru.
- **Augment tier'ları:** 245 ad `curated/augment_tiers/18.4.json` içinde (Chosen of the Sun 18.4'te Silver'a indi). "Nesting Dolls" oyun dosyasında yok.
- **Resmi not düzeltmeleri:** `curated/overrides/18.4.json` içinde 33 augment ve Wisp değeri, 3 şampiyon değeri (18.4b: Varus mana, Mama Beak AD) ve 2026-10-20'de 18.2/18.3/18.4 notlarıyla şampiyon ve trait taramasından çıkan 9 değer (Hecarim başlangıç manası 50, Varus AS 0,75, Lunar AP 7/12/16/20, Sprykin (7) %55, Juggernaut (4) %30, Hunter (4) %40). Trait eşikleri liste sırasıyla adreslenir (`breakpoints.1.values.X`). Elderwood'un çözülemeyen iki değeri (0,25 ve 0,1) her eşikte aynı ve açıklamada görünmüyor; oyunun iç değerleri. Oyun dosyası 18.4 sayı değişikliklerini içermiyordu. Alanı dosyada olmayan değişiklikler (Wisp maliyetleri, Trait Ladder ödülleri vb.) "pending" listesinde.
- `load_knowledge` bu üç katmanı otomatik uyguluyor. Düzeltmenin beklediği eski değer dosyada yoksa yükleme hata veriyor.

## B3 sonucu (2026-10-21)

- **Modifier ve olay katmanı** (`rules/modifiers.py`): kural değiştiren `Modifier` (set/add/mul/min/max, sıra belirlenimli) ve tetikleyiciye bağlı `Event` (now, round_start, after_combat_win/loss, stage_start, level_up, buy_xp, wisp_bought). `Rules` her parametreyi modifier'larla okur, hangi augment'in neyi değiştirdiğini kaydeder ve olayları `end_round`, `buy_xp`, `gain_xp` içinde ateşler.
- **Tek doğruluk kaynağı düzeltmeleri:** Roll hesabı reroll fiyatını `Rules` üzerinden okuyor. 3 turluk ileri bakışın hasarı `player_damage` kuralından geliyor; ayrı `damage_by_stage` tablosu kalktı, sadece hayatta kalan rakip birim sayısı varsayım. `GameState` bedava reroll, sahip olunan augment'ler ve olay sayaçlarını taşıyor; `RollQuery.free_rolls` ile bedava reroll'lar roll hesabında önce kullanılıyor.
- **Shop modeli:** Slot sayısı artık bir dağılım (`slot_probs`). Wisp: shop'ta Wisp çıkma olasılığı varsayım (`wisp_shop_prob`, set verisinden 0,5; 5 Blossom'da 1). Roll adayları iki şekilde hesaplanıyor: Wisp almadan ve "önce Wisp al" (`wisp_price`, varsayılan 1 altın; o turun bütün shop'ları 5 şampiyon). Lux formu: elinde Lux yoksa istediğin formun payı 1/9, başka form elindeyse 0, aynı form elindeyse 1. Inferno ve Riftbeast savaştan sonraki ilk shop'u değiştiriyor; roll hesabı o shop'u zaten ekranda saydığı için modele not olarak yazıldı.
- **Augment modelleri** (`curated/effects/augments.json`): 64 ekonomi/XP/shop augment'i; 27 tam, 32 kısmi (eksik kısım yazılı: birim, item, bileşen, savaş etkisi ya da motorun göremediği koşullar), 5 sadece metin. Sayılar augment kaydındaki değerlere referans; not düzeltmeleri (ör. Level Up! 10 XP) otomatik geliyor. Kapsam: `tft-engine data augments --set set18 --patch 18.4 --list`.
- **Senaryolarda:** Augment teklifi gerçek id ile verilebiliyor (`{"augment": "DA_LevelUp"}`). Sahip olunan augment'ler `state.augments`, bedava reroll'lar `state.free_rerolls`, aktif trait'ler `active_traits` alanında. Yeni senaryolar: `b3_real_augments_3_2`, `b3_wisp_first_three_star`.
- **P1'e etkisi:** Kararların harfi hiçbir senaryoda değişmedi. Yeni Wisp modeli yüzünden o1 ve o5'te en iyi seçenek artık "önce Wisp al, sonra roll at"; n3'te roll seçeneği 3. sıradan 2. sıraya çıktı (hedefe ulaşma %37,8 → %44,0). Hasar düzeltmesi puanları değiştirmedi (aşama 2–6 hasarları aynı kaldı).

## B4 sonucu (2026-10-21)

- **Tarif tablosu** (`rules/items.py`): 10 bileşenin 55 çifti, her biri tek bir item veya amblem. "Bu bileşenlerle ne yapılır", "bütün bileşenleri hangi item'lara çevirebilirim", "bu item için ne eksik" sorguları. 21 amblemin trait'i adından eşleşiyor (Ravager Emblem → Ravager, `DA_18_Slayer`).
- **Aktif trait hesabı** (`rules/traits.py`): Aynı şampiyon tek sayılır; Avatar (Lux) trait'ini iki kez sayar (trait metni); amblem, trait'i zaten olan şampiyonda bir şey eklemez (veride `emblem_on_same_trait_counts`, doğrulanmadı). Eşik değerleri yama düzeltmeleriyle (ör. Lunar 18.4). Senaryodaki birimler gerçek şampiyonsa aktif trait'ler artık tahtadan hesaplanıyor (ör. 5 Blossom → her shop'ta Wisp).
- **Item istatistik toplamı:** Item'ların bonusları toplanır, en zayıf kaynak durumu gösterilir. Savaş hesabı yok, yüzdeler yüzde olarak kalır.
- **Item uyumu** (`decision/item_fit.py`, varsayım): Şampiyon profili yetenek metnindeki AD/AP ikonundan ve menzilden çıkar (ön/arka sıra); rol tank ise tank profili. Ağırlıklar `assumptions.item_fit_weights`. Kural tahmini; oyuncu istatistiği değil.
- **Komutlar:** `tft-engine items --have "B.F. Sword,Recurve Bow"`, `tft-engine traits --board "Ahri,Sett" --emblem "Ornn:Blossom Emblem"`, `tft-engine items-for Ahri`.
- **Eksikler:** Roller (`curated/champion_roles.json` boş, senden bekleniyor). Yetenek sayıları oyun dosyalarında yok (KAYNAKLAR bölüm 2), `unknown`.
- P1 senaryoları değişmedi.

## B5 sonucu (2026-10-21, altyapı)

- **Komp şablonları** (`curated/comps/<yama>.json`): birimler (carry / tank / core / flex), oyun tarzı (reroll_5/6/7, fast8, fast9, standard), carry item üçlüleri, pivotlar, kaynak ve son gözden geçirme tarihi.
- **Meta istatistikleri** (`curated/meta/<yama>/<site>.json`): komptan ayrı. Her dosyada site, yama, rank filtresi, toplama tarihi ve her sayının tanımı zorunlu. Komp başına ortalama sıra / ilk 4 / birincilik; birim başına item üçlüleri.
- **Komp eşleştirme** (`decision/comp_match.py`, varsayım): Elindeki birimler (maliyetle ağırlıklı) ve bileşenlerin carry item'larına uyumu. Site istatistikleri puana karışmaz, yanında gösterilir.
- **Item üçlüsü:** Önce bilinen üçlüler (şablon, site), eksik bileşenleri sayarak; yoksa kural tabanlı uyumdan en iyi üçlü.
- **Komutlar:** `tft-engine comps --units "Krug,Pebbles" --have "Recurve Bow"`, `tft-engine trio Pebbles --have "..." --items "..."`. `data check` şablon ve meta referanslarını da denetliyor.
- **18.4 test verisi:** tactics.tools'tan 3 komp (18.4b, Diamond+; sayfa varsayılanı, senin kuralın Master+). Sayfa item'ları birimlere bağlamıyor; birim kartlarındaki 3 item kaydedildi, etiketsiz sayılar alınmadı.
- **Bekleyen:** 18.5 kompları ve gerçek üçlü istatistikleri (MetaTFT, Master+), veri oturunca.

## Araştırmanın önemli sonuçları (ayrıntı: KAYNAKLAR.md)

- **Seviye 7 shop olasılığı:** Oyun içi tooltip 16/30/43/10/1 gösteriyor, repo bunu kullanıyor. Oyun dosyası (map22) ve resmi 17.1 notu 19/30/40/10/1 diyor; çelişki kaydı. Gerçek roll'ların hangisine uyduğu ancak çok sayıda shop sayılarak kanıtlanabilir.
- **XP tablosu:** 2/2/6/10/20/36/56/68/68 resmi 18.2 notlarıyla tutarlı. 8→9 ve 9→10'un ikisinin de 68 olması doğru (ara yamada geri alındı).
- **CommunityDragon:** Şampiyon, trait, item, augment ve Wisp verisini sağlıyor. Ama Set 18 yetenek sayıları boş; trait değişken adları ve augment tier'ları hash'li.
- **Riot API'de augment yok** (2024 sonundan beri).
- Riot'un TFT politikası maç sırasında anlık duruma göre öneriyi onaylamıyor (alıntılar KAYNAKLAR 1.4'te).

## Senden beklenenler

1. **Şampiyon rolleri:** 65 Set 18 şampiyonunun rolü (Tank, Dövüşçü, Nişancı, Büyücü, Suikastçı ...). MetaTFT birim listesinden ekran görüntüsü yeterli.
2. **Tek maçlık oyun içi kontrol:** [templates/oyun_ici_kontrol.md](../templates/oyun_ici_kontrol.md) formunu doldur.
2. **Veri incelemesi:** İnceleme sayfasında (Set 18 Veri İncelemesi, claude.ai artifact) yanlış gördüğün augment, item, Wisp, şampiyon veya trait'i işaretle ve not bırak. Notları okuyup kaynaklı düzeltme olarak işlerim.
3. **B5'te komp şablonlarını gözden geçirme:** Sitelerden girilen 10–15 kompun senin bilginle uyuşup uyuşmadığına bakman gerekecek.
4. Etiketli senaryolar ve maç kayıtları şimdilik beklemede.
5. Riot API kişisel anahtarı: MVP'den sonra (G0′).

## Bilinen açıklar

- Set 18 verilerinin çoğu üçüncü taraf kaynaktan ve doğrulanmadı. Yeni durum tablosu KAYNAKLAR.md bölüm 3'te.
- P1 belirsiz durumlarda altını korumaya yatkın. Satış kuralı artık veride ve `Rules` içinde var, ama P1'in değerlendirmesi henüz kısmi ilerlemeyi ve satış değerini kullanmıyor ([P1_SONUC.md](P1_SONUC.md)).
- 18.5 notları 21 Ekim'de çıkacak. Gelince yeni CommunityDragon sürümü indirilip `data diff` ile karşılaştırılacak ve `patches/18.5.json` doldurulacak.
