# TFT Engine — Veri Kaynakları ve Set 18 Bilgi Temeli: Araştırma Raporu

Tarih: 2026-10-20 · Canlı yama: 18.4b · Erişim tarihi (aksi yazmıyorsa): 2026-10-20
İlgili: [PLAN.md](PLAN.md) (v0.5), [KAYNAKLAR.md](KAYNAKLAR.md). Sahibin kararları bölüm 15'in altında.

**Ön not:** Bu rapor PLAN v0.5'i yeni bulgularla doğruluyor ve eksiklerini kapatıyor. Asıl yeni kısımlar: meta sitelerinin derin incelemesi, erişim ve izin analizi, eski veri koruması.

---

## 1. Mevcut planın değerlendirmesi ve eksikleri

**Belgeler:** PLAN.md (v0.5), PLAN_v0.4.md, KAYNAKLAR.md, ACIK_KAYNAK_INCELEME.md, P1_SONUC.md.

**v0.5'te doğru olan ve korunması gerekenler:**
- Kaynak ve durum etiketli `Param`.
- Yama katmanı.
- Modifier ile tek doğruluk kaynağı (XP 3 altın örneği).
- `generated` / `curated` ayrımı.
- Meta istatistiğinin kurallardan ayrı tutulması.

**Eksikler** (bu araştırmayla ortaya çıktı):

| # | Eksik | Neden önemli |
|---|---|---|
| E1 | Meta verisinin **nasıl** alınacağı belirsiz ("elle"). Erişim ve izin analizi yok | MetaTFT ve tactics.tools için izinli programatik yol yok (bölüm 4). Elle girişin şablonu, maliyeti ve kaydı tanımlanmalı |
| E2 | Kendi meta istatistiğimizi üretme yolu (Riot API) "ertelendi" olarak kaldı | Komp, birim ve item istatistiğinde **izinli tek otomatik yol** bu. Erteleme kararı bilinçli verilmeli |
| E3 | Eski veri koruması yok | Araştırmada en az 5 site, eski seviye 7 tablosunu Set 18 verisi gibi gösteriyordu. Kayıt düzeyinde yama kontrolü şart (bölüm 9) |
| E4 | Dizilim (board) verisinin kaynağı yok | TFT Academy rehberlerinde örnek dizilim var. Elle ve kaynaklı alınabilir |
| E5 | Meta kayıtlarında örneklem ve tanım alanları zayıf | Siteler arası sayılar farklı tanımlarla üretiliyor (op.gg ile tactics.tools'ta aynı komp için 2,73 ve ~4,3) |
| E6 | Kaynak sayfası değişikliğini algılama yok | Elle alınan bir sayfanın yeni yamada değişip değişmediği takip edilmeli |

**Çelişki:** v0.4'teki "çevrimdışı, asla canlı" ilkesi v0.5'te "şimdilik kapsam dışı" olarak yumuşatıldı. Bu brif de canlı kullanımı kapsam dışı tutuyor. Tutarlı.

---

## 2. İncelenen kaynakların envanteri

**Resmi:**
- Riot yama notları 18.1–18.4 (18.5 henüz yok)
- Set özeti
- Data Dragon `16.20.1` TFT dosyaları
- Riot API `tft-match-v1`
- Developer Portal (anahtar türleri)
- Genel politika ve TFT politikası

**Oyun dosyası:**
- CommunityDragon `cdragon/tft/en_us.json` (16.20, 2026-10-19)
- `map22.bin.json` (shop olasılıkları)

**Meta ve rehber:**
- MetaTFT
- tactics.tools
- TFT Academy
- op.gg TFT
- tftactics.gg
- lolchess.gg
- seemeta, tftflow, metabot, topmeta
- Mobalytics, Blitz, Metasrc

**Wiki:** wiki.leagueoflegends.com (TFT:Gold, TFT:Mana, TFT:Enchanted_Wilds), tftenchantedwilds.wiki (Wisp listesi).

**Açık kaynak:**
- academy-library (ISC)
- CDTB (LGPL-3.0)
- tft-scout
- Roll hesaplayıcıları (damian-kim; HenryVu27, MIT)
- Amberstone (Apache-2.0)
- TFT_GOAT

Bağlantılar ve ayrıntılar KAYNAKLAR.md taslağında.

---

## 3. MetaTFT, tactics.tools ve diğer sitelerden gerçekten ne alınabiliyor

İşaretler: ✅ doğrulandı · ⚠️ kısmen veya çelişkili · ❌ yok · ❓ doğrulanamadı

### 3.1 tactics.tools (sayfalar sunucu tarafında üretiliyor, okunabildi)

| Soru | Durum | Kanıt (18.4b, Ranked, Diamond+) |
|---|---|---|
| Komp gücü (oynanma, ortalama sıra, ilk 4, kazanma) | ✅ | /team-compositions: Riftbeast Brambleback & Elder Dragon 0,07 / 3,66 / %65,4 / %19,3; Riftbeast Pebbles & Krug 0,38 / 4,14 / 57,0 / 12,8; Elderwood Kha'Zix & Hecarim 0,26 / 4,24; Elderwood Ezreal 0,35 / 4,31; Sprykin Azir & Rammus 0,42 / 4,33 |
| Komp başına oyun sayısı | ❌ | Komp sayfasında oyun sayısı yok |
| Komp etiketi (oynanış stili) | ✅ | "Level 7 Reroll", "Fast Level 8", "Items Dependent", "Consistent" |
| Kompun çekirdek ve esnek birimleri, item'ları | ✅ | "Core" ve "Flex" bölümleri, birim yanında item |
| Kompta augment | ❓ | Komp listesinde görünmedi |
| Birim başına oyun sayısı | ✅ | Akali sayfası: **135 bin oyun**, ortalama 4,83, ilk 4 %45,0, kazanma %8,58 |
| **Yıldız seviyesine göre sonuç** | ✅ | Akali: 1★ %20,1 (5,45), 2★ %24,1 (5,17), 3★ %55,1 (4,49), 4★ %0,7 (2,70) |
| Item sayısına göre sonuç | ✅ | 0 item %40,8 (5,21) … 3 item %51,1 (4,35) |
| **Birim × item kombinasyonu** | ✅ | Üçlü item: Nashor's + Gunblade + Titan's %26,7, düzeltilmiş sıra 4,66, sıra 4,47. İkili ve üçlü sekmeleri var. Satır başına oyun sayısı yok, sadece oran |
| Item istatistiği ve en çok kullananlar | ✅ | /items: Gargoyle Stoneplate 5,87/8, 4,41, %51,7, %13,1. En çok kullananlar: Rammus, Sejuani … |
| Birim "güçlü/zayıf olduğu" birimler | ⚠️ | Sekme var, nasıl hesaplandığı yazmıyor |
| Augment istatistiği | ❓ | /augments sütunları var (Games, Place, Top4, Win, 2-1/3-2/4-2'de alınma, "Best With"), ama satırlar okunamadı. Riot API'de augment olmadığından kaynak belirsiz |
| Yama, rank, mod filtresi | ✅ | Yama seçici, Diamond+, Ranked; augment sayfasında Single/Pairs/Trios |
| Aşamaya ve oyuncu level'ına göre sonuç | ❌ | Görülmedi |
| Geçmiş yamalar | ⚠️ | Yama seçici ve "Trends" sekmesi var, içerik doğrulanmadı |
| Gelişmiş Explorer | ⚠️ | "Advanced explorer … is available to patrons". Ücretsiz sürümün sınırı yazmıyor |
| Programatik erişim | ❌ | Belgelenmiş API veya dışa aktarma yok |
| Şartlar | ✅ | [tactics.tools/terms](https://tactics.tools/terms) (son güncelleme 2021-08-23). Kazıma, yeniden dağıtım veya ticari kullanım maddesi yok. "Erişimi önceden bildirmeden sonlandırabiliriz" maddesi var. Doğruluk garantisi yok |
| robots.txt | ✅ | Sadece `User-agent: *`, yasak satırı yok |

### 3.2 MetaTFT (sayfalar JavaScript ile üretiliyor, metin okunamadı)

| Soru | Durum | Kanıt |
|---|---|---|
| Sayfa türleri | ✅ | sitemap.xml (~500 URL): /comps, /units, /items, /traits, /augments, /explorer, /trends, /tier-lists, /tables (~50 tablo, ör. /tables/augment-distibutions, /tables/trait-ladder), /pro-comps, /team-builder, /match-history |
| Tur tur veri | ✅ (kaynağı Overwolf uygulaması) | [App rehberi, 2023-08-11](https://ghost.metatft.com/how-to-use-the-metatft-app/): "round-by-round data … your board for each round". Riot API'nin vermediği veriyi kendi kullanıcılarından topluyor |
| Aşamaya göre istatistik | ⚠️ | Rehbere göre "Early Game Comps" aşama başına tur kazanma oranı veriyor. Bu bölüm uygulamaya özel; sitede Patreon'a açık |
| Item istatistiği (aşama başına en iyi kullanan) | ⚠️ | Rehberde anlatılıyor, sayfa okunamadı |
| Augment istatistiği | ⚠️ **çelişkili** | 2023 rehberi: "Due to a recent policy change by Riot, we aren't allowed to display Augment stats any more". 2026'daki [Overwolf sayfası](https://www.overwolf.com/app/MetaTFT.com-MetaTFT) ise "live augment stats" diyor. Hangisinin güncel olduğu doğrulanamadı |
| Komp ve birim sayıları, örneklem | ❓ | Sayfa okunamadı |
| Programatik erişim | ❌ | Belgelenmiş API yok. `api2.metatft.com` gibi alt alan adları için herkese açık belge bulunamadı |
| Şartlar | ❓ | Şartlar sayfası bulunamadı (/terms içeriği boş) |
| robots.txt | ✅ | `Disallow:` boş, yani tarayıcılara tamamen açık. **Bu, veri kullanım izni anlamına gelmez** |

### 3.3 Diğer siteler

| Site | Ne alınabilir | Durum |
|---|---|---|
| **TFT Academy** | Elle yazılmış rehberler. Örnek: [Azir Rammus](https://tftacademy.com/tierlist/comps/set-18-azir-rammus), 18.4b. Son tahta, **dizilim örneği**, erken item önceliği, carry item'ları ve alternatifleri, augment önceliği ("Items > Econ > Combat") ve önerileri, aşama aşama plan ("4-1'de 2★ Azir ve Rammus, sonra 50 altın üstünde yavaş roll"), oynama koşulu ("çok rod ister"), esnek birimler. **Sayısal istatistik yok** | ✅ Komp şablonu ve dizilim için en zengin nitel kaynak. robots.txt sadece /dashboard/ ve /_app/ yollarını yasaklıyor. Şartlar sayfası bulunamadı (404) |
| op.gg TFT | Komp istatistiği (ortalama sıra, 1. olma, ilk 4, seçilme), "son 24 saatte 2.352.688 oyun" | ⚠️ "Kompu tamamlayanlar" tanımı iyimser sonuç veriyor. Şartlar okunamadı |
| tftactics.gg | Tier listesi, oynanış stili | Sayı yok |
| lolchess.gg | — | ❓ Sayfa boş döndü. robots.txt sadece `/search` yolunu yasaklıyor. Şartlar bulunamadı |
| Mobalytics, Blitz, Metasrc | — | ❓ 403 döndü. Metasrc'nin birim istatistikleri arama sonuçlarında 18.3 için görünüyor |
| seemeta, tftflow, metabot, topmeta | Olasılık, havuz, XP tabloları, 18.5 önizlemesi | ⚠️ Bir kısmı eski tablo kopyalıyor |

---

## 4. Teknik erişim, izinler ve sınırlamalar

**Önemli ayrım:** Verinin teknik olarak çekilebilmesi, onu kullanma izni olduğu anlamına gelmez.

| Kaynak | Resmi API | İndirme/dışa aktarma | Ham veri | Otomatik okuma: teknik / izin | Anahtar/giriş | Yerelde saklama | Yeniden dağıtım ve ticari kullanım | Kırılganlık |
|---|---|---|---|---|---|---|---|---|
| Riot yama notları | ❌ | ❌ | ❌ | Mümkün / açık izin yok. Ama ayda 2 sayfa okumak elle yapılabilecek kadar az | — | Not ve özet | Metin kopyalanmaz, değerler ve link | Düşük |
| **Riot API (tft-match-v1)** | ✅ | — | JSON | ✅ / ✅ kayıtlı ürünle | Kişisel anahtar: ürün kaydı, 20/sn ve 100/2dk, herkese açık ürün olamaz. Production: doğrulama, çalışan prototip | ✅ (saklama süresi şartı bu oturumda doğrulanamadı) | Kayıtlı ürün şartı. Para kazanma ancak kayıtla ve ücretsiz katmanla ("free tier", "transformative") | Düşük, sürümlü |
| Data Dragon | ✅ statik dosya | ✅ | JSON | ✅ / ✅ | Yok | ✅ | Riot "Legal Jibber Jabber" | Düşük, ama güncellemesi gecikebiliyor |
| **CommunityDragon** | ❌ (statik dosya sunucusu) | ✅ sürüm klasörleri | JSON + bin.json | ✅ / ⚠️ resmi değil, Riot onaylamıyor | Yok | ✅ | Ticari kullanım belirsiz. Riot varlıkları Riot'a ait | Orta. Hash'ler ve alan adları sette değişebilir |
| tactics.tools | ❌ | ❌ | ❌ | Teknik olarak sayfa okunabiliyor / **izin yok** (şartlarda yasak yok, ama izin de yok; erişimi kesme hakkı var) | Ücretsiz; gelişmiş Explorer Patreon'da | Elle not alınabilir | Yeniden yayın ve ticari kullanım için **yazılı izin şart** | Yüksek (site tasarımı) |
| MetaTFT | ❌ | ❌ | ❌ | Zor (JavaScript) / izin yok, şartlar bulunamadı | Bir kısmı Patreon | Elle not | Yazılı izin şart | Çok yüksek |
| TFT Academy | ❌ | ❌ | ❌ | Mümkün / izin yok | — | Elle, yapılandırılmış not | Rehber metni kopyalanmaz. Kendi cümlelerimizle özet ve link | Orta |
| op.gg, lolchess | ❌ | ❌ | ❌ | / izin yok (OP.GG'nin genel şartları kazımayı yasaklıyor) | — | Elle not | İzin şart | Yüksek |
| Wiki | MediaWiki API ✅ | ✅ | ✅ | ✅ / ✅ (genellikle CC BY-SA; bu wiki için ayrıca kontrol edilmeli) | Yok | ✅ | Atıf ve aynı lisans şartı | Orta |

**Sonuç:**
- **Otomatik ve izinli yollar:**
  - Data Dragon
  - CommunityDragon (resmi değil, ama yaygın kabul görmüş ve sürümlü)
  - Wiki API
  - Riot API, kayıtlı anahtarla
- **Meta siteleri** (MetaTFT, tactics.tools, op.gg, lolchess, TFT Academy):
  - **Sadece elle inceleme ve kendi yapılandırılmış notlarımız**, kaynak linki ve tarihiyle.
  - Otomatik veri için yazılı izin istenebilir. tactics.tools'un e-postası önceki araştırmada bulunmuştu: tactics.tools@gmail.com.

**Riot politikası** (meta kullanımımızı da ilgilendiriyor): "an app can provide metadata on augment statistics as this information is available prior to the game". Yani oyun öncesi statik meta bilgisi sorun değil. Legend ve Legend tabanlı augment kazanma oranları yasak.

**Kaynak ve tarih kaydı:**
- Her alınan veri bir `source_id` taşır. `sources.json` içinde: URL, erişim tarihi, sitenin gösterdiği yama, filtreler (rank, mod), toplayan kişi (elle/otomatik) ve indirilen dosyalar için sha256.
- Elle alınan sayfalar için isteğe bağlı olarak ekran görüntüsü sadece yerelde tutulur (gitignore). Yeniden dağıtılmaz.

---

## 5. Kaynak karşılaştırma tablosu

| Kaynak | Veri türü | Set 18 | Güncellik | Ayrıntı | Programatik | İzin | Güvenilirlik | Güncelleme | Bakım | Motor için kullanım | Açık soru |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Riot yama notları | Değişiklikler | ✅ 18.1–18.4 | Yama günü | Fark | Elle | ✅ | En yüksek | 2 haftada bir | Düşük | Değişiklik kayıtları, çelişki hakemi | 18.5 notu |
| CommunityDragon JSON | Şampiyon, trait, item, augment, Wisp | ✅ | 1 gün | Yüksek (yetenek sayıları hariç) | ✅ | ⚠️ resmi değil | Yüksek (oyun dosyası) | Her LoL sürümü | Orta (hash'ler) | **Ana varlık kaynağı** | Yetenek değerleri, hash adları |
| CommunityDragon bin | Shop olasılıkları vb. | ✅ | 1 gün | Ham | ✅ | ⚠️ | Yüksek | Aynı | Yüksek (format) | Olasılık tablosunun kaynağı | XP ve havuz yok |
| Data Dragon | Ad, maliyet, ikon | ✅ | Gecikebilir | Düşük | ✅ | ✅ | Yüksek | Elle | Düşük | Ad ve maliyet çapraz kontrolü | Augment kapsamı |
| Riot API | Maç sonu tahtaları, item'lar, sıralama | ✅ | Gerçek zamanlı | Yüksek (augment yok) | ✅ | ✅ kayıtla | Yüksek | Sürekli | Orta (veri hattı) | **Kendi meta istatistiğimiz** (ileride) | Saklama şartları, anahtar onayı |
| tactics.tools | Komp, birim, item istatistiği (yıldıza ve item kombinasyonuna göre) | ✅ 18.4b | Saatlik/günlük | Yüksek | ❌ | Elle not | Orta-yüksek (Diamond+, birim başına örneklem gösteriyor) | Sürekli | Elle: yama başına 1–2 saat | Meta kayıtları (elle), çapraz kontrol | Augment sayılarının kaynağı |
| MetaTFT | Komp, item, tur tur (uygulama) | ❓ | ❓ | Yüksek olabilir | ❌ | Elle | ❓ | Sürekli | Yüksek | Elle çapraz kontrol | Augment istatistiği çelişkisi, şartlar |
| TFT Academy | Komp rehberi, dizilim, plan | ✅ 18.4b | Günlük | Nitel, yüksek | ❌ | Elle, kendi cümlemizle | Uzman görüşü | Günlük | Elle: komp başına ~15 dk | **Komp şablonları ve dizilim** | Şartlar |
| op.gg TFT | Komp istatistiği | ✅ | 24 saat | Orta | ❌ | Elle | Yanlı tanım | Sürekli | — | Sadece çapraz kontrol | — |
| Wiki | Kural açıklamaları | ✅ | Değişken | Orta | ✅ API | ✅ (lisans kontrolü) | Orta | Değişken | Düşük | Kural metni, çelişki adayı | Lisans |
| Topluluk tabloları | Olasılık, havuz, XP | ✅ | Değişken | Düşük | — | — | Düşük–orta | — | — | Sadece çapraz kontrol | Eski kopyalar |

**Birbirini doğrulayan kaynaklar:**
- **Mekanik değerler:** Riot notu ↔ CommunityDragon ↔ oyun içi tooltip. Bu bulgu kanıtlandı: seviye 7 çelişkisi oyun dosyası ve resmi 17.1 notuyla çözüldü.
- **Varlık listeleri:** CommunityDragon ↔ Data Dragon ↔ tactics.tools /info.
- **Meta:** tactics.tools ↔ MetaTFT ↔ (ileride) kendi Riot API istatistiğimiz. Tanımlar farklı olduğu için **sıralama uyumu** karşılaştırılır, mutlak sayılar değil.
- **Komp yapısı:** TFT Academy (nitel) ↔ tactics.tools çekirdek ve esnek birimler (nicel).

---

## 6. Set 18 bilgi ve mekanik envanteri

Durum: ✅ kaynaklı · ⚠️ çelişkili veya topluluk · ❌ kaynak yok

**A. Şampiyonlar ve trait'ler**

| Bilgi | Kaynak | Durum |
|---|---|---|
| 65 oynanabilir şampiyon (14/13/14/14/10); Lux'un 9 formu ayrı | CommunityDragon, tactics.tools | ✅ |
| Maliyet, trait, temel istatistik (can, zırh, MR, AD, AS, menzil, mana, başlangıç manası) | CommunityDragon | ✅ |
| Yetenek açıklaması (şablon metin) | CommunityDragon | ✅ |
| Yıldız başına yetenek sayıları | — | ❌ CommunityDragon'da boş. Ham bin dosyası araştırılacak |
| Hedefleme davranışı | Resmi kaynak yok. Tek resmi bilgi: 18.1'de "kontrol etkisinden çıkan birim hedef değiştirmez" | ❌ |
| Trait eşikleri | CommunityDragon `effects[]` | ✅ |
| Trait değerleri | CommunityDragon (adları hash'li) | ⚠️ |
| Havuz kopya sayısı (30/25/18/10/9) | Topluluk | ⚠️ |
| Shop olasılıkları | Oyun dosyası | ✅ |
| Birleştirme kuralı (3 kopya → bir üst yıldız; 4★ var, tactics.tools'ta %0,7 görülüyor) | Genel kural | ⚠️ 4★'ın nasıl oluştuğu doğrulanmalı |
| Havuz tükenmesinin olasılığa etkisi | Bağımsız seçim modeli (mevcut) | ⚠️ Model varsayımı. Kötü şans koruması bilinmiyor |

**B. Item'lar**

| Bilgi | Kaynak | Durum |
|---|---|---|
| Tarifler | CommunityDragon `composition` | ✅ |
| İstatistik ve etkiler | CommunityDragon `effects` + açıklama | ✅ |
| Türler (artifact, radiant, emblem, support, craftable) | tactics.tools kategorileri + CommunityDragon | ✅ |
| Birim × item başarısı | tactics.tools (elle) | ⚠️ |
| Item × yetenek, trait ve augment etkileşimleri | Kural modeli | ❌ Elle modellenecek |

**C. Augment'ler**

| Bilgi | Kaynak | Durum |
|---|---|---|
| Liste, metin, sayısal etkiler | CommunityDragon (592 kayıt, 548'inde etki değeri var) | ✅ |
| Set 18'de aktif olanlar (249: 69 silver / 112 gold / 68 prismatic) | tactics.tools | ⚠️ |
| Tier | CommunityDragon tag'leri hash'li | ⚠️ |
| Aşamalar (2-1, 3-2, 4-2), yeniden çevirme hakkı 1 | Topluluk + oyun dosyası | ✅/⚠️ |
| Aile sınırları (18.5: bir Destiny, bir unique-item) | Resmi olmayan önizleme | ⚠️ |
| Performans istatistiği | Riot API'de yok; siteler belirsiz | ❌ |
| Mekanik etki modeli | Modifier sistemi (B3) | Elle yapılacak |

**D. Ekonomi, XP ve shop**

| Bilgi | Kaynak | Durum |
|---|---|---|
| XP tablosu (2/2/6/10/20/36/56/68/68) | Resmi farklar | ✅ |
| Shop olasılıkları | Oyun dosyası | ✅ |
| Faiz, temel gelir, PvP galibiyeti | Topluluk | ⚠️ |
| Seri altını | Kaynaklar çelişiyor | ⚠️ |
| Satış değeri | Wiki kendi örneğiyle çelişiyor | ⚠️ |
| Sahne hasarı | Kaynaklar çelişiyor | ⚠️ |
| Reroll maliyeti, XP alımı, max level | Resmi kaynak yok | ❌ |
| Wisp, Blossom, Inferno, Riftbeast kuralları | Wiki + resmi notlar | ⚠️ |

**E. Kompozisyon ve meta**

| Bilgi | Kaynak | Durum |
|---|---|---|
| Komp listesi ve istatistiği | tactics.tools (elle) | ✅ |
| Komp yapısı, plan, dizilim | TFT Academy (elle) | ✅ |
| Popülerlik ile performansı ayırma | Oynanma oranı ile ortalama sıra ayrı tutulur; düşük örneklem işaretlenir | Tasarım |
| Rekabet (contest) etkisi | Havuz modeli + rakip sayısı (mevcut motor) | ⚠️ |
| Geçiş yolları | TFT Academy "alternatif komp" bağlantıları | ⚠️ Nitel |

**F. Savaş ve dizilim**
- Tahta: 7×4 yarı tahta (topluluk, ⚠️).
- Mana kuralları: Tank'ın hasardan mana alma oranında çelişki var (⚠️).
- Menzil: CommunityDragon `range` (✅).
- Hedefleme ve hareket: ❌.
- Örnek dizilimler: TFT Academy (✅, elle).
- tactics.tools'un "Strong/Weak against" birim listeleri: rakibe göre ilk sinyal (⚠️, nasıl hesaplandığı bilinmiyor).

---

## 7. Veri şeması ve sürümleme önerisi

v0.5 bölüm 4 geçerli. Eklenecekler:

**Alanlar türe göre** (hepsi her kayıtta zorunlu değil):

| Alan | Varlık (şampiyon, item…) | Kural parametresi | Meta kaydı | Komp şablonu | Doğrulama kaydı |
|---|---|---|---|---|---|
| `set`, `patch` | ✅ | ✅ | ✅ (sitenin gösterdiği yama) | ✅ | ✅ |
| `entity_id` (oyun apiName'i) | ✅ | — | ✅ | ✅ | ✅ |
| `source_ids` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `retrieved_at` | sources.json üzerinden | aynı | ✅ | ✅ | — |
| `last_verified_at` | ✅ | ✅ | — | ✅ (`last_reviewed`) | ✅ |
| `status` (mevcut 7 durum) | ✅ | ✅ | — | ✅ | ✅ |
| `confidence` | — (status yeterli) | — | ✅ (örneklem ve tanım) | ✅ | — |
| `change_reason` | patch kaydında | patch kaydında | — | ✅ | — |
| `filters` (rank, mod, bölge, zaman penceresi) | — | — | ✅ **zorunlu** | — | — |
| `sample` (oyun sayısı veya "gösterilmiyor") | — | — | ✅ **zorunlu** | — | — |
| `metric_definition` | — | — | ✅ **zorunlu** | — | — |

**Örnek meta kaydı** (tactics.tools, elle):
```json
{"kind":"unit_star_dist","entity_id":"DA_18_Akali_AD","source_id":"tactics.tools/units/da_18_akali_ad@2026-10-20",
 "site_patch":"18.4b","filters":{"mode":"ranked","rank":"diamond_plus"},
 "sample":{"games":135000,"exact":false},
 "values":{"1":{"share":0.201,"avg_place":5.45},"2":{"share":0.241,"avg_place":5.17},"3":{"share":0.551,"avg_place":4.49}},
 "metric_definition":"site-defined; avg_place over games where unit on final board",
 "collected_by":"manual","collected_at":"2026-10-20"}
```

**Sürümleme:** Meta kayıtları `curated/meta/<patch>/<kaynak>-<tarih>.json` dosyalarında tutulur, üzerine yazılmaz. Aynı yama içinde birden çok snapshot olabilir (18.4 ve 18.4b ayrı).

---

## 8. Veri işleme mimarisi (alımdan doğrulamaya)

```
[Kaynak] → [Alım] → [Ham] → [Normalize] → [Birleştirme + çelişki] → [Doğrulama] → [Yayın: load_gamedata]

1. Alım
   - Otomatik (sadece tools/, ağ burada): CommunityDragon, Data Dragon, (ileride) Riot API.
     Sürüm klasöründen indirir; sha256 + manifest yazar.
   - Elle: meta siteleri ve rehberler → şablon formu (templates/meta_kaydi.md, komp_sablonu.md)
     → JSON. Her kayıtta URL ve tarih.
2. Ham: data/raw/ (gitignore). Sadece manifest repoya girer.
3. Normalize: importer → generated/<patch>/ (belirlenimli; aynı girdi → aynı bayt).
4. Birleştirme: generated + curated/overrides + patches.
   - Öncelik kuralı: resmi > oyun içi > oyun dosyası > Data Dragon > wiki ve siteler.
   - Farklı değerler `conflicts` alanına yazılır.
5. Doğrulama: şema, referans bütünlüğü, kural testleri, eski veri kontrolü (bölüm 9).
   Başarısız kayıt yayınlanmaz veya `unverified` olarak işaretlenir.
6. Yayın: load_gamedata(set, patch). Çekirdek katmanlar sadece bunu okur.
```

---

## 9. Çelişkili, eksik ve eski veri stratejisi

- **Çelişki:** Kayıt iki değeri kaynaklarıyla birlikte tutar. Hakem sırası: resmi > oyun içi > oyun dosyası. Hakem yoksa durum `unverified`, kullanılan değer seçilir ve gerekçe yazılır (seviye 7'de yapılan gibi). Kullanan her çıktı uyarı taşır.
- **Eksik:** `unknown` + `null`. Kullanılırsa `UnknownMechanicError` (mevcut).
- **Eski veri koruması** (yeni):
  1. Her elle kayıt, **kaynak sayfanın gösterdiği yamayı** (`site_patch`) ve erişim tarihini yazar. Yama göstermeyen sayfa en fazla `third_party_unverified` olabilir.
  2. Yükleyici, istenen yamadan farklı `site_patch` taşıyan meta kaydını **reddeder**. Bilinçli devralma için `carried_from` alanı ve gerekçe gerekir.
  3. **Bilinen değişiklik kontrolü:** Bir değer, resmi notlarda daha sonra değiştiği bilinen eski bir değerle aynıysa (ör. seviye 7 = 16/30/43, XP 7→8 = 60), test "eski kopya şüphesi" uyarısı verir. Bunun için yama kayıtlarındaki `old` değerleri kullanılır.
  4. **Tarih kontrolü:** `retrieved_at`, yamanın çıkış tarihinden önceyse kayıt o yamaya atanamaz.
  5. **CommunityDragon sürüm ↔ yama eşlemesi:** Manifest dosyası içerik tarihini ve yama takvimini karşılaştırır. Uyuşmazlık hata verir.
- **Kaynak değişikliği uyarısı:** Otomatik kaynaklarda yeni sürüm klasörü çıkınca diff raporu üretilir. Elle kaynaklarda yama başına bir "gözden geçir" listesi oluşur (hangi komp ve meta kaydı eski yamaya ait).

---

## 10. Test ve doğrulama planı

v0.5 bölüm 7 geçerli. Eklenenler:

| Test | Ne kontrol eder |
|---|---|
| Eski kopya testi | Bölüm 9 madde 3 |
| Meta kaydı şeması | `filters`, `sample`, `metric_definition`, `site_patch` alanları zorunlu; oranlar 0–1 aralığında; yıldız dağılımı toplamı ≤ 1 |
| Çapraz kaynak testi | tactics.tools'tan elle alınan birim maliyetleri CommunityDragon ile aynı; komp şablonundaki bütün id'ler o yamada var |
| Sıralama uyumu | tactics.tools ve MetaTFT ilk 10 komp sırası (Spearman), yama başına rapor. Eşik değil, gözlem |
| Kural testleri | XP, altın, faiz ve olasılık için mevcut testler + resmi farklardan referans vakalar |
| Modifier testleri | XP 3 altın örneği; augment yokken P1 bit bit aynı |

---

## 11. İlk Set 18 bilgi temelinin oluşturulma sırası

1. **Kaynak kaydı ve importer** (CommunityDragon 16.20 = 18.4, hemen ardından 18.5). Şampiyon, trait, item, augment ve Wisp listeleri.
2. **Ekonomi ve shop'un tamamlanması**, yama kayıtları 18.2–18.5, oyun içi kontrol listesi.
3. **Modifier sistemi** ve ekonomi, XP ve shop augment'leri.
4. **Item ve trait değerleri** (hash çözümü), rol etiketleri.
5. **Meta ve komp katmanı** (elle):
   - tactics.tools'tan ilk 10–15 kompun istatistiği
   - Birim başına yıldız dağılımı ve en iyi item üçlüleri
   - TFT Academy'den komp şablonları ve dizilimler
6. **Savaş ve dizilim arayüzü** (sadece şema).
7. **Yama döngüsü ve Set 19 provası.**

---

## 12. Yeni sete geçiş stratejisi

- **Setten bağımsız:** Kod, şema, importer, modifier dili, doğrulayıcılar, olasılık motoru.
- **Sete özel:** `data/sets/<set>/` (base, patches, generated, curated). Set mekaniği (Wisp gibi) `shop_rules` ve modifier ile ifade edilir. Yeni tür gerekirse test edilen bir kod değişikliği olur.
- **Geçiş adımları:**
  1. PBE'de CommunityDragon `/pbe/` ile importer provası (Set 19 için tahminen Kasım ortası).
  2. `set19/base.json`: oyun dosyasındaki olasılıklar + resmi set notları.
  3. Meta katmanı boş başlar. İlk hafta elle girilir, eski setten hiçbir meta kaydı taşınmaz.
  4. Set 18 verisi silinmez, salt okunur arşiv olur.

---

## 13. Riskler, hukuki ve kullanım kısıtları, bakım maliyeti

| Risk | Etki | Azaltma |
|---|---|---|
| CommunityDragon resmi değil; format veya hash'ler değişebilir | Importer bozulur | Sürümlü indirme, şema testleri, Data Dragon çapraz kontrolü |
| Set 18 yetenek sayıları yok | Savaş ve yetenek modeli eksik kalır | Ham bin araştırması (B4). Bulunamazsa `unknown` |
| Meta siteleri için izin yok | Otomatik meta mümkün değil | Elle not, kendi Riot API istatistiğimiz (ileride) veya yazılı izin |
| Elle meta girişi zaman alıyor | Yama başına ~2–4 saat (tahmin) | Sadece ilk 10–15 komp; yama başına tek snapshot |
| Augment istatistiği yok | Augment değeri sadece kural modeliyle | Güven sınıfı "varsayım"; elle tier listesi sadece etiket olarak |
| Ticari kullanım | Riot kaydı, Riot varlıkları, site verileri | Şimdilik kişisel kullanım. Ticari niyet olursa ayrı hukuk ve izin turu |
| Set 18'in kalan süresi (6 hafta) | Set 18'e özel elle iş boşa gidebilir | Asıl yatırım kod ve şemada; elle meta minimum |
| Canlı kullanım | Riot politikası ve hesap riski | Kapsam dışı (brif bölüm 10) |

**Bakım tahmini:**
- Her yama: importer + diff ~15 dk; yama notu kayıtları ~1 saat; elle meta ve komp ~2–3 saat.
- Set geçişi: 1–2 gün.

---

## 14. Aşamalı yol haritası ve MVP

v0.5 bölüm 8'deki B0–B7 geçerli. Bu raporun eklemeleri:

| Aşama | Ek iş |
|---|---|
| B1 | `sources.json` içine `site_patch`, `filters` ve `collected_by` alanları; eski veri kontrolleri (bölüm 9) |
| B2 | 18.5 notları çıkınca hemen işlenir |
| B5 | Meta kayıt şablonu (`templates/meta_kaydi.md`); tactics.tools birim yıldız dağılımı ve item üçlüleri; TFT Academy dizilimleri; tactics.tools ile MetaTFT sıralama uyumu raporu |
| **Yeni G0′ (S, karar)** | Riot API kişisel anahtarı: kendi meta istatistiğimiz için izinli tek otomatik yol. Kayıt metni ve veri saklama şartlarının okunması. Veri toplamaya başlamaz, sadece karar ve kayıt |

**MVP** (değişmedi, netleşti), tek yama (18.5) için:
- Bütün varlıklar CommunityDragon'dan, kaynaklı
- Ekonomi ve shop tamam
- Modifier sistemi ve ekonomi, XP ve shop augment'leri
- 10–15 komp şablonu (TFT Academy) + meta snapshot'ı (tactics.tools, elle) + eski veri koruması
- Diff aracı

**Ertelenenler:**
- Riot API veri toplama
- ML
- Dövüş simülatörü
- Maç kayıtları
- Canlı kullanım
- Augment performans istatistiği (kaynağı yok)

---

## 15. Başlamadan önce cevaplaman gereken sorular

1. **Commit:** Bugünkü v0.5 belgeleri (PLAN.md, KAYNAKLAR.md, CLAUDE.md, DURUM.md) diskte ama commit edilmedi. Bu raporun eklemeleriyle birlikte commit ve push yapayım mı?
2. **Ticari niyet:** Proje sadece senin kişisel kullanımın için mi, yoksa ileride başkalarına veya ücretli bir ürüne açılabilir mi? Bu, meta sitelerinden alınan notların ve CommunityDragon'un nasıl kullanılabileceğini belirliyor.
3. **Riot API anahtarı (G0′):** Kendi meta istatistiğimiz için kişisel anahtar başvurusu yapmaya istekli misin? Toplama MVP'den sonra başlar.
4. **Yazılı izin:** tactics.tools'a (ve isteğe bağlı MetaTFT'ye) veri kullanımı için izin e-postası taslağı hazırlayayım mı? Gönderme kararı senin.
5. **Meta filtresi:** Meta kayıtları hangi rank diliminden alınsın? Varsayılan Diamond+ (tactics.tools varsayılanı). Senin ligin farklıysa söyle.
6. **Elle iş bütçesi:** Yama başına elle meta ve komp girişine ne kadar zaman ayırabiliriz? Bunu ben mi gireyim, yoksa sen mi kontrol edeceksin?

### Sahibin kararları (2026-10-20)

1. **Commit:** Onaylandı.
2. **Kullanım amacı:** Sadece kişisel kullanım. Hedef, sahibin kendini geliştirmesi ve pro arenada oynayabilmesi. Ticari ürün veya başkalarına açma planı yok. Meta sitelerinden elle alınan notlar sadece kişisel analiz için tutulur, yeniden yayımlanmaz.
3. **Riot API kişisel anahtarı:** Sonra başvurulacak (G0′, MVP'den sonra).
4. **Sitelerden izin e-postası:** Gerek yok. Otomatik veri izinli kaynaklardan (CommunityDragon, Data Dragon, ileride Riot API) gelecek. Meta siteleri sadece elle çapraz kontrol için kullanılır.
5. **Rank filtresi:** Önce Master, Grandmaster ve Challenger. Örneklem azsa Diamond ve Emerald'a genişletilir. Her meta kaydı kullanılan filtreyi yazar.
6. **Yama başına elle iş bütçesi:** Yeni yama gelince karar verilecek. Şimdi odak ilk bilgi temeli (B1–B5).

---

## Net cevap: neler yapabiliriz, neler yapamayız, doğru sıra ne?

**Yapabileceklerimiz** (gerçekçi, izinli, sürdürülebilir):
- Set 18'in **bütün şampiyon, trait, item, augment ve Wisp listesini**, maliyet, trait üyeliği, temel istatistik, tarif, trait eşiği ve augment sayı değerleriyle **otomatik, sürümlü ve kaynaklı** kurmak (CommunityDragon + Data Dragon + resmi notlar).
- Shop olasılıklarını oyun dosyasından, XP'yi resmi notlardan almak. Ekonomi kurallarını test edilebilir ve augment'le değişebilir hale getirmek.
- Augment'lerin ekonomi, XP ve shop etkilerini kurallarla motora bağlamak.
- Komp şablonlarını (birimler, carry'ler, item'lar, augment önerileri, level planı, dizilim) TFT Academy'den, istatistikleri tactics.tools'tan **elle ama yapılandırılmış ve kaynaklı** girmek. Eski veri ve yanlış tanım koruması da bu işin parçası.
- Set 19'a sadece veri değiştirerek geçmek.

**Yapamayacaklarımız** (şu an):
- MetaTFT, tactics.tools veya diğer sitelerden **izinsiz otomatik veri çekmek**. Teknik olarak kısmen mümkün, ama izin yok. tactics.tools erişimi kesme hakkını saklı tutuyor.
- **Augment performans istatistiği** üretmek. Riot API'de augment yok; sitelerin kaynağı belirsiz.
- Set 18 **yetenek sayılarını** garantili almak. CommunityDragon'da boş, ham dosya araştırması sonucu belirsiz.
- Hedefleme ve hareket kurallarını resmi kaynakla modellemek. Yayınlanmış resmi açıklama yok.
- Kendi istatistiğimiz olmadan sitelerin sayılarını birbirine karıştırmak. Tanımları farklı.

**Doğru başlangıç sırası:**
1. Commit (yapıldı).
2. B1: CommunityDragon importer + kaynak kaydı + eski veri korumaları.
3. B2: ekonomi, shop ve 18.5.
4. B3: modifier'lar.
5. B4: item ve trait'ler.
6. B5: elle meta ve komp.
7. Paralel karar: G0′ (Riot API anahtarı), meta için kalıcı otomatik yolun bu olup olmayacağı.
