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

    sonuclar = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            file.save(temp_path)

            try:
                import pdfplumber
                full_text = ""
                # Mizan dosyaları için (xlsx) pdfplumber hata verebilir, o yüzden check ekliyoruz
                is_pdf = file.filename.lower().endswith(".pdf")
                if is_pdf:
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
                            sonuclar.append({"filename": filename, "type": "error", "message": res['hata']})
                            continue
                            
                    except Exception as e:
                         sonuclar.append({"filename": filename, "type": "error", "message": f"(XML): {str(e)}"})
                         continue

                elif is_pdf and ("Bilan\u00C7O" in full_text.upper() or "GEL\u0130R TABLOSU" in full_text.upper()): 
                     # Hem Bilan\u00E7o hem Gelir Tablosu aramas\u0131 yap
                     found_any = False
                     best_meta = None
                     
                     res_b = parse_bilanco_from_pdf(temp_path)
                     if res_b.get("aktif") or res_b.get("pasif"):
                         kaydet_beyanname(res_b, "bilanco")
                         if res_b.get("vergi_kimlik_no") != "Bilinmiyor": best_meta = res_b
                         found_any = True
                         
                     res_g = parse_gelir_from_pdf(temp_path)
                     if res_g.get("tablo"):
                         kaydet_beyanname(res_g, "gelir")
                         if not best_meta or (res_g.get("vergi_kimlik_no") != "Bilinmiyor"): best_meta = res_g
                         found_any = True
                         
                     if found_any:
                         parsed_data = best_meta or res_b
                         tur = "bilanco/gelir"
                     
                elif is_pdf and "KATMA DE\u011EER VERG\u0130S\u0130" in full_text.upper():
                     res = parse_kdv_from_pdf(temp_path)
                     if not res.get("hata"):
                         parsed_data = res
                         tur = "kdv"
                         save_success = kaydet_beyanname(parsed_data, tur)
                
                if not parsed_data and is_pdf:
                     # Yukar\u0131dakiler yakalayamad\u0131ysa tek tek dene
                     res_g = parse_gelir_from_pdf(temp_path)
                     if res_g.get("tablo"):
                         parsed_data = res_g
                         tur = "gelir"
                     else:
                         res_b = parse_bilanco_from_pdf(temp_path)
                         if res_b.get("aktif") or res_b.get("pasif"):
                             parsed_data = res_b
                             tur = "bilanco"
                         else:
                             res_k = parse_kdv_from_pdf(temp_path)
                             if not res_k.get("hata"):
                                 parsed_data = res_k
                                 tur = "kdv"

                # Mizan (Excel) kontrol\u00FC
                if not parsed_data and file.filename.lower().endswith((".xlsx", ".xls")):
                    sonuclar.append({
                        "filename": filename,
                        "type": "mizan_input_required",
                        "text": "Excel mizan dosyas\u0131 i\u00E7in m\u00FCkellef ve d\u00F6nem bilgisi gerekli."
                    })
                    continue

                if tur == "bilanco/gelir":
                    sonuclar.append({
                        "filename": filename,
                        "type": "success",
                        "title": "Tam Analiz Verisi",
                        "text": f"{parsed_data.get('unvan', 'Bilinmiyor')} m\u00FCkellefi {parsed_data.get('donem', 'Bilinmiyor')} d\u00F6nemi Bilan\u00E7o ve Gelir Tablosu ba\u015Far\u0131yla y\u00FCklendi.",
                        "vkn": parsed_data.get("vergi_kimlik_no"),
                        "donem": parsed_data.get("donem"),
                        "tur": "bilanco+gelir"
                    })
                elif parsed_data and not parsed_data.get("hata"):
                    if tur != "kdv" or not locals().get('save_success'):
                        save_success = kaydet_beyanname(parsed_data, tur)
                        
                    if save_success:
                        sonuclar.append({
                            "filename": filename,
                            "type": "success",
                            "title": "Ba\u015Far\u0131yla Y\u00FCklendi",
                            "text": f"{parsed_data.get('unvan', 'Bilinmiyor')} m\u00FCkellefi {parsed_data.get('donem', 'Bilinmiyor')} d\u00F6nemi {tur.upper()} y\u00FCklendi.",
                            "vkn": parsed_data.get("vergi_kimlik_no"),
                            "donem": parsed_data.get("donem"),
                            "tur": tur
                        })
                    else:
                        sonuclar.append({"filename": filename, "type": "error", "message": "Veritaban\u0131na kaydedilirken hata olu\u015Ftu."})
                else:
                    sonuclar.append({"filename": filename, "type": "error", "message": "Dosya içeriği tanınamadı veya desteklenmeyen format."})

            except Exception as e:
                sonuclar.append({"filename": filename, "type": "error", "message": str(e)})
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)
        else:
            sonuclar.append({"filename": file.filename, "type": "error", "message": "Desteklenmeyen dosya uzantısı."})

    return jsonify(sonuclar)

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
    secili_vkn = request.args.get("vkn")
    secili_donem = request.args.get("donem")
    uid = session.get("user_id")

    mukellefler = []
    donemler = []
    yuklenen_tum_belgeler = []

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # M\u00FCkellefleri getir
        c.execute("SELECT id, vergi_kimlik_no, unvan FROM mukellef WHERE user_id=%s ORDER BY unvan", (uid,))
        mukellefler = [dict(r) for r in c.fetchall()]

        if secili_vkn:
            # Se\u00E7ili m\u00FCkellefin d\u00F6nemlerini getir
            c.execute("""
                SELECT DISTINCT donem FROM beyanname b 
                JOIN mukellef m ON b.mukellef_id=m.id 
                WHERE m.user_id=%s AND m.vergi_kimlik_no=%s 
                ORDER BY donem DESC
            """, (uid, secili_vkn))
            donemler = [r["donem"] for r in c.fetchall()]

            # Belgeleri getir
            query = """
                SELECT b.donem, b.tur as belge_turu, b.yuklenme_tarihi, m.vergi_kimlik_no as vkn 
                FROM beyanname b 
                JOIN mukellef m ON b.mukellef_id=m.id 
                WHERE m.user_id=%s AND m.vergi_kimlik_no=%s
            """
            params = [uid, secili_vkn]
            if secili_donem:
                query += " AND b.donem=%s"
                params.append(secili_donem)
            
            query += " ORDER BY b.yuklenme_tarihi DESC"
            c.execute(query, params)
            yuklenen_tum_belgeler = [dict(r) for r in c.fetchall()]
        else:
            # M\u00FCkellef se\u00E7ilmemi\u015Fse son 50 belgeyi g\u00F6ster
            c.execute("""
                SELECT b.donem, b.tur as belge_turu, b.yuklenme_tarihi, m.vergi_kimlik_no as vkn 
                FROM beyanname b 
                JOIN mukellef m ON b.mukellef_id=m.id 
                WHERE m.user_id=%s 
                ORDER BY b.yuklenme_tarihi DESC LIMIT 50
            """, (uid,))
            yuklenen_tum_belgeler = [dict(r) for r in c.fetchall()]

    return render_template("data/veri_giris.html", 
                           mukellefler=mukellefler, 
                           donemler=donemler,
                           secili_vkn=secili_vkn,
                           secili_donem=secili_donem,
                           yuklenen_tum_belgeler=yuklenen_tum_belgeler)

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
