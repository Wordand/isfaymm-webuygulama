import React, { useState, useCallback } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView, Alert, KeyboardAvoidingView, Platform, Dimensions, Modal, FlatList } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ILLER, BOLGE_MAP, TESVIK_KATKILAR, TESVIK_VERGILER, BOLGE_MAP_9903, TESVIK_KATKILAR_9903, PROGRAM_TURLERI } from '../data/ikv_constants';

const InputField = ({ label, value, onChangeText, placeholder, info, subtext }) => (
  <View style={s.inputContainer}>
    <View style={s.labelRow}>
      <Text style={s.label}>{label}</Text>
      {info && <Ionicons name="information-circle-outline" size={16} color="#94a3b8" />}
    </View>
    <TextInput
      style={s.input}
      placeholder={placeholder}
      keyboardType="numeric"
      value={value}
      onChangeText={onChangeText}
      placeholderTextColor="#cbd5e1"
    />
    {subtext && <Text style={s.subText}>{subtext}</Text>}
  </View>
);

const SelectionField = ({ label, value, options, onSelect, placeholder }) => {
  const [modalVisible, setModalVisible] = React.useState(false);
  const selectedLabel = options.find(o => o.value === value)?.label || value || placeholder;

  return (
    <View style={s.inputContainer}>
      <Text style={s.label}>{label}</Text>
      <TouchableOpacity 
        style={s.selectionTrigger} 
        onPress={() => setModalVisible(true)}
        activeOpacity={0.7}
      >
        <Text style={[s.selectionValue, !value && {color: '#94a3b8'}]}>{selectedLabel}</Text>
        <Ionicons name="chevron-down" size={20} color="#64748b" />
      </TouchableOpacity>

      <Modal
        visible={modalVisible}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={s.modalOverlay}>
          <View style={s.modalContent}>
            <View style={s.modalHeader}>
              <Text style={s.modalTitle}>{label}</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Ionicons name="close" size={24} color="#0f172a" />
              </TouchableOpacity>
            </View>
            <FlatList
              data={options}
              keyExtractor={(item) => item.value}
              renderItem={({ item }) => (
                <TouchableOpacity 
                  style={[s.modalItem, value === item.value && s.modalItemActive]}
                  onPress={() => {
                    onSelect(item.value);
                    setModalVisible(false);
                  }}
                >
                  <Text style={[s.modalItemText, value === item.value && s.modalItemTextActive]}>
                    {item.label}
                  </Text>
                  {value === item.value && <Ionicons name="checkmark-circle" size={20} color="#2563eb" />}
                </TouchableOpacity>
              )}
            />
          </View>
        </View>
      </Modal>
    </View>
  );
};

export default function IndirimliKVScreen({ oranlar }) {
  const kvOrani = oranlar?.oranlar?.kurumlar_vergisi ?? 25;
  const [step, setStep] = useState(1);

  // Gelişmiş Form Verisi
  const [f, setF] = useState({
    karar: '2012/3305',
    vizeDurumu: 'yatirim',
    yatirimTuru: 'komple',
    il: 'Ankara',
    osb: 'yok',
    programTuru: PROGRAM_TURLERI[0],
    
    // Yatırım Tutarları
    toplamYatirim: '',
    gerceklesenYatirim: '',
    devredenKatki: '', // Önceki dönemlerden devreden endekslenmiş yatırıma katkı tutarı (isteğe bağlı)

    // Kazançlar
    toplamMatrah: '',
    yatirimiKazanci: '',
    digerKazanc: '',
    
    // Geçmiş Veriler (9903 ve genel hakediş için)
    baslangicTarihi: '01.01.2025',
    oncekiKullanilan: '',
  });

  const updateF = (key, val) => setF(prev => ({ ...prev, [key]: val }));

  // Dinamik Oranlar
  const is9903 = f.karar === '2025/9903';
  const bolge = is9903 ? "0" : (BOLGE_MAP[f.il] || "1");
  
  let vIndirimOrani = 0;
  let katkiOrani = 0;

  if (is9903) {
    vIndirimOrani = 60; // 2025/9903 de vergi indirim oranı sabittir
    katkiOrani = TESVIK_KATKILAR_9903[f.programTuru] || 0;
  } else {
    const osbKey = `${bolge}_${f.osb}`;
    vIndirimOrani = TESVIK_VERGILER[osbKey] || 0;
    katkiOrani = TESVIK_KATKILAR[osbKey] || 0;
  }
  
  const digerFaaliyetOrani = is9903 ? 50 : (f.vizeDurumu === 'yatirim' ? 80 : 0);
  const uygulananKvOrani = kvOrani * (1 - (vIndirimOrani / 100));

  const [sonuc, setSonuc] = useState(null);

  const validateStep1 = () => true;

  const validateStep2 = () => {
    if (!f.toplamYatirim) {
      Alert.alert('Uyarı', 'Lütfen teşvik belgesindeki toplam tutarı giriniz.');
      return false;
    }
    return true;
  };

  const validateStep3 = () => {
    const parse = (str) => parseFloat((str || '').replace(/\./g, '').replace(',', '.')) || 0;
    const m = parse(f.toplamMatrah);
    const yk = parse(f.yatirimiKazanci);
    const dk = parse(f.digerKazanc);

    if (m <= 0) {
      Alert.alert('Uyarı', 'Toplam KV matrahı boş veya sıfır olamaz.');
      return false;
    }
    // Ufak bir tolerans vererek toplam matrah kontrolü
    if (yk + dk > m + 1) {
       Alert.alert('Uyarı', 'Yatırımdan ve Diğer Faaliyetlerden elde edilen kazançların toplamı, Genel Matrahı aşamaz!');
       return false;
    }
    return true;
  };

  const hesapla = () => {
    if (!validateStep3()) return;

    const parse = (str) => parseFloat((str || '').replace(/\./g, '').replace(',', '.')) || 0;

    const ty = parse(f.toplamYatirim);
    const gy = parse(f.gerceklesenYatirim) || ty;
    const devreden = parse(f.devredenKatki);
    
    let m = parse(f.toplamMatrah);
    let yk = parse(f.yatirimiKazanci);
    let dk = parse(f.digerKazanc);

    // Başlangıç yılı ve dönem farkı (9903 için)
    const currentYear = 2025; 
    let startYear = currentYear;
    
    if (f.baslangicTarihi) {
      // DD.MM.YYYY formatından yılı çekmeye çalış
      const match = f.baslangicTarihi.match(/\d{4}$/);
      if (match) startYear = parseInt(match[0]);
    }
    const periodDiff = currentYear - startYear;

    if (yk === 0 && dk === 0) yk = m;

    const toplamKatkiPotansiyeli = ty * (katkiOrani / 100);
    const fiiliKatkiHakedis = (gy * (katkiOrani / 100)) + devreden;
    
    // Normal Vergi
    const normalKv = m * (kvOrani / 100);

    // Avantajlar
    let ykVergiAvantaji = 0;
    let dkVergiAvantaji = 0;

    // 1) Yatırımdan Kazanç
    let canUseYK = true;
    if (is9903 && periodDiff >= 10) canUseYK = false;

    if (canUseYK && yk > 0) {
      const ykIndirimli = yk * (uygulananKvOrani / 100);
      ykVergiAvantaji = (yk * (kvOrani / 100)) - ykIndirimli;
    }

    // 2) Diğer Faaliyetler
    let canUseDK = f.vizeDurumu === 'yatirim';
    if (is9903) {
      if (periodDiff >= 4) canUseDK = false;
    }

    if (canUseDK && dk > 0) {
      const dkIndirimli = dk * (uygulananKvOrani / 100);
      let potansiyelDKAvantaj = (dk * (kvOrani / 100)) - dkIndirimli;

      if (is9903) {
        // 9903 Sınırı: Diğer faaliyetler toplam katkının %50'sini aşamaz
        const digerButce = (toplamKatkiPotansiyeli * 0.5); 
        dkVergiAvantaji = Math.min(potansiyelDKAvantaj, digerButce);
      } else {
        dkVergiAvantaji = potansiyelDKAvantaj;
      }
    }

    let toplamAvantajKullanimi = ykVergiAvantaji + dkVergiAvantaji;

    // Harcama/Hakediş Sınırı
    if (toplamAvantajKullanimi > fiiliKatkiHakedis) {
       toplamAvantajKullanimi = fiiliKatkiHakedis;
    }

    const odenmesiGerekenVergi = normalKv - toplamAvantajKullanimi;
    const kalanKatki = toplamKatkiPotansiyeli - (parse(f.oncekiKullanilan) + toplamAvantajKullanimi);

    setSonuc({
      fiiliKatkiHakedis,
      normalKv,
      toplamAvantajKullanimi,
      odenmesiGerekenVergi,
      kalanKatki,
      yk, dk, m
    });
    setStep(4);
  };

  const formatTL = (val) => Number(val).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₺';

  // render yardımcıları
  const renderStepper = () => (
    <View style={s.stepper}>
      <View style={[s.stepLine, { width: `${((step - 1) / 3) * 100}%` }]} />
      {[1, 2, 3, 4].map(i => (
        <View key={i} style={[s.stepDot, step >= i && s.stepDotActive]}>
          <Text style={[s.stepDotText, step >= i && s.stepDotTextActive]}>{i}</Text>
        </View>
      ))}
    </View>
  );

  return (
    <KeyboardAvoidingView style={s.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={s.header}>
        <Text style={s.headerTitle}>İndirimli Kurumlar Vergisi</Text>
        <Text style={s.headerSub}>Teşvik Belgesi Kapsamında Profesyonel Hesaplama</Text>
        {renderStepper()}
      </View>

      <ScrollView contentContainerStyle={s.scrollContent} keyboardShouldPersistTaps="handled">
        {step === 1 && (
          <View style={s.card}>
            <Text style={s.cardTitle}>📍 1. Tesis & Belge Bilgileri</Text>
            
            <SelectionField
              label="Tabi Olunan Karar / BKK"
              options={[
                {label: '2012/3305 G.K.', value: '2012/3305'}, 
                {label: '2025/9903 Yeni', value: '2025/9903'},
                {label: '2016/9495 Proje', value: '2016/9495'}
              ]}
              value={f.karar}
              onSelect={(v) => updateF('karar', v)}
            />

            {is9903 && (
              <SelectionField
                label="Program Türü"
                options={PROGRAM_TURLERI.map(pt => ({label: pt, value: pt}))}
                value={f.programTuru}
                onSelect={(v) => updateF('programTuru', v)}
              />
            )}

            {!is9903 && (
              <SelectionField
                label="Yatırımın Türü"
                options={[{label: 'Komple Yeni', value: 'komple'}, {label: 'Tevsi/Modernizasyon', value: 'tevsi'}]}
                value={f.yatirimTuru}
                onSelect={(v) => updateF('yatirimTuru', v)}
              />
            )}

            <SelectionField
              label="Yatırımın Dönemi (Tamamlama Vizesi)"
              options={[{label: 'Yatırım Sürüyor', value: 'yatirim'}, {label: 'İşletmeye Geçildi', value: 'isletme'}]}
              value={f.vizeDurumu}
              onSelect={(v) => updateF('vizeDurumu', v)}
            />

            {!is9903 && (
              <SelectionField
                label="Yatırımın Yapıldığı İl"
                options={ILLER.map(il => ({label: il, value: il}))}
                value={f.il}
                onSelect={(v) => updateF('il', v)}
                placeholder="İl Seçiniz..."
              />
            )}

            {!is9903 && (
              <SelectionField
                label="Bölge İçi Durumu"
                options={[{label: 'OSB / Endüstri Bölgeleri', value: 'var'}, {label: 'Diğer (OSB Dışı)', value: 'yok'}]}
                value={f.osb}
                onSelect={(v) => updateF('osb', v)}
              />
            )}

            <InputField
              label="Yatırıma Başlama Tarihi"
              value={f.baslangicTarihi}
              onChangeText={(v) => updateF('baslangicTarihi', v)}
              placeholder="GG.AA.YYYY"
              info="Yatırımın fiilen başladığı tarihi giriniz. (9903 kararı için süre hesabı bu tarihten başlar)"
            />

            <InputField
              label="Önceki Dönemlerde Kullanılan Toplam Katkı"
              value={f.oncekiKullanilan}
              onChangeText={(v) => updateF('oncekiKullanilan', v)}
              placeholder="0,00"
              subtext="Kalan katkı hesabı için gereklidir."
            />

            <View style={s.bilgiKutusu}>
              <Ionicons name="location" size={20} color="#0284c7" />
              <View style={{flex: 1, marginLeft: 10}}>
                <Text style={s.bilgiBaslik}>Seçilen Bölge: {is9903 ? "Özel" : `${bolge}. Bölge`}</Text>
                <Text style={s.bilgiMetin}>
                  Yatırıma Katkı Oranı: %{katkiOrani}{'\n'}
                  Vergi İndirimi: %{vIndirimOrani}{'\n'}
                  İndirimli KV Oranı: %{uygulananKvOrani.toFixed(1)}{'\n'}
                  {is9903 && <Text style={{fontWeight: '700'}}>Diğer Faal. Katkı Sınırı: %50</Text>}
                </Text>
              </View>
            </View>

            <TouchableOpacity style={s.btnPrimary} onPress={() => validateStep1() && setStep(2)}>
              <Text style={s.btnPrimaryText}>Adım 2: Harcamalar</Text>
              <Ionicons name="arrow-forward" size={18} color="#fff" />
            </TouchableOpacity>
          </View>
        )}

        {step === 2 && (
          <View style={s.card}>
            <Text style={s.cardTitle}>💰 2. Yatırım ve Katkı Tutarları</Text>
            
            <InputField
              label="Belgedeki Toplam Yatırım Tutarı (₺)"
              placeholder="Örn: 50.000.000"
              value={f.toplamYatirim}
              onChangeText={(v) => updateF('toplamYatirim', v)}
              info={true}
            />

            <InputField
              label="Cari Yıl Dahil Fiili (Gerçekleşen) Harcama"
              placeholder="Örn: 15.000.000"
              value={f.gerceklesenYatirim}
              onChangeText={(v) => updateF('gerceklesenYatirim', v)}
              subtext="* Boş bırakılırsa tüm yatırımın gerçekleştiği varsayılır."
            />

            <InputField
              label="Önceki Yıldan Devreden Endeksli Katkı Tutarı"
              placeholder="Örn: 0"
              value={f.devredenKatki}
              onChangeText={(v) => updateF('devredenKatki', v)}
              subtext="* Varsa, yeniden değerleme yapılmış güncel devir tutarı."
            />

            <View style={s.rowBtns}>
              <TouchableOpacity style={s.btnSecondary} onPress={() => setStep(1)}>
                <Ionicons name="arrow-back" size={18} color="#475569" />
                <Text style={s.btnSecondaryText}>Geri</Text>
              </TouchableOpacity>
              <TouchableOpacity style={s.btnPrimaryFlexible} onPress={() => validateStep2() && setStep(3)}>
                <Text style={s.btnPrimaryText}>Adım 3: Kazançlar</Text>
                <Ionicons name="arrow-forward" size={18} color="#fff" />
              </TouchableOpacity>
            </View>
          </View>
        )}

        {step === 3 && (
          <View style={s.card}>
            <Text style={s.cardTitle}>📊 3. Kurumlar Vergisi Matrahı</Text>
            
            <InputField
              label="TOPLAM K.V. MATRAHI (Beyanname)"
              placeholder="Örn: 5.000.000"
              value={f.toplamMatrah}
              onChangeText={(v) => updateF('toplamMatrah', v)}
            />

            <View style={s.divider} />

            <InputField
              label="Sadece Teşvikli Yatırımdan Elde Edilen Kazanç"
              placeholder="Örn: 3.000.000"
              value={f.yatirimiKazanci}
              onChangeText={(v) => updateF('yatirimiKazanci', v)}
              subtext="* Ciro ve oranlama hesaplarınızı net kazanç olarak buraya giriniz."
            />

            <InputField
              label="Diğer Faaliyetlerden Elde Edilen Kazanç"
              placeholder="Örn: 2.000.000"
              value={f.digerKazanc}
              onChangeText={(v) => updateF('digerKazanc', v)}
              subtext="* Teşvike konu olmayan faal. (İşletme döneminde vergi indirimi hesaplanmaz)."
            />

            <View style={s.bilgiKutusuWar}>
              <Ionicons name="warning" size={20} color="#b45309" />
              <View style={{flex: 1, marginLeft: 10}}>
                <Text style={s.bilgiMetinWar}>
                  Yatırım dönemindeki diğer faaliyetler için yasal sınırlar ve oranlar dikkate alınarak otomatik vergi avantajı hesaplanacaktır.
                </Text>
              </View>
            </View>

            <View style={s.rowBtns}>
              <TouchableOpacity style={s.btnSecondary} onPress={() => setStep(2)}>
                <Ionicons name="arrow-back" size={18} color="#475569" />
                <Text style={s.btnSecondaryText}>Geri</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[s.btnPrimaryFlexible, {backgroundColor: '#10b981'}]} onPress={hesapla}>
                <Ionicons name="calculator" size={18} color="#fff" style={{marginRight: 6}}/>
                <Text style={s.btnPrimaryText}>Sonucu Görüntüle</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {step === 4 && sonuc && (
          <View style={s.resultCard}>
            <View style={s.resultHeader}>
              <Ionicons name="checkmark-circle" size={36} color="#10b981" />
              <Text style={s.resultTitle}>Dönem Hesaplaması Özeti</Text>
            </View>
            
            <View style={s.resultRow}>
              <Text style={s.resultKey}>Bölge & Teşvik Şartı</Text>
              <Text style={s.resultVal}>{bolge}. Bölge / {f.osb === 'var' ? 'OSB İçi' : 'OSB Dışı'}</Text>
            </View>
            <View style={s.resultRow}>
               <Text style={s.resultKey}>Yatırımdan Sağlanan Kazanç</Text>
               <Text style={s.resultVal}>{formatTL(sonuc.yk)}</Text>
            </View>
            <View style={s.resultRow}>
               <Text style={s.resultKey}>Diğer Faal. Kazanç</Text>
               <Text style={s.resultVal}>{formatTL(sonuc.dk)}</Text>
            </View>
            <View style={s.resultRow}>
              <Text style={s.resultKey}>Fiili Katkı Hakediş (Limit)</Text>
              <Text style={s.resultVal}>{formatTL(sonuc.fiiliKatkiHakedis)}</Text>
            </View>
            
            <View style={s.divider} />
            
            <View style={s.resultRow}>
              <Text style={s.resultKey}>Normal Kurumlar Vergisi (%{kvOrani})</Text>
              <Text style={s.resultVal}>{formatTL(sonuc.normalKv)}</Text>
            </View>
            <View style={s.resultRow}>
              <Text style={s.resultKey}>Net Vergi Avantajı (İndirim)</Text>
              <Text style={[s.resultVal, {color: '#2563eb'}]}>-{formatTL(sonuc.toplamAvantajKullanimi)}</Text>
            </View>

            <View style={s.highlightBox}>
              <Text style={s.highlightLabel}>ÖDENECEK KURUMLAR VERGİSİ</Text>
              <Text style={s.highlightAmount}>{formatTL(sonuc.odenmesiGerekenVergi)}</Text>
            </View>

            <View style={s.bilgiKutusu}>
               <Ionicons name="documents" size={20} color="#0284c7" />
               <View style={{flex: 1, marginLeft: 10}}>
                  <Text style={s.bilgiBaslik}>Devreden Yatırıma Katkı</Text>
                  <Text style={s.bilgiMetin}>
                    Bir sonraki döneme endekslenmek üzere devreden kullanılmamış katkı tutarı: {'\n'}
                    <Text style={{fontWeight: '800', color: '#0369a1'}}>{formatTL(sonuc.kalanKatki)}</Text>
                  </Text>
               </View>
            </View>

            <TouchableOpacity style={s.btnReset} onPress={() => setStep(1)}>
              <Ionicons name="refresh" size={18} color="#64748b" style={{marginRight: 6}} />
              <Text style={s.btnResetText}>Yeni Form Doldur</Text>
            </TouchableOpacity>
          </View>
        )}

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  header: {
    backgroundColor: '#1e293b', padding: 24, paddingTop: 60, paddingBottom: 30,
    borderBottomLeftRadius: 24, borderBottomRightRadius: 24, zIndex: 10
  },
  headerTitle: { color: '#f8fafc', fontSize: 22, fontWeight: '800' },
  headerSub: { color: '#94a3b8', fontSize: 13, marginTop: 4 },
  
  stepper: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 24, position: 'relative' },
  stepLine: { position: 'absolute', height: 2, backgroundColor: '#3b82f6', top: 14, left: 10, right: 10, zIndex: 1 },
  stepDot: { width: 30, height: 30, borderRadius: 15, backgroundColor: '#334155', alignItems: 'center', justifyContent: 'center', zIndex: 2 },
  stepDotActive: { backgroundColor: '#3b82f6', shadowColor: '#3b82f6', shadowOpacity: 0.5, shadowRadius: 8, elevation: 4 },
  stepDotText: { color: '#94a3b8', fontSize: 13, fontWeight: '700' },
  stepDotTextActive: { color: '#fff' },

  scrollContent: { padding: 20, paddingBottom: 60 },
  card: { backgroundColor: '#fff', borderRadius: 20, padding: 24, shadowColor: '#cbd5e1', shadowOpacity: 0.4, shadowRadius: 16, elevation: 5 },
  cardTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a', marginBottom: 20 },
  
  inputContainer: { marginBottom: 20 },
  labelRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  label: { fontSize: 13, fontWeight: '700', color: '#475569', textTransform: 'uppercase', letterSpacing: 0.5 },
  subText: { fontSize: 11, color: '#94a3b8', marginTop: 6, fontStyle: 'italic' },
  input: { borderWidth: 1.5, borderColor: '#e2e8f0', borderRadius: 12, padding: 14, fontSize: 16, color: '#0f172a', backgroundColor: '#f8fafc', fontWeight: '600' },
  
  selectionTrigger: { 
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    borderWidth: 1.5, borderColor: '#e2e8f0', borderRadius: 12, padding: 14, 
    backgroundColor: '#fff', shadowColor: '#94a3b8', shadowOpacity: 0.1, shadowRadius: 4, elevation: 2
  },
  selectionValue: { fontSize: 16, color: '#0f172a', fontWeight: '600' },
  
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.6)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', borderTopLeftRadius: 32, borderTopRightRadius: 32, paddingBottom: 40, maxHeight: '80%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 24, borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  modalItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  modalItemActive: { backgroundColor: '#eff6ff' },
  modalItemText: { fontSize: 16, color: '#475569', fontWeight: '500' },
  modalItemTextActive: { color: '#2563eb', fontWeight: '700' },

  bilgiKutusu: { flexDirection: 'row', backgroundColor: '#f0f9ff', padding: 16, borderRadius: 12, marginBottom: 20, borderWidth: 1, borderColor: '#bae6fd' },
  bilgiBaslik: { fontSize: 14, fontWeight: '700', color: '#0369a1', marginBottom: 4 },
  bilgiMetin: { fontSize: 13, color: '#0ea5e9', lineHeight: 20 },

  bilgiKutusuWar: { flexDirection: 'row', backgroundColor: '#fffbeb', padding: 14, borderRadius: 12, marginBottom: 20, borderWidth: 1, borderColor: '#fde68a' },
  bilgiMetinWar: { fontSize: 12, color: '#d97706', lineHeight: 18 },

  btnPrimary: { backgroundColor: '#2563eb', padding: 16, borderRadius: 12, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', shadowColor: '#2563eb', shadowOpacity: 0.3, shadowRadius: 8, elevation: 4 },
  btnPrimaryFlexible: { flex: 1, backgroundColor: '#2563eb', padding: 16, borderRadius: 12, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', shadowColor: '#2563eb', shadowOpacity: 0.3, shadowRadius: 8, elevation: 4 },
  btnSecondary: { backgroundColor: '#f1f5f9', padding: 16, borderRadius: 12, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginRight: 12, width: 100 },
  btnPrimaryText: { color: '#fff', fontSize: 16, fontWeight: '700', marginRight: 8 },
  btnSecondaryText: { color: '#475569', fontSize: 15, fontWeight: '700', marginLeft: 8 },
  rowBtns: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },

  resultCard: { backgroundColor: '#fff', borderRadius: 20, padding: 0, shadowColor: '#cbd5e1', shadowOpacity: 0.4, shadowRadius: 16, elevation: 5, overflow: 'hidden' },
  resultHeader: { backgroundColor: '#f0fdf4', padding: 24, paddingBottom: 20, alignItems: 'center', borderBottomWidth: 1, borderBottomColor: '#dcfce3' },
  resultTitle: { fontSize: 20, fontWeight: '800', color: '#065f46', marginTop: 12 },
  
  resultRow: { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 20, paddingVertical: 12 },
  resultKey: { color: '#64748b', fontSize: 13, fontWeight: '600' },
  resultVal: { color: '#0f172a', fontSize: 14, fontWeight: '800' },
  divider: { height: 1, backgroundColor: '#f1f5f9', marginHorizontal: 20, marginVertical: 8 },
  
  highlightBox: { backgroundColor: '#1e293b', margin: 20, padding: 20, borderRadius: 16, alignItems: 'center' },
  highlightLabel: { color: '#94a3b8', fontSize: 13, fontWeight: '600', marginBottom: 8 },
  highlightAmount: { color: '#10b981', fontSize: 28, fontWeight: '900' },

  btnReset: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', padding: 20, borderTopWidth: 1, borderTopColor: '#f1f5f9', backgroundColor: '#f8fafc' },
  btnResetText: { color: '#64748b', fontSize: 15, fontWeight: '700' },
});
