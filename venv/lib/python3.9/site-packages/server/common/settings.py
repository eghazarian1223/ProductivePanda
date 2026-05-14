import logging

ENCODING = 'utf-8'

USER = 'user'
PRESENCE = 'presence'
RESPONSE = 'response'
ERROR = 'error'
ACTION = 'action'
TIME = 'time'
ACCOUNT_NAME = 'account_name'
MESSAGE_TEXT = 'message_text'
MESSAGE = 'message'
SENDER = 'sender'
EXIT = 'exit'
DELETE_CONTACT = 'remove'
ADD_CONTACT = 'add'
USERS_REQUEST = 'get_users'
CONTACT_LIST = 'get_contacts'
DATA = 'data'
PUBLIC_KEY = 'pubkey'
REGISTRATION = 'reg'
PASSWORD = 'passwd'
DATA_LIST = 'data_list'
DESTINATION = 'to'
PUBLIC_KEY_REQUEST = 'pubkey_request'

DEFAULT_PORT = 7777
DEFAULT_IP_ADDRESS = '127.0.0.1'

MAX_PACKAGE_LENGTH = 1024

LOGGING_LEVEL = logging.DEBUG

SERVER_DATABASE = 'sqlite:///server_database.db3'

RESPONSE_200 = {RESPONSE: 200}

RESPONSE_202 = {
    RESPONSE: 202,
    'data_list': None
}

RESPONSE_400 = {
    RESPONSE: 400,
    ERROR: None
}

RESPONSE_511 = {
    RESPONSE: 511,
    DATA: None
}
