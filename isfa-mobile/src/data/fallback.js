// Vergi oranları — Local fallback (internet yoksa kullanılır)
export const LOCAL_ORANLAR = {
  vergi_yili: 2026,
  guncelleme_tarihi: '2026-01-01',
  oranlar: {
    kurumlar_vergisi: 25,
    asgari_kurumlar_vergisi: 10,
    kdv_genel: 20,
    kdv_indirimli_1: 10,
    kdv_indirimli_2: 1,
  },
  teşvik_bolgeleri: {
    '1': { ad: '1. Bölge', kv_indirimi: 0 },
    '2': { ad: '2. Bölge', kv_indirimi: 15 },
    '3': { ad: '3. Bölge', kv_indirimi: 25 },
    '4': { ad: '4. Bölge', kv_indirimi: 35 },
    '5': { ad: '5. Bölge', kv_indirimi: 55 },
    '6': { ad: '6. Bölge', kv_indirimi: 90 },
  },
};
