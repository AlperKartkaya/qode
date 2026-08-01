import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import NumberVerifyScreen from './src/screens/NumberVerifyScreen';
import HomeScreen from './src/screens/HomeScreen';
import AIResultScreen from './src/screens/AIResultScreen';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="NumberVerify">
        <Stack.Screen 
          name="NumberVerify" 
          component={NumberVerifyScreen} 
          options={{ title: 'Login' }}
        />
        <Stack.Screen 
          name="Home" 
          component={HomeScreen} 
          options={{ title: 'Dashboard' }}
        />
        <Stack.Screen 
          name="AIResult" 
          component={AIResultScreen} 
          options={{ title: 'AI Results' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
