import json
import re
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\lalel\Desktop\webuygulama\webuygulama")
sys.path.insert(0, str(ROOT))

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

def tr_normalize_compact(text):
    return re.sub(r'[^a-z0-9]', '', tr_normalize(text))

# Define the 19 new summaries
new_items = [
    {
        "ozelge_no": "13649056-125[2020-ÖZE-02]-26829",
        "tarih": "11.04.2023",
        "konu": "Komple yeni yatırım devam ederken diğer faaliyetlerden elde edilen kazanca (ticari bilanço zararının KKEG eklenmesiyle oluşan kazanç) indirimli kurumlar vergisi uygulanıp uygulanamayacağı",
        "mukellef_sorusu": "Komple yeni yatırım teşvik belgesi kapsamındaki yatırım devam ederken, ilgili dönem kurumlar vergisi beyannamesinde ticari bilanço zararı bulunmasına karşın Kanunen Kabul Edilmeyen Giderlerin (KKEG) eklenmesiyle oluşan safi kurum kazancına indirimli kurumlar vergisinin uygulanıp uygulanamayacağı",
        "maliyenin_cevabi": "Yatırım teşvik belgesi kapsamındaki yatırım devam ederken diğer faaliyetlerden elde edilen kazançlara indirimli kurumlar vergisi uygulanması mümkün olup; bu uygulamanın ticari bilanço kar veya zararına kanunen kabul edilmeyen giderler eklendikten, tüm indirim, istisna ve geçmiş yıl zararları düşüldükten sonra kalan safi kazanç tutarı üzerinden hesaplanması gerekmektedir.",
        "sonuc": "Yatırım döneminde diğer faaliyetlerden elde edilen kazançlara uygulanacak indirimli vergi, ticari bilanço zararına KKEG'ler eklendikten sonra kalan safi kurum kazancı (mali kar) üzerinden hesaplanabilir.",
        "etiketler": ["yatırım dönemi", "ticari bilanço zararı", "KKEG", "safi kurum kazancı", "diğer faaliyet kazancı"]
    },
    {
        "ozelge_no": "B.07.4.DEF.0.03.10.00-GVK.ÖZLG.2011-2-28",
        "tarih": "17.08.2012",
        "konu": "Devam eden yatırımlarda vergi teşviklerinden (KDV istisnası ve indirimli kurumlar vergisi) hangi tarihten itibaren yararlanılabileceği",
        "mukellef_sorusu": "Yatırım teşvik belgesi kapsamında başlanılan ve halen devam eden yatırıma ilişkin olarak vergi teşviklerinden (KDV istisnası ve indirimli kurumlar vergisi) hangi tarihten itibaren yararlanılabileceği",
        "maliyenin_cevabi": "Kurumlar vergisi yönünden, yatırımın kısmen veya tamamen işletilmesine başlanılan hesap/geçici vergi döneminden itibaren indirimli vergi uygulanabilir. KDV yönünden ise yatırım teşvik belgesinin alındığı tarihten itibaren, belge ibraz edilerek yapılacak makine ve teçhizat alımlarında KDV istisnası uygulanacaktır.",
        "sonuc": "İndirimli kurumlar vergisi yatırımın kısmen/tamamen işletilmesine başlandığı dönemde; KDV istisnası ise teşvik belgesinin alındığı tarihten itibaren yapılacak makine-teçhizat teslimlerinde başlar.",
        "etiketler": ["istisna başlangıcı", "makine teçhizat", "KDV istisnası", "işletmeye başlama", "indirimli vergi"]
    },
    {
        "ozelge_no": "84098128-125[32/4-2014/2]-280",
        "tarih": "12.05.2014",
        "konu": "Konteyner limanı inşası yatırımının satış hasılatı paylaşımı yöntemi ile başka bir firma ile birlikte işletilmesi durumunda indirimli kurumlar vergisinden yararlanılıp yararlanılamayacağı",
        "mukellef_sorusu": "Yatırım teşvik belgesi kapsamında konteyner limanı inşaatı yatırımı yapan şirketin, limanın tamamlanması sonrası liman işletmesini satış hasılatı paylaşımı yöntemiyle başka bir işletici firma ile ortak yürütmesi durumunda indirimli kurumlar vergisinden faydalanıp faydalanamayacağı",
        "maliyenin_cevabi": "Limanın satış hasılatı paylaşımı yöntemiyle liman işletmecisi olan firma ile birlikte işletilecek olması indirimli kurumlar vergisi desteğinden yararlanılmasına engel teşkil etmemekte olup, yapılan yatırımdan şirketinizce elde edilecek kazanca indirimli kurumlar vergisi uygulanması mümkün bulunmaktadır. Ancak yatırımın 32/A maddesinin birinci fıkrasına göre hariç tutulan yatırımlar kapsamında yer almaması şarttır.",
        "sonuc": "Limandan elde edilecek kazancın hasılat paylaşımı modeliyle paylaşılması vergi indirimine engel değildir; elde edilen kazanca indirimli kurumlar vergisi uygulanabilir.",
        "etiketler": ["liman yatırımı", "hasılat paylaşımı", "liman işletmeciliği", "ortak işletim", "kazanç tespiti"]
    },
    {
        "ozelge_no": "47285862-010.01[32-2012/09]-19",
        "tarih": "30.07.2013",
        "konu": "Yatırım teşvik belgesinde vergi indirimi satırına yer verilmeyen hidroelektrik santrali yatırımı için indirimli kurumlar vergisinden yararlanılıp yararlanılamayacağı",
        "mukellef_sorusu": "Elektrik üretim lisansı bulunan ve 2010 yılında düzenlenen yatırım teşvik belgesinde destek unsuru olarak sadece Gümrük Vergisi muafiyeti ve KDV istisnasına yer verilen hidroelektrik santrali yatırımı dolayısıyla indirimli kurumlar vergisinden yararlanılmasının mümkün olup olmadığı",
        "maliyenin_cevabi": "Vergi indirimi satırına yer verilmemiş olan Yatırım Teşvik Belgesi kapsamında yapmış olduğunuz yatırım harcamalarınız dolayısıyla indirimli kurumlar vergisi uygulamasından faydalanmanız mümkün bulunmamaktadır.",
        "sonuc": "Yatırım teşvik belgesinde vergi indirimi (indirimli kurumlar vergisi) destek unsuru olarak yer almayan yatırımlar için bu teşvikten yararlanılamaz.",
        "etiketler": ["hidroelektrik santrali", "hesproje", "vergi indirimi satırı", "destek unsurları", "gümrük muafiyeti"]
    },
    {
        "ozelge_no": "85373914-125[49.01.16]-49",
        "tarih": "02.06.2014",
        "konu": "Şirket ortağına ait mermer ocağının rödovans sözleşmesi ile kiralanması durumunda yapılan harcamaların indirimli kurumlar vergisine konu edilip edilemeyeceği",
        "mukellef_sorusu": "Şirket ortağı adına kayıtlı olan ve rödovans sözleşmesi ile şirkete kiralanan mermer ocağı sahasında, şirket adına revize edilen yatırım teşvik belgesi kapsamında yapılan harcamalar nedeniyle indirimli kurumlar vergisi uygulamasından yararlanılıp yararlanılamayacağı",
        "maliyenin_cevabi": "Kurumlar Vergisi Kanununun 32/A maddesi uyarınca rödovans sözleşmelerine bağlı olarak yapılan yatırımlar indirimli kurumlar vergisi uygulamasından hariç tutulmuştur. Bu nedenle rödovans sözleşmesi ile kiralanan mermer ocağında yapılan yatırımlardan elde edilen kazançlar için indirimli kurumlar vergisi uygulanamaz.",
        "sonuc": "Rödovans sözleşmesine bağlı olarak işletilen mermer ocağı sahalarında yapılan yatırımlar, yasal kısıtlama nedeniyle indirimli kurumlar vergisinden yararlanamaz.",
        "etiketler": ["rödovans sözleşmesi", "mermer ocağı", "maden ruhsatı", "kiralama sözleşmesi", "kapsam dışı yatırımlar"]
    },
    {
        "ozelge_no": "62030549-125[32/A-2018/396]-490013",
        "tarih": "06.05.2022",
        "konu": "İmalat sanayiine yönelik yatırım teşvik belgesindeki artırımlı vergi indirimi ve diğer faaliyet kazançlarına mahsup imkanından yararlanma şartları",
        "mukellef_sorusu": "2012/3305 sayılı Karar kapsamında düzenlenen ve revize edilen imalat sanayii yatırım teşvik belgesinde, 2018 ve müteakip yıllardaki harcamalar için 2012/3305 sayılı Kararın Geçici 8. maddesinde öngörülen artırımlı desteklerden (15 puan ek yatırıma katkı payı, %100 vergi indirimi ve diğer faaliyetlerden %100 mahsup) yararlanılıp yararlanılamayacağı",
        "maliyenin_cevabi": "İmalat sanayiine yönelik düzenlenen yatırım teşvik belgesi kapsamındaki 1/1/2017 ile 31/12/2022 tarihleri arasındaki harcamalar için, belgede revize işlemi aranmaksızın Geçici 8. madde kapsamındaki artırımlı destekler (yatırıma katkı oranına 15 puan ilavesiyle %45 yatırıma katkı oranı, %100 vergi indirimi) uygulanabilir. Ayrıca, bu dönemde diğer faaliyetlerden elde edilen kazançlara yatırıma katkı tutarının %100'üne kadar indirimli kurumlar vergisi uygulanabilir.",
        "sonuc": "İmalat sanayii yatırımlarında 2017-2022 yılları arasında gerçekleştirilen harcamalara, revizeye gerek olmaksızın Geçici 8. madde kapsamındaki artırımlı yatırıma katkı ve indirim oranları uygulanır.",
        "etiketler": ["imalat sanayi", "geçici 8. madde", "artırımlı destekler", "yatırım dönemi", "oran revizesi"]
    },
    {
        "ozelge_no": "85373914-125[49.01-76]-49717",
        "tarih": "23.05.2023",
        "konu": "Yatırım teşvik belgesinin genel teşvikten bölgesel teşvike revize edildiği tarihin içinde bulunduğu geçici vergi döneminde diğer faaliyet kazançlarına indirimli vergi uygulanıp uygulanamayacağı",
        "mukellef_sorusu": "Genel teşvik belgesinin Sanayi ve Teknoloji Bakanlığınca geriye dönük bir tarihten itibaren bölgesel teşvik belgesine revize edilmesi durumunda, bu revize tarihinin içinde bulunduğu geçici vergilendirme döneminin başlangıcından itibaren diğer faaliyet kazançlarına indirimli kurumlar vergisi uygulanmasının mümkün olup olmadığı",
        "maliyenin_cevabi": "Revize edilen yatırım teşvik belgesiyle birlikte bölgesel teşvikten yararlanma hakkı kazanan mükellefin, revize tarihinin içinde bulunduğu geçici vergilendirme döneminin başlangıç tarihinden itibaren tamamlama vizesi müracaat tarihini içeren geçici vergilendirme döneminin son gününe kadar diğer faaliyetlerden elde ettiği kazançlara indirimli kurumlar vergisi uygulanabilmesi mümkündür.",
        "sonuc": "Bölgesel teşvike revize edilen belgelere istinaden, revize tarihinin ait olduğu geçici vergilendirme döneminin ilk gününden itibaren diğer faaliyet kazançlarına indirimli vergi uygulanabilir.",
        "etiketler": ["bölgesel teşvik", "belge revizesi", "geçici vergi dönemi kuralı", "diğer faaliyet kazancı", "başlangıç tarihi"]
    },
    {
        "ozelge_no": "38418978-125[32A-15/4]-531740",
        "tarih": "29.12.2017",
        "konu": "Üretim süreçleri eski ve yeni fabrikalarda iç içe geçmiş ürünlerden elde edilen kazançta indirimli kurumlar vergisinin uygulanacağı kazancın tespiti ve geçici vergi düzeltmeleri",
        "mukellef_sorusu": "Komple yeni yatırım belgesi kapsamındaki yeni fabrikalar ile eski fabrikanın üretim süreçleri iç içe geçmiş olduğundan satılan makinelerin kazanç paylarının ayrıştırılamaması halinde indirimli vergi uygulanacak kazancın nasıl tespit edileceği ve geçici vergilere ilişkin düzeltme gerekip gerekmediği",
        "maliyenin_cevabi": "İç içe geçmiş üretim süreçlerinde, satılan ürünlerin kazancının sadece yeni yatırıma isabet eden kısmı indirimli vergiye tabidir. Bu kazanç payı, işin mahiyetine uygun bir dağıtım anahtarı kullanılarak ayrıştırılmalıdır. Ayrıca, yıllık beyannamede indirimli vergi hakkı kullanılmışsa, geçici vergi dönemlerine ait beyannamelerin geriye dönük düzeltilmesine gerek yoktur.",
        "sonuc": "Eski ve yeni tesislerde ortak/iç içe üretilen malların satış kazancı işin mahiyetine uygun bir dağıtım anahtarı ile ayrıştırılarak indirimli vergiye tabi tutulur; geçici vergide geriye dönük düzeltme aranmaz.",
        "etiketler": ["dağıtım anahtarı", "iç içe üretim", "kazanç ayrıştırma", "komple yeni yatırım", "geçici vergi düzeltmesi"]
    },
    {
        "ozelge_no": "62030549-125[32/A-2023]-561630",
        "tarih": "22.05.2023",
        "konu": "Ham petrol depolama tankı ve boru hattı projelerine ilişkin sözleşmelerin kreditör onaylarının gecikmesi nedeniyle geriye dönük yürürlük tarihiyle imzalanmasının indirimli vergi uygulamasına etkisi",
        "mukellef_sorusu": "Yatırım teşvik belgesine konu ham petrol depolama tankı ve boru hattı projelerinin fiili yapımına başlanmış olmasına rağmen finansman kreditör onaylarının gecikmesi nedeniyle EPC sözleşmelerinin imza tarihlerinin geriye dönük yürürlük tarihleriyle belirlenerek imzalanmasının vergi indiriminden yararlanılmasına engel olup olmadığı",
        "maliyenin_cevabi": "Sözleşmelerin geriye dönük yürürlük tarihleriyle imzalanması; söz konusu yatırım harcamalarının şirket adına düzenlenen yatırım teşvik belgesindeki süreler ve kapsam içinde gerçekleştirilmiş olması kaydıyla indirimli kurumlar vergisinden yararlanılmasına engel teşkil etmeyecektir.",
        "sonuc": "Sözleşmelerin imza tarihlerinin geriye dönük yürürlük tarihleriyle belirlenmesi, harcamaların teşvik belgesi süresinde ve kapsamında yapılmış olması şartıyla vergi indirimine engel değildir.",
        "etiketler": ["EPC sözleşmesi", "boru hattı projesi", "geriye dönük sözleşme", "depolama tankı", "kreditör onayı"]
    },
    {
        "ozelge_no": "79690095-125[8-2024-120-143]-57172",
        "tarih": "28.04.2025",
        "konu": "Mülkiyeti şirket ortağına ait arsa üzerine kiralama yoluyla inşa edilen fabrika binasının yatırım harcaması olarak indirimli kurumlar vergisine konu edilip edilemeyeceği",
        "mukellef_sorusu": "Şirket ortağına ait arsanın kiralanması suretiyle bu arsa üzerine inşa edilen fabrika binasına ait inşaat harcamalarının, şirket aktifinde kayıtlı olmayan bir gayrimenkul olması sebebiyle indirimli kurumlar vergisi kapsamında toplam yatırım tutarında dikkate alınıp alınmayacağı",
        "maliyenin_cevabi": "Şirketin aktifinde yer almayan arsa üzerine arsa sahibi ortağı adına yapılan inşaatla ilgili harcamalar, mükellefin kendi aktifinde amortismana tabi iktisadi kıymet oluşturmadığından indirimli kurumlar vergisine konu edilmesi mümkün değildir.",
        "sonuc": "Başkasına (şirket ortağına dahi olsa) ait arsa üzerine inşa edilen fabrika binaları, aktife kaydedilemeyecekleri için indirimli kurumlar vergisi kapsamında yatırım harcaması kabul edilmez.",
        "etiketler": ["kiralık arsa", "fabrika inşaatı", "aktifte yer almama", "özel maliyetler", "kapsam dışı binalar"]
    },
    {
        "ozelge_no": "63611781-125[32/4-2013/4]-10",
        "tarih": "14.04.2014",
        "konu": "İki ayrı teşvik belgesi bulunması durumunda indirimli kurumlar vergisi öncelik sırası, diğer faaliyet kazançları uygulaması ve beyanname matrah bildirimi",
        "mukellef_sorusu": "2009/15199 ve 2012/3305 sayılı kararlara göre iki ayrı yatırım teşvik belgesi bulunan şirketin kazanç yetersizliğinde öncelik sırasını nasıl belirleyeceği, yeni belgeden ötürü diğer faaliyet kazançlarına ne zaman indirim uygulanacağı ve beyannamede tek satır bulunması nedeniyle farklı indirim oranlarının nasıl beyan edileceği",
        "maliyenin_cevabi": "Safi kurum kazancının iki belgeden elde edilen toplam kazançtan düşük olması halinde, her belgenin kazanç payı oranında matrah dağıtılarak indirim oranları uygulanır. 2012/3305 sayılı Karar kapsamındaki yatırımdan henüz kazanç elde edilmese dahi 01.01.2013'ten itibaren diğer faaliyet kazançlarına indirimli kurumlar vergisi uygulanması mümkün bulunmaktadır. Farklı oranlardaki indirim hakları beyanname dışında hesaplanmalı ve toplam vergi indirimini sağlayacak ağırlıklı ortalama bir oran geçici ve yıllık beyannameye dahil edilmelidir.",
        "sonuc": "İki farklı teşvik belgesinde indirim tutarları beyanname dışında hesaplanır; toplam indirimi sağlayacak ağırlıklı oran beyannamedeki tek satıra yazılır; kazanç yetersizse matrah belgelere oranlanır.",
        "etiketler": ["iki adet teşvik belgesi", "matrah dağıtımı", "ağırlıklı indirim oranı", "diğer faaliyet kazancı", "beyanname düzeni"]
    },
    {
        "ozelge_no": "67630374-125[2013-7]-5",
        "tarih": "09.04.2014",
        "konu": "Tevsi yatırımlarda kazancın oranlama yoluyla tespitinde her yıl yeni bir oran hesaplanıp hesaplanmayacağı ve devreden katkı tutarının değerlenmesi",
        "mukellef_sorusu": "Kazancın ayrı hesaplarda izlenememesi nedeniyle brüt sabit kıymet oranlaması yönteminin kullanıldığı tevsi yatırımlarda, sonraki yıllarda indirimli vergilendirilecek kazancı bulmak için her yıl yeni bir oran hesaplanıp hesaplanmayacağı ile devreden yatırıma katkı tutarlarının endekslenip endekslenmeyeceği",
        "maliyenin_cevabi": "Kazancın ayrı tespit edilemediği durumlarda indirimli oran uygulanacak kazanç, gerçekleştirilen tevsi yatırım tutarının her bir dönem sonu itibarıyla şirketinizin aktifine kayıtlı bulunan toplam sabit kıymet tutarına (devam eden yatırımlara ait tutarlar da dahil) oranlanması suretiyle belirlenecektir. Ayrıca yasal düzenleme eksikliği nedeniyle, kullanılamayıp devreden katkı tutarları yeniden değerleme (endeksleme) yapılmaksızın nominal değerle takip eden yıllara aktarılır.",
        "sonuc": "Tevsi yatırımlarda kazanç ayrılamıyorsa her yıl güncel sabit kıymet ve yatırım tutarlarına göre oran yeniden hesaplanır; devreden katkı tutarları ise değerleme yapılmaksızın nominal olarak aktarılır.",
        "etiketler": ["tevsi yatırım", "oranlama yöntemi", "brüt sabit kıymet", "her yıl yeniden hesaplama", "devreden katkı tutarı"]
    },
    {
        "ozelge_no": "B.07.1.GİB.4.35.16.01-176300-713",
        "tarih": "09.12.2011",
        "konu": "Tevsi yatırımlarda kazanç tespiti oranlamasındaki 'toplam sabit kıymet' tanımı ve birikmiş amortismanlar ile yeniden değerlenmiş değerlerin dikkate alınma yöntemi",
        "mukellef_sorusu": "Tevsi yatırımlardan elde edilen kazancın oranlama yöntemiyle tespitinde esas alınacak 'toplam sabit kıymet' kavramına hangi kıymetlerin dahil edileceği, birikmiş amortismanların düşülüp düşülmeyeceği ve 'yeniden değerlenmiş tutar' ifadesinden ne anlaşılması gerektiği",
        "maliyenin_cevabi": "Oranlamada 'toplam sabit kıymet' olarak amortismana tabi olan tüm iktisadi kıymetler (üretimde kullanılsın veya kullanılmasın) esas alınır ve bunların birikmiş amortismanları düşülmeden önceki brüt kayıtlı değerleri baz alınır. Yeniden değerlenmiş tutardan kasıt, yasal şartların oluşması halinde yapılan enflasyon düzeltmesi sonucu oluşan değerdir; bunun dışında başka bir yeniden değerleme yapılmaz.",
        "sonuc": "Tevsi yatırımlarda oranlamada amortismana tabi tüm kıymetlerin birikmiş amortisman düşülmemiş brüt değerleri esas alınır; yeniden değerlemeden kasıt ise sadece enflasyon düzeltmesidir.",
        "etiketler": ["brüt sabit kıymet", "amortisman düşümü", "enflasyon düzeltmesi", "oranlama yöntemi", "tevsi yatırım"]
    },
    {
        "ozelge_no": "68509125-125[2023/8]-7831",
        "tarih": "10.04.2023",
        "konu": "Kullanılabilecek dönemde yararlanılmayan devreden yatırıma katkı tutarının sonraki yıllarda endekslenip endekslenemeyeceği ve diğer teşvik belgelerinden öncelikli kullanılması zorunluluğu",
        "mukellef_sorusu": "Tamamlanmış ve vizesi yapılmış yatırım teşvik belgesine ait hak kazanılan yatırıma katkı tutarından kalan kısmın, mükellefin diğer teşvik belgelerini öncelikli tercih etmesi nedeniyle kullanılmayıp devretmesi durumunda, bu kalan tutarın yeniden değerleme (endeksleme) yapılarak sonraki dönemlerde kullanılıp kullanılamayacağı",
        "maliyenin_cevabi": "İşletme döneminde yatırımdan elde edilen kazanç mevcut ve bu kazançtan yararlanılması mümkün iken yararlanılmayan yatırıma katkı tutarının endekslenerek sonraki yıllarda kullanılması mümkün değildir. Ancak zamanaşımı süresi içinde düzeltme beyannamesiyle bu tutarlar talep edilebilir.",
        "sonuc": "Kullanılabileceği halde sehven kullanılmayan yatırıma katkı tutarları endekslenemez; 5 yıllık zamanaşımı süresi içindeki dönemler için düzeltme beyannamesi ile talep edilebilir.",
        "etiketler": ["sehven kullanılmayan tutar", "yeniden değerleme", "endeksleme", "düzeltme beyannamesi", "zamanaşımı"]
    },
    {
        "ozelge_no": "B.07.1.GİB.4.16.16.01-KV-I1-67-82",
        "tarih": "21.02.2012",
        "konu": "Birden fazla bölgedeki teşvik belgelerine bağlı yatırımlarda indirimli kurumlar vergisinin beyannameye intikali ve tevsi yatırımlarda oranlama yöntemi esasları",
        "mukellef_sorusu": "Şirketin I. ve III. bölgelerde bulunan iki farklı teşvik belgesine bağlı yatırımları nedeniyle hak kazandığı farklı indirim oranlı teşviklerin aynı dönemde beyannameye nasıl aktarılacağı ve tevsi yatırımlarda oranlamada sabit kıymetlerin brüt veya net tutarlarının hangisinin dikkate alınacağı",
        "maliyenin_cevabi": "Tevsi yatırımlarda kazanç ayrılamıyorsa oranlamada sadece tevsi yatırıma konu hizmet ve üretim işletmesinin değil, şirketin tüm amortismana tabi sabit kıymetlerinin birikmiş amortisman düşülmemiş brüt değerleri toplamı dikkate alınır. Farklı oranlara tabi indirimler beyanname dışında hesaplanarak, beyannamedeki tek satıra toplam vergi indirimini sağlayacak ağırlıklı ortalama bir oran yazılmak suretiyle beyan edilir.",
        "sonuc": "Farklı bölgelerdeki teşviklerin indirim tutarları dışarıda hesaplanıp ağırlıklı ortalama bir oranla beyannameye yazılır; oranlamada şirketin tüm brüt sabit kıymetleri dikkate alınır.",
        "etiketler": ["farklı bölgeler", "ağırlıklı indirim oranı", "brüt sabit kıymet", "oranlama yöntemi", "beyanname düzeni"]
    },
    {
        "ozelge_no": "62030549-125[32/A-2013/285]-874",
        "tarih": "11.04.2014",
        "konu": "Yatırımın tamamlanmasından sonraki dönemlerde diğer faaliyetlerden elde edilen kazançlara indirimli kurumlar vergisi uygulanıp uygulanamayacağı",
        "mukellef_sorusu": "Yatırım teşvik belgesine istinaden hak kazanılan yatırıma katkı tutarının, yatırım dönemi bittikten ve yatırım tamamlandıktan sonra da diğer genel faaliyetlerden elde edilen kazançlara indirimli vergi uygulanarak eritilmesinin mümkün olup olmadığı",
        "maliyenin_cevabi": "2012/3305 sayılı Kararın 15/5. maddesi uyarınca yatırım devam ederken (yatırım döneminde) kısıtlı bir şekilde diğer faaliyet kazançlarına indirimli kurumlar vergisi uygulanması mümkündür. Ancak, yatırım tamamlandıktan (yatırım dönemi bittikten) sonra, diğer faaliyetlerden elde edilen kazançlara indirimli kurumlar vergisi uygulanması yasal olarak mümkün değildir.",
        "sonuc": "Yatırım tamamlanıp resmi olarak kapandıktan sonra diğer faaliyetlerden elde edilen kazançlara indirimli kurumlar vergisi uygulanamaz; kalan katkı tutarı sadece yatırımdan elde edilen kazançla eritilebilir.",
        "etiketler": ["yatırım dönemi", "yatırım dönemi sonrası", "diğer faaliyet kazancı kısıtlaması", "tamamlanan yatırım", "eritme yöntemi"]
    },
    {
        "ozelge_no": "47285862-125[32/A-2018/12]-E.22727",
        "tarih": "15.06.2020",
        "konu": "Tamamlanmış ve devralınan yatırım teşvik belgesindeki kullanılmayan yatırıma katkı tutarlarının devralan şirketçe kullanılması ve Geçici 8. madde kapsamı",
        "mukellef_sorusu": "Tamamlama vizesi yapılmış olan bir yatırım teşvik belgesinin başka bir şirkete devredilmesi halinde, devralan şirketin bu yatırımdan elde edeceği kazançlara kalan yatırıma katkı tutarlarını indirimli vergiyle uygulayıp uygulayamayacağı ve Geçici 8. maddedeki artırımlı oranlardan yararlanıp yararlanamayacağı",
        "maliyenin_cevabi": "Yatırımın faaliyete geçmesinden sonra devredilmesi durumunda devralan şirket, devreden şirketin kullanmadığı kalan yatırıma katkı tutarını, yatırımdan elde edeceği kazançlar için indirimli kurumlar vergisi uygulayarak kullanabilir. Katkı tutarı hesabında devralan şirketin devir bedeli değil, ilk yatırımı yapan şirketin fiili harcamaları esas alınır. Ancak, 2015 yılında tamamlama vizesi yapılmış bir yatırım için Geçici 8. maddedeki (2017-2018 yılları harcamalarına yönelik) artırımlı oranlardan yararlanılamaz.",
        "sonuc": "Devralınan tamamlanmış yatırımlarda, devreden şirketten kalan yatırıma katkı tutarları devralan şirketçe yatırımdan elde edilen kazançlar üzerinden kullanılabilir; ancak geçmişte kapanmış belgelere artırımlı oranlar uygulanmaz.",
        "etiketler": ["teşvik belgesi devri", "devralınan yatırım", "kalan katkı tutarı", "geçici 8. madde", "tamamlama vizesi"]
    },
    {
        "ozelge_no": "30094508-125[2018/1.2]-E.8068",
        "tarih": "04.04.2018",
        "konu": "Yıllara sari inşaat işlerinden elde edilen hak ediş kazançlarının yatırım döneminde 'diğer faaliyetlerden elde edilen kazanç' kapsamında indirimli vergiye tabi tutulup tutulamayacağı",
        "mukellef_sorusu": "Yıllara sari inşaat ve onarım işleri ile iştigal eden şirketin, yatırım teşvik belgesi kapsamındaki yatırımı devam ederken (yatırım döneminde) yıllara sari inşaat işlerinin tamamlandığı dönemde elde ettiği hakediş kazançlarının 'diğer faaliyet kazancı' olarak indirimli vergilendirilip vergilendirilemeyeceği",
        "maliyenin_cevabi": "Yıllara sari inşaat ve onarma işi yapan mükelleflerin, teşvikli yatırımlarının yatırım döneminde, bu yıllara sari işlerinin tamamlanması üzerine beyan ettikleri hakediş kazançları, 'diğer faaliyetlerden elde edilen kazanç' kapsamında değerlendirilerek indirimli kurumlar vergisine tabi tutulabilir.",
        "sonuc": "Yıllara sari inşaat işlerinin tamamlandığı yılda beyan edilen hakediş kazançları, yatırım döneminde 'diğer faaliyet kazancı' sayılarak indirimli kurumlar vergisine tabi tutulabilir.",
        "etiketler": ["yıllara sari inşaat", "hakediş kazancı", "yatırım dönemi", "diğer faaliyet kazancı", "vergi indirim hakkı"]
    },
    {
        "ozelge_no": "17192610-125[KV-25-130]-127160",
        "tarih": "29.04.2025",
        "konu": "Üretim ve ihracat faaliyetlerinden elde edilen kazancın tespitinde ortak/müşterek gider ve gelirlerin hesaplamaya dahil edilmesinin zorunlu olup olmadığı",
        "mukellef_sorusu": "Kurumlar Vergisi Kanunu 32. maddesi kapsamında, binek otomobil, motor aksamı ve yedek parçalarının imalat, montaj ve ticareti ile iştigal eden şirketin, ihracattan ve üretim faaliyetlerinden elde ettiği kazançların tespitine ilişkin hesaplamalarda müşterek gelirlere yer verilip verilemeyeceği ile müşterek giderlerin dağıtıma dahil edilmesinin zorunlu olup olmadığı",
        "maliyenin_cevabi": "İhracattan ve imalat faaliyetlerinden elde edilen kazançlara 5 puanlık kurumlar vergisi indiriminin uygulanabilmesi için bu kazançların muhasebe kayıtlarında ayrı izlenmesi esastır. Bu kazançların tespitinde, ortak/müşterek giderlerden de işin mahiyetine uygun bir dağıtım anahtarı kullanılarak pay verilmesi zorunludur. Ancak, ana faaliyetle doğrudan ilgisi olmayan müşterek gelirlerin ihracat/üretim kazancını artıracak şekilde bu hesaplamaya dahil edilmesi mümkün değildir.",
        "sonuc": "İmalat ve ihracat indirimine esas kazanç tespiti yapılırken müşterek giderlerden işin mahiyetine uygun pay verilmesi zorunludur; ancak arızi müşterek gelirler bu kazancı artıracak şekilde hesaba dahil edilemez.",
        "etiketler": ["ihracat indirimi", "imalat indirimi", "müşterek giderler", "müşterek gelirler", "dağıtım anahtarı"]
    }
]

def rebuild():
    # 1. Read clean ozelgeler_88_yeni.txt
    txt_path = ROOT / "services" / "ocr_text" / "ozelgeler_88_yeni.txt"
    if not txt_path.exists():
        print("Error: ozelgeler_88_yeni.txt not found!")
        sys.exit(1)
        
    print("Reading ozelgeler_88_yeni.txt...")
    raw = txt_path.read_text(encoding="utf-8").strip()
    raw_combined = '[' + raw.lstrip('[').rstrip(']').replace(']\n[', ',').replace(']\r\n[', ',') + ']'
    data = json.loads(raw_combined)
    print(f"Loaded {len(data)} items from text file.")
        
    # 2. Deduplicate based on normalized konu
    seen = set()
    unique_items = []
    
    for item in data:
        no = (item.get("ozelge_no") or "").strip().lower()
        if "kv-2011-1-32/a-11" in no:
            continue
            
        key = tr_normalize_compact(item.get("konu") or "")
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
            
    print(f"Unique AI items after deduplication by konu: {len(unique_items)}")
    
    # 3. Load the 8 missing items from integrate_missing_summaries
    from scratch.integrate_missing_summaries import missing_items
    print(f"Loaded {len(missing_items)} missing items from scratch.integrate_missing_summaries.")
    
    # Deduplicate missing items
    unique_missing = []
    for item in missing_items:
        key = tr_normalize_compact(item.get("konu") or "")
        if key not in seen:
            seen.add(key)
            unique_missing.append(item)
        else:
            print(f"Skipping duplicate missing item: {item.get('ozelge_no')}")
            
    print(f"Unique missing items added: {len(unique_missing)}")
    
    # 4. Add the 19 new items
    unique_new = []
    for item in new_items:
        key = tr_normalize_compact(item.get("konu") or "")
        if key not in seen:
            seen.add(key)
            unique_new.append(item)
        else:
            print(f"Skipping duplicate new item: {item.get('ozelge_no')}")
            
    print(f"Unique new items added: {len(unique_new)}")
    
    # 5. Combine all
    full_88_items = unique_items + unique_missing + unique_new
    print(f"Total items in combined list: {len(full_88_items)}")
    
    # 6. Save ozelgeler_yeni.json
    out_path = ROOT / "static" / "data" / "ozelgeler_yeni.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(full_88_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Successfully wrote clean data to: {out_path}")

if __name__ == "__main__":
    rebuild()
