"""The demo data may only use states the application knows.

Both status columns are plain varchar, so nothing at the database level stops a writer from
inventing a value — and the seed had invented two. `inactive` for a customer is not a value
the app knows, and the web client renders anything that is not exactly `active` as
"Archivado", so those rows quietly looked archived. `returned` for a pledge outlived the
vocabulary it belonged to.

This reads the seed's own source rather than running it: seeding needs a database and a
fixture that wipes it, and what is being pinned is a claim about the code — that every state
it writes comes from the enum that defines them.
"""

import re
from pathlib import Path

from src.domain.enums.collateral import CollateralStatus, CustomerStatus

SEED = Path(__file__).resolve().parents[1] / "src" / "infrastructure" / "persistence" / "seed.py"


def _source() -> str:
    return SEED.read_text(encoding="utf8")


def test_the_seed_writes_no_literal_status_strings() -> None:
    """`status="something"` in the seed is a value nobody validated."""
    source = "\n".join(
        line for line in _source().split("\n") if not line.strip().startswith("#")
    )

    literals = re.findall(r'status\s*=\s*"([a-z_]+)"', source)
    # The loan and interest-charge statuses have their own enums and paths; the two this
    # guards are the ones that were free text and were got wrong.
    stray = [value for value in literals if value in {"inactive", "returned", "archived", "active"}]

    assert not stray, (
        f"the seed writes {stray} as bare strings; use CustomerStatus / CollateralStatus so a "
        "value the application does not know cannot be created"
    )


def test_every_collateral_state_the_seed_uses_exists() -> None:
    used = set(re.findall(r"CollateralStatus\.(\w+)", _source()))
    known = {member.name for member in CollateralStatus}
    assert used, "the seed should name its collateral states through the enum"
    assert used <= known, f"unknown collateral states: {sorted(used - known)}"


def test_every_customer_state_the_seed_uses_exists() -> None:
    used = set(re.findall(r"CustomerStatus\.(\w+)", _source()))
    known = {member.name for member in CustomerStatus}
    assert used, "the seed should name its customer states through the enum"
    assert used <= known, f"unknown customer states: {sorted(used - known)}"
