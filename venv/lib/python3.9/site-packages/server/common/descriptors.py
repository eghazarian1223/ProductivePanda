import logging

server_logger = logging.getLogger('server')


class Port:
    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            server_logger.critical(
                f'Попытка запуска сервера с указанием неподходящего порта {value}. Допустимы адреса с 1024 до 65535.')
            exit(1)
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


class Address:
    def __set__(self, instance, value):
        if value != '':
            value_list = value.split('.')

            if len(value_list) != 4:
                server_logger.critical(
                    f'Попытка запуска сервера с указанием неподходящего адреса {value}.')
                exit(1)
            for val in value_list:
                try:
                    val = int(val)
                except ValueError:
                    server_logger.critical(
                        f'Адрес сервера должен состоять из цифр.')
                    exit(1)
                if not 0 <= val <= 255:
                    server_logger.critical(
                        f'Попытка запуска сервера с указанием неподходящего адреса {value}. '
                        f'Значения октетов должны быть от 0 до 255.')
                    exit(1)

        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
