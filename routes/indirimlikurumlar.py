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
import psycopg2
import psycopg2.extras

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
            'calculators/indirimlikurumlar.html',
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
    from flask import redirect, url_for
    return redirect(url_for('mukellef.index'))


# Not: mukellef-sec rotası mukellef_routes blueprintine taşındı.


# Not: mukellef-ekle, guncelle, sil ve sec rotaları mukellef_routes blueprintine taşındı.




@bp.route("/list_tesvik_docs")
@login_required
def list_tesvik_docs():
    user_id = session["user_id"]
    mukellef_id = session.get("aktif_mukellef_id")

    docs = get_all_tesvik_docs(user_id, mukellef_id)

    return jsonify({"docs": docs})


@bp.route('/new_tesvik', methods=['POST'])
@login_required
def new_tesvik():
    """Yeni teşvik belgesi oluşturur (mükellef + kullanıcı bazında)."""
    try:
        data = request.get_json()
        mukellef_id = session.get("aktif_mukellef_id")
        user_id = session.get("user_id")

        if not user_id or not mukellef_id:
            return jsonify({
                "status": "error",
                "title": "Oturum Bilgisi Eksik",
                "message": "Kullanıcı veya mükellef bilgisi bulunamadı. Lütfen tekrar giriş yapın."
            }), 400

        belge_no = data.get("belge_no", "").strip()
        belge_tarihi = data.get("belge_tarihi", "").strip()

        if not belge_no or not belge_tarihi:
            return jsonify({
                "status": "warning",
                "title": "Eksik Bilgi",
                "message": "Belge numarası ve tarihi zorunludur."
            }), 400

        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            c.execute("""
                INSERT INTO tesvik_belgeleri (
                    user_id, mukellef_id, yukleme_tarihi,
                    belge_no, belge_tarihi, olusturan_id
                )
                VALUES (%s, %s, NOW(), %s, %s, %s)
                RETURNING id;
            """, (user_id, mukellef_id, belge_no, belge_tarihi, user_id))

            row = c.fetchone()
            if not row:
                raise Exception("INSERT başarılı fakat id döndürülmedi.")

            new_id = row["id"]
            conn.commit()

        # 🔥 Kritik: Form akışının düzgün çalışması için ID'yi session'a kaydediyoruz.
        session["current_tesvik_id"] = new_id

        return jsonify({
            "status": "success",
            "title": "Yeni Belge Oluşturuldu",
            "message": f"Belge başarıyla oluşturuldu. (ID: {new_id})",
            "id": new_id
        }), 200

    except Exception as e:
        current_app.logger.error(f"❌ new_tesvik hatası: {e}")
        return jsonify({
            "status": "error",
            "title": "Sunucu Hatası",
            "message": str(e)
        }), 500





@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    print("🔥 indirimlikurumlar.index çalıştı")
    sekme = request.args.get("sekme", "form")
    user_id = session["user_id"]
    aktif_mukellef_id = session.get("aktif_mukellef_id")

    if not aktif_mukellef_id:
        from flask import url_for
        return redirect(url_for("mukellef.index", next=url_for("indirimlikurumlar.index")))
    
    # 🔍 Eğer unvan oturumda yoksa veritabanından çek (Formun görünmesi için kritik)
    if not session.get("aktif_mukellef_unvan"):
        try:
            with get_conn() as conn:
                c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                c.execute("SELECT vergi_kimlik_no, unvan FROM mukellef WHERE id = %s AND user_id = %s", (aktif_mukellef_id, user_id))
                row = c.fetchone()
                if row:
                    session["aktif_mukellef_vkn"] = row["vergi_kimlik_no"]
                    session["aktif_mukellef_unvan"] = row["unvan"]
                    print(f"✅ Oturum verisi tazelendi: {row['unvan']}")
        except Exception as e:
            print(f"⚠️ Oturum verisi tazelenirken hata: {e}")

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
        docs = get_all_tesvik_docs(user_id, aktif_mukellef_id)
        user_df = get_user_profit_df(user_id)
        
        

                    

        view_id = request.args.get("view", type=int)

        if sekme == "tesvik" and view_id:
            edit_doc = next((d for d in docs if d["id"] == view_id and d["mukellef_id"] == aktif_mukellef_id), None)
            if edit_doc:
                print(f"📄 Teşvik detayı görüntüleniyor: ID={view_id}")

        elif sekme == "form" and view_id:
            with get_conn() as conn_form:
                cur = conn_form.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("""
                    SELECT *
                    FROM tesvik_belgeleri
                    WHERE id = %s AND user_id = %s AND mukellef_id = %s
                """, (view_id, user_id, aktif_mukellef_id))
                current_belge = cur.fetchone()

            if current_belge:
                print(f"📝 Form için belge yüklendi: ID={view_id}")

    # 🔹 Yeni Nesil Tasarım İçin Kullanimlar Verisini Hazırla
    kullanimlar = {}
    if docs:
        with get_conn() as conn_k:
            cur_k = conn_k.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            belge_nolar = [d["belge_no"] for d in docs if d.get("belge_no")]
            if belge_nolar:
                cur_k.execute("""
                    SELECT * FROM tesvik_kullanim 
                    WHERE user_id = %s AND belge_no = ANY(%s)
                    ORDER BY hesap_donemi DESC
                """, (user_id, belge_nolar))
                all_k = cur_k.fetchall()
                for item in all_k:
                    bno = item["belge_no"]
                    if bno not in kullanimlar:
                        kullanimlar[bno] = []
                    kullanimlar[bno].append(item)
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
        kullanimlar=kullanimlar,
        BOLGE_MAP_9903 = globals().get("BOLGE_MAP_9903", {}),
        TESVIK_KATKILAR_9903 = globals().get("TESVIK_KATKILAR_9903", {}),
        rows=rows,
    )

    if sekme == "mukellef":
        return redirect(url_for("mukellef.index"))
    return render_template("calculators/indirimlikurumlar.html", **ctx)


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

    # ---------------------------------------------------
    #        🔍 1) TESVIK ID BELİRLEME
    # ---------------------------------------------------
    view_id = request.args.get("view", type=int)
    tesvik_id = None

    if view_id:
        tesvik_id = view_id
        print(f"🔗 URL’den gelen view_id kullanılıyor: {tesvik_id}")

    else:
        tesvik_id_raw = request.form.get("tesvik_id")
        if tesvik_id_raw and tesvik_id_raw.isdigit():
            tesvik_id = int(tesvik_id_raw)
            print(f"📌 Formdaki tesvik_id kullanılıyor: {tesvik_id}")

        elif session.get("current_tesvik_id"):
            tesvik_id = session["current_tesvik_id"]
            print(f"📌 Session’daki mevcut tesvik_id kullanılıyor: {tesvik_id}")

    belge_no = request.form.get("belge_no") \
         or request.form.get("belge_no_hidden") \
         or "(otomatik)"
         
    belge_tarihi = request.form.get("belge_tarihi") \
               or request.form.get("belge_tarihi_hidden") \
               or ""

    bolge = request.form.get("bolge") \
            or request.form.get("bolge_hidden")

    if tesvik_id is None and belge_no and belge_no != "(otomatik)":
        with get_conn() as conn0:
            c0 = conn0.cursor()
            c0.execute("""
                SELECT id
                FROM tesvik_belgeleri
                WHERE user_id=%s AND mukellef_id=%s AND belge_no=%s
            """, (user_id, mukellef_id, belge_no))
            row0 = c0.fetchone()
            if row0:
                tesvik_id = row0["id"]
                print(f"🔄 Belge no ile mevcut ID bulundu: {tesvik_id}")

    print("🎯 SON KULLANILACAK TESVIK ID =", tesvik_id)

    # ---------------------------------------------------
    #        🔢 2) SAYISAL PARSER
    # ---------------------------------------------------
    def parse_amount(field):
        s = (request.form.get(field) or "0").replace(".", "").replace(",", ".")
        try:
            return float(s)
        except:
            return 0.0

    # ---------------------------------------------------
    #        📄 3) FORM ALANLARI
    # ---------------------------------------------------

    karar = request.form.get("karar")
    program_turu = request.form.get("program_turu") or ""
    yatirim_turu1 = request.form.get("yatirim_turu1")
    yatirim_turu2 = request.form.get("yatirim_turu2")
    vize_durumu = request.form.get("vize_durumu")
    donem = request.form.get("donem")
    il = request.form.get("il")
    osb = request.form.get("osb")


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

    # ---------------------------------------------------
    #        🔔 YENİ: HATA AYIKLAMA İÇİN LOGLAMA 🔔
    # ---------------------------------------------------
    # Hata anında tüm bu değişkenlerin değerlerini konsola yazdırır.
    log_vars = {
        'tesvik_id': tesvik_id, 'user_id': user_id, 'mukellef_id': mukellef_id, 
        'karar': karar, 'belge_no': belge_no, 'toplam_tutar': toplam_tutar, 
        'katki_orani': katki_orani, 'vergi_orani': vergi_orani, 'belge_tarihi': belge_tarihi,
        'vize_durumu': vize_durumu, 'cari_toplam_katki': cari_toplam_katki, 'brut_satis': brut_satis,
        'program_turu': program_turu, 'il': il, 'osb': osb, 'bolge': bolge
        # Diğer kritik alanları buraya ekleyebilirsiniz
    }
    # ---------------------------------------------------

    # ---------------------------------------------------
    #        💾 4) KAYDET / GÜNCELLE  (TRY–EXCEPT TAM!)
    # ---------------------------------------------------
    with get_conn() as conn:
        c = conn.cursor()

        try:
            if tesvik_id:
                # ------------------ UPDATE ------------------
                # 🔥 KRİTİK: UPDATE sorgusuna RETURNING id ekle (Hata kontrolü için)
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
                        brut_satis=%s, ihracat=%s, imalat=%s, diger_faaliyet=%s, use_detailed_profit_ratios=%s, olusturan_id=%s
                    WHERE id=%s AND user_id=%s AND mukellef_id=%s
                    RETURNING id
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
                    brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios, user_id,
                    tesvik_id, user_id, mukellef_id
                ))
                
                row = c.fetchone()
                if not row and c.rowcount == 0:
                    # KRİTİK KONTROL: Eğer güncelleme 0 satırı etkilediyse, bu hatayı fırlatırız.
                    raise Exception(f"UPDATE başarısız: ID={tesvik_id}, User={user_id}, Mukellef={mukellef_id} için eşleşen kayıt bulunamadı.")

                session["current_tesvik_id"] = tesvik_id
                conn.commit()
                print(f"✅ Belge ID {tesvik_id} başarıyla güncellendi.")

            else:
                # ------------------ INSERT ------------------
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
                        brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios, olusturan_id
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
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
                    brut_satis, ihracat, imalat, diger_faaliyet, use_detailed_profit_ratios, user_id
                ))

                row = c.fetchone()
                if not row:
                    raise Exception("INSERT başarılı fakat RETURNING id boş döndü!")

                tesvik_id = row["id"]
                session["current_tesvik_id"] = tesvik_id
                conn.commit()

        except Exception as e:
            conn.rollback()
            # 🔔 KRİTİK LOGLAMA: Hata izini ve değişkenleri konsola yazdır
            print("-" * 50)
            print(f"❌ KAYIT BAŞARISIZ! Tespit Edilen Hata: {repr(e)}")
            print(f"❌ Hataya Neden Olan Değişkenler: {log_vars}")
            print("-" * 50)
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "title": "Kayıt Hatası!",
                "message": f"Veritabanı hatası oluştu. Logları kontrol ediniz. Detay: {repr(e).splitlines()[0]}"
            })

    # -------------------------------------
    #  Sonuç
    # -------------------------------------
    return jsonify({
        "status": "success",
        "title": "Başarılı!",
        "message": "Teşvik belgesi kaydedildi.",
        "tesvik_id": tesvik_id
    })






def get_all_tesvik_docs(user_id: int, mukellef_id: int = None):
    """Kullanıcının teşvik belgelerini ve dönemlerini döndürür."""
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 🔹 1) Eğer mükellef filtresi varsa ona göre çek
        if mukellef_id:
            c.execute("""
                SELECT *
                FROM tesvik_belgeleri
                WHERE user_id = %s AND mukellef_id = %s
                ORDER BY id DESC
            """, (user_id, mukellef_id))
        else:
            c.execute("""
                SELECT *
                FROM tesvik_belgeleri
                WHERE user_id = %s
                ORDER BY id DESC
            """, (user_id,))

        docs = c.fetchall()
        if not docs:
            return []

        # 🔹 2) Her belgeye dönem listesini ekle
        for d in docs:
            belge_no = d["belge_no"]

            c.execute("""
                SELECT hesap_donemi, donem_turu
                FROM tesvik_kullanim
                WHERE user_id = %s AND belge_no = %s
                ORDER BY hesap_donemi ASC
            """, (user_id, belge_no))

            d["donemler"] = c.fetchall() or []

        return docs







@bp.route('/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_tesvik(doc_id):
    """Bir teşvik belgesini ve ona bağlı dönem kayıtlarını güvenli şekilde siler."""
    user_id = session.get("user_id")

    with get_conn() as conn:
        c = conn.cursor()

        try:
            # ----------------------------------------------------------
            # 1) Belge gerçekten bu kullanıcıya mı ait? Güvenlik kontrolü
            # ----------------------------------------------------------
            c.execute("""
                SELECT belge_no
                FROM tesvik_belgeleri
                WHERE id=%s AND user_id=%s
            """, (doc_id, user_id))

            row = c.fetchone()
            if not row:
                return jsonify({
                    "status": "error",
                    "title": "Yetki Hatası",
                    "message": "Bu belge size ait değil veya bulunamadı."
                }), 403

            belge_no = row["belge_no"]

            # ----------------------------------------------------------
            # 2) Eğer silinen belge aktif seçili belgemizse -> session temizle
            # ----------------------------------------------------------
            if session.get("current_tesvik_id") == doc_id:
                session.pop("current_tesvik_id", None)

            # ----------------------------------------------------------
            # 3) Önce dönem kayıtlarını sil
            # ----------------------------------------------------------
            c.execute("""
                DELETE FROM tesvik_kullanim
                WHERE user_id=%s AND belge_no=%s
            """, (user_id, belge_no))

            # ----------------------------------------------------------
            # 4) Sonra belgenin kendisini sil
            # ----------------------------------------------------------
            c.execute("""
                DELETE FROM tesvik_belgeleri
                WHERE id=%s AND user_id=%s
            """, (doc_id, user_id))

            conn.commit()

            return jsonify({
                "status": "success",
                "title": "Silindi!",
                "message": "Belge ve tüm dönem kayıtları başarıyla silindi."
            })

        except Exception as e:
            conn.rollback()
            print(f"❌ Belge silme hatası: {e}")
            return jsonify({
                "status": "error",
                "title": "Hata!",
                "message": f"Silme sırasında hata oluştu: {str(e)}"
            }), 500


@bp.route("/tesvik/pdf/<int:doc_id>")
@login_required
def download_tesvik_pdf(doc_id):
    user_id = session.get("user_id")

    # 1️⃣ Belgeyi DB'den Çek
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT *
            FROM tesvik_belgeleri
            WHERE id = %s AND user_id = %s
        """, (doc_id, user_id))

        row = c.fetchone()

    if not row:
        return jsonify({
            "status": "error",
            "title": "Bulunamadı",
            "message": "Teşvik belgesi bulunamadı."
        }), 404

    # 🟢 Dict → Namespace
    data = SimpleNamespace(**row)

    # 2️⃣ wkhtmltopdf Yolu
    wkhtml_path = (
        current_app.config.get("WKHTMLTOPDF_PATH")
        or shutil.which("wkhtmltopdf")
    )

    if not wkhtml_path:
        return jsonify({
            "status": "error",
            "title": "Eksik Araç",
            "message": "wkhtmltopdf bulunamadı. Sunucu yapılandırmasını kontrol edin."
        }), 500

    config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

    # 3️⃣ HTML Oluştur
    try:
        rendered_html = render_template(
            "kv_tablosu_pdf.html",
            data=data,
            now=datetime.now
        )
    except Exception as e:
        return jsonify({
            "status": "error",
            "title": "Şablon Hatası",
            "message": f"PDF HTML şablonu oluşturulamadı: {e}"
        }), 500

    # 4️⃣ Geçici PDF Dosyası (otomatik silinecek)
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:

            pdfkit.from_string(
                rendered_html,
                tmpfile.name,
                configuration=config,
                options={
                    "page-size": "A4",
                    "encoding": "UTF-8",
                    "enable-local-file-access": "",
                    "margin-top": "15mm",
                    "margin-bottom": "15mm",
                    "margin-left": "12mm",
                    "margin-right": "12mm",
                    "dpi": 300,
                },
            )

            tmp_path = tmpfile.name

    except Exception as e:
        print("❌ PDF oluşturma hatası:", e)
        return jsonify({
            "status": "error",
            "title": "PDF Hatası",
            "message": str(e)
        }), 500

    # 5️⃣ PDF Döndür ve sonra dosyayı sil
    try:
        filename = f"tesvik_{data.belge_no or doc_id}.pdf"
        response = send_file(
            tmp_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
    finally:
        try:
            os.remove(tmp_path)
        except:
            pass

    return response

        
    
    
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
    Her hesap dönemi için teşvik kullanım kaydını oluşturur veya günceller. 
    Bu fonksiyon, sadece tesvik_kullanim tablosuna ait sütunları kullanır.
    """
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"status": "error", "message": "Oturum bulunamadı."}), 401

        data = request.get_json(force=True)

        belge_no = data.get("belge_no")
        hesap_donemi = int(data.get("hesap_donemi"))
        donem_turu = data.get("donem_turu", "KURUMLAR")

        if not belge_no:
            return jsonify({"status": "error", "message": "Belge no eksik."}), 400
        
        # ⚠️ TABLO ŞEMANIZDA KESİNLİKLE VAR OLAN SÜTUNLAR İLE EŞLEŞTİRİLDİ
        # Hata veren 'onceki_yatirim_katki_tutari', 'onceki_katki_tutari' gibi alanlar çıkarıldı.
        # Bunlar formda gösterilse bile tesvik_kullanim tablonuzda tanımlı değildir.
        fields = [
            # Kazanç Tipleri (init_db'de mevcut)
            "yatirimdan_elde_edilen_kazanc",
            "tevsi_yatirim_kazanci",
            "diger_faaliyet", 
            
            # Cari Dönem Katkıları (init_db'de mevcut)
            "cari_yatirim_katki",
            "cari_diger_katki",
            "cari_toplam_katki",
            
            # Genel Sonuçlar (init_db'de mevcut)
            "genel_toplam_katki",
            "kalan_katki_tutari", # init_db'de var
            
            # İndirimli KV Bilgileri (init_db'de mevcut)
            "indirimli_matrah", 
            "indirimli_kv", 
            "indirimli_kv_oran",
            
            # NOT: Frontend'den gelen 'kalan_katki' ve Aşama 4 verileri 
            # (onceki_yatirim_katki_tutari, endeks_katki_tutari) bu listeden çıkarıldı,
            # çünkü tablo şemasında bu sütunlar yok. Sadece güvenli olanları tutuyoruz.
        ]
        
        # EK KONTROL: Eğer Frontend'den 'kalan_katki' ve 'kalan_katki_tutari' farklı isimlerle geliyorsa
        # ve her ikisi de tabloda yoksa, en az hata verecek olan 'kalan_katki_tutari' tercih edilir.
        # Ancak buradaki listeye sadece 'kalan_katki_tutari' dahil edilmiştir (init_db'de olduğu için).
        
        # Sayısal değerleri çek ve sadece fields listesindekileri kullan
        values = [float(data.get(f, 0)) for f in fields]

        with get_conn() as conn:
            cur = conn.cursor()

            # SQL sorgusu, sadece tabloda var olan sütunları kullanır.
            cur.execute(f"""
                INSERT INTO tesvik_kullanim (
                    user_id, belge_no, hesap_donemi, donem_turu,
                    {", ".join(fields)}
                )
                VALUES (
                    %s, %s, %s, %s,
                    {", ".join(["%s"] * len(fields))}
                )
                ON CONFLICT (user_id, belge_no, hesap_donemi, donem_turu)
                DO UPDATE SET
                    {", ".join([f"{col} = EXCLUDED.{col}" for col in fields])},
                    kayit_tarihi = CURRENT_TIMESTAMP;
            """, (user_id, belge_no, hesap_donemi, donem_turu, *values))

            conn.commit()

        return jsonify({
            "status": "success",
            "title": "Kayıt Başarılı",
            "message": f"{belge_no} ({hesap_donemi} - {donem_turu}) dönem kaydedildi."
        })

    except Exception as e:
        print("save_tesvik_kullanim hatası:", e)
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "status": "error",
            "title": "Kayıt Hatası",
            "message": str(e)
        }), 500
        
        
        
        
@bp.route("/clone_tesvik_donem", methods=["POST"])
@login_required
def clone_tesvik_donem():
    """Yeni dönem ekler. Eğer önceki dönem varsa değerler klonlanır, yoksa sıfırdan açılır."""
    try:
        user_id = session.get("user_id")
        data = request.get_json(force=True)

        belge_no = data.get("belge_no")
        donem_text = (data.get("donem_text") or "").strip()

        if not belge_no or not donem_text:
            return jsonify({
                "status": "error",
                "title": "Eksik Bilgi",
                "message": "Belge numarası veya dönem bilgisi eksik."
            }), 400

        # ======================================================
        # 🧠 Dönem ayrıştırma (2025 - Kurumlar)
        # ======================================================
        import re
        match = re.match(r"(\d{4})\s*-\s*(.+)", donem_text)

        if match:
            hesap_donemi = int(match.group(1))
            donem_turu = match.group(2).strip()
        else:
            hesap_donemi = datetime.now().year
            donem_turu = "KURUMLAR"

        donem_turu = donem_turu.upper()

        # ======================================================
        # 🔍 Önceki dönem değerlerini çek
        # ======================================================
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Sadece tesvik_kullanim tablosunda KESİN var olan kolonlar seçiliyor
            clone_fields = [
                "yatirimdan_elde_edilen_kazanc",
                "tevsi_yatirim_kazanci",
                "diger_faaliyet",
                "cari_yatirim_katki",
                "cari_diger_katki",
                "cari_toplam_katki",
                "genel_toplam_katki",
                "kalan_katki_tutari"
            ]

            cur.execute(f"""
                SELECT {", ".join(clone_fields)}
                FROM tesvik_kullanim
                WHERE user_id = %s 
                  AND belge_no = %s
                ORDER BY hesap_donemi DESC, donem_turu DESC
                LIMIT 1
            """, (user_id, belge_no))

            prev = cur.fetchone()
            
            # Önceki değerleri al, yoksa varsayılan 0 kullan
            if prev:
                # Klonlama mantığı: Önceki dönemden sadece kalan katkı tutarını alıp 
                # diğer cari katkıları sıfırlamak isteyebilirsiniz. 
                # Ancak burada basit klonlama mantığı korundu.
                prev_vals = [prev.get(k, 0) for k in clone_fields]
            else:
                prev_vals = [0.0] * len(clone_fields)

            # ======================================================
            # ➕ Yeni dönem ekle
            # ======================================================
            cur.execute(f"""
                INSERT INTO tesvik_kullanim (
                    user_id, belge_no, hesap_donemi, donem_turu,
                    {", ".join(clone_fields)}
                )
                VALUES (
                    %s, %s, %s, %s,
                    {", ".join(["%s"]*len(clone_fields))}
                )
                ON CONFLICT (user_id, belge_no, hesap_donemi, donem_turu) 
                DO NOTHING;
            """, (user_id, belge_no, hesap_donemi, donem_turu, *prev_vals))

            conn.commit()

        return jsonify({
            "status": "success",
            "title": "Yeni Dönem Eklendi",
            "message": f"{belge_no} ({hesap_donemi} - {donem_turu}) dönemi başarıyla oluşturuldu."
        })

    except Exception as e:
        # Benzersizlik hatası varsa (PostgreSQL/SQLite)
        if 'duplicate key' in str(e) or 'UNIQUE constraint' in str(e):
             return jsonify({
                "status": "warning",
                "title": "Kayıt Mevcut",
                "message": f"{belge_no} ({donem_text}) dönemi zaten eklenmiş."
            }), 409 # Conflict
             
        print("⚠️ clone_tesvik_donem hata:", e)
        return jsonify({
            "status": "error",
            "title": "Hata",
            "message": str(e)
        }), 500





@bp.route("/delete_tesvik_donem", methods=["POST"])
@login_required
def delete_tesvik_donem():
    """Belirli bir belge + hesap dönemi + dönem türü kaydını siler."""
    try:
        user_id = session.get("user_id")
        data = request.get_json(force=True)

        belge_no = data.get("belge_no")
        # Gelen veriyi güvenli bir şekilde tam sayıya dönüştürme
        hesap_donemi = int(data.get("hesap_donemi")) 
        donem_turu = (data.get("donem_turu") or "").strip().upper()

        if not belge_no or not hesap_donemi:
            return jsonify({
                "status": "error",
                "title": "Eksik Bilgi",
                "message": "Belge numarası veya dönem bilgisi eksik."
            }), 400

        if not donem_turu:
            return jsonify({
                "status": "error",
                "title": "Eksik Bilgi",
                "message": "Dönem türü eksik."
            }), 400

        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("""
                DELETE FROM tesvik_kullanim
                WHERE user_id = %s 
                  AND belge_no = %s
                  AND hesap_donemi = %s
                  AND UPPER(donem_turu) = %s
            """, (user_id, belge_no, hesap_donemi, donem_turu))

            # Kaç satırın silindiğini kontrol etmek isterseniz (opsiyonel)
            row_count = cur.rowcount
            conn.commit()

        if row_count == 0:
            return jsonify({
                "status": "warning",
                "title": "Silme Başarısız",
                "message": "Belirtilen dönem kaydı bulunamadı."
            })
            
        return jsonify({
            "status": "success",
            "title": "Silindi",
            "message": f"{belge_no} ({hesap_donemi} - {donem_turu}) dönemi başarıyla silindi."
        })

    except ValueError:
        # Hesap döneminin int'e çevrilememesi gibi hataları yakalar
        return jsonify({
            "status": "error",
            "title": "Veri Hatası",
            "message": "Hesap dönemi geçerli bir sayı olmalıdır."
        }), 400
        
    except Exception as e:
        print(f"⚠️ delete_tesvik_donem hata: {e}")
        return jsonify({
            "status": "error",
            "title": "Silme Hatası",
            "message": str(e)
        }), 500





def _fetch_and_prepare_kullanim(user_id, belge_no, yil, turu):
    """ Veritabanından belirli bir döneme ait tesvik_kullanim verilerini çeker. """
    turu_upper = turu.upper().replace('%20', ' ').replace('%C4%B0', 'İ').replace('%C3%87', 'Ç') 

    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 1. Belge ID'sini bul
        cur.execute("SELECT id FROM tesvik_belgeleri WHERE user_id = %s AND belge_no = %s", (user_id, belge_no))
        belge_row = cur.fetchone()
        if not belge_row:
            return None, None
        tesvik_id = belge_row["id"]

        # 2. Dönem kullanım verilerini çek
        cur.execute("""
            SELECT *
            FROM tesvik_kullanim
            WHERE user_id = %s AND belge_no = %s AND hesap_donemi = %s AND UPPER(donem_turu) = %s
        """, (user_id, belge_no, yil, turu_upper))
        kullanim_verisi = cur.fetchone()

    return kullanim_verisi, tesvik_id


@bp.route("/edit_tesvik_kullanim/<belge_no>/<int:yil>/<turu>")
@login_required
def edit_tesvik_kullanim(belge_no, yil, turu):
    """
    Bir teşvik belgesine ait dönem seçildiğinde form ekranına yönlendirir ve DÖNEM VERİLERİNİ yükler.
    """
    user_id = session.get("user_id")
    
    kullanim_verisi, tesvik_id = _fetch_and_prepare_kullanim(user_id, belge_no, yil, turu)

    if not kullanim_verisi:
        flash("Dönem kaydı veya belge bulunamadı.", "warning")
        return redirect(url_for("indirimlikurumlar.index", sekme="tesvik"))

    # Session doldurma (Aynı kalır)
    session["current_belge_no"] = belge_no
    session["current_hesap_donemi"] = yil
    session["current_donem_turu"] = turu
    session["current_tesvik_id"] = tesvik_id 

    for key, value in kullanim_verisi.items():
        if key not in ['user_id', 'belge_no', 'hesap_donemi', 'donem_turu', 'kayit_tarihi']:
            if value is not None:
                session[f"form_{key}"] = str(value)
            else:
                session.pop(f"form_{key}", None)

    # Form ekranına yönlendir
    return redirect(f"/indirimlikurumlar/?sekme=form&view={tesvik_id}&editdonem=1")



@bp.route("/api/get_tesvik_kullanim/<belge_no>/<int:yil>/<turu>")
@login_required
def get_tesvik_kullanim_data(belge_no, yil, turu):
    """ Dönemler sayfasındaki modal için verileri çeker (AJAX). """
    from flask import jsonify, current_app 
    
    user_id = session.get("user_id")
    
    # 1. Yardımcı fonksiyonu çağır
    kullanim_verisi, tesvik_id = _fetch_and_prepare_kullanim(user_id, belge_no, yil, turu)
    
    # 2. turu_upper'ı doğrudan _fetch_and_prepare_kullanim içindeki mantığa uygun olarak ayarla
    # Böylece HTML'e göndermek için doğru formatı kullanabiliriz.
    turu_display = turu.upper().replace('%20', ' ').replace('%C4%B0', 'İ').replace('%C3%87', 'Ç')
    
    

    if not kullanim_verisi:
        return jsonify({
            "status": "warning", 
            "message": f"{yil} - {turu} dönemine ait kullanım kaydı bulunamadı.",
            "html": "Detay bulunamadı."
        }), 200

    # Veriyi HTML formatına hazırla (Detay Modal için)
    html_content = f"""
    <h5>Belge No: {belge_no} | Dönem: {yil} - {turu_display}</h5>
    <table class="table table-sm table-bordered">
        <thead><th>Açıklama</th><th>Tutar (TL)</th></thead>
        <tbody>
        """
    
    for key, value in kullanim_verisi.items():
        if isinstance(value, (float, int)) and value != 0 and key not in ['id', 'user_id']:
            formatted_value = f"{value:,.2f} TL".replace(',', 'X').replace('.', ',').replace('X', '.')
            clean_key = key.replace('_', ' ').title().replace('Kv', 'KV').replace('Tutari', 'Tutarı')
            
            html_content += f"""
            <tr>
                <td>{clean_key}</td>
                <td>{formatted_value}</td>
            </tr>
            """
    
    html_content += """
        </tbody>
    </table>
    """
    
    return jsonify({
        "status": "success",
        "html": html_content
    }), 200

# ----------------------------------------------------
# 🗑️ SİLME İŞLEMLERİ (YENİ EKLENEN)
# ----------------------------------------------------

@bp.route("/tesvik_sil/<int:id>", methods=["POST"])
@login_required
def tesvik_sil(id):
    """
    Teşvik belgesini ve ona bağlı tüm dönem kullanım kayıtlarını siler.
    """
    user_id = session.get("user_id")
    mukellef_id = session.get("aktif_mukellef_id")

    try:
        if not user_id:
             return jsonify({"status": "error", "message": "Oturum süresi dolmuş."}), 401

        with get_conn() as conn:
            c = conn.cursor()
            
            # Öncelikle belgenin bu kullanıcıya ve aktif mükellefe ait olup olmadığını kontrol et
            c.execute("""
                SELECT id, belge_no FROM tesvik_belgeleri 
                WHERE id = %s AND user_id = %s
            """, (id, user_id))
            
            row = c.fetchone()
            if not row:
                return jsonify({
                    "status": "error",
                    "message": "Silinecek belge bulunamadı veya yetkiniz yok."
                }), 404

            del_id, belge_no = row
            
            # 1. Bağlı Kullanım Kayıtlarını Sil (belge_no ile bağlılarsa)
            if belge_no:
                 c.execute("""
                    DELETE FROM tesvik_kullanim 
                    WHERE belge_no = %s AND user_id = %s
                """, (belge_no, user_id))

            # 2. Belgeyi Sil
            c.execute("DELETE FROM tesvik_belgeleri WHERE id = %s", (id,))
            
            conn.commit()
            print(f"🗑️ Teşvik Belgesi Silindi: ID={id}, BelgeNo={belge_no}")

        return jsonify({
            "status": "success",
            "message": "Teşvik belgesi ve tüm bağlı kayıtları başarıyla silindi."
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Silme işlemi başarısız: {str(e)}"
        }), 500


@bp.route("/delete_tesvik_kullanim/<int:id>", methods=["POST"])
@login_required
def delete_tesvik_kullanim(id):
    """
    Tekil bir dönem kullanım kaydını siler.
    """
    user_id = session.get("user_id")

    try:
        with get_conn() as conn:
            c = conn.cursor()
            
            # Kaydın varlığını kontrol et
            c.execute("SELECT id FROM tesvik_kullanim WHERE id = %s AND user_id = %s", (id, user_id))
            if not c.fetchone():
                return jsonify({
                    "status": "error",
                    "message": "Silinecek dönem kaydı bulunamadı."
                }), 404

            # Sil
            c.execute("DELETE FROM tesvik_kullanim WHERE id = %s", (id,))
            conn.commit()
            print(f"🗑️ Teşvik Kullanım Dönemi Silindi: ID={id}")

        return jsonify({
            "status": "success",
            "message": "Dönem kaydı başarıyla silindi."
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Silme işlemi başarısız: {str(e)}"
        }), 500
