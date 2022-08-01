import React, { useState, useEffect, } from 'react'
import {
  StatusBar, LogBox,
  Platform, PermissionsAndroid, Alert,
  useColorScheme, ActivityIndicator,
  View, TouchableOpacity, Text,
} from 'react-native'

import notifee, { AndroidCategory, AndroidImportance, AndroidVisibility, EventType } from '@notifee/react-native'

import base64 from 'react-native-base64'
import { BleManager } from 'react-native-ble-plx'

const COLORS = {
  dark: '#222',
  light: '#eee',
  important: '#ff0000',
  btn: '#2196F3'
}

const GP_SERVICE_UUID = '00000001-1000-2000-3000-111122223333'
const IP_CHARACTERISTIC_UUID = '00000002-1000-2000-3000-111122223333'
const LABEL_CHARACTERISTIC_UUID = '00000003-1000-2000-3000-111122223333'

const bleManager = new BleManager()
LogBox.ignoreLogs(['new NativeEventEmitter'])

const App = () => {
  const [isAllPermissionsGranted, setIsAllPermissionsGranted] = useState(false)

  const [isScanning, setIsScanning] = useState(false)
  const [connectedDevice, setConnectedDevice] = useState(null)
  const [isDeviceConnected, setIsDeviceConnected] = useState(false)

  const [ip, setIp] = useState(null)
  const [labels, setLabels] = useState(null)

  const isDarkMode = useColorScheme() === 'dark'
  const viewStyle = { backgroundColor: isDarkMode ? COLORS.dark : COLORS.light }
  const textStyle = { color: isDarkMode ? COLORS.light : COLORS.dark, fontSize: 17 }

  const scanDevices = async () => {
    const bleState = await bleManager.state()
    if (bleState !== 'PoweredOn') {
      Alert.alert('Warning!!!', 'Bluetooth is required to use this app. Turn it ON first!')
      return
    }

    if (!isAllPermissionsGranted) {
      const permissions = await Promise.all([
        PermissionsAndroid.check('android.permission.ACCESS_FINE_LOCATION'),
        PermissionsAndroid.check('android.permission.BLUETOOTH_SCAN'),
        PermissionsAndroid.check('android.permission.BLUETOOTH_CONNECT')
      ])

      if (permissions.includes(false)) {
        Alert.alert('Warning!!!', 'Go to Settings -> Apps -> RpiBleApp. And allow required permissions to continue.')
        return
      }
    }

    let timeoutId = null
    setIsScanning(true)
    console.log('Scanning...')

    bleManager.startDeviceScan(null, null, (error, scannedDevice) => {
      if (error) {
        Alert.alert('ERROR', error.message)
        console.log(error.reason);
        setIsScanning(false)
        return
      }

      if (scannedDevice && scannedDevice.name == 'Rpi') {
        bleManager.stopDeviceScan()
        clearTimeout(timeoutId)
        connectDevice(scannedDevice)
      }
    })

    // stop scanning after 5 seconds
    timeoutId = setTimeout(() => {
      bleManager.stopDeviceScan()
      console.log('Scan completed, Rpi not found!')
      Alert.alert('Connection Failure!', 'Rpi is out of range.')
      setIsScanning(false)
    }, 5000)
  }

  async function displayNotification(body) {
    const channelId = await notifee.createChannel({
      id: 'important',
      name: 'Important Notifications',
      importance: AndroidImportance.HIGH,
      visibility: AndroidVisibility.PUBLIC,
    });

    await notifee.displayNotification({
      id: 'lbl',
      title: 'LABELS:',
      body: body,
      android: {
        channelId,
        category: AndroidCategory.SERVICE,
        importance: AndroidImportance.HIGH,
        visibility: AndroidVisibility.PUBLIC,
        showTimestamp: true,
        fullScreenAction: {
          id: 'default',
        },
        pressAction: {
          id: 'default',
          launchActivity: 'default',
        },
      },
    })
  }

  const connectDevice = async (device) => {
    console.log('Connecting to Device:', device.name)

    device
      .connect({ requestMTU: 75 })
      .then(device => {
        setConnectedDevice(device)
        setIsDeviceConnected(true)
        return device.discoverAllServicesAndCharacteristics()
      })
      .then(device => {
        setIsScanning(false)

        const subscription = bleManager.onDeviceDisconnected(device.id, (err, device) => {
          console.log('Disconnected!')

          bleManager.cancelTransaction('iptransaction');
          bleManager.cancelTransaction('labeltransaction');

          setConnectedDevice(null)
          setIsDeviceConnected(false)
          setIp(null)
          setLabels(null)
          subscription.remove()
        })

        // Read IP
        device
          .readCharacteristicForService(GP_SERVICE_UUID, IP_CHARACTERISTIC_UUID, 'iptransaction')
          .then(characteristic => {
            setIp(base64.decode(characteristic?.value))
            console.log('IP value received:', base64.decode(characteristic?.value))
          })

        // Monitor Label
        device
          .monitorCharacteristicForService(
            GP_SERVICE_UUID,
            LABEL_CHARACTERISTIC_UUID,
            (error, characteristic) => {
              if (characteristic?.value != null) {
                setLabels(base64.decode(characteristic?.value))
                displayNotification(base64.decode(characteristic?.value))
                console.log('Label update received:', base64.decode(characteristic?.value))
              }
            },
            'labeltransaction',
          )

        console.log('Connected!')
      })
      .catch(err => {
        Alert.alert('ERROR!!!', err)
      })
  }

  const disconnectDevice = async () => {
    if (connectedDevice != null) {
      console.log('Disconnecting from Device:', connectedDevice.name + '-' + connectedDevice.id)

      bleManager.cancelTransaction('iptransaction');
      bleManager.cancelTransaction('labeltransaction');
      bleManager.cancelDeviceConnection(connectedDevice.id)
    }
  }

  useEffect(() => {
    if (Platform.OS === 'android') {
      PermissionsAndroid
        .requestMultiple([
          PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
          PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
          PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
        ])
        .then((result) => {
          if (
            result &&
            result['android.permission.ACCESS_FINE_LOCATION'] === 'granted' &&
            result['android.permission.BLUETOOTH_SCAN'] === 'granted'
          ) {
            setIsAllPermissionsGranted(true)
          }
        })
    }

    return notifee.onForegroundEvent(({ type, detail }) => {
      switch (type) {
        case EventType.DISMISSED:
          console.log('ForegroundEvent: User dismissed notification');
          break;
        case EventType.PRESS:
          console.log('ForegroundEvent: User pressed notification');
          break;
      }
    });
  }, [])

  return (
    <View style={{
      ...viewStyle,
      flex: 1,
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <StatusBar
        barStyle={isDarkMode ? 'light-content' : 'dark-content'}
        backgroundColor={isDarkMode ? COLORS.dark : COLORS.light}
        translucent={true}
      />

      <View style={{ paddingBottom: 20, }}>
        <Text style={{
          ...textStyle,
          fontSize: 27,
          fontWeight: 'bold',
        }}>
          Rpi BLE App
        </Text>
      </View>

      {isScanning ? (
        <ActivityIndicator size={'large'} />
      ) : (
        <TouchableOpacity
          style={{
            width: 140,
            height: 40,
            borderRadius: 20,
            backgroundColor: COLORS.btn,
            justifyContent: 'center',
            alignItems: 'center',
          }}
          onPress={() => {
            !isDeviceConnected ? scanDevices() : disconnectDevice()
          }}
        >
          <Text style={{
            fontSize: 17,
            fontWeight: 'bold',
            color: COLORS.light,
          }}>
            {!isDeviceConnected ? 'Connect' : 'Disconnect'}
          </Text>
        </TouchableOpacity>
      )}

      {ip &&
        <View style={{ marginTop: 20, flexDirection: 'row' }}>
          <Text style={{ fontSize: 17, fontStyle: 'italic', color: COLORS.important, }}>IP{'<'}{ip}{'>'}</Text>
        </View>
      }

      {labels &&
        <View style={{ marginTop: 20, alignItems: 'center', borderWidth: 1, borderColor: COLORS.important, padding: 10}}>
          {labels // "Pede."
            .split(', ') // ["Stop", "Speed Limit 50 Km/h"]
            .map((label, index) => (
              <Text key={index} style={{ ...textStyle, fontSize: 18, }}>{label}</Text>
            ))
          }
        </View>
      }
    </View>
  )
}

export default App