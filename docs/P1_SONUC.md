# P1 sonuçları: ilk uçtan uca karar prototipi

Tarih: 2026-10-20 · Veri: Set 18, yama 18.4 (doğrulanmamış değerler içeriyor) · Kod: `src/tft_engine/decision/`

## Ne yapıyor

Elle yazılmış bir oyun durumunu (`scenarios/p1/*.json`) alır ve dört tür adayı karşılaştırır:

- **A:** mevcut kompozisyon için mevcut level'da roll.
- **B:** bir sonraki level'a kadar XP al.
- **C:** altını koru.
- **D:** başka bir kompozisyon için roll (pivot).

Augment teklifleri ayrıca sıralanır. Ekonomi ve kaynak tipleri değerlendirilir, diğer tipler "değerlendirilmedi" olarak gösterilir.

Her sayı bir güven sınıfı taşır:

- **Kesin:** ulaşma olasılığı, roll sayısı, karardan sonraki altın. Bunlar shop ve ekonomi kurallarından hesaplanır, ama kullandıkları oyun verisi henüz doğrulanmadı.
- **Varsayım:** tahta gücü, kazanma olasılığı, HP kaybı, elenme riski ve puan.

Hassasiyet raporu, 16 varsayımın her birini aralığının iki ucuna çekip motorun tercihinin değişip değişmediğini gösterir.

Çalıştırma:

```
tft-engine decide scenarios/p1/o1_one_copy_from_3star.json
```

## Kabul kriterleri

| Kriter | Sonuç |
|---|---|
| En az 10 senaryoda çalışır, her çıktı güven sınıfı taşır | 10 senaryo, testle kontrol ediliyor |
| Senaryo başına süre ≤ 10 sn | Bu ortamda en uzunu 0.7 sn (hassasiyet ve augment'ler dahil). Senin makinende ölçülmedi |
| Aynı girdi aynı sonuç; Monte Carlo seed'li | Testle kontrol ediliyor. 3'ten fazla hedefte Monte Carlo kullanılıyor, seed senaryodan türetiliyor |
| Bariz 5 senaryoda doğru taraf | 5/5. o4 (ucuz level) ilk denemede yanlıştı, nedeni aşağıda |
| Senin etiketlediğin ≥ 20 senaryo ile karşılaştırma | **Yapılmadı:** senin etiketlerin gerekiyor |

## Senaryo sonuçları

| Senaryo | Tercih | Beklenen | İkinciyle fark (HP) | Tercihi değiştiren varsayımlar |
|---|---|---|---|---|
| o1 3 yıldız için 1 kopya | A | A | 14.3 | yok |
| o2 erken, vurulacak bir şey yok | C | B veya C | 2.8 | fazla altının değeri, level değeri |
| o3 taşıyıcının bütün kopyaları rakiplerde | C | B veya C | 22.5 | yok |
| o4 ucuz level, altın 50'nin üstünde | B | B | **0.8** | birim gücü, fazla altının değeri, rakip gücü, 2 yıldız çarpanı |
| o5 rekabetsiz alternatife pivot | D | D | 5.4 | komp bonusu, kazanma eğrisi |
| n1 4-1: roll mu level mı | C | etiket yok | 9.6 | yok |
| n2 augment teklifleri | C | etiket yok | 6.6 | yok |
| n3 3 maliyetliden 3 yıldız | C | etiket yok | 5.7 | yok |
| n4 geç oyun, düşük HP | C | etiket yok | 4.1 | 7 varsayım |
| n5 erken, az altın | C | etiket yok | 6.3 | yok |

## Bulgular

1. **Kararı en çok değiştiren varsayımlar** (10 senaryonun toplamı):
   - Tahta gücü formülü (birim gücünün maliyetle artışı, 2 yıldız çarpanı, komp bonusu).
   - Görünmeyen rakiplerin gücü.

   Planın öngördüğü gibi en zayıf halka tahta gücü (M4), ikincisi rakip modeli (M5). Shop modeli varyantları (Wisp, havuz tükenmesi, roll eşiği) bu 10 senaryoda hiçbir tercihi değiştirmedi.
2. **Motor altını korumaya yatkın.** Bariz olmayan 5 senaryonun hepsinde C'yi seçiyor. Bunun bilinen iki nedeni var:
   - Hedef tutmazsa roll'da alınan birimlerin altını kayıp sayılıyor. Kısmi ilerleme ve satış değeri hesaba girmiyor, çünkü satış kuralları henüz bilinmiyor (M1b).
   - Karardan sonra tahta sabit kabul ediliyor. Korunan altının sonradan güce dönüşmesi sadece sabit bir "altın değeri" ile temsil ediliyor.

   Bu yüzden n1'deki "4-1'de roll mu" sorusundaki C tercihi güvenilir değil. Senin etiketlerinle karşılaştırınca ilk bakılacak yer burası.
3. **o4 ilk denemede yanlıştı.** Motor 50 altının üstündeki altını da faiz getiren altınla aynı değerde sayıyordu. Faiz sınırının üstündeki altın artık ayrı ve daha düşük değerleniyor (`excess_gold_value_hp`). Düzeltmeden sonra B seçiliyor, ama fark küçük (0.8 HP). Bu senaryo varsayımlara çok duyarlı.

## Sıradaki adımlar için öneri

- Senden ≥ 20 etiketli senaryo: her senaryoda "ben ne yapardım" (A/B/C/D) yazman yeterli. Geliştirme ve test kümesi ayrı tutulacak.
- M1b'de satış kuralı ve kısmi alımlar eklenmeli. Altın koruma yanlılığının ilk nedeni bu.
- M4'ün (tahta gücü) önceliği hassasiyet sonucuyla doğrulandı.
