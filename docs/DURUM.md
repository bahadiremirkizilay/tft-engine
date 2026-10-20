# Proje durumu

Son güncelleme: 2026-10-20. Ayrıntılı plan: [PLAN.md](PLAN.md) (v0.4.2).

## Neredeyiz

| Aşama | Durum |
|---|---|
| G0: veri ve politika kapısı | Başlamadı (Riot API kaydı senin onayını bekliyor) |
| M0: proje iskeleti | Bitti |
| M1a: mekanik çekirdek (ekonomi kuralları, shop olasılıkları, yama katmanı) | Bitti |
| P1: ilk karar prototipi | İlk sürüm bitti ([P1_SONUC.md](P1_SONUC.md)). Senin etiketlerinle karşılaştırma bekliyor |
| M1b: Set 18 ayrıntıları ve kayıtlarla doğrulama | Sıradaki. Maç kayıtların gerekiyor |
| M2 ve sonrası | Başlamadı |

## Senden beklenenler (öncelik sırasıyla)

1. **Oyun içi kontroller** (bir maç yeter):
   - seviye 7 shop olasılıkları
   - 8'den 9'a ve 9'dan 10'a geçmek için gereken XP
   - Wisp'li shop'ta 4 şampiyon olup olmadığı
2. **20 etiketli durum** (P1 karşılaştırması): [templates/senaryo_etiketi.md](../templates/senaryo_etiketi.md). Ekran görüntüsü ve "A/B/C/D, eminlik" yeterli.
3. **10-20 kayıtlı ranked maç** (M1b):
   - OBS ile kaydet. Videolar bilgisayarında kalsın, depoya yüklenmez.
   - Her maç için [templates/mac_formu.md](../templates/mac_formu.md) formunu doldur.
   - Bana aşama başlarının (2-1, 3-1, 4-1, 5-1) ve roll yaptığın anların ekran görüntülerini gönder.
4. **Ligin**: tahta gücü doğrulamasında hangi elo dilimine bakılacağını belirler.
5. **Riot API kişisel anahtarı** (G0): kayıt metnini ben hazırlarım, onay senin.

Yayın ve VOD'lar: indirme veya otomatik işleme yapılmaz (YouTube ve Kick şartları). Sadece izlerken alınan elle notlar kullanılır (plan bölüm 6.5).

## Bilinen açıklar

- Set 18 verilerinin çoğu üçüncü taraf kaynaktan ve doğrulanmadı. Liste [README](../README.md#oyun-içinde-doğrulanması-gerekenler-set-18) içinde.
- P1 belirsiz durumlarda altını korumaya yatkın, çünkü satış kuralları bilinmiyor. Ayrıntı [P1_SONUC.md](P1_SONUC.md) içinde.
- 18.2, 18.3 ve 18.4 yama notları henüz işlenmedi.
