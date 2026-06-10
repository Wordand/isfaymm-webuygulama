import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional runtime dependency
    PdfReader = None


TOPIC_RULES = [
    ("Tevsi ve sabit kıymet oranlaması", ["tevsi", "sabit kıymet", "sabit kiymet", "oranlama"]),
    ("Diğer faaliyet kazancı", ["diğer faaliyet", "diger faaliyet", "yatırım dönemi", "yatirim donemi"]),
    ("Yatırım kazancı", ["yatırımdan elde edilen kazanç", "yatirimdan elde edilen kazanc"]),
    ("Endeksleme", ["endeks", "yeniden değerleme", "yeniden degerleme"]),
    ("Tamamlama vizesi", ["tamamlama vizesi", "vize"]),
    ("Devir ve belge devri", ["devir", "devralan", "devreden"]),
    ("Katkıya dahil edilmeyen harcamalar", ["arsa", "arazi", "royalti", "yedek parça", "yedek parca", "amortismana tabi olmayan"]),
    ("Birden fazla belge", ["birden fazla", "iki adet yatırım teşvik", "iki adet yatirim tesvik", "birden çok teşvik", "birden cok tesvik"]),
]

POPULAR_TOPICS = [
    "Tevsi ve sabit kıymet oranlaması",
    "Diğer faaliyet kazancı",
    "Yatırım kazancı",
    "Endeksleme",
    "Tamamlama vizesi",
    "Katkıya dahil edilmeyen harcamalar",
]

QUESTION_MARKERS = [
    "İlgide kayıtlı özelge talep formunuzda",
    "İlgide kayıtlı özelge talep formunda",
    "İlgide kayıtlı dilekçenizde",
    "İlgide kayıtlı başvurunuzda",
    "özelge talep formunuzda",
]

ANSWER_MARKERS = [
    "Bu hüküm ve açıklamalara göre",
    "Bu hüküm ve açıklamalar çerçevesinde",
    "Yukarıda yer alan hüküm ve açıklamalar çerçevesinde",
    "Yukarıda yer alan hüküm",
    "Yukarıda yapılan açıklamalar",
    "Buna göre",
    "Sonuç olarak",
]

BOILERPLATE_MARKERS = [
    "Bilgi edinilmesini",
    "Bu Özelge",
    "Bu ozelge",
    "(*)",
    "(**)",
]


def _first_existing(*paths):
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def slugify(value, max_length=120):
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    value = value[:max_length].strip("-")
    return value or "ozelge"


def display_code(filename):
    return Path(filename).stem.replace("_", " ").strip()


def normalize_search_text(value):
    value = (value or "").lower()
    tr_map = str.maketrans("çğıöşüâîû", "cgiosuaiu")
    value = value.translate(tr_map)
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_text(text):
    text = text or ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact_text(text):
    text = clean_text(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compact_for_display(value, limit=520):
    value = compact_text(value)
    value = re.sub(r"\s+([,.;:])", r"\1", value)
    value = value.strip(" ;:-")
    if len(value) > limit:
        value = value[:limit].rsplit(" ", 1)[0].strip(" ,.;:-") + "..."
    elif value and value[-1] not in ".!?":
        value += "."
    return value


def split_sentences(value):
    value = compact_text(value)
    value = re.sub(r"\s*~\s*", " ", value)
    parts = re.split(r"(?<=[.!?])\s+|;\s+", value)
    return [part.strip(" -•") for part in parts if len(part.strip(" -•")) > 18]


def remove_boilerplate(value):
    compact = compact_text(value)
    stop_positions = []
    for marker in BOILERPLATE_MARKERS:
        idx = find_marker_index(compact, [marker])
        if idx is not None and idx > 40:
            stop_positions.append(idx)
    if stop_positions:
        compact = compact[:min(stop_positions)]
    return compact


def pick_relevant_sentences(value, keywords, limit=3):
    sentences = split_sentences(value)
    picked = []
    norm_keywords = [normalize_search_text(k) for k in keywords]
    for sentence in sentences:
        norm_sentence = normalize_search_text(sentence)
        if any(k in norm_sentence for k in norm_keywords):
            if sentence not in picked:
                picked.append(sentence)
        if len(picked) >= limit:
            break
    if not picked:
        picked = sentences[:limit]
    return picked


def join_decision_sentences(sentences, limit=430):
    cleaned = []
    for sentence in sentences:
        sentence = re.sub(r"^[-~•]\s*", "", sentence).strip()
        sentence = re.sub(r"\s+", " ", sentence)
        if sentence and sentence not in cleaned:
            cleaned.append(sentence)
    return compact_for_display(" ".join(cleaned), limit=limit)


def strip_leading_marker(value, markers):
    cleaned = compact_text(value)
    lowered = normalize_search_text(cleaned)
    for marker in markers:
        norm = normalize_search_text(marker)
        if lowered.startswith(norm):
            return cleaned[len(marker):].strip(" ;:-,.")
    return cleaned


def extract_after_label(text, label, max_lines=2):
    lines = [line.strip() for line in (text or "").splitlines()]
    label_norm = normalize_search_text(label)
    stop_labels = {
        "konu",
        "sayi",
        "kanun",
        "kanun numarasi",
        "ozelge tarihi",
        "ozelge no",
        "ilgide kayitli",
    }
    for idx, line in enumerate(lines):
        line_norm = normalize_search_text(line)
        if line_norm == label_norm or label_norm in line_norm:
            picked = []
            for next_line in lines[idx + 1:idx + 1 + max_lines + 5]:
                if not next_line:
                    continue
                low = normalize_search_text(next_line)
                if low in stop_labels:
                    break
                picked.append(next_line)
                if len(picked) >= max_lines:
                    break
            return " ".join(picked).strip()
    return ""


def extract_subject(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    collected = []
    for line in lines[:10]:
        low = normalize_search_text(line)
        if low.startswith(("kanun", "ozelge", "gelir idaresi", "t c", "i c")):
            break
        collected.append(line)
    first_heading = " ".join(collected).strip()
    if len(first_heading) >= 12:
        return compact_for_display(first_heading, limit=300).rstrip(".")
    konu = extract_after_label(text, "Konu", max_lines=3)
    return compact_for_display(konu, limit=300).rstrip(".") if konu else ""


def extract_date_sort(value):
    match = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", value or "")
    if not match:
        return ""
    day, month, year = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def display_date(value):
    sort_value = extract_date_sort(value)
    if not sort_value:
        return value or ""
    year, month, day = sort_value.split("-")
    return f"{day}.{month}.{year}"


def find_marker_index(text, markers):
    text_norm = normalize_search_text(text)
    best = None
    for marker in markers:
        marker_norm = normalize_search_text(marker)
        idx = text_norm.find(marker_norm)
        if idx == -1:
            continue
        plain_marker = re.search(re.escape(marker), text, flags=re.I)
        original_idx = plain_marker.start() if plain_marker else idx
        best = original_idx if best is None else min(best, original_idx)
    return best


def slice_between_markers(text, start_markers, end_markers):
    compact = compact_text(text)
    start_idx = find_marker_index(compact, start_markers)
    if start_idx is None:
        return ""
    chunk = compact[start_idx:]
    end_candidates = []
    for marker in end_markers:
        idx = find_marker_index(chunk[len(start_markers[0]):] if chunk else "", [marker])
        if idx is not None:
            end_candidates.append(idx + len(start_markers[0]))
    if end_candidates:
        chunk = chunk[:min(end_candidates)]
    return chunk


def extract_question(text):
    compact = compact_text(text)
    subject = extract_subject(text)
    smart = make_smart_question(compact, subject)
    if smart:
        return smart

    start_idx = find_marker_index(compact, QUESTION_MARKERS)
    if start_idx is None:
        return compact_for_display(subject, limit=420)

    tail = compact[start_idx:]
    stop_markers = [
        "konularında Başkanlığımız görüşü",
        "hususunda Başkanlığımız görüşü",
        "Başkanlığımız görüşü sorulmuştur",
        "5520 sayılı",
        "Kurumlar Vergisi Kanununun",
        "indirimli kurumlar vergisi uygulaması ile ilgili",
    ]
    stop_positions = []
    for marker in stop_markers:
        idx = find_marker_index(tail, [marker])
        if idx is not None and idx > 20:
            stop_positions.append(idx)
    if stop_positions:
        tail = tail[:min(stop_positions)]
    tail = strip_leading_marker(tail, QUESTION_MARKERS)
    return compact_for_display(tail, limit=360)


def extract_answer(text):
    compact = compact_text(text)
    smart = make_smart_answer(compact)
    if smart:
        return smart

    start_idx = find_marker_index(compact, ANSWER_MARKERS)
    if start_idx is None:
        return make_summary(text)
    tail = compact[start_idx:]
    tail = remove_boilerplate(tail)
    return compact_for_display(tail, limit=430)


def make_smart_question(compact, subject):
    norm = normalize_search_text(compact)
    title = compact_for_display(subject, limit=180).rstrip(".")

    if "egitim ogretim" in norm and "istisna" in norm and "indirimli kurumlar" in norm:
        return "Özel okul yatırımında eğitim kazancı istisnası ile indirimli kurumlar vergisinin hangi kazanç ve dönemlerde uygulanacağı soruluyor."

    if "erp" in norm and ("lisans" in norm or "yazilim" in norm):
        return "ERP lisansı veya yazılım bedelinin yatırım harcaması sayılıp sayılmayacağı ve yatırıma katkı hesabına dahil edilip edilmeyeceği soruluyor."

    if "diger faaliyet" in norm and ("ust sinir" in norm or "matrah" in norm):
        return "Yatırım döneminde diğer faaliyet kazançlarına indirimli kurumlar vergisi uygulanırken üst sınır ve indirimli matrahın nasıl hesaplanacağı soruluyor."

    if "yeniden degerleme" in norm or "endeks" in norm:
        return "Kullanılamayan yatırıma katkı tutarının yeniden değerleme veya endeksleme ile artırılıp artırılamayacağı soruluyor."

    if "tevsi" in norm and ("sabit kiymet" in norm or "oranlama" in norm):
        return "Tevsi yatırımda indirimli kurumlar vergisine esas kazancın ayrı izlenememesi halinde sabit kıymet oranlamasının nasıl yapılacağı soruluyor."

    if any(k in norm for k in ["arsa", "arazi", "royalti", "yedek parca", "amortismana tabi olmayan", "yazilim"]):
        return "Yapılan harcamanın indirimli kurumlar vergisi hesabında yatırım harcaması olarak dikkate alınıp alınmayacağı soruluyor."

    if "tamamlama vizesi" in norm:
        return "Tamamlama vizesi, yatırım dönemi veya işletme döneminin indirimli kurumlar vergisi kullanımına etkisi soruluyor."

    if title:
        return f"{title} konusunda uygulamanın nasıl yapılacağı soruluyor."
    return ""


def make_smart_answer(compact):
    norm = normalize_search_text(compact)
    start_idx = find_marker_index(compact, ANSWER_MARKERS)
    decision = compact[start_idx:] if start_idx is not None else compact
    decision = remove_boilerplate(decision)

    if "egitim ogretim" in norm and "istisna" in norm and "indirimli kurumlar" in norm:
        return (
            "Taşınan okul veya kapasite artışı yeni okul açılışı sayılmadığından mevcut okullar için yeniden eğitim kazancı istisnası uygulanamaz. "
            "Yeni fen lisesi için faaliyete geçtikten sonra gerekli başvuru yapılırsa eğitim kazancı istisnası uygulanabilir. "
            "İstisnaya konu edilen kazançlarda aynı dönem için indirimli kurumlar vergisi kullanılamaz; yatırım döneminde varsa diğer faaliyet kazançları için sınırlar dahilinde kullanım mümkündür."
        )

    if "erp" in norm and ("lisans" in norm or "yazilim" in norm):
        sentences = pick_relevant_sentences(
            decision,
            ["dikkate alınamaz", "dikkate alınabilir", "yatırım harcaması", "amortisman", "lisans", "yazılım"],
        )
        return join_decision_sentences(sentences)

    if "diger faaliyet" in norm and ("ust sinir" in norm or "matrah" in norm):
        sentences = pick_relevant_sentences(
            decision,
            ["gerçekleştirilen yatırım harcaması", "toplam yatırıma katkı", "diğer faaliyet", "üst sınır", "mümkün"],
        )
        return join_decision_sentences(sentences)

    if "yeniden degerleme" in norm or "endeks" in norm:
        sentences = pick_relevant_sentences(
            decision,
            ["yeniden değerleme", "tamamlandığı hesap dönemi", "kalan yatırıma katkı", "mümkün"],
        )
        return join_decision_sentences(sentences)

    if "tevsi" in norm and ("sabit kiymet" in norm or "oranlama" in norm):
        sentences = pick_relevant_sentences(
            decision,
            ["ayrı hesaplarda", "oranlama", "sabit kıymet", "brüt", "dönem sonunda", "mümkün"],
        )
        return join_decision_sentences(sentences)

    if any(k in norm for k in ["arsa", "arazi", "royalti", "yedek parca", "amortismana tabi olmayan", "yazilim"]):
        sentences = pick_relevant_sentences(
            decision,
            ["yatırım harcaması", "dikkate alınamaz", "dikkate alınabilir", "amortismana tabi", "katkı tutarı"],
        )
        return join_decision_sentences(sentences)

    sentences = pick_relevant_sentences(
        decision,
        ["mümkün", "mümkün değildir", "dikkate alınacaktır", "uygulanabilecektir", "yararlanmanız", "tabiidir"],
    )
    return join_decision_sentences(sentences)


def extract_structured_summary(text):
    return {
        "konu_ozeti": compact_for_display(extract_subject(text), limit=220),
        "soru_ozeti": extract_question(text),
        "cevap_ozeti": extract_answer(text),
    }


def infer_topics(text, filename):
    haystack = f"{filename} {text or ''}".lower()
    topics = []
    for label, needles in TOPIC_RULES:
        if any(n.lower() in haystack for n in needles):
            topics.append(label)
    return topics or ["Özelge"]


def extract_metadata(text, filename):
    subject = extract_subject(text)
    ozelge_no = extract_after_label(text, "Özelge No", max_lines=1)
    if not ozelge_no:
        match = re.search(r"([A-Z]?\-?\d[\w.\-\[\]/ ]{8,})", filename)
        ozelge_no = match.group(1).strip() if match else display_code(filename)
    tarih = extract_after_label(text, "Özelge Tarihi", max_lines=1)
    if tarih and not re.search(r"\d{1,2}[./]\d{1,2}[./]\d{4}", tarih):
        match = re.search(r"\d{1,2}[./]\d{1,2}[./]\d{4}", text or "")
        tarih = match.group(0) if match else tarih
    elif not tarih:
        match = re.search(r"\d{1,2}[./]\d{1,2}[./]\d{4}", text or "")
        tarih = match.group(0) if match else ""
    return {
        "subject": subject,
        "ozelge_no": ozelge_no,
        "date": display_date(tarih),
        "date_sort": extract_date_sort(tarih),
    }


def make_summary(text):
    text = clean_text(text)
    if not text:
        return ""
    compact = compact_text(text)
    compact = re.sub(r"Kanun Numarası.*?Özelge Tarihi\s+\d{1,2}[./]\d{1,2}[./]\d{4}", " ", compact, flags=re.I)
    compact = re.sub(r"T\.?C\.? GELİR İDARESİ BAŞKANLIĞI.*?Konu", "Konu", compact, flags=re.I)
    for marker in ANSWER_MARKERS:
        idx = find_marker_index(compact, [marker])
        if idx is not None:
            return compact_for_display(compact[idx:idx + 520], limit=520)
    konu_idx = normalize_search_text(compact).find("konu")
    if 0 <= konu_idx < 500:
        compact = compact[konu_idx + 4:].strip()
    return compact_for_display(compact[:420], limit=420)


def item_sort_key(item):
    date_sort = item.get("date_sort") or extract_date_sort(item.get("date"))
    return (date_sort, item.get("title") or "")


def rank_ozelge(item, query):
    q = normalize_search_text(query)
    if not q:
        return 0
    words = [w for w in q.split() if len(w) > 1]
    fields = {
        "title": normalize_search_text(item.get("title")),
        "topics": normalize_search_text(" ".join(item.get("topics", []))),
        "summary": normalize_search_text(item.get("summary")),
        "soru": normalize_search_text(item.get("soru_ozeti")),
        "cevap": normalize_search_text(item.get("cevap_ozeti")),
        "no": normalize_search_text(item.get("ozelge_no") or item.get("code")),
        "date": normalize_search_text(item.get("date")),
        "text": normalize_search_text(item.get("search_text")),
    }
    score = 0
    if q in fields["title"]:
        score += 90
    if q in fields["topics"]:
        score += 65
    if q in fields["no"]:
        score += 70
    if q in fields["date"]:
        score += 45
    if q in fields["soru"]:
        score += 35
    if q in fields["cevap"]:
        score += 35
    if q in fields["summary"]:
        score += 25
    if q in fields["text"]:
        score += 12
    for word in words:
        if word in fields["title"]:
            score += 22
        if word in fields["topics"]:
            score += 16
        if word in fields["no"]:
            score += 16
        if word in fields["soru"]:
            score += 9
        if word in fields["cevap"]:
            score += 9
        if word in fields["text"]:
            score += 3
    return score


def search_ozelgeler(items, query):
    if not query:
        return sorted(items, key=item_sort_key, reverse=True)
    ranked = [(rank_ozelge(item, query), item) for item in items]
    ranked = [pair for pair in ranked if pair[0] > 0]
    return [item for _, item in sorted(ranked, key=lambda pair: (pair[0], item_sort_key(pair[1])), reverse=True)]


def read_ocr_text(root, pdf_stem):
    text_path = root / "services" / "ocr_text" / f"{pdf_stem}.txt"
    if not text_path.exists():
        return ""
    for encoding in ("utf-8", "utf-8-sig", "cp1254"):
        try:
            return clean_text(text_path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    return clean_text(text_path.read_text(encoding="utf-8", errors="ignore"))


def extract_text_from_pdf(pdf_path, max_pages=None):
    if PdfReader is None:
        return "", 0, "pypdf_yok"
    try:
        reader = PdfReader(str(pdf_path))
        pages = len(reader.pages)
        texts = []
        limit = min(pages, max_pages) if max_pages else pages
        for page in reader.pages[:limit]:
            texts.append(page.extract_text() or "")
        text = "\n".join(texts).strip()
        return text, pages, "metin_var" if text else "ocr_gerekli"
    except Exception as exc:
        return "", 0, f"hata: {type(exc).__name__}"


def build_ozelge_index(root_path):
    root = Path(root_path)
    source_dir = _first_existing(root / "services" / "ozelgeler", root / "ozelgeler")
    data_dir = root / "static" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    yeni_json_path = data_dir / "ozelgeler_yeni.json"

    yeni_data = None
    if yeni_json_path.exists():
        try:
            with open(yeni_json_path, "r", encoding="utf-8") as f:
                yeni_data = json.load(f)
        except Exception:
            yeni_data = None

    if yeni_data:
        unique_yeni_data = []
        seen_keys = set()
        for item in yeni_data:
            key = (item.get("ozelge_no") or "").strip().lower()
            if not key:
                key = (item.get("konu") or "").strip().lower()
            if key not in seen_keys:
                seen_keys.add(key)
                unique_yeni_data.append(item)
        yeni_data = unique_yeni_data

        def normalize_no(no):
            if not no:
                return ""
            no = no.replace("İ", "I").replace("ı", "i").replace("Ğ", "G").replace("ğ", "g")
            no = no.replace("Ö", "O").replace("ö", "o").replace("Ş", "S").replace("ş", "s")
            no = no.replace("Ç", "C").replace("ç", "c")
            no = re.sub(r'[^a-zA-Z0-9]', '', no)
            return no.lower().strip()

        json_map = {}
        for item in yeni_data:
            norm = normalize_no(item.get("ozelge_no"))
            if norm:
                json_map[norm] = item

        def tr_lower(text):
            mapping_dict = {'I': 'ı', 'İ': 'i', 'Ö': 'ö', 'Ü': 'ü', 'Ş': 'ş', 'Ğ': 'ğ', 'Ç': 'ç'}
            for k, v in mapping_dict.items():
                text = text.replace(k, v)
            return text.lower()

        def tr_normalize(text):
            text = tr_lower(text)
            tr_map = str.maketrans('çğıöşüâîû', 'cgiosuaiu')
            text = text.translate(tr_map)
            text = re.sub(r'[^a-z0-9\s]', ' ', text)
            return re.sub(r'\s+', ' ', text).strip()

        ocr_dir = root / "services" / "ocr_text"
        txt_files = list(ocr_dir.glob("*.txt"))
        ocr_texts = {}
        for txt_file in txt_files:
            if txt_file.name in ["birlesik.txt", "ozelgeler_88.txt", "ozelgeler_88_yeni.txt"]:
                continue
            try:
                text = txt_file.read_text(encoding="utf-8", errors="ignore")
                ocr_texts[txt_file.name] = tr_normalize(text)
            except Exception:
                pass

        all_pairs = []
        for idx, item in enumerate(yeni_data):
            ozelge_no = item.get("ozelge_no", "")
            tarih = item.get("tarih", "")
            konu = item.get("konu", "")
            mukellef_sorusu = item.get("mukellef_sorusu", "")

            no_clean = re.sub(r'[^a-zA-Z0-9]', '', ozelge_no).lower()
            parts = [p for p in re.split(r'[^a-zA-Z0-9]', ozelge_no) if len(p) >= 2]
            tarih_clean = tarih.replace(".", "/")
            
            norm_konu = tr_normalize(konu)
            norm_soru = tr_normalize(mukellef_sorusu)
            combined_words = re.split(r'\s+', norm_konu + ' ' + norm_soru)
            keywords = [w for w in combined_words if len(w) > 4]

            for filename, ocr_clean in ocr_texts.items():
                score = 0
                if no_clean and no_clean in ocr_clean:
                    score += 1000
                for part in parts:
                    if part.lower() in ocr_clean:
                        score += len(part) * 10
                
                stem = filename.replace(".txt", "").lower()
                if parts and (stem in parts[-1].lower() or parts[-1].lower() in stem):
                    score += 500
                    
                if tarih and (tarih in ocr_clean or tarih_clean in ocr_clean):
                    score += 300
                    
                content_score = sum(1 for w in keywords if w in ocr_clean)
                score += content_score

                all_pairs.append((score, idx, filename))

        all_pairs.sort(key=lambda x: x[0], reverse=True)

        final_mapping = {}
        assigned_idx = set()
        used_files = set()

        for score, idx, filename in all_pairs:
            if idx not in assigned_idx and filename not in used_files:
                assigned_idx.add(idx)
                used_files.add(filename)
                final_mapping[idx] = filename.replace(".txt", ".pdf")

        items = []
        for idx, item in enumerate(yeni_data):
            filename = final_mapping.get(idx) or "10.pdf"
            pdf_path = source_dir / filename
            pages = 0
            file_size = 0
            if pdf_path.exists():
                file_size = pdf_path.stat().st_size
                if PdfReader is not None:
                    try:
                        reader = PdfReader(str(pdf_path))
                        pages = len(reader.pages)
                    except Exception:
                        pass

            code = display_code(filename)
            slug = slugify(f"{code}-{item.get('konu', '')}")

            clean_text_combined = f"{item.get('konu', '')} {item.get('mukellef_sorusu', '')} {item.get('maliyenin_cevabi', '')}"
            topics = infer_topics(clean_text_combined, filename)

            merged_topics = list(topics)
            for tag in item.get("etiketler", []):
                tag_title = tag.strip().capitalize()
                if tag_title not in merged_topics:
                    merged_topics.append(tag_title)

            search_text = f"{item.get('ozelge_no', '')} {item.get('tarih', '')} {item.get('konu', '')} {item.get('mukellef_sorusu', '')} {item.get('maliyenin_cevabi', '')} {item.get('sonuc', '')} {' '.join(item.get('etiketler', []))}"
            search_text = re.sub(r"\s+", " ", search_text).strip()

            built_item = {
                "filename": filename,
                "slug": slug,
                "code": code,
                "title": item.get("konu", "").strip(),
                "ozelge_no": item.get("ozelge_no"),
                "date": item.get("tarih"),
                "date_sort": extract_date_sort(item.get("tarih")),
                "summary": item.get("sonuc"),
                "konu_ozeti": compact_for_display(item.get("konu", ""), limit=220),
                "soru_ozeti": compact_for_display(item.get("mukellef_sorusu", ""), limit=360),
                "cevap_ozeti": compact_for_display(item.get("maliyenin_cevabi", ""), limit=430),
                "topics": merged_topics,
                "page_count": pages,
                "file_size": file_size,
                "extraction_status": "json_entegrasyon",
                "search_text": search_text[:12000],
                "indexed_at": datetime.now().strftime("%Y-%m-%d"),
            }
            items.append(built_item)
    else:
        items = []
        for pdf in sorted(source_dir.glob("*.pdf"), key=lambda p: p.name.lower()):
            ocr_text = read_ocr_text(root, pdf.stem)
            extracted_text, pages, pdf_status = extract_text_from_pdf(pdf, max_pages=2)
            text = ocr_text or extracted_text
            status = "ocr_metin_var" if ocr_text else pdf_status
            metadata = extract_metadata(text, pdf.name)
            code = display_code(pdf.name)
            slug = slugify(f"{code}-{metadata.get('subject') or ''}")
            subject = metadata.get("subject") or f"{code} Sayılı Özelge"
            summary = make_summary(text)
            structured = extract_structured_summary(text)
            item = {
                "filename": pdf.name,
                "slug": slug,
                "code": code,
                "title": subject,
                "ozelge_no": metadata.get("ozelge_no"),
                "date": metadata.get("date"),
                "date_sort": metadata.get("date_sort"),
                "summary": summary,
                "konu_ozeti": structured.get("konu_ozeti"),
                "soru_ozeti": structured.get("soru_ozeti"),
                "cevap_ozeti": structured.get("cevap_ozeti"),
                "topics": infer_topics(text, pdf.name),
                "page_count": pages,
                "file_size": pdf.stat().st_size,
                "extraction_status": status,
                "search_text": re.sub(r"\s+", " ", text)[:12000],
                "indexed_at": datetime.now().strftime("%Y-%m-%d"),
            }
            items.append(item)

    items = sorted(items, key=item_sort_key, reverse=True)
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "ozelgeler",
        "count": len(items),
        "items": items,
    }
    index_path = data_dir / "ozelgeler_index.json"
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload



def load_ozelge_index(root_path):
    root = Path(root_path)
    index_path = root / "static" / "data" / "ozelgeler_index.json"
    if not index_path.exists():
        return build_ozelge_index(root_path)
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return build_ozelge_index(root_path)
    data["items"] = sorted(data.get("items", []), key=item_sort_key, reverse=True)
    return data


def get_ozelge_by_slug(root_path, slug):
    data = load_ozelge_index(root_path)
    for item in data.get("items", []):
        if item.get("slug") == slug:
            return item
    return None
