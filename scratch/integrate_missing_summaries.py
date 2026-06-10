import json
from pathlib import Path

root = Path('.')
yeni_json_path = root / "static" / "data" / "ozelgeler_yeni.json"

if not yeni_json_path.exists():
    print("Error: ozelgeler_yeni.json not found!")
    exit(1)

with open(yeni_json_path, "r", encoding="utf-8") as f:
    yeni_data = json.load(f)

# Deduplicate and remove the incorrect item B.07.1.GİB.4.06.16.01-KV-2011-1-32/A-11
unique_items = []
seen_keys = set()
removed_incorrect = False

for item in yeni_data:
    no = (item.get("ozelge_no") or "").strip().lower()
    
    # Skip the incorrect item
    if "kv-2011-1-32/a-11" in no:
        removed_incorrect = True
        continue
        
    key = no if no else (item.get("konu") or "").strip().lower()
    if key not in seen_keys:
        seen_keys.add(key)
        unique_items.append(item)

print(f"Original items: {len(yeni_data)}")
print(f"Removed incorrect item: {removed_incorrect}")
print(f"Unique items before adding missing: {len(unique_items)}")

# Define the 8 missing/correct items
missing_items = [
    {
        "ozelge_no": "B.07.1.GİB.4.21.15.01-KV-125[32-2012/33]-12",
        "tarih": "01.06.2012",
        "konu": "Komple yeni yatırıma ilaveten eski fabrikadaki makine teçhizatın entegre edilmesi ve mermer ocağı devralınmasının komple yeni mi yoksa tevsi yatırım mı sayılacağı",
        "mukellef_sorusu": "Diyarbakır OSB'de komple yeni yatırım şeklinde kurulan mermer fabrikasına ilaveten, eski fabrikada mevcut bulunan makine ve teçhizatların entegre edilmesi ve ayrıca Hani ilçesindeki mermer ocağının devralınması dolayısıyla yatırımın komple yeni yatırım mı yoksa tevsi yatırım mı sayılacağı ile olağan/olağandışı gelir ve giderlerin indirimli kurumlar vergisi hesabında dikkate alınıp alınmayacağı",
        "maliyenin_cevabi": "Yatırım teşvik belgesine müracaat ve belgedeki yatırım cinsini (komple yeni/tevsi) belirleme yetkisi Ekonomi Bakanlığı'na aittir. Belgede yatırım cinsi 'komple yeni yatırım' olarak belirtildiğinden vergi uygulamasında da bu cinsten faydalanılması gerekir; itirazlar Bakanlığa yapılmalıdır. İndirimli vergi uygulanacak kazanç, yatırımdan elde edilen ticari bilanço karına göre tespit edilir ve beyannamedeki matrahı aşamaz.",
        "sonuc": "Yatırım teşvik belgesinde yer alan komple yeni yatırım cinsi vergi uygulamasında esas alınır; indirimli kurumlar vergisi yatırımdan elde edilen ticari bilanço karı üzerinden matrahla sınırlı olarak uygulanır.",
        "etiketler": ["komple yeni yatırım", "mermer fabrikası", "ekonomi bakanlığı", "yatırım cinsi", "ticari bilanço karı"]
    },
    {
        "ozelge_no": "38418978-125 [32/A-22/5]-174093",
        "tarih": "19.04.2023",
        "konu": "Teşvik belgesi kapsamında satın alınan AutoCAD çizim yazılımı abonelik bedellerinin yatırım harcaması sayılıp sayılmayacağı",
        "mukellef_sorusu": "Yatırım teşvik belgesi kapsamında satın alınan AutoCAD çizim yazılımı yıllık abonelik bedellerinin yatırıma katkı tutarı hesabında yatırım harcaması olarak dikkate alınıp alınmayacağı",
        "maliyenin_cevabi": "Royalti, yedek parça ve amortismana tabi olmayan diğer harcamalar vergi indiriminden yararlanamaz. Gayrimaddi hak bedellerinin amortismana tabi olabilmesi için işletmede bir yıldan fazla kullanılması ve aktife kaydedilmesi gerekir. Yıllık abonelik bedeli amortismana tabi olmayan bir harcama niteliği taşıdığından yatırıma katkı tutarı hesabına dahil edilemez; ancak doğrudan gider yazılabilir.",
        "sonuc": "Yıllık abonelik şeklinde kiralanan yazılım/lisans bedelleri amortismana tabi olmadığından teşvik kapsamında yatırım harcaması kabul edilmez; doğrudan gider yazılabilir.",
        "etiketler": ["yazılım aboneliği", "autocad", "amortismana tabi olmayan harcamalar", "kiralama bedeli", "gider yazma"]
    },
    {
        "ozelge_no": "50426076-125[32-2022/20-459]-180023",
        "tarih": "11.12.2023",
        "konu": "Sanayi sicil belgesinde yer almayan yumurta üretim faaliyetinden elde edilen kazançlarda 1 puanlık indirimli kurumlar vergisi uygulanıp uygulanamayacağı",
        "mukellef_sorusu": "Yem üretim faaliyeti için sanayi sicil belgesi olmasına karşın, yumurta üretim faaliyeti için kapasite raporu ve işletme tescil belgesi bulunup sanayi sicil belgesi bulunmayan şirketin, yumurta üretiminden elde ettiği kazançlara 1 puanlık kurumlar vergisi indiriminin uygulanıp uygulanamayacağı",
        "maliyenin_cevabi": "Kurumlar Vergisi Kanunu 32/8 maddesi uyarınca 1 puanlık vergi indiriminin uygulanabilmesi için hem fiilen üretim yapılması hem de sanayi sicil belgesine sahip olunması şarttır. Sanayi sicil belgesi olmayan faaliyetlerden elde edilen kazançlar 1 puanlık indirimden yararlanamaz.",
        "sonuc": "Yumurta üretim faaliyetine ait sanayi sicil belgesi bulunmayan şirketin, bu faaliyetinden elde ettiği kazançlara 1 puanlık kurumlar vergisi indirimi uygulanamaz.",
        "etiketler": ["sanayi sicil belgesi", "yumurta üretimi", "1 puan indirim", "kapasite raporu", "fiilen üretim"]
    },
    {
        "ozelge_no": "19341373-125 [ÖZELGE-2013/6]-27",
        "tarih": "09.04.2014",
        "konu": "Yatırım döneminde indirimli kurumlar vergisinin diğer faaliyetlerden elde edilen kazançlara uygulanmasının uygun olup olmadığı",
        "mukellef_sorusu": "2012/3305 sayılı BKK kapsamında düzenlenen yatırım teşvik belgesine istinaden, yatırım devam ederken diğer faaliyetlerden elde edilen kazançlara indirimli kurumlar vergisi uygulanıp uygulanmayacağı",
        "maliyenin_cevabi": "2012/3305 sayılı Karar'a göre düzenlenen teşvik belgeleri kapsamında, 01.01.2013 tarihinden itibaren, yatırım devam ederken gerçekleştirilen yatırım harcamasını aşmamak ve bölge sınırlarını geçmemek üzere diğer faaliyet kazançlarına indirimli kurumlar vergisi uygulanabilir.",
        "sonuc": "Yatırım teşvik belgesi kapsamındaki yatırım devam ederken, gerçekleştirilen yatırım harcamasını aşmamak kaydıyla diğer faaliyetlerden elde edilen kazançlara yatırım döneminde indirimli kurumlar vergisi uygulanabilir.",
        "etiketler": ["yatırım dönemi", "diğer faaliyet kazancı", "vergi indirimi", "2012/3305 sayılı BKK", "fiili yatırım harcaması"]
    },
    {
        "ozelge_no": "66491453-125-2995",
        "tarih": "22.02.2022",
        "konu": "Tevsi yatırımlardan elde edilen kazancın oranlama yoluyla tespitinde sabit kıymetlerin VUK Geçici 31. maddesi kapsamındaki yeniden değerlenmiş değerlerinin mi yoksa değerleme öncesi değerlerinin mi dikkate alınacağı",
        "mukellef_sorusu": "Tevsi yatırım teşvik belgeli şirketin, kazanç ayrımının ayrı hesaplarda yapılamaması sebebiyle oranlama yaparken, VUK Geçici 31 kapsamında yeniden değerleme sonrası brüt değerleri mi yoksa değerleme öncesi brüt değerleri mi dikkate alacağı",
        "maliyenin_cevabi": "Kazancın ayrı hesaplarda izlenerek tespiti esastır; bu mümkün değilse oranlama yöntemi kullanılır. Oranlamada, dönem sonundaki toplam brüt sabit kıymetlerin VUK Geçici 31. maddesi uyarınca yeniden değerlenmiş tutarlarıyla dikkate alınması gerekmektedir. Ancak bu değerleme yatırıma katkı tutarını artırmaz.",
        "sonuc": "Tevsi yatırımlarda kazanç ayrılamıyorsa yapılan oranlamada, VUK Geçici 31 uyarınca yeniden değerlenmiş brüt sabit kıymet tutarları dikkate alınır, ancak bu değerleme yatırıma katkı tutarını artırmaz.",
        "etiketler": ["tevsi yatırım", "oran yöntemi", "brüt sabit kıymet", "yeniden değerleme", "vuk geçici 31"]
    },
    {
        "ozelge_no": "96620903-125-32576",
        "tarih": "07.02.2023",
        "konu": "Yabancı bayraklı gemilere limanda verilen hizmetlerden elde edilen kazançlara 1 puanlık kurumlar vergisi indiriminin uygulanıp uygulanamayacağı",
        "mukellef_sorusu": "Limanda yabancı bayraklı gemilere verilen hizmetlerden (tahmil, tahliye, kılavuzlama vb.) elde edilen kazançların hizmet ihracı kapsamında değerlendirilerek 1 puanlık vergi indiriminden yararlanıp yararlanamayacağı",
        "maliyenin_cevabi": "1 puanlık ihracat indirimi, münhasıran mal veya hizmet ihracından elde edilen kazançlara uygulanır. Hizmet ihracı sayılabilmesi için hizmetin yurt dışındaki bir müşteri için yapılması ve yurt dışında faydalanılması gerekir. Yabancı bayraklı gemilere Türkiye limanlarında verilen hizmetler bu kapsamda değerlendirilemeyeceğinden vergi indirimi uygulanamaz.",
        "sonuc": "Türkiye limanlarında yabancı bayraklı gemilere verilen liman hizmetleri hizmet ihracı sayılmaz ve bu kazançlara 1 puanlık kurumlar vergisi indirimi uygulanmaz.",
        "etiketler": ["liman hizmetleri", "yabancı bayraklı gemi", "hizmet ihracı", "1 puan indirim", "kurumlar vergisi oranı"]
    },
    {
        "ozelge_no": "96620903-125-39328",
        "tarih": "24.02.2023",
        "konu": "Su ürünleri yetiştiriciliği belgesi ile yürütülen üretim faaliyetinden elde edilen kazanca 1 puanlık indirimli kurumlar vergisi uygulanıp uygulanamayacağı ve bu belgenin sanayi sicil belgesi yerine geçip geçmeyeceği",
        "mukellef_sorusu": "Su ürünleri yetiştiriciliği belgesi ile balık yetiştiriciliği yapan şirketin, bu faaliyetinden elde ettiği kazanca 1 puanlık kurumlar vergisi indiriminin uygulanıp uygulanamayacağı ve bu belgenin sanayi sicil belgesi yerine geçip geçmeyeceği",
        "maliyenin_cevabi": "1 puanlık vergi indiriminden yararlanmak için sanayi sicil belgesine sahip olma ve fiilen üretim yapma şartlarının birlikte sağlanması gerekir. Su ürünleri yetiştiriciliği belgesinin sanayi sicil belgesi yerine geçeceğine dair bir düzenleme bulunmadığından vergi indirimi uygulanamaz.",
        "sonuc": "Su ürünleri yetiştiricilik belgesi ile yapılan balık yetiştiriciliği faaliyeti, sanayi sicil belgesi şartını sağlamadığından 1 puanlık kurumlar vergisi indiriminden yararlanamaz.",
        "etiketler": ["su ürünleri yetiştiriciliği", "sanayi sicil belgesi", "1 puan indirim", "tarım bakanlığı belgesi", "fiilen üretim"]
    },
    {
        "ozelge_no": "61504625-125.32-53376",
        "tarih": "13.12.2023",
        "konu": "İndirimli kurumlar vergisinden sehven faydalanılmayan dönemler için düzeltme yapılması ve devreden katkı tutarının endekslenmesi",
        "mukellef_sorusu": "Tamamlama vizesi yapılmış yatırıma ilişkin hak edilen yatırıma katkı tutarından geçmiş yıllarda sehven yararlanılmadığından, bu hakların sonraki yıllarda endekslenerek kullanılıp kullanılamayacağı",
        "maliyenin_cevabi": "İlgili hesap dönemlerinde yararlanma imkanı varken sehven yararlanılmayan (tercihen kullanılmayan) tutarların endekslenerek sonraki yıllarda kullanılması mümkün değildir. Bu sehven kullanılmayan tutarlar için vergi zamanaşımı süresi (5 yıl) içinde düzeltme beyannamesi verilebilir. Zamanaşımına uğramış dönemlere ilişkin tutarlar ise indirimli vergi uygulamasına konu edilemez.",
        "sonuc": "Kullanılabileceği halde sehven kullanılmayan yatırıma katkı tutarları endekslenemez; 5 yıllık zamanaşımı süresi içindeki dönemler için düzeltme beyannamesi ile talep edilebilir.",
        "etiketler": ["sehven yararlanılmayan tutar", "yeniden değerleme", "endeksleme", "düzeltme beyannamesi", "zamanaşımı"]
    }
]

unique_items.extend(missing_items)
print(f"Total unique items after merging missing: {len(unique_items)}")

# Write back to ozelgeler_yeni.json
with open(yeni_json_path, "w", encoding="utf-8") as f:
    json.dump(unique_items, f, ensure_ascii=False, indent=2)

print("Successfully updated ozelgeler_yeni.json!")
