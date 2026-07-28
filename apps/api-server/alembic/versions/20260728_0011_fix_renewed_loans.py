"""Stop a renewed loan from carrying its principal twice, and move its pledges

`renew_loan` closed the source loan but left its `outstanding_principal` untouched, while
the new loan was created carrying that same amount. `principal-context` reports every loan
that still owes something, so a single 1.000.000 loan renewed once showed the customer owing
2.000.000 — on the collection screen and on the printed customer statement — and the half
sitting on the closed loan could never be collected, because `_resolve_principal_targets`
excludes closed loans. The comment in `principal_context` assumed a closed loan carries no
principal; renewal was what made that untrue.

The pledges had the mirror problem: they stayed pointed at the closed source, so the live
debt had no security recorded against it and the custody report attributed the goods to a
loan nobody was collecting.

This only touches loans that actually were renewed into another one — a source whose
renewal was later deleted keeps its principal, because in that case nothing else carries it.

Revision ID: 20260728_0011
Revises: 20260727_0010
Create Date: 2026-07-28 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260728_0011"
down_revision = "20260727_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Pledges first: once the source principal is zero the loan looks settled, and moving
    # the goods afterwards would leave a window where the debt has no security at all.
    #
    # One hop at a time, until nothing moves: a loan renewed repeatedly leaves a chain
    # (1 -> 2 -> 3), and a single pass would park the pledge on loan 2, which is just as
    # closed as loan 1 was. The loop walks each chain to the loan that is actually alive.
    while True:
        moved = conn.execute(
            text(
                """
                UPDATE collateral_items c
                   SET loan_id = r.id
                  FROM loans r
                 WHERE r.renewal_of = c.loan_id
                   AND c.status = 'in_custody'
                """
            )
        ).rowcount
        if not moved:
            break

    conn.execute(
        text(
            """
            UPDATE loans s
               SET outstanding_principal = 0
              FROM loans r
             WHERE r.renewal_of = s.id
               AND s.status = 'closed'
               AND s.outstanding_principal > 0
            """
        )
    )


def downgrade() -> None:
    # Not reversible: the amount a source carried before renewal is exactly what the new
    # loan was created with, and there is no record of which pledges came from where.
    pass
