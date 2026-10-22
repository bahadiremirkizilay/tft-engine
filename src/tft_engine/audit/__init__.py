"""Project audit: checks that keep the code, data, assumptions and docs connected.

Each check returns ``Finding`` objects. Accepted exceptions live in ``audit.toml`` at the
repo root, each with a reason; an entry of kind ``debt`` keeps a known problem visible in
the report without failing it. The audit reads files only (and ``git log`` for dates);
it makes no network calls.
"""

from tft_engine.audit.core import AuditConfig, Finding, load_config, run_audit

__all__ = ["AuditConfig", "Finding", "load_config", "run_audit"]
