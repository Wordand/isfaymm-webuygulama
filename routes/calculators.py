from flask import Blueprint, render_template

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
