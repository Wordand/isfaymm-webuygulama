import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  ScrollView, Linking, FlatList
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const MEVZUAT = [
  {
    kategori: 'Kurumlar Vergisi',
    renk: '#1e2a47',
    ikon: 'business-outline',
    mevzuatlar: [
      {
        baslik: '5520 Sayılı Kurumlar Vergisi Kanunu',
        tur: 'Kanun',
        url: 'https://www.mevzuat.gov.tr/mevzuatmetin/1.5.5520.pdf',
        ozet: 'Kurumlar vergisinin temel kanunu',
        yeni: false,
      },
      {
        baslik: 'İndirimli KV Genel Tebliği (Seri No: 1)',
        tur: 'Tebliğ',
        url: 'https://www.gib.gov.tr/node/98600',
        ozet: 'Yatırım teşvik belgesi kapsamında indirimli KV',
        yeni: false,
      },
      {
        baslik: '2025/9903 Yeni Teşvik Sistemi',
        tur: 'Cumhurbaşkanlığı Kararı',
        url: 'https://www.resmigazete.gov.tr',
        ozet: 'Yeni yatırım teşvik sistemi esasları',
        yeni: true,
      },
    ],
  },
  {
    kategori: 'KDV',
    renk: '#0ea5e9',
    ikon: 'receipt-outline',
    mevzuatlar: [
      {
        baslik: '3065 Sayılı KDV Kanunu',
        tur: 'Kanun',
        url: 'https://www.mevzuat.gov.tr/MevzuatMetin/1.5.3065.pdf',
        ozet: 'Katma değer vergisinin temel kanunu',
        yeni: false,
      },
      {
        baslik: 'KDV Genel Uygulama Tebliği',
        tur: 'Tebliğ',
        url: 'https://www.gib.gov.tr/kdv-genel-uygulama-tebligi',
        ozet: 'KDV uygulamalarına ilişkin açıklamalar',
        yeni: false,
      },
    ],
  },
  {
    kategori: 'Gelir Vergisi',
    renk: '#10b981',
    ikon: 'person-outline',
    mevzuatlar: [
      {
        baslik: '193 Sayılı Gelir Vergisi Kanunu',
        tur: 'Kanun',
        url: 'https://www.mevzuat.gov.tr/MevzuatMetin/1.3.193.pdf',
        ozet: 'Gelir vergisinin temel kanunu',
        yeni: false,
      },
    ],
  },
];

export default function MevzuatScreen() {
  const [acik, setAcik] = useState(null);

  const acLink = (url) => Linking.openURL(url).catch(() => {});

  return (
    <ScrollView style={s.container}>
      <View style={s.header}>
        <Ionicons name="library-outline" size={28} color="#fff" />
        <Text style={s.headerTitle}>Mevzuat & Rehber</Text>
        <Text style={s.headerSub}>Güncel mevzuata hızlı erişim</Text>
      </View>

      {MEVZUAT.map((kategori, ki) => (
        <View key={ki} style={s.kategoriCard}>
          <TouchableOpacity
            style={[s.kategoriHeader, { borderLeftColor: kategori.renk }]}
            onPress={() => setAcik(acik === ki ? null : ki)}
          >
            <View style={[s.kategoriIkon, { backgroundColor: kategori.renk + '18' }]}>
              <Ionicons name={kategori.ikon} size={20} color={kategori.renk} />
            </View>
            <Text style={s.kategoriBaslik}>{kategori.kategori}</Text>
            <Text style={s.kategoriSayi}>{kategori.mevzuatlar.length} belge</Text>
            <Ionicons
              name={acik === ki ? 'chevron-up' : 'chevron-down'}
              size={18} color="#9ca3af"
            />
          </TouchableOpacity>

          {acik === ki && kategori.mevzuatlar.map((m, mi) => (
            <TouchableOpacity
              key={mi}
              style={s.mevzuatItem}
              onPress={() => acLink(m.url)}
            >
              <View style={s.mevzuatContent}>
                <View style={s.mevzuatUstRow}>
                  <View style={[s.turBadge, { backgroundColor: kategori.renk + '18' }]}>
                    <Text style={[s.turText, { color: kategori.renk }]}>{m.tur}</Text>
                  </View>
                  {m.yeni && (
                    <View style={s.yeniBadge}>
                      <Text style={s.yeniText}>YENİ</Text>
                    </View>
                  )}
                </View>
                <Text style={s.mevzuatBaslik}>{m.baslik}</Text>
                <Text style={s.mevzuatOzet}>{m.ozet}</Text>
              </View>
              <Ionicons name="open-outline" size={18} color="#9ca3af" />
            </TouchableOpacity>
          ))}
        </View>
      ))}

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f1f5f9' },
  header: {
    backgroundColor: '#1e2a47', padding: 24, paddingTop: 40,
    alignItems: 'center', gap: 6,
  },
  headerTitle: { color: '#fff', fontSize: 20, fontWeight: '800', marginTop: 8 },
  headerSub: { color: 'rgba(255,255,255,0.55)', fontSize: 13 },
  kategoriCard: {
    margin: 12, marginBottom: 0, backgroundColor: '#fff',
    borderRadius: 14, overflow: 'hidden',
    shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 2,
  },
  kategoriHeader: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    padding: 16, borderLeftWidth: 3,
  },
  kategoriIkon: {
    width: 38, height: 38, borderRadius: 10,
    alignItems: 'center', justifyContent: 'center',
  },
  kategoriBaslik: { flex: 1, fontSize: 15, fontWeight: '700', color: '#111827' },
  kategoriSayi: { fontSize: 12, color: '#9ca3af', marginRight: 4 },
  mevzuatItem: {
    flexDirection: 'row', alignItems: 'center',
    padding: 14, paddingLeft: 20,
    borderTopWidth: 1, borderTopColor: '#f3f4f6',
  },
  mevzuatContent: { flex: 1 },
  mevzuatUstRow: { flexDirection: 'row', gap: 6, marginBottom: 6 },
  turBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 50 },
  turText: { fontSize: 10, fontWeight: '700' },
  yeniBadge: { backgroundColor: '#dcfce7', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 50 },
  yeniText: { fontSize: 10, fontWeight: '700', color: '#16a34a' },
  mevzuatBaslik: { fontSize: 13, fontWeight: '700', color: '#111827', marginBottom: 3 },
  mevzuatOzet: { fontSize: 12, color: '#9ca3af' },
});
