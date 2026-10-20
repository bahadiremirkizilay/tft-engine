"""Source registry and patch calendar, with stale-data checks.

Every record in the knowledge base points to one or more ``source_id``s in
``data/sources.json``. A source says where data came from, when it was taken,
which patch the source itself claimed to show, and (for stats sites) which
filters were active. The patch calendar (``data/sets/<set>/calendar.json``)
says when each patch's official notes came out, so a record can be checked
against the patch it is filed under (PLAN v0.5, VERI_KAYNAKLARI section 9).
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tft_engine.gamedata.schema import SchemaError

SOURCE_TYPES = (
    "official_notes",  # Riot patch notes and official articles
    "official_static",  # Data Dragon
    "official_policy",  # Riot developer policies
    "official_api",  # Riot API
    "game_file",  # CommunityDragon exports of game files
    "wiki",
    "stats_site",  # tactics.tools, MetaTFT, op.gg ... (manual notes only)
    "guide_site",  # TFT Academy and similar (manual notes only)
    "community_table",  # third-party odds/xp/pool tables
    "observation",  # the owner's in-game checks
    "player_report",  # something the owner said, not yet checked
)
COLLECTED_BY = ("auto", "manual")
# Sources whose numbers depend on the site's own filters and patch window.
NEEDS_FILTERS = ("stats_site",)
_REPO_DATA = Path(__file__).resolve().parents[3] / "data"


def _date(value: Any, where: str) -> dt.date:
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        raise SchemaError(f"{where}: expected a YYYY-MM-DD date, got {value!r}") from None


@dataclass(frozen=True)
class Source:
    id: str
    type: str
    title: str
    url: str
    retrieved_at: dt.date
    collected_by: str
    site_patch: str | None = None  # the patch the source itself said it showed
    version: str | None = None  # e.g. CommunityDragon "16.20"
    sha256: dict[str, str] = field(default_factory=dict)  # file name -> hash
    filters: dict[str, str] = field(default_factory=dict)
    note: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Source:
        where = f"source {d.get('id')!r}"
        for key in ("id", "type", "title", "url", "retrieved_at", "collected_by"):
            if not d.get(key):
                raise SchemaError(f"{where}: missing {key}")
        if d["type"] not in SOURCE_TYPES:
            raise SchemaError(f"{where}: type must be one of {SOURCE_TYPES}")
        if d["collected_by"] not in COLLECTED_BY:
            raise SchemaError(f"{where}: collected_by must be one of {COLLECTED_BY}")
        if d["type"] in NEEDS_FILTERS and (not d.get("filters") or not d.get("site_patch")):
            raise SchemaError(f"{where}: stats sources need site_patch and filters")
        allowed = set(cls.__dataclass_fields__)
        extra = set(d) - allowed
        if extra:
            raise SchemaError(f"{where}: unknown fields {sorted(extra)}")
        d = dict(d)
        d["retrieved_at"] = _date(d["retrieved_at"], where)
        return cls(**d)


class SourceRegistry:
    def __init__(self, sources: list[Source]) -> None:
        self.by_id: dict[str, Source] = {}
        for s in sources:
            if s.id in self.by_id:
                raise SchemaError(f"duplicate source id {s.id!r}")
            self.by_id[s.id] = s

    def __contains__(self, source_id: str) -> bool:
        return source_id in self.by_id

    def __getitem__(self, source_id: str) -> Source:
        try:
            return self.by_id[source_id]
        except KeyError:
            raise SchemaError(f"unknown source id {source_id!r}; add it to sources.json") from None

    def check_ids(self, ids: list[str], where: str) -> None:
        if not ids:
            raise SchemaError(f"{where}: needs at least one source_id")
        for sid in ids:
            if sid not in self:
                raise SchemaError(f"{where}: unknown source id {sid!r}")


def load_sources(path: Path | None = None) -> SourceRegistry:
    path = Path(path) if path else _REPO_DATA / "sources.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    return SourceRegistry([Source.from_dict(d) for d in doc.get("sources", [])])


@dataclass(frozen=True)
class PatchInfo:
    patch: str
    notes_published: dt.date
    status: str  # "released" or "planned"
    source_id: str


@dataclass
class PatchCalendar:
    set_id: str
    patches: list[PatchInfo]
    # CommunityDragon version folder -> TFT patch, with how we know it.
    cdragon: dict[str, dict[str, str]]

    def __post_init__(self) -> None:
        dates = [p.notes_published for p in self.patches]
        if dates != sorted(dates):
            raise SchemaError(f"{self.set_id} calendar: patches must be in date order")

    def info(self, patch: str) -> PatchInfo:
        for p in self.patches:
            if p.patch == patch:
                return p
        raise SchemaError(f"{self.set_id} calendar has no patch {patch!r}")

    def patch_on(self, day: dt.date) -> tuple[str | None, bool]:
        """Patch that was live on a day, and whether that day is ambiguous.

        We only know when the notes were published, not the exact hour the patch
        went live, so a day equal to a notes date is reported as ambiguous.
        """
        live, ambiguous = None, False
        for p in self.patches:
            if p.status != "released":
                continue
            if p.notes_published <= day:
                live = p.patch
                ambiguous = p.notes_published == day
        return live, ambiguous

    def check_assignment(self, source: Source, patch: str) -> list[str]:
        """Problems with filing data from this source under this patch (empty = fine)."""
        problems: list[str] = []
        if source.site_patch:
            claimed = source.site_patch.rstrip("abcdefghijklmnopqrstuvwxyz")
            if claimed != patch:
                problems.append(
                    f"{source.id}: source says patch {source.site_patch}, filed under {patch}"
                )
            return problems
        live, ambiguous = self.patch_on(source.retrieved_at)
        if live is None:
            problems.append(f"{source.id}: retrieved before the set started")
        elif live != patch:
            problems.append(
                f"{source.id}: retrieved {source.retrieved_at} while {live} was live, "
                f"filed under {patch}"
            )
        elif ambiguous:
            problems.append(f"{source.id}: retrieved on the {patch} notes day; check by hand")
        return problems


def load_calendar(set_id: str, root: Path | None = None) -> PatchCalendar:
    root = Path(root) if root else _REPO_DATA / "sets"
    doc = json.loads((root / set_id / "calendar.json").read_text(encoding="utf-8"))
    if doc.get("set") != set_id:
        raise SchemaError(f"{set_id}/calendar.json declares set {doc.get('set')!r}")
    patches = []
    for d in doc.get("patches", []):
        where = f"{set_id} calendar {d.get('patch')}"
        if d.get("status") not in ("released", "planned"):
            raise SchemaError(f"{where}: status must be 'released' or 'planned'")
        if not d.get("source_id"):
            raise SchemaError(f"{where}: missing source_id")
        patches.append(
            PatchInfo(d["patch"], _date(d["notes_published"], where), d["status"], d["source_id"])
        )
    return PatchCalendar(set_id, patches, doc.get("cdragon_versions", {}))
