from common.settings import LOGGING_LEVEL
import logging.handlers
import os
import sys

# sys.path.append('../../')

# os.chdir(os.path.dirname(os.path.abspath(__file__)))
# PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.getcwd()
PATH = os.path.join(PATH, 'log/server.log')


server_log = logging.getLogger('server')
server_log.setLevel(LOGGING_LEVEL)

server_handler = logging.handlers.TimedRotatingFileHandler(
    PATH, encoding='utf_8', interval=1, when='D')

server_format = logging.Formatter(
    "%(asctime)-25s %(levelname)-9s %(filename)-20s %(message)s")
server_handler.setFormatter(server_format)

server_log.addHandler(server_handler)

if __name__ == '__main__':
    server_log.debug('отладочная информация')
    server_log.info('информационное сообщение')
    server_log.warning('предупреждение')
    server_log.error('ошибка')
    server_log.critical('критическая ошибка')
