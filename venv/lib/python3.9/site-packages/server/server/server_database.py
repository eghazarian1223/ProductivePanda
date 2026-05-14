import datetime
import os
import threading

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker, aliased
from sqlalchemy.sql import default_comparator


class ServerStorage:
    class Users:
        def __init__(self, username, hash_password):
            self.id = None
            self.username = username
            self.hash_password = hash_password
            self.public_key = None
            self.last_login = datetime.datetime.now()

    class ActiveUsers:
        def __init__(self, user_id, ip_address, port, login_time):
            self.id = None
            self.user_id = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time

    class LoginHistory:
        def __init__(self, username_id, date_time, ip_address, port):
            self.id = None
            self.username_id = username_id
            self.login_time = date_time
            self.ip_address = ip_address
            self.port = port

    class ContactList:
        def __init__(self, username_id, contact_id):
            self.id = None
            self.username_id = username_id
            self.contact_id = contact_id

    # история сообщений
    class MessageHistory:
        def __init__(self, username_id):
            self.id = None
            self.username_id = username_id
            self.number_messages_sent = 0
            self.number_messages_received = 0

    def __init__(self, path, database_lock):
        self.database_lock = database_lock
        # path = os.path.dirname(os.path.realpath(__file__))
        path = os.getcwd()
        filename = f'server_database.db3'
        self.database_engine = create_engine(
            f'sqlite:///{os.path.join(path, filename)}',
            echo=False,
            pool_recycle=7200,
            connect_args={
                'check_same_thread': False})

        self.metadata = MetaData()
        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('username', String, unique=True),
                            Column('hash_password', String),
                            Column('public_key', String),
                            Column('last_login', DateTime)
                            )

        active_users_table = Table(
            'Active_users', self.metadata, Column(
                'id', Integer, primary_key=True), Column(
                'user_id', ForeignKey('Users.id'), unique=True), Column(
                'ip_address', String), Column(
                    'port', Integer), Column(
                        'login_time', DateTime))

        login_history_table = Table(
            'Login_history', self.metadata, Column(
                'id', Integer, primary_key=True), Column(
                'username_id', ForeignKey('Users.id')), Column(
                'login_time', DateTime), Column(
                    'ip_address', String), Column(
                        'port', String))

        contact_list_table = Table(
            'Contact_list', self.metadata, Column(
                'id', Integer, primary_key=True), Column(
                'username_id', ForeignKey('Users.id')), Column(
                'contact_id', ForeignKey('Users.id')))

        message_history_table = Table(
            'Message_history', self.metadata, Column(
                'id', Integer, primary_key=True), Column(
                'username_id', ForeignKey('Users.id')), Column(
                'number_messages_sent', Integer), Column(
                    'number_messages_received', Integer))

        self.metadata.create_all(self.database_engine)

        mapper(self.Users, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, login_history_table)
        mapper(self.ContactList, contact_list_table)
        mapper(self.MessageHistory, message_history_table)

        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Когда устанавливаем соединение, очищаем таблицу активных
        # пользователей
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, username, ip_address, port, key):
        print(username, ip_address, port)

        rez = self.session.query(self.Users).filter_by(username=username)

        # обновляем время последнего входа
        if rez.count():
            user = rez.first()
            user.last_login = datetime.datetime.now()
            if user.public_key != key:
                user.public_key = key
        # Если нет, то создаздаём нового пользователя
        else:
            user = self.Users(username)
            self.session.add(user)
            self.session.commit()
            user_in_history = self.MessageHistory(user.id)
            self.session.add(user_in_history)
            self.session.commit()

        # Создаем запись в таблицу активных пользователей.
        new_active_user = self.ActiveUsers(
            user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)
        self.session.commit()

        history = self.LoginHistory(
            user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)
        self.session.commit()

    # Функция фиксирующая отключение пользователя
    def user_logout(self, username):
        user = self.session.query(
            self.Users).filter_by(
            username=username).first()

        # Удаляем запись из таблицы ActiveUsers
        self.session.query(
            self.ActiveUsers).filter_by(
            user_id=user.id).delete()
        self.session.commit()

    def users_list(self):
        query = self.session.query(
            self.Users.username,
            self.Users.last_login,
        )
        return query.all()

    # Функция возвращает список активных пользователей
    def active_users_list(self):
        with self.database_lock:
            query = self.session.query(
                self.Users.username,
                self.ActiveUsers.ip_address,
                self.ActiveUsers.port,
                self.ActiveUsers.login_time
            ).join(self.Users)

        return query.all()

    # Функция возвращающая историю входов по пользователю или всем
    # пользователям
    def login_history(self, username=None):
        query = self.session.query(self.Users.username,
                                   self.LoginHistory.login_time,
                                   self.LoginHistory.ip_address,
                                   self.LoginHistory.port
                                   ).join(self.Users)

        if username:
            query = query.filter(self.Users.username == username)
        return query.all()

    # Функция возвращает список контактов пользователя
    def contact_list(self, username=None):
        alias1 = aliased(self.Users)
        alias2 = aliased(self.Users)
        query = self.session.query(alias1.username,
                                   alias2.username
                                   ) \
            .select_from(self.ContactList) \
            .join(alias1, alias1.id == self.ContactList.username_id) \
            .join(alias2, alias2.id == self.ContactList.contact_id)

        if username:
            query = query.filter(alias1.username == username)
        return [contact[1] for contact in query.all()]

    # Функция добавляет запись в БД о новом контакте contact_name, для
    # user_name
    def add_contact(self, user_name, contact_name):
        # Получаем id user'а и contact'а
        user_id = self.session.query(
            self.Users).filter_by(
            username=user_name).first().id
        contact_id = self.session.query(
            self.Users).filter_by(
            username=contact_name).first().id
        # Если такая запись уже есть в таблице завершаем работу функции
        if self.session.query(
                self.ContactList).filter_by(
                username_id=user_id).count():
            return
        # если нет то добавляем
        contact = self.ContactList(user_id, contact_id)
        self.session.add(contact)
        self.session.commit()

    # Функция удаляет запись из БД о контакте contact_name, для user_name
    def delete_contact(self, user_name, contact_name):
        # Получаем id user'а и contact'а
        user_id = self.session.query(
            self.Users).filter_by(
            username=user_name).first().id
        contact_id = self.session.query(
            self.Users).filter_by(
            username=contact_name).first().id
        # Проверяем наличие удаляемой записи в таблице
        if self.session.query(
                self.ContactList).filter_by(
                username_id=user_id,
                contact_id=contact_id).count():
            self.session.query(
                self.ContactList).filter_by(
                username_id=user_id,
                contact_id=contact_id).delete()
            self.session.commit()
        else:
            return

    def message_history_add(self, sender, recipient):
        sender_id = self.session.query(
            self.Users).filter_by(
            username=sender).first().id
        recipient_id = self.session.query(
            self.Users).filter_by(
            username=recipient).first().id

        sender_row = self.session.query(
            self.MessageHistory).filter_by(
            username_id=sender_id).first()

        recipient_row = self.session.query(
            self.MessageHistory).filter_by(
            username_id=recipient_id).first()
        if recipient_row:
            recipient_row.number_messages_received += 1
        if sender_row:
            sender_row.number_messages_sent += 1

        self.session.commit()

    def message_history(self):
        query = self.session.query(
            self.Users.username,
            self.Users.last_login,
            self.MessageHistory.number_messages_sent,
            self.MessageHistory.number_messages_received
        ).join(self.Users)

        return query.all()

    def check_user(self, username):
        if self.session.query(self.Users).filter_by(username=username).count():
            return True
        else:
            return False

    def user_registration(self, username, hash_password):
        user = self.Users(username, hash_password)
        self.session.add(user)
        self.session.commit()
        history = self.MessageHistory(user.id)
        self.session.add(history)
        self.session.commit()

    def get_hash(self, username):
        query = self.session.query(
            self.Users).filter_by(
            username=username).first()
        return query.hash_password

    def get_pubkey(self, username):
        user = self.session.query(
            self.Users).filter_by(
            username=username).first()
        return user.public_key


if __name__ == '__main__':
    test_db = ServerStorage()
    # выполняем 'подключение' пользователя
    test_db.user_login('client_1', '192.168.1.4', 8888)
    test_db.user_login('client_2', '192.168.1.5', 7777)
    # выводим список кортежей - активных пользователей
    print('Список активных пользователей:')
    print(test_db.active_users_list())
    # выполянем 'отключение' пользователя
    test_db.user_logout('client_1')
    # выводим список активных пользователей
    print(test_db.active_users_list())
    # запрашиваем историю входов по пользователю
    print('История входов пользователя client_1:')
    print(test_db.login_history('client_1'))
    # выводим список известных пользователей
    print('Cписок известных пользователей')
    print(test_db.users_list())
    print('Список контактов:')
    print(test_db.contact_list())
    # print(test_db.contact_list('client_2'))
    print('Список контакттов после уделения:')
    print(test_db.delete_contact('client_1', 'client_2'))
    test_db.add_contact('client_1', 'client_2')
    print(test_db.message_history())
