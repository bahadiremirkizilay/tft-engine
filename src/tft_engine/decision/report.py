"""Plain-text report for one scenario (Turkish labels, for the player)."""

from __future__ import annotations

from tft_engine.decision.evaluate import AugmentRow, Evaluation, SensitivityRow
from tft_engine.decision.scenario import Scenario

TRUST_TR = {"exact": "kesin", "assumption": "varsayım", "data_estimated": "veriden tahmin"}
METRICS_TR = [
    ("p_hit", "Hedefe ulaşma olasılığı", "{:.1%}"),
    ("exp_rolls", "Beklenen roll sayısı", "{:.1f}"),
    ("gold_after_action", "Karardan sonra altın (ortalama)", "{:.1f}"),
    ("levels_gained", "Kazanılan level", "{:.0f}"),
    ("strength_now", "Tahta gücü (sezgisel)", "{:.1f}"),
    ("p_win_next", "Sonraki turu kazanma", "{:.0%}"),
    ("exp_hp_lost", "Ufukta beklenen HP kaybı", "{:.1f}"),
    ("p_elim", "Ufukta elenme riski", "{:.1%}"),
    ("exp_gold_end", "Ufuk sonunda altın", "{:.1f}"),
    ("exp_level_end", "Ufuk sonunda level", "{:.2f}"),
    ("future_hp_loss_per_round", "Ufuktan sonra tur başına HP kaybı", "{:.1f}"),
]


def render(
    sc: Scenario,
    ev: Evaluation,
    sens: list[SensitivityRow] | None = None,
    augs: list[AugmentRow] | None = None,
) -> str:
    out = [f"Senaryo: {sc.id}", f"  {sc.description}", f"  Set {sc.set_id}, yama {sc.patch}", ""]
    out.append("Adaylar (puan: varsayım, HP cinsinden; yüksek olan daha iyi):")
    for rank, c in enumerate(ev.ranked, 1):
        out.append(f"  {rank}. [{c.key}] {c.label}  puan={c.score:.2f}")
        for key, name, fmt in METRICS_TR:
            m = c.metrics.get(key)
            if m is None:
                continue
            out.append(f"       {name}: {fmt.format(m.value)} ({TRUST_TR[m.trust]})")
    for c in ev.candidates:
        if not c.available:
            out.append(f"  -  [{c.key}] {c.label}: yok ({c.reason})")
    best = ev.best
    out += ["", f"Motorun tercihi: [{best.key}] {best.label}"]
    if len(ev.ranked) > 1:
        gap = best.score - ev.ranked[1].score
        out.append(f"  İkinciyle fark: {gap:.2f} HP eşdeğeri" + (" (çok yakın)" if gap < 1 else ""))
    if sc.expected:
        ok = best.key in sc.expected["best_in"]
        out.append(f"  Beklenen: {sc.expected['best_in']} -> {'UYUMLU' if ok else 'UYUMSUZ'}")
    if sc.expert_choice:
        out.append(f"  Senin seçimin: {sc.expert_choice}")
    if augs:
        out += ["", "Augment teklifleri:"]
        for r in augs:
            if r.evaluated:
                out.append(
                    f"  {r.offer_id} ({r.type}): en iyi aday {r.best_candidate}, puan {r.score:.2f}"
                )
            else:
                out.append(f"  {r.offer_id} ({r.type}): değerlendirilmedi")
            for n in r.notes:
                out.append(f"     not: {n}")
    if sens is not None:
        out += ["", "Kararı en çok etkileyen varsayımlar:"]
        moving = [r for r in sens if r.flips or r.regret > 1e-9]
        if not moving:
            out.append("  Hiçbir varsayım kendi aralığında tercihi değiştirmiyor.")
        for r in moving[:3]:
            flip = "tercih DEĞİŞİYOR" if r.flips else "tercih aynı kalıyor"
            out.append(
                f"  {r.name} [{r.low} .. {r.high}]: {flip} ({r.best_low} / {r.best_high}),"
                f" en kötü kayıp {r.regret:.2f} HP  ({r.description})"
            )
    weak = sorted({k for k, s in ev.data_status.items() if s not in ("verified", "observed")})
    out += ["", f"Shop modeli: {ev.shop_model}"]
    for a in ev.shop_assumptions:
        out.append(f"  varsayım: {a}")
    out.append(f"Doğrulanmamış oyun verisi: {', '.join(weak) if weak else 'yok'}")
    if ev.unreviewed_patches:
        out.append(f"Gözden geçirilmemiş yamalar: {', '.join(ev.unreviewed_patches)}")
    out.append("Not: Bu bir araştırma çıktısıdır, doğru karar iddiası değildir.")
    return "\n".join(out)
