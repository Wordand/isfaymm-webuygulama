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
        "7/A SEÇENEĞİ (FONKSİYON ESASI)": {
            "700": "Maliyet Muhasebesi Bağlantı Hesabı",
            "701": "Maliyet Muhasebesi Yansıtma Hesabı",
            "710": "Direkt İlk Madde ve Malzeme Giderleri",
            "711": "Direkt İlk Madde ve Malzeme Yansıtma Hesabı",
            "712": "Direkt İlk Madde ve Malzeme Fiyat Farkı",
            "713": "Direkt İlk Madde ve Malzeme Miktar Farkı",
            "720": "Direkt İşçilik Giderleri",
            "721": "Direkt İşçilik Giderleri Yansıtma Hesabı",
            "722": "Direkt İşçilik Ücret Farkları",
            "723": "Direkt İşçilik Süre (Zaman) Farkları",
            "730": "Genel Üretim Giderleri",
            "731": "Genel Üretim Giderleri Yansıtma Hesabı",
            "732": "Genel Üretim Giderleri Bütçe Farkları",
            "733": "Genel Üretim Giderleri Verimlilik Farkları",
            "734": "Genel Üretim Giderleri Kapasite Farkları",
            "740": "Hizmet Üretim Maliyeti",
            "741": "Hizmet Üretim Maliyeti Yansıtma Hesabı",
            "742": "Hizmet Üretim Maliyeti Fark Hesapları",
            "750": "Araştırma ve Geliştirme Giderleri",
            "751": "Araştırma ve Geliştirme Giderleri Yansıtma Hesabı",
            "752": "Araştırma ve Geliştirme Gider Farkları",
            "760": "Pazarlama Satış ve Dağıtım Giderleri",
            "761": "Pazarlama Satış ve Dağıtım Giderleri Yansıtma Hesabı",
            "762": "Pazarlama Satış ve Dağıtım Gider Farkları",
            "770": "Genel Yönetim Giderleri",
            "771": "Genel Yönetim Giderleri Yansıtma Hesabı",
            "772": "Genel Yönetim Gider Farkları",
            "780": "Finansman Giderleri",
            "781": "Finansman Giderleri Yansıtma Hesabı",
            "782": "Finansman Giderleri Fark Hesabı",
        },
        "7/B SEÇENEĞİ (ÇEŞİT ESASI)": {
            "790": "İlk Madde ve Malzeme Giderleri",
            "791": "İşçi Ücret ve Giderleri",
            "792": "Memur Ücret ve Giderleri",
            "793": "Dışarıdan Sağlanan Fayda ve Hizmetler",
            "794": "Çeşitli Giderler",
            "795": "Vergi, Resim ve Harçlar",
            "796": "Amortismanlar ve Tükenme Payları",
            "797": "Finansman Giderleri",
            "798": "Gider Çeşitleri Yansıtma Hesapları",
            "799": "Üretim Maliyet Hesabı",
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