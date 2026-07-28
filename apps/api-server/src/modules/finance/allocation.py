"""How money is spread over the periods a loan owes.

The rule is one sentence long and it is the same everywhere money lands on interest:
**oldest billing period first, and within a period the penalty before the interest.** It
lives here rather than inline at each call site because taking interest at the counter and
taking it out of a foreclosure sale must apply the money identically — two copies of this
loop drifting apart is how the same debt starts reporting two different figures.

The functions here are pure: they decide amounts, never write rows. The caller builds the
``PaymentEvent`` records, because only the caller knows what kind of movement it was.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class AllocationTarget:
    """One billing period that still owes something, as far as allocation cares."""

    interest_charge_id: int
    loan_id: int
    billing_period: str
    outstanding: float
    pending_penalty: float
    overdue: bool
    due_date: date


@dataclass(frozen=True)
class AllocationSlice:
    """What a single period received out of one payment."""

    target: AllocationTarget
    allocated_total: float
    allocated_penalty: float
    allocated_interest: float
    fully_covered: bool


def allocate_oldest_first(
    targets: list[AllocationTarget],
    amount: float,
) -> tuple[list[AllocationSlice], float]:
    """Spread ``amount`` over ``targets`` in the order given, penalty before interest.

    ``targets`` must already be ordered oldest first — the collection endpoints get that
    from ``pending_interest_items_for_customer``, which sorts by due date. Returns the
    slices and whatever could not be applied, which the caller decides what to do with:
    interest collection parks it as an advance, a foreclosure sale keeps it for the house.
    """
    remaining = round(amount, 2)
    slices: list[AllocationSlice] = []

    for target in targets:
        if remaining <= 0:
            break

        allocated_total = round(min(target.outstanding, remaining), 2)
        if allocated_total <= 0:
            continue

        # The penalty is settled before the interest it was charged on, so a partial payment
        # never leaves a period owing only a penalty with the interest already cleared.
        allocated_penalty = round(min(target.pending_penalty, allocated_total), 2)
        allocated_interest = round(max(0.0, allocated_total - allocated_penalty), 2)

        slices.append(
            AllocationSlice(
                target=target,
                allocated_total=allocated_total,
                allocated_penalty=allocated_penalty,
                allocated_interest=allocated_interest,
                fully_covered=allocated_total >= target.outstanding,
            )
        )
        remaining = round(remaining - allocated_total, 2)

    return slices, max(0.0, remaining)
