from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from services.db import get_conn
from auth import login_required, kdv_access_required, api_kdv_access_required
import psycopg2.extras
from datetime import datetime

bp = Blueprint('kdv', __name__)

STATUS_STAGES = {
    'Listeler': [
        'Listeler hazırlanacak',
        'Listeler hazırlandı',
        'Listeler GİB\'e yüklendi',
        'İade dilekçesi girildi'
    ],
    'Tutar / Tahsilat': [
        'Nakit İade Tutarı hesaba geçti',
        'Teminat Tutarı hesaba geçti',
        'Teminat sonrası kalan tutar hesaba geçti',   
        'Mahsuben iade gerçekleşti',
        'Ön Kontrol Raporu Tutarı hesaba geçti',
        'Ön Kontrol Raporu Kalan Tutar hesaba geçti',
        'Tecil-Tekin gerçekleşti'
    ],
    'YMM Rapor Süreci': [
        'Karşıtlar gönderildi',
        'Karşıtlar tamamlandı',
        'Rapor onaylanacak',
        'Rapor onaylandı'
    ],
    'Vergi Dairesi (Süreç)': [
        'Kontrol Raporu oluştu',
        'Eksiklik yazısı geldi',
        'İzahat hazırlanıyor',
        'İzahat gönderildi'
    ],
    'Vergi Dairesi (Makam)': [
        'YMM Ofisinde',
        'Memurda',
        'Müdür Yardımcısında',
        'Müdürde',
        'Defterdarlıkta',
        'Muhasebede',
        'İade Tamamlandı'
    ]
}

@bp.route("/kdv-yonetimi")
@kdv_access_required
def index():
    return render_template("kdv/dashboard.html")

@bp.route("/kdv-arsiv")
@kdv_access_required
def archive():
    return render_template("kdv/arsiv.html")

@bp.route("/kdv-detay/<int:file_id>")
@kdv_access_required
def details(file_id):
    return render_template("kdv/detay.html", file_id=file_id, STATUS_STAGES=STATUS_STAGES)

@bp.route("/kdv-mukellefler")
@kdv_access_required
def mukellefler():
    user_id = session.get("user_id")
    role = session.get("role")
    
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        if role in ('admin', 'ymm'):
            # Tüm KDV mükellefleri
            c.execute("""
                SELECT m.*, 
                       (SELECT COUNT(*) FROM kdv_files WHERE mukellef_id = m.id AND is_active = TRUE) as active_files,
                       (SELECT COALESCE(SUM(amount_request), 0) FROM kdv_files WHERE mukellef_id = m.id AND is_active = TRUE) as total_request
                FROM kdv_mukellef m 
                ORDER BY m.unvan ASC
            """)
        else:
            # Sadece atanmış KDV mükellefleri
            c.execute("""
                SELECT m.*, 
                       (SELECT COUNT(*) FROM kdv_files WHERE mukellef_id = m.id AND is_active = TRUE) as active_files,
                       (SELECT COALESCE(SUM(amount_request), 0) FROM kdv_files WHERE mukellef_id = m.id AND is_active = TRUE) as total_request
                FROM kdv_mukellef m 
                JOIN kdv_user_assignments kua ON kua.mukellef_id = m.id
                WHERE kua.user_id = %s
                ORDER BY m.unvan ASC
            """, (user_id,))
            
        mukellefler = c.fetchall()
        
    return render_template("kdv/mukellefler.html", mukellefler=mukellefler)

@bp.route("/kdv-ayarlar")
@kdv_access_required
def settings():
    if session.get("role") not in ('admin', 'ymm'):
        flash("Ayarlar sayfasına sadece yönetici ve YMM erişebilir.", "warning")
        return redirect(url_for('kdv.index'))
    return render_template("kdv/settings.html")

@bp.route("/kdv-portal/verify", methods=["GET", "POST"])
@login_required 
def verify_pin():
    if not session.get("has_kdv_access") and session.get("username", "").lower() != "admin":
        flash("Bu alana erişim yetkiniz bulunmamaktadır.", "danger")
        return redirect(url_for("main.home"))

    if request.method == "POST":
        input_pin = request.form.get("pin")
        user_id = session.get("user_id")
        
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("SELECT kdv_pin FROM users WHERE id = %s", (user_id,))
            user = c.fetchone()
            
            db_pin = user.get("kdv_pin", "1234") if user else "1234"
            if not db_pin: db_pin = "1234"
            
            if input_pin == db_pin:
                session["kdv_portal_pin_verified"] = True
                flash("KDV Portalı kilidi açıldı. Hoş geldiniz.", "success")
                return redirect(url_for("kdv.index"))
            else:
                flash("Hatalı PIN kodu! Lütfen tekrar deneyiniz.", "danger")
                
    return render_template("kdv/verify_pin.html")

# --- API ENDPOINTS ---

@bp.route("/api/kdv/stats")
@api_kdv_access_required
def get_stats():
    user_id = session.get("user_id")
    role = session.get("role")
    mukellef_id = request.args.get('mukellef_id') or request.args.get('mukellef') # Support both keys
    
    def parse_money(val):
        """Helper to parse currency strings like '1.250.000,00' to float."""
        if not val: return 0.0
        if isinstance(val, (int, float)): return float(val)
        # Assuming format 1.250.000,00 (Turkish)
        # Remove dots, replace comma with dot
        clean = str(val).replace('.', '').replace(',', '.')
        # Also clean currency symbols if any
        clean = clean.replace('₺', '').replace('TL', '').strip()
        try:
            return float(clean)
        except:
            return 0.0

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Base query filter
        base_filter = " WHERE is_active = TRUE"
        params = []
        
        if role not in ('admin', 'ymm'):
            base_filter += " AND user_id = %s"
            params.append(user_id)
            
        if mukellef_id:
            base_filter += " AND mukellef_id = %s"
            params.append(mukellef_id)
            
        # Fetch all active file data to process in Python (safer for mixed formats)
        c.execute(f"SELECT status, amount_request, type, subject, date FROM kdv_files {base_filter}", tuple(params))
        all_files = c.fetchall()
        
        pending_amount = 0.0
        completed_amount = 0.0
        missing_docs_count = 0
        guarantee_amount = 0.0
        
        status_dist_map = {} # status -> count

        for f in all_files:
            amt = parse_money(f['amount_request'])
            status = f['status'] or 'Bilinmiyor'
            
            # 1. Pending (Not completed)
            if status not in ('İade Tamamlandı', 'İade Alındı'):
                pending_amount += amt
                
            # 2. Completed
            else:
                completed_amount += amt
                
            # 3. Missing Docs
            if status == 'Eksiklik yazısı geldi':
                missing_docs_count += 1
                
            # 4. Guarantee
            subj = (f.get('subject') or '').lower()
            typ = (f.get('type') or '').lower()
            if 'teminat' in subj or 'teminat' in typ:
                guarantee_amount += amt
                
            # Status Dist
            status_dist_map[status] = status_dist_map.get(status, 0) + 1
            
        # Convert map to list
        status_dist = [{'status': k, 'count': v} for k, v in status_dist_map.items()]

        # Chart Data: Monthly Trend (Last 6 Months)
        # Fetch raw date and amount, then process in Python to be safe against format issues
        c.execute(f"SELECT date, amount_request FROM kdv_files {base_filter}", tuple(params))
        all_files = c.fetchall()
        
        from collections import defaultdict
        monthly_totals = defaultdict(float)
        
        for f in all_files:
            try:
                d_str = f['date'] # Expected 'DD.MM.YYYY' or similar
                if not d_str: continue
                
                # Simple parsing logic
                if '.' in d_str:
                    parts = d_str.split('.')
                    if len(parts) == 3:
                        # parts[2] = Year, parts[1] = Month
                        # Verify lengths to ensure correct format
                        if len(parts[2]) == 4 and len(parts[1]) == 2:
                            key = f"{parts[2]}-{parts[1]}"
                            monthly_totals[key] += float(f['amount_request'] or 0)
                elif '-' in d_str:
                    # Maybe YYYY-MM-DD
                    parts = d_str.split('-')
                    if len(parts) == 3:
                         if len(parts[0]) == 4 and len(parts[1]) == 2:
                            key = f"{parts[0]}-{parts[1]}"
                            monthly_totals[key] += float(f['amount_request'] or 0)
            except:
                continue
                
        # Sort by month key (YYYY-MM) descending and take top 6
        sorted_months = sorted(monthly_totals.keys(), reverse=True)[:6]
        
        trend_labels = []
        trend_data = []
        
        tr_months = {'01': 'Oca', '02': 'Şub', '03': 'Mar', '04': 'Nis', '05': 'May', '06': 'Haz', 
                     '07': 'Tem', '08': 'Ağu', '09': 'Eyl', '10': 'Eki', '11': 'Kas', '12': 'Ara'}

        for m_str in reversed(sorted_months):
            parts = m_str.split('-')
            label = tr_months.get(parts[1], parts[1])
            trend_labels.append(label)
            trend_data.append(monthly_totals[m_str])

        stats = {
            "pending_amount": float(pending_amount),
            "completed_amount": float(completed_amount),
            "missing_docs_count": int(missing_docs_count),
            "guarantee_amount": float(guarantee_amount),
            "status_dist": status_dist,
            "trend_labels": trend_labels,
            "trend_data": trend_data
        }
        
    return jsonify(stats)

@bp.route("/api/kdv/files")
@api_kdv_access_required
def list_files():
    user_id = session.get("user_id")
    role = session.get("role")
    
    is_active = request.args.get('active', 1, type=int)
    mukellef_filter = request.args.get('mukellef_id') or request.args.get('mukellef')
    status_filter = request.args.get('status')
    filter_type = request.args.get('filter_type') # e.g. 'guarantee'
    
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Base Query
        query = """
            SELECT f.*, m.unvan as client_name 
            FROM kdv_files f 
            JOIN kdv_mukellef m ON f.mukellef_id = m.id 
            WHERE f.is_active = %s
        """
        params = [True if is_active == 1 else False]
        
        # Role Filter
        if role not in ('admin', 'ymm'):
            query += " AND f.user_id = %s"
            params.append(user_id)
            
        # Mukellef Filter
        if mukellef_filter:
            query += " AND f.mukellef_id = %s"
            params.append(mukellef_filter)
            
        # Status Filter
        if status_filter:
            query += " AND f.status = %s"
            params.append(status_filter)
            
        # Special Filter Types
        if filter_type == 'guarantee':
            query += " AND (f.subject ILIKE %s OR f.type ILIKE %s)"
            params.extend(['%Teminat%', '%Teminat%'])
            
        query += " ORDER BY f.id DESC"
        
        c.execute(query, tuple(params))
        files = [dict(r) for r in c.fetchall()]
        
    return jsonify(files)

@bp.route("/api/kdv/users")
@api_kdv_access_required
def get_kdv_users():
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Fetch users + count of assigned mukellefs
        c.execute("""
            SELECT u.id, u.username, u.role, u.has_kdv_access,
                   (SELECT COUNT(*) FROM kdv_user_assignments WHERE user_id = u.id) as assigned_count
            FROM users u
            WHERE u.has_kdv_access != 0 OR u.role = 'admin'
            ORDER BY u.id ASC
        """)
        users_raw = c.fetchall()
        users = [dict(r) for r in users_raw]
    return jsonify(users)

@bp.route("/api/kdv/all-mukellefs")
@api_kdv_access_required
def get_all_kdv_mukellefs():
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("SELECT id, unvan, vkn FROM kdv_mukellef ORDER BY unvan ASC")
        rows = c.fetchall()
    return jsonify([dict(r) for r in rows])

@bp.route("/api/kdv/update-pin", methods=["POST"])
@api_kdv_access_required
def update_kdv_pin():
    if session.get("role") not in ('admin', 'ymm'):
        return jsonify({"status": "error", "message": "PIN değiştirme yetkiniz bulunmamaktadır."}), 403
        
    new_pin = request.json.get('pin')
    if not new_pin or len(new_pin) < 4:
        return jsonify({"status": "error", "message": "Geçersiz PIN formatı."}), 400
        
    user_id = session.get("user_id")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET kdv_pin = %s WHERE id = %s", (new_pin, user_id))
        conn.commit()
    return jsonify({"status": "success", "message": "Portal PIN başarıyla güncellendi."})

# Helper for System Logs
def kdv_log_action(user_name, action, description):
    try:
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS kdv_system_logs (
                    id SERIAL PRIMARY KEY,
                    date TEXT,
                    user_name TEXT,
                    action TEXT,
                    description TEXT
                )
            """)
            c.execute("""
                INSERT INTO kdv_system_logs (date, user_name, action, description)
                VALUES (%s, %s, %s, %s)
            """, (datetime.now().strftime("%d.%m.%Y %H:%M"), user_name, action, description))
            conn.commit()
    except Exception as e:
        print(f"Log Error: {e}")

# Note: add_kdv_user removed as per user request (should not add users from here)



@bp.route("/api/kdv/user-assignments/<int:user_id>")
@api_kdv_access_required
def get_user_assignments(user_id):
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT m.id, m.unvan, m.vkn
            FROM kdv_user_assignments a
            JOIN kdv_mukellef m ON a.mukellef_id = m.id
            WHERE a.user_id = %s
        """, (user_id,))
        assignments_raw = c.fetchall()
        assignments = [dict(r) for r in assignments_raw]
    return jsonify(assignments)

@bp.route("/api/kdv/assign-mukellef", methods=["POST"])
@api_kdv_access_required
def assign_mukellef():
    # Sadece Admin ve YMM atama yapabilir
    if session.get("role") not in ('admin', 'ymm'):
        return jsonify({"status": "error", "message": "Atama yapma yetkiniz bulunmamaktadır."}), 403
        
    data = request.json
    user_id = data.get('user_id')
    mukellef_id = data.get('mukellef_id')
    
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO kdv_user_assignments (user_id, mukellef_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, mukellef_id) DO NOTHING
            """, (user_id, mukellef_id))
            
            # Log Action
            c.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            target_user = c.fetchone()[0]
            c.execute("SELECT unvan FROM kdv_mukellef WHERE id = %s", (mukellef_id,))
            target_mukellef = c.fetchone()[0]
            
            conn.commit()
            
            kdv_log_action(session.get('username', 'Admin'), "Yetki Atama", f"\"{target_user}\" kullanıcısına \"{target_mukellef}\" yetkisi atandı.")
            
        except Exception as e:
            conn.rollback()
            return jsonify({"status": "error", "message": str(e)}), 500
            
    return jsonify({"status": "success", "message": "Atama başarıyla yapıldı."})

@bp.route("/api/kdv/remove-assignment", methods=["POST"])
@api_kdv_access_required
def remove_assignment():
    # Sadece Admin ve YMM atama silebilir
    if session.get("role") not in ('admin', 'ymm'):
        return jsonify({"status": "error", "message": "Atama silme yetkiniz bulunmamaktadır."}), 403
        
    data = request.json
    user_id = data.get('user_id')
    mukellef_id = data.get('mukellef_id')
    
    with get_conn() as conn:
        c = conn.cursor()
        
        # Get names for logging before delete
        c.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        target_user_row = c.fetchone()
        target_user = target_user_row[0] if target_user_row else "Bilinmeyen"
        
        c.execute("SELECT unvan FROM kdv_mukellef WHERE id = %s", (mukellef_id,))
        target_mukellef_row = c.fetchone()
        target_mukellef = target_mukellef_row[0] if target_mukellef_row else "Bilinmeyen"

        c.execute("DELETE FROM kdv_user_assignments WHERE user_id = %s AND mukellef_id = %s", (user_id, mukellef_id))
        conn.commit()
        
        kdv_log_action(session.get('username', 'Admin'), "Yetki Kaldırma", f"\"{target_user}\" kullanıcısının \"{target_mukellef}\" yetkisi kaldırıldı.")
            
    return jsonify({"status": "success", "message": "Atama kaldırıldı."})

@bp.route("/api/kdv/delete-user/<int:user_id>", methods=["POST"])
@api_kdv_access_required
def delete_kdv_user(user_id):
    if session.get("role") not in ('admin', 'ymm'):
        return jsonify({"status": "error", "message": "Yetki kaldırma yetkiniz bulunmamaktadır."}), 403
    with get_conn() as conn:
        c = conn.cursor()
        # KDV yetkisini kaldır, silme
        c.execute("UPDATE users SET has_kdv_access = 0 WHERE id = %s", (user_id,))
        # Atamaları da temizle
        c.execute("DELETE FROM kdv_user_assignments WHERE user_id = %s", (user_id,))
        conn.commit()
    return jsonify({"status": "success", "message": "Kullanıcının KDV yetkisi kaldırıldı."})

@bp.route("/api/kdv/logs")
@api_kdv_access_required
def get_kdv_logs():
    if session.get("role") != 'admin':
        return jsonify({"status": "error", "message": "Yetkisiz erişim"}), 403
        
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Check if table exists
        c.execute("SELECT to_regclass('public.kdv_system_logs')")
        if not c.fetchone()[0]:
             return jsonify([])
             
        c.execute("SELECT * FROM kdv_system_logs ORDER BY id DESC LIMIT 50")
        logs = [dict(r) for r in c.fetchall()]
    return jsonify(logs)

@bp.route("/api/kdv/logs/delete", methods=["POST"])
@api_kdv_access_required
def delete_all_logs():
    if session.get("role") != 'admin':
        return jsonify({"status": "error", "message": "Yetkisiz erişim"}), 403
        
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM kdv_system_logs")
        conn.commit()
    return jsonify({"status": "success"})
    
@bp.route("/api/kdv/all-mukellefs")
@api_kdv_access_required
def get_all_mukellefs():
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("SELECT id, unvan, vkn FROM kdv_mukellef ORDER BY unvan ASC")
        rows = c.fetchall()
        mukellefs = [dict(r) for r in rows]
    return jsonify(mukellefs)

@bp.route("/api/kdv/file/<int:file_id>")
@api_kdv_access_required
def get_file(file_id):
    user_id = session.get("user_id")
    role = session.get("role")
    
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if role in ('admin', 'ymm'):
            c.execute("""
                SELECT f.*, m.unvan as client_name 
                FROM kdv_files f
                JOIN kdv_mukellef m ON f.mukellef_id = m.id
                WHERE f.id = %s
            """, (file_id,))
        else:
            c.execute("""
                SELECT f.*, m.unvan as client_name 
                FROM kdv_files f
                JOIN kdv_mukellef m ON f.mukellef_id = m.id
                WHERE f.id = %s AND f.user_id = %s
            """, (file_id, user_id))
            
        file_row = c.fetchone()
        if not file_row:
            return jsonify({"status": "error", "message": "Dosya bulunamadı veya yetkiniz yok."}), 404
            
        file = dict(file_row)
        
        c.execute("SELECT * FROM kdv_history WHERE file_id = %s ORDER BY id DESC", (file_id,))
        file['history'] = [dict(r) for r in c.fetchall()]
        
        c.execute("SELECT * FROM kdv_documents WHERE file_id = %s ORDER BY id DESC", (file_id,))
        file['documents'] = [dict(r) for r in c.fetchall()]
        
    return jsonify(file)

@bp.route("/api/kdv/add", methods=["POST"])
@api_kdv_access_required
def add_file():
    data = request.get_json()
    user_id = session.get("user_id")
    
    try:
        with get_conn() as conn:
            c = conn.cursor()
            
            query = """
                INSERT INTO kdv_files (
                    mukellef_id, user_id, period, subject, type, amount_request, status, date, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """
            params = (
                data['mukellef_id'], user_id, data['period'], data['subject'], 
                data['type'], data['amount_request'], 'Listeler hazırlanacak',
                datetime.now().strftime("%d.%m.%Y")
            )
            
            from services.db import USE_SQLITE
            if not USE_SQLITE:
                query += " RETURNING id"
                c.execute(query, params)
                res = c.fetchone()
                file_id = res['id'] if isinstance(res, dict) else res[0]
            else:
                c.execute(query, params)
                file_id = c.lastrowid
            
            c.execute("""
                INSERT INTO kdv_history (file_id, date, text)
                VALUES (%s, %s, 'Dosya oluşturuldu')
            """, (file_id, datetime.now().strftime("%d.%m.%Y %H:%M")))
            
            conn.commit()
        return jsonify({"status": "success", "file_id": file_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/api/kdv/update-status", methods=["POST"])
@api_kdv_access_required
def update_status():
    data = request.get_json()
    file_id = data.get('file_id')
    new_status = data.get('status')
    new_location = data.get('location')
    description = data.get('description', '')
    user_id = session.get("user_id")
    
    
    with get_conn() as conn:
        c = conn.cursor()
        
        # Auth Check
        if session.get('role') not in ('admin', 'ymm'):
             c.execute("SELECT id FROM kdv_files WHERE id = %s AND user_id = %s", (file_id, user_id))
             if not c.fetchone():
                 return jsonify({"status": "error", "message": "Yetkisiz erişim"}), 403

        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

        if new_status:
            c.execute("UPDATE kdv_files SET status = %s WHERE id = %s", (new_status, file_id))
            c.execute("""
                INSERT INTO kdv_history (file_id, date, text, description)
                VALUES (%s, %s, %s, %s)
            """, (file_id, now_str, new_status, description))
            
        if new_location:
            c.execute("UPDATE kdv_files SET location = %s WHERE id = %s", (new_location, file_id))
            # Log Location Change separately so it appears in Makam Timeline
            # We use the location name as 'text' so frontend filter catches it
            c.execute("""
                INSERT INTO kdv_history (file_id, date, text, description)
                VALUES (%s, %s, %s, %s)
            """, (file_id, now_str, new_location, description))
        conn.commit()
    return jsonify({"status": "success"})

@bp.route("/api/kdv/delete", methods=["POST"])
@api_kdv_access_required
def delete_file():
    file_id = request.get_json().get('id')
    user_id = session.get("user_id")
    role = session.get('role')
    
    with get_conn() as conn:
        c = conn.cursor()
        if role in ('admin', 'ymm'):
             c.execute("DELETE FROM kdv_files WHERE id = %s", (file_id,))
        else:
             c.execute("DELETE FROM kdv_files WHERE id = %s AND user_id = %s", (file_id, user_id))
        conn.commit()
    return jsonify({"status": "success"})

@bp.route("/api/kdv/tax-offices")
@api_kdv_access_required
def get_tax_offices():
    default_offices = [
        "Selçuk Vergi Dairesi", "Meram Vergi Dairesi", "Mevlana Vergi Dairesi", 
        "Konya İhtisas Vergi Dairesi", "İkitelli Vergi Dairesi"
    ]
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("SELECT DISTINCT vergi_dairesi FROM kdv_mukellef WHERE vergi_dairesi IS NOT NULL AND vergi_dairesi != ''")
        rows = c.fetchall()
        db_offices = [row['vergi_dairesi'] for row in rows]
    
    # Merge, unique and sort
    all_offices = sorted(list(set(default_offices + db_offices)))
    return jsonify(all_offices)

@bp.route("/api/kdv/toggle-active", methods=["POST"])
@api_kdv_access_required
def toggle_active():
    data = request.get_json()
    file_id = data.get('id')
    is_active = data.get('is_active')
    user_id = session.get("user_id")
    
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE kdv_files SET is_active = %s WHERE id = %s", (bool(is_active), file_id))
        conn.commit()
    return jsonify({"status": "success"})

# --- KDV MÜKELLEF İŞLEMLERİ ---

@bp.route("/api/kdv/add-mukellef", methods=["POST"])
@api_kdv_access_required
def add_kdv_mukellef():
    # Uzman, Admin ve YMM mükellef ekleyebilir
    if session.get("role") not in ('admin', 'ymm', 'uzman'):
        return jsonify({"status": "error", "message": "Yetkisiz işlem."}), 403
        
    data = request.json
    vkn = data.get('vkn')
    unvan = data.get('unvan')
    
    if not vkn or not unvan:
        return jsonify({"status": "error", "message": "VKN ve Ünvan zorunludur."}), 400
        
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO kdv_mukellef (vkn, unvan, vergi_dairesi, ilgili_memur, sektor, adres, yetkili_ad_soyad, yetkili_tel, yetkili_eposta)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (vkn, unvan, data.get('vergi_dairesi'), data.get('ilgili_memur'), 
                  data.get('sektor'), data.get('adres'), data.get('yetkili_ad_soyad'),
                  data.get('yetkili_tel'), data.get('yetkili_eposta')))
            conn.commit()
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
            
    return jsonify({"status": "success", "message": "KDV Mükellefi başarıyla eklendi."})

@bp.route("/api/kdv/update-mukellef", methods=["POST"])
@api_kdv_access_required
def update_kdv_mukellef():
    if session.get("role") not in ('admin', 'ymm', 'uzman'):
        return jsonify({"status": "error", "message": "Yetkisiz işlem."}), 403
        
    data = request.json
    mid = data.get('id')
    
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE kdv_mukellef 
            SET unvan=%s, vkn=%s, vergi_dairesi=%s, ilgili_memur=%s, 
                sektor=%s, adres=%s, yetkili_ad_soyad=%s, yetkili_tel=%s, yetkili_eposta=%s
            WHERE id=%s
        """, (data.get('unvan'), data.get('vkn'), data.get('vergi_dairesi'), data.get('ilgili_memur'),
              data.get('sektor'), data.get('adres'), data.get('yetkili_ad_soyad'),
              data.get('yetkili_tel'), data.get('yetkili_eposta'), mid))
        conn.commit()
        
    return jsonify({"status": "success", "message": "KDV Mükellefi güncellendi."})

@bp.route("/api/kdv/delete-mukellef", methods=["POST"])
@api_kdv_access_required
def delete_kdv_mukellef():
    if session.get("role") not in ('admin', 'ymm', 'uzman'):
        return jsonify({"status": "error", "message": "Yetkisiz işlem."}), 403
        
    data = request.json
    mid = data.get('id')
    
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM kdv_mukellef WHERE id = %s", (mid,))
        conn.commit()
        
    return jsonify({"status": "success", "message": "KDV Mükellefi silindi."})


# --- KDV DOCUMENT MANAGEMENT ---

@bp.route("/api/kdv/upload-doc", methods=["POST"])
@api_kdv_access_required
def upload_document():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Dosya seçilmedi"}), 400
        
    file = request.files['file']
    file_id = request.form.get('file_id')
    doc_type = request.form.get('doc_type') # e.g. 'İade Dilekçesi'
    
    if not file_id:
        return jsonify({"status": "error", "message": "Dosya ID eksik"}), 400

    # Check allowed extensions
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}):
        return jsonify({"status": "error", "message": "Geçersiz dosya uzantısı"}), 400
        
    import os
    import uuid
    from werkzeug.utils import secure_filename

    # Check file size (3MB limit)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > 3 * 1024 * 1024:
        return jsonify({"status": "error", "message": "Hata: Dosya boyutu 3MB'dan büyük olamaz."}), 400

    try:
        filename = secure_filename(file.filename)
        if not filename:
            filename = f"file_{uuid.uuid4().hex[:8]}"
            
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        # Ensure uploads/kdv_docs directory exists
        # Navigate to static/uploads/kdv_docs
        static_folder = os.path.join(current_app.root_path, 'static')
        upload_folder = os.path.join(static_folder, 'uploads', 'kdv_docs')
        
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Store relative path for frontend access (relative to static)
        # Note: In templates we usually use url_for('static', filename='uploads/kdv_docs/...')
        relative_path = f"uploads/kdv_docs/{unique_filename}"
        
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO kdv_documents (file_id, type, name, date, file_path)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (file_id, doc_type, filename, datetime.now().strftime("%d.%m.%Y %H:%M"), relative_path))
            new_id = c.fetchone()[0]
            conn.commit()
            
        return jsonify({
            "status": "success", 
            "message": "Dosya yüklendi", 
            "doc": {
                "id": new_id,
                "name": filename,
                "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "file_path": relative_path,
                "type": doc_type
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Yükleme hatası: {str(e)}"}), 500

@bp.route("/api/kdv/document/delete/<int:doc_id>", methods=["DELETE"])
@api_kdv_access_required
def delete_document(doc_id):
    with get_conn() as conn:
        c = conn.cursor()
        # Get file path first
        c.execute("SELECT file_path FROM kdv_documents WHERE id = %s", (doc_id,))
        row = c.fetchone()
        
        if row and row[0]:
            import os
            try:
                full_path = os.path.join(current_app.root_path, 'static', row[0])
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as e:
                print(f"Error deleting physical file: {e}")
                
        c.execute("DELETE FROM kdv_documents WHERE id = %s", (doc_id,))
        conn.commit()
            
    return jsonify({"status": "success", "message": "Belge silindi"})
