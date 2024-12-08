from enum import Enum

SERVER_PORT_NUMBER = 50000

CLIENT_PORT_NUMBER = 50001

BUFFER_SIZE = 1024

LOCAL_HOST = "127.0.0.1"

class HTTPStatus(int, Enum):
    COMPLETED = 200
    IN_PROGRESS = 202
    NO_MESSAGE = 400
    NOT_FOUND = 404
    UNKNOWN_ERROR = 500