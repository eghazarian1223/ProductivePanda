import json
import unittest

from common.settings import ENCODING, RESPONSE, ERROR, PRESENCE
from common.utils import send_message, receiving_message


class TestSocket:
    def __init__(self, test_message_dict):
        self.test_message_dict = test_message_dict
        self.test_message_bytes = None
        self.received_message = None

    def send(self, message_to_send):
        test_message_json = json.dumps(self.test_message_dict)
        self.test_message_bytes = test_message_json.encode(ENCODING)
        self.received_message = message_to_send

    def recv(self, max_len):
        test_message_json = json.dumps(self.test_message_dict)
        return test_message_json.encode(ENCODING)


class TestUtils(unittest.TestCase):
    test_message_send = {
        'action': PRESENCE,
        'time': 1,
        'user': {
            'account_name': 'guest__',
        }
    }
    test_message_recv_200 = {RESPONSE: 200}
    test_message_recv_400 = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }

    def test_send_message(self):
        test_socket = TestSocket(self.test_message_send)
        send_message(test_socket, self.test_message_send)
        self.assertEqual(
            test_socket.test_message_bytes,
            test_socket.received_message)
        with self.assertRaises(Exception):
            send_message(test_socket, test_socket)

    def test_get_response(self):
        test_sock_ok = TestSocket(self.test_message_recv_200)
        test_sock_err = TestSocket(self.test_message_recv_400)
        self.assertEqual(
            receiving_message(test_sock_ok),
            self.test_message_recv_200)
        self.assertEqual(
            receiving_message(test_sock_err),
            self.test_message_recv_400)


if __name__ == '__main__':
    unittest.main()
