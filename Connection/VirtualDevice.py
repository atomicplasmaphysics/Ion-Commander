from time import sleep
from random import random
from socket import socket


from serial import Serial


class VirtualSerial(Serial):
    """Virtual implementation of Serial with no functionality"""

    def __init__(self):
        sleep(1)
        super().__init__()

    def write(self, data):
        print(f'Virtual Serial: Writing: {data}')
        sleep(0.5)

    def read(self, size: int = 1) -> bytes:
        print('Virtual Serial: Reading')
        sleep(0.5)
        return str(int(random() * 100)).encode('utf-8')

    def readline(self, size: int = -1) -> bytes:
        print('Virtual Serial: Reading line')
        sleep(0.5)
        return str(int(random() * 100)).encode('utf-8')

    def close(self):
        print('Virtual Serial: Closing')
        sleep(0.5)


class VirtualSocket(socket):
    """Virtual implementation of serial with no functionality"""

    def __init__(self):
        sleep(1)
        super().__init__()

    def send(self, data, flags: int = ...) -> int:
        print(f'Virtual Socket: Writing: {data}')
        sleep(0.5)
        return 1

    def recv(self, bufsize: int, flags: int = ...) -> bytes:
        print('Virtual Socket: Reading')
        sleep(0.5)
        return str(int(random() * 100)).encode('utf-8')

    def close(self):
        print('Virtual Socket: Closing')
        sleep(0.5)
