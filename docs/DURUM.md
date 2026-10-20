# Proje durumu

Son güncelleme: 2026-10-20. Plan: [PLAN.md](PLAN.md) (v0.5, bilgi altyapısı; kararlar en üstte). Kaynaklar: [KAYNAKLAR.md](KAYNAKLAR.md). Veri erişim ve izin raporu: [VERI_KAYNAKLARI.md](VERI_KAYNAKLARI.md). Önceki plan: [PLAN_v0.4.md](PLAN_v0.4.md).

## Neredeyiz

| Aşama | Durum |
|---|---|
| M0: proje iskeleti | Bitti |
| M1a: mekanik çekirdek (ekonomi, shop olasılıkları, yama katmanı) | Bitti |
| P1: ilk karar prototipi | İlk sürüm bitti ([P1_SONUC.md](P1_SONUC.md)). Artık regresyon testi olarak kullanılıyor |
| **B0: plan v0.5 ve belgeler** | **Bitti (2026-10-20)** |
| **B1: kaynak kaydı + CommunityDragon importer** | **Bitti (2026-10-20)**, 18.4 için. Ayrıntı aşağıda |
| B2: ekonomi ve shop'u tamamlama (18.2–18.4 kayıtları) | Sıradaki (B1 ile paralel) |
| B3: modifier ve olay sistemi | Başlamadı |
| B4: item ve trait yapısı | Başlamadı |
| B5: komp şablonları ve meta | Başlamadı |
| B6: savaş ve dizilim arayüzü | Başlamadı |
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
- B2'ye kalanlar: bilinen eski değer uyarısı (yama kayıtlarında eski değerler gerekiyor), Data Dragon ile ad ve maliyet çapraz kontrolü.

## Araştırmanın önemli sonuçları (ayrıntı: KAYNAKLAR.md)

- **Seviye 7 shop olasılığı:** Oyun dosyası 19/30/40/10/1 diyor, repodaki değerle aynı. 16/30/43 veren siteler 17.1 öncesi eski tabloyu kopyalıyor.
- **XP tablosu:** 2/2/6/10/20/36/56/68/68 resmi 18.2 notlarıyla tutarlı. 8→9 ve 9→10'un ikisinin de 68 olması doğru (ara yamada geri alındı).
- **CommunityDragon:** Şampiyon, trait, item, augment ve Wisp verisini sağlıyor. Ama Set 18 yetenek sayıları boş; trait değişken adları ve augment tier'ları hash'li.
- **Riot API'de augment yok** (2024 sonundan beri).
- Riot'un TFT politikası maç sırasında anlık duruma göre öneriyi onaylamıyor (alıntılar KAYNAKLAR 1.4'te).

## Senden beklenenler

1. **Tek maçlık oyun içi kontrol:**
   - Seviye 7 tooltip
   - Reroll maliyeti ve XP alım maliyeti
   - Seri altını
   - 2 yıldızlı birimin satış değeri
   - Sahne hasarı
   - Birkaç trait eşiği ve tarif

   Liste B2'de `templates/oyun_ici_kontrol.md` olarak hazırlanacak.
2. **B5'te komp şablonlarını gözden geçirme:** Sitelerden girilen 10–15 kompun senin bilginle uyuşup uyuşmadığına bakman gerekecek.
3. Etiketli senaryolar ve maç kayıtları şimdilik beklemede.
4. Riot API kişisel anahtarı: MVP'den sonra (G0′).

## Bilinen açıklar

- Set 18 verilerinin çoğu üçüncü taraf kaynaktan ve doğrulanmadı. Yeni durum tablosu KAYNAKLAR.md bölüm 3'te.
- P1 belirsiz durumlarda altını korumaya yatkın; satış kuralı ve kısmi alım eksik ([P1_SONUC.md](P1_SONUC.md)).
- 18.2, 18.3 ve 18.4 yama dosyaları boş (`not_reviewed`). Değişiklikler B2'de işlenecek.
- 18.5 notları 21 Ekim'de çıkacak.
