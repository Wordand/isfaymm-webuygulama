from flask import Blueprint, render_template, abort
from datetime import datetime # Dummy data için


blog_bp = Blueprint('blog', __name__, template_folder='../templates')


blog_posts = [
    {
        'title': '2025 Vergi Rehberi: İşletmeler İçin Önemli Değişiklikler',
        'slug': 'vergi-rehberi-2025',
        'summary': '2025 yılında vergi mevzuatında gerçekleşecek temel değişiklikler ve işletmelerin uyum süreçleri hakkında kapsamlı bir rehber.',
        'content': """
            <h3>2025 Vergi Rehberi: Yeni Oranlar, Dijitalleşme ve Uyum Süreci</h3>
            <p>2025 yılı, Türkiye’de vergi sisteminde hem oranlar hem yükümlülükler açısından önemli bir dönüşüm yılı olarak öne çıkıyor. Kurumlar vergisi, gelir vergisi dilimleri, e-belge uygulamaları ve usulsüzlük cezaları gibi birçok alan güncellendi. İşletmelerin ve bireylerin bu değişikliklere hazırlıklı olması artık kaçınılmaz.</p>

            <h4>Öne Çıkan Oran ve İstisna Güncellemeleri</h4>
            <ul>
              <li><strong>Gelir Vergisi Dilimleri:</strong> 2025’te yeniden değerleme oranına göre güncellendi. Ücretlilerde ve gelir vergisine tabi diğer kazançlarda oran değişikliğine gidildi.</li>
              <li><strong>Asgari Kurumlar Vergisi:</strong> Kurumlar vergisi uygulamasında indirim ve istisnaların ardından şirketlerin ödeyeceği asgari vergi tutarı uygulaması devreye giriyor.</li>
              <li><strong>Usulsüzlük ve Belge Düzenleme Yükümlülükleri:</strong> Vergi Usul Kanunu’nda yer alan belge düzeni sınırları, 9.900 TL fatura düzenleme limiti gibi kriterler 1/1/2025’ten itibaren değişti.</li>
            </ul>

            <h4>Dijital Dönüşüm ve E-Belge Zorunlulukları</h4>
            <p>2025 yılı itibarıyla e-fatura, e-arşiv, e-defter uygulamaları yaygınlaşıyor; dijitalleşme süreci yalnızca teknik değil, aynı zamanda vergi uyumu bakımından stratejik hale geliyor.</p>

            <h4>KDV, Dolaylı Vergiler ve Muafiyetlerde Yenilikler</h4>
            <ul>
              <li>KDV ve diğer dolaylı vergilerde yerel üretimi teşvik etmek amacıyla oran ve muafiyet düzenlemeleri yapıldı.</li>
              <li>Vergiden muafiyet düzenlemeleri evden çalışanlar, genç girişimciler ve e-ticaret yapanlar için yeniden düzenlendi.</li>
            </ul>

            <h4>İşletmelere Düşen Görevler</h4>
            <ul>
              <li>Vergi planlamanızı 2025/ sonrası için gözden geçirin — özellikle kurumlar vergisi ve indirim haklarını.</li>
              <li>E-belge ve dijital defter uygulamalarına geçiş için zamanlama ve entegrasyon stratejinizi oluşturun.</li>
              <li>Belgelerinizi, beyanlarınızı ve denetim süreçlerinizi belge düzenleme yükümlülükleri çerçevesinde hazırlayın.</li>
              <li>Yeni muafiyet ve teşvik düzenlemelerini takip ederek avantajlarını değerlendirin.</li>
            </ul>


            <h4 class="mt-5">2025 Vergi Döneminde Odaklanmanız Gereken 4 Ana Başlık</h4>
            <div class="row text-center mt-4 g-4">
              <div class="col-md-6 col-lg-3" data-aos="fade-up" data-aos-delay="100">
                <div class="p-4 bg-light rounded-4 shadow-sm h-100">
                  <i class="bi bi-percent fs-1 text-primary mb-3"></i>
                  <h6 class="fw-bold text-primary">Yeni Vergi Oranları</h6>
                  <p class="small text-muted mb-0">Kurumlar vergisi ve gelir dilimlerinde yapılan değişiklikleri planlamalarınıza dahil edin.</p>
                </div>
              </div>
              <div class="col-md-6 col-lg-3" data-aos="fade-up" data-aos-delay="200">
                <div class="p-4 bg-light rounded-4 shadow-sm h-100">
                  <i class="bi bi-receipt-cutoff fs-1 text-success mb-3"></i>
                  <h6 class="fw-bold text-success">Asgari Vergi Uygulaması</h6>
                  <p class="small text-muted mb-0">Tüm şirketler için getirilen asgari kurumlar vergisi sistemine hazırlanın.</p>
                </div>
              </div>
              <div class="col-md-6 col-lg-3" data-aos="fade-up" data-aos-delay="300">
                <div class="p-4 bg-light rounded-4 shadow-sm h-100">
                  <i class="bi bi-cloud-arrow-up fs-1 text-warning mb-3"></i>
                  <h6 class="fw-bold text-warning">E-Belge Zorunlulukları</h6>
                  <p class="small text-muted mb-0">E-fatura ve e-arşiv geçiş takvimini kontrol edin; teknik uyum sürecini başlatın.</p>
                </div>
              </div>
              <div class="col-md-6 col-lg-3" data-aos="fade-up" data-aos-delay="400">
                <div class="p-4 bg-light rounded-4 shadow-sm h-100">
                  <i class="bi bi-lightbulb fs-1 text-info mb-3"></i>
                  <h6 class="fw-bold text-info">Teşvik & Muafiyetler</h6>
                  <p class="small text-muted mb-0">2025’te yürürlüğe giren yeni teşvik ve muafiyetlerden yararlanma şartlarını inceleyin.</p>
                </div>
              </div>
            </div>

            <p class="mt-4"><em>İSFA YMM olarak, 2025 vergi mevzuatı değişikliklerine dair bütün boyutları analiz ediyor, işletmelerin yeni döneme sorunsuz geçmesini sağlayacak danışmanlık hizmeti sunuyoruz.</em></p>
        """,
        'publish_date': datetime(2025, 7, 1),
        'category': 'Vergi',
        'author': 'İSFA YMM',
        'tags': ['Vergi', 'Kurumlar Vergisi', 'E-Belge'],
        'image_url': None
    },
    {
        'title': 'KDV İadesi Püf Noktaları: Süreci Hızlandırın!',
        'slug': 'kdv-iadesi-puf-noktalari',
        'summary': 'KDV iadesi alırken süreci hızlandırmak ve olası riskleri minimize etmek için bilmeniz gereken pratik ipuçları.',
        'content': """
            <h3>KDV İadesi Nedir?</h3>
            <p>Katma Değer Vergisi (KDV) iadesi, mükelleflerin belirli işlemlerinden kaynaklanan ve indirim yoluyla telafi edilemeyen KDV tutarlarının, nakden veya mahsuben iade edilmesi sürecidir. Vergi sisteminin nötrlüğünü sağlamak ve üretim-ihracat zincirinde biriken yükleri kaldırmak amacıyla uygulanır.</p>

            <h4>KDV İadesinin Amacı</h4>
            <p>KDV iadesinin temel amacı; ihracat, yatırım, teşvikli işlem veya kamu yararına yapılan faaliyetler gibi alanlarda mükellef üzerindeki vergi yükünü ortadan kaldırmaktır. Böylece hem rekabet gücü artırılır hem de işletmelerin finansal dengesi korunur.</p>

            <h4>KDV İadesi Türleri</h4>
            <div class="table-responsive mt-3">
              <table class="table table-bordered table-striped align-middle small">
                <thead class="table-primary">
                  <tr>
                    <th scope="col">İade Türü</th>
                    <th scope="col">Açıklama</th>
                    <th scope="col">Örnek İşlem</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>İhracat Kaynaklı KDV İadesi</strong></td>
                    <td>İhracat teslimlerinde KDV istisnası uygulanır, buna rağmen yüklenilen KDV tutarları iade edilir.</td>
                    <td>Yurt dışına mal ihracatı yapan bir üretici firmanın yüklenmiş olduğu KDV’nin iadesi</td>
                  </tr>
                  <tr>
                    <td><strong>Tevkifat Kaynaklı KDV İadesi</strong></td>
                    <td>Kısmi tevkifat uygulanan işlemlerde satıcı tarafından beyan edilen ancak alıcıya ödenmeyen KDV’nin iadesi mümkündür.</td>
                    <td>Yapım işleri, danışmanlık veya temizlik hizmetlerinde uygulanan tevkifatlı işlemler</td>
                  </tr>
                  <tr>
                    <td><strong>İstisna Kapsamındaki İşlemlerden Doğan KDV İadesi</strong></td>
                    <td>KDV Kanunu’nun 13, 14 ve 15. maddelerinde sayılan istisna işlemlerden doğan iade hakkıdır.</td>
                    <td>Yatırım teşvik belgesi kapsamında yapılan makine-teçhizat alımları</td>
                  </tr>
                  <tr>
                    <td><strong>İndirimli Orana Tabi İşlemlerden Doğan KDV İadesi</strong></td>
                    <td>%1 veya %10 oranlı satışlarda, yüklenilen KDV yüksek kaldığı için iade hakkı doğar.</td>
                    <td>Gıda, sağlık veya eğitim hizmeti sağlayan işletmeler</td>
                  </tr>
                  <tr>
                    <td><strong>İade Edilmeyen KDV’nin Mahsubu</strong></td>
                    <td>İade hakkı doğmasına rağmen nakit alınmayan KDV’nin, diğer vergi borçlarına mahsup edilmesi mümkündür.</td>
                    <td>Kurumlar vergisi veya SGK prim borçlarına mahsup işlemi</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <h4 class="mt-4">KDV İadesi Almanın Temel Şartları</h4>
            <ul>
              <li>İade hakkı doğuran işlem için <strong>belge ve beyannamelerin eksiksiz olması</strong></li>
              <li>İade talebinin yasal süresi içinde yapılması</li>
              <li>Yüklenilen KDV’nin <strong>istisna veya indirimli oranlı işleme doğrudan bağlı olması</strong></li>
              <li>Yeminli Mali Müşavir (YMM) raporu veya vergi incelemesi sonucuna göre iade yapılması</li>
            </ul>
            
             <h4 class="mt-4">KDV İadesi Sürecinde Püf Noktalar</h4>
            <p>KDV iadesi sürecinde zaman kaybını önlemek ve olası red risklerini azaltmak için aşağıdaki uygulamalar büyük önem taşır:</p>
            <ul>
              <li><strong>Belgelerin Tutarlılığı:</strong> Fatura, gümrük beyannamesi ve muhasebe kayıtları birebir uyumlu olmalıdır.</li>
              <li><strong>Yüklenilen KDV Listesi:</strong> Yalnızca istisna veya indirimli oranlı işleme ait maliyet kalemleri dahil edilmelidir.</li>
              <li><strong>e-İade Sisteminin Etkin Kullanımı:</strong> Başvuru ve belgelerin elektronik ortamda tam olarak yüklenmesi süreci hızlandırır.</li>
              <li><strong>YMM Raporu Kalitesi:</strong> Açıklamalı ve belgeye dayalı raporlar, inceleme süresini kısaltır.</li>
              <li><strong>Düzenli Ön Kontrol:</strong> İade talebinden önce sistemdeki eksik veya hatalı kayıtlar kontrol edilmelidir.</li>
            </ul>

            <h4 class="mt-4">KDV İadesi Talebi Nasıl Yapılır?</h4>
            <p>İade talepleri elektronik ortamda <strong>İnteraktif Vergi Dairesi</strong> veya <strong>KDV İade Talep Formu (KDVİRA)</strong> sistemi üzerinden yapılır. Mükellefler, nakden veya mahsuben iade seçeneklerinden birini tercih edebilir.</p>

            <h4 class="mt-4">İade Sürecinde Dikkat Edilmesi Gerekenler</h4>
            <ul>
              <li>İade dayanağı belgelerin doğruluğu ve sıralı düzeni çok önemlidir.</li>
              <li>YMM raporu hazırlanırken, yüklenilen KDV hesaplamasının her kalem için net olması gerekir.</li>
              <li>Eksik veya hatalı belgeler iade sürecini geciktirir, hatta reddine yol açabilir.</li>
            </ul>

            <h4 class="mt-4">Sonuç</h4>
            <p>KDV iadesi, işletmelerin finansal yönetiminde önemli bir nakit avantajı sağlar. Ancak sürecin mevzuata uygun yürütülmesi, belgelerin eksiksiz hazırlanması ve beyanların doğru yapılması kritik öneme sahiptir.</p>
            <p><em>İSFA YMM olarak, KDV iadesi süreçlerinde teknik analiz, YMM raporu hazırlığı ve iade takibi dahil olmak üzere uçtan uca danışmanlık desteği sunmaktayız.</em></p>
        """,
        'publish_date': datetime(2025, 6, 10),
        'category': 'KDV',
        'author': 'İSFA YMM',
        'tags': ['KDV', 'İade', 'Vergi Süreçleri'],
        'image_url': None
    },
    {
        'title': '2025/9903 Sayılı Kararla Yatırım Teşviklerinde Yeni Dönem',
        'slug': 'yatirim-tesvik-2025-guncellemeleri',
        'summary': '2025/9903 sayılı Kararla yatırım teşvik sistemi yenilendi; katkı oranları ve destek unsurları güncellendi.',
        'content': """
            <h3>2025/9903 Sayılı Karar ile Yatırım Teşviklerinde Yeni Dönem</h3>
            <p>30 Mayıs 2025 tarihli ve <strong>2025/9903 sayılı Cumhurbaşkanı Kararı</strong> ile yürürlüğe giren yeni teşvik sistemi, 
            Türkiye’nin yatırım politikalarında köklü bir değişimi temsil ediyor. 
            Bu karar ile <strong>2012/3305 sayılı sistem yürürlükten kaldırılmış</strong> ve 
            “<strong>Türkiye Yüzyılı Kalkınma Hamlesi</strong>” vizyonuna uygun yeni bir yapı getirilmiştir.</p>

            <h4>Yeni Sistem: Üç Katmanlı Teşvik Yapısı</h4>
            <ul>
            <li><strong>Türkiye Yüzyılı Kalkınma Hamlesi:</strong> 
            Teknoloji Hamlesi, Yerel Kalkınma Hamlesi ve Stratejik Hamle programlarından oluşur. 
            Ar-Ge, yüksek teknoloji ve sürdürülebilir yatırımlar bu kapsamda önceliklidir.</li>
            <li><strong>Sektörel Teşvik Sistemi:</strong> 
            Öncelikli ve Hedef Yatırımlar başlıkları altında, stratejik sektörlerde üretimi destekler.</li>
            <li><strong>Bölgesel Teşvikler:</strong> 
            Altı bölge sistemi korunmuş; istihdam ve bölgesel kalkınma odaklı destekler sadeleştirilmiştir.</li>
            </ul>

            <h4>Başlıca Destek Unsurları</h4>
            <ul>
            <li><strong>Vergi İndirimi:</strong> 
            5520 sayılı Kanun’un 32/A maddesi uyarınca uygulanacak <em>yatırıma katkı oranları</em> yeniden belirlenmiştir:</li>
            </ul>

            <table class="table table-sm table-bordered">
            <thead>
                <tr>
                <th>Program</th>
                <th>Yatırıma Katkı Oranı</th>
                <th>İndirimli KV Oranı</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>Teknoloji / Yerel Kalkınma Hamlesi</td><td>%50</td><td>%60 indirimli</td></tr>
                <tr><td>Stratejik Hamle Programı</td><td>%40</td><td>%60 indirimli</td></tr>
                <tr><td>Öncelikli Yatırımlar Sistemi</td><td>%30</td><td>%60 indirimli</td></tr>
                <tr><td>Hedef Yatırımlar Sistemi</td><td>%20</td><td>%60 indirimli</td></tr>
            </tbody>
            </table>

            <p>Diğer faaliyet kazançlarına uygulanabilecek katkı oranı %50 ile sınırlandırılmıştır. 
            Finans, sigorta, Yap-İşlet-Devret ve rödovans yatırımları bu destekten yararlanamaz.</p>

            <ul>
            <li><strong>Makine Desteği:</strong> Makine bedelinin %25’i oranında hibe sağlanabilir; 
            Teknoloji ve Yerel Kalkınma Programlarında azami 240 milyon TL’ye kadar destek mümkündür.</li>
            <li><strong>Faiz/Kâr Payı Desteği:</strong> Yatırım kredilerinin 5 yıla kadar faizinin %25–40’ı devlet tarafından karşılanabilir.</li>
            <li><strong>SGK Prim Desteği:</strong> 6. bölgede 12 yıl, diğer bölgelerde 8 yıl süreyle işveren primi; 
            ayrıca 6. bölgede işçi hissesi prim desteği 10 yıl süreyle sağlanır.</li>
            </ul>

            <h4>Dijital ve Yeşil Dönüşüm Programları</h4>
            <p>İlk kez <strong>Dijital Dönüşüm</strong> ve <strong>Yeşil Dönüşüm</strong> programları mevzuata girmiştir. 
            Amaç; dijitalleşme, otomasyon, döngüsel ekonomi ve düşük karbonlu üretim yatırımlarını teşvik etmektir.</p>

            <h4>Yeni Esaslar ve Yükümlülükler</h4>
            <ul>
            <li>Tüm işlemler <strong>E-TUYS</strong> sistemi üzerinden elektronik ortamda yürütülecektir.</li>
            <li>Büyük yatırımlar için <strong>Ekosistem Geliştirme Planı</strong> şartı getirilmiştir: 
            yatırımın %2’si Ar-Ge, eğitim veya sürdürülebilirlik projelerine ayrılmalıdır.</li>
            <li><strong>Asgari yatırım tutarı:</strong> 1. ve 2. bölgelerde 12 milyon TL, diğer bölgelerde 6 milyon TL olarak belirlenmiştir.</li>
            </ul>

            <h4>Sonuç</h4>
            <p><strong>2025/9903 sayılı Karar</strong>, yatırım teşvik sistemini tamamen yenileyerek 
            program bazlı, performans ve sürdürülebilirlik odaklı bir yapıya geçişi sağlamıştır. 
            Bu sayede üretim, ihracat ve yeşil dönüşüm hedefleri bir arada desteklenmektedir.</p>
            <p><em>İSFA YMM uzman kadrosu olarak, yeni dönemde yatırım teşvik belgesi alım ve uygulama süreçlerinde tam danışmanlık hizmeti sunuyoruz.</em></p>
        """,
        'publish_date': datetime(2025, 10, 20),
        'category': 'Yatırım Teşvik',
        'author': 'İSFA YMM',
        'tags': ['Yatırım Teşvik', '9903', 'İndirimli KV', '2025', 'Katkı Oranı'],
        'image_url': None
    }
]

@blog_bp.route('/')
def index():
    """Tüm blog yazılarını listeleme sayfası."""
    # latest_posts sadece ana sayfada gösterildiği için, burada tüm blog_posts'u gönderiyoruz.
    return render_template('blog/blog_list.html', posts=blog_posts)

@blog_bp.route('/<string:slug>')
def detail(slug):
    """Tekil blog yazısı detay sayfası."""
    post = next((p for p in blog_posts if p['slug'] == slug), None)
    if post is None:
        abort(404) # Yazı bulunamazsa 404 hatası döndür

    return render_template('blog/blog_detail.html', post=post)