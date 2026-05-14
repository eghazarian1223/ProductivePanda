import inspect
import logging
import sys

if 'client' in sys.argv[0]:
    logger = logging.getLogger('client')
else:
    logger = logging.getLogger('server')


def log(func):
    def decorated(*args, **kwargs):
        logger.info(
            f'Функция {func.__name__} вызвана из функции {inspect.stack()[1][3]}, с аргументами {args} {kwargs}',
            stacklevel=2)
        # print(f'Функция {func.__name__} вызвана из функции {inspect.stack()[1][3]}, с аргументами {args} {kwargs}')
        return func(*args, **kwargs)

    return decorated


class Log():
    def __call__(self, func):
        def decorated(*args, **kwargs):
            logger.info(
                f'Функция {func.__name__} вызвана из функции {inspect.stack()[1][3]}, с аргументами {args} {kwargs}',
                stacklevel=2)
            # print(f'Функция {func.__name__} вызвана из функции {inspect.stack()[1][3]}, с аргументами {args} {kwargs}')
            return func(*args, **kwargs)

        return decorated


if __name__ == '__main__':
    @Log()
    def temp(a, b):
        print(a, b)

    def main():
        temp(1, 3)

    main()
