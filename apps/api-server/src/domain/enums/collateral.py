from enum import StrEnum


class CollateralStatus(StrEnum):
    """Where a pledge is in its custody life.

    Stored as a varchar (``native_enum=False``), the same choice ``UserRole`` makes: Python and
    Pydantic reject anything outside this list, but adding a value later needs no ``ALTER TYPE``
    the way ``LoanStatus`` does.

    ``in_custody`` -> ``for_sale`` -> ``sold`` | ``liquidated``
    ``in_custody`` -> ``released``

    ``released``, ``sold`` and ``liquidated`` are terminal. The field is never edited directly —
    ``PUT /collateral-items/{id}`` refuses a status different from the stored one — because each
    move has a precondition that only its own endpoint checks. Writing it freely once let a loan
    officer mark a pledge ``released`` on a loan with its full principal outstanding, walking
    straight past ``_assert_loan_fully_settled``.

    There is no ``returned``. It appeared in the frontend types and in one label, but no endpoint
    ever wrote it — only the demo seed did — and it sat next to the real ``released`` inviting
    exactly the confusion this enum exists to end.
    """

    in_custody = "in_custody"
    for_sale = "for_sale"
    released = "released"
    liquidated = "liquidated"
    sold = "sold"


class CustomerStatus(StrEnum):
    """Whether a customer is offered in the pickers.

    Only visibility. It is deliberately **not** about whether they may borrow again: a customer
    in arrears has to stay visible so they can be collected from, and hiding them to stop new
    lending would hide them from the screen that chases the debt. If "do not lend to this person"
    is ever needed it is a separate flag, not a third value here.

    The column had no validation at all: `status: str = "active"` accepted any string, and the
    web client renders anything that is not exactly `active` as "Archivado" — so a typo from the
    API archived a customer on screen with nothing failing anywhere.
    """

    active = "active"
    archived = "archived"
