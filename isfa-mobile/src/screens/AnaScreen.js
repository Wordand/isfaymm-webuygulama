import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function AnaScreen({ navigation }) {
  const menuItems = [
    { id: 'ikv', title: 'İndirimli Kurumlar Vergisi', sub: 'Teşvik belgesi K.V. hesaplama', icon: 'business' },
    { id: 'araclar', title: 'Diğer Hesaplamalar', sub: 'Asgari K.V., Finansman Gideri', icon: 'calculator' },
    { id: 'mevzuat', title: 'Mevzuat & Rehber', sub: '2026 güncel oranlar ve tebliğler', icon: 'library' },
  ];

  const handleNav = (id) => {
    if (id === 'ikv') navigation.navigate('İndirimli KV');
    if (id === 'araclar') navigation.navigate('Hesaplama');
    if (id === 'mevzuat') navigation.navigate('Mevzuat');
  };

  return (
    <ScrollView style={s.container}>
      <View style={s.header}>
        <View style={s.logoCircle}>
          <Text style={s.logoText}>ISFA</Text>
        </View>
        <Text style={s.greeting}>Hoş Geldiniz,</Text>
        <Text style={s.subText}>İş Dünyası için Vergi Çözümleri</Text>
      </View>

      <View style={s.content}>
        <Text style={s.sectionTitle}>Hızlı Erişim</Text>
        <View style={s.grid}>
          {menuItems.map((item, i) => (
            <TouchableOpacity key={i} style={s.card} onPress={() => handleNav(item.id)}>
              <View style={s.iconBox}>
                <Ionicons name={item.icon} size={28} color="#2563eb" />
              </View>
              <Text style={s.cardTitle}>{item.title}</Text>
              <Text style={s.cardSub}>{item.sub}</Text>
              
              <View style={s.cardBottom}>
                <Text style={s.startText}>Başla</Text>
                <Ionicons name="arrow-forward" size={16} color="#3b82f6" />
              </View>
            </TouchableOpacity>
          ))}
        </View>

        <View style={s.infoBox}>
          <Ionicons name="information-circle-outline" size={24} color="#059669" style={{ marginTop: 2 }} />
          <View style={{ flex: 1 }}>
            <Text style={s.infoTitle}>Biliyor muydunuz?</Text>
            <Text style={s.infoText}>
              2025/9903 kararı ile yeni yatırım teşvik sistemi yürürlüğe girdi. Detayları Mevzuat sekmesinden inceleyebilirsiniz.
            </Text>
          </View>
        </View>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  header: {
    backgroundColor: '#1e293b',
    padding: 24, paddingTop: 60, paddingBottom: 40,
    borderBottomLeftRadius: 30, borderBottomRightRadius: 30,
  },
  logoCircle: {
    width: 60, height: 60, borderRadius: 30,
    backgroundColor: '#3b82f6', alignItems: 'center', justifyContent: 'center',
    marginBottom: 20,
  },
  logoText: { color: '#fff', fontSize: 20, fontWeight: '900', letterSpacing: 1 },
  greeting: { fontSize: 28, fontWeight: '800', color: '#f8fafc', marginBottom: 4 },
  subText: { fontSize: 15, color: '#94a3b8', fontWeight: '500' },
  
  content: { padding: 20, paddingTop: 24 },
  sectionTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a', marginBottom: 16 },
  
  grid: { gap: 16 },
  card: {
    backgroundColor: '#fff', padding: 20, borderRadius: 20,
    shadowColor: '#cbd5e1', shadowOpacity: 0.3, shadowRadius: 10, elevation: 3,
  },
  iconBox: {
    width: 54, height: 54, borderRadius: 16, backgroundColor: '#eff6ff',
    alignItems: 'center', justifyContent: 'center', marginBottom: 16,
  },
  cardTitle: { fontSize: 18, fontWeight: '700', color: '#1e293b', marginBottom: 6 },
  cardSub: { fontSize: 14, color: '#64748b', marginBottom: 16 },
  
  cardBottom: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingTop: 16, borderTopWidth: 1, borderTopColor: '#f1f5f9'
  },
  startText: { fontSize: 14, fontWeight: '700', color: '#3b82f6' },
  
  infoBox: {
    flexDirection: 'row', gap: 12, backgroundColor: '#ecfdf5',
    padding: 16, borderRadius: 16, marginTop: 24,
    borderWidth: 1, borderColor: '#d1fae5'
  },
  infoTitle: { fontSize: 15, fontWeight: '700', color: '#065f46', marginBottom: 4 },
  infoText: { fontSize: 13, color: '#047857', lineHeight: 20 },
});
