import sys
from pybleno import *

import label_characteristic
import ip_characteristic

GP_SERVICE_UUID           = '00000001-1000-2000-3000-111122223333'
IP_CHARACTERISTIC_UUID    = '00000002-1000-2000-3000-111122223333'
LABEL_CHARACTERISTIC_UUID = '00000003-1000-2000-3000-111122223333'

print('----------------------')
print('| Rpi BLE Peripheral |')
print('----------------------')
print('Press <ANY_KEY> to disconnect')

bleno = Bleno()

def onStateChange(state):
    print('on -> stateChange: ' + state)

    if (state == 'poweredOn'):
        bleno.startAdvertising('Rpi', [GP_SERVICE_UUID])
    else:
        bleno.stopAdvertising()
        bleno.disconnect()
        sys.exit(1)


def onAdvertisingStart(error):
    print('on -> advertisingStart: ' +
          ('error ' + error if error else 'success'))

    if not error:
        bleno.setServices([
            BlenoPrimaryService({
                'uuid': GP_SERVICE_UUID,
                'characteristics': [
                    ip_characteristic.IPCharacteristic(IP_CHARACTERISTIC_UUID),
                    label_characteristic.LabelCharacteristic(
                        LABEL_CHARACTERISTIC_UUID)
                ]
            })
        ])


bleno.on('stateChange', onStateChange)
bleno.on('advertisingStart', onAdvertisingStart)
bleno.on('accept', lambda client: print('\non -> accept: ' + client + ' connected'))
bleno.on('disconnect', lambda client: print('on -> disconnect: ' + client + ' disconnected'))

bleno.start()

try:
    input()
except:
    bleno.stopAdvertising()
    bleno.disconnect()

print('\nRpi disconnected...')
sys.exit(1)