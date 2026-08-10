import re
import unicodedata
from collections import defaultdict
from datetime import datetime


RISK_GUIDE_VERSION = "20.07.2026"


RISK_GUIDE = [
    {
        "category": "Nakit ve finansal hesaplar",
        "title": "Kasa bakiyesi ve fiili nakit",
        "accounts": "100",
        "level": "Ek veri gerekli",
        "sources": ["Mizan", "Kasa sayımı", "Tahsilat belgeleri"],
        "description": "Yüksek veya alacak bakiye veren kasa hesabı tek başına ihlal değildir; fiili kasa, hareketler ve ticari hacimle birlikte incelenir.",
        "action": "Kasa sayımını, günlük hareketleri, banka dışı tahsilatları ve ilişkili kişi kullanımını karşılaştırın.",
        "basis": "VUK kayıt, belge ve tevsik hükümleri; KVK md. 13 yönünden ilişkili kişi işlemleri",
    },
    {
        "category": "Nakit ve finansal hesaplar",
        "title": "Banka hesapları mutabakatı",
        "accounts": "102",
        "level": "Mutabakat",
        "sources": ["Mizan", "Banka ekstresi"],
        "description": "Dönem sonu banka bakiyesi ile mizan bakiyesi arasındaki açıklanamayan fark kayıt ve dönem kesimi riski oluşturur.",
        "action": "Tüm banka hesaplarını ekstre, kur değerlemesi ve yoldaki para kayıtlarıyla mutabık hale getirin.",
        "basis": "VUK kayıt nizamı ve değerleme hükümleri",
    },
    {
        "category": "Nakit ve finansal hesaplar",
        "title": "Çek ve senetlerin sınıflandırılması",
        "accounts": "101, 103, 121, 321",
        "level": "Sınıflandırma",
        "sources": ["Mizan", "Çek/senet listesi"],
        "description": "Ters bakiyeler ile vadeli çeklerin dönem sonundaki sınıflandırması mali tablo sunumunu ve reeskont değerlendirmesini etkileyebilir.",
        "action": "Vade, tahsil/ödeme durumu ve dönem sonu sınıflandırmasını belge bazında kontrol edin.",
        "basis": "VUK değerleme hükümleri ve Tekdüzen Hesap Planı",
    },
    {
        "category": "Ticari ve ilişkili kişi hesapları",
        "title": "Alıcılar ve satıcılarda ters bakiye",
        "accounts": "120, 320",
        "level": "Risk sinyali",
        "sources": ["Mizan", "Cari hesap ekstresi"],
        "description": "120 hesabın alacak veya 320 hesabın borç bakiye vermesi avans, iade, mahsup ya da yanlış hesap kullanımına işaret edebilir.",
        "action": "Ters bakiye veren alt hesapları 159 ve 340 hesapları ile fatura ve ödeme tarihleri üzerinden inceleyin.",
        "basis": "VUK kayıt nizamı ve dönemsellik ilkesi",
    },
    {
        "category": "Ticari ve ilişkili kişi hesapları",
        "title": "Şüpheli ticari alacak karşılığı",
        "accounts": "128, 129, 654",
        "level": "Belge kontrolü",
        "sources": ["Mizan", "Dava/icra dosyası", "Alacak belgesi"],
        "description": "Karşılığın vergi matrahında dikkate alınabilmesi alacağın niteliği ve kanuni takip şartlarıyla birlikte değerlendirilir.",
        "action": "Alacağın ticari niteliğini, vadesini, dava/icra safhasını ve karşılığın ayrıldığı dönemi belgeleyin.",
        "basis": "VUK md. 323",
    },
    {
        "category": "Ticari ve ilişkili kişi hesapları",
        "title": "Ortaklardan alacaklar",
        "accounts": "131, 231",
        "level": "Yüksek öncelik",
        "sources": ["Mizan", "Cari hesap hareketi", "Sözleşme"],
        "description": "İlişkili kişiye sağlanan finansmanın tutarı, süresi, emsal bedeli ve KDV uygulaması birlikte incelenir.",
        "action": "İşlem bazında adat, emsal faiz, faturalama ve transfer fiyatlandırması belgelendirmesini kontrol edin.",
        "basis": "KVK md. 13; KDV ve transfer fiyatlandırması düzenlemeleri",
    },
    {
        "category": "Ticari ve ilişkili kişi hesapları",
        "title": "Ortaklara borçlar ve örtülü sermaye",
        "accounts": "331, 431",
        "level": "Yüksek öncelik",
        "sources": ["Mizan", "Dönem başı özkaynak", "Borç sözleşmeleri"],
        "description": "Ortak veya ilişkili kişiden sağlanan borçların örtülü sermaye kapsamı yalnızca dönem sonu bakiye ile değil, dönem içi tutar, özkaynak ve kanuni istisnalarla belirlenir.",
        "action": "İlişkili kişi bazında borcun en yüksek seviyesini, dönem başı özkaynağı, faiz ve kur farklarını ayrı hesaplayın.",
        "basis": "KVK md. 12",
    },
    {
        "category": "Stok ve maliyet",
        "title": "Stok, fiili sayım ve negatif bakiye",
        "accounts": "150-158",
        "level": "Envanter kontrolü",
        "sources": ["Mizan", "Stok listesi", "Fiili sayım"],
        "description": "Mizan ile fiili sayım farkı, negatif stok ve olağandışı stok hareketi kayıt dışı alış/satış veya maliyetleme hatası sinyali olabilir.",
        "action": "Miktar ve değer bazında envanter mutabakatı yapın; fire, zayi, sayım farkı ve değer düşüklüğünü belgeleyin.",
        "basis": "VUK envanter ve değerleme hükümleri",
    },
    {
        "category": "Stok ve maliyet",
        "title": "Satışların maliyeti ve brüt kâr",
        "accounts": "620-623",
        "level": "Analitik kontrol",
        "sources": ["Gelir tablosu", "Mizan", "Stok hareketleri"],
        "description": "Brüt kâr marjındaki açıklanamayan değişim maliyet aktarımı, dönem kesimi veya stok değerleme farkına işaret edebilir.",
        "action": "Maliyet hesaplarını üretim ve stok hareketleriyle, marjı da önceki dönem ve faaliyet yapısıyla karşılaştırın.",
        "basis": "VUK maliyet bedeli ve dönemsellik hükümleri",
    },
    {
        "category": "Dönemsellik ve değerleme",
        "title": "Gelecek dönem gider ve gelirleri",
        "accounts": "180, 280, 380, 480",
        "level": "Dönemsellik",
        "sources": ["Mizan", "Sözleşme", "Fatura"],
        "description": "Birden fazla dönemi ilgilendiren gider ve gelirlerin doğru döneme ayrılması gerekir.",
        "action": "Sigorta, kira, bakım, lisans ve benzeri süreli sözleşmeleri başlangıç-bitiş tarihleriyle kontrol edin.",
        "basis": "VUK dönemsellik ve tahakkuk ilkeleri",
    },
    {
        "category": "Dönemsellik ve değerleme",
        "title": "Maddi duran varlıklar ve amortisman",
        "accounts": "250-258, 257",
        "level": "Belge kontrolü",
        "sources": ["Mizan", "Sabit kıymet listesi", "Fatura"],
        "description": "Aktifleştirme tarihi, faydalı ömür, maliyete eklenen unsurlar ve kıst amortisman uygulaması vergi matrahını etkiler.",
        "action": "Sabit kıymet listesi ile mizanı; aktife giriş, kullanım tarihi, oran ve birikmiş amortisman yönünden eşleştirin.",
        "basis": "VUK maliyet bedeli ve amortisman hükümleri",
    },
    {
        "category": "Dönemsellik ve değerleme",
        "title": "Yapılmakta olan yatırımlar",
        "accounts": "258",
        "level": "Aktifleştirme",
        "sources": ["Mizan", "Yatırım dosyası", "Kabul tutanağı"],
        "description": "Yatırım tamamlanmadan ayrılan amortisman veya doğrudan giderleştirilen maliyet unsurları matrah riski yaratabilir.",
        "action": "Kullanıma hazır olma tarihini ve maliyete dahil edilen harcamaları proje belgeleriyle doğrulayın.",
        "basis": "VUK maliyet bedeli ve amortisman hükümleri",
    },
    {
        "category": "Vergi, SGK ve karşılıklar",
        "title": "Vergi karşılığı ve peşin ödenen vergiler",
        "accounts": "360, 370, 371",
        "level": "Mutabakat",
        "sources": ["Mizan", "Beyanname", "Tahakkuk fişi"],
        "description": "Beyanname, tahakkuk ve mahsup kayıtlarının mizanla uyuşmaması dönem sonucu ve vergi borcunu etkileyebilir.",
        "action": "Geçici/yıllık vergi tahakkukları ile peşin ödenen vergi ve mahsup kayıtlarını dönem bazında karşılaştırın.",
        "basis": "KVK ve VUK tahakkuk/kayıt hükümleri",
    },
    {
        "category": "Vergi, SGK ve karşılıklar",
        "title": "SGK yükümlülükleri",
        "accounts": "361",
        "level": "Ödeme kontrolü",
        "sources": ["Mizan", "SGK tahakkuku", "Ödeme kayıtları"],
        "description": "Prim tahakkuku, ödeme zamanı ve gider indirimi şartları birlikte değerlendirilir; mizan bakiyesi tek başına sonuç üretmez.",
        "action": "Tahakkuk, ödeme ve ilgili dönemde giderleştirme kayıtlarını bordro ve banka kayıtlarıyla doğrulayın.",
        "basis": "5510 sayılı Kanun ve ilgili gelir/kurumlar vergisi hükümleri",
    },
    {
        "category": "Vergi, SGK ve karşılıklar",
        "title": "Kıdem tazminatı karşılığı",
        "accounts": "372, 472",
        "level": "KKEG kontrolü",
        "sources": ["Mizan", "Beyanname", "Bordro/ödeme"],
        "description": "Muhasebe standartları uyarınca ayrılan karşılık ile vergi matrahında indirilebilecek fiili ödeme aynı değildir.",
        "action": "Karşılık giderinin beyannamede KKEG olarak dikkate alınıp alınmadığını ve fiili ödemeleri ayrı izleyin.",
        "basis": "VUK karşılık hükümleri ve GVK/KVK safi kazanç esasları",
    },
    {
        "category": "Özkaynak ve finansman",
        "title": "Özkaynak enflasyon farkları",
        "accounts": "502 ve ilgili özkaynak fark hesapları",
        "level": "İşlem kontrolü",
        "sources": ["Mizan", "Genel kurul kararı", "Sermaye işlemleri"],
        "description": "Enflasyon düzeltme farklarının başka hesaba aktarılması, çekilmesi veya sermaye azaltımı özel vergileme sonuçları doğurabilir.",
        "action": "Fark hesaplarındaki tüm virmanları işlem tarihi, amaç ve karar belgeleriyle inceleyin.",
        "basis": "VUK mükerrer 298 ve geçici 33; ilgili tebliğler",
    },
    {
        "category": "Özkaynak ve finansman",
        "title": "Geçmiş yıl zararları",
        "accounts": "580, beyanname zarar satırları",
        "level": "Süre ve tutar kontrolü",
        "sources": ["Mizan", "Kurumlar vergisi beyannameleri"],
        "description": "Muhasebe zararları ile beyannamede taşınan mali zararlar aynı olmayabilir; yıl ve tutar bazında izlenmelidir.",
        "action": "Mahsup edilen zararı kaynak yıl, beyan edilen tutar ve kanuni süre yönünden beyanname zinciriyle doğrulayın.",
        "basis": "KVK md. 9",
    },
    {
        "category": "Özkaynak ve finansman",
        "title": "Finansman gider kısıtlaması",
        "accounts": "3, 4, 5 hesap sınıfları; 660, 661, 780",
        "level": "Hesaplama gerekli",
        "sources": ["Mizan", "Finansman gider dökümü", "Beyanname"],
        "description": "Yabancı kaynak-özkaynak karşılaştırması yalnızca başlangıçtır; kapsam dışı unsurlar, yatırım maliyetine eklenen tutarlar ve aynı kaynağa ait kur farkları ayrıca ayrıştırılır.",
        "action": "Geçici dönemler dahil, yabancı kaynak aşımını ve kapsama giren net finansman giderlerini mevzuattaki istisnalarla hesaplayın.",
        "basis": "KVK md. 11/1-i ve 1 Seri No.lu KVK Genel Tebliği 11.13",
    },
    {
        "category": "Hasılat ve giderler",
        "title": "Hasılat - KDV matrahı uyumu",
        "accounts": "600-602; KDV beyannamesi matrah alanları",
        "level": "Çapraz kontrol",
        "sources": ["Gelir tablosu", "Mizan", "KDV beyannamesi"],
        "description": "Hasılat ile KDV teslim/hizmet bedelleri arasındaki fark her zaman hata değildir; istisna, ihracat, demirbaş satışı, kur ve vade farkı gibi nedenlerle açıklanmalıdır.",
        "action": "Aylık KDV matrahlarını gelir hesaplarıyla eşleştirip farkları işlem türü bazında açıklayın.",
        "basis": "KDV Kanunu ve KDV Genel Uygulama Tebliği; VUK kayıt hükümleri",
    },
    {
        "category": "Hasılat ve giderler",
        "title": "Faaliyet ve yönetim giderleri",
        "accounts": "760, 770",
        "level": "Belge ve işle ilgisi",
        "sources": ["Mizan", "Fatura", "Sözleşme"],
        "description": "Giderin işletme faaliyetiyle ilgisi, belgesi, dönemi ve varsa özel sınırlamaları birlikte değerlendirilir.",
        "action": "Yüksek tutarlı ve olağandışı alt hesapları belge, onay ve işle ilgili olma yönünden örneklemle inceleyin.",
        "basis": "KVK md. 6, 8 ve 11; VUK belge hükümleri",
    },
    {
        "category": "Hasılat ve giderler",
        "title": "KKEG - beyanname eşleştirmesi",
        "accounts": "689 ve açıklamasında KKEG bulunan tüm gider hesapları",
        "level": "Beyanname mutabakatı",
        "sources": ["Mizan", "Kurumlar/geçici vergi beyannamesi"],
        "description": "KKEG yalnızca 689 hesabında izlenmeyebilir; tüm gider hesaplarındaki KKEG alt kırılımları beyannamedeki tutarla karşılaştırılmalıdır.",
        "action": "Hesap kodundan bağımsız KKEG etiketli alt hesapları toplayın ve beyanname satırıyla mutabık hale getirin.",
        "basis": "KVK md. 11 ve ilgili özel gider kısıtlamaları",
    },
    {
        "category": "KDV kontrolleri",
        "title": "Devreden KDV zinciri",
        "accounts": "190; KDV1 önceki/sonraki dönem devri",
        "level": "Matematiksel kontrol",
        "sources": ["Aylık KDV beyannameleri"],
        "description": "Bir ayın sonraki döneme devreden KDV tutarı, izleyen ayın önceki dönemden devreden KDV tutarıyla karşılaştırılır.",
        "action": "Fark bulunan ayları düzeltme beyannamesi, devir/terk işlemi ve mahsup kayıtlarıyla açıklayın.",
        "basis": "KDV Kanunu indirim mekanizması ve KDV Genel Uygulama Tebliği",
    },
    {
        "category": "KDV kontrolleri",
        "title": "KDV beyanname içi matematik",
        "accounts": "KDV1 matrah, hesaplanan, ilave, indirim ve sonuç alanları",
        "level": "Matematiksel kontrol",
        "sources": ["KDV beyannamesi"],
        "description": "Ayrıştırılan oran detayları, hesaplanan KDV ve toplam KDV alanları arasında matematiksel tutarlılık aranır.",
        "action": "Farkı önce PDF ayrıştırma kalitesiyle, ardından beyanname satırları ve düzeltme kayıtlarıyla kontrol edin.",
        "basis": "KDV beyannamesi hesap yapısı",
    },
    {
        "category": "KDV kontrolleri",
        "title": "KDV dönem sürekliliği",
        "accounts": "Aylık KDV1 dönemleri",
        "level": "Veri kapsamı",
        "sources": ["KDV beyannameleri"],
        "description": "Tamamlanmış yıllarda 12 aylık seri, cari yılda ise yüklenen son aya kadar kesintisiz dönem dizisi aranır.",
        "action": "Eksik veya mükerrer dönemi tamamlayın; düzeltme beyannamesinin güncel sürüm olduğundan emin olun.",
        "basis": "KDV beyan dönemleri",
    },
    {
        "category": "KDV kontrolleri",
        "title": "KDV matrahında olağandışı değişim",
        "accounts": "KDV1 toplam matrah",
        "level": "Risk sinyali",
        "sources": ["Aylık KDV beyannameleri"],
        "description": "Aylık matrahtaki keskin artış veya düşüş tek başına hata değildir; sezon, yatırım, iade, istisna veya faaliyet değişimiyle açıklanabilir.",
        "action": "Belirgin değişim gösteren ayları satış faturaları ve gelir hesaplarıyla karşılaştırın.",
        "basis": "Analitik vergi kontrolü",
    },
    {
        "category": "Beyanname ve veri bütünlüğü",
        "title": "Tekdüzen hesap kodu ve sınıf uyumu",
        "accounts": "1-9 hesap sınıfları",
        "level": "Hesap planı kontrolü",
        "sources": ["Mizan", "Tekdüzen Hesap Planı"],
        "description": "Ana hesap kodu, adı ve hesap sınıfı Tekdüzen Hesap Planıyla karşılaştırılır. Kuruma özel yardımcı ve alt hesaplar ayrıca değerlendirilir.",
        "action": "Ana hesapları hesap planında doğrulayın; alt hesapları kurumun hesap planı ve işlemin gerçek niteliğiyle birlikte inceleyin.",
        "basis": "1 Seri No.lu Muhasebe Sistemi Uygulama Genel Tebliği ve Tekdüzen Hesap Planı",
    },
    {
        "category": "Beyanname ve veri bütünlüğü",
        "title": "Mizan - bilanço - gelir tablosu eşitliği",
        "accounts": "1-6 hesap sınıfları",
        "level": "Matematiksel kontrol",
        "sources": ["Mizan", "Bilanço", "Gelir tablosu"],
        "description": "Aktif-pasif eşitliği, dönem sonucu ve temel mali tablo kalemleri kaynaklar arasında karşılaştırılır.",
        "action": "Farkları kapanış, yansıtma, vergi karşılığı ve dönem sonu mahsup kayıtları üzerinden çözün.",
        "basis": "VUK kayıt nizamı ve mali tablo ilkeleri",
    },
]


for _guide_item in RISK_GUIDE:
    _account_match = re.search(r"\b\d{3}\b", _guide_item.get("accounts", ""))
    _guide_item["tdhp_query"] = _account_match.group(0) if _account_match else ""


def _canon(value):
    text = str(value or "")
    text = "".join(
        char for char in unicodedata.normalize("NFD", text)
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", text).strip().upper().replace("İ", "I")


def _amount(value):
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if text in {"", "-", ".", ","}:
        return 0.0
    negative = (
        (text.startswith("(") and text.endswith(")"))
        or text.startswith("-")
        or text.endswith("-")
    )
    text = text.replace("(", "").replace(")", "").replace("-", "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    elif text.count(".") == 1 and len(text.rsplit(".", 1)[1]) == 3:
        text = text.replace(".", "")
    text = re.sub(r"[^0-9.]", "", text)
    try:
        amount = float(text or 0)
    except ValueError:
        return 0.0
    return -amount if negative else amount


def period_sort_key(value):
    text = _canon(value)
    year_match = re.search(r"\b(20\d{2})\b", text)
    year = int(year_match.group(1)) if year_match else 0
    temporary_match = re.search(r"([1-4])\s*\.\s*GECICI", text)
    if temporary_match:
        return year, int(temporary_match.group(1)) * 3
    month = parse_kdv_period(value)
    if month:
        return month[0], month[1]
    return year, 12


def parse_kdv_period(value):
    text = _canon(value)
    numeric = re.search(r"(?<!\d)(20\d{2})\s*[/.-]\s*(0?[1-9]|1[0-2])(?!\d)", text)
    if numeric:
        return int(numeric.group(1)), int(numeric.group(2))

    numeric = re.search(r"(?<!\d)(0?[1-9]|1[0-2])\s*[/.-]\s*(20\d{2})(?!\d)", text)
    if numeric:
        return int(numeric.group(2)), int(numeric.group(1))

    month_names = {
        "OCAK": 1, "SUBAT": 2, "MART": 3, "NISAN": 4,
        "MAYIS": 5, "HAZIRAN": 6, "TEMMUZ": 7, "AGUSTOS": 8,
        "EYLUL": 9, "EKIM": 10, "KASIM": 11, "ARALIK": 12,
    }
    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match:
        for name, number in month_names.items():
            if name in text:
                return int(year_match.group(1)), number
    return None


def _field_map(parsed):
    fields = {}
    detail_tax = 0.0
    detail_count = 0
    detail_matrah = 0.0
    detail_matrah_count = 0
    for row in parsed.get("veriler", []):
        label = _canon(row.get("alan"))
        if not label or label.startswith("§") or row.get("tip") == "header":
            continue
        value = _amount(row.get("deger"))
        fields[label] = value
        if "- MATRAH" in label and "INDIRIM" not in label:
            detail_matrah += value
            detail_matrah_count += 1
        if "- VERGI" in label and "INDIRIM" not in label:
            detail_tax += value
            detail_count += 1
    return fields, detail_tax, detail_count, detail_matrah, detail_matrah_count


def _first(fields, *labels):
    for label in labels:
        key = _canon(label)
        if key in fields:
            return fields[key]
    return 0.0


def _field_exists(fields, label):
    return _canon(label) in fields


def _period_label(year, month):
    return f"{month:02d}/{year}"


def _make_finding(category, title, status, classification, detail, **extra):
    finding = {
        "category": category,
        "title": title,
        "status": status,
        "classification": classification,
        "detail": detail,
    }
    finding.update(extra)
    return finding


def _extract_income_net_sales(parsed):
    for row in parsed.get("tablo", []):
        label = _canon(
            row.get("aciklama") or row.get("Açıklama") or row.get("hesap_adi")
            or row.get("Hesap Adı") or row.get("kalem") or row.get("title")
        )
        if "NET SATISLAR" not in label:
            continue
        for key in ("Cari Dönem", "cari_donem", "tutar", "Tutar", "deger", "Değer"):
            if key in row:
                return _amount(row.get(key))
    return 0.0


def _extract_income_gross_sales(parsed):
    for row in parsed.get("tablo", []):
        label = _canon(
            row.get("aciklama") or row.get("Açıklama") or row.get("hesap_adi")
            or row.get("Hesap Adı") or row.get("kalem") or row.get("title")
        )
        if "BRUT SATISLAR" not in label:
            continue
        for key in ("Cari Dönem", "cari_donem", "tutar", "Tutar", "deger", "Değer"):
            if key in row:
                return _amount(row.get(key))
    return None


def _format_amount_tr(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _temporary_months(period):
    text = _canon(period)
    year_match = re.search(r"\b(20\d{2})\b", text)
    if not year_match:
        return None
    year = int(year_match.group(1))
    temporary_match = re.search(r"([1-4])\s*\.\s*GECICI", text)
    if temporary_match:
        end_month = int(temporary_match.group(1)) * 3
        return year, list(range(1, end_month + 1))
    if re.fullmatch(r"\s*20\d{2}\s*", str(period or "")):
        return year, list(range(1, 13))
    return None


def build_data_coverage(records):
    labels = {
        "mizan": ("Mizan", "bi-table"),
        "bilanco": ("Bilanço", "bi-layout-text-window"),
        "gelir": ("Gelir tablosu", "bi-bar-chart-line"),
        "kdv": ("KDV beyannamesi", "bi-receipt"),
    }
    grouped = defaultdict(list)
    for record in records:
        grouped[record.get("tur")].append(str(record.get("donem") or ""))

    result = []
    for key, (label, icon) in labels.items():
        periods = sorted(set(grouped.get(key, [])), key=period_sort_key)
        result.append({
            "key": key,
            "label": label,
            "icon": icon,
            "count": len(periods),
            "periods": periods,
            "latest": periods[-1] if periods else None,
        })
    return result


def build_kdv_tax_checks(kdv_records, other_records=None, current_year=None):
    current_year = current_year or datetime.now().year
    other_records = other_records or []
    periods = []
    unparsed = []

    for record in kdv_records:
        parsed = record.get("parsed") or {}
        raw_period = parsed.get("donem") or record.get("donem")
        period = parse_kdv_period(raw_period)
        if not period:
            unparsed.append(str(raw_period or "Bilinmeyen dönem"))
            continue
        fields, detail_tax, detail_count, detail_matrah, detail_matrah_count = _field_map(parsed)
        year, month = period
        periods.append({
            "year": year,
            "month": month,
            "label": _period_label(year, month),
            "fields": fields,
            "matrah": _first(fields, "Toplam Matrah", "Matrah Toplamı"),
            "hesaplanan": _first(fields, "Hesaplanan KDV"),
            "ilave": _first(fields, "Daha Önce İndirim Konusu Yapılan KDV’nin İlavesi"),
            "toplam_kdv": _first(fields, "Toplam KDV"),
            "indirim": _first(fields, "İndirimler Toplamı"),
            "onceki_devreden": _first(fields, "Önceki Dönemden Devreden KDV"),
            "sonraki_devreden": _first(fields, "Sonraki Döneme Devreden KDV"),
            "odenecek": _first(fields, "Ödenmesi Gereken KDV"),
            "iade": _first(fields, "İade Edilmesi Gereken KDV"),
            "teslim_aylik": _first(fields, "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (Aylık)"),
            "teslim_kumulatif": _first(fields, "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (Kümülatif)"),
            "detail_tax": detail_tax,
            "detail_count": detail_count,
            "detail_matrah": detail_matrah,
            "detail_matrah_count": detail_matrah_count,
        })

    periods.sort(key=lambda item: (item["year"], item["month"]))
    by_key = {(item["year"], item["month"]): item for item in periods}
    by_year = defaultdict(list)
    for item in periods:
        by_year[item["year"]].append(item)

    findings = []
    overview = []

    if unparsed:
        findings.append(_make_finding(
            "KDV veri kapsamı",
            "Dönemi okunamayan KDV kaydı",
            "warning",
            "Veri kalitesi",
            f"{len(unparsed)} kaydın ay/yıl bilgisi ayrıştırılamadı: {', '.join(unparsed[:4])}.",
            source="KDV beyannamesi",
            action="Beyanname dönem bilgisini ve yüklenen PDF'nin okunabilirliğini kontrol edin.",
        ))

    for year, items in sorted(by_year.items()):
        months = sorted({item["month"] for item in items})
        expected_end = 12 if year < current_year else (max(months) if months else 0)
        expected = set(range(1, expected_end + 1))
        missing = sorted(expected - set(months))
        overview.append({
            "year": year,
            "loaded": len(months),
            "expected": expected_end,
            "missing": missing,
            "complete": not missing and len(months) == expected_end,
        })
        if missing:
            missing_text = ", ".join(f"{month:02d}" for month in missing)
            findings.append(_make_finding(
                "KDV veri kapsamı",
                f"{year} KDV dönem dizisinde boşluk var",
                "warning",
                "Veri kapsamı",
                f"{expected_end} aylık beklenen dizide {len(months)} dönem yüklü. Eksik aylar: {missing_text}.",
                period=str(year),
                source="KDV beyannamesi",
                action="Eksik ay beyannamesini veya varsa güncel düzeltme beyannamesini yükleyin.",
            ))
        else:
            scope = "12 aylık seri" if expected_end == 12 else f"01-{expected_end:02d} aralığı"
            findings.append(_make_finding(
                "KDV veri kapsamı",
                f"{year} KDV dönemleri kesintisiz",
                "success",
                "Veri kapsamı",
                f"{scope} için {len(months)} dönem yüklü ve dönem sıralamasında boşluk yok.",
                period=str(year),
                source="KDV beyannamesi",
            ))

        continuity_differences = []
        continuity_checks = 0
        for month in range(1, 12):
            previous = by_key.get((year, month))
            following = by_key.get((year, month + 1))
            if not previous or not following:
                continue
            if not _field_exists(following["fields"], "Önceki Dönemden Devreden KDV"):
                continue
            continuity_checks += 1
            difference = following["onceki_devreden"] - previous["sonraki_devreden"]
            if abs(difference) > 1:
                continuity_differences.append((following["label"], difference))

        if continuity_checks:
            if continuity_differences:
                findings.append(_make_finding(
                    "KDV devir zinciri",
                    f"{year} devreden KDV zincirinde fark",
                    "warning",
                    "Matematiksel uyumsuzluk",
                    f"{continuity_checks} ardışık ay geçişinin {len(continuity_differences)} tanesinde fark bulundu.",
                    period=str(year),
                    source="KDV beyannamesi",
                    breakdown=[
                        {
                            "period": label,
                            "label": (
                                "Önceki dönemden devreden tutar, önceki ayın sonraki devrinden fazla"
                                if difference > 0 else
                                "Önceki dönemden devreden tutar, önceki ayın sonraki devrinden eksik"
                            ),
                            "amount": abs(difference),
                        }
                        for label, difference in continuity_differences
                    ],
                    action="İlgili ayların son ve ilk devir tutarlarını düzeltme beyannameleriyle birlikte kontrol edin.",
                    basis="KDV1 önceki dönemden devreden / sonraki döneme devreden alanları",
                ))
            else:
                findings.append(_make_finding(
                    "KDV devir zinciri",
                    f"{year} devreden KDV zinciri uyumlu",
                    "success",
                    "Matematiksel kontrol",
                    f"Karşılaştırılabilen {continuity_checks} ardışık ay geçişinde 1 TL üzerinde fark bulunmadı.",
                    period=str(year),
                    source="KDV beyannamesi",
                ))

    math_issues = []
    detail_coverage_issues = []
    for item in periods:
        expected_total = item["hesaplanan"] + item["ilave"]
        if item["toplam_kdv"] or expected_total:
            difference = item["toplam_kdv"] - expected_total
            if abs(difference) > 1:
                math_issues.append({
                    "period": item["label"],
                    "label": (
                        "Toplam KDV, hesaplanan KDV ve ilave KDV toplamından fazla"
                        if difference > 0 else
                        "Toplam KDV, hesaplanan KDV ve ilave KDV toplamından eksik"
                    ),
                    "amount": abs(difference),
                })
        if item["detail_count"] and item["hesaplanan"]:
            matrah_difference = item["matrah"] - item["detail_matrah"]
            if item["detail_matrah_count"] and abs(matrah_difference) > 1:
                detail_coverage_issues.append({
                    "period": item["label"],
                    "label": "PDF oran detaylarında eksik okunan matrah",
                    "amount": abs(matrah_difference),
                })
                continue
            detail_difference = item["hesaplanan"] - item["detail_tax"]
            if abs(detail_difference) > 1:
                math_issues.append({
                    "period": item["label"],
                    "label": (
                        "Hesaplanan KDV, oran detayları toplamından fazla"
                        if detail_difference > 0 else
                        "Hesaplanan KDV, oran detayları toplamından eksik"
                    ),
                    "amount": abs(detail_difference),
                })

    if math_issues:
        findings.append(_make_finding(
            "KDV beyanname içi kontrol",
            "KDV hesap alanlarında matematik farkı",
            "warning",
            "Matematiksel uyumsuzluk",
            f"{len(math_issues)} dönemsel matematik farkı bulundu. Ayrıntılar aşağıda dönem bazında gösterilmiştir.",
            source="KDV beyannamesi",
            breakdown=math_issues,
            action="Önce PDF ayrıştırılan satırları, ardından beyanname hesap alanlarını kontrol edin.",
            basis="Hesaplanan KDV + ilave KDV = toplam KDV ve oran detayı toplamları",
        ))
    elif periods:
        findings.append(_make_finding(
            "KDV beyanname içi kontrol",
            "KDV temel hesap alanları uyumlu",
            "success",
            "Matematiksel kontrol",
            f"{len(periods)} dönemin ayrıştırılabilen temel hesap alanlarında 1 TL üzerinde fark bulunmadı.",
            source="KDV beyannamesi",
        ))

    if detail_coverage_issues:
        findings.append(_make_finding(
            "KDV PDF ayrıştırma kontrolü",
            "Bazı KDV oran detayları eksik okunmuş",
            "info",
            "Ayrıştırma bilgisi",
            (
                f"{len(detail_coverage_issues)} dönemde toplam matrah ile PDF'den okunan "
                "oran detayları aynı kapsamda değil. Bu durum vergi hatası olarak değerlendirilmedi."
            ),
            source="KDV beyannamesi",
            breakdown=detail_coverage_issues,
            action="İlgili dönem PDF'lerini yeniden yükleyerek Diğer İşlemler satırlarının ayrıştırıldığını kontrol edin.",
        ))

    movements = []
    for previous, current in zip(periods, periods[1:]):
        if (previous["year"], previous["month"] + 1) != (current["year"], current["month"]):
            continue
        if previous["matrah"] <= 0 or current["matrah"] <= 0:
            continue
        ratio = current["matrah"] / previous["matrah"]
        if ratio >= 3 or ratio <= (1 / 3):
            direction = "arttı" if ratio >= 3 else "azaldı"
            movements.append(f"{current['label']} matrahı önceki aya göre {ratio:.1f} kat {direction}")
    if movements:
        findings.append(_make_finding(
            "KDV analitik kontrol",
            "Aylık KDV matrahında belirgin değişim",
            "info",
            "Risk sinyali",
            "; ".join(movements[:5]),
            source="KDV beyannamesi",
            action="Bu değişim tek başına hata değildir; satışlar, sezon, iade ve faaliyet değişimiyle açıklayın.",
        ))

    for record in other_records:
        report_type = record.get("tur")
        parsed = record.get("parsed") or {}
        period_scope = _temporary_months(record.get("donem"))
        if not period_scope:
            continue
        year, months = period_scope

        if report_type == "gelir":
            ending_item = by_key.get((year, months[-1]))
            cumulative_label = "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (Kümülatif)"
            gross_sales = _extract_income_gross_sales(parsed)
            if (
                ending_item
                and _field_exists(ending_item["fields"], cumulative_label)
                and gross_sales is not None
            ):
                cumulative_sales = ending_item["teslim_kumulatif"]
                difference = cumulative_sales - gross_sales
                tolerance = 1.0
                if abs(difference) <= tolerance:
                    status = "success"
                    classification = "Çapraz kontrol"
                    title = "KDV kümülatif bedeli - brüt satışlar uyumlu"
                else:
                    status = "info"
                    classification = "Açıklama gerekli"
                    title = "KDV kümülatif bedeli - brüt satışlar farkı"

                period_text = str(record.get("donem") or "")
                detail = (
                    f"{period_text} için {ending_item['label']} KDV beyannamesindeki kümülatif teslim ve "
                    f"hizmet bedeli {_format_amount_tr(cumulative_sales)} TL, gelir tablosundaki brüt "
                    f"satışlar {_format_amount_tr(gross_sales)} TL."
                )
                if status != "success":
                    direction = "fazla" if difference > 0 else "eksik"
                    detail += (
                        f" KDV kümülatif bedeli brüt satışlardan {_format_amount_tr(abs(difference))} TL "
                        f"{direction}. Fark, işlem kapsamı veya dönem kayıtları nedeniyle vergi hatası olmayabilir."
                    )
                else:
                    detail += f" Mutlak fark {_format_amount_tr(abs(difference))} TL."

                findings.append(_make_finding(
                    "KDV - gelir tablosu çapraz kontrol",
                    title,
                    status,
                    classification,
                    detail,
                    period=period_text,
                    source="KDV beyannamesi + Gelir tablosu",
                    amount=abs(difference),
                    amount_label="Mutlak fark",
                    action=(
                        "Farkı; satış iadeleri, KDV dışı veya istisna işlemler, sabit kıymet satışları, "
                        "kur/vade farkları ve dönem kayıtları üzerinden açıklayın."
                        if status != "success" else None
                    ),
                    basis="KDV1 kümülatif teslim ve hizmet bedeli ile gelir tablosu brüt satışlar",
                ))

        monthly_items = [by_key.get((year, month)) for month in months]
        if any(item is None for item in monthly_items):
            continue
        kdv_sales = sum((item["teslim_aylik"] or item["matrah"]) for item in monthly_items)
        if report_type == "mizan":
            report_sales = _amount((parsed.get("summary") or {}).get("net_sales"))
            report_label = "Mizan"
        elif report_type == "gelir":
            report_sales = _extract_income_net_sales(parsed)
            report_label = "Gelir tablosu"
        else:
            continue
        if not report_sales or not kdv_sales:
            continue
        difference = kdv_sales - report_sales
        tolerance = max(1.0, max(abs(report_sales), abs(kdv_sales)) * 0.005)
        if abs(difference) <= tolerance:
            status = "success"
            classification = "Çapraz kontrol"
            title = f"KDV matrahı - {report_label.lower()} uyumlu"
            detail = f"{record.get('donem')} döneminde karşılaştırılan satış tutarlarında fark {difference:,.2f} TL."
        else:
            status = "info"
            classification = "Açıklama gerekli"
            title = f"KDV matrahı - {report_label.lower()} farkı"
            detail = (
                f"{record.get('donem')} döneminde KDV teslim/matrah toplamı ile {report_label.lower()} "
                f"satış tutarı arasında {difference:,.2f} TL fark var. Fark, işlem kapsamı nedeniyle vergi hatası olmayabilir."
            )
        findings.append(_make_finding(
            "KDV çapraz kontrol",
            title,
            status,
            classification,
            detail,
            period=record.get("donem"),
            source=f"KDV beyannamesi + {report_label}",
            action="İhracat, istisna, demirbaş satışı, kur/vade farkı ve KDV dışı işlemler üzerinden mutabakat hazırlayın." if status != "success" else None,
            basis="KDV teslim ve hizmet bedelleri ile muhasebe satış hesapları",
        ))

    return findings, overview, periods
