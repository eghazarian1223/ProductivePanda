import argparse
import binascii
import configparser
import hmac
import json
import logging
import os
import select
import sys
import threading
import socket

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

import log.configs.server_log_config
from common.descriptors import Port, Address
from common.metaclasses import ServerVerifier
from common.settings import PRESENCE, RESPONSE, ERROR, ACTION, ACCOUNT_NAME, TIME, MESSAGE, MESSAGE_TEXT, \
    SENDER, USER, RESPONSE_200, RESPONSE_202, RESPONSE_400, ADD_CONTACT, DELETE_CONTACT, CONTACT_LIST, USERS_REQUEST, \
    RESPONSE_511, DATA, PUBLIC_KEY, PASSWORD, DESTINATION, PUBLIC_KEY_REQUEST
from common.utils import receiving_message, send_message
from server.server_database import ServerStorage
from server.server_gui import MainWindow, HistoryWindow, ConfigWindow

server_logger = logging.getLogger('server')
database_lock = threading.Lock()


class Server(threading.Thread, metaclass=ServerVerifier):

    #"""Основной класс сервера. Работает в отдельном потоке."""

    address = Address()
    port = Port()

    def __init__(self, address, port, database):
        self.clients = []
        self.messages = []
        # словарь имя: сокет.
        self.client_names = dict()

        self.listen_sockets = None
        self.error_sockets = None

        self.address = address
        self.port = port
        self.database = database
        super().__init__()

    def run(self):
        """
        Метод основного цикла работы сервера.
        Инициализирует сокет сервера.
        Устанавливает соедение с клиентом.
        Принимает сообщения от клиентов.
        """

        # self.address, self.port = self.arg_parser()

        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_server.bind((self.address, self.port))
        self.socket_server.settimeout(0.5)
        # server_logger.info(f'Установлено соедение с клиентом {self.address}')
        self.socket_server.listen()

        while True:
            try:
                client, client_address = self.socket_server.accept()
            except OSError:
                pass
            else:
                server_logger.info(
                    f'Установлено соедение с клиентом {client_address}')
                self.clients.append(client)

            recv_list = []
            # send_list = []
            # err_list = []

            try:
                if self.clients:
                    recv_list, self.listen_sockets, self.error_sockets = select.select(
                        self.clients, self.clients, [], 0)
            except OSError as err:
                server_logger.error(f'Ошибка работы с сокетами: {err}')
            except ValueError as err:
                server_logger.error(f'Ошибка работы с сокетами: {err}')

            if recv_list:
                for client_with_message in recv_list:
                    # print(client_with_message)
                    try:
                        self.pars_message_from_client(
                            receiving_message(client_with_message), client_with_message)

                    except (OSError, json.JSONDecodeError, TypeError) as err:
                        server_logger.info(
                            f'Клиент {client_with_message.getpeername()} отключился от сервера.',
                            exc_info=err)
                        self.remove_client(client_with_message)

    # @Log()
    @staticmethod
    def arg_parser(default_port, default_address):
        """Парсер аргументов коммандной строки."""

        parser = argparse.ArgumentParser()
        parser.add_argument('-p', default=default_port, type=int, nargs='?')
        parser.add_argument('-a', default=default_address, nargs='?')
        namespace = parser.parse_args(sys.argv[1:])
        listen_addr = namespace.a
        listen_port = namespace.p

        return listen_addr, listen_port

    # @Log()
    # def pars_message_from_client(self, message, messages_list, client,
    # clients, names):
    def pars_message_from_client(self, message, client):
        """
        Метод разбора сообщения от клиента.

        :param message (dict): Сообщение от клиента.
        :param client (str): Имя клиента.
        """

        # global new_connection
        server_logger.debug(f'Разбор сообщения от клиента : {message}')

        if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
                and USER in message:
            users_list = [user[0] for user in self.database.users_list()]
            # print(users_list)
            # если клиента нет в БД (в списке известных пользователей) -
            # регистрируем
            if message[USER][ACCOUNT_NAME] not in users_list:
                with database_lock:
                    self.database.user_registration(
                        message[USER][ACCOUNT_NAME], message[USER][PASSWORD])

            self.authorization(message, client)

        elif ACTION in message and message[ACTION] == MESSAGE and 'to' in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message and self.client_names[message[SENDER]] == client:
            if message['to'] in self.client_names:
                with database_lock:
                    self.database.message_history_add(
                        message[SENDER], message['to'])
                self.send_message_to_client(message)
                try:
                    send_message(client, RESPONSE_200)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                try:
                    send_message(client, response)
                except OSError:
                    pass
            return

        elif ACTION in message and message[ACTION] == 'exit' and ACCOUNT_NAME in message:
            with database_lock:
                self.database.user_logout(message[ACCOUNT_NAME])
            server_logger.info(
                f'Клиент {message[ACCOUNT_NAME]} корректно отключился от сервера.')
            self.clients.remove(self.client_names[message[ACCOUNT_NAME]])
            self.client_names[message[ACCOUNT_NAME]].close()
            del self.client_names[message[ACCOUNT_NAME]]
            # with conflag_lock:
            #     new_connection = True
            # return

        elif ACTION in message and message[ACTION] == MESSAGE and \
                'to' in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            with database_lock:
                self.database.message_history_add(message[SENDER], message['to'])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)
            return

        elif ACTION in message and message[ACTION] == CONTACT_LIST and USER in message:
            # self.client_names[message[USER]] == client:
            response = RESPONSE_202
            with database_lock:
                response['data_list'] = self.database.contact_list(message[USER])
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

        elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message and USER in message:
            # and self.client_names[message[USER]] == client:
            with database_lock:
                self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)

        elif ACTION in message and message[ACTION] == DELETE_CONTACT and ACCOUNT_NAME in message and USER in message:
            # and self.client_names[message[USER]] == client:
            with database_lock:
                self.database.delete_contact(message[USER], message[ACCOUNT_NAME])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)

        elif ACTION in message and message[ACTION] == USERS_REQUEST and ACCOUNT_NAME in message:
            # and self.client_names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            with database_lock:
                response['data_list'] = [user[0]
                                     for user in self.database.users_list()]
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

        elif ACTION in message and message[ACTION] == PUBLIC_KEY_REQUEST and ACCOUNT_NAME in message:
            response = RESPONSE_511
            with database_lock:
                response[DATA] = self.database.get_pubkey(message[ACCOUNT_NAME])
            if response[DATA]:
                try:
                    send_message(client, response)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Нет публичного ключа для данного пользователя'
                try:
                    send_message(client, response)
                except OSError:
                    self.remove_client(client)
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)
            return

    def authorization(self, message, client):
        """
        Метод реализующий авторизацию пользователей.

        :param message (dict): Сообщение с запросом на авторизацию.
        :param client (socket): Сокет клиента.
        """
        with database_lock:
            check_user = self.database.check_user(message[USER][ACCOUNT_NAME])
        if not check_user:
            response = RESPONSE_400
            response[ERROR] = 'Пользователь не зарегистрирован.'
            try:
                server_logger.debug(
                    f'Пользователь не зарегистрирован. {response}')
                send_message(client, response)
            except OSError:
                pass
            self.clients.remove(client)
            client.close()
        elif message[USER][ACCOUNT_NAME] in self.client_names.keys():
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято.'
            try:
                send_message(client, response)
            except OSError:
                server_logger.debug('OS Error')
            self.clients.remove(client)
            client.close()
        else:
            message_auth = RESPONSE_511
            # message_auth[DATA] = os.urandom(64).decode('base-64')
            random_str = binascii.hexlify(os.urandom(64))
            message_auth[DATA] = random_str.decode('ascii')
            # send_message(client, message_auth)

            with database_lock:
                key = self.database.get_hash(
                    message[USER][ACCOUNT_NAME]).encode('ascii')
            hash = hmac.new(key, random_str, 'MD5')
            digest = hash.digest()

            try:
                send_message(client, message_auth)
                response = receiving_message(client)
            except OSError as err:
                server_logger.debug('Ошибка авторизации, data:', exc_info=err)
                client.close()
                return
            client_digest = binascii.a2b_base64(response[DATA])

            # print(response)
            if RESPONSE in response and response[RESPONSE] == 511 and hmac.compare_digest(
                    digest, client_digest):
                self.client_names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                try:
                    send_message(client, RESPONSE_200)
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])

                with database_lock:
                    self.database.user_login(message[USER][ACCOUNT_NAME],
                                         client_ip,
                                         client_port,
                                         message[USER][PUBLIC_KEY])
            else:
                response = RESPONSE_400
                response[ERROR] = 'Неверный пароль.'
                try:
                    send_message(client, response)
                except OSError:
                    pass
                self.clients.remove(client)
                client.close()
            # with conflag_lock:
            #     new_connection = True

    # @Log()
    def send_message_to_client(self, message):
        """
        Метод пересылающий сообщение от одного клиента другому.

        :param message (dict): Сообщение. Содержит информацию об отправителе и получателе, а также само сообщение.
        """
        if message[DESTINATION] in self.client_names and self.client_names[message[DESTINATION]
        ] in self.listen_sockets:
            try:
                send_message(self.client_names[message[DESTINATION]], message)
                server_logger.info(
                    f'Отправлено сообщение пользователю {message[DESTINATION]} от пользователя {message[SENDER]}.')
            except OSError:
                self.remove_client(message[DESTINATION])
        elif message[DESTINATION] in self.client_names and self.client_names[
            message[DESTINATION]] not in self.listen_sockets:
            server_logger.error(
                f'Связь с клиентом {message[DESTINATION]} была потеряна. Соединение закрыто, доставка невозможна.')
            self.remove_client(self.client_names[message[DESTINATION]])
        else:
            server_logger.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, отправка сообщения невозможна.')

    #     if message['to'] in self.client_names and self.client_names[message['to']] in self.listen_sockets:
    #         send_message(self.client_names[message['to']], message)
    #         server_logger.info(f'Отправлено сообщение пользователю {message["to"]} '
    #                            f'от пользователя {message[SENDER]}.')
    #         self.database.add_contact(message[SENDER], message["to"])
    #     elif message['to'] in self.client_names and self.client_names[message['to']] not in self.listen_sockets:
    #         raise ConnectionError
    #     else:
    #         server_logger.error(
    #             f'Пользователь {message["to"]} не зарегистрирован на сервере, '
    #             f'отправка сообщения невозможна.')

    def remove_client(self, client_name):
        """
        Метод отключающий клиента от сервера.

        :param client_name (socket): сокет клиента"""
        server_logger.info(
            f'Клиент {client_name.getpeername()} отключился от сервера.')
        for name in self.client_names:
            if self.client_names[name] == client_name:
                with database_lock:
                    self.database.user_logout(name)
                del self.client_names[name]
                break
        self.clients.remove(client_name)
        client_name.close()


def print_help():
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('contact - список контактов пользователей')
    print('connected - список подключенных пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    config = configparser.ConfigParser()

    # dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.getcwd()
    config_path = os.path.join(dir_path, 'server/server.ini')
    # config.read(f"{dir_path}/{'server.ini'}")
    config.read(config_path)

    # Загрузка параметров командной строки, если нет параметров, то задаём
    # значения по умоланию.
    address, port = Server.arg_parser(
        config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])

    # Инициализация базы данных
    database = ServerStorage(os.path.join(
        config['SETTINGS']['Database_path'],
        config['SETTINGS']['Database_file']),
        database_lock)

    server = Server(address, port, database)
    server.daemon = True
    server.start()

    server_app = QApplication(sys.argv)
    main_window = MainWindow(database)

    # main_window.statusBar().showMessage('Server working')
    # main_window.active_clients_table.setModel(gui_create_model(database))
    # main_window.active_clients_table.resizeColumnsToContents()
    # main_window.active_clients_table.resizeRowsToContents()

    # def list_update():
    #     # global new_connection
    #     # if new_connection:
    #         # main_window.active_clients_table.setModel(
    #         #     gui_create_model(database))
    #     main_window.active_clients_table.resizeColumnsToContents()
    #     main_window.active_clients_table.resizeRowsToContents()
    #         # with conflag_lock:
    #         #     new_connection = False
    #
    # def window_statistics():
    #     global stat_window
    #     stat_window = HistoryWindow(database)
    #     # stat_window.history_table.setModel(create_stat_model(database))
    #     stat_window.history_table.resizeColumnsToContents()
    #     stat_window.history_table.resizeRowsToContents()
    #     stat_window.show()
    #
    # def window_config():
    #     global config_window
    #     # Создаём окно и заносим в него текущие параметры
    #     config_window = ConfigWindow()
    #     config_window.db_path_edit.insert(config['SETTINGS']['Database_path'])
    #     config_window.db_file_edit.insert(config['SETTINGS']['Database_file'])
    #     config_window.port_edit.insert(config['SETTINGS']['Default_port'])
    #     config_window.ip_edit.insert(config['SETTINGS']['Listen_Address'])
    #     config_window.save_button.clicked.connect(save_server_config)
    #
    # def save_server_config():
    #     global config_window
    #     message = QMessageBox()
    #     config['SETTINGS']['Database_path'] = config_window.db_path_edit.text()
    #     config['SETTINGS']['Database_file'] = config_window.db_file_edit.text()
    #     try:
    #         port = int(config_window.port_edit.text())
    #     except ValueError:
    #         message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
    #     else:
    #         config['SETTINGS']['Listen_Address'] = config_window.ip_edit.text()
    #         if 1023 < port < 65536:
    #             config['SETTINGS']['Default_port'] = str(port)
    #             print(port)
    #             with open('server.ini', 'w') as conf:
    #                 config.write(conf)
    #                 message.information(
    #                     config_window, 'OK', 'Настройки успешно сохранены!')
    #         else:
    #             message.warning(
    #                 config_window,
    #                 'Ошибка',
    #                 'Порт должен быть от 1024 до 65536')

    # # Таймер, обновляющий список клиентов 1 раз в секунду
    # timer = QTimer()
    # timer.timeout.connect(list_update)
    # timer.start(1000)

    # # Связываем кнопки с процедурами
    # main_window.refresh_button.triggered.connect(list_update)
    # main_window.show_history_button.triggered.connect(window_statistics)
    # main_window.config_btn.triggered.connect(window_config)

    server_app.exec_()


if __name__ == '__main__':
    main()
