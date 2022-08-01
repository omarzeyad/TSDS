import {AppRegistry} from 'react-native';
import App from './App';
import {name as appName} from './app.json';
import notifee, { EventType } from '@notifee/react-native';

notifee.onBackgroundEvent(async ({ type, detail }) => {
  switch (type) {
    case EventType.DISMISSED:
      console.log('BackgroundEvent: User dismissed notification');
      break;
    case EventType.PRESS:
      console.log('BackgroundEvent: User pressed notification');
      break;
  }
});

AppRegistry.registerComponent(appName, () => App);
