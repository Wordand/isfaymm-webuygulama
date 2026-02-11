from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from services.db import get_conn
from auth import login_required, kdv_access_required, api_kdv_access_required, role_required
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

def kdv_log_action(user_name, action, details):
    try:
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO kdv_logs (user_name, action, details, timestamp)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """, (user_name, action, details))
            conn.commit()
    except Exception as e:
        print(f"Log Insert Error: {e}")

@bp.route("/kdv-yonetimi")
@kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def index():
    user_id = session.get("user_id")
    role = session.get("role")
    
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Get all users with KDV access for the filter dropdown
        c.execute("""
            SELECT id, username, role 
            FROM users 
            WHERE (has_kdv_access != 0 OR role = 'admin') 
              AND lower(username) NOT IN ('uzman', 'ymm', 'yonetici')
            ORDER BY username ASC
        """)
        users_list = [dict(r) for r in c.fetchall()]
        
    return render_template("kdv/dashboard.html", users_list=users_list)

@bp.route("/kdv-arsiv")
@kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def archive():
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Get all users with KDV access for the filter dropdown
        c.execute("""
            SELECT id, username, role 
            FROM users 
            WHERE (has_kdv_access != 0 OR role = 'admin') 
              AND lower(username) NOT IN ('uzman', 'ymm', 'yonetici')
            ORDER BY username ASC
        """)
        users_list = [dict(r) for r in c.fetchall()]
        
    return render_template("kdv/arsiv.html", users_list=users_list)


@bp.route("/kdv-detay/<int:file_id>")
@kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def details(file_id):
    return render_template(
        "kdv/detay.html",
        file_id=file_id,
        STATUS_STAGES=STATUS_STAGES
    )

@bp.route("/kdv-mukellef-ozet/<int:mukellef_id>")
@kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def mukellef_ozet(mukellef_id):
    user_id = session.get("user_id")
    role = session.get("role")

    # 🔐 UZMAN → SADECE ATANMIŞ MÜKELLEF
    if role == "uzman":
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("""
                SELECT 1 FROM kdv_user_assignments
                WHERE user_id = %s AND mukellef_id = %s
            """, (user_id, mukellef_id))
            if not c.fetchone():
                flash("Bu mükellefi görüntüleme yetkiniz yok.", "danger")
                return redirect(url_for("kdv.mukellefler"))

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("SELECT * FROM kdv_mukellef WHERE id = %s", (mukellef_id,))
        mukellef = c.fetchone()
        if not mukellef:
            flash("Mükellef bulunamadı.", "danger")
            return redirect(url_for("kdv.mukellefler"))

    return render_template("kdv/mukellef_ozet.html", mukellef=dict(mukellef))


@bp.route("/kdv-mukellefler")
@kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def mukellefler():
    user_id = session.get("user_id")
    role = session.get("role")
    
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get all users with KDV access for the filter dropdown
        c.execute("""
            SELECT id, username, role 
            FROM users 
            WHERE (has_kdv_access != 0 OR role = 'admin') 
              AND lower(username) NOT IN ('uzman', 'ymm', 'yonetici')
            ORDER BY username ASC
        """)
        users_list = [dict(r) for r in c.fetchall()]

        if role in ('admin', 'ymm', 'yonetici'):
            # Fetch all clients with their assigned usernames
            c.execute("""
                SELECT m.*, 
                       (SELECT COUNT(*) FROM kdv_files WHERE mukellef_id = m.id AND is_active = TRUE) as active_files,
                       (SELECT COALESCE(SUM(amount_request), 0) FROM kdv_files WHERE mukellef_id = m.id AND is_active = TRUE) as total_request,
                       (SELECT STRING_AGG(u.username, ', ') 
                        FROM users u 
                        JOIN kdv_user_assignments kua ON kua.user_id = u.id 
                        WHERE kua.mukellef_id = m.id) as assigned_names
                FROM kdv_mukellef m 
                ORDER BY m.unvan ASC
            """)
        else:
            # Fetch only assigned clients for this user
            c.execute("""
                SELECT m.*, 
                       (SELECT COUNT(*) FROM kdv_files WHERE mukellef_id = m.id AND is_active = TRUE) as active_files,
                       (SELECT COALESCE(SUM(amount_request), 0) FROM kdv_files WHERE mukellef_id = m.id AND is_active = TRUE) as total_request,
                       (SELECT STRING_AGG(u.username, ', ') 
                        FROM users u 
                        JOIN kdv_user_assignments kua ON kua.user_id = u.id 
                        WHERE kua.mukellef_id = m.id) as assigned_names
                FROM kdv_mukellef m 
                JOIN kdv_user_assignments kua_filter ON kua_filter.mukellef_id = m.id
                WHERE kua_filter.user_id = %s
                ORDER BY m.unvan ASC
            """, (user_id,))
            
        mukellefler = [dict(r) for r in c.fetchall()]
        
    return render_template("kdv/mukellefler.html", mukellefler=mukellefler, users_list=users_list)

@bp.route("/kdv-ayarlar")
@kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici"))
def settings():
    return render_template("kdv/settings.html")

@bp.route("/kdv-portal/verify", methods=["GET", "POST"])
@login_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def verify_pin():
    if request.method == "POST":
        input_pin = request.form.get("pin")
        user_id = session.get("user_id")
        
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("SELECT kdv_pin FROM users WHERE id = %s", (user_id,))
            user = c.fetchone()
            
            db_pin = user.get("kdv_pin", "1234") if user else "1234"
            if not db_pin:
                db_pin = "1234"
            
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
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def get_stats():
    user_id = session.get("user_id")
    role = session.get("role")
    mukellef_id = request.args.get("mukellef_id") or request.args.get("mukellef")
    filter_user_id = request.args.get("user_id")

    def parse_money(val):
        if not val:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        clean = (
            str(val)
            .replace(".", "")
            .replace(",", ".")
            .replace("₺", "")
            .replace("TL", "")
            .strip()
        )
        try:
            return float(clean)
        except:
            return 0.0

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 🔒 GÜVENLİ BASE FILTER
        base_filter = " WHERE is_active = TRUE"
        params = []

        if role == "uzman":
            base_filter += """
                AND mukellef_id IN (
                    SELECT mukellef_id
                    FROM kdv_user_assignments
                    WHERE user_id = %s
                )
            """
            params.append(user_id)

        elif role not in ("admin", "ymm", "yonetici"):
            base_filter += " AND user_id = %s"
            params.append(user_id)

        if mukellef_id:
            base_filter += " AND mukellef_id = %s"
            params.append(mukellef_id)

        if filter_user_id:
            base_filter += " AND user_id = %s"
            params.append(filter_user_id)

        # 🔹 ANA DATA
        c.execute(
            f"""
            SELECT status, amount_request, type, subject, date
            FROM kdv_files
            {base_filter}
            """,
            tuple(params),
        )
        all_files = c.fetchall()

        pending_amount = 0.0
        completed_amount = 0.0
        missing_docs_count = 0
        guarantee_amount = 0.0
        status_dist_map = {}

        for f in all_files:
            amt = parse_money(f["amount_request"])
            status = f["status"] or "Bilinmiyor"

            if status not in ("İade Tamamlandı", "İade Alındı"):
                pending_amount += amt
            else:
                completed_amount += amt

            if status == "Eksiklik yazısı geldi":
                missing_docs_count += 1

            subj = (f.get("subject") or "").lower()
            typ = (f.get("type") or "").lower()
            if "teminat" in subj or "teminat" in typ:
                guarantee_amount += amt

            status_dist_map[status] = status_dist_map.get(status, 0) + 1

        status_dist = [
            {"status": k, "count": v} for k, v in status_dist_map.items()
        ]

        # 🔹 TREND
        c.execute(
            f"""
            SELECT date, amount_request
            FROM kdv_files
            {base_filter}
            """,
            tuple(params),
        )
        trend_rows = c.fetchall()

        from collections import defaultdict

        monthly_totals = defaultdict(float)

        for f in trend_rows:
            try:
                d = f["date"]
                if not d:
                    continue

                if "." in d:
                    parts = d.split(".")
                    if len(parts) == 3 and len(parts[2]) == 4:
                        key = f"{parts[2]}-{parts[1]}"
                        monthly_totals[key] += parse_money(
                            f["amount_request"]
                        )
                elif "-" in d:
                    parts = d.split("-")
                    if len(parts) == 3 and len(parts[0]) == 4:
                        key = f"{parts[0]}-{parts[1]}"
                        monthly_totals[key] += parse_money(
                            f["amount_request"]
                        )
            except:
                continue

        sorted_months = sorted(monthly_totals.keys(), reverse=True)[:6]

        tr_months = {
            "01": "Oca",
            "02": "Şub",
            "03": "Mar",
            "04": "Nis",
            "05": "May",
            "06": "Haz",
            "07": "Tem",
            "08": "Ağu",
            "09": "Eyl",
            "10": "Eki",
            "11": "Kas",
            "12": "Ara",
        }

        trend_labels = []
        trend_data = []

        for m in reversed(sorted_months):
            year, month = m.split("-")
            trend_labels.append(tr_months.get(month, month))
            trend_data.append(monthly_totals[m])

        stats = {
            "pending_amount": float(pending_amount),
            "completed_amount": float(completed_amount),
            "missing_docs_count": int(missing_docs_count),
            "guarantee_amount": float(guarantee_amount),
            "status_dist": status_dist,
            "trend_labels": trend_labels,
            "trend_data": trend_data,
        }

        # 🕒 Son 5 Aktivite
        try:
            c.execute("""
                SELECT date, user_name, action, description
                FROM kdv_system_logs
                ORDER BY id DESC
                LIMIT 5
            """)
            stats["recent_activities"] = [dict(r) for r in c.fetchall()]
        except:
            stats["recent_activities"] = []

    return jsonify(stats)


@bp.route("/api/kdv/files")
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def list_files():
    user_id = session.get("user_id")
    role = session.get("role")

    is_active = request.args.get("active", 1, type=int)
    mukellef_filter = request.args.get("mukellef_id") or request.args.get("mukellef")
    status_filter = request.args.get("status")
    filter_type = request.args.get("filter_type")  # guarantee
    filter_user_id = request.args.get("user_id")

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 🔒 GÜVENLİ BASE QUERY
        query = """
            SELECT f.*, m.unvan AS client_name
            FROM kdv_files f
            JOIN kdv_mukellef m ON f.mukellef_id = m.id
            WHERE f.is_active = %s
        """
        params = [True if is_active == 1 else False]

        # 🔐 ROL BAZLI ERİŞİM
        if role == "uzman":
            query += """
                AND f.mukellef_id IN (
                    SELECT mukellef_id
                    FROM kdv_user_assignments
                    WHERE user_id = %s
                )
            """
            params.append(user_id)

        elif role not in ("admin", "ymm", "yonetici"):
            query += " AND f.user_id = %s"
            params.append(user_id)

        # 🔹 MÜKELLEF FİLTRESİ (artık güvenli)
        if mukellef_filter:
            query += " AND f.mukellef_id = %s"
            params.append(mukellef_filter)
            
        if filter_user_id:
            query += " AND f.user_id = %s"
            params.append(filter_user_id)

        # 🔹 STATÜ FİLTRESİ
        if status_filter:
            query += " AND f.status = %s"
            params.append(status_filter)

        # 🔹 ÖZEL FİLTRELER
        if filter_type == "guarantee":
            query += " AND (f.subject ILIKE %s OR f.type ILIKE %s)"
            params.extend(["%Teminat%", "%Teminat%"])

        query += " ORDER BY f.id DESC"

        c.execute(query, tuple(params))
        files = [dict(r) for r in c.fetchall()]

    return jsonify(files)


@bp.route("/api/kdv/users")
@api_kdv_access_required
@role_required(allow_roles=("admin",))
def get_kdv_users():
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT 
                u.id,
                u.username,
                u.role,
                u.has_kdv_access,
                (
                    SELECT COUNT(*)
                    FROM kdv_user_assignments
                    WHERE user_id = u.id
                ) AS assigned_count
            FROM users u
            WHERE u.has_kdv_access != 0 OR u.role = 'admin'
            ORDER BY u.id ASC
        """)
        users = [dict(r) for r in c.fetchall()]
    return jsonify(users)



@bp.route("/api/kdv/all-mukellefs")
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def get_all_kdv_mukellefs():
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT id, unvan, vkn
            FROM kdv_mukellef
            ORDER BY unvan ASC
        """)
        mukellefs = [dict(r) for r in c.fetchall()]
    return jsonify(mukellefs)



@bp.route("/api/kdv/update-pin", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin",))
def update_kdv_pin():
    new_pin = request.json.get("pin")

    if not new_pin or len(new_pin) < 4:
        return jsonify({
            "status": "error",
            "message": "Geçersiz PIN formatı."
        }), 400

    user_id = session.get("user_id")

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE users SET kdv_pin = %s WHERE id = %s",
            (new_pin, user_id)
        )
        conn.commit()

    return jsonify({
        "status": "success",
        "message": "Portal PIN başarıyla güncellendi."
    })


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
@role_required(allow_roles=("admin",))
def get_user_assignments(user_id):
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT m.id, m.unvan, m.vkn
            FROM kdv_user_assignments a
            JOIN kdv_mukellef m ON a.mukellef_id = m.id
            WHERE a.user_id = %s
        """, (user_id,))
        assignments = [dict(r) for r in c.fetchall()]

    return jsonify(assignments)


@bp.route("/api/kdv/assign-mukellef", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin",))
def assign_mukellef():
    data = request.json
    user_id = data.get("user_id")
    mukellef_id = data.get("mukellef_id")

    if not user_id or not mukellef_id:
        return jsonify({
            "status": "error",
            "message": "Eksik parametre."
        }), 400

    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO kdv_user_assignments (user_id, mukellef_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, mukellef_id) DO NOTHING
            """, (user_id, mukellef_id))

            # Log için isimleri al
            c.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            res_user = c.fetchone()
            target_user = res_user["username"] if res_user else "Bilinmeyen"

            c.execute("SELECT unvan FROM kdv_mukellef WHERE id = %s", (mukellef_id,))
            res_mukellef = c.fetchone()
            target_mukellef = res_mukellef["unvan"] if res_mukellef else "Bilinmeyen"

            conn.commit()

            kdv_log_action(
                session.get("username", "Admin"),
                "Yetki Atama",
                f"\"{target_user}\" kullanıcısına \"{target_mukellef}\" mükellefi atandı."
            )

        except Exception as e:
            conn.rollback()
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

    return jsonify({
        "status": "success",
        "message": "Atama başarıyla yapıldı."
    })


@bp.route("/api/kdv/remove-assignment", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin",))
def remove_assignment():
    data = request.json
    user_id = data.get("user_id")
    mukellef_id = data.get("mukellef_id")

    if not user_id or not mukellef_id:
        return jsonify({
            "status": "error",
            "message": "Eksik parametre."
        }), 400

    with get_conn() as conn:
        c = conn.cursor()

        # Log için isimleri al
        c.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        row_user = c.fetchone()
        target_user = row_user["username"] if row_user and "username" in row_user else "Bilinmeyen"

        c.execute("SELECT unvan FROM kdv_mukellef WHERE id = %s", (mukellef_id,))
        row_muk = c.fetchone()
        target_mukellef = row_muk["unvan"] if row_muk and "unvan" in row_muk else "Bilinmeyen"

        c.execute("""
            DELETE FROM kdv_user_assignments
            WHERE user_id = %s AND mukellef_id = %s
        """, (user_id, mukellef_id))

        conn.commit()

        kdv_log_action(
            session.get("username", "Admin"),
            "Yetki Kaldırma",
            f"\"{target_user}\" kullanıcısının \"{target_mukellef}\" mükellefi kaldırıldı."
        )

    return jsonify({
        "status": "success",
        "message": "Atama kaldırıldı."
    })


@bp.route("/api/kdv/delete-user/<int:user_id>", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin",))
def delete_kdv_user(user_id):
    with get_conn() as conn:
        c = conn.cursor()

        # Log için kullanıcı adını al
        c.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        row = c.fetchone()
        target_user = row["username"] if row and "username" in row else "Bilinmeyen"

        # KDV yetkisini kaldır (kullanıcı silinmez)
        c.execute("""
            UPDATE users
            SET has_kdv_access = 0
            WHERE id = %s
        """, (user_id,))

        # Tüm mükellef atamalarını temizle
        c.execute("""
            DELETE FROM kdv_user_assignments
            WHERE user_id = %s
        """, (user_id,))

        conn.commit()

        # Sistem logu
        kdv_log_action(
            session.get("username", "Admin"),
            "KDV Yetkisi Kaldırma",
            f"\"{target_user}\" kullanıcısının KDV yetkisi kaldırıldı."
        )

    return jsonify({
        "status": "success",
        "message": "Kullanıcının KDV yetkisi kaldırıldı."
    })


@bp.route("/api/kdv/logs")
@api_kdv_access_required
@role_required(allow_roles=("admin",))
def get_kdv_logs():
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Tablo var mı kontrolü
        c.execute("SELECT to_regclass('public.kdv_system_logs')")
        res = c.fetchone()
        if not res or not list(res.values())[0]:
            return jsonify([])

        c.execute("""
            SELECT *
            FROM kdv_system_logs
            ORDER BY id DESC
            LIMIT 50
        """)
        logs = [dict(r) for r in c.fetchall()]

    return jsonify(logs)


@bp.route("/api/kdv/logs/delete", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin",))
def delete_all_logs():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM kdv_system_logs")
        conn.commit()

    return jsonify({"status": "success"})

    


@bp.route("/api/kdv/file/<int:file_id>")
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def get_file(file_id):
    user_id = session.get("user_id")
    role = session.get("role")

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if role in ("admin", "ymm", "yonetici"):
            # 🔓 Tam erişim
            c.execute("""
                SELECT f.*, m.unvan AS client_name
                FROM kdv_files f
                JOIN kdv_mukellef m ON f.mukellef_id = m.id
                WHERE f.id = %s
            """, (file_id,))
        else:
            # 🔐 Uzman → sadece atanmış mükellefin dosyası
            c.execute("""
                SELECT f.*, m.unvan AS client_name
                FROM kdv_files f
                JOIN kdv_mukellef m ON f.mukellef_id = m.id
                WHERE f.id = %s
                  AND f.mukellef_id IN (
                      SELECT mukellef_id
                      FROM kdv_user_assignments
                      WHERE user_id = %s
                  )
            """, (file_id, user_id))

        file_row = c.fetchone()

        if not file_row:
            return jsonify({
                "status": "error",
                "message": "Dosya bulunamadı veya yetkiniz yok."
            }), 404

        file = dict(file_row)

        # 📜 Geçmiş
        c.execute("""
            SELECT *
            FROM kdv_history
            WHERE file_id = %s
            ORDER BY id DESC
        """, (file_id,))
        file["history"] = [dict(r) for r in c.fetchall()]

        # 📎 Belgeler
        c.execute("""
            SELECT *
            FROM kdv_documents
            WHERE file_id = %s
            ORDER BY id DESC
        """, (file_id,))
        file["documents"] = [dict(r) for r in c.fetchall()]

        # 📝 Notlar (Hızlı Bilgi)
        c.execute("""
            SELECT *
            FROM kdv_notes
            WHERE file_id = %s
            ORDER BY created_at DESC
        """, (file_id,))
        file["notes"] = [dict(r) for r in c.fetchall()]

    return jsonify(file)


@bp.route("/api/kdv/add-file", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def add_file():
    data = request.get_json()
    user_id = session.get("user_id")
    role = session.get("role")

    mukellef_id = data.get("mukellef_id")

    if not mukellef_id:
        return jsonify({
            "status": "error",
            "message": "Mükellef seçilmelidir."
        }), 400

    # 🔐 Uzman → atanmış mükellef kontrolü
    if role == "uzman":
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT 1
                FROM kdv_user_assignments
                WHERE user_id = %s AND mukellef_id = %s
            """, (user_id, mukellef_id))
            if not c.fetchone():
                return jsonify({
                    "status": "error",
                    "message": "Bu mükellef için dosya oluşturma yetkiniz yok."
                }), 403

    
    # Batch Support: 'periods' keys can be a list of period strings
    # Fallback to single 'period' if not present
    periods = data.get("periods", [])
    if not periods and data.get("period"):
        periods = [data.get("period")]
    
    if not periods:
        return jsonify({"status": "error", "message": "En az bir dönem seçilmelidir."}), 400

    no_refund = data.get("no_refund", False)
    
    # Common Values
    base_subject = data.get("subject")
    base_type = data.get("type")
    base_amount = data.get("amount_request")

    if no_refund:
        base_subject = "İADESİ YOK"
        base_type = "-"
        base_amount = 0
        initial_status = "İade Yok"
    else:
        initial_status = "Listeler hazırlanacak"

    # Transaction Start
    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            inserted_count = 0
            
            for p in periods:
                # Check duplication first
                c.execute("""
                    SELECT id FROM kdv_files 
                    WHERE mukellef_id = %s AND period = %s AND is_active = TRUE
                """, (mukellef_id, p))
                if c.fetchone():
                    continue # Skip existing

                query = """
                    INSERT INTO kdv_files (
                        mukellef_id,
                        user_id,
                        period,
                        subject,
                        type,
                        amount_request,
                        status,
                        date,
                        is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                """
                
                params = (
                    mukellef_id,
                    user_id,
                    p,
                    base_subject,
                    base_type,
                    base_amount,
                    initial_status,
                    datetime.now().strftime("%d.%m.%Y")
                )

                file_id = None
                # PostgreSQL
                query += " RETURNING id"
                c.execute(query, params)
                row = c.fetchone()
                if row: file_id = row["id"]
                
                if file_id:
                    inserted_count += 1
                    # 📜 History
                    c.execute("""
                        INSERT INTO kdv_history (file_id, date, text)
                        VALUES (%s, %s, %s)
                    """, (
                        file_id,
                        datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "Dosya oluşturuldu - " + initial_status
                    ))

            # Log
            c.execute("SELECT unvan FROM kdv_mukellef WHERE id = %s", (mukellef_id,))
            m_row = c.fetchone()
            m_name = m_row["unvan"] if m_row else "Bilinmeyen"
            
            conn.commit()

            if inserted_count == 0 and len(periods) > 0:
                 return jsonify({"status": "error", "message": "Seçilen dönemler için zaten dosya mevcut."}), 400
            
            kdv_log_action(
                session.get("username", "Admin"),
                "Dosya Oluşturma",
                f"{session.get('username')} \"{m_name}\" mükellefi için {inserted_count} adet yeni iade dosyası ekledi."
            )

        return jsonify({
            "status": "success", 
            "message": f"{inserted_count} adet dosya oluşturuldu."
        })

    except Exception as e:
        print(f"Error in add_file: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/api/kdv/update-status", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def update_status():
    data = request.get_json()
    user_id = session.get("user_id")
    role = session.get("role")

    file_id = data.get("file_id")
    new_status = data.get("status")
    new_location = data.get("location")
    description = data.get("description", "")

    if not file_id:
        return jsonify({
            "status": "error",
            "message": "Dosya ID zorunludur."
        }), 400

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    with get_conn() as conn:
        c = conn.cursor()
        # 🔍 Dosya ve Mükellef Bilgisi
        c.execute("""
            SELECT f.*, m.unvan 
            FROM kdv_files f
            JOIN kdv_mukellef m ON f.mukellef_id = m.id
            WHERE f.id = %s
        """, (file_id,))
        file_row = c.fetchone()
        if not file_row:
            return jsonify({
                "status": "error",
                "message": "Dosya bulunamadı."
            }), 404

        # 🔐 UZMAN → SADECE ATANMIŞ MÜKELLEF
        if role == "uzman":
            c.execute("""
                SELECT 1
                FROM kdv_user_assignments
                WHERE user_id = %s AND mukellef_id = %s
            """, (user_id, file_row["mukellef_id"]))
            if not c.fetchone():
                return jsonify({"status": "error", "message": "Bu dosya üzerinde işlem yapma yetkiniz yok."}), 403

        # 🔄 Statü güncelleme
        if new_status:
            c.execute("""
                UPDATE kdv_files
                SET status = %s
                WHERE id = %s
            """, (new_status, file_id))

            c.execute("""
                INSERT INTO kdv_history (file_id, date, text, description)
                VALUES (%s, %s, %s, %s)
            """, (file_id, now_str, new_status, description))
            
            kdv_log_action(
                session.get("username", "Admin"),
                "Durum Değişikliği",
                f"{session.get('username')} \"{file_row['unvan']}\" mükellefinin {file_row['period']} dönemi süreç akışını \"{new_status}\" olarak değiştirdi."
            )

        # 📍 Lokasyon güncelleme
        if new_location:
            c.execute("""
                UPDATE kdv_files
                SET location = %s
                WHERE id = %s
            """, (new_location, file_id))

            c.execute("""
                INSERT INTO kdv_history (file_id, date, text, description)
                VALUES (%s, %s, %s, %s)
            """, (file_id, now_str, new_location, description))
            
            kdv_log_action(
                session.get("username", "Admin"),
                "Yer Değişikliği",
                f"{session.get('username')} \"{file_row['unvan']}\" mükellefinin {file_row['period']} dönemi dosya lokasyonunu \"{new_location}\" olarak değiştirdi."
            )

        conn.commit()

    return jsonify({
        "status": "success",
        "message": "Dosya durumu güncellendi."
    })


@bp.route("/api/kdv/update-file-amounts", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def update_file_amounts():
    data = request.get_json()
    file_id = data.get("file_id")
    user_id = session.get("user_id")
    role = session.get("role")

    if not file_id:
        return jsonify({"status": "error", "message": "Dosya ID zorunludur."}), 400

    # Helper: Parse money
    def pm(val):
        if val is None or val == "":
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        clean = str(val).replace(".", "").replace(",", ".").replace("₺", "").replace("TL", "").strip()
        try:
            return float(clean)
        except:
            return 0.0
            
    amt_request = pm(data.get("amount_request"))
    amt_guarantee = pm(data.get("amount_guarantee"))
    amt_tenzil = pm(data.get("amount_tenzil"))
    amt_bloke = pm(data.get("amount_bloke"))
    amt_resolved = pm(data.get("amount_resolved"))

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 🔍 Dosya ve Yetki Kontrolü
        c.execute("""
            SELECT f.mukellef_id, f.period, m.unvan 
            FROM kdv_files f
            JOIN kdv_mukellef m ON f.mukellef_id = m.id
            WHERE f.id = %s
        """, (file_id,))
        row = c.fetchone()
        
        if not row:
            return jsonify({"status": "error", "message": "Dosya bulunamadı."}), 404

        # 🔐 UZMAN KONTROLÜ
        if role == "uzman":
            c.execute("SELECT 1 FROM kdv_user_assignments WHERE user_id = %s AND mukellef_id = %s", (user_id, row["mukellef_id"]))
            if not c.fetchone():
                return jsonify({"status": "error", "message": "Yetkisiz işlem."}), 403

        # 💾 GÜNCELLEME
        c.execute("""
            UPDATE kdv_files
            SET amount_request = %s,
                amount_guarantee = %s,
                amount_tenzil = %s,
                amount_bloke = %s,
                amount_resolved = %s
            WHERE id = %s
        """, (amt_request, amt_guarantee, amt_tenzil, amt_bloke, amt_resolved, file_id))

        # 📜 Log
        log_msg = f"{session.get('username')} \"{row['unvan']}\" {row['period']} dosyası tutarlarını güncelledi. (Talep: {amt_request}, Sonuç: {amt_resolved})"
        kdv_log_action(session.get("username", "System"), "Tutar Güncelleme", log_msg)

        conn.commit()

    return jsonify({"status": "success", "message": "Tutarlar başarıyla güncellendi."})


@bp.route("/api/kdv/delete", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm"))
def delete_file():
    data = request.get_json()
    file_id = data.get("id")

    if not file_id:
        return jsonify({
            "status": "error",
            "message": "Dosya ID zorunludur."
        }), 400

    with get_conn() as conn:
        c = conn.cursor()

        # Dosya ve Mükellef Bilgisini Log için Al
        c.execute("""
            SELECT f.period, m.unvan 
            FROM kdv_files f
            JOIN kdv_mukellef m ON f.mukellef_id = m.id
            WHERE f.id = %s
        """, (file_id,))
        f_row = c.fetchone()
        f_info = f"\"{f_row['unvan']}\" mükellefinin {f_row['period']} dönemi" if f_row else f"ID {file_id}"

        c.execute("DELETE FROM kdv_files WHERE id = %s", (file_id,))
        conn.commit()

        kdv_log_action(
            session.get("username", "Admin"),
            "Dosya Silme",
            f"{session.get('username')} {f_info} iade dosyasını sildi."
        )

    return jsonify({"status": "success"})


@bp.route("/api/kdv/tax-offices")
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def get_tax_offices():
    default_offices = [
        "Selçuk Vergi Dairesi",
        "Meram Vergi Dairesi",
        "Mevlana Vergi Dairesi",
        "Konya İhtisas Vergi Dairesi",
        "İkitelli Vergi Dairesi"
    ]

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("""
            SELECT DISTINCT vergi_dairesi
            FROM kdv_mukellef
            WHERE vergi_dairesi IS NOT NULL
              AND vergi_dairesi != ''
        """)
        db_offices = [row["vergi_dairesi"] for row in c.fetchall()]

    all_offices = sorted(set(default_offices + db_offices))
    return jsonify(all_offices)


@bp.route("/api/kdv/toggle-active", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm"))
def toggle_active():
    data = request.get_json()
    file_id = data.get("id")
    is_active = data.get("is_active")

    if file_id is None or is_active is None:
        return jsonify({
            "status": "error",
            "message": "Eksik parametre."
        }), 400

    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
            UPDATE kdv_files
            SET is_active = %s
            WHERE id = %s
        """, (bool(is_active), file_id))

        conn.commit()

        kdv_log_action(
            session.get("username", "Admin"),
            "Dosya Durumu",
            f"ID {file_id} dosyası {'aktif' if is_active else 'pasif'} yapıldı."
        )

    return jsonify({"status": "success"})


# --- KDV MÜKELLEF ÖZET ---

@bp.route("/api/kdv/mukellef-summary/<int:mukellef_id>")
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def mukellef_summary(mukellef_id):
    user_id = session.get("user_id")
    role = session.get("role")

    # 🔐 UZMAN → SADECE ATANMIŞ MÜKELLEF
    if role == "uzman":
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("""
                SELECT 1 FROM kdv_user_assignments
                WHERE user_id = %s AND mukellef_id = %s
            """, (user_id, mukellef_id))
            if not c.fetchone():
                return jsonify({"status": "error", "message": "Yetkisiz erişim"}), 403

    def parse_money(val):
        if not val:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        clean = str(val).replace(".", "").replace(",", ".").replace("₺", "").replace("TL", "").strip()
        try:
            return float(clean)
        except:
            return 0.0

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Mükellef bilgisi
        c.execute("SELECT id, unvan, vkn, vergi_dairesi FROM kdv_mukellef WHERE id = %s", (mukellef_id,))
        mukellef = c.fetchone()
        if not mukellef:
            return jsonify({"status": "error", "message": "Mükellef bulunamadı"}), 404

        # İade dosyaları
        c.execute("""
            SELECT f.id, f.period, f.subject, f.type, 
                   f.amount_request, f.amount_tenzil, f.amount_bloke, f.amount_resolved,
                   f.amount_guarantee,
                   f.status, f.is_active, f.is_guaranteed, f.guarantee_date, f.date
            FROM kdv_files f
            WHERE f.mukellef_id = %s AND f.is_active = TRUE
            ORDER BY f.period DESC, f.id DESC
        """, (mukellef_id,))
        files = c.fetchall()

        # Banka teminatları (Yedek kaynak)
        c.execute("""
            SELECT bg.file_id, COALESCE(SUM(bg.amount), 0) as total_guarantee
            FROM kdv_bank_guarantees bg
            WHERE bg.mukellef_id = %s AND bg.status = 'Aktif'
            GROUP BY bg.file_id
        """, (mukellef_id,))
        guarantee_map = {}
        for row in c.fetchall():
            guarantee_map[row["file_id"]] = parse_money(row["total_guarantee"])

    # Dosyaları düzenle
    result_files = []
    totals = {
        "amount_request": 0,
        "amount_guarantee": 0,
        "amount_post_guarantee": 0,
        "amount_tenzil": 0,
        "amount_bloke": 0,
        "amount_resolved": 0
    }

    for f in files:
        amt_request = parse_money(f["amount_request"])
        amt_tenzil = parse_money(f.get("amount_tenzil"))
        amt_bloke = parse_money(f.get("amount_bloke"))
        amt_resolved = parse_money(f.get("amount_resolved"))
        
        # Teminat: Manuel girildiyse onu kullan, yoksa banka kayıtlarını kullan
        amt_guarantee_manual = parse_money(f.get("amount_guarantee"))
        amt_guarantee_bank = guarantee_map.get(f["id"], 0)
        
        amt_guarantee = amt_guarantee_manual if amt_guarantee_manual > 0 else amt_guarantee_bank
        amt_post_guarantee = max(0, amt_request - amt_guarantee)

        file_data = {
            "id": f["id"],
            "period": f["period"] or "",
            "subject": f["subject"] or "",
            "type": f["type"] or "",
            "amount_request": amt_request,
            "amount_guarantee": amt_guarantee,
            "amount_post_guarantee": amt_post_guarantee,
            "amount_tenzil": amt_tenzil,
            "amount_bloke": amt_bloke,
            "amount_resolved": amt_resolved,
            "status": f["status"] or "",
            "date": f.get("date") or ""
        }
        result_files.append(file_data)

        totals["amount_request"] += amt_request
        totals["amount_guarantee"] += amt_guarantee
        totals["amount_post_guarantee"] += amt_post_guarantee
        totals["amount_tenzil"] += amt_tenzil
        totals["amount_bloke"] += amt_bloke
        totals["amount_resolved"] += amt_resolved

    return jsonify({
        "status": "success",
        "mukellef": dict(mukellef),
        "files": result_files,
        "totals": totals,
        "file_count": len(result_files)
    })


# --- KDV MÜKELLEF İŞLEMLERİ ---

@bp.route("/api/kdv/add-mukellef", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def add_kdv_mukellef():
    data = request.json
    user_id = session.get("user_id")
    role = session.get("role")

    if not data.get("vkn") or not data.get("unvan"):
        return jsonify({"status": "error", "message": "VKN ve Ünvan zorunludur."}), 400

    with get_conn() as conn:
        c = conn.cursor()
        
        from services.db import USE_SQLITE
        
        insert_query = """
            INSERT INTO kdv_mukellef (
                vkn, unvan, vergi_dairesi, ilgili_memur,
                sektor, adres, yetkili_ad_soyad,
                yetkili_tel, yetkili_eposta
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        params = (
            data["vkn"], data["unvan"],
            data.get("vergi_dairesi"),
            data.get("ilgili_memur"),
            data.get("sektor"),
            data.get("adres"),
            data.get("yetkili_ad_soyad"),
            data.get("yetkili_tel"),
            data.get("yetkili_eposta"),
        )

        if not USE_SQLITE:
            insert_query += " RETURNING id"
            c.execute(insert_query, params)
            mukellef_id = c.fetchone()["id"]
        else:
            c.execute(insert_query, params)
            mukellef_id = c.lastrowid

        # 🔑 Eğer ekleyen Uzman ise, mükellefi kendisine otomatik ata
        if role == "uzman":
            c.execute("""
                INSERT INTO kdv_user_assignments (user_id, mukellef_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, mukellef_id) DO NOTHING
            """, (user_id, mukellef_id))

        conn.commit()
        
        kdv_log_action(
            session.get("username", "Admin"),
            "Mükellef Ekleme",
            f"{session.get('username')} \"{data['unvan']}\" mükellefini sisteme ekledi."
        )

    return jsonify({"status": "success"})


@bp.route("/api/kdv/update-mukellef", methods=["POST"])
@api_kdv_access_required
def update_kdv_mukellef():
    role = session.get("role")
    user_id = session.get("user_id")
    data = request.json
    mid = data.get("id")

    if not mid:
        return jsonify({"status": "error", "message": "ID eksik"}), 400

    with get_conn() as conn:
        c = conn.cursor()

        # 🔒 UZMAN → SADECE ATANMIŞ MÜKELLEF
        if role == "uzman":
            c.execute("""
                SELECT 1
                FROM kdv_user_assignments
                WHERE user_id = %s AND mukellef_id = %s
            """, (user_id, mid))
            if not c.fetchone():
                return jsonify({"status": "error", "message": "Yetkisiz erişim"}), 403

        elif role not in ("admin", "ymm", "yonetici"):
            return jsonify({"status": "error", "message": "Yetkisiz"}), 403

        c.execute("""
            UPDATE kdv_mukellef
            SET unvan=%s, vkn=%s, vergi_dairesi=%s,
                ilgili_memur=%s, sektor=%s, adres=%s,
                yetkili_ad_soyad=%s, yetkili_tel=%s, yetkili_eposta=%s
            WHERE id=%s
        """, (
            data.get("unvan"),
            data.get("vkn"),
            data.get("vergi_dairesi"),
            data.get("ilgili_memur"),
            data.get("sektor"),
            data.get("adres"),
            data.get("yetkili_ad_soyad"),
            data.get("yetkili_tel"),
            data.get("yetkili_eposta"),
            mid
        ))
        conn.commit()
        
        kdv_log_action(
            session.get("username", "Admin"),
            "Mükellef Güncelleme",
            f"{session.get('username')} \"{data.get('unvan')}\" mükellefini güncelledi."
        )

    return jsonify({"status": "success"})

@bp.route("/api/kdv/delete-mukellef", methods=["POST"])
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def delete_kdv_mukellef():
    role = session.get("role")
    user_id = session.get("user_id")
    mid = request.json.get("id")

    if not mid:
        return jsonify({"status": "error", "message": "ID eksik"}), 400

    with get_conn() as conn:
        c = conn.cursor()

        # 🔒 UZMAN → SADECE ATANMIŞ MÜKELLEF
        if role == "uzman":
            c.execute("""
                SELECT 1
                FROM kdv_user_assignments
                WHERE user_id = %s AND mukellef_id = %s
            """, (user_id, mid))
            if not c.fetchone():
                return jsonify({"status": "error", "message": "Bu mükellefi silme yetkiniz yok."}), 403

        # Log için ismi al
        c.execute("SELECT unvan FROM kdv_mukellef WHERE id = %s", (mid,))
        m_row = c.fetchone()
        m_name = m_row["unvan"] if m_row else "Bilinmeyen"

        c.execute("DELETE FROM kdv_mukellef WHERE id = %s", (mid,))
        conn.commit()
        
        kdv_log_action(
            session.get("username", "Admin"),
            "Mükellef Silme",
            f"{session.get('username')} \"{m_name}\" mükellefini sildi."
        )

    return jsonify({"status": "success"})



# --- KDV DOCUMENT MANAGEMENT ---

@bp.route("/api/kdv/upload-doc", methods=["POST"])
@api_kdv_access_required
def upload_document():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Dosya seçilmedi"}), 400
        
    file = request.files['file']
    file_id = request.form.get('file_id')
    doc_type = request.form.get('doc_type')
    user_id = session.get("user_id")
    role = session.get("role")
    
    if not file_id:
        return jsonify({"status": "error", "message": "Dosya ID eksik"}), 400

    # 🔒 YETKİ KONTROLÜ
    with get_conn() as conn:
        c = conn.cursor()

        if role == "uzman":
            # Uzman → sadece kendine atanmış mükellefin dosyasına belge ekleyebilir
            c.execute("""
                SELECT 1
                FROM kdv_files f
                JOIN kdv_user_assignments a ON a.mukellef_id = f.mukellef_id
                WHERE f.id = %s AND a.user_id = %s
            """, (file_id, user_id))
            if not c.fetchone():
                return jsonify({
                    "status": "error",
                    "message": "Bu dosyaya belge yükleme yetkiniz yok."
                }), 403

        elif role not in ('admin', 'ymm', 'yonetici'):
            return jsonify({
                "status": "error",
                "message": "Yetkisiz işlem."
            }), 403

    # 📎 DOSYA UZANTI KONTROLÜ
    if not (
        '.' in file.filename and
        file.filename.rsplit('.', 1)[1].lower()
        in {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}
    ):
        return jsonify({"status": "error", "message": "Geçersiz dosya uzantısı"}), 400
        
    import os
    import uuid
    from werkzeug.utils import secure_filename

    # 📏 DOSYA BOYUTU (3MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > 3 * 1024 * 1024:
        return jsonify({
            "status": "error",
            "message": "Hata: Dosya boyutu 3MB'dan büyük olamaz."
        }), 400

    try:
        filename = secure_filename(file.filename)
        if not filename:
            filename = f"file_{uuid.uuid4().hex[:8]}"
            
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        static_folder = os.path.join(current_app.root_path, 'static')
        upload_folder = os.path.join(static_folder, 'uploads', 'kdv_docs')
        
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        relative_path = f"uploads/kdv_docs/{unique_filename}"
        
        with get_conn() as conn:
            c = conn.cursor()
            from services.db import USE_SQLITE
            
            query = """
                INSERT INTO kdv_documents (file_id, type, name, date, file_path)
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (
                file_id,
                doc_type,
                filename,
                datetime.now().strftime("%d.%m.%Y %H:%M"),
                relative_path
            )

            if not USE_SQLITE:
                query += " RETURNING id"
                c.execute(query, params)
                new_id = c.fetchone()["id"]
            else:
                c.execute(query, params)
                new_id = c.lastrowid
                
            # Log için dosya/mükellef bilgisi al
            c.execute("""
                SELECT f.period, m.unvan 
                FROM kdv_files f
                JOIN kdv_mukellef m ON f.mukellef_id = m.id
                WHERE f.id = %s
            """, (file_id,))
            f_row = c.fetchone()
            f_info = f"{f_row['unvan']} {f_row['period']} dönemi" if f_row else "Bilinmeyen dosya"

            conn.commit()
            
            kdv_log_action(
                session.get("username", "Admin"),
                "Belge Yükleme",
                f"{session.get('username')} {f_info} \"{doc_type}\" belgesini yükledi."
            )
            
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
        return jsonify({
            "status": "error",
            "message": f"Yükleme hatası: {str(e)}"
        }), 500


@bp.route("/api/kdv/document/delete/<int:doc_id>", methods=["DELETE"])
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici", "uzman"))
def delete_document(doc_id):
    user_id = session.get("user_id")
    role = session.get("role")

    with get_conn() as conn:
        c = conn.cursor()

        # 🔒 YETKİ KONTROLÜ
        c.execute("""
            SELECT d.file_path, f.mukellef_id 
            FROM kdv_documents d
            JOIN kdv_files f ON d.file_id = f.id
            WHERE d.id = %s
        """, (doc_id,))
        row = c.fetchone()

        if not row:
            return jsonify({"status": "error", "message": "Belge bulunamadı."}), 404

        if role == "uzman":
            # Uzman → sadece kendine atanmış mükellefin belgesini silebilir
            c.execute("""
                SELECT 1
                FROM kdv_user_assignments
                WHERE user_id = %s AND mukellef_id = %s
            """, (user_id, row["mukellef_id"]))
            if not c.fetchone():
                return jsonify({"status": "error", "message": "Bu belgeyi silme yetkiniz yok."}), 403

        if row.get("file_path"):
            import os
            try:
                full_path = os.path.join(current_app.root_path, "static", row["file_path"])
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as e:
                print(f"Dosya silme hatası: {e}")

        # Log için dosya/mükellef bilgisi al
        c.execute("""
            SELECT f.period, m.unvan, d.type
            FROM kdv_documents d
            JOIN kdv_files f ON d.file_id = f.id
            JOIN kdv_mukellef m ON f.mukellef_id = m.id
            WHERE d.id = %s
        """, (doc_id,))
        f_row = c.fetchone()
        log_msg = f"{session.get('username')} {f_row['unvan']} {f_row['period']} dönemi \"{f_row['type']}\" belgesini sildi." if f_row else "Bir belge sildi."

        c.execute("DELETE FROM kdv_documents WHERE id = %s", (doc_id,))
        conn.commit()
        
        kdv_log_action(
            session.get("username", "Admin"),
            "Belge Silme",
            log_msg
        )

    return jsonify({"status": "success", "message": "Belge silindi"})


# --- KDV NOTES (Hızlı Bilgi) ---
@bp.route("/api/kdv/note/add", methods=["POST"])
@api_kdv_access_required
def add_note():
    data = request.json
    file_id = data.get("file_id")
    text = data.get("text")
    
    if not file_id or not text:
        return jsonify({"status": "error", "message": "Eksik bilgi"}), 400
        
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO kdv_notes (file_id, note_text, created_at)
            VALUES (%s, %s, %s)
        """, (file_id, text, now))
        conn.commit()
        
    return jsonify({"status": "success", "message": "Bilgi eklendi"})

@bp.route("/api/kdv/note/update", methods=["POST"])
@api_kdv_access_required
def update_note():
    data = request.json
    note_id = data.get("id")
    text = data.get("text")
    
    if not note_id or not text:
        return jsonify({"status": "error", "message": "Eksik bilgi"}), 400
        
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE kdv_notes
            SET note_text = %s, updated_at = %s
            WHERE id = %s
        """, (text, now, note_id))
        conn.commit()
        
    return jsonify({"status": "success", "message": "Bilgi güncellendi"})

@bp.route("/api/kdv/note/delete/<int:note_id>", methods=["DELETE"])
@api_kdv_access_required
def delete_note(note_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM kdv_notes WHERE id = %s", (note_id,))
        conn.commit()
        
    return jsonify({"status": "success", "message": "Bilgi silindi"})

@bp.route("/api/kdv/delete-file/<int:file_id>", methods=["DELETE"])
@api_kdv_access_required
@role_required(allow_roles=("admin", "ymm", "yonetici"))
def api_delete_file(file_id):
    try:
        user_id = session.get("user_id")
        username = session.get("username", "Unknown")
        
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get file info for log
            c.execute("""
                SELECT kf.mukellef_id, km.unvan, kf.period 
                FROM kdv_files kf 
                LEFT JOIN kdv_mukellef km ON kf.mukellef_id = km.id 
                WHERE kf.id = %s
            """, (file_id,))
            row = c.fetchone()
            
            if not row:
                return jsonify({"status": "error", "message": "Dosya bulunamadı"}), 404
                
            m_name = row['unvan'] or "Bilinmeyen"
            period = row['period']

            # Soft Delete
            c.execute("UPDATE kdv_files SET is_active = FALSE WHERE id = %s", (file_id,))
            conn.commit()
            
            # Log
            kdv_log_action(username, "Dosya Silme", f"{username} kullanıcısı {m_name} mükellefine ait {period} dönemli dosyayı sildi.")
            
        return jsonify({"status": "success", "message": "Dosya başarıyla silindi."})
            
    except Exception as e:
        print(f"Error in delete_file: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
