export const ILLER = [
  "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin",
  "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
  "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum",
  "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir",
  "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kırıkkale", "Kırklareli", "Kırşehir",
  "Kilis", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş", "Nevşehir",
  "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Şanlıurfa", "Şırnak",
  "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"
];

export const BOLGE_MAP = {
  "Ankara": "1", "İstanbul": "1", "İzmir": "1", "Antalya": "1", "Bursa": "1", "Eskişehir": "1", "Kocaeli": "1", "Muğla": "1",
  "Adana": "2", "Aydın": "2", "Bolu": "2", "Çanakkale": "2", "Denizli": "2", "Edirne": "2", "Isparta": "2", "Kayseri": "2", "Kırklareli": "2", "Konya": "2", "Sakarya": "2", "Tekirdağ": "2", "Yalova": "2",
  "Balıkesir": "3", "Bilecik": "3", "Burdur": "3", "Gaziantep": "3", "Karabük": "3", "Karaman": "3", "Manisa": "3", "Mersin": "3", "Samsun": "3", "Trabzon": "3", "Uşak": "3", "Zonguldak": "3",
  "Afyonkarahisar": "4", "Amasya": "4", "Artvin": "4", "Bartın": "4", "Çorum": "4", "Düzce": "4", "Elazığ": "4", "Erzincan": "4", "Hatay": "4", "Kastamonu": "4", "Kırıkkale": "4", "Kırşehir": "4", "Kütahya": "4", "Malatya": "4", "Nevşehir": "4", "Rize": "4", "Sivas": "4",
  "Adıyaman": "5", "Aksaray": "5", "Bayburt": "5", "Çankırı": "5", "Erzurum": "5", "Giresun": "5", "Gümüşhane": "5", "Kahramanmaraş": "5", "Kilis": "5", "Niğde": "5", "Ordu": "5", "Osmaniye": "5", "Sinop": "5", "Tokat": "5", "Tunceli": "5", "Yozgat": "5",
  "Ağrı": "6", "Ardahan": "6", "Batman": "6", "Bingöl": "6", "Bitlis": "6", "Diyarbakır": "6", "Hakkari": "6", "Iğdır": "6", "Kars": "6", "Mardin": "6", "Muş": "6", "Siirt": "6", "Şanlıurfa": "6", "Şırnak": "6", "Van": "6"
};

// [Bölge, OSB Durumu]: Katkı Oranı
export const TESVIK_KATKILAR = {
  "1_var": 20, "1_yok": 15,
  "2_var": 25, "2_yok": 20,
  "3_var": 30, "3_yok": 25,
  "4_var": 35, "4_yok": 30,
  "5_var": 40, "5_yok": 40,
  "6_var": 50, "6_yok": 50,
};

// [Bölge, OSB Durumu]: Vergi İndirimi Oranı
export const TESVIK_VERGILER = {
  "1_var": 55, "1_yok": 50,
  "2_var": 60, "2_yok": 55,
  "3_var": 70, "3_yok": 60,
  "4_var": 80, "4_yok": 70,
  "5_var": 90, "5_yok": 80,
  "6_var": 90, "6_yok": 90,
};
export const BOLGE_MAP_9903 = {
  "Ankara": "1", "Antalya": "1", "Bursa": "1", "Eskişehir": "1", "İstanbul": "1", "İzmir": "1", "Kocaeli": "1", "Muğla": "1",
  "Aydın": "2", "Balıkesir": "2", "Bolu": "2", "Çanakkale": "2", "Denizli": "2", "Edirne": "2", "Kayseri": "2", "Konya": "2", "Manisa": "2", "Mersin": "2", "Sakarya": "2", "Tekirdağ": "2", "Yalova": "2",
  "Adana": "3", "Bilecik": "3", "Burdur": "3", "Düzce": "3", "Gaziantep": "3", "Isparta": "3", "Karabük": "3", "Karaman": "3", "Kırıkkale": "3", "Kırklareli": "3", "Kütahya": "3", "Nevşehir": "3", "Rize": "3", "Samsun": "3", "Trabzon": "3", "Uşak": "3", "Zonguldak": "3",
  "Afyonkarahisar": "4", "Aksaray": "4", "Amasya": "4", "Artvin": "4", "Çorum": "4", "Elazığ": "4", "Erzincan": "4", "Kastamonu": "4", "Kırşehir": "4", "Malatya": "4", "Sivas": "4",
  "Bartın": "5", "Bayburt": "5", "Çankırı": "5", "Erzurum": "5", "Giresun": "5", "Hatay": "5", "Kahramanmaraş": "5", "Kilis": "5", "Niğde": "5", "Ordu": "5", "Osmaniye": "5", "Sinop": "5", "Tokat": "5", "Tunceli": "5", "Yozgat": "5",
  "Adıyaman": "6", "Ağrı": "6", "Ardahan": "6", "Batman": "6", "Bingöl": "6", "Bitlis": "6", "Diyarbakır": "6", "Gümüşhane": "6", "Hakkari": "6", "Iğdır": "6", "Kars": "6", "Mardin": "6", "Muş": "6", "Siirt": "6", "Şanlıurfa": "6", "Şırnak": "6", "Van": "6"
};

export const TESVIK_KATKILAR_9903 = {
  "Teknoloji Hamlesi Programı": 50,
  "Yerel Kalkınma Hamlesi Programı": 50,
  "Stratejik Hamle Programı": 40,
  "Öncelikli Yatırımlar Teşvik Sistemi": 30,
  "Hedef Yatırımlar Teşvik Sistemi": 20,
};

export const PROGRAM_TURLERI = [
  "Teknoloji Hamlesi Programı",
  "Yerel Kalkınma Hamlesi Programı",
  "Stratejik Hamle Programı",
  "Öncelikli Yatırımlar Teşvik Sistemi",
  "Hedef Yatırımlar Teşvik Sistemi"
];
