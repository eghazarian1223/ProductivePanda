import json

from common.settings import ENCODING, MAX_PACKAGE_LENGTH


# Кодирует сообщение в байты и отправляет его
def send_message(socket, message):
    json_message = json.dumps(message)
    message_bytes = json_message.encode(ENCODING)
    socket.send(message_bytes)


# Принимает сообщение в байтах и декодирует его
def receiving_message(socket):
    response_bytes = socket.recv(MAX_PACKAGE_LENGTH)
    if isinstance(response_bytes, bytes):
        response_json = response_bytes.decode(ENCODING)
        response = json.loads(response_json)
        if isinstance(response, dict):
            return response
        raise ValueError
    raise ValueError
