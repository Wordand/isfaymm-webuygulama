from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from config import tarifeler, asgari_ucretler, GECIKME_ZAMMI_ORANLARI
from auth import login_required

bp = Blueprint('tools', __name__)

# --- Helper Functions ---
def gelir_vergisi_hesapla(yil: int, gelir: float, tarifeler: dict, ucret: bool = False) -> float:
    tarife_yili = tarifeler.get(yil)
    if not tarife_yili:
        raise ValueError(f"{yil} yılı için vergi tarifesi tanımlı değil.")

    tarife_tipi = "ucret" if ucret else "normal"
    dilimler = tarife_yili.get(tarife_tipi)
    if not dilimler:
        raise ValueError(f"{yil} yılı için '{tarife_tipi}' tarifesi bulunamadı.")

    vergi = 0.0

    for i, (alt_limit, _, oran) in enumerate(dilimler):
        ust_limit = dilimler[i + 1][0] if i + 1 < len(dilimler) else float("inf")

        if gelir > alt_limit:
            vergilenecek = min(gelir, ust_limit) - alt_limit
            vergi += vergilenecek * oran
        else:
            break

    return round(vergi, 2)

def asgari_ucret_istisnasi_hesapla(yil: int, ay_sayisi: int, ucret: bool = True):
    veriler = asgari_ucretler.get(yil)
    if not veriler or "istisnalar" not in veriler:
        return 0.0, 0.0

    toplam = 0.0
    son_ay_istisnasi = 0.0
    for ay in range(1, ay_sayisi + 1):
        tutar = veriler["istisnalar"].get(ay, 0.0)
        toplam += tutar
        if ay == ay_sayisi:
            son_ay_istisnasi = tutar

    return round(toplam, 2), round(son_ay_istisnasi, 2)

def gecikme_orani_bul(tarih):
    for r in GECIKME_ZAMMI_ORANLARI:
        bas = datetime.strptime(r["baslangic"], "%Y-%m-%d").date()

        if r["bitis"]:
            bit = datetime.strptime(r["bitis"], "%Y-%m-%d").date()
            if bas <= tarih <= bit:
                return Decimal(str(r["oran"]))
        else:
            if tarih >= bas:
                return Decimal(str(r["oran"]))

    raise ValueError("Gecikme zammı oranı bulunamadı")

def efektif_gecikme_orani(aylik_oran, borc_turu):
    if borc_turu == "mahkeme_cezasi":
        return aylik_oran / Decimal("2")
    if borc_turu == "usulsuzluk":
        return Decimal("0")
    return aylik_oran

def gunluk_gecikme_orani(aylik_oran):
    oran = Decimal(str(aylik_oran)) / Decimal("30")
    return oran.quantize(Decimal("0.000000"), rounding=ROUND_HALF_UP)

def gecikme_zammi_hesapla(borc, vade, odeme, borc_turu):
    if odeme <= vade:
        return Decimal("0")

    aylik_oran = gecikme_orani_bul(vade)
    oran = efektif_gecikme_orani(aylik_oran, borc_turu)

    if oran == Decimal("0"):
        return Decimal("0")

    gun_sayisi = (odeme - vade).days
    gunluk_oran = gunluk_gecikme_orani(oran)

    zam = borc * gunluk_oran * Decimal(gun_sayisi)

    # 6183 md.51 – 1 TL alt sınır
    if Decimal("0") < zam < Decimal("1"):
        return Decimal("1")

    return zam.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --- Routes ---

@bp.route("/asgari")
@login_required
def asgari():
    return render_template("calculators/asgari.html")

@bp.route("/sermaye")
def sermaye():
    return render_template("calculators/sermaye.html")

@bp.route("/serbest-meslek")
def serbest_meslek():
    return render_template("calculators/serbest_meslek.html")

@bp.route("/finansman")
@login_required
def finansman():
    return render_template("calculators/finansman.html")

@bp.route("/sermaye-azaltimi")
@login_required
def sermaye_azaltimi():
    return render_template("calculators/sermaye_azaltimi.html")

@bp.route("/vergi-hesapla", methods=["POST"])
def vergi_hesapla_api():
    try:
        data = request.get_json(force=True)

        yil = int(data.get("yil", 0))
        brut = float(data.get("brut", 0))
        ay = int(data.get("ay", 0))
        gelir_turu = data.get("gelir_turu", "ucret")
        ucret_mi = gelir_turu == "ucret"
        istisna_var = bool(data.get("istisna", False))
        onceki_dict = data.get("onceki_matrahlar", {})

        onceki_toplam = 0.0
        for v in onceki_dict.values():
            try:
                onceki_toplam += float(v)
            except (ValueError, TypeError):
                continue

        if ucret_mi:
            if istisna_var:
                matrah_yillik = (onceki_toplam + brut) if ay > 0 else brut
                istisna_ay = ay if ay > 0 else 12
            else:
                matrah_yillik = (onceki_toplam + brut) if ay > 0 else brut
                istisna_ay = 0
        else:
            matrah_yillik = brut
            istisna_ay = 0

        vergi = gelir_vergisi_hesapla(yil, matrah_yillik, tarifeler, ucret=ucret_mi)

        istisna = tek_ay_istisna = 0.0
        if istisna_var and ucret_mi and istisna_ay > 0:
            istisna, tek_ay_istisna = asgari_ucret_istisnasi_hesapla(yil, istisna_ay, True)
            vergi = max(vergi - istisna, 0)

        if ay > 0 and ay < 12 and onceki_toplam > 0:
            onceki_vergi = gelir_vergisi_hesapla(yil, onceki_toplam, tarifeler, ucret=ucret_mi)
            vergi = max(vergi - onceki_vergi, 0)

        tam_yillik_istisna = 0.0
        if ucret_mi and istisna_var:
            tam_yillik_istisna, _ = asgari_ucret_istisnasi_hesapla(yil, 12, True)

        return jsonify({
            "vergi": round(vergi, 2),
            "istisna": round(istisna, 2),
            "istisna_ay": istisna_ay,
            "tam_istisna": round(tam_yillik_istisna, 2),
            "tek_ay_istisna": round(tek_ay_istisna, 2)
        })

    except Exception as e:
        return jsonify({"error": f"Hesaplama hatası: {str(e)}"}), 400

@bp.route("/asgari-istisna", methods=["POST"])
def asgari_istisna_api():
    try:
        data = request.get_json(force=True)
        yil = int(data.get("yil", 0))
        ay = int(data.get("ay_sayisi", 1))
        ucret = bool(data.get("ucret", True))

        toplam, tek_ay = asgari_ucret_istisnasi_hesapla(yil, ay, ucret)
        return jsonify({
            "toplam_istisna": round(toplam, 2),
            "tek_ay_istisna": round(tek_ay, 2)
        })

    except Exception as e:
        return jsonify({"error": f"Hesaplama hatası: {str(e)}"}), 400

@bp.route("/gecikme-zammi-hesapla", methods=["POST"])
@login_required
def gecikme_zammi_hesapla_api():
    try:
        data = request.get_json(silent=True)
        borc = Decimal(str(data["borc"]))
        vade = datetime.strptime(data["vade"], "%Y-%m-%d").date()
        odeme = datetime.strptime(data["odeme"], "%Y-%m-%d").date()
        borc_turu = data["borc_turu"]

        zam = gecikme_zammi_hesapla(borc, vade, odeme, borc_turu)

        return jsonify({
            "gecikme_zammi": float(zam),
            "toplam_borc": float((borc + zam).quantize(Decimal("0.01")))
        })

    except Exception as e:
        print("Gecikme zammı hatası:", repr(e))
        # Keep 500 or 400? app.py raised, which causes 500 usually
        raise e
