import time
import unittest

from common.settings import PRESENCE, RESPONSE, ERROR
from server_app import response_to_client


class TestServer(unittest.TestCase):
    response_error = {RESPONSE: 400, ERROR: 'Bad request'}

    def test_response_to_client_200(self):
        self.assertEqual(response_to_client({
            'action': PRESENCE,
            'time': time.time(),
            'user': {
                'account_name': 'guest',
            }
        }), {RESPONSE: 200})

    def test_response_to_client_not_guest(self):
        self.assertEqual(response_to_client({
            'action': PRESENCE,
            'time': time.time(),
            'user': {
                'account_name': 'guest__',
            }}), self.response_error)

    def test_response_to_client_no_action(self):
        self.assertEqual(response_to_client({
            'time': time.time(),
            'user': {
                'account_name': 'guest',
            }}), self.response_error)

    def test_response_to_client_no_time(self):
        self.assertEqual(response_to_client({
            'action': PRESENCE,
            'user': {
                'account_name': 'guest',
            }}), self.response_error)

    def test_response_to_client_no_user(self):
        self.assertEqual(response_to_client({
            'action': PRESENCE,
            'time': time.time(),
        }), self.response_error)

    def test_response_to_client_not_PRESENSE(self):
        self.assertEqual(response_to_client({
            'action': 123,
            'time': time.time(),
            'user': {
                'account_name': 'guest__',
            }}), self.response_error)


if __name__ == '__main__':
    unittest.main()
