from enum import Enum


class UserRole(str, Enum):
    administrator = "administrator"
    loan_officer = "loan_officer"
    collector = "collector"
