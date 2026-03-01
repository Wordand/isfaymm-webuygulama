// API Baz URL — Render'a deploy ettikten sonra gerçek URL'yi buraya yaz
export const API_BASE = 'http://127.0.0.1:5000/api/mobile';

export const ENDPOINTS = {
  ping:    `${API_BASE}/ping`,
  oranlar: `${API_BASE}/oranlar`,
  mevzuat: `${API_BASE}/mevzuat`,
  hesapla: {
    kv:     `${API_BASE}/hesapla/kv`,
    asgari: `${API_BASE}/hesapla/asgari`,
  },
};
