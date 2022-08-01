from pybleno import Characteristic
import socket


class IPCharacteristic(Characteristic):
    def __init__(self, uuid):
        Characteristic.__init__(self, {
            'uuid': uuid,
            'properties': ['read'],
            'value': None
          })

        self._value = 'NO_IP'
        self._updateValueCallback = None
          
    def onReadRequest(self, offset, callback):
        try:          
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(('8.8.8.8', 1))
            self._value = sock.getsockname()[0]
        except:
            self._value = 'NO_IP'
            
        print(f'IPCharacteristic -> onReadRequest: ip = {self._value}')
        callback(Characteristic.RESULT_SUCCESS, self._value.encode())