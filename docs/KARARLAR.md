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
| 2026-10-22 | Borç temizliği: yıldız başına güç tablosu veriden (`star_multipliers.hp`); yıldız kopya tablosu tek yerde; sim politika sayıları 7 yeni `sim_*` varsayımı, tahta gücü sayıları 4 yeni `power_*` varsayımı, item uyumu sınırları `item_fit_weights` içinde (hepsi eski değerleriyle, gerekçe: tahmin); ölü `sim.unit_power` ve yalnız onun kullandığı `sim_item_bonus`, `sim_item_good_fit` silindi; yetenek kayıtlarına durum ve kaynak eklendi | Kural 6 ve 8; ilk tam denetim | Sahip (denetim planı, adım 6) | Hiçbiri: altın çıktılar aynı |
| 2026-10-22 | 18.5 yetenek değerleri (`curated/abilities/18.5.json`, 65 şampiyon, Blitz) tahta gücüne bağlandı; Adaptor formları (Nidalee AD, Gromp AP, diğerleri güçlü form); 16 şampiyon rolü Blitz'e göre düzeltildi (Ashe, Ezreal, Sivir, Varus, Yunara, Cinderling Caster; Azir Marksman; Gnar, Caitlyn, Kayle Specialist; Kennen, Murkwolf Assassin; Rengar Fighter; Rammus, Vi, Yorick Tank); yeni varsayımlar `power_aoe_targets`, `power_line_targets`, `power_conditional_share`, `power_sustain_weight`, `power_adaptor_form` | Yetenek hasarı maliyete göre tahmindi; sahibin Blitz yapıştırmaları, 18.5 notlarıyla tutuyor | Sahip (1. adım planı, 2026-10-22) | `tests/golden/sim_seed3.json`: rol değişikliği item dağıtımını ve tahtaları oynattı (sim 18.4'te, yetenek kaydı yok); 18.4 tahta golden'ı aynı |
| 2026-10-22 | `build_stars` level 8: 4 maliyetliler 1★ yerine 2★ (biten tahta) | Sahip: level 8'de tamamlanmış komp 2★ 4 maliyetli hedefler; şans ve ekonomiye göre maçtan maça değişir | Sahip (2026-10-22) | `tests/golden/board_blossom_8.json`: 4 maliyetliler 2★, tahta ve item sahipleri değişti. 18.5 en güçlü 10 tahtada ana carry 2★ Aphelios oldu |
