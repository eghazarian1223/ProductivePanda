import unittest

from client_app import generating_presence_message, pars_response_from_server
from common.settings import PRESENCE, RESPONSE, ERROR


class TestClient(unittest.TestCase):

    def test_presense(self):
        test_presense_dict = generating_presence_message()
        test_presense_dict['time'] = 1
        self.assertEqual(
            test_presense_dict, {
                'action': PRESENCE, 'time': 1, 'user': {
                    'account_name': 'guest'}})

    def test_pars_response_200(self):
        self.assertEqual(pars_response_from_server(
            {RESPONSE: 200}), '200 : OK')

    def test_pars_response_400(self):
        self.assertEqual(pars_response_from_server(
            {RESPONSE: 400, ERROR: 'Bad request'}), '400 : Bad request')

    def test_pars_response_error(self):
        self.assertRaises(
            ValueError, pars_response_from_server, {
                ERROR: 'Bad request'})


if __name__ == '__main__':
    unittest.main()
