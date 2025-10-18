from flask import Blueprint, render_template, abort
from datetime import datetime # Dummy data için


blog_bp = Blueprint('blog', __name__, template_folder='../templates')


blog_posts = [
    {
        'title': '2025 Vergi Rehberi: İşletmeler İçin Önemli Değişiklikler',
        'slug': 'vergi-rehberi-2025',
        'summary': '2025 yılında vergi mevzuatında gerçekleşecek temel değişiklikler ve işletmelerin uyum süreçleri hakkında kapsamlı bir rehber.',
        'content': """
            <h3>2025 Vergi Rehberi Detayları</h3>
            <p>2025 yılı, vergi dünyasında birçok önemli değişikliği beraberinde getiriyor. Bu değişiklikler, hem küçük işletmeler hem de büyük kurumsal yapılar için ciddi sonuçlar doğurabilir. Bu rehberde, yeni vergi oranları, teşvik programları ve beyanname süreçlerindeki güncellemeler detaylı bir şekilde ele alınmıştır.</p>
            <h4>Yeni Vergi Oranları</h4>
            <p>Kurumlar vergisi ve KDV oranlarında yapılan ayarlamalar, işletmelerin finansal planlamalarını doğrudan etkileyecektir. Uzmanlarımız, bu oranların işletmenizin karlılığı üzerindeki potansiyel etkilerini analiz etmenize yardımcı olabilir.</p>
            <h4>Dijital Dönüşüm ve E-Belge Uygulamaları</h4>
            <p>E-fatura, e-arşiv ve diğer e-belge uygulamalarında yapılan son güncellemeler, dijitalleşme sürecinin hız kesmeden devam ettiğini gösteriyor. İşletmelerin bu süreçlere uyum sağlaması için gerekli adımlar ve dikkat edilmesi gereken noktalar...</p>
            <h4>Vergi Teşvikleri ve Destekler</h4>
            <p>Hükümetin Ar-Ge, inovasyon ve istihdamı desteklemek amacıyla sunduğu yeni vergi teşvikleri, işletmeler için önemli fırsatlar sunmaktadır. Bu teşviklerden nasıl faydalanabileceğiniz konusunda detaylı bilgi almak için bizimle iletişime geçin.</p>
            <p>Bu ve daha fazlası için ISFAYMM uzman ekibi her zaman yanınızda.</p>
        """,
        'publish_date': datetime(2025, 7, 1),
        'image_url': 'images/blog/blog1.jpg' # static/images/blog/ klasörünüzde olmalı
    },
    {
        'title': 'E-Fatura ve E-Arşiv Geçiş Süreci: Adım Adım Kılavuz',
        'slug': 'e-fatura-gecis-sureci',
        'summary': 'E-fatura ve e-arşiv uygulamalarına geçiş yapmak isteyen işletmeler için pratik bilgiler ve sıkça sorulan soruların cevapları.',
        'content': """
            <h3>E-Fatura ve E-Arşiv Geçiş Kılavuzu</h3>
            <p>Elektronik belge uygulamaları, günümüz iş dünyasının vazgeçilmez bir parçası haline geldi. E-fatura ve e-arşiv uygulamalarına geçiş, birçok işletme için hem bir zorunluluk hem de operasyonel verimlilik sağlayan bir fırsattır.</p>
            <p>Bu kılavuzda, geçiş sürecinde dikkat etmeniz gereken yasal yükümlülükler, teknik entegrasyon adımları ve sık karşılaşılan sorunlar için çözümler bulacaksınız. Unutmayın, doğru planlama ile bu süreç sorunsuz atlatılabilir.</p>
        """,
        'publish_date': datetime(2025, 6, 20),
        'image_url': 'images/blog/blog2.jpg'
    },
    {
        'title': 'KDV İadesi Püf Noktaları: Süreci Hızlandırın!',
        'slug': 'kdv-iadesi-puf-noktalari',
        'summary': 'KDV iadesi alırken süreci hızlandırmak ve olası riskleri minimize etmek için bilmeniz gereken pratik ipuçları.',
        'content': """
            <h3>KDV İadesi Sürecini Hızlandırma Yolları</h3>
            <p>KDV iadesi, işletmelerin nakit akışını olumlu etkileyen önemli bir süreçtir. Ancak bu süreç, mevzuatın karmaşıklığı ve detaylı evrak gereksinimi nedeniyle zaman zaman zorlayıcı olabilir.</p>
            <p>Bu yazımızda, KDV iadesi başvurularınızı daha hızlı sonuçlandırmanın yollarını, sıkça yapılan hataları ve iade sürecini sorunsuz tamamlamanız için pratik ipuçlarını bulacaksınız. Uzmanlarımızdan destek alarak iade sürecinizi en verimli şekilde yönetebilirsiniz.</p>
        """,
        'publish_date': datetime(2025, 6, 10),

    },
]

@blog_bp.route('/')
def index():
    """Tüm blog yazılarını listeleme sayfası."""
    # latest_posts sadece ana sayfada gösterildiği için, burada tüm blog_posts'u gönderiyoruz.
    return render_template('blog_list.html', posts=blog_posts)

@blog_bp.route('/<string:slug>')
def detail(slug):
    """Tekil blog yazısı detay sayfası."""
    post = next((p for p in blog_posts if p['slug'] == slug), None)
    if post is None:
        abort(404) # Yazı bulunamazsa 404 hatası döndür

    return render_template('blog_detail.html', post=post)