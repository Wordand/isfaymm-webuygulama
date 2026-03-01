import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { View, Text, ActivityIndicator, StyleSheet, StatusBar } from 'react-native';

import AnaScreen         from './src/screens/AnaScreen';
import IndirimliKVScreen from './src/screens/IndirimliKVScreen';
import HesaplamaScreen   from './src/screens/HesaplamaScreen';
import MevzuatScreen     from './src/screens/MevzuatScreen';
import { ENDPOINTS }     from './src/api/config';
import { LOCAL_ORANLAR } from './src/data/fallback';

const Tab = createBottomTabNavigator();

export default function App() {
  const [oranlar, setOranlar] = useState(LOCAL_ORANLAR);
  const [oranTarih, setOranTarih] = useState(null);

  // Başlangıçta güncel oranları çek
  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    fetch(ENDPOINTS.oranlar, { signal: controller.signal })
      .then((r) => r.json())
      .then((data) => {
        setOranlar(data);
        setOranTarih(data.guncelleme_tarihi);
        clearTimeout(timeoutId);
      })
      .catch(() => {
        // İnternet yoksa local fallback kullan — sessizce geç
        console.log("Oranlar yerel fallback'ten yüklendi");
        clearTimeout(timeoutId);
      });
  }, []);

  return (
    <NavigationContainer>
      <StatusBar barStyle="light-content" backgroundColor="#1e2a47" />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarStyle: styles.tabBar,
          tabBarActiveTintColor: '#2563eb', // Daha taze mavi
          tabBarInactiveTintColor: '#94a3b8',
          tabBarLabelStyle: styles.tabLabel,
          tabBarIcon: ({ focused, color, size }) => {
            const icons = {
              'Ana Sayfa':    focused ? 'home' : 'home-outline',
              'İndirimli KV': focused ? 'business' : 'business-outline',
              'Hesaplama':    focused ? 'calculator' : 'calculator-outline',
              'Mevzuat':      focused ? 'library' : 'library-outline',
            };
            return <Ionicons name={icons[route.name]} size={24} color={color} />; // İkonu büyüttük
          },
        })}
      >
        <Tab.Screen name="Ana Sayfa" component={AnaScreen} />
        <Tab.Screen name="İndirimli KV">
          {() => <IndirimliKVScreen oranlar={oranlar} />}
        </Tab.Screen>
        <Tab.Screen name="Hesaplama" component={HesaplamaScreen} />
        <Tab.Screen name="Mevzuat" component={MevzuatScreen} />
      </Tab.Navigator>

      {/* Oran güncelleme tarihi küçük gösterge */}
      {oranTarih && (
        <View style={styles.banner}>
          <Text style={styles.bannerText}>
            📡 Oranlar güncellendi: {oranTarih}
          </Text>
        </View>
      )}
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: '#ffffff',
    borderTopColor: '#f3f4f6',
    borderTopWidth: 1,
    height: 62,
    paddingBottom: 8,
    paddingTop: 4,
  },
  tabLabel: {
    fontSize: 11,
    fontWeight: '600',
  },
  banner: {
    position: 'absolute',
    bottom: 62,
    left: 0,
    right: 0,
    backgroundColor: '#f0fdf4',
    paddingVertical: 4,
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#bbf7d0',
  },
  bannerText: {
    fontSize: 11,
    color: '#16a34a',
    fontWeight: '600',
  },
});
