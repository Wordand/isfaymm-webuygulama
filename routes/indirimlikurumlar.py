import os
import pandas as pd
import io
import pdfkit
import pdfplumber
import re
import tempfile
import os
import shutil
import json
import traceback

from datetime import datetime
from flask import Blueprint, render_template, request, session, flash, redirect, url_for, flash, make_response, current_app, send_file, jsonify
from werkzeug.utils import secure_filename


from services.db import get_conn
from config import ILLER, BOLGE_MAP, BOLGE_MAP_9903, TESVIK_KATKILAR, TESVIK_VERGILER, TESVIK_KATKILAR_9903
from auth import login_required
from types import SimpleNamespace

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
            "FROM profit_data WHERE user_id = %s",
            (user_id,)
        )
        db_data = c.fetchall()

        if db_data:
            for row_idx, val_b, val_c, val_d, val_e in db_data:
                try:
                    row_idx = int(row_idx)
                except (ValueError, TypeError):
                    continue  # Geçersiz indeksleri atla
                if 0 <= row_idx < len(explanations): 
                    df.at[row_idx, 'B'] = val_b
                    df.at[row_idx, 'C'] = val_c
                    df.at[row_idx, 'D'] = val_d
                    df.at[row_idx, 'E'] = val_e
        else:
            for i, _ in enumerate(explanations):
                c.execute(
                    "INSERT INTO profit_data (user_id, aciklama_index, column_b, column_c, column_d, column_e) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
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
            c.execute("""
                INSERT INTO profit_data (user_id, aciklama_index, column_b, column_c, column_d, column_e)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, aciklama_index)
                DO UPDATE SET
                    column_b = EXCLUDED.column_b,
                    column_c = EXCLUDED.column_c,
                    column_d = EXCLUDED.column_d,
                    column_e = EXCLUDED.column_e
            """, (user_id, i, row['B'], row['C'], row['D'], row['E']))
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




@bp.route('/ayrintili-kazanc', methods=['GET', 'POST'])
@login_required
def ayrintili_kazanc():
    user_id = session["user_id"]

    try:
        if request.method == 'POST':
            current_df_profit = get_user_profit_df(user_id)

            # 🟦 İçe Aktar
            if 'import' in request.form:
                return jsonify({
                    "status": "warning",
                    "title": "İçe Aktarılamadı!",
                    "message": "İçe aktar henüz uygulanmadı."
                })

            # 📤 Dışa Aktar
            elif 'export' in request.form or request.form.get("action") == "export":
                df = get_user_profit_df(user_id).copy()

                # 🧮 Formdan gelen değerleri oku
                for i in range(len(df)):
                    for col in ['B', 'C', 'D', 'E']:
                        raw_val = (request.form.get(f"{col}_{i}") or "").replace(".", "").replace(",", ".")
                        try:
                            df.at[i, col] = float(raw_val)
                        except ValueError:
                            df.at[i, col] = 0.0



                # 💡 1️⃣ Toplamları hesapla
                total_b = df['B'].sum()
                total_c = df['C'].sum()
                total_d = df['D'].sum()
                total_e = df['E'].sum()

                # 💡 2️⃣ ORANLAR (%) (ilk satır)
                df.at[0, 'Açıklama'] = "ORANLAR (%) (FAALİYET TÜRLERİ İTİBARİYLE)"
                df.at[0, 'B'] = 100.00
                if total_b != 0:
                    df.at[0, 'C'] = round((total_c / total_b) * 100, 2)
                    df.at[0, 'D'] = round((total_d / total_b) * 100, 2)
                    df.at[0, 'E'] = round((total_e / total_b) * 100, 2)
                else:
                    df.at[0, ['C', 'D', 'E']] = 0.00

                # 💡 3️⃣ İHRACAT, İMALAT VE DİĞER FAALİYETLERİN TOPLAM PAYLARI (%)
                df.at[54, 'Açıklama'] = "İHRACAT, İMALAT VE DİĞER FAALİYETLERİN TOPLAM PAYLARI (%)"
                df.at[54, 'B'] = 100.00
                if total_b != 0:
                    df.at[54, 'C'] = round((total_c / total_b) * 100, 2)
                    df.at[54, 'D'] = round((total_d / total_b) * 100, 2)
                    df.at[54, 'E'] = round((total_e / total_b) * 100, 2)
                else:
                    df.at[54, ['C', 'D', 'E']] = 0.00







                # 📈 Excel oluştur
                import io, xlsxwriter
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name="Ayrıntılı Kazanç Tablosu")
                output.seek(0)
                return send_file(
                    output,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    as_attachment=True,
                    download_name="ayrintili_kazanc_tablosu.xlsx"
                )

            # 💾 Kaydetme işlemi
            else:
                for i in range(len(explanations)):
                    for col in ['B', 'C', 'D', 'E']:
                        raw = (request.form.get(f"{col}_{i}") or '').replace('.', '').replace(',', '.')
                        try:
                            val = raw.replace('%', '')
                            current_df_profit.at[i, col] = float(val) if val != '' else 0.0
                        except ValueError:
                            current_df_profit.at[i, col] = 0.0

                save_user_profit_df(user_id, current_df_profit)
                return jsonify({
                    "status": "success",
                    "title": "Kaydedildi!",
                    "message": "Ayrıntılı kazanç tablosu başarıyla kaydedildi."
                })

        # 🟨 GET isteği — tabloyu yükle
        current_df_profit = get_user_profit_df(user_id)
        formatted_data_for_html = format_df_for_html(current_df_profit)

        safe_bolge_map = {str(k): v if v is not None else None for k, v in BOLGE_MAP.items()}
        safe_katkilar_json = {f"{k[0]}|{k[1]}" if isinstance(k, tuple) else str(k): v for k, v in TESVIK_KATKILAR.items()}
        safe_vergiler_json = {f"{k[0]}|{k[1]}" if isinstance(k, tuple) else str(k): v for k, v in TESVIK_VERGILER.items()}

        initial_ayrintili_ratios = {
            "C": f"{current_df_profit.at[54,'C']:.2f}".replace('.', ',') + "%" if not pd.isna(current_df_profit.at[54,'C']) else "0,00%",
            "D": f"{current_df_profit.at[54,'D']:.2f}".replace('.', ',') + "%" if not pd.isna(current_df_profit.at[54,'D']) else "0,00%",
            "E": f"{current_df_profit.at[54,'E']:.2f}".replace('.', ',') + "%" if not pd.isna(current_df_profit.at[54,'E']) else "0,00%",
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
        print(f"ayrintili_kazanc hata: {e}")
        return jsonify({
            "status": "error",
            "title": "Sunucu Hatası!",
            "message": f"Beklenmeyen bir sunucu hatası oluştu: {str(e)}"
        })







@bp.route("/mukellef-listesi")
@login_required
def mukellef_listesi():
    """Aktif kullanıcının mükellef listesini getirir"""
    uid = session.get("user_id")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, vergi_kimlik_no, unvan FROM mukellef WHERE user_id = %s", (uid,))
        rows = [dict(zip([desc[0] for desc in c.description], r)) for r in c.fetchall()]
    return jsonify(rows)


@bp.route("/mukellef-bilgi")
@login_required
def mukellef_bilgi():
    user_id = session.get("user_id")
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, vergi_kimlik_no, unvan FROM mukellef WHERE user_id = %s", (user_id,))
        data = c.fetchall()
    return render_template("mukellef_bilgi.html", mukellefler=data)


@bp.route("/mukellef-sec", methods=["POST"])
@login_required
def mukellef_sec():
    try:
        data = request.get_json()
        mukellef_id = data.get("id")

        with get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT vergi_kimlik_no, unvan FROM mukellef WHERE id = %s", (mukellef_id,))
            row = c.fetchone()

        if not row:
            return jsonify({"status": "error", "message": "Mükellef bulunamadı."}), 404

        # 🟢 Burada artık dict olarak erişiyoruz:
        session["aktif_mukellef_id"] = mukellef_id
        session["aktif_mukellef_vkn"] = row["vergi_kimlik_no"]
        session["aktif_mukellef_unvan"] = row["unvan"]

        print(f"✅ Mükellef seçildi: {row['unvan']} ({row['vergi_kimlik_no']})")

        return jsonify({"status": "success"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        print("❌ mukellef-sec hatası:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/mukellef-ekle", methods=["POST"])
@login_required
def mukellef_ekle():
    data = request.get_json()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO mukellef (user_id, vergi_kimlik_no, unvan) VALUES (%s, %s, %s)",
            (session["user_id"], data["vergi_kimlik_no"], data["unvan"])
        )
        conn.commit()
    return jsonify({"status": "success"})


@bp.route("/mukellef-guncelle", methods=["POST"])
@login_required
def mukellef_guncelle():
    data = request.get_json()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE mukellef SET vergi_kimlik_no=%s, unvan=%s WHERE id=%s AND user_id=%s",
            (data["vergi_kimlik_no"], data["unvan"], data["id"], session["user_id"])
        )
        conn.commit()
    return jsonify({"status": "success"})


@bp.route("/mukellef-sil", methods=["POST"])
@login_required
def mukellef_sil():
    data = request.get_json()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM mukellef WHERE id=%s AND user_id=%s",
            (data["id"], session["user_id"])
        )
        conn.commit()
    return jsonify({"status": "success"})







@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    sekme = request.args.get("sekme", "mukellef")
    user_id = session["user_id"]
    aktif_mukellef_id = session.get("aktif_mukellef_id")

    if not aktif_mukellef_id and sekme != "mukellef":
        return redirect(url_for("indirimlikurumlar.index", sekme="mukellef"))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, vergi_kimlik_no, unvan FROM mukellef WHERE user_id = %s ORDER BY id DESC",
            (user_id,),
        )
        mukellefler = c.fetchall()

    docs, user_df, current_belge = [], None, None
    edit_doc = None

    if aktif_mukellef_id:
        docs = get_all_tesvik_docs(user_id)
        user_df = get_user_profit_df(user_id)

        view_id = request.args.get("view", type=int)
        if sekme == "tesvik" and view_id:
            edit_doc = next((d for d in docs if d["id"] == view_id), None)
            if edit_doc:
                print(f"📄 Teşvik detayı görüntüleniyor: ID={view_id}")

    # 🟩 Eğer sekme ayrıntılıysa DataFrame'den rows üret
    rows = []
    if sekme == "ayrintili":
        try:
            df = get_user_profit_df(user_id)
            rows = format_df_for_html(df)
        except Exception as e:
            print(f"⚠️ Ayrıntılı tablo yüklenirken hata: {e}")
            rows = []  # hata olsa bile boş liste dön

    # Güvenli JSON objeleri
    safe_bolge_map = {}
    for k, v in (globals().get("BOLGE_MAP") or {}).items():
        key = str(k)
        safe_bolge_map[key] = v if v is not None and not (isinstance(v, float) and pd.isna(v)) else None

    safe_katkilar_json = {}
    for k, v in (globals().get("TESVIK_KATKILAR") or {}).items():
        key = f"{k[0]}|{k[1]}" if isinstance(k, tuple) and len(k)==2 else str(k)
        safe_katkilar_json[key] = v if v is not None and not (isinstance(v, float) and pd.isna(v)) else None

    safe_vergiler_json = {}
    for k, v in (globals().get("TESVIK_VERGILER") or {}).items():
        key = f"{k[0]}|{k[1]}" if isinstance(k, tuple) and len(k)==2 else str(k)
        safe_vergiler_json[key] = v if v is not None and not (isinstance(v, float) and pd.isna(v)) else None


    initial_ayrintili_ratios = {}
    if user_df is not None:
        initial_ayrintili_ratios = {
            c: f"{user_df.at[54, c]:.2f}".replace(".", ",") + "%"
            if not pd.isna(user_df.at[54, c])
            else "0,00%"
            for c in ["C", "D", "E"]
        }

    ctx = dict(
        sekme=sekme,
        mukellefler=mukellefler,
        aktif_mukellef_id=aktif_mukellef_id,
        iller = globals().get("ILLER", []),
        bolge_json=safe_bolge_map,
        katkilar_json=safe_katkilar_json,
        vergiler_json=safe_vergiler_json,
        initial_ayrintili_ratios=initial_ayrintili_ratios,
        docs=docs,
        current_belge=current_belge,
        edit_doc=edit_doc,
        BOLGE_MAP_9903 = globals().get("BOLGE_MAP_9903", {}),
        TESVIK_KATKILAR_9903 = globals().get("TESVIK_KATKILAR_9903", {}),
        rows=rows,
    )

    if sekme == "mukellef":
        return render_template("mukellef_bilgi.html", **ctx)
    return render_template("indirimlikurumlar.html", **ctx)




@bp.route("/form", methods=["POST"])
@login_required
def form_kaydet():
    print(">>> form_kaydet GİRİLDİ")
    user_id = session["user_id"]
    mukellef_id = session.get("aktif_mukellef_id")

    if not mukellef_id:
        return jsonify({
            "status": "error",
            "title": "Eksik Bilgi!",
            "message": "Lütfen önce bir mükellef seçiniz."
        }), 400

    # Teşvik ID tespiti
    tesvik_id = session.get("current_tesvik_id") or request.form.get("tesvik_id")
    tesvik_id = int(tesvik_id) if tesvik_id and str(tesvik_id).isdigit() else None
    print(f"→ Aktif Teşvik ID: {tesvik_id}")

    # Yardımcı fonksiyon
    def parse_amount(field):
        s = (request.form.get(field) or "0").replace(".", "").replace(",", ".")
        try: 
            return float(s)
        except:
            return 0.0

    # Form alanları
    belge_no = request.form.get("belge_no") or "(otomatik)"
    belge_tarihi = request.form.get("belge_tarihi") or ""
    karar = request.form.get("karar")
    program_turu = request.form.get("program_turu") or ""
    yatirim_turu1 = request.form.get("yatirim_turu1")
    yatirim_turu2 = request.form.get("yatirim_turu2")
    vize_durumu = request.form.get("vize_durumu")
    donem = request.form.get("donem")
    il = request.form.get("il")
    osb = request.form.get("osb")
    bolge = request.form.get("bolge")

    if karar == "2025/9903":
        bolge = BOLGE_MAP_9903.get(il, "Bilinmiyor")
        katki_orani = float(TESVIK_KATKILAR_9903.get(program_turu, 0))
        vergi_orani = 60.0
        diger_oran = 50.0
    else:
        katki_orani = parse_amount("katki_orani")
        vergi_orani = parse_amount("vergi_orani")
        diger_oran = parse_amount("diger_oran")

    toplam_tutar = parse_amount("toplam_tutar")
    katki_tutari = parse_amount("katki_tutari")
    diger_katki_tutari = parse_amount("diger_katki_tutari")
    cari_harcama_tutari = parse_amount("cari_harcama_tutari")
    toplam_harcama_tutari = parse_amount("toplam_harcama_tutari")
    fiili_katki_tutari = parse_amount("fiili_katki_tutari")
    endeks_katki_tutari = parse_amount("endeks_katki_tutari")
    onceki_yatirim_katki_tutari = parse_amount("onceki_yatirim_katki_tutari")
    onceki_diger_katki_tutari = parse_amount("onceki_diger_katki_tutari")
    onceki_katki_tutari = parse_amount("onceki_katki_tutari")
    cari_yatirim_katki = parse_amount("cari_yatirim_katki")
    cari_diger_katki = parse_amount("cari_diger_katki")
    cari_toplam_katki = parse_amount("cari_toplam_katki")
    genel_toplam_katki = parse_amount("genel_toplam_katki")
    brut_satis = parse_amount("brut_satis")
    ihracat = parse_amount("ihracat")
    imalat = parse_amount("imalat")
    diger_faaliyet = parse_amount("diger_faaliyet")
    use_detailed_profit_ratios = 'use_detailed_profit_ratios' in request.form

    with get_conn() as conn:
        c = conn.cursor()
        try:
            if tesvik_id:
                c.execute("""
                    UPDATE tesvik_belgeleri
                    SET mukellef_id=%s, belge_no=%s, belge_tarihi=%s, karar=%s,
                        program_turu=%s, yatirim_turu1=%s, yatirim_turu2=%s,
                        vize_durumu=%s, donem=%s, il=%s, osb=%s, bolge=%s,
                        katki_orani=%s, vergi_orani=%s, diger_oran=%s,
                        toplam_tutar=%s, katki_tutari=%s, diger_katki_tutari=%s,
                        cari_harcama_tutari=%s, toplam_harcama_tutari=%s,
                        fiili_katki_tutari=%s, endeks_katki_tutari=%s,
                        onceki_yatirim_katki_tutari=%s, onceki_diger_katki_tutari=%s, onceki_katki_tutari=%s,
                        cari_yatirim_katki=%s, cari_diger_katki=%s, cari_toplam_katki=%s, genel_toplam_katki=%s,
                        brut_satis=%s, ihracat=%s, imalat=%s, diger_faaliyet=%s, use_detailed_profit_ratios=%s
                    WHERE id=%s AND user_id=%s
                """, (
                    mukellef_id, belge_no, belge_tarihi, karar,
                    program_turu, yatirim_turu1, yatirim_turu2,
                    vize_durumu, donem, il, osb, bolge,
                    katki_orani, vergi_orani, diger_oran,
                    toplam_tutar, katki_tutari, diger_katki_tutari,
                    cari_harcama_tutari, toplam_harcama_tutari,
                    fiili_katki_tutari, endeks_katki_tutari,
                    onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                    cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                    brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios,
                    tesvik_id, user_id
                ))
                conn.commit()

            else:
                c.execute("""
                    INSERT INTO tesvik_belgeleri (
                        user_id, mukellef_id, belge_no, belge_tarihi,
                        karar, program_turu, yatirim_turu1, yatirim_turu2,
                        vize_durumu, donem, il, osb, bolge,
                        katki_orani, vergi_orani, diger_oran,
                        toplam_tutar, katki_tutari, diger_katki_tutari,
                        cari_harcama_tutari, toplam_harcama_tutari,
                        fiili_katki_tutari, endeks_katki_tutari,
                        onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                        cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                        brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id;
                """, (
                    user_id, mukellef_id, belge_no, belge_tarihi,
                    karar, program_turu, yatirim_turu1, yatirim_turu2,
                    vize_durumu, donem, il, osb, bolge,
                    katki_orani, vergi_orani, diger_oran,
                    toplam_tutar, katki_tutari, diger_katki_tutari,
                    cari_harcama_tutari, toplam_harcama_tutari,
                    fiili_katki_tutari, endeks_katki_tutari,
                    onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                    cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                    brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios
                ))

                row = c.fetchone()
                if not row:
                    raise Exception("INSERT başarılı fakat RETURNING id boş döndü!")

                tesvik_id = row[0]
                session["current_tesvik_id"] = tesvik_id
                conn.commit()
                print(f"✅ Yeni belge oluşturuldu: ID={tesvik_id}")

            return jsonify({
                "status": "success",
                "title": "Başarılı!",
                "message": "Teşvik belgesi kaydedildi.",
                "tesvik_id": tesvik_id
            })

        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "title": "Kayıt Hatası!",
                "message": f"Veritabanı hatası: {repr(e)}"
            })



def get_all_tesvik_docs(user_id: int):
    """Kullanıcının teşvik belgelerini döndürür (hem SQLite hem PostgreSQL uyumlu)."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT
                id, user_id, yukleme_tarihi, belge_no, belge_tarihi,
                karar, program_turu, yatirim_turu1, yatirim_turu2, vize_durumu, donem, il, osb, bolge,
                katki_orani, vergi_orani, diger_oran, toplam_tutar, katki_tutari, diger_katki_tutari,
                cari_harcama_tutari, toplam_harcama_tutari, fiili_katki_tutari, endeks_katki_tutari,
                onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios
            FROM tesvik_belgeleri
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,),
        )

        rows = c.fetchall()

        if rows and isinstance(rows[0], dict):
            return rows

        colnames = [desc[0] for desc in c.description]
        return [dict(zip(colnames, row)) for row in rows]


@bp.route('/tesvik', methods=['GET', 'POST'])
@login_required
def tesvik():
    user_id = session.get("user_id")

    # 🔹 Tüm belgeleri listele
    docs = get_all_tesvik_docs(user_id)

    # 🔹 Eğer ?view=ID varsa detay moduna geç
    view_id = request.args.get('view', type=int)
    edit_doc = None

    if view_id:
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT
                    id, user_id, mukellef_id, yukleme_tarihi,
                    belge_no, belge_tarihi, karar, program_turu,
                    yatirim_turu1, yatirim_turu2, vize_durumu, donem, il, osb, bolge,
                    katki_orani, vergi_orani, diger_oran,
                    toplam_tutar, katki_tutari, diger_katki_tutari,
                    cari_harcama_tutari, toplam_harcama_tutari,
                    fiili_katki_tutari, endeks_katki_tutari,
                    onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                    cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                    brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios
                FROM tesvik_belgeleri
                WHERE id = %s AND user_id = %s
            """, (view_id, user_id))
            row = c.fetchone()

        if row:
            colnames = [desc[0] for desc in c.description]  # cursor.description okunduğunda saklanmış olur
            edit_doc = dict(zip(colnames, row))              # ✅ tuple → dict dönüşümü
            print(f"🔍 Detay görüntüleniyor: {edit_doc.get('belge_no')} (ID: {view_id})")
        else:
            flash("Belge bulunamadı veya erişim yetkiniz yok.", "warning")

    return render_template('tesvik.html', docs=docs, edit_doc=edit_doc)



@bp.route('/tesvik/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_tesvik(doc_id):
    user_id = session.get("user_id")

    with get_conn() as conn:
        c = conn.cursor()
        try:
            # 🟢 Önce silinen belge aktif belgemiz miydi?
            if session.get("current_tesvik_id") == doc_id:
                session.pop("current_tesvik_id", None)  # ✅ temizle

            c.execute(
                "DELETE FROM tesvik_belgeleri WHERE id=%s AND user_id=%s",
                (doc_id, user_id)
            )
            conn.commit()

            return jsonify({
                "status": "success",
                "title": "Silindi!",
                "message": "Belge başarıyla silindi."
            })

        except Exception as e:
            conn.rollback()
            print(f"❌ Belge silinirken hata oluştu: {e}")
            return jsonify({
                "status": "error",
                "title": "Hata!",
                "message": f"Belge silinirken hata oluştu: {str(e)}"
            })



@bp.route("/tesvik/pdf/<int:doc_id>")
@login_required
def download_tesvik_pdf(doc_id):
    user_id = session["user_id"]

    # 🧾 1️⃣ Veritabanından belgeyi çek
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT
                id, user_id, yukleme_tarihi, belge_no, belge_tarihi,
                karar, program_turu, yatirim_turu1, yatirim_turu2,
                vize_durumu, donem, il, osb, bolge,
                katki_orani, vergi_orani, diger_oran,
                toplam_tutar, katki_tutari, diger_katki_tutari,
                cari_harcama_tutari, toplam_harcama_tutari,
                fiili_katki_tutari, endeks_katki_tutari,
                onceki_yatirim_katki_tutari, onceki_diger_katki_tutari, onceki_katki_tutari,
                cari_yatirim_katki, cari_diger_katki, cari_toplam_katki, genel_toplam_katki,
                brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios
            FROM tesvik_belgeleri
            WHERE id = %s AND user_id = %s
        """, (doc_id, user_id))

        row = c.fetchone()
        if not row:
            return jsonify({"status": "error", "title": "Hata!", "message": "Belge bulunamadı."}), 404

        # 🟢 Burada cursor hala açık → güvenli dict dönüşümü
        if isinstance(row, dict):
            data_dict = row
        else:
            colnames = [desc[0] for desc in c.description]
            data_dict = dict(zip(colnames, row))

    # 🟢 Artık bağlantı kapansa da sorun yok
    data = SimpleNamespace(**data_dict)

    try:
        # 2️⃣ wkhtmltopdf yolu
        wkhtml_path = current_app.config.get("WKHTMLTOPDF_PATH") or shutil.which("wkhtmltopdf")
        if not wkhtml_path:
            return jsonify({"status": "error", "title": "Eksik Araç", "message": "wkhtmltopdf bulunamadı."}), 500

        config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

        # 3️⃣ HTML şablonu
        rendered = render_template("kv_tablosu_pdf.html", data=data, now=datetime.now)

        # 4️⃣ PDF oluşturma (geçici dosya)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            pdfkit.from_string(rendered, tmpfile.name, configuration=config, options={
                "page-size": "A4",
                "encoding": "UTF-8",
                "enable-local-file-access": "",
                "margin-top": "15mm", "margin-bottom": "15mm",
                "margin-left": "12mm", "margin-right": "12mm",
                "dpi": 300,
            })
            tmpfile.flush()

        # 5️⃣ Kullanıcıya gönder
        filename = f"tesvik_{data.belge_no or doc_id}.pdf"
        return send_file(tmpfile.name, mimetype="application/pdf", as_attachment=True, download_name=filename)

    except Exception as e:
        print(f"⚠️ PDF oluşturma hatası: {e}")
        return jsonify({"status": "error", "title": "PDF Hatası!", "message": str(e)}), 500

        
        
        
        
    
    
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
                'program_turu': find_deger('Program Türü') or find_deger('Programın Türü'),
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






@bp.route("/save_tesvik_kullanim", methods=["POST"])
@login_required
def save_tesvik_kullanim():
    """
    Her hesap dönemi için teşvik kullanım kaydı oluşturur veya günceller.
    (Aşama 7 tamamlandığında otomatik çağrılır)
    """
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"status": "error", "message": "Oturum bulunamadı."}), 401

        data = request.get_json(force=True)
        belge_no = data.get("belge_no")
        hesap_donemi = int(data.get("hesap_donemi", datetime.now().year))

        yatirim_kazanci = float(data.get("yatirim_kazanci", 0))
        diger_kazanc = float(data.get("diger_kazanc", 0))
        cari_yatirim_katkisi = float(data.get("cari_yatirim_katkisi", 0))
        cari_diger_katkisi = float(data.get("cari_diger_katkisi", 0))
        genel_toplam_katki = float(data.get("genel_toplam_katki", 0))
        kalan_katki = float(data.get("kalan_katki", 0))

        if not belge_no:
            return jsonify({"status": "error", "message": "Belge numarası eksik."}), 400

        with get_conn() as conn:
            cur = conn.cursor()

            
            insert_sql = """
                INSERT INTO tesvik_kullanim (
                    user_id, belge_no, hesap_donemi,
                    yatirim_kazanci, diger_kazanc,
                    cari_yatirim_katkisi, cari_diger_katkisi,
                    genel_toplam_katki, kalan_katki
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id, belge_no, hesap_donemi)
                DO UPDATE SET
                    yatirim_kazanci = EXCLUDED.yatirim_kazanci,
                    diger_kazanc = EXCLUDED.diger_kazanc,
                    cari_yatirim_katkisi = EXCLUDED.cari_yatirim_katkisi,
                    cari_diger_katkisi = EXCLUDED.cari_diger_katkisi,
                    genel_toplam_katki = EXCLUDED.genel_toplam_katki,
                    kalan_katki = EXCLUDED.kalan_katki,
                    kayit_tarihi = CURRENT_TIMESTAMP;
            """

            cur.execute(insert_sql, (
                user_id, belge_no, hesap_donemi,
                yatirim_kazanci, diger_kazanc,
                cari_yatirim_katkisi, cari_diger_katkisi,
                genel_toplam_katki, kalan_katki
            ))

            conn.commit()

        return jsonify({
            "status": "success",
            "title": "Kayıt Başarılı",
            "message": f"{belge_no} ({hesap_donemi}) dönemine ait teşvik kullanımı kaydedildi."
        })

    except Exception as e:
        print(f"⚠️ save_tesvik_kullanim hata: {e}")
        return jsonify({
            "status": "error",
            "title": "Kayıt Hatası",
            "message": f"Kaydedilirken bir hata oluştu: {str(e)}"
        }), 500








@bp.route("/mevzuat", methods=["GET"])
@login_required
def mevzuat():
    """
    İndirimli Kurumlar Vergisi uygulamasına ilişkin mevzuat, kanun ve kararların
    açıklandığı bilgi sayfası (statik bilgilendirme sayfası).
    """
    return render_template("indirimlikurumlar/mevzuat.html", title="İndirimli Kurumlar Vergisi Mevzuatı")
