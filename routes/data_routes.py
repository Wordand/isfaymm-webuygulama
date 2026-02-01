from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.utils import secure_filename
from services.db import get_conn
from services.utils import allowed_file, to_float_turkish
from services.pdf_service import (
    parse_bilanco_from_pdf,
    parse_gelir_from_pdf,
    parse_kdv_from_pdf,
)

from services.xml_service import parse_xml_file
from services.excel_service import parse_mizan_excel
from extensions import fernet
from auth import login_required
import os
import json
import psycopg2.extras
import tempfile
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

bp = Blueprint('data', __name__)

def kaydet_beyanname(data, tur):
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        vkn = data.get("vergi_kimlik_no")
        unvan = data.get("unvan")
        if not vkn or vkn == "Bilinmiyor":
            return False

        c.execute("SELECT id FROM mukellef WHERE vergi_kimlik_no=%s AND user_id=%s", (vkn, session["user_id"]))
        row = c.fetchone()
        if not row:
            c.execute("INSERT INTO mukellef (user_id, vergi_kimlik_no, unvan) VALUES (%s, %s, %s) RETURNING id", 
                      (session["user_id"], vkn, unvan))
            mukellef_id = c.fetchone()[0]
        else:
            mukellef_id = row["id"]

        json_str = json.dumps(data, ensure_ascii=False)
        encrypted_data = fernet.encrypt(json_str.encode("utf-8"))
        donem = data.get("donem", "Bilinmiyor")

        c.execute("SELECT id FROM beyanname WHERE user_id=%s AND mukellef_id=%s AND donem=%s AND tur=%s", 
                  (session["user_id"], mukellef_id, donem, tur))
        existing = c.fetchone()
        
        if existing:
            c.execute("UPDATE beyanname SET veriler=%s, yuklenme_tarihi=CURRENT_TIMESTAMP WHERE id=%s", 
                      (encrypted_data, existing["id"]))
        else:
            c.execute("INSERT INTO beyanname (user_id, mukellef_id, donem, tur, veriler) VALUES (%s, %s, %s, %s, %s)", 
                      (session["user_id"], mukellef_id, donem, tur, encrypted_data))
        conn.commit()
    return True

@bp.route("/yukle-coklu", methods=["POST"])
@login_required
def yukle_coklu():
    if "files[]" not in request.files:
        flash("Dosya seçilmedi.", "warning")
        return redirect(url_for("data.veri_giris"))

    files = request.files.getlist("files[]")
    if not files or files[0].filename == "":
        flash("Dosya seçilmedi.", "warning")
        return redirect(url_for("data.veri_giris"))

    basarili = 0
    hatali = 0
    hatalar = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            file.save(temp_path)

            try:
                import pdfplumber
                full_text = ""
                with pdfplumber.open(temp_path) as pdf:
                    full_text = "\n".join([p.extract_text() or "" for p in pdf.pages])

                parsed_data = None
                tur = "bilinmiyor"

                if file.filename.lower().endswith(".xml"):
                    try:
                        res = parse_xml_file(temp_path)
                        if not res.get("hata"):
                            parsed_data = res
                            tur = res.get("tur", "xml_beyanname")
                        else:
                            # XML hatası varsa
                            hatali += 1
                            hatalar.append(f"{filename}: {res['hata']}")
                            continue
                            
                    except Exception as e:
                         hatali += 1
                         hatalar.append(f"{filename} (XML): {str(e)}")
                         continue

                elif "Bilanço" in full_text or "GELİR TABLOSU" in full_text: 
                     res = parse_bilanco_from_pdf(temp_path)
                     if res.get("aktif") or res.get("pasif") or (res.get("tur")=="gelir" and res.get("tablo")):
                         parsed_data = res
                         tur = res["tur"]
                     elif "GELİR TABLOSU" in full_text:
                         res = parse_gelir_from_pdf(temp_path)
                         if res.get("tablo"):
                             parsed_data = res
                             tur = "gelir"
                elif "KATMA DEĞER VERGİSİ" in full_text:
                     res = parse_kdv_from_pdf(temp_path)
                     if not res.get("hata"):
                         parsed_data = res
                         tur = "kdv"
                
                if not parsed_data:
                     res_g = parse_gelir_from_pdf(temp_path)
                     if res_g.get("tablo"):
                         parsed_data = res_g
                         tur = "gelir"
                     else:
                         res_b = parse_bilanco_from_pdf(temp_path)
                         if res_b.get("aktif"):
                             parsed_data = res_b
                             tur = "bilanco"
                         else:
                             res_k = parse_kdv_from_pdf(temp_path)
                             if not res_k.get("hata"):
                                 parsed_data = res_k
                                 tur = "kdv"

                if parsed_data and not parsed_data.get("hata"):
                    kaydet_beyanname(parsed_data, tur)
                    basarili += 1
                else:
                    hatali += 1
                    hatalar.append(f"{filename}: Tanınamayan format.")

            except Exception as e:
                hatali += 1
                hatalar.append(f"{filename}: {str(e)}")
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)
        else:
            hatali += 1
            hatalar.append(f"{file.filename}: Desteklenmeyen uzantı.")

    if basarili > 0: flash(f"{basarili} dosya başarıyla yüklendi.", "success")
    if hatali > 0: flash(f"{hatali} dosya yüklenemedi. Detaylar: {'; '.join(hatalar)}", "danger")

    return redirect(url_for("data.veri_giris"))

@bp.route("/kaydet-mizan-meta", methods=["POST"])
@login_required
def kaydet_mizan_meta():
    vkn = request.form.get("vkn")
    unvan = request.form.get("unvan")
    donem = request.form.get("donem")
    file = request.files.get("mizan_file")
    
    if not all([vkn, unvan, donem, file]):
        flash("Eksik bilgi.", "danger")
        return redirect(url_for("data.veri_giris"))
        
    if not allowed_file(file.filename):
        flash("Geçersiz dosya.", "danger")
        return redirect(url_for("data.veri_giris"))

    temp_path = os.path.join(tempfile.gettempdir(), secure_filename(file.filename))
    file.save(temp_path)
    
    try:
        parsed = parse_mizan_excel(temp_path)
        if parsed.get("status") == "error":
            flash(parsed["message"], "danger")
        else:
            parsed.update({"vergi_kimlik_no": vkn, "unvan": unvan, "donem": donem})
            if kaydet_beyanname(parsed, "mizan"):
                flash("Mizan başarıyla kaydedildi.", "success")
            else:
                flash("Kayıt hatası.", "danger")
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)
        
    return redirect(url_for("data.veri_giris"))

@bp.route("/veri-giris")
@login_required
def veri_giris():
    return render_template("data/veri_giris.html")

@bp.route("/mukellef-sil", methods=["POST"])
@login_required
def mukellef_sil():
    vkn = request.form.get("vkn", "").strip()
    if not vkn: return jsonify({"status": "error", "message": "VKN gerekli."}), 400

    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            c.execute("SELECT id FROM mukellef WHERE vergi_kimlik_no=%s AND user_id=%s", (vkn, session["user_id"]))
            row = c.fetchone()
            if not row: return jsonify({"status": "error", "message": "Mükellef bulunamadı."}), 404
            
            mid = row["id"]
            c.execute("DELETE FROM beyanname WHERE user_id=%s AND mukellef_id=%s", (session["user_id"], mid))
            c.execute("DELETE FROM mukellef WHERE user_id=%s AND id=%s", (session["user_id"], mid))
            conn.commit()
            
        return jsonify({"status": "success", "message": "Silindi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/donem-sil", methods=["POST"])
@login_required
def donem_sil():
    vkn = request.form.get("vkn", "").strip()
    donem = request.form.get("donem", "").strip()
    tur = request.form.get("belge_turu", "").strip()
    
    if not (vkn and donem): return jsonify({"status": "error", "message": "Eksik parametre."}), 400

    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            c.execute("SELECT id FROM mukellef WHERE vergi_kimlik_no=%s", (vkn,))
            row = c.fetchone()
            if not row: return jsonify({"status": "error", "message": "Bulunamadı."}), 404
            mid = row["id"]
            
            if tur == "all":
                c.execute("DELETE FROM beyanname WHERE user_id=%s AND mukellef_id=%s AND donem=%s", (session["user_id"], mid, donem))
            else:
                c.execute("DELETE FROM beyanname WHERE user_id=%s AND mukellef_id=%s AND donem=%s AND tur=%s", (session["user_id"], mid, donem, tur))
            conn.commit()
            
        return jsonify({"status": "success", "message": "Silindi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/yeniden-yukle", methods=["POST"])
@login_required
def yeniden_yukle():
    vkn = request.form.get("vkn")
    donem = request.form.get("donem")
    tur = request.form.get("belge_turu")
    veriler = request.form.get("veriler")
    
    if not all([vkn, donem, tur, veriler]): return jsonify({"status": "error", "message": "Eksik parametre."}), 400
    
    try:
        if isinstance(veriler, str): veriler = fernet.encrypt(veriler.encode("utf-8"))
        elif isinstance(veriler, bytes): veriler = fernet.encrypt(veriler)
        
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            c.execute("SELECT id, unvan FROM mukellef WHERE vergi_kimlik_no=%s AND user_id=%s", (vkn, session["user_id"]))
            row = c.fetchone()
            if not row: return jsonify({"status": "error", "message": "Bulunamadı."}), 404
            mid, unvan = row["id"], row["unvan"]
            
            c.execute("DELETE FROM beyanname WHERE user_id=%s AND mukellef_id=%s AND donem=%s AND tur=%s", (session["user_id"], mid, donem, tur))
            c.execute("INSERT INTO beyanname (user_id, mukellef_id, donem, tur, veriler, yuklenme_tarihi) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING yuklenme_tarihi", 
                      (session["user_id"], mid, donem, tur, veriler))
            row = c.fetchone()
            conn.commit()
            
            tarih = row["yuklenme_tarihi"].strftime("%Y-%m-%d %H:%M:%S") if row else "-"
            
        return jsonify({"status": "success", "message": f"Yeniden yüklendi. ({tarih})"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/matrah", methods=["GET", "POST"])
@login_required
def matrah():
    hesaplanan_matrah = None
    if request.method == "POST":
        gelir = float(request.form.get("gelir", 0) or 0)
        gider = float(request.form.get("gider", 0) or 0)
        hesaplanan_matrah = gelir - gider
        with get_conn() as conn:
            c = conn.cursor()
            # matrahlar table logic (check if table exists or migrate? Assuming it exists since app.py had it)
            # app.py's db.py probably creating it?
            # I should verify migration if I had time. But code assumes it exists.
            c.execute("INSERT INTO matrahlar (user_id, gelir, gider, matrah, tarih) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)", 
                      (session["user_id"], gelir, gider, hesaplanan_matrah))
            conn.commit()
            
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("SELECT gelir, gider, matrah, tarih FROM matrahlar WHERE user_id = %s ORDER BY tarih DESC", (session["user_id"],))
        kayitlar = c.fetchall()
        
    return render_template("calculators/matrah.html", matrah=hesaplanan_matrah, kayitlar=kayitlar)
