from enum import Enum


class LoanType(str, Enum):
    pawn = "pawn"
    personal = "personal"


class LoanStatus(str, Enum):
    active = "active"
    overdue = "overdue"
    defaulted = "defaulted"
    closed = "closed"
