# TFT Engine: Karar Motoru Odaklı Yol Haritası (v0.4.2)

Tarih: 2026-10-18 · Durum: **Onaylandı** (v0.4). M0, M1a ve P1'in ilk sürümü tamamlandı. v0.4.1: yayın ve VOD notları eklendi (bölüm 6.5). v0.4.2: her analiz yama bazlı (bölüm 8.6)
Önceki sürümler: [PLAN_v0.3.md](PLAN_v0.3.md), [PLAN_v0.2.md](PLAN_v0.2.md), [PLAN_v0.1.md](PLAN_v0.1.md) (değiştirilmeden saklandı)
İlgili rapor: [ACIK_KAYNAK_INCELEME.md](ACIK_KAYNAK_INCELEME.md)

**v0.4'te ne değişti:**

- **Proje artık bir veri ve simülasyon projesi değil, erken aşamada çalışan bir karar motoru projesi.** İlk karar prototipi (P1), M1'in en küçük parçasından hemen sonra geliyor. Bundan sonraki her milestone o prototipin bir parçasını gerçek veriyle değiştiriyor.
- **Item ve augment sona bırakılmadı.** P1'de ortak bir "etki" arayüzü ve ekonomi tipi augment'ler var. Item katkısı M4'te gerçek veriyle ölçülüyor. Augment'ler beş tipe ayrıldı ve her tipin güven seviyesi ayrı (bölüm 9).
- **Rakip modeli ikiye ayrıldı:** veriden gelen rakip önseli (`OpponentPrior`) ve kayıtlarında gözlenen rakip durumu (`ObservedOpponentState`). İkisi asla tek bir kesin bilgi gibi birleştirilmiyor (bölüm 8.3).
- **M2'den önce bir veri ve politika kapısı (G0) var.** Rate limit kapasitesi veri toplama izni olarak kabul edilmiyor.
- **Simülatörün güvenilirlik haritası:** M6, karar tipi başına "güvenilir / şartlı / güvenilmez" haritası üretmeden kabul edilmiyor.
- **Her milestone'da iki kabul kriteri var:** teknik kabul ve hedefe katkı.
- **Kayıtların ikiye bölündü:** geliştirme kümesi ve bağımsız test kümesi (bölüm 6.4).

Etiketler:

- **[DOĞRULANDI]**: Bu oturumda bir kaynakta okundu, link verildi.
- **[KAYNAK GEREKLİ]**: Koda girmeden önce doğrulanacak.
- **[VARSAYIM]**: Bilinçli seçilmiş, değiştirilebilir varsayım.
- **[HESAP]**: Verilmiş rakamlardan türetilmiş tahmin; ölçülerek düzeltilecek.
- **[HEDEF]**: Kabul kriteri için başlangıç eşiği. İlk baseline ölçüldükten sonra seninle kesinleşecek.

---

## 1. Kısa özet

1. **İlk çalışan karar prototipine en kısa yol:** M0 (iskelet) → M1a (ekonomi kuralları, bağımsız shop modeli, kesin ulaşma olasılığı) → **P1** (elle girilen bir durumda roll, level, ekonomi ve pivot seçeneklerini karşılaştıran prototip). Bu yol API anahtarı, veri toplama veya ML gerektirmiyor.
2. **P1 kazanma olasılığı vermez.** Sadece mekanikten gelen kesin sonuçları (ulaşma olasılığı, harcanan altın, kalan ekonomi) ve açıkça etiketlenmiş varsayımlardan gelen tahminleri (tahta gücü, HP kaybı) verir. En değerli çıktısı bir hassasiyet raporu: "bu karar hangi varsayım değişince tersine dönüyor". Bu rapor, hangi modele önce yatırım yapmamız gerektiğini söyler.
3. **Item'lar augment'lerden çok daha iyi durumda.** Item'lar Riot API'de var (`itemNames`), yani item taşıyıcının tahta gücüne katkısı gerçek veriyle ölçülebilir (M4). Augment'ler API'de yok. Augment'lerin sadece ekonomi ve kaynak veren türleri kesin mekanikle değerlendirilebilir. Savaş augment'leri en düşük güvenle kalır.
4. Veri kaynakları, Set 18/19 planı, kayıtların kullanımı ve açık kaynak bulguları v0.3'teki gibi geçerli (bölüm 4-7). Sadece eleştirinin haklı olduğu yerlerde güncellendi.

---

## 2. Dış eleştirinin değerlendirmesi

Eleştiriyi tek tek inceledim. Çoğunda haklı. Birkaç noktada ise ya v0.3 bunu zaten yapıyordu ya da önerinin bir tuzağı var.

### 2.1 Katıldığım noktalar (plana işlendi)

| Eleştiri | Değerlendirmem | Plandaki karşılığı |
|---|---|---|
| Karar motoru (M7) çok geç geliyor; önce altyapı büyüyor | **Tamamen haklı.** v0.3'ün en büyük zaafı buydu. Karar motorunun işe yarayıp yaramadığını aylarca göremezdik. Yazılımda buna "yürüyen iskelet" denir: önce uçtan uca ince bir sürüm kurulur, sonra her parça kalınlaştırılır | P1 ve P2 (bölüm 11) |
| Rakip önseli ile gözlenen rakip durumu ayrılmalı | **Haklı ve önemli.** v0.3'te `PoolBelief` vardı, ama bilginin kaynağı ayrılmıyordu. Rakibin bir kompozisyonu bırakıp birimleri havuza geri vermesi maç sonu verisinden kurulamaz | `OpponentPrior` ve `ObservedOpponentState` (bölüm 8.3) |
| Veri toplamadan önce bir doğrulama kapısı olmalı | **Haklı.** v0.3'te politika kontrol listesi M2'nin içindeydi. Kapı olarak öne alınması daha doğru | G0 (bölüm 11) |
| Master+ ile başlamak bir varsayım olmalı ve senin liginde test edilmeli | **Haklı.** v0.3 bunu varsayım olarak işaretlemişti ama test etmiyordu | M4 hedefe katkı kriteri |
| M6 simülatörünün güvenilirlik sınırları ölçülmeli | **Haklı.** Sadece meta dağılımına uyum yetmez. Simülatör bazı karar tiplerinde güvenilir, bazılarında değil olabilir | Güvenilirlik haritası (M6) |
| Her aşamada hedefe katkıyı ölçen bir kriter olmalı | **Haklı.** v0.3'ün kriterleri çoğunlukla teknikti | Her milestone'da "hedefe katkı" satırı |
| M1'i düzeltmek için kullanılan kayıt, bağımsız başarı testi sayılmamalı | **Çok iyi bir nokta.** Bunu kaçırmıştım. Aynı veriyle hem ayar yapıp hem test edersek sonuç iyimser olur | Kayıtların geliştirme ve test kümelerine bölünmesi (bölüm 6.4) |
| On binlerce maç tek başına iyi bir karar motoru yapmaz | **Haklı.** Maç verisi tahta gücünü ve meta'yı öğretir; kararları öğretmez | Değişmedi, ama artık açıkça yazıyor |

### 2.2 Kısmen katıldığım veya itiraz ettiğim noktalar

| Eleştiri | İtirazım | Sonuç |
|---|---|---|
| "M1 çok ayrıntılı" | M1'deki ayrıntı ucuz ve değerli. Roll mu, level mı kararının ilk yarısı tamamen shop olasılığına bağlı. M1 olmadan P1'in karşılaştırması da tamamen varsayım olur. Ama P1'in **M1'in tamamını** beklemesi gerekmiyor | M1 ikiye bölündü: M1a (P1'e gereken en küçük kısım) ve M1b (Set 18'e özel kurallar, kötü şans koruması, kayıtlarla doğrulama). P1, M1a'dan hemen sonra geliyor |
| Erken prototip mimariyi doğrular | Doğru, ama bir tuzak var. Erken prototipin çıktıları, varsayımlar etiketlense bile zamanla "motorun cevabı" gibi algılanmaya başlar. Bu yüzden P1'in amacı karar vermek değil; mimariyi test etmek ve hangi varsayımın kararı değiştirdiğini ölçmek | P1'in kabul kriterleri hassasiyet raporu ve bariz senaryolar üzerine kurulu, "doğru karar" iddiası üzerine değil |
| "Kişisel anahtar kişisel projeler ve araştırma için" | Doğru, ama küçük bir düzeltme: Riot'un dokümanı "sadece geliştirici veya küçük, özel bir topluluk" diyor, "araştırma" kelimesi geçmiyor. Kişisel anahtarın kendisi de ürün kaydı ve Riot onayıyla veriliyor, yani izin mekanizması zaten bu kayıt. v0.3 de rate limit'i bir izin olarak sunmamıştı; ama bunu açık yazmak iyi | G0'da yazılı karar |
| Augment ve item'lar ilk prototipte olmalı | Arayüz olarak evet, ucuz ve doğru. Değerlendirme olarak ise ancak bir kısmı mümkün. Senin vurgun önemli: item ve augment'ler TFT'de gerçekten belirleyici. Ama önemli olmaları onları ölçebileceğimiz anlamına gelmiyor. Objektif durum bölüm 9'da | P1'de etki arayüzü + ekonomi ve kaynak augment'leri; M4'te item katkısı; P2'de trait/amblem augment'leri |
| Eleştirinin söylemediği şey | Erken prototipin "hedefe katkısını" nasıl ölçeceğimiz belirtilmemiş. Gerçek veri yokken bir karar motorunu test etmenin dürüst yolları sınırlı | Üç yöntem: (1) cevabı bariz olan senaryolarda doğru tarafı seçmesi, (2) senin uzman etiketlerinle uyum (geliştirme ve test kümesi ayrı), (3) hassasiyet ve bilgi değeri raporu |

---

## 3. Kapsam, uyum ve gerçekçilik

### 3.1 Kapsam (senin tanımınla aynı)

Çevrimdışı araştırma, maç sonrası analiz ve bağımsız simülasyon. Canlı oyunda rakip takibi yok, oyun sırasında dinamik öneri yok. `spectator-tft-v5` (aktif oyun) endpoint'i kullanılmayacak. Riot'un TFT politikası scouting'i, gerçek zamanlı değişen önerileri ve kararı dikte eden uygulamaları onaylamıyor. Legend ve Legend tabanlı augment'ler için kazanma oranı gösterilemiyor ([TFT politikası](https://support-developer.riotgames.com/hc/en-us/articles/22698732381587-Teamfight-Tactics)) [DOĞRULANDI]. Genel politika kayıtlı ürün şartı koyuyor; haksız avantajı, oyuncu anonimliğini kaldırmayı ve MMR/ELO hesaplayıcı gibi ranked alternatiflerini yasaklıyor ([genel politika](https://developer.riotgames.com/policies/general)) [DOĞRULANDI].

**P1 ile gelen yeni bir risk:** P1, elle girilen bir oyun durumunu analiz ediyor. Bu, maç sırasında kullanılırsa tam olarak politikanın yasakladığı "gerçek zamanlı öneri" olur. Bu yüzden P1 ve sonraki sürümler, maç sonrası ve araştırma senaryoları için tasarlanacak. Hızlı "şu anki tahtamı gir" iş akışı optimize edilmeyecek [VARSAYIM: senin de kullanım niyetin bu].

### 3.2 Hedeflerin gerçekçilik tablosu

| Hedef | Durum | Gerekçe ve alternatif |
|---|---|---|
| Rakip kompozisyonları, ortak havuz, rekabet etkisi | **Gerçekçi** | 8 oyuncunun son tahtası veride var; havuz etkisi M1 ile kesin hesaplanır |
| Kalmak / pivot / alternatif kompozisyon | **Kısmen** | Kompozisyon gücü veriden ölçülür; geçiş maliyeti olasılık motoru ve simülasyonla hesaplanır, gerçek veriyle doğrudan doğrulanamaz |
| Ekonomi, level, roll, satın alma fırsat maliyetleri | **Kısmen** | Mekanik kesin (M1); sıralamaya etkisi sadece simülasyonda ölçülür |
| **Item değerlendirmesi** | **Kısmen-gerçekçi** | Son item'lar API'de var. Taşıyıcı ve item'ın tahta gücüne katkısı ölçülebilir. Bileşen yolu ve zamanlaması yok (bölüm 9.1) |
| **Augment değerlendirmesi** | **Tipe göre değişir** | Veriden öğrenmek mümkün değil (Set 13'ten beri API'de yok: [Mortdog, Kasım 2024](https://x.com/Mortdog/status/1856785428852216007); Mayıs 2026'ya kadar geri gelmedi: [Manifold](https://manifold.markets/Cy/tft-augment-stats-return-before-may)). Ekonomi ve kaynak augment'leri mekanikle hesaplanabilir; savaş augment'leri en düşük güvenle (bölüm 9.2) |
| Rakip strateji değişimlerini modellemek | **Kısmen** | Sadece son durum görünür. Alternatif: rakip önseli + kayıtlarındaki gözlemler + kalibre simülatör |
| Tahminleri gerçekle karşılaştırıp iyileşmek | **Tahta ve lobi seviyesinde gerçekçi, karar seviyesinde değil** | Karar değerleri karşı-olgusaldır |
| Tam motoru Set 18'de test etmek | **Gerçekçi değil** | Set 18 ~6 hafta içinde bitiyor. Ama P1 Set 18 mekaniğiyle çalışabilir (bölüm 4) |
| 10-20 maçla model eğitmek | **Gerçekçi değil** | Bölüm 6'daki istatistik hesabı |
| "En iyi algoritma" | **Önceden bilinemez** | Aday yöntemler aynı senaryolarda yarıştırılır (bölüm 10) |

---

## 4. Güncel set (Set 18) test planı ve takvim

### 4.1 Set 18 hakkında bildiklerimiz

- **Set 18: Enchanted Wilds**, 25 Ağustos 2026'da çıktı ([esports.gg](https://esports.gg/news/teamfight-tactics/tft-set-18-enchanted-wilds-release-date-champions-traits-and-more/)) [DOĞRULANDI].
- Yama takvimi: 18.4 canlıda (7 Ekim). 18.5 21 Ekim'de, 18.6 4 Kasım'da, 18.6B 11 Kasım'da çıkacak. **Set 19 1 Aralık'ta** başlıyor ([esports.gg yama takvimi](https://esports.gg/news/teamfight-tactics/tft-patch-schedule-2026/)) [DOĞRULANDI; tarihler değişebilir].
- **Shop'u doğrudan etkileyen Set 18 mekanikleri** (aynı kaynak) [DOĞRULANDI, ayrıntıları KAYNAK GEREKLİ]:
  - **Wisp'ler:** Her iki shop'tan birinin en sağ slotunda çıkıyor; tur başına bir tane alınabiliyor. Wisp'in bir şampiyon slotunun yerini alıp almadığı doğrulanmalı. Alıyorsa, bu shop'larda şampiyon olasılıkları değişir.
  - **Inferno trait'i:** Shop slotları "tutuşuyor" ve bir üst maliyet katmanından şampiyon geliyor.
  - **Riftbeast (5):** Birkaç dövüşte bir sonraki shop Riftbeast'lerle doluyor.
  - **Blossom:** (5)'te her shop'ta Wisp çıkıyor; (9)'da tur başına 2 Wisp alınabiliyor.

Bu, açık kaynak raporunun "sete özel shop kuralları için şemada yer aç" önerisinin Set 18'de **gerçekten gerekli** olduğunu gösteriyor. M1'in temel shop modeli bu kuralları tanımadan Set 18'de yanlış sonuç verir.

### 4.2 Fazlar (güncellendi)

| Faz | Zaman | Milestone'lar | Ne test edilir |
|---|---|---|---|
| **Faz A: Set 18** | Şimdi → 1 Aralık | G0, M0, M1a, **P1**, M1b, M2, M3 (deneme), kayıt protokolü | Karar prototipi Set 18 mekaniğiyle; ekonomi ve shop senin Set 18 oyunlarınla; veri hattı ve taksonomi Set 18 maçlarıyla |
| **Faz B: Set 19 geçişi** | 1 Aralık → | Set 19 `gamedata`, M1 yeniden doğrulama, M2-M3 tekrar, M4, **P2** | Yeni sete uyum süresi; P1'in varsayımsal tahta gücünün gerçek modelle değişmesi |
| **Faz C** | Set 19 içinde | M5, M6 | Rakip modeli; simülatörün güvenilirlik haritası |
| **Faz D** | Set 19 ortası → | M7, M8, M9 | Arama tabanlı karar motoru; derin item/augment; analiz arayüzü |

**Neden böyle:** P1 sete bağımlı model içermediği için Set 18'de anlamlı. Tahta gücü ve rakip modelleri ise Aralık'ta geçersiz olacağı için Set 19'da kuruluyor. M1-M3 ve P1 kodu set bağımsız yazılırsa, Set 18'de yapılan iş Set 19'a sadece veri dosyaları değişerek taşınır.

**Doğrulanmamış Set 18 kuralları:** Wisp, Inferno ve Riftbeast kuralları ayrıntıları doğrulanana kadar **kesin bilgi gibi uygulanmaz**. Her biri `status: unverified` ile ayrı bir senaryo varyantı olarak çalışır. Çıktıda "bu kural açıkken / kapalıyken" farkı gösterilir. Varsayılan, kuralın kapalı olması ve bir uyarı göstermek [VARSAYIM].

### 4.3 Set 18'de kabul edilecek "güncel set" kriterleri

- [ ] Set 18 (18.5 veya 18.6) `gamedata` dosyası; her alan kaynaklı.
- [ ] Kural motoru, senin kayıtlarından çıkarılan gerçek tur geçişlerinin (altın, faiz, seri, XP) ≥ %98'ini birebir doğru tahmin eder [HEDEF]. Uyuşmayan her geçiş incelenir ve kural, veri ya da kayıt hatası olarak sınıflandırılır.
- [ ] Shop modeli, senin kayıtlarındaki shop gözlemleriyle level başına maliyet dağılımı testinden geçer (bölüm 6.3). Wisp slotu kuralı ayrıca test edilir.
- [ ] Veri hattı Set 18 ranked maçlarını yama etiketli toplar; Set 18 meta taksonomisi üretilir ve MetaTFT / tactics.tools ile elle kıyaslanır.
- [ ] P1, Set 18 verisiyle bölüm 11'deki kabul kriterlerini geçer.

---

## 5. Veri kaynakları

### 5.1 Riot API'nin sağladıkları [DOĞRULANDI]

Kaynak: `tft-match-v1` şeması ([Riot dokümanı aynası](https://glama.ai/mcp/servers/@chirpon9/riot-docs-mcp/blob/bd23bbcbe155efed4c6774a7dde0bb8020d76191/src/riot_docs/tft-match-v1.md)), [hextechdocs](https://hextechdocs.dev/match-history-tft/), [riot-watcher](https://riot-watcher.readthedocs.io/en/latest/riotwatcher/TeamFightTactics/MatchApi.html).

| Seviye | Alanlar |
|---|---|
| Maç | `game_datetime`, `game_length`, `game_version`, `queue_id`, `tft_game_type`, `tft_set_number`, `tft_set_core_name` |
| Oyuncu | `placement`, `level`, `gold_left`, `last_round`, `time_eliminated`, `players_eliminated`, `total_damage_to_players`, `win`, `puuid`, Riot ID |
| Trait | `name`, `num_units`, `style`, `tier_current`, `tier_total` |
| Birim | `character_id`, `tier` (yıldız), `rarity`, `itemNames` |
| Maç listesi | PUUID başına en fazla 100 maç ID'si, zaman filtresi (`startTime`, `endTime`) |
| Lig (`tft-league-v1`) | Challenger, Grandmaster ve Master listeleri; elo dilimine göre örnekleme için |

Elenen oyuncunun son tahtası, elendiği turdaki tahtasıdır (`last_round` ile). Bu farklı aşamalardan tahta verisi sağlar, ama sadece kaybeden tahtaları gösterdiği için seçilim yanlılığı taşır.

### 5.2 Riot API'nin sağlamadıkları

| Eksik | Etkisi | Telafi |
|---|---|---|
| Augment'ler (Set 13'ten beri) | Augment değeri veriden öğrenilemez | Kural şablonu + simülasyon; senin kayıtların (sadece kişisel analiz) |
| Tur tur zaman çizelgesi | Karar zamanlaması, ekonomi eğrisi, pivot anı gözlenemez | Senin kayıtların (küçük); simülasyon |
| Shop içerikleri, roll sayısı | Shop modeli API ile test edilemez | Senin kayıtların |
| Pozisyon | Pozisyonlama öğrenilemez | Ertelendi |
| Tur bazlı dövüş sonuçları | Sadece eleme zamanı var | Tahta gücü modeli + simülasyon |
| Bench, envanter, bileşenler | Tutulan birimler ve bileşen yolu görünmez | Senin kayıtların |
| Shop olasılıkları, havuz boyutları | API'de yok | Yama notu, oyun içi tooltip, oyun dosyası (çapraz kontrollü) |

### 5.3 Analiz siteleri ve Riot Developer Portal

| Kaynak | Ne sunuyor | Yasal durum | Teknik durum | Karar |
|---|---|---|---|---|
| **Riot Developer Portal** | Resmi API ve anahtarlar | **Geliştirme anahtarı:** 24 saatte bir devre dışı kalıyor, sadece deneme için. **Kişisel anahtar:** "sadece geliştirici veya küçük, özel bir topluluk" için; ürün kaydı ve ayrıntılı açıklama gerekiyor; limit bölge başına 20 istek/sn ve 100 istek/2 dk, limit artışı yok. **Production anahtarı:** geniş kitle için; çalışan prototip gerekiyor; 500 istek/10 sn ve 30.000 istek/10 dk ([Portal dokümanı](https://developer.riotgames.com/docs/portal)) [DOĞRULANDI] | Resmi, stabil | **Ana kaynak.** Kişisel anahtar bizim kullanımımıza tam uyuyor |
| **MetaTFT** | Meta istatistikleri; Overwolf uygulamasında tur tur maç geçmişi, canlı augment istatistikleri, lobi scouting ([Overwolf sayfası](https://www.overwolf.com/app/MetaTFT.com-MetaTFT)) [DOĞRULANDI] | Kullanım şartları okunamadı (sayfa JavaScript gerektiriyor) [KAYNAK GEREKLİ]. robots.txt tarayıcılara açık, ama bu veri kullanım izni anlamına gelmez | Herkese açık API veya dışa aktarma bulunamadı | **Elle kıyaslama.** Tur tur verisi değerli olurdu, ama uygulama kullanıcılarına ait ve bize açık değil. Uygulamanın canlı özellikleri kapsamımız dışında. İstersen veri iş birliği için iletişime geçilebilir |
| **tactics.tools** | Meta, kompozisyon ve item istatistikleri | Şartlarda kazıma hakkında açık bir madde yok; "erişimi herhangi bir nedenle sonlandırabiliriz" maddesi var ([şartlar](https://tactics.tools/terms)) [DOĞRULANDI] | Herkese açık API bulunamadı | **Elle kıyaslama.** Veri istenirse önce yazılı izin (tactics.tools@gmail.com) |
| **lolchess.gg** | Oyuncu profilleri, meta | Kendi kullanım şartları bulunamadı [KAYNAK GEREKLİ]. OP.GG'nin şartları kazımayı ve otomatik script'leri açıkça yasaklıyor, ama bu metin lolchess.gg'yi kapsamıyor ([OP.GG şartları](https://op.gg/lol/policies/agreement)). robots.txt `/search` yolunu yasaklıyor | Herkese açık API bulunamadı | **Elle kıyaslama.** Oyuncu profili verisi gizlilik planımızla zaten uyumsuz |
| Resmi yama notları ve oyun içi tooltip'ler | Mekanik değerleri ve değişiklikler | Halka açık, birinci el | Elle aktarım | **Ana mekanik kaynağı** |
| CommunityDragon (oyun dosyaları) | Birim istatistikleri, trait eşikleri, shop parametreleri | Riot onaylamıyor, lisans belirtilmemiş ([communitydragon.org](https://www.communitydragon.org/)) | Bu sandbox'tan erişim engelli; senin bilgisayarından erişilebilir olmalı | **Dikkatli kullan:** "community-extracted" etiketi, resmi kaynakla çapraz kontrol |
| `spectator-tft-v5` | Aktif oyun bilgisi | Canlı rakip bilgisi | - | **Kullanılmayacak** |

**Analiz sitelerinin bize gerçek katkısı:** Bu sitelerin toplu istatistikleri büyük ölçüde aynı Riot maç verisinden üretiliyor. Bizim kendi verimizden hesaplayamayacağımız bir şey sunmuyorlar (MetaTFT'nin uygulama verisi hariç, o da bize açık değil). Bu yüzden asıl değerleri bir **dış doğrulama noktası** olmaları. Örneğin bizim taksonomimizdeki en popüler 10 arketipin oynanma oranları ve ilk 4 oranları onların sayılarına kabaca yakın değilse, bizim veri hattımızda veya örneklemimizde bir sorun var demektir. Kıyaslama elle, birkaç sayı üzerinden yapılır ve hangi elo, bölge ve zaman aralığının kullanıldığı not edilir.

### 5.4 Veri toplama kapasitesi (kişisel anahtarla) [HESAP]

- 100 istek / 2 dk = saatte **3.000 istek**, bölge başına. Bir maç detayı 1 istek, bir oyuncunun 100 maçlık ID listesi 1 istek.
- Liste ve tekrar ayıklama ek yükü %10-20 olursa, bölge başına saatte **yaklaşık 2.500 maç**.
- Günde 8 saat çalışırsa yaklaşık **20.000 maç**, yani 160.000 tahta. İki haftalık bir yamada bu, tek bir bölgeden bile bir tahta gücü modeli için fazlasıyla yeterli.
- Bu rakamlar M2'de gerçek ölçümle düzeltilecek. Elo dilimi ve bölge seçimi örneklem tasarımının parçası (M2).

### 5.5 Veri ve politika kapısı (G0)

M2 başlamadan önce yazılı bir karar belgesi (`DATA_POLICY.md`) üretilir. Rate limit kapasitesi tek başına bir izin değildir; izin, kayıtlı ürünün Riot tarafından onaylanması ve kullanım şartlarına uymaktır. Belgenin cevaplaması gerekenler:

1. Riot kullanım şartlarının veri saklama, saklama süresi ve model geliştirme ile ilgili maddeleri [KAYNAK GEREKLİ].
2. Ürün kaydı metni: ne topluyoruz, neden, kim kullanacak (sadece sen).
3. Örneklem planı: hangi bölge, hangi elo dilimleri, hangi kuyruk, hangi zaman aralığı. Master+ bir başlangıç varsayımı; senin ligin için ayrı bir doğrulama dilimi.
4. Hangi karar sorusu hangi veriyle cevaplanacak. Veri, karar motorunun ihtiyaç duymadığı bir şey için toplanmayacak.
5. Kendi kayıtlarının kullanım kuralları (geliştirme ve test kümesi, bölüm 6.4).
6. Analiz sitelerinin kullanımı: sadece elle kıyaslama.
7. Yayın ve VOD notlarının kullanımı: elle not, video saklanmaz; otomatik işleme sadece yazılı izinle (bölüm 6.5).

---

## 6. Senin 10-20 maç kaydın: gerçekçi kullanım

### 6.1 Kayıt nasıl olmalı

- TFT'nin resmi bir tekrar izleme (replay) sistemi olduğunu bilmiyorum [KAYNAK GEREKLİ]. Bu yüzden "kayıt" derken **OBS gibi bir araçla ekran videosu** varsayıyorum [VARSAYIM].
- **Oyun sırasında hiçbir analiz aracı çalışmaz.** Video sadece kaydedilir; işleme maçtan sonra yapılır. Bu, kapsam sınırımızla uyumlu [VARSAYIM: Riot politikasının odağı canlı kullanım].
- Her maçtan sonra kısa bir form doldurulur (aşağıda). Maç ID'si daha sonra API'den zaman damgasıyla eşleştirilir; böylece rakiplerin son tahtaları da resmi kaynaktan gelir.
- Videolar büyük dosyalar. Önerim, videoları buraya yüklemek yerine kendi bilgisayarında belirli kareleri çıkarmak (shop görünen anlar, aşama başları). Bunun için ileride küçük bir script veririm.

**Maç sonrası form (taslak):**

| Alan | Ne zaman | Neden |
|---|---|---|
| Her aşama başında (2-1, 3-1, 4-1, 5-1 ...) altın, level, XP, HP, seri | Videodan | Kural motoru testi |
| Augment teklifleri (3 seçenek, yeniden çevirme dahil) ve seçimin | Videodan | Augment şablonlarının kapsamı, kişisel analiz |
| Önemli kararlar (roll, level, pivot) ve kısa gerekçen | Maçtan hemen sonra | M9 vaka çalışmaları |
| Hedeflediğin kompozisyon ve ne zaman değiştiğin | Maçtan hemen sonra | Pivot analizi |
| Son sıralama | API'den | - |

### 6.2 Neye yarar, neye yaramaz

| Kullanım | Yarar mı | Gerekçe [HESAP] |
|---|---|---|
| **Kural motoru testi** (altın, faiz, seri, XP, level) | **Evet, çok** | 20 maç × ~30 tur ≈ **600 gerçek geçiş**. Her biri birebir doğrulanabilir bir test vakası |
| **Shop modeli testi** (level başına maliyet dağılımı, Wisp slotu) | **Evet** | Maç başına ~50 shop × 5 slot ≈ 250 slot; 20 maçta **~5.000 slot**. Bir level'da 1.000 slot varsa, %20'lik bir olasılık ±%1,3 standart hatayla ölçülür. Yanlış girilmiş bir olasılık tablosunu veya Wisp slotunun etkisini yakalar |
| Kötü şans korumasını tespit etmek | **Muhtemelen hayır** | Etki uzun "kuraklık" serilerinde ortaya çıkar; bunlar seyrek. Ancak çok büyük bir etki varsa görünür |
| **Altın fikstürler** (gerçek durumlardan test senaryoları) | **Evet** | Elle uydurulmuş değil, gerçek oyun durumları |
| **M9 vaka çalışmaları** (maç sonrası analiz arayüzünün testi) | **Evet** | Motorun önerilerini senin gerçek kararlarınla nitel olarak karşılaştırmak |
| Tahta gücü veya sıralama modeli eğitmek | **Hayır** | Gereken veri on binlerce tahta; API bunu zaten sağlıyor |
| Augment kazanma oranı veya değeri | **Hayır** | ~60 augment teklifi, yüzlerce farklı augment arasında dağılıyor |
| Motorun senden daha iyi karar verdiğini kanıtlamak | **Hayır** | 20 maçta ortalama sıralamanın standart hatası ≈ 2,3 / √20 ≈ **0,5 sıra**. 1 sıradan küçük farklar bu gürültüde görünmez |
| Simülatör kalibrasyonu | **Hayır** (az) | Kalibrasyon API'deki binlerce maç sonu dağılımıyla yapılır; kayıtlar sadece nitel kontrol |

**Sonuç:** Kayıtları bir **eğitim seti değil, test seti ve doğrulama kaynağı** olarak kullanacağız. Hiçbir zaman eğitimde kullanılmayacaklar ki bağımsız kalsınlar. Set 18 bitmeden 10-20 maç kaydetmen, M1'in güncel sette test edilmesini sağlar. Bu yüzden ne kadar erken başlarsan o kadar iyi.

### 6.3 Shop gözlem testinin tasarımı

- Her shop için: level, 5 slotun maliyetleri (ve birim isimleri), Wisp slotu olup olmadığı, aktif Inferno veya Riftbeast etkisi.
- Test: level başına gözlenen maliyet dağılımı ile `gamedata`'daki tablo arasında çok terimli (multinomial) olabilirlik testi. Sete özel etkilerin olduğu shop'lar ayrı tutulur.
- Kabul edilmeden önce güç analizi yapılır: hangi büyüklükteki sapmayı yakalayabildiğimiz rapora yazılır. Bunu yapmazsak "sapma bulunmadı" sonucu yanıltıcı olur.
- İlk etiketleme elle yapılır. Örnek sayısı artarsa, birim ikonlarını tanıyan basit bir yarı otomatik araç (kendi videoların üzerinde, maç sonrası) değerlendirilir. Bu ancak elle etiketleme gerçekten darboğaz olursa yapılır.

---

### 6.4 Geliştirme ve test kümesi ayrımı (yeni)

Kayıtlarını baştan rastgele ama tohumlu biçimde ikiye ayırıyoruz [VARSAYIM: yaklaşık yarı yarıya]:

- **Geliştirme kümesi:** Kural ve shop hatalarını bulmak, P1 senaryolarını kurmak ve uzman etiketlerini ayarlamak için. Burada bulunan her hata düzeltilir.
- **Test kümesi:** M1b ve P1/P2 kabulü için **bir kez** kullanılır. Bu kümeyle hiçbir ayar yapılmaz. Bir hata burada bulunursa düzeltilir, ama o kayıt artık bağımsız test sayılmaz ve rapora öyle yazılır.

İki ayrı soru da ayrı ölçülür: (a) kural motoru oyunu doğru modelliyor mu, (b) motorun önerileri senin kararlarından farklı mı ve neden. İkincisi hiçbir zaman "motor senden iyi" iddiasına dönüşmez; 20 maçla bunun istatistiksel gücü yok.


### 6.5 Üst seviye yayınlar ve VOD'lar (yeni, v0.4.1)

Kick ve YouTube'daki üst seviye oyuncu yayınları, API'nin vermediği tur bazlı bilgiyi (aşamaya göre altın, level, HP, roll zamanları, augment seçimleri) gösteren tek büyük kaynak. Fikir değerli; ama nasıl kullanıldığı önemli.

**Yasal sınırlar** [DOĞRULANDI, hukuki görüş değildir]:

- YouTube şartları, YouTube veya hak sahibinin önceden yazılı izni olmadan içeriği indirmeyi ve servise robot veya kazıyıcı gibi otomatik yollarla erişmeyi yasaklıyor; içerik kişisel, ticari olmayan izleme için ([YouTube şartları, 15 Aralık 2023](https://www.youtube.com/static?template=terms)).
- Kick şartları, servisin herhangi bir bölümünü otomatik veya otomatik olmayan yollarla kopyalamayı ve robot, spider veya "offline reader" gibi otomatik sistemlerle erişmeyi yasaklıyor ([ConductAtlas'taki Mayıs 2026 kopyası](https://conductatlas.com/platform/kick/kick-terms-of-service/prohibition-on-scraping-service-content/); güncel metin [KAYNAK GEREKLİ]: https://kick.com/terms-of-service).

**Sonuç:**

| Yöntem | Durum |
|---|---|
| Videoları indirmek, kare çıkarmak, otomatik OCR ile okumak | **Yapılmayacak** (yayıncı ve platform izni olmadan) |
| Normal izleyerek, elle yapılandırılmış notlar almak (altın, level, HP, augment, karar) | **Uygun** [VARSAYIM: kişisel izleme + kendi notlarımız; video, kare veya klip saklanmaz] |
| Yayıncıdan yazılı izin almak | **En iyi yol**, otomatik işlemeyi de mümkün kılar |
| Ekrandaki rakip ve izleyici isimlerini kaydetmek | **Yapılmayacak** (gizlilik) |

**Maliyet** [HESAP]: Bir maçı 8 aşama noktasında (2-1, 2-5, 3-2, 3-5, 4-1, 4-5, 5-1, oyun sonu) elle not etmek, video hızlandırılarak maç başına yaklaşık 15-25 dakika. 30-50 maç birkaç haftalık iş. Otomatik okuma (OCR) izin gerektirdiği gibi, yayın overlay'leri, kamera ve sete göre değişen arayüz yüzünden de pahalı. Önce 5 maçla süre ölçülür, sonra karar verilir.

**Yanlılıklar:**

- **Seçilim:** YouTube'a yüklenen maçlar çoğunlukla iyi biten veya ilginç maçlar. Tam yayın kayıtları (VOD) daha az yanlı; bunlar tercih edilir.
- **Az sayıda oyuncu:** Birkaç yayıncının kişisel stili veri setine hâkim olur. Oyuncu başına maç sayısı sınırlanır ve analizde oyuncu ayrı bir değişken olur.
- **Yayın davranışı:** Yayıncılar eğlence için deneysel oynayabilir. Bu maçlar not edilir.
- **Bölge ve yama:** Çoğu yayın NA, EUW veya KR. Her not yama ve bölge etiketi taşır; yama uyuşmazsa sadece nitel kullanılır.
- **Kısmi gözlem:** Sadece yayıncının ekranı görünür; rakipler sadece yayıncı baktığında.

**Mimarideki yeri:** Bu veri `ObservedOpponentState` ve `ownlogs` ile aynı sınıfta, ayrı bir kaynak etiketiyle (`source: stream-notes`) tutulur. Riot API verisiyle karıştırılmaz.

| Kullanım | Yarar | Nerede |
|---|---|---|
| Aşamaya göre tipik altın, level ve HP gidişatı | **Yüksek.** P1'in ve `OpponentPrior`'ın en zayıf varsayımlarını (ör. "4-1'de rakipler son tahtalarına ne kadar yakın") gerçek gözleme bağlar | P1 varsayımları, M5 |
| Simülatör gidişat doğrulaması | **Yüksek.** M6 güvenilirlik haritasının "gerçek gidişat" testine üst seviye örnekler ekler | M6 |
| Augment seçimi dağılımı (kazanma oranı değil) | **Orta.** Hangi augment'in hangi durumda seçildiğini gösterir; iyi olup olmadığını göstermez | M8 şablon önceliği |
| Uzman taban çizgisi | **Orta.** "Güçlü oyuncu bu durumda ne yaptı" bir karşılaştırma noktasıdır, doğru cevap etiketi değildir | P1/P2 uzman uyumu |
| Kararların doğruluğunu öğrenmek | **Hayır.** Senin de dediğin gibi, yaptıkları doğru kabul edilmez; ve maç başına bir sonuç çok gürültülü | - |

**Kural:** Senin kayıtların gibi, yayın notları da geliştirme ve test kümelerine ayrılır. Bir yayıncının bütün maçları aynı kümede durur, böylece model bir oyuncunun stilini ezberleyip başka maçlarında test edilmiş gibi görünmez.

---

## 7. Açık kaynak inceleme bulgularının plana etkisi

Kaynak: [ACIK_KAYNAK_INCELEME.md](ACIK_KAYNAK_INCELEME.md).

| Bulgu | Plana etkisi |
|---|---|
| `tft_analyzer`'ın lisansı yok | Kod kopyalanmayacak; fikirler kendi kodumuzla yazılacak |
| `teamfight-simulator` ISC lisanslı ama Set 6'da kalmış dövüş motoru (94 tahmini sabit, tohumlanamayan RNG, tarayıcıya bağlı, 19 aydır bakımsız) | Dövüş simülatörü kurmama kararı güçlendi. Gerçeğe yakın bir dövüş motorunun bakım maliyetinin somut örneği |
| Oyun dosyalarında shop **kötü şans koruması** parametre bloğu (Set 11'de görülmüş) | **M1a** (arayüz) **ve M1b** (korumalı model): `ShopModel` arayüzü, bağımsız ve korumalı iki model, Set 18'de koruma durumunun doğrulanması (bölüm 11, M1) |
| Shop oranları, havuz boyutları ve seri altını oyun dosyasından otomatik çıkarılabiliyor | **M1b:** Opsiyonel çıkarıcı, `community-extracted` etiketiyle ve resmi kaynakla çapraz kontrolle |
| Sete özel shop kuralları (Set 10 Headliner) | **M1a** (şema) **ve M1b** (kurallar): `shop_rules` bloğu. Set 18'de Wisp, Inferno ve Riftbeast ile **gerçekten gerekli** (bölüm 4.1) |
| `tft_analyzer` veri hattı: ham JSON'u önce diske yazmak, çok pencereli rate limiter, 5 tablolu normalize şema, gömülü DuckDB | **M2 şablonu.** Bizim farklarımız: PUUID hash'leme, Riot ID'nin atılması, tarama anında ranked (`queue_id = 1100` [KAYNAK GEREKLİ: güncel değer]) ve zaman filtresi, şema doğrulama, yama sabitli statik veri, elo dengeli örnekleme |
| `tft_analyzer` istatistikleri: güven aralığı, yama ayrımı ve lobi analizi yok; kompozisyon imzası kırılgan | M3-M5'in özgün olduğunu doğruluyor; taksonomide kararlılık testi şart |
| İki projede de lobi düzeyi analiz, havuz çakışması, rekabet etkisi ve 8 oyunculu simülasyon yok | Planın rakip ve rekabet kısmını kısaltacak hazır bir şey yok |

---

## 8. Mimari

Beş katman. Her katman sadece altındakine bağımlı. Çekirdek (katman 1-4) ağ çağrısı yapmaz.

```
Katman 5  ARAYÜZ VE DENEYLER
          analysis/     maç sonrası analiz (önce CLI)
          experiments/  config, seed, metrik kaydı, eşleştirilmiş karşılaştırma

Katman 4  KARAR MOTORU
          decision/candidates  aday kararlar: makro aksiyonlar + kompozisyon hedefleri
          decision/evaluate    adayların sonuç dağılımı (sıralama, ilk 4, risk)
          decision/search      beam + sınırlı lookahead, CRN, önbellek, bütçe
          decision/explain     bileşen katkıları, varsayımlar, güven

Katman 3  SİMÜLASYON
          macrosim/  8 oyunculu soyut oyun: ekonomi ve shop K1'den, dövüş sonucu
                     BoardStrength'ten, rakipler OpponentModel'den, augment/item şablonları

Katman 2  MODELLER
          comp_taxonomy   arketip kümeleri (yama bazlı)
          meta            arketip payları, güç, rekabet etkisi
          board_strength  tahta → sıralama dağılımı (Plackett-Luce + GBDT)
          opponent        lobi dağılımı, PoolBelief üretimi, kalibre rakip politikaları
          items           item-birim eşleşmesi ve katkısı
          augments        yapılandırılmış etki şablonları (veriden değil, kuraldan)
          comp_value      kompozisyon hedefinin değeri ve ulaşma maliyeti

Katman 1  MEKANİK ÇEKİRDEK (M0 + M1)
          gamedata  versiyonlu statik veri, kaynak ve durum etiketleri, shop_rules
          state     GameState, bilinmeyenler için açık tipler, PoolBelief
          rules     ekonomi, XP, satın alma/satma, trait aktivasyonu
          prob      ShopModel arayüzü; kesin hesap + tohumlanabilir örnekleyici

Katman 0  VERİ (çekirdekten ayrı)
          ingest    Riot API istemcisi; ham ve işlenmiş veri ayrı
          datasets  versiyonlu veri setleri, veri kartları, train/val/test bölmeleri
          ownlogs   senin kayıtların için şema, doğrulayıcı, video kare etiketleri
```

### 8.1 İstediğin yeteneklerin yeri

| Yetenek | Nerede | Nasıl |
|---|---|---|
| Rakip modelleme | `opponent` (K2), `macrosim` (K3) | Lobi dağılımı + `PoolBelief` (rakiplerin muhtemel birimleri → kalan kopya dağılımı) + kalibre rakip politikaları |
| Kompozisyon değerlendirmesi | `comp_taxonomy`, `meta`, `comp_value` (K2) | Değer = ulaşma olasılığı ve maliyeti (M1 + `PoolBelief`) × hedef tahta gücü − rekabet cezası |
| Kal / pivot / alternatif | `decision` (K4) | Her kompozisyon hedefi bir aday; adaylar aynı rastgele dünyalarda (CRN) simüle edilir |
| Augment değerlendirmesi | `augments` (K2), `decision` (K4) | Her teklif bir aday karar; çıktı "simulated, düşük güven" + hassasiyet |
| Ekonomi, level, roll, satın alma | `rules`, `prob` (K1), `decision` (K4) | Makro aksiyonlar ("8'e kadar roll", "level al", "50'de faiz tut") |
| Gerçekle karşılaştırma | `experiments`, `datasets`, `ownlogs` | Zaman bölmeli test setleri + senin kayıtların ayrı bir değerlendirme seti |

### 8.2 M1'in sonraki modüllere bağlantısı

| M1 bileşeni | Kim kullanır | Tasarım şartı |
|---|---|---|
| `rules` | `macrosim`, `decision` | Saf fonksiyonlar, veri dosyasından parametreli |
| `prob.exact` | `comp_value`, `decision/evaluate` | Çoklu hedef; havuz girdisi dağılım (`PoolBelief`) |
| `prob.sampler` | `macrosim` | Vektörize; aynı seed aynı shop dizisi (CRN) |
| `ShopModel` | Hepsi | Bağımsız / korumalı / sete özel kurallar takılabilir; kullanılan model her çıktıda yazar |
| `GameState` | Hepsi | JSON'a serileştirilebilir, hash'lenebilir, bilinmeyenler açık |

---

### 8.3 Rakip bilgisi: önsel ve gözlem ayrımı (yeni)

| Kavram | Kaynak | Ne söyler | Ne söylemez |
|---|---|---|---|
| `OpponentPrior` | Riot API maç sonu verisi (meta + lobi dağılımı) | Bu yama ve elo diliminde rakiplerin hangi kompozisyonlarla bitirdiği | Rakibin belirli bir turda ne tuttuğu, neyi bıraktığı, ne zaman pivot yaptığı |
| `ObservedOpponentState` | Senin kayıtlarındaki ekran görüntüleri | Belirli bir anda ekranda görünen tahta ve (görünüyorsa) bench | Görünmeyen bench, sonraki satışlar, oyuncunun niyeti |
| `PoolBelief` | İkisinin birleşimi + kendi tahtan | Kalan kopya sayısının **dağılımı** | Kesin kopya sayısı (ancak tüm tahtalar ve bench'ler görünürse) |

Birleştirme kuralları:

- Her girdi kaynağıyla ve zaman damgasıyla saklanır. Çıktıda havuz hesabının ne kadarının gözleme, ne kadarının önsele dayandığı yazar.
- Gözlem, gözlendiği an için bir **alt sınırdır** (görünen birimler kesin alınmış), sonrası için değil. Gözlem eskidikçe belirsizliği artar, çünkü rakip birim satmış ya da pivot yapmış olabilir [VARSAYIM: eskime modeli basit başlar, kayıtlarınla kontrol edilir].
- Önsel aşamaya göre koşullanırken kullanılan her geçiş varsayımı (ör. "4-1'de rakipler son kompozisyonlarının %X'ine sahiptir") `assumption` olarak etiketlenir. Maç sonu verisinden öğrenilmiş gibi gösterilmez.

### 8.4 Etki arayüzü: item, augment ve diğerleri (yeni)

P1'den itibaren her item, augment, Wisp ve benzeri şey aynı arayüzle tanımlanır, böylece sonradan mimariye eklemek gerekmez:

```
Effect
  id, set, patch, source, status (verified / unverified / unknown)
  type: economy | resource | trait | combat | special
  apply(state) -> state        # sadece mekanik olarak tanımlanabilen kısım
  strength_modifier(board)     # savaş etkisi; P1'de varsayım, M4'ten sonra veriden
  confidence: exact | data_estimated | assumption
```

### 8.5 Üç güven sınıfı (her çıktıda)

| Sınıf | Örnek | Nasıl gösterilir |
|---|---|---|
| **Kesin (mekanik)** | Ulaşma olasılığı, harcanan altın, faiz | Değer + kesin hesap |
| **Veriden tahmin** | Tahta gücü, item katkısı, meta, rekabet etkisi | Değer + güven aralığı + veri sürümü |
| **Varsayım veya simülasyon** | HP kaybı modeli, savaş augment'leri, rakip geçişleri, kararların sıralamaya etkisi | Değer + "varsayım" etiketi + hassasiyet aralığı |

Bir sonuç, girdilerinin en zayıf güven sınıfını taşır. Yani bir karar önerisi, içinde tek bir varsayım varsa "varsayım" sınıfındadır.

Bir sonuç, girdilerinin en zayıf güven sınıfını taşır. Yama bilgisi de bunun parçasıdır: gözden geçirilmemiş bir yamanın verisiyle üretilen sonuç bu uyarıyı taşır.

### 8.6 Yama katmanı: her analiz yama bazlı (yeni, v0.4.2)

Bir set tek bir bütün olarak analiz edilmez. Ekonomi kuralları çoğu yamada aynı kalsa da şampiyon, item ve augment değerleri her yamada buff ve nerf alabilir. Bu yüzden:

1. **Veri katmanı:** Her set için bir `base.json`, her yama için ayrı bir `patches/<yama>.json` dosyası tutulur. Yama dosyası sadece değişiklikleri içerir. Her değişiklik bir kayıttır: hangi parametre, yeni değer, tür (`buff`, `nerf`, `adjustment`, `system`, `new`, `removed`, `correction`) ve kaynak (yama notu bağlantısı). Kaynaksız değişiklik reddedilir. **[M1a'da yapıldı]**
2. **Yükleme:** `load_gamedata(set, yama)` taban veriye o yamaya kadarki bütün değişiklikleri sırayla uygular. Dosyası olmayan bir yama istenirse hata verir, sessizce eski veriyi kullanmaz. Yama notları henüz işlenmemiş yamalar `not_reviewed` olarak işaretlenir ve her çıktıda uyarı olarak görünür. **[M1a'da yapıldı]**
3. **Anahtarlama:** Her veri kaydı, model, deney kaydı ve rapor bir yama kimliği taşır. Bir maç, oynandığı yamanın verisiyle değerlendirilir.
4. **Yama başına değerlendirme:** Meta (M3), tahta gücü ve item katkısı (M4), augment değeri (M8) ve rakip önseli (M5) her yama için ayrı ölçülür. Kalibrasyon ve doğruluk metrikleri de yama başına raporlanır.
5. **Yamalar arası bilgi paylaşımı:** Yeni yamanın ilk günlerinde örnek azdır. O zaman önceki yamanın tahmini başlangıç noktası olur ve yeni veri geldikçe ağırlığı azalır (shrinkage). Sadece o yamada değişen birimler, item'lar ve augment'ler için önceki yamanın ağırlığı daha da düşürülür. Değişmeyen bir şeyin verisi yamalar arasında birleştirilebilir. Ancak bunun için önce iki yamanın dağılımları karşılaştırılır (drift testi). Fark anlamlıysa veri birleştirilmez.
6. **Değişiklik etkisi raporu:** Her yeni yamada "bu yamada ne değişti, hangi kararlar değişti" raporu çıkarılır. P1/P2 senaryoları eski ve yeni yamada koşulur, farklılaşan kararlar listelenir.
7. **Sınır:** Yama içinde yapılan sessiz düzeltmeler (hotfix) ayrı bir yama kimliğiyle kaydedilir (örneğin `18.4b`).

---

## 9. Item ve augment: objektif değerlendirme

Item ve augment'ler TFT'de belirleyici, buna katılıyorum. Ama ne kadarını gerçek veriyle değerlendirebileceğimiz ikisi için çok farklı.

### 9.1 Item'lar

| Soru | Veri var mı | Ne zaman | Güven |
|---|---|---|---|
| Bu birim bu item'larla tahtaya ne katıyor? | **Evet**, son item'lar API'de | M4 | Veriden tahmin |
| En iyi item taşıyıcısı kim? | **Evet** | M3-M4 | Veriden tahmin |
| Bu bileşenleri şimdi mi birleştirmeli, beklemeli mi? | Hayır (bileşen ve zamanlama yok) | P2'de basit, M8'de derin | Varsayım |
| Bu bileşen hangi item'a gitmeli? | Kısmen (son item'ların dağılımı var, yol yok) | M8 | Veriden tahmin + varsayım |
| Item'ın savaşta tam etkisi | Hayır (dövüş simülasyonu yok) | Ertelendi | - |

**Sonuç:** Item'ların büyük kısmı M4'te gerçek veriyle giriyor, yani sona kalmıyor. P1'de item'lar sadece etki arayüzüyle ve varsayımsal güç çarpanıyla var.

### 9.2 Augment'ler: beş tip

| Tip | Örnek etki | Nasıl değerlendirilir | En erken | Güven |
|---|---|---|---|---|
| **Ekonomi** | Altın, faiz, XP, ücretsiz roll | M1 kurallarıyla kesin: ekonomiye etkisi tam hesaplanır | **P1** | Ekonomi etkisi kesin; sıralamaya etkisi varsayım |
| **Kaynak** | Bileşen, item, birim, amblem verilmesi | Kaynak kesin eklenir; değeri item ve tahta modelinden | **P1** (kaynak), P2 (değer) | Kaynak kesin; değeri veriden tahmin (M4 sonrası) |
| **Trait / amblem** | Trait +1, amblem | `comp_value` ile trait eşiği değişimi; tahta gücü modeli trait seviyesini zaten kullanıyor | P2 | Veriden tahmin (dolaylı) |
| **Savaş istatistiği** | Saldırı hızı, can, kalkan | Sadece tahta gücüne varsayımsal çarpan | P2 (arayüz), M8 | Varsayım, en düşük |
| **Özel mekanik** | Kural değiştiren augment'ler | Tek tek; tanımlanamayan `unknown` | M8 | Çoğunlukla bilinmiyor |

Her augment'in metni oyun içinden veya yama notundan gelir; etkisi kaynakla birlikte şablona yazılır. Şablona yazılamayan augment `unknown` kalır ve motor onu değerlendirdiğini iddia etmez.

**Augment'ler için gerçekten mümkün olan doğrulama:** Kendi kayıtlarındaki augment teklifleri (~60 teklif) ile motorun sıralaması ve senin seçimin karşılaştırılır. Bu bir doğruluk ölçüsü değil, tutarlılık kontrolü. Ayrıca Riot'un augment istatistiklerini bilinçli olarak gizlediğini hatırlatmak gerekiyor; kendi kural tabanlı değerlendirmemizi kişisel analiz için kullanıyoruz, kamuya istatistik olarak sunmuyoruz.

---

## 10. Algoritma seçimleri

| Problem | Başlangıç yöntemi | Rakip yöntem(ler) | Nasıl karar verilir |
|---|---|---|---|
| Shop ve ulaşma olasılığı | Kesin DP / Markov zinciri | Monte Carlo | İkisi her zaman birbirini doğrular; kesin hesap mümkün olmayan durumlarda Monte Carlo |
| Tahta gücü | Plackett-Luce (8'li sıralama modeli) + gradient boosting | Basit sezgisel baseline'lar; ileride küçük sinir ağı | Zaman bölmeli test log-olabilirliği ve kalibrasyon |
| Kompozisyon taksonomisi | k-medoids veya hiyerarşik kümeleme | Kural tabanlı imza (tft_analyzer tarzı) | Bootstrap kararlılığı ve yama sonrası kapsama |
| Lobi / rakip dağılımı | Düzgünleştirilmiş koşullu sayım | Daha karmaşık modeller ancak baseline'ı geçerse | Test lobilerinde log-loss |
| Rakip politikaları | Parametreli, simülasyonla kalibre politikalar | - | Kalibrasyonda kullanılmayan istatistiklerle uyum |
| Kararlar | Makro aksiyonlarda eşleştirilmiş Monte Carlo + beam + sınırlı lookahead | MCTS (açık döngü, şans düğümlü) | Aynı bütçe, aynı senaryolar, beklenen sıralama |
| Kullanılmayanlar | Satranç minimax (TFT iki kişilik tam bilgi oyunu değil); RL (simülatör gerçeğe yakın olmadan, simülatörün hatalarını öğrenir) | | |

**Simülatörü sömürme riski:** Karar motoru simülatörde test edildiği için, simülatörün hatalarından yararlanan kararlar "iyi" görünebilir. Her karar karşılaştırması, simülatör parametreleri belirsizlik aralığında değiştirildiğinde de tekrarlanır. Sadece bu değişikliklere dayanıklı üstünlükler raporlanır.

---

## 11. Yol haritası (v0.4)

Her milestone çalışan ve testli bir çıktı bırakır. Boyut göreli: **S** küçük, **M** orta, **L** büyük. Ortak teknik kriterler her milestone için geçerli: tüm testler geçer; aynı seed ve config ile aynı sonuç; deney kaydında config, seed, git commit ve veri sürümü var; kural ve olasılık kodunda satır kapsamı ≥ %90.

Her milestone'da iki kriter var: **Teknik kabul** (doğru çalışıyor mu) ve **Hedefe katkı** (karar motoruna ne kattı, nasıl ölçüldü).

```
G0 (veri/politika kapısı) ──────────────────► M2 ─► M3 ─► M4 ─► P2 ─► M5 ─► M6 ─► M7 ─► M8 ─► M9
M0 ─► M1a ─► P1 (ilk karar prototipi) ─► M1b ─┘                ▲
                     └────────── hassasiyet raporu, öncelikleri belirler ──┘
Kayıt protokolü (sen) ─► M1b ve P1 testleri
```

**İlk çalışan karar prototipine en kısa yol:** M0 → M1a → P1. G0 paralel ilerler. API anahtarı, veri toplama ve ML gerekmez.

### G0: Veri ve politika kapısı · Faz A · S · paralel

- **Görevler:** Bölüm 5.5'teki altı soru; `DATA_POLICY.md`; Riot ürün kaydı metni.
- **Teknik kabul:** Altı sorunun her biri kaynaklı cevaplanmış veya açıkça "bilinmiyor" olarak işaretlenmiş.
- **Hedefe katkı:** Toplanacak her veri alanı, cevaplayacağı karar sorusuyla eşleştirilmiş. Eşleşmeyen alan toplanmıyor.

### M0: Proje iskeleti · Faz A · S

- **Görevler:** Paket yapısı; Python sürümü; pytest, hypothesis, ruff; seed yönetimi; deney kayıt formatı; Windows talimatı.
- **Teknik kabul:** `pytest` temiz; örnek deney iki kez çalıştırıldığında aynı sonuç; senin makinende çalışır.
- **Hedefe katkı:** Yok (altyapı). Bu yüzden en küçük tutuluyor.

### M1a: En küçük mekanik çekirdek · Faz A · S

- **Görevler:**
  1. `gamedata` şeması (kaynak ve durum alanları, `shop_rules` bloğu).
  2. Set 18 temel verisi: level başına shop olasılıkları, havuz boyutları, XP ve roll maliyetleri, ekonomi kuralları. Kaynaklar yama notu ve senin tooltip ekran görüntülerin; uyuşmazlık raporlanır.
  3. `state`: ekonomi alt kümesi + `PoolBelief` (dağılım).
  4. `rules`: gelir, faiz, seri, XP, level, satın alma, satma, roll.
  5. `prob`: `ShopModel` arayüzü; sadece `IndependentShopModel`; kesin ulaşma olasılığı (tek ve çoklu hedef); tohumlanabilir örnekleyici.
- **Teknik kabul:** Şema kaynaksız alanı reddeder; 30 senaryoda Monte Carlo kesin hesabın %99 güven aralığında; özellik testleri (altın, havuz korunumu, olasılık toplamı, rekabetle monoton azalma); aynı seed aynı shop dizisi.
- **Durum: tamamlandı.** 86 test geçiyor. `tft-engine odds` komutu bir durumun kesin olasılığını yazdırıyor. Set 18 değerleri doğrulanmadı (bkz. README).
- **Hedefe katkı:** P1'in ihtiyaç duyduğu üç soruyu kesin cevaplar: "G altınla bu birimleri bulma olasılığı", "beklenen harcanan altın", "rakipler aynı birimi tutuyorsa olasılık ne kadar düşer".

### P1: İlk uçtan uca karar prototipi · Faz A · M

- **Durum: ilk sürüm tamamlandı (2026-10-20).** 10 senaryo, bariz 5'i doğru, senaryo başına ≤ 1 sn. Uzman uyumu (senin etiketlerin) bekliyor. Sonuçlar: `repo/docs/P1_SONUC.md`.

- **Amaç:** Mimarinin hedef problemi gerçekten çözüp çözmediğini erkenden görmek ve hangi varsayımın kararı değiştirdiğini ölçmek. **"Doğru karar" iddiası değil.**
- **Girdi:** JSON olarak elle girilmiş bir oyun durumu: aşama, altın, level, XP, HP, tahta, bench, item'lar, augment'ler, bilinen rakip tahtaları (gözlem) ve varsayılan rakip önseli.
- **Aday kararlar:**
  - A: Mevcut kompozisyonda kal, mevcut level'da roll yap (eşiğe kadar).
  - B: Level al, ekonomiyi koru.
  - C: Ekonomiyi koru, roll yapma.
  - D: Daha az rekabet edilen alternatif kompozisyona geç (1-3 aday hedef, elle veya basit kuralla).
  - Augment seçimi varsa: her teklif ayrı aday (sadece ekonomi ve kaynak tipi değerlendirilir; diğerleri "değerlendirilmedi" etiketiyle gösterilir).
- **Değerlendirme ufku:** Sonraki 2-4 tur [VARSAYIM]. Bu kısa ufuk bilinçli: tam oyun simülasyonu P1'in işi değil.
- **Çıktılar (her aday için):**
  - Kesin: hedef tahtaya ulaşma olasılığı, harcanan altın dağılımı, ufuk sonundaki ekonomi.
  - Varsayım: tahta gücü (yapılandırılabilir sezgisel formül), tur kazanma olasılığı (rakip önseline karşı), beklenen HP kaybı ve elenme riski.
  - Hassasiyet raporu: her varsayım belirsizlik aralığında değiştirildiğinde adayların sıralaması değişiyor mu; kararı en çok değiştiren üç varsayım.
  - Etiketler: her sayının güven sınıfı (bölüm 8.5), kullanılan shop modeli, `unverified` kurallar.
- **Teknik kabul:**
  - En az 10 elle hazırlanmış senaryoda çalışır; her çıktı güven sınıfı taşır.
  - Senaryo başına süre senin makinende ölçülür [HEDEF: ≤ 10 saniye].
  - Aynı seed ile aynı sonuç; adaylar ortak rastgele sayılarla (CRN) karşılaştırılır.
- **Hedefe katkı:**
  - **Bariz senaryolar:** Cevabı herkesin bildiği en az 5 senaryoda (ör. 3 yıldız için 1 kopya eksik, havuzda bol kopya, yeterli altın var) doğru tarafı seçer. Seçmezse bu bir hata kabul edilir ve kaynağı bulunur.
  - **Uzman uyumu:** Senin etiketlediğin senaryolar (geliştirme ve test kümesi ayrı, en az 20 senaryo [HEDEF]) ile P1'in tercihleri karşılaştırılır. Uyuşmazlıklar tek tek incelenir ve "motorun varsayımı yanlış", "senin tercihin farklı bilgi kullanıyor" veya "belirsiz" olarak sınıflandırılır. Bu bir doğruluk iddiası değil, mimarinin doğru soruları sorup sormadığının kontrolü.
  - **Öncelik raporu:** Hassasiyet raporundan, kararı en çok değiştiren varsayımlar listelenir. Sonraki milestone'ların sırası bu listeye göre gözden geçirilir. Örneğin kararlar en çok tahta gücü varsayımına duyarlıysa M4 öne çekilir.

### M1b: Set 18 ayrıntıları ve kayıtlarla doğrulama · Faz A · M

- **Görevler:** Wisp, Inferno ve Riftbeast kuralları (senaryo varyantı olarak); kötü şans korumasının araştırılması ve doğrulanırsa `BadLuckProtectionShopModel`; opsiyonel oyun dosyası çıkarıcısı (`community-extracted`); kayıtlardan tur geçişi ve shop gözlem testleri; benchmark.
- **Teknik kabul:** Tur geçişlerinin ≥ %98'i birebir doğru (önce geliştirme kümesi, sonra bir kez test kümesi) [HEDEF]; shop gözlem testi güç analiziyle raporlanır; kötü şans korumasının durumu belgelenir; doğrulanmamış her kural `unverified` olarak kalır.
- **Hedefe katkı:** P1'in kesin kısmının gerçek Set 18 oyunlarına ne kadar uyduğu ölçülür. Doğrulanmamış kuralların P1 kararlarını ne kadar değiştirdiği raporlanır.

### M2: Veri hattı · Faz A · M · G0'dan sonra

- **Görevler:** `ingest` (bölge yönlendirmesi, rate limiter, ham JSON'u diske yazma, tarama anında ranked ve zaman filtresi); G0'daki örneklem planı; `datasets` (normalize şema, PUUID hash'leme, Riot ID atma, veri kartı); zaman bölmeli train/val/test; `ownlogs` şeması.
- **Teknik kabul:** Ölçülen toplama hızı raporlanır; tekrar yok; yama etiketli; ham veriden tek komutla yeniden üretim; analiz setinde kimlik bilgisi yok; bölme sızıntı testi geçer.
- **Hedefe katkı:** G0'daki her karar sorusu için gereken alanların veri setinde olduğu ve yeterli örnek sayısına sahip olduğu raporlanır (ör. her arketip için en az N tahta [HEDEF]).

### M3: Kompozisyon taksonomisi ve meta · Faz A'da deneme, Faz B'de asıl · M

- **Görevler:** Tahta özellik vektörleri; kümeleme; bootstrap kararlılığı; arketip isimlendirme (senin kontrolünle); oynanma oranı, ortalama sıralama ve ilk 4 oranı (güven aralığıyla); elo dilimine göre ayrım; harici sitelerle elle kıyaslama.
- **Teknik kabul:** Bootstrap kararlılığı (ARI) ≥ 0,8 [HEDEF]; tahtaların ≥ %85'i bir arketipe atanır [HEDEF]; aynı kod Set 19'da sadece veri değişerek çalışır.
- **Hedefe katkı:** P1'deki elle girilen "alternatif kompozisyon" adaylarının yerini veriden gelen arketipler alır; `OpponentPrior`'ın ilk sürümü (meta payları) P1'e bağlanır.

### M4: Tahta gücü ve item katkısı · Faz B · M

- **Görevler:** Baseline'lar (trait sayısı + maliyet sezgiseli, arketip ortalaması, birim ortalaması); Plackett-Luce + gradient boosting; item taşıyıcı ve item özellikleri; `last_round` dilimleri ve seçilim yanlılığı; kalibrasyon.
- **Teknik kabul:** Zaman bölmeli testte log-olabilirlik ve ilk 4 Brier skoru üç baseline'ı da anlamlı biçimde geçer; ECE ≤ 0,03 [HEDEF]; item ablation raporu.
- **Hedefe katkı:**
  - P1'deki varsayımsal tahta gücü formülü bu modelle değiştirilir. P1'in senaryolarında kaç kararın değiştiği raporlanır (değişen her karar incelenir).
  - **Senin ligin:** Model, Master+ dışındaki bir doğrulama diliminde ayrıca test edilir (G0'daki örneklem planına göre). Performans düşüşü raporlanır; Master+ varsayımı bu sonuca göre korunur veya değiştirilir.

### P2: Karar prototipi v2 · Faz B · M

- **Görevler:** P1'e M3 ve M4'ü bağlamak; trait/amblem augment'leri (`comp_value` üzerinden); kaynak augment'lerinin değeri (M4'ten); savaş augment'leri için arayüz (varsayım çarpanı); bileşen birleştirme kararı için basit model; değerlendirme ufkunu aşamanın sonuna kadar uzatmak.
- **Teknik kabul:** P1'in tüm kabul kriterleri; ek olarak M4 tabanlı çıktılar güven aralığıyla.
- **Hedefe katkı:** P1 ile aynı senaryolarda: bariz senaryolarda başarı korunur; test kümesindeki uzman uyumu P1'e göre raporlanır (iyileşme şartı yok, değişim incelenir); hassasiyet raporunda "varsayım" sınıfındaki girdilerin karar üzerindeki payı azalır [HEDEF: ölçülür ve raporlanır].

### M5: Rakip modeli (önsel ve gözlem) · Faz C · M

- **Görevler:** `OpponentPrior` (lobi dağılımı, bilinen k rakipten diğerleri); `ObservedOpponentState` (kayıtlardan); `PoolBelief` birleştirme kuralları ve eskime modeli (bölüm 8.3); rekabet etkisi ölçümü.
- **Teknik kabul:** Test lobilerinde k = 1..4 için log-loss marjinal baseline'ı geçer; rekabet etkisi güven aralığıyla; havuz hesabında her girdinin kaynağı izlenebilir.
- **Hedefe katkı:** Kayıtlarında bir rakibin gerçekten görüldüğü anlarda, `PoolBelief`'in o rakibin sonraki gözleminde görülen birimlerle ne kadar uyumlu olduğu ölçülür (eskime modelinin testi). Pivot kararlarının rekabet bilgisine duyarlılığı raporlanır.

### M6: Makro simülatör ve güvenilirlik haritası · Faz C · L

- **Görevler:** 8 oyunculu soyut oyun (ekonomi M1, dövüş M4, rakipler M5); HP kaybı modeli [KAYNAK GEREKLİ: mevcut setin oyuncu hasarı kuralları]; rakip politikalarının kalibrasyonu; güvenilirlik haritası.
- **Teknik kabul:** Kalibrasyon hedefleri (arketip payları, level dağılımı, arketip başına ortalama sıralama) toplam varyasyon mesafesi ≤ 0,1 [HEDEF]; kalibrasyonda kullanılmayan istatistikler raporlanır; tüm çıktılar "simulated" etiketli.
- **Hedefe katkı: güvenilirlik haritası.** Her karar tipi (roll/level zamanı, ekonomi tutma, pivot, augment tipi) için:
  1. **Kalibrasyon dışı tutarlılık:** O karar tipiyle ilgili gerçek istatistikler (ör. arketip başına `last_round` dağılımı) simülasyonda tutuyor mu?
  2. **Kayıtlardaki gidişat:** Test kümesindeki gerçek HP ve altın gidişatı, aynı başlangıç durumundan simüle edilen dağılımın içinde mi?
  3. **Hassasiyet:** Simülatör parametreleri belirsizlik aralığında değişince kararın yönü korunuyor mu?
  4. **Bozulma koşulları:** Hangi aşama, HP ve ekonomi aralıklarında yukarıdakilerden biri bozuluyor?

  Sonuç her karar tipi için **güvenilir / şartlı (hangi koşullarda) / güvenilmez** olarak yazılır. M7, güvenilmez olarak işaretlenen karar tipleri için öneri vermez; sadece mekanik ve veriden gelen çıktıları gösterir.

### M7: Arama tabanlı karar motoru · Faz D · L

- **Görevler:** P2'nin aday ve değerlendirme katmanını aramayla genişletmek (beam + sınırlı lookahead, CRN, önbellek, uyarlanabilir bütçe); baseline politikalar (sabit level eğrisi, "50'ye ekonomi", "her zaman en güçlü arketip", P2); MCTS ile karşılaştırma.
- **Teknik kabul:** Sabit senaryolarda beklenen sıralama baseline'lardan anlamlı biçimde iyi; parametre değişimlerinde üstünlüğün korunduğu senaryo oranı ≥ %80 [HEDEF]; MCTS ve beam aynı bütçede karşılaştırılmış.
- **Hedefe katkı:** Sadece M6 haritasında "güvenilir" veya "şartlı" karar tiplerinde öneri verilir. P2'ye göre fark, test kümesi senaryolarında incelenir.

### M8: Derin item ve augment değerlendirmesi · Faz D · M

- **Görevler:** Bileşen fırsat maliyeti (simülasyon); bileşen → item hedefi; savaş ve özel mekanik augment şablonları; tanımlanamayanlar `unknown`.
- **Teknik kabul:** Her şablonun kaynağı ve kapsamı belgeli; augment önerileri tip ve güven sınıfıyla.
- **Hedefe katkı:** Kendi kayıtlarındaki ~60 augment teklifinde motorun sıralaması ile senin seçimin karşılaştırılır (tutarlılık kontrolü, test kümesi ayrı). `unknown` augment oranı raporlanır [HEDEF: oran her yamada azalır].

### M9: Maç sonrası analiz arayüzü · Faz D · M

- **Görevler:** Maç yükleme (API + kayıt); kritik anlarda alternatif kararlar; dışa aktarma. P1'den beri var olan CLI çıktısının olgunlaşmış hali.
- **Teknik kabul:** Tek komutla analiz; her önerinin güven sınıfı, varsayımları ve hesap maliyeti görünür.
- **Hedefe katkı:** Test kümesindeki en az 5 maçın vaka çalışması; her vakada motorun önerisi, senin kararın ve sonuç yan yana.

### Sürekli: yama döngüsü

Her yamada (ayrıntı bölüm 8.6): yama notundaki değişiklikler kaynaklı kayıtlar olarak `patches/<yama>.json` dosyasına girer; M3-M5 yeniden eğitilir; M6 yeniden kalibre edilir ve güvenilirlik haritası yenilenir; regresyon paketi çalışır; P1/P2 senaryoları yeniden koşulur ve değişen kararlar incelenir.

### Opsiyonel

Pozisyonlama için küçük dövüş mikro-simülatörü; makro simülatörde RL (şart: M7'yi simülatör dışı bir ölçütte geçmesi).

---

## 12. Test ve değerlendirme planı

- **Birim testleri:** Her kural fonksiyonu; değerler veri dosyasından.
- **Özellik testleri (hypothesis):** Altın negatif olmaz; havuz korunur; olasılıklar toplamı 1; monotonluk.
- **İstatistiksel testler:** Kesin hesap ve Monte Carlo uyumu; sabit seed; çoklu test düzeltmesi.
- **Gerçek veri testleri:** Senin kayıtlarından tur geçişleri ve shop gözlemleri (güç analiziyle).
- **Altın fikstürler:** Gerçek oyun durumlarından; çıktı değişirse test kırılır ve değişiklik gerekçelendirilir.
- **Regresyon paketi:** Sabit senaryolar, her değişiklikte.
- **Benchmark:** Süre ve bellek, makine bilgisiyle; optimizasyon sadece baseline'a karşı ölçülürse kabul edilir.
- **Kontrollü iyileştirme döngüsü:** Tek değişiklik → aynı senaryolar ve seed'lerde eski ve yeni sürüm → eşleştirilmiş karşılaştırma, güven aralığıyla → sonuç kaydedilir → gerekçeliyse tutulur. Her sürüm git etiketiyle geri alınabilir.
- **Sızıntı önlemleri:** Zaman ve yama bölmesi; aynı maç aynı bölmede; test seti en sonda ve bir kez.
- **Üç güvenilirlik sınıfı** her raporda ayrı: gerçek veriyle doğrulanmış, kesin hesaplanmış, simülasyonla değerlendirilmiş.
- **Dış tutarlılık:** Meta tabloları MetaTFT ve tactics.tools ile elle kıyaslanır.
- **Etiket uyarısı:** Son sıralama, tek tek kararların etiketi olarak kullanılmaz.

---
- **Hedefe katkı ölçümü:** Her milestone, P1/P2 senaryo setinde yeniden koşulur. Değişen kararlar listelenir ve tek tek incelenir. Hassasiyet raporunda "varsayım" sınıfının payı izlenir.
- **Kayıt kümeleri:** Geliştirme kümesi serbestçe kullanılır; test kümesi her kabul için bir kez. Test kümesiyle düzeltilen hatalar rapora yazılır.

---

## 13. Donanım, riskler ve yapılmayacaklar

### 13.1 Donanım

CPU öncelikli (Ryzen 5 4600H, 6 çekirdek/12 iş parçacığı): NumPy ile vektörize Monte Carlo, scikit-learn gradient boosting. Windows `multiprocessing` için az sayıda büyük iş paketi. GPU (GTX 1650) sadece bir benchmark anlamlı fayda gösterirse. Bir yamalık veri (yaklaşık 100 bin maç, 800 bin tahta [HESAP]) 16 GB RAM'de sütun bazlı depolamayla rahat işlenir; M2'de ölçülecek.

### 13.2 En büyük üç teknik risk (güncellendi)

1. **Simülatörün kendi içinde tutarlı ama gerçekte yanlış kararlar üretmesi.** Bu artık en büyük risk. *Azaltma:* Güvenilirlik haritası; güvenilmez karar tiplerinde öneri yok; her önerinin en zayıf güven sınıfını taşıması; kayıtlardaki gerçek gidişatla karşılaştırma.
2. **Erken prototipin varsayımlarının "motorun cevabı" gibi algılanması.** P1 hızlı geri bildirim veriyor ama tahta gücü ve HP kaybı tamamen varsayım. *Azaltma:* Her sayıda güven sınıfı; P1'in kabul kriterleri doğruluk değil, bariz senaryolar ve hassasiyet; P2 ile değişen kararların tek tek incelenmesi.
3. **Rakip bilgisinin olduğundan kesin görünmesi.** Maç sonu verisi rakiplerin oyun içi davranışını göstermiyor. *Azaltma:* Önsel ve gözlem ayrımı, kaynak izleme, eskime modeli, önseldeki geçiş varsayımlarının `assumption` etiketi.

Yakın risk: **Set ve yama hızı.** Set 18'in sete özel shop mekanikleri ve Set 19 geçişi. *Azaltma:* Kurallar veride, doğrulanmamış kural varsayılan olarak kapalı ve uyarılı, Set 19 geçişi ölçülen bir test.

### 13.3 Şimdilik yapılmayacaklar

- Gerçek TFT'yi taklit eden dövüş simülatörü, birime özel yetenekler.
- RL, MuZero, self-play.
- Analiz sitelerinden otomatik veri çekme (yazılı izin olmadan).
- Augment istatistiklerini toplu kaynaklardan yeniden oluşturmak veya kamuya augment istatistiği sunmak.
- Canlı oyun verisi, overlay, oyun sırasında ekran okuma, istemci entegrasyonu; P1'i maç sırasında kullanmaya yönelik hızlı giriş akışı.
- Bireysel oyuncu beceri veya MMR modeli.
- Set 18 verisiyle M4 ve sonrasını eğitmek.
- Sinir ağları ve GPU kodu, web uygulaması, veritabanı sunucusu, bulut eğitimi.

---

## 14. Senin kararın gerekenler

1. **v0.4 uygun mu?** Onaylarsan G0 ile M0'a paralel başlarım. M0 → M1a → P1 en kısa yol.
2. **Kod nerede duracak?** Önerim: GitHub'da yeni bir repo. Bunun için GitHub hesabını bağlaman gerekiyor. Alternatif: bilgisayarındaki bir klasör.
3. **Uzman etiketleri:** P1 için en az 20 senaryoda "ben burada şunu yapardım, şu kadar eminim" diye etiket verebilir misin? Senaryoları ben hazırlarım; bir kısmı senin kayıtlarından gelir.
4. **Maç kayıtları:** Set 18 bitmeden 10-20 ranked maçı videoya kaydedip kısa bir form doldurabilir misin?
5. **Riot API:** Ürün kaydı yapıp kişisel anahtar almaya istekli misin? Metni ben hazırlarım (G0).
6. **Bölge ve ligin:** Hangi sunucuda oynuyorsun ve hangi ligdesin? Varsayılanım TR/EUW; ligin M4'teki doğrulama dilimini belirler.

---

## Kaynaklar

- Riot TFT geliştirici politikası: https://support-developer.riotgames.com/hc/en-us/articles/22698732381587-Teamfight-Tactics
- Riot genel geliştirici politikası: https://developer.riotgames.com/policies/general
- Riot Developer Portal, anahtar türleri ve limitler: https://developer.riotgames.com/docs/portal
- Riot DevRel, TFT match history (2019): https://riotgames.com/en/DevRel/new-game-policy-and-tft-match-history
- tft-match-v1 şeması (Riot dokümanı aynası): https://glama.ai/mcp/servers/@chirpon9/riot-docs-mcp/blob/bd23bbcbe155efed4c6774a7dde0bb8020d76191/src/riot_docs/tft-match-v1.md
- riot-watcher TFT MatchApi: https://riot-watcher.readthedocs.io/en/latest/riotwatcher/TeamFightTactics/MatchApi.html
- Hextechdocs: https://hextechdocs.dev/match-history-tft/ · https://hextechdocs.dev/tag/static-data
- Augment'lerin maç geçmişinden kaldırılması: https://x.com/Mortdog/status/1856785428852216007 · https://manifold.markets/Cy/tft-augment-stats-return-before-may · https://dotesports.com/tft/news/mortdog-admits-tfts-ban-on-augment-stats-sites-was-naive-as-riot-changes-course
- Set 18 Enchanted Wilds: https://esports.gg/news/teamfight-tactics/tft-set-18-enchanted-wilds-release-date-champions-traits-and-more/
- TFT 2026 yama takvimi: https://esports.gg/news/teamfight-tactics/tft-patch-schedule-2026/
- MetaTFT (Overwolf): https://www.overwolf.com/app/MetaTFT.com-MetaTFT
- tactics.tools şartları: https://tactics.tools/terms
- OP.GG kullanıcı sözleşmesi: https://op.gg/lol/policies/agreement
- CommunityDragon: https://www.communitydragon.org/
- Riot, GDC "Simulating Teamfight": https://www.gdcvault.com/play/1028851/Machine-Learning-Simulating-Teamfight
- Açık kaynak inceleme raporu: [ACIK_KAYNAK_INCELEME.md](ACIK_KAYNAK_INCELEME.md)
- YouTube kullanım şartları: https://www.youtube.com/static?template=terms
- Kick kullanım şartları (ConductAtlas kopyası): https://conductatlas.com/platform/kick/kick-terms-of-service/prohibition-on-scraping-service-content/
