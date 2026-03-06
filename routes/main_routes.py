from flask import Blueprint, render_template, request, make_response, send_from_directory, url_for, current_app, redirect, flash

from auth import login_required
from datetime import datetime
import os

bp = Blueprint("main", __name__)

@bp.route("/")
def home():
    stats = {
        "experience_years": 15,
        "financial_ratios": 120,
        "ymm_cities": 2
    }
    return render_template("index.html", stats=stats)

@bp.route("/about")
@login_required
def about():
    return render_template("pages/about.html")

@bp.route("/team")
@login_required
def team():
    return render_template("pages/team.html")

@bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        flash("📨 Mesajınız bize ulaştı, teşekkür ederiz!", "success")
        return redirect(url_for("main.contact"))
    return render_template("pages/contact.html")

@bp.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")

@bp.route("/sitemap.xml")
def sitemap_xml():
    host = request.host_url.rstrip('/')
    urls = []



    # Statik URL'ler
    static_endpoints = [
        ('main.home', {}),
        ('main.about', {}),
        ('main.team', {}),
        ('main.mevzuat', {}),
        ('main.indirim', {}),
        ('main.ceza', {}),
        ('main.birlesme', {}),
        ('main.kdv_tebligi', {}),
        ('main.kv_tebligi', {}),
        ('main.enflasyon_duzeltmesi', {}),
        ('main.mevzuat_degisiklikleri', {}),
        ('main.contact', {}),
        
        # Araçlar (Tools)
        ('tools.asgari', {}),
        ('tools.sermaye', {}),
        ('tools.finansman', {}),
        ('tools.serbest_meslek', {}),
        ('tools.sermaye_azaltimi', {}),
        
        # Hesaplamalar (Calculators)
        ('calculators.index', {}),
        ('calculators.gelir_vergisi', {}),
        ('calculators.ithalat_kdv', {}),
        ('calculators.gecikme_zammi', {}),
        ('calculators.tdhp', {}),
        
        # İndirimli Kurumlar
        ('indirimlikurumlar.index', {}),
    ]

    for rule, kw in static_endpoints:
        try:
            url = url_for(rule, _external=True, **kw)
            urls.append({
                "loc": url,
                "lastmod": datetime.now().strftime("%Y-%m-%d"),
                "priority": "0.5"
            })
        except Exception:
            pass
            
    # Dinamik KDV ve KV rotaları
    import json
    def parse_links(items, base_route):
        for item in items:
            uid = str(item.get("uid", item.get("id", "")))
            clean_uid = uid.replace("/", "-")
            url = url_for(base_route, bolum_id=clean_uid, _external=True)
            urls.append({
                "loc": url,
                "lastmod": datetime.now().strftime("%Y-%m-%d"),
                "priority": "0.8"
            })
            if item.get("sub"):
                parse_links(item["sub"], base_route)
                
    try:
        kdv_path = os.path.join(current_app.root_path, 'static', 'data', 'kdv_tebligi.json')
        if os.path.exists(kdv_path):
            with open(kdv_path, 'r', encoding='utf-8') as f:
                parse_links(json.load(f), 'main.kdv_tebligi')
    except Exception as e:
        current_app.logger.error(f"Sitemap KDV Data Error: {e}")
        
    try:
        kv_path = os.path.join(current_app.root_path, 'static', 'data', 'kv_tebligi.json')
        if os.path.exists(kv_path):
            with open(kv_path, 'r', encoding='utf-8') as f:
                parse_links(json.load(f), 'main.kv_tebligi')
    except Exception as e:
        current_app.logger.error(f"Sitemap KV Data Error: {e}")

    response = make_response(render_template("sitemap.xml", urls=urls))
    response.headers["Content-Type"] = "application/xml"
    return response

@bp.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(current_app.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon'
    )

@bp.route("/ceza")
def ceza():
    return render_template("pages/ceza.html")

@bp.route("/mevzuat")
def mevzuat():
    return render_template("pages/mevzuat.html")

@bp.route("/mevzuat/kdv-tebligi")
@bp.route("/mevzuat/kdv-tebligi/<path:bolum_id>")
def kdv_tebligi(bolum_id=None):
    import json
    selected_item = None
    if bolum_id:
        json_path = os.path.join(current_app.root_path, 'static', 'data', 'kdv_tebligi.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                def find_item(items, target_id):
                    for item in items:
                        uid = str(item.get("uid", item.get("id", "")))
                        clean_uid = uid.replace("/", "-")
                        if clean_uid == target_id:
                            return item
                        if item.get("sub"):
                            found = find_item(item["sub"], target_id)
                            if found:
                                return found
                    return None
                    
                selected_item = find_item(data, bolum_id)
        except Exception as e:
            current_app.logger.error(f"Error reading kdv_tebligi.json: {e}")
            
    return render_template("pages/kdv_tebligi.html", bolum_id=bolum_id, selected_item=selected_item)

@bp.route("/mevzuat/kv-tebligi")
@bp.route("/mevzuat/kv-tebligi/<path:bolum_id>")
def kv_tebligi(bolum_id=None):
    import json
    import os
    from flask import current_app
    selected_item = None
    if bolum_id:
        json_path = os.path.join(current_app.root_path, 'static', 'data', 'kv_tebligi.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                def find_item(items, target_id):
                    for item in items:
                        uid = str(item.get("uid", item.get("id", "")))
                        clean_uid = uid.replace("/", "-")
                        if clean_uid == target_id:
                            return item
                        if item.get("sub"):
                            found = find_item(item["sub"], target_id)
                            if found:
                                return found
                    return None
                    
                selected_item = find_item(data, bolum_id)
        except Exception as e:
            current_app.logger.error(f"Error reading kv_tebligi.json: {e}")
            
    return render_template("pages/kv_tebligi.html", bolum_id=bolum_id, selected_item=selected_item)

@bp.route("/mevzuat-degisiklikleri")
def mevzuat_degisiklikleri():
    return render_template("pages/mevzuat_degisiklikleri.html")

@bp.route("/enflasyon-duzeltmesi")
def enflasyon_duzeltmesi():
    return render_template("pages/enflasyon_duzeltmesi.html")

@bp.route("/indirim")
def indirim():
    return render_template("pages/indirim.html")

@bp.route("/birlesme")
def birlesme():
    return render_template("pages/birlesme.html")
