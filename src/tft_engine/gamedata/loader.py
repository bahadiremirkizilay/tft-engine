"""Load game data for one set and one patch.

Layout on disk::

    data/sets/<set_id>/base.json            set-level parameters (valid from the first patch)
    data/sets/<set_id>/patches/<patch>.json changes introduced by that patch

The data for patch P is the base with every patch file up to and including P
applied in order. Each patch file is a list of explicit changes (parameter,
new value, kind, source), so "what changed in 18.4" is always answerable and
analyses never mix patches by accident.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tft_engine.gamedata.schema import Param, SchemaError

CHANGE_KINDS = ("buff", "nerf", "adjustment", "system", "new", "removed", "correction")

_DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "data" / "sets"


def parse_patch(patch: str) -> tuple[int, ...]:
    """'18.4' -> (18, 4); '18.6b' -> (18, 6, 1). Used only for ordering."""
    parts: list[int] = []
    for piece in patch.lower().split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        letters = "".join(ch for ch in piece if ch.isalpha())
        if not digits:
            raise SchemaError(f"bad patch id {patch!r}")
        parts.append(int(digits))
        if letters:
            parts.append(ord(letters) - ord("a") + 1)
    return tuple(parts)


@dataclass(frozen=True)
class PatchChange:
    patch: str
    param: str
    new: dict[str, Any] | None  # full Param dict, or None when removed
    kind: str
    source: str
    note: str = ""


@dataclass
class GameData:
    set_id: str
    patch: str
    params: dict[str, Param]
    shop_rules: dict[str, Param]
    changes: list[PatchChange] = field(default_factory=list)
    # Review state of each applied patch file, e.g. {"18.4": "not_reviewed"}.
    patch_status: dict[str, str] = field(default_factory=dict)

    @property
    def unreviewed_patches(self) -> list[str]:
        return [p for p, s in self.patch_status.items() if s != "reviewed"]

    def param(self, name: str) -> Param:
        try:
            return self.params[name]
        except KeyError:
            raise SchemaError(f"no parameter {name!r} in set {self.set_id} {self.patch}") from None

    def get(self, name: str) -> Any:
        return self.param(name).get()

    def changes_in(self, patch: str) -> list[PatchChange]:
        return [c for c in self.changes if c.patch == patch]

    def provenance_report(self) -> dict[str, list[str]]:
        """Parameter names grouped by trust status."""
        report: dict[str, list[str]] = {}
        for group in (self.params, self.shop_rules):
            for name, p in group.items():
                report.setdefault(p.status, []).append(name)
        return {k: sorted(v) for k, v in sorted(report.items())}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SchemaError(f"{path}: invalid JSON ({e})") from e


def _parse_params(raw: dict[str, Any], where: str) -> dict[str, Param]:
    if not isinstance(raw, dict):
        raise SchemaError(f"{where}: expected an object")
    return {name: Param.from_dict(f"{where}.{name}", d) for name, d in raw.items()}


def load_gamedata(set_id: str, patch: str, root: Path | None = None) -> GameData:
    root = Path(root) if root else _DEFAULT_ROOT
    set_dir = root / set_id
    base = _read_json(set_dir / "base.json")
    if str(base.get("set")) != set_id:
        raise SchemaError(f"{set_dir}/base.json declares set {base.get('set')!r}")
    first = base.get("valid_from_patch")
    if not first:
        raise SchemaError(f"{set_dir}/base.json needs valid_from_patch")
    target = parse_patch(patch)
    if target < parse_patch(first):
        raise SchemaError(f"patch {patch} is before set {set_id} starts ({first})")

    params = _parse_params(base.get("params", {}), "params")
    shop_rules = _parse_params(base.get("shop_rules", {}), "shop_rules")
    changes: list[PatchChange] = []
    patch_status: dict[str, str] = {}

    patch_files = sorted((set_dir / "patches").glob("*.json"), key=lambda p: parse_patch(p.stem))
    known_patches = {p.stem for p in patch_files}
    if patch != first and patch not in known_patches:
        raise SchemaError(
            f"no data file for patch {patch}; add data/sets/{set_id}/patches/{patch}.json "
            "(it may list zero changes, but its absence means nobody checked that patch)"
        )
    for pf in patch_files:
        if parse_patch(pf.stem) > target:
            break
        doc = _read_json(pf)
        if doc.get("patch") != pf.stem:
            raise SchemaError(f"{pf}: 'patch' field must equal the file name")
        status = doc.get("status")
        if status not in ("reviewed", "not_reviewed"):
            raise SchemaError(f"{pf}: status must be 'reviewed' or 'not_reviewed'")
        patch_status[pf.stem] = status
        for i, ch in enumerate(doc.get("changes", [])):
            where = f"{pf.name} change {i}"
            for key in ("param", "kind", "source"):
                if not ch.get(key):
                    raise SchemaError(f"{where}: missing {key}")
            if ch["kind"] not in CHANGE_KINDS:
                raise SchemaError(f"{where}: kind must be one of {CHANGE_KINDS}")
            group_name, _, name = ch["param"].partition(".")
            group = {"params": params, "shop_rules": shop_rules}.get(group_name)
            if group is None or not name:
                raise SchemaError(f"{where}: param must look like 'params.x' or 'shop_rules.x'")
            new = ch.get("new")
            if new is None:
                group.pop(name, None)
            else:
                group[name] = Param.from_dict(f"{where}.{name}", copy.deepcopy(new))
            changes.append(
                PatchChange(pf.stem, ch["param"], new, ch["kind"], ch["source"], ch.get("note", ""))
            )
    return GameData(set_id, patch, params, shop_rules, changes, patch_status)
