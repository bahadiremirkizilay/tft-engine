# Kararlar ve öğrenimler

Motorun sonuçlarını değiştiren her karar burada bir satır. Amaç: bir varsayım, veri ya da model değişince "neden değişti, kim onayladı, hangi sonuç kaydı" sorusunun cevabı tek yerde olsun.

**Ne zaman satır yazılır:**
- `tests/golden/` altındaki bir dosya değiştiyse (pre-commit bunu ister),
- bir varsayımın varsayılanı ya da aralığı değiştiyse,
- sahibin bir düzeltmesi, oyun içi gözlemi veya kararı işlendiyse,
- bir modelin yaklaşımı değiştiyse (ör. P1'in güç hesabı).

**Satır biçimi:** tarih · ne değişti · neden (kaynak ya da gözlem) · onay (sahip / Claude, plan adımı) · etkilenen kayıtlar (`tests/golden/...`) ve sonuçta ne oynadı.

Ayrıntılı tarihçe: git geçmişi ve [DURUM.md](DURUM.md). Varsayımların tam listesi ve P1'de kararı çevirenler: [VARSAYIMLAR.md](VARSAYIMLAR.md). Kim neyi kullanıyor: [BAGLANTILAR.md](BAGLANTILAR.md).

## Kayıtlar

| Tarih | Ne değişti | Neden | Onay | Etkilenen sonuç |
|---|---|---|---|---|
| 2026-10-22 | Altın çıktılar başladı: 12 P1 senaryosu, sim (tohum 3), Blossom amblemli level 8 tahta | Değişikliklerin sonuçları nasıl oynattığını görünür yapmak (denetim planı, adım 3) | Sahip (denetim planı onayı) | `tests/golden/` ilk kayıt; sonuç değişmedi |
