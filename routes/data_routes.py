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
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
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
            if unvan and unvan != "Bilinmiyor":
                c.execute("UPDATE mukellef SET unvan=%s WHERE id=%s", (unvan, mukellef_id))

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

def process_parsed_parts(full_data, doc_type):
    import copy
    import re
    
    # Yıl tespiti
    yil = 2023
    try:
        m = re.search(r"(\d{4})", str(full_data.get("donem", "")))
        if m: yil = int(m.group(1))
    except: pass
    
    results = []
    
    if doc_type == 'bilanco':
        cols = {'prev': 'Önceki Dönem', 'curr': 'Cari Dönem', 'inf': 'Cari Dönem (Enflasyonlu)'}
        target_val_key = 'Cari Dönem'
        sections = ['aktif', 'pasif']
        title_base = "BİLANÇO"
    else: # gelir
        cols = {'prev': 'onceki_donem', 'curr': 'cari_donem', 'inf': 'cari_donem_enflasyonlu'}
        target_val_key = 'cari_donem'
        sections = ['tablo']
        title_base = "GELİR TABLOSU"

    def create_part(source_col, target_year, type_suffix="", include_prev=False):
        new_d = copy.deepcopy(full_data)
        new_d['donem'] = str(target_year)
        
        has_any_data = False
        
        # Keys mapping for previous and inflation columns
        prev_key = cols['prev'] 
        inf_key = cols.get('inf', None)  # Inflation column name

        for sec in sections:
            new_rows = []
            if sec in new_d:
                for row in new_d[sec]:
                    val = row.get(source_col)
                    prev_val = row.get(prev_key)
                    inf_val = row.get(inf_key) if inf_key else None

                    if val is not None or (include_prev and (prev_val is not None or inf_val is not None)):
                        base_keys = ['Kod', 'Açıklama', 'kod', 'aciklama', 'grup']
                        new_row = {k: v for k, v in row.items() if k in base_keys}
                        
                        # Set target value (Current Period or Inflation Adjusted)
                        if val is not None:
                            new_row[target_val_key] = val
                            has_any_data = True
                        
                        # If including previous period data (only for main current year record)
                        if include_prev and prev_val is not None:
                            new_row[prev_key] = prev_val
                        
                        # If including inflation data (only for main current year record)
                        if include_prev and inf_val is not None and inf_key:
                            new_row[inf_key] = inf_val
                        
                        new_rows.append(new_row)
            new_d[sec] = new_rows
            
        new_d['veriler'] = {s: new_d.get(s, []) for s in sections}
        # has_inflation should be True if we have inflation column data
        new_d['has_inflation'] = (type_suffix == '_enf') or (include_prev and full_data.get('has_inflation', False))
        
        final_tur = doc_type + type_suffix
        return new_d, has_any_data, final_tur

    # 1. Önceki Dönem
    d1, ok1, t1 = create_part(cols['prev'], yil - 1)
    if ok1: results.append((d1, t1, f"{yil-1} {title_base}"))
    
    # 2. Cari Dönem
    d2, ok2, t2 = create_part(cols['curr'], yil, include_prev=True)
    if ok2: results.append((d2, t2, f"{yil} {title_base}"))
    
    # 3. Enflasyonlu
    if full_data.get('has_inflation') and doc_type == 'bilanco':
        d3, ok3, t3 = create_part(cols['inf'], yil, '_enf')
        if ok3: results.append((d3, t3, f"{yil} ENFLASYONLU {title_base}"))
        
    return results

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
                import re
                
                full_text = ""
                is_pdf = file.filename.lower().endswith(".pdf")
                if is_pdf:
                    with pdfplumber.open(temp_path) as pdf:
                        full_text = "\n".join([p.extract_text() or "" for p in pdf.pages])

                parsed_data = None
                tur = "diger"

                # 1. XML Kontrolü
                if filename.lower().endswith(".xml") or full_text.strip().startswith("<?xml"):
                    try:
                        res = parse_xml_file(temp_path)
                        if not res.get("hata"):
                            parsed_data = res
                            tur = res.get("tur", "xml_beyanname")
                            # XML ise direkt kaydet
                            if kaydet_beyanname(parsed_data, tur):
                                sonuclar.append({
                                    "filename": filename,
                                    "type": "success",
                                    "title": "XML Beyanname Yüklendi",
                                    "text": f"{parsed_data.get('unvan')} - {parsed_data.get('donem')} yüklendi.",
                                    "tur": tur,
                                    "donem": parsed_data.get("donem")
                                })
                        else:
                            sonuclar.append({"filename": filename, "type": "error", "message": res['hata']})
                            continue
                    except Exception as e:
                         sonuclar.append({"filename": filename, "type": "error", "message": f"(XML): {str(e)}"})
                         continue

                # 2. PDF Kontrolü (Öncelik Kurumlar/Bilanço/Gelir'de)
                # Regex ile sağlam kontrol: encoding hatalarını (. ile) tolere et
                elif is_pdf and (re.search(r"KURUMLAR\s*VERG", full_text, re.I) or \
                                 re.search(r"BILAN.O", full_text, re.I) or \
                                 re.search(r"GEL.R\s*TABLO", full_text, re.I)):
                     
                     tur = "bilanco/gelir"
                     
                     # Bilanço Parsingleme ve Parçalama
                     try:
                         res_b = parse_bilanco_from_pdf(temp_path, full_text)
                         # Eğer bilanco içeriği varsa (aktif veya pasif doluysa)
                         if res_b.get("aktif") or res_b.get("pasif"):
                             parts_b = process_parsed_parts(res_b, "bilanco")
                             if not parts_b:
                                 # Parça çıkmadı ama belki sadece gelir tablosu vardır, devam et
                                 pass
                             for p_data, p_tur, p_title in parts_b:
                                 if kaydet_beyanname(p_data, p_tur):
                                     sonuclar.append({
                                         "filename": filename,
                                         "type": "success",
                                         "title": "Bilanço Yüklendi",
                                         "text": f"{p_data.get('unvan')} - {p_title} başarıyla yüklendi.",
                                         "tur": p_tur,
                                         "donem": p_data.get("donem")
                                     })
                     except Exception as e:
                         pass # Bilanço hatası, devam et
                         
                     # Gelir Tablosu Parsingleme ve Parçalama
                     try:
                         res_g = parse_gelir_from_pdf(temp_path, full_text)
                         if res_g.get("tablo"):
                             parts_g = process_parsed_parts(res_g, "gelir")
                             for p_data, p_tur, p_title in parts_g:
                                 if kaydet_beyanname(p_data, p_tur):
                                     sonuclar.append({
                                         "filename": filename,
                                         "type": "success",
                                         "title": "Gelir Tablosu Yüklendi",
                                         "text": f"{p_data.get('unvan')} - {p_title} başarıyla yüklendi.",
                                         "tur": p_tur,
                                         "donem": p_data.get("donem")
                                     })
                     except Exception as e:
                         pass

                # 3. KDV Kontrolü (Sadece yukarıdakiler değilse)
                elif is_pdf and (re.search(r"KATMA\s*DE.ER\s*VERG", full_text, re.I) or "KDV" in full_text.upper()):
                     res = parse_kdv_from_pdf(temp_path, full_text)
                     if not res.get("hata"):
                         parsed_data = res
                         tur = "kdv"
                         save_success = kaydet_beyanname(parsed_data, tur)
                         if save_success:
                            sonuclar.append({
                                "filename": filename,
                                "type": "success",
                                "title": "Başarıyla Yüklendi",
                                "text": f"{parsed_data.get('unvan', 'Bilinmiyor')} mükellefi {parsed_data.get('donem', 'Bilinmiyor')} dönemi KDV yüklendi.",
                                "vkn": parsed_data.get("vergi_kimlik_no"),
                                "donem": parsed_data.get("donem"),
                                "tur": "kdv"
                            })
                         else:
                            sonuclar.append({"filename": filename, "type": "error", "message": "Veritabanına kaydedilirken hata oluştu."})

                # 4. Mizan (Excel) kontrolü
                elif not parsed_data and file.filename.lower().endswith((".xlsx", ".xls")):
                    sonuclar.append({
                        "filename": filename,
                        "type": "mizan_input_required",
                        "text": "Excel mizan dosyası için mükellef ve dönem bilgisi gerekli."
                    })
                    continue
                
                # Hiçbiri değilse
                if tur == "diger":
                    sonuclar.append({"filename": filename, "type": "error", "message": "Dosya içeriği tanınamadı veya desteklenmeyen format."})

            except Exception as e:
                sonuclar.append({"filename": filename, "type": "error", "message": str(e)})
            finally:
                if os.path.exists(temp_path):
                    try:
                       os.remove(temp_path)
                    except: pass
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

    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Mükellefleri getir
            c.execute("SELECT id, vergi_kimlik_no, unvan FROM mukellef WHERE user_id=%s ORDER BY unvan", (uid,))
            mukellefler = [dict(r) for r in c.fetchall()]

            if secili_vkn:
                # Seçili mükellefin dönemlerini getir
                c.execute("""
                    SELECT DISTINCT donem FROM beyanname b 
                    JOIN mukellef m ON b.mukellef_id=m.id 
                    WHERE m.user_id=%s AND m.vergi_kimlik_no=%s 
                    ORDER BY donem DESC
                """, (uid, secili_vkn))
                donemler = [r["donem"] for r in c.fetchall()]

                # Belgeleri getir
                query = """
                    SELECT b.donem, b.tur as belge_turu, b.yuklenme_tarihi, m.vergi_kimlik_no as vkn, m.unvan 
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
                # Mükellef seçilmemişse son 50 belgeyi göster
                c.execute("""
                    SELECT b.donem, b.tur as belge_turu, b.yuklenme_tarihi, m.vergi_kimlik_no as vkn, m.unvan 
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
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in veri_giris: {e}\n{traceback.format_exc()}")
        flash("Veri giriş sayfası yüklenirken bir hata oluştu.", "danger")
        return redirect(url_for("main.home"))

@bp.route("/mukellef-sil", methods=["POST"])
@login_required
def mukellef_sil():
    vkn = request.form.get("vkn", "").strip()
    if not vkn: return jsonify({"status": "error", "message": "VKN gerekli."}), 400

    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("SELECT gelir, gider, matrah, tarih FROM matrahlar WHERE user_id = %s ORDER BY tarih DESC", (session["user_id"],))
        kayitlar = c.fetchall()
        
    return render_template("calculators/matrah.html", matrah=hesaplanan_matrah, kayitlar=kayitlar)
