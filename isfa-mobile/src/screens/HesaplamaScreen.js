import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ScrollView, Alert
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const ARAÇLAR = [
  {
    id: 'asgari',
    baslik: 'Asgari Kurumlar Vergisi',
    aciklama: 'Ticari kazanç üzerinden %10',
    ikon: 'trending-up-outline',
    renk: '#6366f1',
  },
  {
    id: 'finansman',
    baslik: 'Finansman Gider Kısıtlaması',
    aciklama: 'Yabancı kaynak finansman gider kısıtlaması',
    ikon: 'cash-outline',
    renk: '#f59e0b',
  },
];

function AsgariKV({ onBack }) {
  const [hasilat, setHasilat] = useState('');
  const [sonuc, setSonuc] = useState(null);

  const hesapla = () => {
    const h = parseFloat(hasilat.replace(',', '.'));
    if (!h || h <= 0) { Alert.alert('Hata', 'Geçerli bir hasılat girin'); return; }
    setSonuc({ hasilat: h, asgariKv: h * 0.10 });
  };

  const fmt = (v) => v?.toLocaleString('tr-TR', { minimumFractionDigits: 2 }) + ' ₺';

  return (
    <View style={s.toolContainer}>
      <TouchableOpacity onPress={onBack} style={s.backBtn}>
        <Ionicons name="arrow-back" size={20} color="#6366f1" />
        <Text style={s.backText}>Geri</Text>
      </TouchableOpacity>
      <Text style={s.toolTitle}>Asgari Kurumlar Vergisi</Text>
      <Text style={s.toolSub}>Ticari bilanço karı bazında %10 hesaplama</Text>

      <Text style={s.label}>Ticari Bilanço Karı (₺)</Text>
      <TextInput
        style={s.input} placeholder="Örn: 5000000"
        keyboardType="numeric" value={hasilat} onChangeText={setHasilat}
        placeholderTextColor="#9ca3af"
      />
      <TouchableOpacity style={[s.btn, { backgroundColor: '#6366f1' }]} onPress={hesapla}>
        <Text style={s.btnText}>Hesapla</Text>
      </TouchableOpacity>

      {sonuc && (
        <View style={s.resultBox}>
          <View style={s.resultRow}>
            <Text style={s.rKey}>Bilanço Karı</Text>
            <Text style={s.rVal}>{fmt(sonuc.hasilat)}</Text>
          </View>
          <View style={[s.resultRow, { marginTop: 8, backgroundColor:'#eef2ff', borderRadius:10, padding:12 }]}>
            <Text style={[s.rKey, { color:'#4338ca', fontWeight:'700' }]}>Asgari KV (%10)</Text>
            <Text style={[s.rVal, { color:'#4338ca' }]}>{fmt(sonuc.asgariKv)}</Text>
          </View>
        </View>
      )}
    </View>
  );
}

function FinansmanGider({ onBack }) {
  const [yabanci, setYabanci] = useState('');
  const [finansman, setFinansman] = useState('');
  const [sonuc, setSonuc] = useState(null);

  const hesapla = () => {
    const y = parseFloat(yabanci.replace(',', '.'));
    const f = parseFloat(finansman.replace(',', '.'));
    if (!y || !f) { Alert.alert('Hata', 'Tüm alanları doldurun'); return; }
    // Kısıtlamaya tabi gider: yabancı kaynak / öz kaynak oranı > 1 ise %10 kısıtlama
    const kisitlama = f * 0.10;
    const indirilecek = f - kisitlama;
    setSonuc({ toplamGider: f, kisitlama, indirilecek });
  };

  const fmt = (v) => v?.toLocaleString('tr-TR', { minimumFractionDigits: 2 }) + ' ₺';

  return (
    <View style={s.toolContainer}>
      <TouchableOpacity onPress={onBack} style={s.backBtn}>
        <Ionicons name="arrow-back" size={20} color="#f59e0b" />
        <Text style={[s.backText, { color: '#f59e0b' }]}>Geri</Text>
      </TouchableOpacity>
      <Text style={s.toolTitle}>Finansman Gider Kısıtlaması</Text>
      <Text style={s.toolSub}>Yabancı kaynak fazlası varsa %10 kısıtlama uygulanır</Text>

      <Text style={s.label}>Yabancı Kaynak Toplamı (₺)</Text>
      <TextInput style={s.input} placeholder="Örn: 10000000" keyboardType="numeric"
        value={yabanci} onChangeText={setYabanci} placeholderTextColor="#9ca3af" />

      <Text style={s.label}>Finansman Giderleri (₺)</Text>
      <TextInput style={s.input} placeholder="Örn: 500000" keyboardType="numeric"
        value={finansman} onChangeText={setFinansman} placeholderTextColor="#9ca3af" />

      <TouchableOpacity style={[s.btn, { backgroundColor: '#f59e0b' }]} onPress={hesapla}>
        <Text style={s.btnText}>Hesapla</Text>
      </TouchableOpacity>

      {sonuc && (
        <View style={s.resultBox}>
          <View style={s.resultRow}>
            <Text style={s.rKey}>Toplam Finansman Gideri</Text>
            <Text style={s.rVal}>{fmt(sonuc.toplamGider)}</Text>
          </View>
          <View style={s.resultRow}>
            <Text style={[s.rKey, { color: '#ef4444' }]}>Kanunen Kabul Edilmeyen (%10)</Text>
            <Text style={[s.rVal, { color: '#ef4444' }]}>{fmt(sonuc.kisitlama)}</Text>
          </View>
          <View style={[s.resultRow, { marginTop: 4, backgroundColor: '#fef3c7', borderRadius: 10, padding: 12 }]}>
            <Text style={[s.rKey, { color: '#92400e', fontWeight: '700' }]}>İndirilebilecek (%90)</Text>
            <Text style={[s.rVal, { color: '#92400e' }]}>{fmt(sonuc.indirilecek)}</Text>
          </View>
        </View>
      )}
    </View>
  );
}

export default function HesaplamaScreen() {
  const [aktif, setAktif] = useState(null);

  if (aktif === 'asgari') return <AsgariKV onBack={() => setAktif(null)} />;
  if (aktif === 'finansman') return <FinansmanGider onBack={() => setAktif(null)} />;

  return (
    <ScrollView style={{ flex: 1, backgroundColor: '#f1f5f9' }}>
      <View style={s.pageHeader}>
        <Text style={s.pageTitle}>Hesaplama Araçları</Text>
        <Text style={s.pageSub}>Vergi hesaplamalarınızı anında yapın</Text>
      </View>
      {ARAÇLAR.map((a) => (
        <TouchableOpacity key={a.id} style={s.aracCard} onPress={() => setAktif(a.id)}>
          <View style={[s.aracIkon, { backgroundColor: a.renk + '20' }]}>
            <Ionicons name={a.ikon} size={24} color={a.renk} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={s.aracBaslik}>{a.baslik}</Text>
            <Text style={s.aracAciklama}>{a.aciklama}</Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color="#9ca3af" />
        </TouchableOpacity>
      ))}
      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  pageHeader: { padding: 24, paddingTop: 40, backgroundColor: '#1e2a47' },
  pageTitle: { color: '#fff', fontSize: 22, fontWeight: '800' },
  pageSub: { color: 'rgba(255,255,255,0.5)', fontSize: 13, marginTop: 4 },
  aracCard: {
    flexDirection: 'row', alignItems: 'center', gap: 14,
    margin: 12, marginBottom: 0, backgroundColor: '#fff',
    borderRadius: 14, padding: 16, shadowColor: '#000',
    shadowOpacity: 0.05, shadowRadius: 8, elevation: 2,
  },
  aracIkon: { width: 48, height: 48, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  aracBaslik: { fontSize: 15, fontWeight: '700', color: '#111827' },
  aracAciklama: { fontSize: 12, color: '#9ca3af', marginTop: 2 },
  // Tool içi
  toolContainer: { flex: 1, padding: 20, paddingTop: 50, backgroundColor: '#f1f5f9' },
  backBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 20 },
  backText: { color: '#6366f1', fontSize: 15, fontWeight: '600' },
  toolTitle: { fontSize: 20, fontWeight: '800', color: '#111827', marginBottom: 4 },
  toolSub: { fontSize: 13, color: '#9ca3af', marginBottom: 20 },
  label: { fontSize: 13, fontWeight: '600', color: '#374151', marginBottom: 6, marginTop: 12 },
  input: {
    borderWidth: 1.5, borderColor: '#e5e7eb', borderRadius: 10,
    padding: 12, fontSize: 16, color: '#111827', backgroundColor: '#fff',
  },
  btn: {
    borderRadius: 12, padding: 14, alignItems: 'center',
    justifyContent: 'center', marginTop: 20,
  },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  resultBox: { marginTop: 20, backgroundColor: '#fff', borderRadius: 14, padding: 16 },
  resultRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 },
  rKey: { fontSize: 13, color: '#6b7280' },
  rVal: { fontSize: 13, fontWeight: '700', color: '#111827' },
});
