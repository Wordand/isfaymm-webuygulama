import os
import pandas as pd
import io
import pdfkit
import pdfplumber
import re
from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, make_response, current_app, send_file, jsonify
from werkzeug.utils import secure_filename
import json # JSON modülünü import ediyoruz

from services.db import get_conn
from config import ILLER, BOLGE_MAP, BOLGE_MAP_9903, TESVIK_KATKILAR, TESVIK_VERGILER, TESVIK_KATKILAR_9903
from auth import login_required

bp = Blueprint("indirimlikurumlar", __name__, url_prefix="/indirimlikurumlar")

explanations = [
    "ORANLAR (%) (FAALİYET TÜRLERİ İTİBARİYLE)",                 #0
    "A-BRÜT SATIŞLAR (60)",                                      #1
    "Yurtiçi Satışlar (600)",                                    #2
    "Yurtdışı Satışlar (601)",                                   #3
    "Diğer Gelirler (602)",                                      #4
    "B-SATIŞ İNDİRİMLERİ (-) (61)",                              #5
    "Satıştan İadeler (-) (610)",                                #6
    "Satış İskontoları (-) (611)",                               #7
    "Diğer İndirimler (-) (612)",                                #8
    "NET SATIŞLAR",                                              #9
    "C-SATIŞLARIN MALİYETİ (-) (62)",                            #10
    "Satılan Mamuller Maliyeti (620)",                           #11
    "Satılan Ticari Mal Maliyeti (621)",                         #12
    "Satılan Hizmet Maliyeti (622)",                             #13
    "Diğer Satışların Maliyeti (623)",                           #14
    "BRÜT SATIŞ KARI / ZARARI",                                  #15
    "D-FAALİYET GİDERLERİ (-) (63)",                             #16
    "Araştırma ve Geliştirme Giderleri (-) (630)",               #17
    "Pazarlama, Satış ve Dağıtım Giderleri (-) (631)",           #18
    "Genel Yönetim Giderleri (-) (632)",                         #19
    "MÜŞTEREK GENEL GİDERLER",                                   #20
    "AMORTİSMAN GİDERLERİ",                                      #21
    "FAALİYET KARI / ZARARI",                                    #22
    "E-DİĞER FAALİYETLERDEN GELİR VE KARLAR (64)",               #23
    "İştiraklerden Temettü Gelirleri (640)",                     #24
    "Bağlı Ortaklıklardan Temettü Gelirleri (641)",              #25
    "Faiz Gelirleri (642)",                                      #26
    "Komisyon Gelirleri (643)",                                  #27
    "Konusu Olmayan Karşılıklar (644)",                           #28
    "Menkul Kıymet Satış Karları (645)",                          #29
    "Kambiyo Karları (646)",                                      #30
    "Reeskont Faiz Gelirleri (647)",                              #31
    "Enflasyon Düzeltmesi Karları (648)",                         #32
    "Faaliyetle İlgili Diğer Gelir ve Karlar (649)",              #33
    "F-DİĞER FAALİYETLERDEN GİDERLER VE ZARARLAR (65)",           #34
    "Komisyon Giderleri (653)",                                   #35
    "Karşılık Giderleri (654)",                                   #36
    "Menkul Kıymet Satış Zararları (655)",                        #37
    "Kambiyo Zararları (656)",                                    #38
    "Reeskont Faiz Giderleri (657)",                              #39
    "Enflasyon Düzeltmesi Zararları (658)",                       #40
    "Diğer Olağan Gider ve Zararlar (659)",                       #41
    "G-FİNANSMAN GİDERLERİ (-) (66)",                             #42
    "Kısa Vadeli Borçlanma Giderleri (-) (660)",                  #43
    "Uzun Vadeli Borçlanma Giderleri (-) (661)",                  #44
    "OLAĞAN KAR VEYA ZARAR",                                      #45
    "H-OLAĞANDIŞI GELİR VE KÂRLAR (67)",                          #46
    "Önceki Dönem Gelir ve Karları (671)",                        #47
    "Diğer Olağan Dışı Gelir ve Karlar (679)",                    #48
    "I-OLAĞANDIŞI GİDER VE ZARARLAR (-) (68)",                    #49
    "Çalışmayan Kısım Gider ve Zararları (-) (680)",              #50
    "Önceki Dönem Gider ve Zararları (-) (681)",                  #51
    "Diğer Olağan Dışı Gider ve Zararlar (-) (689)",              #52
    "DÖNEM KÂRİ VEYA ZARARI (TİCARİ BİLANÇO KARI ZARARI)",        #53
    "İHRACAT, İMALAT VE DİĞER FAALİYETLERİN TOPLAM PAYLARI (%)"   #54
]


import re
import pdfplumber

def parse_ikv_from_pdf(path):
    tablolar = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            

            if "Teşvik Belgesi Numarası" in text:
                veriler = []

                def ekle(alan, regex):
                    match = re.search(regex, text)
                    if match:
                        deger = match.group(1).strip()
                        veriler.append({'alan': alan, 'deger': deger})

                ekle("Teşvik Belgesi Numarası", r"Teşvik Belgesi Numarası\s*:?\s*(\d+)")
                ekle("Teşvik Belgesinin Hangi Karara Göre Düzenlendiği", r"Karara Göre Düzenlendiği\s*:?\s*([^\n]+)")                
                ekle("Yatırıma Başlama Tarihi", r"Başlama Tarihi\s*:?\s*([^\n]+)")
                ekle("Yatırımın Türü 1", r"Yatırımın Türü 1\s*:?\s*([^\n]+)")
                ekle("Yatırımın Türü 2", r"Yatırımın Türü 2\s*:?\s*([^\n]+)")

                ekle("Toplam Yatırım Tutarı (İndirimli KV Kapsamında Olmayan Harcamalar Hariç)", r"Toplam Yatırım Tutarı.*?(?<!Katkı).*?:?\s*([0-9\.,]+)")
                ekle("Yatırıma Katkı Oranı", r"Yatırıma Katkı Oranı\s*:?\s*([0-9]+)")
                ekle("Vergi İndirim Oranı", r"Vergi İndirim Oranı\s*:?\s*([0-9]+)")
                ekle("Yatırımın Yapıldığı Bölge", r"Yatırımın Yapıldığı Bölge\s*:?\s*([^\n]+)")
                ekle("İndirimli KV Oranı", r"İndirimli KV Oranı\s*:?\s*([0-9]+)")

                ekle("Toplam Yatırıma Katkı Tutarı", r"Toplam Yatırıma Katkı Tutarı[^\d]*([0-9\.,]+)")
                ekle("Cari Yılda Fiilen Gerçekleştirilen Yatırım Harcaması Tutarı", r"Cari Yılda Fiilen Gerçekleştirilen(?: Yatırım Harcaması)?(?: Tutarı)?[^\d]*([0-9\.,]+)")
                ekle("Fiilen Gerçekleştirilen Yatırım Harcaması Tutarı \(Başlangıçtan İtibaren\)", r"Gerçekleştirilen Yatırım Harcaması.*Başlangıçtan.*?:?\s*([0-9\.,]+)")
                ekle("Fiili Yatırım Harcaması Nedeniyle Hak Kazanılan Yatırıma Katkı Tutarı", r"Hak Kazanılan Yatırıma Katkı Tutarı\s*:?\s*([0-9\.,]+)")
                ekle("Endekslenmiş Tutarlar Nedeniyle Hak Kazanılan Yatırıma Katkı Tutarı", r"Endekslenmiş.*Hak Kazanılan.*Katkı Tutarı\s*:?\s*([0-9\.,]+)")

                ekle("Önceki Dönemlerde Yararlanılan Yatırıma Katkı (Yatırımdan Elde Edilen Kazanç Dolayısıyla)", r"Önceki.*Yatırımdan Elde Edilen Kazanç Dolayısıyla\)\s*:?\s*([0-9\.,]+)")
                ekle("Önceki Dönemlerde Yararlanılan Yatırıma Katkı (Diğer Faaliyetlerden Elde Edilen Kazanç Dolayısıyla)", r"Önceki.*Diğer Faaliyetlerden Elde Edilen Kazanç Dolayısıyla\)\s*:?\s*([0-9\.,]+)")
                ekle("Önceki Dönemlerde Yararlanılan Toplam Yatırıma Katkı Tutarı", r"Önceki.*Toplam Yatırıma Katkı Tutarı\s*:?\s*([0-9\.,]+)")
                ekle("Cari Dönemde Yararlanılan Yatırıma Katkı (Yatırımdan Elde Edilen Kazanç Dolayısıyla)", r"Cari.*Yatırımdan Elde Edilen Kazanç Dolayısıyla\)\s*:?\s*([0-9\.,]+)")
                ekle("Cari Dönemde Yararlanılan Yatırıma Katkı (Diğer Faaliyetlerden Elde Edilen Gelirler Dolayısıyla)", r"Cari.*Diğer Faaliyetlerden Elde Edilen Gelirler Dolayısıyla\)\s*:?\s*([0-9\.,]+)")
                ekle("Cari Dönem Dahil Olmak Üzere Yararlanılan Toplam Yatırıma Katkı Tutarı", r"Cari Dönem Dahil.*Toplam Yatırıma Katkı Tutarı\s*:?\s*([0-9\.,]+)")
                ekle("Cari Dönemde Yararlanılan Toplam Yatırıma Katkı Tutarı", r"Cari.*Toplam Yatırıma Katkı Tutarı\s*:?\s*([0-9\.,]+)")

                tablolar.append({'veriler': veriler})
                
                bulunan_alanlar = [v['alan'] for v in veriler]
                print("Tespit edilen alanlar:", bulunan_alanlar)

    return {"tablolar": tablolar}



def format_date_for_input(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return date_str  # zaten doğruysa olduğu gibi döndür

# JSON serileştirme sorunlarını gidermek için yardımcı fonksiyon
def _clean_json_value(val):
    if pd.isna(val):
        return None  # NaN'ı JSON null'a çevir
    if isinstance(val, (int, float, bool, type(None))):
        return val  # Zaten serileştirilebilir
    return str(val) # Diğer tüm tipleri string'e çevir (tuple'lar dahil)



def get_user_profit_df(user_id: int) -> pd.DataFrame:
    """
    Belirtilen kullanıcıya ait kâr tablosu verilerini veritabanından çeker
    ve bir Pandas DataFrame'e dönüştürür.
    Eğer veri yoksa, varsayılan bir DataFrame oluşturur ve veritabanına kaydeder.
    """
    df = pd.DataFrame({
        'Açıklama': explanations,
        'B': 0.0, 'C': 0.0, 'D': 0.0, 'E': 0.0
    })

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT aciklama_index, column_b, column_c, column_d, column_e "
            "FROM profit_data WHERE user_id = ?",
            (user_id,)
        )
        db_data = c.fetchall()

        if db_data:
            for row_idx, val_b, val_c, val_d, val_e in db_data:
                if 0 <= row_idx < len(explanations): 
                    df.at[row_idx, 'B'] = val_b
                    df.at[row_idx, 'C'] = val_c
                    df.at[row_idx, 'D'] = val_d
                    df.at[row_idx, 'E'] = val_e
        else:
            for i, _ in enumerate(explanations):
                c.execute(
                    "INSERT INTO profit_data (user_id, aciklama_index, column_b, column_c, column_d, column_e) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, i, 0.0, 0.0, 0.0, 0.0)
                )
            conn.commit()

    return df

def save_user_profit_df(user_id: int, dataframe: pd.DataFrame):
    """
    Kullanıcının kâr tablosu verilerini veritabanına kaydeder/günceller.
    """
    with get_conn() as conn:
        c = conn.cursor()
        for i, row in dataframe.iterrows():
            c.execute(
                "INSERT OR REPLACE INTO profit_data (user_id, aciklama_index, column_b, column_c, column_d, column_e) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, i, row['B'], row['C'], row['D'], row['E'])
            )
        conn.commit()

def format_df_for_html(dataframe: pd.DataFrame) -> list[dict]:
    formatted_rows = []
    for index, row in dataframe.iterrows():
        formatted_row = {'Açıklama': row['Açıklama']}
        for col in ['B', 'C', 'D', 'E']:
            value = row[col]

            if pd.isna(value) or value is None:
                numeric_value = 0.0
            else:
                try:
                    numeric_value = float(value)
                except (ValueError, TypeError):
                    numeric_value = 0.0

            if index == 0 or index == 54:
                if col == 'B' and index != 54:
                    formatted_col_value = "100%"
                else:
                    formatted_col_value = f"{numeric_value:.2f}%".replace('.', ',')
            else:
                if numeric_value == 0.0:
                    formatted_col_value = ""
                else:
                    formatted_col_value = f"{numeric_value:.2f}".replace('.', ',')
            
            formatted_row[col] = formatted_col_value
        formatted_rows.append(formatted_row)
    return formatted_rows

@bp.route('/ayrintili-kazanc', methods=['GET','POST'])
@login_required 
def ayrintili_kazanc():
    user_id = session["user"]

    # --- BU DAHA KAPSAMLI TRY-EXCEPT BLOĞUNU EKLEYİN ---
    try:
        # POST geldiğinde hem import/export hem de kaydetme işlemi
        if request.method == 'POST':
            # Bu satır, profit_data tablosu veya user_id ile ilgili bir sorun varsa hata verebilir
            current_df_profit = get_user_profit_df(user_id) 

            if 'import' in request.form:
                return jsonify({"status": "warning", "title": "İçe Aktarılamadı!", "message": "İçe aktar henüz uygulanmadı."})      
            elif 'export' in request.form:
                buf = io.StringIO()
                current_df_profit.to_csv(buf, index=False, encoding='utf-8-sig')
                buf.seek(0)
                return send_file(
                    io.BytesIO(buf.getvalue().encode('utf-8-sig')),
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name='kazanc_hesap_ayrintili.csv'
                )
            else: # Bu, kaydetme bölümü (mevcut try-except bloğunuz burada)
                for i in range(len(explanations)):
                    for col in ['B','C','D','E']:
                        raw = (request.form.get(f"{col}_{i}") or '').replace('.', '').replace(',', '.')
                        try:
                            val = raw.replace('%','')
                            current_df_profit.at[i, col] = float(val) if val != '' else 0.0
                        except ValueError:
                            current_df_profit.at[i, col] = 0.0

                try: # Mevcut içteki try-except bloğu
                    save_user_profit_df(user_id, current_df_profit)
                    return jsonify({"status": "success", "title": "Kaydedildi!", "message": "Ayrıntılı kazanç tablosu başarıyla kaydedildi."})
                except Exception as e:
                    print(f"Ayrıntılı kazanç tablosu kaydedilirken hata oluştu (iç blok): {e}") 
                    return jsonify({"status": "error", "title": "Kaydetme Hatası!", "message": f"Veritabanına kaydedilirken bir sorun oluştu: {str(e)}"})
            
        # GET geldiğinde veya POST sonrası redirect sonrası:
        # Bu kısım da hatalara karşı korumalı olmalı, özellikle current_df_profit çekilirken
        current_df_profit = get_user_profit_df(user_id) 
        formatted_data_for_html = format_df_for_html(current_df_profit)

        # index() içindeki JSON hazırlama kodu birebir alındı - bu render_template bağlamı içindir
        safe_bolge_map = {}
        for k, v in BOLGE_MAP.items():
            key = str(k)
            safe_bolge_map[key] = v if v is not None and not (isinstance(v, float) and pd.isna(v)) else None

        safe_katkilar_json = {}
        for k, v in TESVIK_KATKILAR.items():
            key = f"{k[0]}|{k[1]}" if isinstance(k, tuple) and len(k)==2 else str(k)
            safe_katkilar_json[key] = v if v is not None and not (isinstance(v, float) and pd.isna(v)) else None

        safe_vergiler_json = {}
        for k, v in TESVIK_VERGILER.items():
            key = f"{k[0]}|{k[1]}" if isinstance(k, tuple) and len(k)==2 else str(k)
            safe_vergiler_json[key] = v if v is not None and not (isinstance(v, float) and pd.isna(v)) else None

        initial_ayrintili_ratios = {
            "C": f"{current_df_profit.at[54,'C']:.2f}".replace('.',',') + "%" if not pd.isna(current_df_profit.at[54,'C']) else "0,00%",
            "D": f"{current_df_profit.at[54,'D']:.2f}".replace('.',',') + "%" if not pd.isna(current_df_profit.at[54,'D']) else "0,00%",
            "E": f"{current_df_profit.at[54,'E']:.2f}".replace('.',',') + "%" if not pd.isna(current_df_profit.at[54,'E']) else "0,00%",
        }

        return render_template(
            'indirimlikurumlar.html',
            sekme='ayrintili',
            rows=formatted_data_for_html,
            iller=ILLER,
            bolge_json=safe_bolge_map,
            katkilar_json=safe_katkilar_json,
            vergiler_json=safe_vergiler_json,
            initial_ayrintili_ratios=initial_ayrintili_ratios,
            belgeler=[]
        )

    except Exception as e:
        # Ana POST veya GET bloğunda beklenmeyen bir hata oluştuğunda
        print(f"ayrintili_kazanc fonksiyonunda genel hata oluştu: {e}")
        # Frontend'e JSON hata yanıtı dön
        return jsonify({"status": "error", "title": "Sunucu Hatası!", "message": f"Beklenmeyen bir sunucu hatası oluştu: {str(e)}"})


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    sekme = request.args.get("sekme", "form")
    user_id = session["user"]
    
    # URL'den gelen 'view' parametresini her zaman kontrol edelim.
    # Bu, hem 'tesvik' sekmesinde detay görmek hem de 'form' sekmesinde belge düzenlemek için kullanılır.
    view_id = request.args.get("view", type=int) 

    # Kullanıcının tüm teşvik belgelerini çek
    docs = get_all_tesvik_docs(user_id) 

    # 'tesvik' sekmesinde belirli bir belgenin detayını göstermek için kullanılır
    edit_doc = None
    if sekme == "tesvik" and view_id:
        edit_doc = next((d for d in docs if d["id"] == view_id), None)

    # Kullanıcının ayrıntılı kâr tablosu verilerini çek
    user_df = get_user_profit_df(user_id)

    # 'form' sekmesi için güncel belgeyi belirleme mantığı
    current_belge = None
    if sekme == "form":
        # Eğer URL'de 'view_id' parametresi varsa (yani bir belgeyi güncellemek için gelindiyse)
        if view_id: 
            current_belge = next((d for d in docs if d["id"] == view_id), None)
            if current_belge:
                # Belge bulunduysa, ID'sini session'a kaydet (güncelleme durumunda bu ID kullanılacak)
                session["current_tesvik_id"] = current_belge["id"]
                print(f"→ Güncelleme isteği: current_belge ID set edildi: {session['current_tesvik_id']}")
            else:
                # view_id ile belge bulunamadıysa (örneğin ID yanlışsa), session'ı temizle
                session["current_tesvik_id"] = None 
                print("→ Güncelleme isteği için belge bulunamadı. session ID temizlendi.")
        elif docs: 
            # Eğer 'view_id' yoksa ve kullanıcının belgeleri varsa, en son belgeyi formda göster
            # (Bu, kullanıcının en son çalıştığı belgeye devam etmesini sağlar)
            current_belge = docs[0] # get_all_tesvik_docs ORDER BY id DESC yaptığı için en yenisi ilk sırada
            session["current_tesvik_id"] = current_belge["id"]
            print(f"→ En son belge current_belge ID set edildi: {session['current_tesvik_id']}")
        else:
            # Eğer hiç belge yoksa (yeni bir kullanıcı veya tüm belgeler silinmişse), formu boş başlat
            session["current_tesvik_id"] = None
            print("→ Hiç belge yok. current_belge ve session ID temizlendi.")

  

    safe_bolge_map = {str(k): (v if v==v else None) for k,v in (BOLGE_MAP or {}).items()}
    safe_katkilar_json = {}
    for k, v in (TESVIK_KATKILAR or {}).items():
        key = f"{k[0]}|{k[1]}" if isinstance(k, tuple) else str(k)
        safe_katkilar_json[key] = v if v==v else None
    safe_vergiler_json = {}
    for k, v in (TESVIK_VERGILER or {}).items():
        key = f"{k[0]}|{k[1]}" if isinstance(k, tuple) else str(k)
        safe_vergiler_json[key] = v if v==v else None

    initial_ayrintili_ratios = {
        c: f"{user_df.at[54, c]:.2f}".replace(".", ",") + "%" if not pd.isna(user_df.at[54, c]) else "0,00%"
        for c in ["C","D","E"]
    }
    saved = request.args.get("saved") == "1"

    # Context’u hazırla
    ctx = {
        "sekme": sekme,
        "iller": ILLER or [],
        "bolge_json": safe_bolge_map,
        "katkilar_json": safe_katkilar_json,
        "vergiler_json": safe_vergiler_json,
        "initial_ayrintili_ratios": initial_ayrintili_ratios,
        "docs": docs,
        "edit_doc": edit_doc,
        "current_belge": current_belge,
        "BOLGE_MAP_9903": BOLGE_MAP_9903,
        "TESVIK_KATKILAR_9903": TESVIK_KATKILAR_9903,
        "pdf_saved": saved
    }
    
    if sekme == "ayrintili":
        ctx["rows"] = format_df_for_html(user_df)

    return render_template("indirimlikurumlar.html", **ctx)



@bp.route("/form", methods=["POST"])
@login_required
def form_kaydet():
    print(">>> form_kaydet GİRİLDİ")
    print("POST verileri:", dict(request.form))
    user_id = session["user"]
    print(">>> form_kaydet called. form data:", dict(request.form))

    # TEŞVİK ID BELİRLEME MANTIĞI:
    form_tesvik_id_raw = request.form.get("tesvik_id")
    if form_tesvik_id_raw:
        try:
            tesvik_id = int(form_tesvik_id_raw)
        except ValueError:
            tesvik_id = None # Hatalı bir ID gelirse yeni kayıt olarak değerlendir
    else:
        tesvik_id = None # Formdan boş geldi: yeni kayıt

    print("→ belirlenen tesvik_id (INSERT/UPDATE için):", tesvik_id)

    # Formdan gelen diğer verileri al
    belge_no = request.form.get("belge_no") or request.form.get("belge_no_hidden") or "(otomatik)"
    belge_tarihi = request.form.get("belge_tarihi") or request.form.get("belge_tarihi_hidden") or ""
    
    karar = request.form.get("karar")
    yatirim_turu1 = request.form.get("yatirim_turu1")
    yatirim_turu2 = request.form.get("yatirim_turu2")
    program_turu = request.form.get("program_turu")
    vize_durumu = request.form.get("vize_durumu")
    donem = request.form.get("donem")
    il = request.form.get("il")
    osb = request.form.get("osb")
    bolge = request.form.get("bolge") or request.form.get("bolge_hidden")
    
    # Sayısal alanları parse etmek için yardımcı fonksiyon
    def parse_amount(field):
        s = (request.form.get(field) or "0").replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0
    

    # === 🔹 2025/9903 kararına göre özel hesaplama ===
    if karar == "2025/9903":
        print("→ 9903 sayılı karar seçildi: özel oranlar uygulanıyor.")

        # (1) Bölge: BOLGE_MAP_9903'ten
        bolge = BOLGE_MAP_9903.get(il, "Bilinmiyor")

        # (2) Katkı oranı: TESVIK_KATKILAR_9903'tan
        katki_orani = float(TESVIK_KATKILAR_9903.get(program_turu, 0))

        # (4) Vergi oranı: sabit %60
        vergi_orani = 60.0

        # (5) Diğer kazanç oranı: sabit %50
        diger_oran = 50.0

        print(f"→ Bölge: {bolge}, Program: {program_turu}, Katkı: {katki_orani}%, Vergi: {vergi_orani}%, Diğer: {diger_oran}%")

    else:
        # === Diğer kararlar (normal mantık) ===
        def get_oran(map_data, key_tuple):
            return map_data.get(key_tuple, map_data.get((key_tuple[0], "OSB Dışında"), 0))

        if il and il in BOLGE_MAP:
            bolge = bolge or BOLGE_MAP[il]

        katki_orani = get_oran(TESVIK_KATKILAR, (bolge, osb))
        vergi_orani = get_oran(TESVIK_VERGILER, (bolge, osb))
        diger_oran = parse_amount("diger_oran")




    toplam_tutar = parse_amount("toplam_tutar")
    katki_tutari = parse_amount("katki_tutari")
    diger_katki_tutari = parse_amount("diger_katki_tutari")
    cari_harcama_tutari = parse_amount("cari_harcama_tutari")
    toplam_harcama_tutari = parse_amount("toplam_harcama_tutari")
    fiili_katki_tutari = parse_amount("fiili_katki_tutari")
    onceki_yatirim_katki_tutari = parse_amount("onceki_yatirim_katki_tutari")
    onceki_diger_katki_tutari = parse_amount("onceki_diger_katki_tutari")
    onceki_katki_tutari = parse_amount("onceki_katki_tutari")
    kalan_katki_tutari = parse_amount("kalan_katki_tutari")
    endeks_katki_tutari = parse_amount("endeks_katki_tutari")
    brut_satis = parse_amount("brut_satis")
    ihracat = parse_amount("ihracat")
    imalat = parse_amount("imalat")
    diger_faaliyet = parse_amount("diger_faaliyet")
    use_detailed_profit_ratios = 'use_detailed_profit_ratios' in request.form
    cari_yatirim_katki = parse_amount("cari_yatirim_katki")
    cari_diger_katki = parse_amount("cari_diger_katki")
    cari_toplam_katki = parse_amount("cari_toplam_katki")
    genel_toplam_katki = parse_amount("genel_toplam_katki")

    with get_conn() as conn:
        c = conn.cursor()
        try:
            if tesvik_id is None: # Yeni belge oluştur
                c.execute(
                    """INSERT INTO tesvik_belgeleri (user_id, dosya_adi, belge_no, belge_tarihi,
                                                    karar, yatirim_turu1, yatirim_turu2, vize_durumu, donem, il, osb, bolge,
                                                    katki_orani, vergi_orani, diger_oran, toplam_tutar, katki_tutari, diger_katki_tutari,
                                                    cari_harcama_tutari, toplam_harcama_tutari, fiili_katki_tutari, endeks_katki_tutari,
                                                    onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                                                    cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                                                    brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (user_id, belge_no, belge_no, belge_tarihi, # dosya_adi olarak belge_no kullanıldı
                     karar, yatirim_turu1, yatirim_turu2, vize_durumu, donem, il, osb, bolge,
                     katki_orani, vergi_orani, diger_oran, toplam_tutar, katki_tutari, diger_katki_tutari,
                     cari_harcama_tutari, toplam_harcama_tutari, fiili_katki_tutari, endeks_katki_tutari,
                     onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                     cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                     brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios)
                )
                tesvik_id = c.lastrowid # Yeni oluşturulan belgenin ID'sini al
                conn.commit()
                # Yeni oluşturulan ID'yi session'a kaydet, böylece sonraki kaydetmeler update olur
                session["current_tesvik_id"] = tesvik_id 
                print(f"→ Yeni belge oluşturuldu. ID: {tesvik_id}")
                return jsonify({"status": "success", "title": "Başarılı!", "message": "Yeni teşvik belgesi oluşturuldu."})

            
            else: # Mevcut belgeyi güncelle
                c.execute(
                    """
                    UPDATE tesvik_belgeleri
                    SET
                        belge_no = ?, belge_tarihi = ?, karar = ?, yatirim_turu1 = ?, yatirim_turu2 = ?,
                        vize_durumu = ?, donem = ?, il = ?, osb = ?, bolge = ?,
                        katki_orani = ?, vergi_orani = ?, diger_oran = ?,
                        toplam_tutar = ?, katki_tutari = ?, diger_katki_tutari = ?,
                        cari_harcama_tutari = ?, toplam_harcama_tutari = ?, fiili_katki_tutari = ?, endeks_katki_tutari = ?,
                        onceki_yatirim_katki_tutari = ?, onceki_diger_katki_tutari = ?, onceki_katki_tutari = ?,
                        cari_yatirim_katki = ?, cari_diger_katki = ?, cari_toplam_katki = ?, genel_toplam_katki = ?,
                        brut_satis = ?, ihracat = ?, imalat = ?, diger_faaliyet = ?, use_detailed_profit_ratios = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (
                        belge_no, belge_tarihi, karar, yatirim_turu1, yatirim_turu2,
                        vize_durumu, donem, il, osb, bolge,
                        katki_orani, vergi_orani, diger_oran,
                        toplam_tutar, katki_tutari, diger_katki_tutari,
                        cari_harcama_tutari, toplam_harcama_tutari, fiili_katki_tutari, endeks_katki_tutari,
                        onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                        cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                        brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios,
                        tesvik_id, user_id
                    )
                )
                conn.commit()
                print(f"→ Mevcut belge güncellendi. ID: {tesvik_id}")
                return jsonify({"status": "success", "title": "Başarılı!", "message": "Teşvik belgesi başarıyla güncellendi."})
        except Exception as e:
            conn.rollback()
            print(f"Veritabanı işlemi sırasında hata oluştu: {e}")
            return jsonify({"status": "error", "title": "Hata!", "message": f"Belge kaydedilirken bir hata oluştu: {str(e)}"})


@bp.route("/veri-giris", methods=["GET", "POST"])
@login_required
def veri_giris():
    if request.method == "POST":
        faaliyet_kodu = request.form.get("faaliyet_kodu")
        faaliyet_adi  = request.form.get("faaliyet_adi")
        user_id = session["user"] 
        # TODO: Veritabanına kaydetme işlemi - user_id'yi de eklemeyi unutmayın
        flash(f"Kaydedildi: {faaliyet_kodu} - {faaliyet_adi}")
        return redirect(url_for("indirimlikurumlar.index"))
    return render_template("veri_giris.html")




def get_all_tesvik_docs(user_id: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT
                id, user_id, dosya_adi, yukleme_tarihi, belge_no, belge_tarihi,
                karar, yatirim_turu1, yatirim_turu2, vize_durumu, donem, il, osb, bolge,
                katki_orani, vergi_orani, diger_oran, toplam_tutar, katki_tutari, diger_katki_tutari,
                cari_harcama_tutari, toplam_harcama_tutari, fiili_katki_tutari, endeks_katki_tutari,
                onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios
            FROM tesvik_belgeleri
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        )
        cols = [d[0] for d in c.description]
        rows = c.fetchall()
    return [dict(zip(cols, r)) for r in rows]

@bp.route('/tesvik', methods=['GET', 'POST'])
@login_required
def tesvik():
    user_id = session['user']
    if request.method == 'POST':
        # Buradaki POST logic'i artık kullanılmayacak, form_kaydet tarafından yönetilecek
        # Ancak eğer tesvik.html'de ayrıca bir form varsa, o da AJAX'a çevrilmeli.
        # Genelde bu kısım "Tesvik Belgesi Ekle/Güncelle" formunu yönetir.
        # Şu anki HTML'de sadece "Detay" butonu edit_doc'u görüntülüyor, doğrudan update postu yok gibi.
        # Bu yüzden bu kısım şimdilik sadece GET için geçerli olacak varsayıyorum.
        pass # Bu bölüm boş bırakıldı, çünkü form_kaydet route'u işi devraldı

    # GET
    docs = get_all_tesvik_docs(session['user'])
    view_id = request.args.get('view', type=int)
    edit_doc = None
    if view_id:
        edit_doc = next((d for d in docs if d['id'] == view_id), None)
    return render_template('tesvik.html', docs=docs, edit_doc=edit_doc)

@bp.route('/tesvik/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_tesvik(doc_id):
    user_id = session['user']
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute("DELETE FROM tesvik_belgeleri WHERE id=? AND user_id=?", (doc_id, user_id))
            conn.commit()
            # flash('Belge silindi.', 'warning')
            return jsonify({"status": "success", "title": "Silindi!", "message": "Belge başarıyla silindi."})
        except Exception as e:
            conn.rollback()
            print(f"Belge silinirken hata oluştu: {e}")
            return jsonify({"status": "error", "title": "Hata!", "message": f"Belge silinirken bir hata oluştu: {str(e)}"})
    # return redirect(url_for('indirimlikurumlar.tesvik')) # Bu satır artık kullanılmayacak


from flask import Response
@bp.route('/tesvik/pdf/<int:doc_id>')
@login_required
def download_tesvik_pdf(doc_id):
    user_id = session['user']
    # 1) Veritabanından belgeyi çekelim
    with get_conn() as conn:
        c = conn.cursor()
        # PDF için gerekli tüm sütunları çekiyoruz
        c.execute(
            """
            SELECT
                id, user, dosya_adi, yukleme_tarihi, belge_no, belge_tarihi,
                karar, yatirim_turu1, yatirim_turu2, vize_durumu, donem, il, osb, bolge,
                katki_orani, vergi_orani, diger_oran, toplam_tutar, katki_tutari, diger_katki_tutari,
                cari_harcama_tutari, toplam_harcama_tutari, fiili_katki_tutari, endeks_katki_tutari,
                onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios
            FROM tesvik_belgeleri WHERE id = ? AND user_id = ?
            """,
            (doc_id, user_id)
        )
        row = c.fetchone()
    if not row:
        # flash("Belge bulunamadı.", "danger")
        return jsonify({"status": "error", "title": "Hata!", "message": "Belge bulunamadı."}) # Hata mesajı JSON olarak dönüldü
        # return redirect(url_for("indirimlikurumlar.index", sekme="tesvik")) # Bu satır kullanılmayacak

    cols = [d[0] for d in c.description]
    data = dict(zip(cols, row))

    # pdfkit’e wkhtmltopdf’in tam yolunu göster
    config = pdfkit.configuration(
        wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    # 2) Şablonu render edip HTML elde edelim
    html = render_template('kv_tablosu_pdf.html', data=data)

    try:
        # 3) PDF’e dönüştürelim
        pdf = pdfkit.from_string(html, False, configuration=config, options={
            'page-size': 'A4',
            'encoding': 'UTF-8',
            'margin-top': '10mm',
            'margin-bottom': '10mm',
        })

        # 4) PDF’i kullanıcıya dönelim
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=tesvik_{data["belge_no"]}.pdf'
        return response
    except Exception as e:
        print(f"PDF oluşturulurken hata oluştu: {e}")
        # PDF oluşturma hatası durumunda JSON yanıtı dön
        return jsonify({"status": "error", "title": "PDF Hatası!", "message": f"PDF oluşturulurken bir hata oluştu: {str(e)}"})
    
    
from io import BytesIO
import pdfplumber

@bp.route('/upload-kv-beyan', methods=['POST'])
@login_required
def upload_kv_beyan():
    f = request.files.get('kv_pdf')
    if not f or not f.filename.lower().endswith('.pdf'):
        return jsonify(status='error', title='Geçersiz Dosya', message='Lütfen bir PDF dosyası yükleyin.'), 400

    try:
        # PDF verisini belleğe al
        pdf_data = BytesIO(f.read())

        # parse_ikv_from_pdf fonksiyonun path yerine bytes kabul ediyorsa:
        veri = parse_ikv_from_pdf(pdf_data)

        # Eğer parse_ikv_from_pdf sadece path kabul ediyorsa, onu da şöyle güncelleyeceğiz:
        # with pdfplumber.open(BytesIO(pdf_data)) as pdf: ...

        tablolar = veri.get("tablolar", [])
        if not tablolar:
            return jsonify(status='error', title='Veri Hatası', message='Hiç tablo bulunamadı.'), 400

        def parse_veri_listesi(veri_listesi):
            def find_deger(alan):
                for e in veri_listesi:
                    if e["alan"] == alan:
                        return e["deger"]
                return ''
            return {
                'belge_no':    find_deger('Teşvik Belgesi Numarası'),
                'karar':       find_deger('Teşvik Belgesinin Hangi Karara Göre Düzenlendiği'),
                'belge_tarihi':find_deger('Yatırıma Başlama Tarihi'),
                'yatirim_turu1': find_deger('Yatırımın Türü 1'),
                'yatirim_turu2': find_deger('Yatırımın Türü 2'),
                'toplam_tutar': find_deger('Toplam Yatırım Tutarı (İndirimli KV Kapsamında Olmayan Harcamalar Hariç)'),
                'katki_orani':  find_deger('Yatırıma Katkı Oranı'),
                'vergi_orani':  find_deger('Vergi İndirim Oranı'),
                'bolge':        find_deger('Yatırımın Yapıldığı Bölge'),
                'diger_oran':   find_deger('İndirimli KV Oranı'),
                'katki_tutari':          find_deger('Toplam Yatırıma Katkı Tutarı'),
                'cari_harcama_tutari':   find_deger('Cari Yılda Fiilen Gerçekleştirilen Yatırım Harcaması Tutarı'),
                'toplam_harcama_tutari': find_deger('Fiilen Gerçekleştirilen Yatırım Harcaması (Yatırımın Başlangıcından İtibaren)'),
                'fiili_katki_tutari':    find_deger('Fiili Yatırım Harcaması Nedeniyle Hak Kazanılan Yatırıma Katkı Tutarı'),
                'endeks_katki_tutari':   find_deger('Endekslenmiş Tutarlar Nedeniyle Hak Kazanılan Yatırıma Katkı Tutarı'),
                'onceki_yatirim_katki_tutari': find_deger('Önceki Dönemlerde Yararlanılan Yatırıma Katkı (Yatırımdan Elde Edilen)'),
                'onceki_diger_katki_tutari':   find_deger('Önceki Dönemlerde Yararlanılan Yatırıma Katkı (Diğer Faaliyetlerden)'),
                'onceki_katki_tutari':         find_deger('Önceki Dönemlerde Yararlanılan Toplam Yatırıma Katkı Tutarı'),
                'cari_yatirim_katki':    find_deger('Cari Dönemde Yararlanılan Yatırıma Katkı (Yatırımdan Elde Edilen)'),
                'cari_diger_katki':      find_deger('Cari Dönemde Yararlanılan Yatırıma Katkı (Diğer Faaliyetlerden)'),
                'cari_toplam_katki':     find_deger('Cari Dönemde Yararlanılan Toplam Yatırıma Katkı Tutarı'),
                'genel_toplam_katki':    find_deger('Cari Dönem Dahil Olmak Üzere Yararlanılan Toplam Yatırıma Katkı Tutarı'),
            }

        if len(tablolar) > 1:
            parsed_list = []
            secenekler = []
            for i, tablo in enumerate(tablolar):
                parsed = parse_veri_listesi(tablo.get("veriler", []))
                current_app.logger.info(f"[DEBUG] Tablo {i} - Belge No: {parsed.get('belge_no')}")
                parsed_list.append(parsed)
                secenekler.append({
                    "index": i,
                    "belge_no": parsed["belge_no"] or f"Belge {i+1}"
                })
            return jsonify(status='multiple', tablolar=secenekler, raw_data=parsed_list)

        parsed = parse_veri_listesi(tablolar[0].get("veriler", []))
        return jsonify(status='ok', parsed=parsed)

    except Exception as e:
        current_app.logger.exception("PDF parse hatası")
        return jsonify(status='error', title='Parse Hatası', message=str(e)), 500




@bp.route("/mevzuat", methods=["GET"])
@login_required
def mevzuat():
    return render_template("mevzuat.html")


