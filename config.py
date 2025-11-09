# config.py
import os


# Ortam değişkenlerinden oku
SECRET_KEY = os.getenv("SECRET_KEY")
FERNET_KEY = os.getenv("FERNET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# İzin verilen dosya uzantıları
ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "xls"}

# wkhtmltopdf çalıştırılabilir yolu (PDF oluşturma)
WKHTMLTOPDF_PATH = os.getenv("WKHTMLTOPDF_PATH") or "/usr/local/bin/wkhtmltopdf"

# Maksimum yükleme boyutu (bayt cinsinden)
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB


# --------------------------------------
# İndirimli Kurumlar Modülü Sabitleri
# --------------------------------------

# Türkiye illeri
ILLER = [
    "Ankara", "İstanbul", "İzmir", "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray",
    "Amasya", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman",
    "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Bozcaada ve Gökçeada İlçeleri", "Burdur",
    "Bursa", "Çanakkale (Bozcaada ve Gökçeada İlçeleri Hariç)", "Çankırı", "Çorum", "Denizli",
    "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep",
    "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "Kahramanmaraş", "Karabük",
    "Karaman", "Kars", "Kastamonu", "Kayseri", "Kırıkkale", "Kırklareli", "Kırşehir", "Kilis",
    "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş",
    "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop",
    "Sivas", "Şanlıurfa", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van",
    "Yalova", "Yozgat", "Zonguldak"
]

# İl -> Bölge haritası
BOLGE_MAP = {
    "Ankara": "1. Bölge",
    "İstanbul": "1. Bölge",
    "İzmir": "1. Bölge",
    "Adana": "2. Bölge",
    "Adıyaman": "5. Bölge",
    "Afyonkarahisar": "4. Bölge",
    "Ağrı": "6. Bölge",
    "Aksaray": "5. Bölge",
    "Amasya": "4. Bölge",
    "Antalya": "1. Bölge",
    "Ardahan": "6. Bölge",
    "Artvin": "4. Bölge",
    "Aydın": "2. Bölge",
    "Balıkesir": "3. Bölge",
    "Bartın": "4. Bölge",
    "Batman": "6. Bölge",
    "Bayburt": "5. Bölge",
    "Bilecik": "3. Bölge",
    "Bingöl": "6. Bölge",
    "Bitlis": "6. Bölge",
    "Bolu": "2. Bölge",
    "Bozcaada ve Gökçeada İlçeleri": "6. Bölge",
    "Burdur": "3. Bölge",
    "Bursa": "1. Bölge",
    "Çanakkale (Bozcaada ve Gökçeada İlçeleri Hariç)": "2. Bölge",
    "Çankırı": "5. Bölge",
    "Çorum": "4. Bölge",
    "Denizli": "2. Bölge",
    "Diyarbakır": "6. Bölge",
    "Düzce": "4. Bölge",
    "Edirne": "2. Bölge",
    "Elazığ": "4. Bölge",
    "Erzincan": "4. Bölge",
    "Erzurum": "5. Bölge",
    "Eskişehir": "1. Bölge",
    "Gaziantep": "3. Bölge",
    "Giresun": "5. Bölge",
    "Gümüşhane": "5. Bölge",
    "Hakkari": "6. Bölge",
    "Hatay": "4. Bölge",
    "Iğdır": "6. Bölge",
    "Isparta": "2. Bölge",
    "Kahramanmaraş": "5. Bölge",
    "Karabük": "3. Bölge",
    "Karaman": "3. Bölge",
    "Kars": "6. Bölge",
    "Kastamonu": "4. Bölge",
    "Kayseri": "2. Bölge",
    "Kırıkkale": "4. Bölge",
    "Kırklareli": "2. Bölge",
    "Kırşehir": "4. Bölge",
    "Kilis": "5. Bölge",
    "Kocaeli": "1. Bölge",
    "Konya": "2. Bölge",
    "Kütahya": "4. Bölge",
    "Malatya": "4. Bölge",
    "Manisa": "3. Bölge",
    "Mardin": "6. Bölge",
    "Mersin": "3. Bölge",
    "Muğla": "1. Bölge",
    "Muş": "6. Bölge",
    "Nevşehir": "4. Bölge",
    "Niğde": "5. Bölge",
    "Ordu": "5. Bölge",
    "Osmaniye": "5. Bölge",
    "Rize": "4. Bölge",
    "Sakarya": "2. Bölge",
    "Samsun": "3. Bölge",
    "Siirt": "6. Bölge",
    "Sinop": "5. Bölge",
    "Sivas": "4. Bölge",
    "Şanlıurfa": "6. Bölge",
    "Şırnak": "6. Bölge",
    "Tekirdağ": "2. Bölge",
    "Tokat": "5. Bölge",
    "Trabzon": "3. Bölge",
    "Tunceli": "5. Bölge",
    "Uşak": "3. Bölge",
    "Van": "6. Bölge",
    "Yalova": "2. Bölge",
    "Yozgat": "5. Bölge",
    "Zonguldak": "3. Bölge",
}

BOLGE_MAP_9903 = {
    # 1. Bölge
    "Ankara": "1. Bölge", "Antalya": "1. Bölge", "Bursa": "1. Bölge",
    "Eskişehir": "1. Bölge", "İstanbul": "1. Bölge", "İzmir": "1. Bölge",
    "Kocaeli": "1. Bölge", "Muğla": "1. Bölge",
    
    # 2. Bölge
    "Aydın": "2. Bölge", "Balıkesir": "2. Bölge", "Bolu": "2. Bölge",
    "Çanakkale": "2. Bölge", "Denizli": "2. Bölge", "Edirne": "2. Bölge",
    "Kayseri": "2. Bölge", "Konya": "2. Bölge", "Manisa": "2. Bölge",
    "Mersin": "2. Bölge", "Sakarya": "2. Bölge", "Tekirdağ": "2. Bölge",
    "Yalova": "2. Bölge",
    
    # 3. Bölge
    "Adana": "3. Bölge", "Bilecik": "3. Bölge", "Burdur": "3. Bölge",
    "Düzce": "3. Bölge", "Gaziantep": "3. Bölge", "Isparta": "3. Bölge",
    "Karabük": "3. Bölge", "Karaman": "3. Bölge", "Kırıkkale": "3. Bölge",
    "Kırklareli": "3. Bölge", "Kütahya": "3. Bölge", "Nevşehir": "3. Bölge",
    "Rize": "3. Bölge", "Samsun": "3. Bölge", "Trabzon": "3. Bölge",
    "Uşak": "3. Bölge", "Zonguldak": "3. Bölge",
    
    # 4. Bölge
    "Afyonkarahisar": "4. Bölge", "Aksaray": "4. Bölge", "Amasya": "4. Bölge",
    "Artvin": "4. Bölge", "Çorum": "4. Bölge", "Elazığ": "4. Bölge",
    "Erzincan": "4. Bölge", "Kastamonu": "4. Bölge", "Kırşehir": "4. Bölge",
    "Malatya": "4. Bölge", "Sivas": "4. Bölge",
    
    # 5. Bölge
    "Bartın": "5. Bölge", "Bayburt": "5. Bölge", "Çankırı": "5. Bölge",
    "Erzurum": "5. Bölge", "Giresun": "5. Bölge", "Hatay": "5. Bölge",
    "Kahramanmaraş": "5. Bölge", "Kilis": "5. Bölge", "Niğde": "5. Bölge",
    "Ordu": "5. Bölge", "Osmaniye": "5. Bölge", "Sinop": "5. Bölge",
    "Tokat": "5. Bölge", "Tunceli": "5. Bölge", "Yozgat": "5. Bölge",
    
    # 6. Bölge
    "Adıyaman": "6. Bölge", "Ağrı": "6. Bölge", "Ardahan": "6. Bölge",
    "Batman": "6. Bölge", "Bingöl": "6. Bölge", "Bitlis": "6. Bölge",
    "Diyarbakır": "6. Bölge", "Gümüşhane": "6. Bölge", "Hakkari": "6. Bölge",
    "Iğdır": "6. Bölge", "Kars": "6. Bölge", "Mardin": "6. Bölge",
    "Muş": "6. Bölge", "Siirt": "6. Bölge", "Şanlıurfa": "6. Bölge",
    "Şırnak": "6. Bölge", "Van": "6. Bölge",
}

# Teşvik katkı oranları
TESVIK_KATKILAR = {
    ("1. Bölge", "OSB İçinde"): 20, ("1. Bölge", "OSB Dışında"): 15,
    ("2. Bölge", "OSB İçinde"): 25, ("2. Bölge", "OSB Dışında"): 20,
    ("3. Bölge", "OSB İçinde"): 30, ("3. Bölge", "OSB Dışında"): 25,
    ("4. Bölge", "OSB İçinde"): 35, ("4. Bölge", "OSB Dışında"): 30,
    ("5. Bölge", "OSB İçinde"): 40, ("5. Bölge", "OSB Dışında"): 40,
    ("6. Bölge", "OSB İçinde"): 50, ("6. Bölge", "OSB Dışında"): 50,
}

# Teşvik vergi oranları
TESVIK_VERGILER = {
    ("1. Bölge", "OSB İçinde"): 55, ("1. Bölge", "OSB Dışında"): 50,
    ("2. Bölge", "OSB İçinde"): 60, ("2. Bölge", "OSB Dışında"): 55,
    ("3. Bölge", "OSB İçinde"): 70, ("3. Bölge", "OSB Dışında"): 60,
    ("4. Bölge", "OSB İçinde"): 80, ("4. Bölge", "OSB Dışında"): 70,
    ("5. Bölge", "OSB İçinde"): 90, ("5. Bölge", "OSB Dışında"): 80,
    ("6. Bölge", "OSB İçinde"): 90, ("6. Bölge", "OSB Dışında"): 90,
}

TESVIK_KATKILAR_9903 = {
    "Teknoloji Hamlesi Programı": 50,
    "Yerel Kalkınma Hamlesi Programı": 50,
    "Stratejik Hamle Programı": 40,
    "Öncelikli Yatırımlar Teşvik Sistemi": 30,
    "Hedef Yatırımlar Teşvik Sistemi": 20,
}



tarifeler = {
    2020: {
        "normal": [
            (0, 0, 0.15),
            (22000, 3300, 0.20),
            (49000, 8700, 0.27),
            (120000, 27870, 0.35),
            (600000, 195870, 0.40)
        ],
        "ucret": [
            (0, 0, 0.15),
            (22000, 3300, 0.20),
            (49000, 8700, 0.27),
            (180000, 44070, 0.35),
            (600000, 191070, 0.40)
        ]
    },
    2021: {
        "normal": [
            (0, 0, 0.15),
            (24000, 3600, 0.20),
            (53000, 9400, 0.27),
            (130000, 30190, 0.35),
            (650000, 212190, 0.40)
        ],
        "ucret": [
            (0, 0, 0.15),
            (24000, 3600, 0.20),
            (53000, 9400, 0.27),
            (190000, 46390, 0.35),
            (650000, 207390, 0.40)
        ]
    },
    2022: {
        "normal": [
            (0, 0, 0.15),
            (32000, 4800, 0.20),
            (70000, 12400, 0.27),
            (170000, 39400, 0.35),
            (880000, 287900, 0.40)
        ],
        "ucret": [
            (0, 0, 0.15),
            (32000, 4800, 0.20),
            (70000, 12400, 0.27),
            (250000, 61000, 0.35),
            (880000, 281500, 0.40)
        ]
    },
    2023: {
        "normal": [
            (0, 0, 0.15),
            (70000, 10500, 0.20),
            (150000, 26500, 0.27),
            (370000, 85900, 0.35),
            (1900000, 621400, 0.40)
        ],
        "ucret": [
            (0, 0, 0.15),
            (70000, 10500, 0.20),
            (150000, 26500, 0.27),
            (550000, 134500, 0.35),
            (1900000, 607000, 0.40)
        ]
    },
    2024: {
        "normal": [
            (0, 0, 0.15),
            (110000, 16500, 0.20),
            (230000, 40500, 0.27),
            (580000, 135000, 0.35),
            (3000000, 982000, 0.40)
        ],
        "ucret": [
            (0, 0, 0.15),
            (110000, 16500, 0.20),
            (230000, 40500, 0.27),
            (870000, 213300, 0.35),
            (3000000, 958800, 0.40)
        ]
    },
    2025: {
        "normal": [
            (0, 0, 0.15),
            (158000, 23700, 0.20),
            (330000, 58100, 0.27),
            (800000, 185000, 0.35),
            (4300000, 1410000, 0.40)
        ],
        "ucret": [
            (0, 0, 0.15),
            (158000, 23700, 0.20),
            (330000, 58100, 0.27),
            (1200000, 293000, 0.35),
            (4300000, 1378000, 0.40)
        ]
    }
}


asgari_ucretler = {
    2025: {
        "net": 22104.67,
        "istisnalar": {
            1: 3315.70, 2: 3315.70, 3: 3315.70, 4: 3315.70,
            5: 3315.70, 6: 3315.70, 7: 3315.70, 8: 4257.57,
            9: 4420.93, 10: 4420.93, 11: 4420.93, 12: 4420.93
        }
    },
    2024: {
        "net": 17002.12,
        "istisnalar": {
            1: 2550.32, 2: 2550.32, 3: 2550.32, 4: 2550.32,
            5: 2550.32, 6: 2550.32, 7: 3001.06, 8: 3400.42,
            9: 3400.42, 10: 3400.42, 11: 3400.42, 12: 3400.42
        }
    },
    2023: {
        "net": 11402.32,
        "istisnalar": {
            1: 1276.02, 2: 1276.02, 3: 1276.02, 4: 1276.02,
            5: 1276.02, 6: 1276.02, 7: 1710.35, 8: 1902.62,
            9: 2280.46, 10: 2280.46, 11: 2280.46, 12: 2280.46
        }
    },
    2022: {
        "net": 5500.35,
        "istisnalar": {
            1: 638.01, 2: 638.01, 3: 638.01, 4: 638.01,
            5: 638.01, 6: 638.01, 7: 825.05, 8: 1051.11,
            9: 1100.07, 10: 1100.07, 11: 1100.07, 12: 1100.07
        }
    }
}