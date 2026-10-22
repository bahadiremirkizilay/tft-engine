"""Generated docs: docs/VARSAYIMLAR.md (assumptions) and docs/BAGLANTILAR.md (who uses what).

Both are written from the code and the golden outputs by ``tft-engine audit --write-docs``
and never edited by hand; the docs check reports them when they are out of date.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tft_engine.audit.core import AuditConfig
from tft_engine.audit.wiring import connections

ASSUMPTIONS_DOC = "docs/VARSAYIMLAR.md"
CONNECTIONS_DOC = "docs/BAGLANTILAR.md"
HEADER = (
    "> Bu dosya koddan üretilir: `tft-engine audit --write-docs`. Elle düzenleme; "
    "kaynağı {src}. Güncel değilse denetim hata verir.\n"
)


def _short(value: Any, width: int = 48) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = text.replace("|", "/")
    return text if len(text) <= width else text[: width - 1] + "…"


def p1_flips(root: Path) -> dict[str, list[str]]:
    """Assumption -> P1 scenarios whose best choice changes at its low or high end."""
    out: dict[str, list[str]] = {}
    for path in sorted((root / "tests" / "golden" / "p1").glob("*.json")):
        flips = json.loads(path.read_text(encoding="utf-8")).get("flips", {})
        for name in flips:
            out.setdefault(name, []).append(path.stem)
    return out


def render_assumptions(root: Path) -> str:
    from tft_engine.decision.assumptions import DEFAULTS

    used = connections(root)["assumptions"]
    flips = p1_flips(root)
    varied = sum(a.varied for a in DEFAULTS.values())
    based = sum(bool(a.basis) for a in DEFAULTS.values())
    lines = [
        "# Varsayımlar",
        "",
        HEADER.format(src="`src/tft_engine/decision/assumptions.py` ve `tests/golden/p1/`"),
        "Oyun verisi olmayan her model sayısı burada. Hepsinin güven sınıfı `assumption`: "
        "ölçülmedi, motorun tahmini. Aralıklı olanlar P1'in hassasiyet raporunda iki ucuyla "
        "yeniden hesaplanır.",
        "",
        f"- **{len(DEFAULTS)} varsayım**, {varied} tanesinin aralığı var, "
        f"{based} tanesinin gerekçesi yazılı.",
        f"- P1'de en az bir senaryonun kararını çeviren: **{len(flips)}** varsayım.",
        "",
        "## Kararı en çok çevirenler (P1 senaryoları)",
        "",
        "| Varsayım | Senaryo sayısı | Senaryolar |",
        "|---|---|---|",
    ]
    for name, scen in sorted(flips.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"| `{name}` | {len(scen)} | {', '.join(scen)} |")
    lines += [
        "",
        "## Tam liste",
        "",
        "| Varsayım | Varsayılan | Aralık | Açıklama | Gerekçe | Nasıl doğrulanır | Kullanan |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, a in DEFAULTS.items():
        rng = f"{_short(a.low, 12)} – {_short(a.high, 12)}" if a.varied else "—"
        lines.append(
            f"| `{name}` | {_short(a.default)} | {rng} | {_short(a.description, 90)} | "
            f"{_short(a.basis, 60) or 'yazılmadı'} | {_short(a.validate_by, 60) or '—'} | "
            f"{', '.join(used.get(name, [])) or '—'} |"
        )
    return "\n".join(lines) + "\n"


def render_connections(root: Path, config: AuditConfig) -> str:
    conn = connections(root)
    accepted = config.accept
    lines = [
        "# Bağlantılar",
        "",
        HEADER.format(src="kodun kendisi (`src/`, `tools/`) ve `data/sets/*`"),
        "Bir şeyi değiştirmeden önce buraya bak: o parametreyi, dosyayı ya da modülü kim "
        "kullanıyor? Değişiklikten sonra bu kullananların testleri ve altın çıktıları "
        "kontrol edilir.",
        "",
        "## Veri parametreleri → okuyan kod",
        "",
        "| Parametre | Okuyan | Not |",
        "|---|---|---|",
    ]
    for name, readers in sorted(conn["params"].items()):
        note = accepted.get(f"param:{name}", {}).get("reason", "")
        lines.append(f"| `{name}` | {', '.join(readers) or '—'} | {note} |")
    lines += [
        "",
        "## Curated dosyalar → yükleyen kod",
        "",
        "| Klasör / dosya | Yükleyen | Not |",
        "|---|---|---|",
    ]
    for name, readers in sorted(conn["curated"].items()):
        note = accepted.get(f"curated:{name}", {}).get("reason", "")
        lines.append(f"| `{name}` | {', '.join(readers) or '—'} | {note} |")
    lines += [
        "",
        "## Modüller → kullananlar",
        "",
        "| Modül | Kullanan |",
        "|---|---|",
    ]
    for mod, users in conn["modules"].items():
        if mod.endswith("__main__"):
            continue
        short = [u.removeprefix("tft_engine.") for u in users]
        lines.append(f"| `{mod.removeprefix('tft_engine.')}` | {', '.join(short) or '—'} |")
    lines += [
        "",
        "Kabul edilen istisnalar ve bilinen borçlar: [audit.toml](../audit.toml).",
    ]
    return "\n".join(lines) + "\n"


def generated_docs(root: Path, config: AuditConfig) -> dict[str, str]:
    return {
        ASSUMPTIONS_DOC: render_assumptions(root),
        CONNECTIONS_DOC: render_connections(root, config),
    }


def write_docs(root: Path, config: AuditConfig) -> list[str]:
    written = []
    for rel, text in generated_docs(root, config).items():
        path = root / rel
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(rel)
    return written
