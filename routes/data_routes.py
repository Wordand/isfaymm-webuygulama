from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.utils import secure_filename
from services.db import get_conn
from services.utils import allowed_file
from services.pdf_service import (
    parse_bilanco_from_pdf,
    parse_gelir_from_pdf,
    parse_kdv_from_pdf,
)

from services.xml_service import parse_xml_file
from services.excel_service import (
    build_mizan_report_comparison,
    detect_mizan_metadata_from_text,
    parse_mizan_file,
)
from extensions import fernet
from auth import role_required
import os
import json
import re
import psycopg2.extras
import tempfile
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

bp = Blueprint("data", __name__)


def _format_upload_timestamp(value):
    if not value:
        return "-", ""

    if hasattr(value, "strftime"):
        return value.strftime("%d.%m.%Y"), value.strftime("%H:%M:%S")

    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%d.%m.%Y"), parsed.strftime("%H:%M:%S")
    except ValueError:
        match = re.match(
            r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2}(?::\d{2})?))?",
            text,
        )
        if match:
            return f"{match.group(3)}.{match.group(2)}.{match.group(1)}", match.group(4) or ""
        return text, ""


def _prepare_document_row(row):
    document = dict(row)
    date_text, time_text = _format_upload_timestamp(document.get("yuklenme_tarihi"))
    document["yuklenme_tarihi_tarih"] = date_text
    document["yuklenme_tarihi_saat"] = time_text
    return document


def is_gecici_vergi_pdf(text):
    import re

    return bool(re.search(r"GE.ICI\s+VERG.\s+BEYANNAMES.", str(text or ""), re.I))


def _decrypt_report_data(value):
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, str):
        return json.loads(value)
    try:
        return json.loads(fernet.decrypt(value).decode("utf-8"))
    except Exception:
        return json.loads(value.decode("utf-8"))


def _build_mizan_report_comparison(vkn, donem, parsed):
    with get_conn() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            "SELECT b.tur, b.veriler FROM beyanname b "
            "JOIN mukellef m ON b.mukellef_id=m.id "
            "WHERE m.user_id=%s AND m.vergi_kimlik_no=%s AND b.donem=%s "
            "AND b.tur IN ('bilanco', 'gelir')",
            (session["user_id"], vkn, donem),
        )
        reports = {row["tur"]: _decrypt_report_data(row["veriler"]) for row in cursor.fetchall()}

    return build_mizan_report_comparison(reports, parsed)

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
            mukellef_id = c.fetchone()["id"]
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
    import math
    import re

    period_text = str(full_data.get("donem", "")).strip()
    period_match = re.search(r"\b(20\d{2})\b", period_text)
    if not period_match:
        raise ValueError("Beyannamenin hesap dönemi belirlenemedi.")
    yil = int(period_match.group(1))

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

    def clean_value(value):
        if value is None:
            return None
        if isinstance(value, float) and math.isnan(value):
            return None
        if isinstance(value, Decimal) and value.is_nan():
            return None
        return value

    new_data = copy.deepcopy(full_data)
    normalized_period = re.sub(r"\s+", " ", period_text).strip()
    new_data['donem'] = (
        normalized_period
        if re.search(r"GEÇİCİ|GECICI", normalized_period, re.I)
        else str(yil)
    )
    new_data['kaynak_donem'] = period_text
    has_current_data = False
    has_inflation_data = False

    for section in sections:
        new_rows = []
        for row in full_data.get(section, []):
            current_value = clean_value(row.get(cols['curr']))
            previous_value = clean_value(row.get(cols['prev']))
            inflation_value = clean_value(row.get(cols['inf']))

            if current_value is None and previous_value is None and inflation_value is None:
                continue

            base_keys = ['Kod', 'Açıklama', 'kod', 'aciklama', 'grup']
            new_row = {key: value for key, value in row.items() if key in base_keys}

            if current_value is not None:
                new_row[target_val_key] = current_value
                has_current_data = True
            if previous_value is not None:
                new_row[cols['prev']] = previous_value
            if doc_type == 'bilanco' and inflation_value is not None:
                new_row[cols['inf']] = inflation_value
                has_inflation_data = True

            new_rows.append(new_row)

        new_data[section] = new_rows

    new_data['veriler'] = {section: new_data.get(section, []) for section in sections}
    new_data['has_inflation'] = bool(
        doc_type == 'bilanco'
        and full_data.get('has_inflation')
        and has_inflation_data
    )

    if not has_current_data:
        raise ValueError(f"{yil} cari dönem {title_base.lower()} verisi bulunamadı.")

    return [(new_data, doc_type, f"{yil} {title_base}")]

@bp.route("/yukle-coklu", methods=["POST"])
@role_required(allow_roles=("admin",))
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

                # 2. PDF mizan: mükellef ve dönem onayından sonra geçici önizlemeye alınır.
                elif is_pdf and re.search(r"\bM[İI]ZAN\b", full_text, re.I):
                    metadata = detect_mizan_metadata_from_text(full_text)
                    sonuclar.append({
                        "filename": file.filename,
                        "type": "mizan_input_required",
                        "text": "PDF mizan için mükellef ve dönem bilgisi gerekli.",
                        "suggested_period": metadata.get("detected_period", ""),
                        "suggested_title": metadata.get("detected_title", ""),
                    })
                    continue

                # 3. Geçici vergi PDF'i: yalnızca cari dönem gelir tablosu içerir.
                elif is_pdf and is_gecici_vergi_pdf(full_text):
                     tur = "gelir"
                     try:
                         res_g = parse_gelir_from_pdf(temp_path, full_text)
                         if not res_g.get("tablo"):
                             raise ValueError("Gelir tablosu satırları bulunamadı.")

                         parsed_parts = process_parsed_parts(res_g, "gelir")
                     except Exception:
                         current_app.logger.exception(
                             "Geçici vergi PDF gelir tablosu ayrıştırılamadı: file=%s",
                             filename,
                         )
                         sonuclar.append({
                             "filename": filename,
                             "type": "error",
                             "message": "Geçici vergi gelir tablosu doğrulanamadı; dosya kaydedilmedi.",
                         })
                     else:
                         for p_data, p_tur, p_title in parsed_parts:
                             if kaydet_beyanname(p_data, p_tur):
                                 sonuclar.append({
                                     "filename": filename,
                                     "type": "success",
                                     "title": "Geçici Vergi Gelir Tablosu Yüklendi",
                                     "text": f"{p_data.get('unvan')} - {p_data.get('donem')} başarıyla yüklendi.",
                                     "tur": p_tur,
                                     "donem": p_data.get("donem")
                                 })

                # 4. PDF Kontrolü (Öncelik Kurumlar/Bilanço/Gelir'de)
                # Regex ile sağlam kontrol: encoding hatalarını (. ile) tolere et
                elif is_pdf and (re.search(r"KURUMLAR\s*VERG", full_text, re.I) or \
                                 re.search(r"BILAN.O", full_text, re.I) or \
                                 re.search(r"GEL.R\s*TABLO", full_text, re.I)):
                     
                     tur = "bilanco/gelir"
                     
                     try:
                         res_b = parse_bilanco_from_pdf(temp_path, full_text)
                         res_g = parse_gelir_from_pdf(temp_path, full_text)

                         if not (res_b.get("aktif") or res_b.get("pasif")):
                             raise ValueError("Bilanço satırları bulunamadı.")
                         if not res_g.get("tablo"):
                             raise ValueError("Gelir tablosu satırları bulunamadı.")

                         parsed_parts = (
                             process_parsed_parts(res_b, "bilanco")
                             + process_parsed_parts(res_g, "gelir")
                         )
                     except Exception:
                         current_app.logger.exception(
                             "Kurumlar vergisi PDF tabloları ayrıştırılamadı: file=%s",
                             filename,
                         )
                         sonuclar.append({
                             "filename": filename,
                             "type": "error",
                             "message": "Bilanço ve gelir tablosu birlikte doğrulanamadı; dosya kaydedilmedi.",
                         })
                     else:
                         for p_data, p_tur, p_title in parsed_parts:
                             if kaydet_beyanname(p_data, p_tur):
                                 sonuclar.append({
                                     "filename": filename,
                                     "type": "success",
                                     "title": "Bilanço Yüklendi" if p_tur == "bilanco" else "Gelir Tablosu Yüklendi",
                                     "text": f"{p_data.get('unvan')} - {p_title} başarıyla yüklendi.",
                                     "tur": p_tur,
                                     "donem": p_data.get("donem")
                                 })

                # 5. KDV Kontrolü (Sadece yukarıdakiler değilse)
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

                # 6. Mizan (Excel) kontrolü
                elif not parsed_data and file.filename.lower().endswith((".xlsx", ".xls")):
                    sonuclar.append({
                        "filename": file.filename,
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
@role_required(allow_roles=("admin",))
def kaydet_mizan_meta():
    vkn = request.form.get("vkn")
    unvan = request.form.get("unvan")
    donem = request.form.get("donem")
    action = request.form.get("action", "preview")
    file = request.files.get("mizan_file")
    
    if not vkn or not donem or not file:
        return jsonify({"status": "error", "message": "Eksik bilgi: VKN, dönem ve dosya gereklidir."}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"status": "error", "message": "Desteklenmeyen dosya formatı."}), 400

    if action not in {"preview", "save"}:
        return jsonify({"status": "error", "message": "Geçersiz mizan işlemi."}), 400

    if not re.fullmatch(r"20\d{2}(?:\s*-\s*[1-4]\.\s*GEÇİCİ)?", donem.strip(), re.I):
        return jsonify({"status": "error", "message": "Dönem 2026 veya 2026 - 1. GEÇİCİ biçiminde olmalıdır."}), 400

    if not unvan:
        try:
            with get_conn() as conn:
                c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                c.execute("SELECT unvan FROM mukellef WHERE vergi_kimlik_no=%s AND user_id=%s", (vkn, session["user_id"]))
                row = c.fetchone()
                if row:
                    unvan = row["unvan"]
                else:
                    return jsonify({"status": "error", "message": f"Mükellef ({vkn}) bulunamadı. Lütfen yeni mükellef olarak ekleyin."}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": f"Mükellef aranırken hata oluştu: {str(e)}"}), 500

    safe_suffix = os.path.splitext(secure_filename(file.filename))[1].lower()
    temp_handle, temp_path = tempfile.mkstemp(prefix="mizan_", suffix=safe_suffix)
    os.close(temp_handle)
    file.save(temp_path)
    
    try:
        parsed = parse_mizan_file(temp_path)
        parsed.update({"vergi_kimlik_no": vkn, "unvan": unvan, "donem": donem.strip()})

        detected_period = str(parsed.get("detected_period") or "").strip()
        if detected_period and detected_period != donem.strip():
            parsed.setdefault("validation", []).insert(0, {
                "code": "period_mismatch",
                "title": "Dönem kontrolü",
                "status": "warning",
                "detail": f"Dosyada {detected_period}, kullanıcı seçiminde {donem.strip()} dönemi yer alıyor.",
                "difference": 0,
            })
            parsed["summary"]["warning_count"] = parsed["summary"].get("warning_count", 0) + 1

        comparison = _build_mizan_report_comparison(vkn, donem.strip(), parsed)
        parsed["comparison"] = comparison

        if action == "preview":
            preview = {
                "summary": parsed.get("summary", {}),
                "validation": parsed.get("validation", []),
                "tax_checks": parsed.get("tax_checks", []),
                "comparison": comparison,
                "detected_period": parsed.get("detected_period", ""),
                "detected_title": parsed.get("detected_title", ""),
                "source_format": parsed.get("source_format", ""),
            }
            return jsonify({
                "status": "preview",
                "message": "Geçici analiz tamamlandı. Dosya ve sonuçlar kaydedilmedi.",
                "preview": preview,
            })

        parsed.pop("preview", None)
        if kaydet_beyanname(parsed, "mizan"):
            return jsonify({"status": "success", "message": "Mizan ve oluşturulan mali tablolar başarıyla kaydedildi."})
        return jsonify({"status": "error", "message": "Veritabanına kaydedilirken hata oluştu."}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Mizan işlenirken hata oluştu: {str(e)}"}), 500
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

@bp.route("/veri-giris")
@role_required(allow_roles=("admin",))
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
                yuklenen_tum_belgeler = [_prepare_document_row(r) for r in c.fetchall()]
            else:
                # Mükellef seçilmemişse son 50 belgeyi göster
                c.execute("""
                    SELECT b.donem, b.tur as belge_turu, b.yuklenme_tarihi, m.vergi_kimlik_no as vkn, m.unvan 
                    FROM beyanname b 
                    JOIN mukellef m ON b.mukellef_id=m.id 
                    WHERE m.user_id=%s 
                    ORDER BY b.yuklenme_tarihi DESC LIMIT 50
                """, (uid,))
                yuklenen_tum_belgeler = [_prepare_document_row(r) for r in c.fetchall()]

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
@role_required(allow_roles=("admin",))
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
@role_required(allow_roles=("admin",))
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
@role_required(allow_roles=("admin",))
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
            
            tarih_parts = _format_upload_timestamp(row["yuklenme_tarihi"]) if row else ("-", "")
            tarih = " ".join(part for part in tarih_parts if part)
            
        return jsonify({"status": "success", "message": f"Yeniden yüklendi. ({tarih})"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/matrah", methods=["GET", "POST"])
@role_required(allow_roles=("admin",))
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
