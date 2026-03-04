import React from 'react';
import { StyleSheet, View, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import { API_BASE } from '../api/config';

export default function IndirimliKVScreen() {
  // webViewUrl: API_BASE'den domaine çıkarak /indirimlikurumlar/ adresine git
  // Emülatörde 127.0.0.1 yerine 10.0.2.2 kullanılması gerekebilir, bu API_BASE'de tanımlı olmalı.
  const webViewUrl = API_BASE.replace('/api/mobile', '') + '/indirimlikurumlar/?source=mobile';

  return (
    <SafeAreaView style={styles.container}>
      <WebView 
        source={{ uri: webViewUrl }}
        startInLoadingState={true}
        renderLoading={() => (
          <View style={styles.loading}>
            <ActivityIndicator size="large" color="#2563eb" />
          </View>
        )}
        style={styles.webview}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  webview: {
    flex: 1,
  },
  loading: {
    position: 'absolute',
    height: '100%',
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
});
