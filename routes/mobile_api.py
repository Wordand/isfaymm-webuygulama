"""
ISFA Mobile API — Herkese açık, login gerektirmez.
Endpoint'ler:
  GET  /api/mobile/oranlar        → Güncel vergi oranları
  GET  /api/mobile/mevzuat        → Mevzuat listesi
  POST /api/mobile/hesapla/kv     → Kurumlar vergisi hesaplama
  POST /api/mobile/hesapla/gv     → Gelir vergisi hesaplama
  POST /api/mobile/hesapla/asgari → Asgari KV hesaplama
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
from config import tarifeler, asgari_ucretler

bp = Blueprint('mobile_api', __name__, url_prefix='/api/mobile')


# ─────────────────────────────────────────
# CORS — mobil uygulamanın istek atabilmesi için
# ─────────────────────────────────────────
@bp.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@bp.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@bp.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return jsonify({}), 200


# ─────────────────────────────────────────
# 1. GÜNCEL VERGİ ORANLARI
# ─────────────────────────────────────────
@bp.route('/oranlar', methods=['GET'])
def get_oranlar():
    """
    Mobil uygulama bu endpoint'i açılışta çağırır.
    Oranlar değişince sadece burayı güncelle — uygulama otomatik alır.
    """
    return jsonify({
        "vergi_yili": 2026,
        "guncelleme_tarihi": "2026-01-01",
        "versiyon": "1.0",
        "oranlar": {
            "kurumlar_vergisi": 25,           # %25
            "kucuk_isletme_kv": 20,           # %20 (bazı küçük işletmeler)
            "asgari_kurumlar_vergisi": 10,    # %10
            "kdv_genel": 20,                  # %20
            "kdv_indirimli_1": 10,            # %10
            "kdv_indirimli_2": 1,             # %1
            "damga_vergisi": 0.759,           # Binde 7.59
            "stopaj_temettü": 10,             # %10
        },
        "asgari_ucret": {
            "2026": asgari_ucretler.get(2026, {}).get("brut", 22104),
            "2025": asgari_ucretler.get(2025, {}).get("brut", 20002.5),
        },
        "teşvik_bolgeleri": {
            "1": {"ad": "1. Bölge", "kv_indirimi": 0},
            "2": {"ad": "2. Bölge", "kv_indirimi": 15},
            "3": {"ad": "3. Bölge", "kv_indirimi": 25},
            "4": {"ad": "4. Bölge", "kv_indirimi": 35},
            "5": {"ad": "5. Bölge", "kv_indirimi": 55},
            "6": {"ad": "6. Bölge", "kv_indirimi": 90},
        }
    })


# ─────────────────────────────────────────
# 2. MEVZUAT LİSTESİ
# ─────────────────────────────────────────
@bp.route('/mevzuat', methods=['GET'])
def get_mevzuat():
    """
    Mevzuat başlıkları ve URL'leri.
    Yeni mevzuat eklemek için sadece listeye ekle.
    """
    return jsonify({
        "kategoriler": [
            {
                "id": "kv",
                "baslik": "Kurumlar Vergisi",
                "ikon": "building-2",
                "mevzuatlar": [
                    {
                        "id": "kv_kanun",
                        "baslik": "5520 Sayılı Kurumlar Vergisi Kanunu",
                        "tur": "kanun",
                        "url": "https://www.mevzuat.gov.tr/mevzuatmetin/1.5.5520.pdf",
                        "ozet": "Kurumlar vergisinin temel kanunu"
                    },
                    {
                        "id": "indirimli_kv",
                        "baslik": "İndirimli KV Genel Tebliği (2012/1)",
                        "tur": "tebliğ",
                        "url": "https://www.gib.gov.tr/node/98600",
                        "ozet": "Yatırım indirimi ve teşvik belgesi uygulamaları"
                    },
                    {
                        "id": "9903_teblig",
                        "baslik": "2025/9903 Yeni Teşvik Sistemi",
                        "tur": "cumhurbaskanligi_karari",
                        "url": "https://www.resmigazete.gov.tr",
                        "ozet": "Yeni yatırım teşvik sistemi esasları",
                        "yeni": True
                    }
                ]
            },
            {
                "id": "kdv",
                "baslik": "KDV",
                "ikon": "percent",
                "mevzuatlar": [
                    {
                        "id": "kdv_kanun",
                        "baslik": "3065 Sayılı KDV Kanunu",
                        "tur": "kanun",
                        "url": "https://www.mevzuat.gov.tr/MevzuatMetin/1.5.3065.pdf",
                        "ozet": "Katma değer vergisinin temel kanunu"
                    },
                    {
                        "id": "kdv_teblig",
                        "baslik": "KDV Genel Uygulama Tebliği",
                        "tur": "tebliğ",
                        "url": "https://www.gib.gov.tr/kdv-genel-uygulama-tebligi",
                        "ozet": "KDV uygulamalarına ilişkin açıklamalar"
                    }
                ]
            },
            {
                "id": "gv",
                "baslik": "Gelir Vergisi",
                "ikon": "user",
                "mevzuatlar": [
                    {
                        "id": "gv_kanun",
                        "baslik": "193 Sayılı Gelir Vergisi Kanunu",
                        "tur": "kanun",
                        "url": "https://www.mevzuat.gov.tr/MevzuatMetin/1.3.193.pdf",
                        "ozet": "Gelir vergisinin temel kanunu"
                    }
                ]
            }
        ],
        "son_guncelleme": "2026-01-01"
    })


# ─────────────────────────────────────────
# 3. KURUMLAR VERGİSİ HESAPLA
# ─────────────────────────────────────────
@bp.route('/hesapla/kv', methods=['POST'])
def hesapla_kv():
    """
    Basit KV hesaplama.
    Body: { "matrah": 1000000, "bolge": 3, "yil": 2026 }
    """
    try:
        data = request.get_json(force=True)
        matrah = float(data.get('matrah', 0))
        bolge = int(data.get('bolge', 1))
        yil = int(data.get('yil', 2026))

        if matrah <= 0:
            return jsonify({"error": "Matrah 0'dan büyük olmalı"}), 400

        # Bölgeye göre indirim oranı
        bolge_indirimi = {1: 0, 2: 15, 3: 25, 4: 35, 5: 55, 6: 90}
        indirim_orani = bolge_indirimi.get(bolge, 0)

        kv_orani = 25  # Temel KV oranı — oranlar endpoint'inden çekilmeli
        indirimli_oran = kv_orani * (1 - indirim_orani / 100)

        temel_kv = matrah * (kv_orani / 100)
        indirimli_kv = matrah * (indirimli_oran / 100)
        tasarruf = temel_kv - indirimli_kv

        return jsonify({
            "matrah": matrah,
            "kv_orani": kv_orani,
            "bolge": bolge,
            "indirim_orani": indirim_orani,
            "indirimli_oran": round(indirimli_oran, 2),
            "temel_kv": round(temel_kv, 2),
            "indirimli_kv": round(indirimli_kv, 2),
            "tasarruf": round(tasarruf, 2),
            "tasarruf_orani": round((tasarruf / temel_kv) * 100, 1) if temel_kv > 0 else 0
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ─────────────────────────────────────────
# 4. ASGARİ KURUMLAR VERGİSİ HESAPLA
# ─────────────────────────────────────────
@bp.route('/hesapla/asgari', methods=['POST'])
def hesapla_asgari_kv():
    """
    Asgari KV hesaplama.
    Body: { "hasilat": 5000000, "yil": 2026 }
    """
    try:
        data = request.get_json(force=True)
        hasilat = float(data.get('hasilat', 0))

        if hasilat <= 0:
            return jsonify({"error": "Hasılat 0'dan büyük olmalı"}), 400

        asgari_oran = 0.10   # %10
        asgari_kv = hasilat * asgari_oran

        return jsonify({
            "hasilat": hasilat,
            "asgari_oran": 10,
            "asgari_kv": round(asgari_kv, 2),
            "aciklama": "Ticari bilanço karı üzerinden %10 asgari kurumlar vergisi"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ─────────────────────────────────────────
# 5. SAĞLIK KONTROLÜ
# ─────────────────────────────────────────
@bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "ok",
        "app": "ISFA Mobile API",
        "timestamp": datetime.utcnow().isoformat()
    })
