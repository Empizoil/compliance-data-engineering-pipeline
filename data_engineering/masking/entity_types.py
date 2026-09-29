from enum import Enum




class EntityType(str, Enum):
    NAME = "NAME"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    ADDRESS = "ADDRESS"
    ACCOUNT = "ACCOUNT"
    SSN = "SSN"
    DOLLAR_AMOUNT = "DOLLAR_AMOUNT"