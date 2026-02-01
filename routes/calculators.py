from flask import Blueprint, render_template
from hesaplar import BILANCO_HESAPLARI
from gelir import GELIR_TABLOSU_HESAPLARI

calculators_bp = Blueprint(
    "calculators",
    __name__,
    url_prefix="/hesaplama-araclari"
)

# 📌 Hesaplama Araçları Ana Sayfa (Katalog)
@calculators_bp.route("/")
def index():
    return render_template("calculators/index.html")


# 📄 Gelir Vergisi Hesaplama
@calculators_bp.route("/gelir-vergisi")
def gelir_vergisi():
    return render_template("calculators/gelir_vergisi.html")


# 🚢 İthalatta KDV
@calculators_bp.route("/ithalat-kdv")
def ithalat_kdv():
    return render_template("calculators/ithalat_kdv.html")


# ⏱️ Gecikme Zammı
@calculators_bp.route("/gecikme-zammi")
def gecikme_zammi():
    return render_template("calculators/gecikme_zammi.html")


# 📚 Tek Düzen Hesap Planı
@calculators_bp.route("/tek-duzen-hesap-plani")
def tdhp():
    # Load Descriptions from JSON
    import json
    import os
    
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tdhp_data.json')
    descriptions = {}
    
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                descriptions = json.load(f)
        except Exception as e:
            print(f"Error loading JSON: {e}")

    # Maliyet Hesapları (Basitleştirilmiş)
    maliyet_hesaplari = {
        "7. MALİYET HESAPLARI": {
            "70": "Maliyet Muhasebesi Bağlantı Hesapları",
            "710": "Direkt İlk Madde ve Malzeme Giderleri",
            "720": "Direkt İşçilik Giderleri",
            "730": "Genel Üretim Giderleri",
            "740": "Hizmet Üretim Maliyeti",
            "750": "Araştırma ve Geliştirme Giderleri",
            "760": "Pazarlama Satış ve Dağıtım Giderleri",
            "770": "Genel Yönetim Giderleri",
            "780": "Finansman Giderleri"
        }
    }
    
    # Nazım Hesaplar (Örnek)
    nazim_hesaplar = {
        "9. NAZIM HESAPLAR": {
            "900": "Teminat Mektupları",
            "950": "Kanunen Kabul Edilmeyen Giderler",
            "951": "Kanunen Kabul Edilmeyen Giderler Alacaklı Hesabı"
        }
    }

    return render_template(
        "calculators/tdhp.html",
        bilanco=BILANCO_HESAPLARI,
        gelir=GELIR_TABLOSU_HESAPLARI,
        maliyet=maliyet_hesaplari,
        nazim=nazim_hesaplar,
        descriptions=descriptions
    )


# deploy trigger – no functional change