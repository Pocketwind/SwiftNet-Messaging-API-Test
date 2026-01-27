from enum import IntEnum

class MessageType(IntEnum):
    JSON = 1
    BINARY = 2
    STRING = 3
    HMAC_JSON = 4
    HMAC_STRING = 5