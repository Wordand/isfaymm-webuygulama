import os
# Prevent OpenMP and threading crashes on Windows - MUST BE BEFORE ANY OTHER IMPORTS
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from flask import Blueprint, render_template, request, make_response, jsonify, send_from_directory, url_for, current_app, redirect, flash
from auth import login_required
from datetime import datetime
import logging
import re
import json
from rapidfuzz import fuzz, process
import threading

_resource_lock = threading.Lock()

bp = Blueprint("main", __name__)

# --- TAX TERMINOLOGY SYNONYMS ---
TAX_SYNONYMS = {
    "stopaj": ["tevkifat", "kesinti"],
    "tevkifat": ["stopaj", "kesinti"],
    "iade": ["geri ödeme", "restitüsyon"],
    "istisna": ["muafiyet", "indirim"],
    "muafiyet": ["istisna"],
    "oran": ["yüzde", "katsayı"],
    "limit": ["sınır", "eşik"],
    "tebliğ": ["mevzuat", "yönetmelik"],
    "ithalat": ["dış alım"],
    "ihracat": ["dış satım"]
}

def expand_query(question):
    """Enriches the query with technical synonyms"""
    q_lower = question.lower()
    expanded_terms = []
    words = re.findall(r"\w+", q_lower)
    
    for word in words:
        if word in TAX_SYNONYMS:
            expanded_terms.extend(TAX_SYNONYMS[word])
            
    if expanded_terms:
        # Avoid duplicate words in the final query
        unique_additions = [t for t in set(expanded_terms) if t not in q_lower]
        return question + " " + " ".join(unique_additions)
    return question

# --- GLOBAL SEARCH CACHE ---
_SEARCH_RESOURCES = {
    "kdv": {"meta": None},
    "kv": {"meta": None}
}

def get_search_resources(tax_type=None):
    global _SEARCH_RESOURCES
    
    with _resource_lock:
        if tax_type in ["kdv", "kv"]:
            if _SEARCH_RESOURCES[tax_type]["meta"] is None:
                # Try to load the simpler metadata from embeddings dir, or fall back to main json
                meta_path = os.path.join(current_app.root_path, "static", "data", "embeddings", f"{tax_type}_meta.json")
                if not os.path.exists(meta_path):
                    # Fallback to the original json if meta doesn't exist
                    meta_path = os.path.join(current_app.root_path, "static", "data", f"{tax_type}_tebligi.json")
                
                if not os.path.exists(meta_path):
                    current_app.logger.error(f"❌ Missing data files for {tax_type.upper()}")
                    return None

                try:
                    current_app.logger.info(f"📊 Loading {tax_type.upper()} Metadata...")
                    with open(meta_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
                    # If it's the raw tebligi.json, we need to flatten it
                    if isinstance(data, list) and len(data) > 0 and "sub" in data[0]:
                        flat_items = []
                        def flatten(items):
                            for it in items:
                                if it.get("content"):
                                    flat_items.append({
                                        "id": it.get("uid", it.get("id")),
                                        "title": it.get("title"),
                                        "content": it.get("content")
                                    })
                                if it.get("sub"): flatten(it["sub"])
                        flatten(data)
                        _SEARCH_RESOURCES[tax_type]["meta"] = flat_items
                    else:
                        _SEARCH_RESOURCES[tax_type]["meta"] = data
                        
                    current_app.logger.info(f"✅ {tax_type.upper()} Metadata loaded.")
                except Exception as e:
                    current_app.logger.error(f"❌ {tax_type.upper()} Meta Load Failed: {e}")
                    return None
                    
    return _SEARCH_RESOURCES

# --- SEARCH HELPERS ---

def get_smart_snippet(content, question, search_words):
    """Karakter değil, tam cümle bazlı akıllı paragraf üretici"""
    if not search_words: return content[:250] + "..."
    
    # Metni cümlelere böl
    sentences = re.split(r'(?<=[.!?])\s+', content)
    
    # Aranan kelimelerin en çok geçtiği veya ilk geçtiği cümleyi bul
    best_sentence_idx = -1
    for i, s in enumerate(sentences):
        if any(w.lower() in s.lower() for w in search_words):
            best_sentence_idx = i
            break
            
    if best_sentence_idx != -1:
        # Seçilen cümle ve yanındaki cümleyi al (daha dolgun bir paragraf için)
        start = max(0, best_sentence_idx)
        end = min(len(sentences), best_sentence_idx + 2)
        snippet = " ".join(sentences[start:end])
        return snippet if len(snippet) < 350 else snippet[:347] + "..."
        
    return content[:250] + "..."

def get_legal_level(id_str):
    """Determines the legal hierarchy level of an ID"""
    if not id_str: return ""
    levels = id_str.strip('.').split('.')
    depth = len(levels)
    if depth == 1: return "Bölüm"
    if depth == 2: return "Madde"
    if depth == 3: return "Alt Madde"
    return "Fıkra/Bent"

def detect_query_intent(question):
    """Sorgunun amacını tespit eder (Oran, Liste, Tanım vb.)"""
    q = question.lower()
    if any(w in q for w in ["oran", "yüzde", "%", "tutar", "limit", "sınır", "kaçtır"]):
        return "RATE"
    if any(w in q for w in ["nedir", "ne demek", "tanım", "kapsam", "kimdir"]):
        return "DEFINITION"
    if any(w in q for w in ["çeşit", "tür", "liste", "nelerdir", "hangileri", "sayılan"]):
        return "LIST"
    if any(w in q for w in ["nasıl", "yol", "yöntem", "hesapla", "şartlar"]):
        return "HOWTO"
    return "GENERAL"

def extract_list_from_content(content):
    """Metin içindeki liste öğelerini (madde madde) ayıklar"""
    # 1. Sayısal listeler (1., 2. veya a), b))
    items = re.findall(r"(?:^|\s)(\d+\.|\w\))\s+([^.]+?)(?=\s+\d+\.|\s+\w\)|$)", content)
    if items:
        return [f"{i[0]} {i[1].strip()}" for i in items[:8]] # İlk 8 madde
    
    # 2. Tireli listeler
    items = re.findall(r"(?:^|\s)-\s+([^.]+?)(?=\s+-|$)", content)
    if items:
        return [f"• {i.strip()}" for i in items[:8]]
        
    return []

def synthesize_ai_answer(best_item, question, intent):
    """Nokta atışı cevap üretici: Sadece en alakalı bilgiyi (Örn: Oran) gösterir"""
    content = (best_item.get('content', '') or "").strip()
    title = best_item.get('title', 'İlgili Mevzuat')
    
    # Mevzuat gürültülerini temizle
    content = re.sub(r'(\d+/\d+)\d{2,}', r'\1', content)
    sentences = re.split(r'(?<=[.!?])\s+', content)
    
    # 1. ORAN SORGUSU: Dolgun Kutu
    if intent == "RATE":
        all_rates = re.findall(r"(\d+/10|%\s*\d+)", content)
        best_sentence = ""
        for s in sentences:
            if any(r in s for r in ["/10", "%"]):
                best_sentence = s.strip()
                break
        
        if all_rates:
            val = all_rates[0].replace(" ", "")
            return f"""
            <div class='py-3'>
                <div class='row align-items-center'>
                    <div class='col-md-4 text-center border-end'>
                        <div class='display-4 fw-bold text-primary mb-1'>{val}</div>
                        <div class='small text-muted text-uppercase fw-bold'>Güncel Oran/Limit</div>
                    </div>
                    <div class='col-md-8 ps-md-4'>
                        <h6 class='fw-bold text-dark mb-2'><i class='bi bi-info-circle-fill text-primary me-2'></i>{title}</h6>
                        <p class='text-secondary small mb-0 lh-base'>{best_sentence}</p>
                    </div>
                </div>
            </div>
            """

    # 2. LİSTE SORGUSU: Madde Madde Göster
    if intent == "LIST":
        list_items = extract_list_from_content(content)
        if list_items:
            list_html = "".join([f"<li class='mb-2'>{item}</li>" for item in list_items])
            return f"""
            <div class='py-2'>
                <h6 class='fw-bold text-dark mb-3'><i class='bi bi-list-check text-success me-2'></i>{title} (Özet Liste)</h6>
                <ul class='small text-secondary list-unstyled ps-0'>
                    {list_html}
                </ul>
                <div class='small text-primary mt-2 italic'>* Detaylı bilgi için aşağıdaki kaynak maddeyi inceleyebilirsiniz.</div>
            </div>
            """

    # 3. GENEL / TANIM SORGUSU: Özetle
    search_terms = [t for t in re.findall(r"\w+", question.lower()) if len(t) > 3]
    relevant_sentences = []
    for s in sentences:
        if any(t in s.lower() for t in search_terms):
            relevant_sentences.append(s.strip())
            if len(relevant_sentences) >= 3: break

    summary = " ".join(relevant_sentences) if relevant_sentences else content[:250] + "..."
    return f"🚀 <b>Özet Analiz:</b> {summary}"

def perform_hybrid_search(tax_type, question):
    try:
        current_app.logger.info(f"🔍 Starting {tax_type} fuzzy search for: {question[:50]}...")
        resources = get_search_resources(tax_type)
        if not resources or not resources[tax_type]["meta"]:
            return "Sistem henüz hazır değil, lütfen bekleyin.", []

        meta_data = resources[tax_type]["meta"]
        expanded_question = expand_query(question).lower()
        search_words = [w for w in re.findall(r"\w+", question.lower()) if len(w) > 2]
        
        # 1. Regex ID Extraction
        article_match = re.search(r"\b\d+(\.\d+)*\b", question)
        target_id = article_match.group() if article_match else None

        candidate_results = []
        for item in meta_data:
            score = 0
            content_lower = (item.get("content", "") or "").lower()
            title_lower = (item.get("title", "") or "").lower()
            id_str = (item.get("id", "") or "").lower()
            
            # Fuzzy Match scores (Title is more important)
            title_fuzzy = fuzz.partial_ratio(expanded_question, title_lower)
            content_fuzzy = fuzz.partial_ratio(expanded_question, content_lower)
            
            score += title_fuzzy * 0.8
            score += content_fuzzy * 0.2
            
            # Exact Phrase Matching
            if question.lower() in title_lower: score += 40
            elif question.lower() in content_lower: score += 20
            
            # Keyword Boost
            for w in search_words:
                if w in title_lower: score += 15
                if w in content_lower: score += 5
            # Article/ID Boost
            if target_id and target_id in id_str:
                score += 100
                
            if score > 50:
                candidate_results.append({
                    "score": score,
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "content": item.get("content")
                })

        # Diversification & Best Result
        candidate_results = sorted(candidate_results, key=lambda x: x["score"], reverse=True)
        final_results = []
        seen_ids = set()
        for res in candidate_results:
            if res["id"] not in seen_ids:
                res["snippet"] = get_smart_snippet(res["content"], question, search_words)
                final_results.append(res)
                seen_ids.add(res["id"])
            if len(final_results) >= 5: break
        
        if not final_results:
            return "Üzgünüm, aradığınız konuyu mevzuatta bulamadım.", []

        intent = detect_query_intent(question)
        answer = synthesize_ai_answer(final_results[0], question, intent)
        
        return answer, final_results

    except Exception as e:
        logging.error(f"Search Crash Avoided: {e}")
        return "Şu an teknik bir aksaklık yaşanıyor, lütfen aramayı basitleştirip tekrar deneyin.", []

# --- PAGE ROUTES ---

@bp.route("/")
def home():
    stats = {"experience_years": 15, "financial_ratios": 120, "ymm_cities": 2}
    return render_template("index.html", stats=stats)

@bp.route("/about")
@login_required
def about(): return render_template("pages/about.html")

@bp.route("/team")
@login_required
def team(): return render_template("pages/team.html")

@bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        flash("📨 Mesajınız bize ulaştı, teşekkür ederiz!", "success")
        return redirect(url_for("main.contact"))
    return render_template("pages/contact.html")

@bp.route("/robots.txt")
def robots(): return send_from_directory("static", "robots.txt")

@bp.route("/sitemap.xml")
def sitemap_xml():
    host = request.host_url.rstrip('/')
    urls = []
    static_endpoints = [
        ('main.home', {}), ('main.about', {}), ('main.team', {}), ('main.mevzuat', {}),
        ('main.indirim', {}), ('main.ceza', {}), ('main.birlesme', {}), ('main.kdv_tebligi', {}),
        ('main.kv_tebligi', {}), ('main.enflasyon_duzeltmesi', {}), ('main.mevzuat_degisiklikleri', {}), ('main.contact', {}),
        ('tools.asgari', {}), ('tools.sermaye', {}), ('tools.finansman', {}), ('tools.serbest_meslek', {}), ('tools.sermaye_azaltimi', {}),
        ('calculators.index', {}), ('calculators.gelir_vergisi', {}), ('calculators.ithalat_kdv', {}), ('calculators.gecikme_zammi', {}), ('calculators.tdhp', {}),
        ('indirimlikurumlar.index', {}),
    ]
    for rule, kw in static_endpoints:
        try:
            url = url_for(rule, _external=True, **kw)
            urls.append({"loc": url, "lastmod": datetime.now().strftime("%Y-%m-%d"), "priority": "0.5"})
        except Exception: pass
            
    def parse_links(items, base_route):
        for item in items:
            uid = str(item.get("uid", item.get("id", "")))
            url = url_for(base_route, bolum_id=uid.replace("/", "-"), _external=True)
            urls.append({"loc": url, "lastmod": datetime.now().strftime("%Y-%m-%d"), "priority": "0.8"})
            if item.get("sub"): parse_links(item["sub"], base_route)
                
    try:
        for t in ["kdv", "kv"]:
            path = os.path.join(current_app.root_path, 'static', 'data', f'{t}_tebligi.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f: parse_links(json.load(f), f'main.{t}_tebligi')
    except Exception: pass
    response = make_response(render_template("sitemap.xml", urls=urls))
    response.headers["Content-Type"] = "application/xml"
    return response

@bp.route("/favicon.ico")
def favicon(): return send_from_directory(os.path.join(current_app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@bp.route("/ceza")
def ceza(): return render_template("pages/ceza.html")

@bp.route("/mevzuat")
def mevzuat(): return render_template("pages/mevzuat.html")

@bp.route("/mevzuat/kdv-tebligi")
@bp.route("/mevzuat/kdv-tebligi/<path:bolum_id>")
def kdv_tebligi(bolum_id=None):
    selected_item = None
    if bolum_id:
        json_path = os.path.join(current_app.root_path, 'static', 'data', 'kdv_tebligi.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                def find_item(items, target_id):
                    for item in items:
                        if str(item.get("uid", item.get("id", ""))).replace("/", "-") == target_id: return item
                        if item.get("sub"):
                            found = find_item(item["sub"], target_id)
                            if found: return found
                    return None
                selected_item = find_item(data, bolum_id)
        except Exception: pass
    return render_template("pages/kdv_tebligi.html", bolum_id=bolum_id, selected_item=selected_item)

@bp.route("/mevzuat/kv-tebligi")
@bp.route("/mevzuat/kv-tebligi/<path:bolum_id>")
def kv_tebligi(bolum_id=None):
    selected_item = None
    if bolum_id:
        json_path = os.path.join(current_app.root_path, 'static', 'data', 'kv_tebligi.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                def find_item(items, target_id):
                    for item in items:
                        if str(item.get("uid", item.get("id", ""))).replace("/", "-") == target_id: return item
                        if item.get("sub"):
                            found = find_item(item["sub"], target_id)
                            if found: return found
                    return None
                selected_item = find_item(data, bolum_id)
        except Exception: pass
    return render_template("pages/kv_tebligi.html", bolum_id=bolum_id, selected_item=selected_item)

@bp.route("/mevzuat-degisiklikleri")
def mevzuat_degisiklikleri(): return render_template("pages/mevzuat_degisiklikleri.html")

@bp.route("/enflasyon-duzeltmesi")
def enflasyon_duzeltmesi(): return render_template("pages/enflasyon_duzeltmesi.html")

@bp.route("/indirim")
def indirim(): return render_template("pages/indirim.html")

@bp.route("/birlesme")
def birlesme(): return render_template("pages/birlesme.html")

# --- API ROUTES ---

@bp.route("/api/kdv-search", methods=["POST"])
def kdv_search():
    data = request.get_json()
    question = data.get("question", "").strip().lower()
    if not question: return jsonify({"answer": "Soru giriniz.", "items": []})
    answer, items = perform_hybrid_search("kdv", question)
    return jsonify({"answer": answer, "items": items})

@bp.route("/api/kv-search", methods=["POST"])
def kv_search():
    data = request.get_json()
    question = data.get("question", "").strip().lower()
    if not question: return jsonify({"answer": "Soru giriniz.", "items": []})
    answer, items = perform_hybrid_search("kv", question)
    return jsonify({"answer": answer, "items": items})

@bp.route("/api/kdv-suggestions", methods=["GET"])
def kdv_suggestions():
    expert_questions = ["Tam Tevkifat Çeşitleri?", "Kısmi Tevkifat Oranları?", "İade Hakkı Doğuran İşlemler", "Yolcu Beraberinde Eşya İadesi"]
    import random
    return jsonify({"suggestions": random.sample(expert_questions, 4)})

@bp.route("/api/kv-suggestions", methods=["GET"])
def kv_suggestions():
    expert_questions = ["İştirak Kazançları İstisnası?", "Örtülü Sermaye Şartları?", "Kurumlar Vergisi Oranı 2026", "Zarar Mahsubu"]
    import random
    return jsonify({"suggestions": random.sample(expert_questions, 4)})
