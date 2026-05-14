import dis


class ServerVerifier(type):
    def __init__(self, clsname, bases, clsdict):

        methods = []
        attrs = []

        for func in clsdict:
            try:
                instructions = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for instruction in instructions:
                    # print(instruction)
                    if instruction.opname == 'LOAD_METHOD':
                        if instruction.argval not in methods:
                            methods.append(instruction.argval)
                    elif instruction.opname == 'LOAD_ATTR':
                        if instruction.argval not in attrs:
                            attrs.append(instruction.argval)
        # print(methods)
        # print(attrs)

        if 'connect' in methods:
            raise TypeError(
                'Использование метода connect недопустимо в серверном классе')

        if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
            raise TypeError('Некорректная инициализация сокета.')

        super().__init__(clsname, bases, clsdict)


class ClientVerifier(type):
    def __init__(self, clsname, bases, clsdict):
        methods = []
        for func in clsdict:
            try:
                instructions = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for instruction in instructions:
                    # print(instruction)
                    if instruction.opname == 'LOAD_GLOBAL':
                        if instruction.argval not in methods:
                            methods.append(instruction.argval)
        # print(methods)
        for command in ('accept', 'listen', 'socket'):
            if command in methods:
                raise TypeError(
                    'В классе обнаружено использование запрещённого метода')
        if 'receiving_message' in methods or 'send_message' in methods:
            pass
        else:
            raise TypeError(
                'Отсутствуют вызовы функций, работающих с сокетами.')
        super().__init__(clsname, bases, clsdict)
