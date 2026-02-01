from flask import Blueprint, render_template, request, make_response, send_from_directory, url_for, current_app, redirect, flash
from routes.blog import blog_posts
from auth import login_required
from datetime import datetime
import os

bp = Blueprint('main', __name__)

@bp.route("/")
def home():
    stats = {
        "experience_years": 15,
        "financial_ratios": 120,
        "ymm_cities": 2
    }
    return render_template("index.html", blog_posts=blog_posts, stats=stats, latest_posts=blog_posts[:3] if blog_posts else [])

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
def robots_txt():
    response = make_response(render_template("robots.txt"))
    response.headers["Content-Type"] = "text/plain"
    return response

@bp.route("/sitemap.xml")
def sitemap_xml():
    host = request.host_url.rstrip('/')
    urls = []

    # Dinamik Blog URL'leri
    for post in blog_posts:
        if post.get("slug"):
            urls.append({
                "loc": f"{host}/blog/{post['slug']}",
                "lastmod": post.get("date", datetime.now().strftime("%Y-%m-%d")),
                "priority": "0.8"
            })

    # Statik URL'ler
    static_endpoints = [
        ('main.home', {}),
        ('main.mevzuat', {}),
        ('main.indirim', {}),
        ('main.ceza', {}),
        ('main.contact', {}),
        ('tools.asgari', {}),
        ('tools.sermaye', {}),
        ('tools.finansman', {})
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

@bp.route("/mevzuat-degisiklikleri")
def mevzuat_degisiklikleri():
    return render_template("pages/mevzuat_degisiklikleri.html")

@bp.route("/indirim")
def indirim():
    return render_template("pages/indirim.html")

@bp.route("/birlesme")
def birlesme():
    return render_template("pages/birlesme.html")
