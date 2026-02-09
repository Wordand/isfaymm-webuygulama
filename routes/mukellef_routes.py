from flask import Blueprint, render_template, request, jsonify, session
from services.db import get_conn
from auth import login_required
import psycopg2.extras

bp = Blueprint('mukellef', __name__)

@bp.route("/mukellef-yonetimi")
@login_required
def index():
    user_id = session.get("user_id")
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("""
            SELECT m.*, 
                   (SELECT COUNT(*) FROM kdv_files WHERE mukellef_id = m.id AND is_active = TRUE) as active_files,
                   (SELECT COALESCE(SUM(amount_request), 0) FROM kdv_files WHERE mukellef_id = m.id AND is_active = TRUE) as total_request
            FROM mukellef m 
            WHERE m.user_id = %s 
            ORDER BY m.unvan ASC
        """, (user_id,))
        mukellefler = c.fetchall()
    return render_template("mukellef/index.html", mukellefler=mukellefler)

@bp.route("/api/mukellef-listesi")
@login_required
def listesi():
    """Aktif kullanıcının mükellef listesini JSON olarak getirir"""
    uid = session.get("user_id")
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("SELECT id, vergi_kimlik_no, unvan FROM mukellef WHERE user_id = %s ORDER BY unvan ASC", (uid,))
        rows = [dict(r) for r in c.fetchall()]
    return jsonify(rows)

@bp.route("/api/mukellef-ekle", methods=["POST"])
@login_required
def ekle():
    data = request.get_json()
    vkn = data.get("vergi_kimlik_no", "").strip()
    unvan = data.get("unvan", "").strip()
    vergi_dairesi = data.get("vergi_dairesi", "").strip()
    ilgili_memur = data.get("ilgili_memur", "").strip()
    
    if not vkn or not unvan:
        return jsonify({"status": "error", "message": "VKN ve Unvan boş olamaz."}), 400
        
    user_id = session.get("user_id")
    try:
        with get_conn() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO mukellef (user_id, vergi_kimlik_no, unvan, vergi_dairesi, ilgili_memur) VALUES (%s, %s, %s, %s, %s)",
                (user_id, vkn, unvan, vergi_dairesi, ilgili_memur)
            )
            conn.commit()
        return jsonify({"status": "success", "message": "Mükellef başarıyla eklendi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/api/mukellef-guncelle", methods=["POST"])
@login_required
def guncelle():
    data = request.get_json()
    mid = data.get("id")
    vkn = data.get("vergi_kimlik_no", "").strip()
    unvan = data.get("unvan", "").strip()
    vergi_dairesi = data.get("vergi_dairesi", "").strip()
    ilgili_memur = data.get("ilgili_memur", "").strip()
    
    if not mid or not vkn or not unvan:
        return jsonify({"status": "error", "message": "Eksik bilgi."}), 400
        
    user_id = session.get("user_id")
    try:
        with get_conn() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE mukellef SET vergi_kimlik_no=%s, unvan=%s, vergi_dairesi=%s, ilgili_memur=%s WHERE id=%s AND user_id=%s",
                (vkn, unvan, vergi_dairesi, ilgili_memur, mid, user_id)
            )
            conn.commit()
        return jsonify({"status": "success", "message": "Mükellef güncellendi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/api/mukellef-sil", methods=["POST"])
@login_required
def sil():
    data = request.get_json()
    mid = data.get("id")
    user_id = session.get("user_id")
    
    if not mid:
        return jsonify({"status": "error", "message": "ID gerekli."}), 400
        
    try:
        with get_conn() as conn:
            c = conn.cursor()
            # Silme işleminden önce beyannameleri ve teşvik belgelerini de kontrol etmek gerekebilir 
            # ancak veritabanında ON DELETE CASCADE varsa sorun olmaz. 
            # Ama biz güvenli gidelim.
            c.execute("DELETE FROM beyanname WHERE mukellef_id=%s AND user_id=%s", (mid, user_id))
            c.execute("DELETE FROM tesvik_belgeleri WHERE mukellef_id=%s AND user_id=%s", (mid, user_id))
            c.execute("DELETE FROM mukellef WHERE id=%s AND user_id=%s", (mid, user_id))
            conn.commit()
        return jsonify({"status": "success", "message": "Mükellef ve ilgili tüm veriler silindi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/api/mukellef-sec", methods=["POST"])
@login_required
def sec():
    data = request.get_json()
    mukellef_id = data.get("id")
    user_id = session.get("user_id")

    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            c.execute("SELECT id, vergi_kimlik_no, unvan FROM mukellef WHERE id = %s AND user_id = %s", (mukellef_id, user_id))
            row = c.fetchone()

        if not row:
            return jsonify({"status": "error", "message": "Mükellef bulunamadı."}), 404

        session["aktif_mukellef_id"] = row["id"]
        session["aktif_mukellef_vkn"] = row["vergi_kimlik_no"]
        session["aktif_mukellef_unvan"] = row["unvan"]

        return jsonify({"status": "success", "unvan": row["unvan"]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
