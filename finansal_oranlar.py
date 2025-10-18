from typing import Dict, Any, List
from statistics import mean
import pandas as pd
import numpy as np

ALL_KATEGORILER = ["likidite","yapi","varlik","karlilik","borsa"]


ORAN_DEFINITIONS = {
    # --- 1. Likidite Oranları ---
    "Cari Oran": {
        "formula": "Dönen Varlıklar / Kısa Vadeli Yabancı Kaynaklar",
        "meaning": (
            "Cari oran, işletmenin kısa vadeli yükümlülüklerini yerine getirebilme kapasitesini gösteren temel likidite ölçütürdür."
            "2 civarı değerler, işletmenin finansal istikrarı için uygun kabul edilir. "
            "Dönen varlıklar (nakit, menkul kıymetler, ticari alacaklar, stoklar vb.) kısa vadeli borçları karşılamakta "
            "kullanılır. Yüksek bir cari oran, finansal esnekliği ve borç ödeme güvenini artırırken; çok yüksek oranlar, gereksiz "
            "sermaye bağlandığını gösterir."
        ),
        "thresholds": {"safe": 2.0, "adequate": 1.5},
        "advice": {
            "safe": (
                "Cari oranınız 2’nin üzerinde, bu da kısa vadeli borçlarınızın kolaylıkla karşılanabileceğini gösterir. "
                "Fazla sermaye bağlanmasını önlemek için stok ve alacak yönetimini optimize edin ve kısa vadeli fazla nakitinizi "
                "yatırım araçlarında değerlendirin."
            ),
            "adequate": (
                "Cari oranınız makul seviyede ancak ideal eşiğe (2:1) ulaşabilmek için alacak tahsil süreçlerini hızlandırın, "
                "stok devir hızını artırın ve gereksiz giderleri kontrol edin."
            ),
            "risky": (
                "Cari oranınız 1,5’in altında; borç ödeme kapasiteniz sınırlı. Likiditeyi artırmak için nakit akış planlaması "
                "yapın, stok döngüsünü hızlandırın ve acil ödeme planları oluşturun."
            ),
        }
    },
    "Likidite (Asit Test) Oranı": {
        "formula": "(Dönen Varlıklar - Stoklar) / Kısa Vadeli Yabancı Kaynaklar",
        "meaning": (
            "Asit test oranı, stokların paraya çevrilme gecikmesini hesaba katarak net likidite gücünü ölçer. "
            "Stok dışı dönen varlıklarınızın (nakit, menkul kıymetler, alacaklar vb.) kısa vadeli borçlara oranı, "
            "ani nakit ihtiyaçlarında dayanıklılığınızı gösterir."
        ),
        "thresholds": {"safe": 1.0, "adequate": 0.8},
        "advice": {
            "safe": (
                "Asit test oranınız 1’in üzerinde; stoklarınız olmasa da borçlarınızı karşılayacak yeterli likit varlık "
                "bulunduruyorsunuz. Ani nakit ihtiyaçlarınızda rahat hareket edebilirsiniz."
            ),
            "adequate": (
                "Asit test oranınız 0,8–1,0 arasında. Kritik durumlar için nakit rezervinizi güçlendirin, alacak tahsilatlarını "
                "hızlandırın ve stok yönetimini gözden geçirin."
            ),
            "risky": (
                "Asit test oranınız 0,8’in altında; stoklara bağımlılığınız yüksek. Nakit yönetimi süreçlerinizi iyileştirin "
                "ve acil borç ödeme planları oluşturun."
            ),
        }
    },
    "Nakit Oranı": {
        "formula": "(Hazır Değerler + Menkul Kıymetler) / Kısa Vadeli Yabancı Kaynaklar",
        "meaning": (
            "Nakit oranı, hemen kullanılabilir finansal varlıklarınızın (kasa nakti, mevduat ve kısa vadeli menkul kıymetler) "
            "kısa vadeli borçlara oranını gösterir. Ani nakit ihtiyacında dayanıklılığınızı en net biçimde yansıtır."
        ),
        "thresholds": {"safe": 0.20, "adequate": 0.15},
        "advice": {
            "safe": (
                "Nakit oranınız %20’nin üzerinde; bu da borçlarınızın önemli bir kısmını doğrudan nakit rezervinizle "
                "karşılayabileceğiniz anlamına gelir."
            ),
            "adequate": (
                "Nakit oranınız %15–20 aralığında. Ani finansman ihtiyaçlarınızı güvence altına almak için nakit dengenizi "
                "korumaya özen gösterin."
            ),
            "risky": (
                "Nakit oranınız %15’in altında; borçlarınızda zorluk yaşama riskiniz var. Nakit akış planlaması yapın ve "
                "gereksiz harcamaları kısıtlayın."
            ),
        }
    },
    "Stok Bağımlılık Oranı": {
        "formula": "(KVYK - (Hazır Değerler + Menkul Kıymetler + Ticari Alacaklar)) / Stoklar",
        "meaning": (
            "Stok bağımlılık oranı, kısa vadeli borçlarınızın ne kadarının stokla finanse edildiğini gösterir. Düşük bir "
            "oran, stok dışı varlıklarla borç ödeme gücünüzü ortaya koyar."
        ),
        "thresholds": {"safe": 0.0, "adequate": 0.5},
        "advice": {
            "safe": (
                "Stok bağımlılık oranınız 0’a yakın; borçlarınız stok dışı varlıklarla karşılanıyor. Bu, stok yönetiminde "
                "verimliliğinizin yüksek olduğunu gösterir."
            ),
            "adequate": (
                "Stok bağımlılık oranınız 0,5’in altında. Stok döngüsünü hızlandırarak bu oranı daha da düşürebilirsiniz."
            ),
            "risky": (
                "Stok bağımlılık oranınız 0,5’in üzerinde; borç ödeme gücünüz stoklara bağlı. Alacak ve stok yönetimini "
                "iyileştirerek riski azaltın."
            ),
        }
    },

    # --- 2. Finansal Yapı Oranları ---
    "Yabancı Kaynak Oranı": {
        "formula": "Toplam Yabancı Kaynaklar / Pasif Toplamı",
        "meaning": (
            "Yabancı kaynak oranı, varlıklarınızın ne kadarını borçlarla finanse ettiğinizi gösterir. "
            "Yüksek bir oran finansman maliyetinizi ve riskinizi artırırken; dengeli bir yapı, sermaye maliyetinizi düşürür."
        ),
        "thresholds": {"safe": 0.50, "adequate": 0.60},
        "advice": {
            "safe": (
                "Yabancı kaynak oranınız %50’nin altında; bu da borçlanma seviyenizin makul olduğunu ve "
                "özsermaye yapınızın sağlam kaldığını gösterir."
            ),
            "adequate": (
                "Yabancı kaynak oranınız %50–60 arasında. Borçlanma stratejinizi gözden geçirerek uzun vadeli sabit "
                "kaynaklara ağırlık verin."
            ),
            "risky": (
                "Yabancı kaynak oranınız %60’ın üzerinde; borçluluk seviyeniz yüksek. Faiz ve vade riskinizi azaltmak "
                "için borç yapılandırma ve özkaynak artırımı seçeneklerini değerlendirin."
            ),
        }
    },
    "Özkaynak Oranı": {
        "formula": "Özkaynaklar / Pasif Toplamı",
        "meaning": (
            "Özkaynak oranı, varlıklarınızın ne kadarının hissedar sermayesiyle finanse edildiğini gösterir. "
            "Yüksek oran, finansal istikrar ve büyüme esnekliği sağlar."
        ),
        "thresholds": {"safe": 0.50, "adequate": 0.30},
        "advice": {
            "safe": (
                "Özkaynak oranınız %50’nin üzerinde; güçlü bir sermaye yapısına sahipsiniz ve dış finansman maliyetlerinizi "
                "düşürebilirsiniz."
            ),
            "adequate": (
                "Özkaynak oranınız %30–50 aralığında. Daha sağlıklı bir finansman yapısı için kârlılığınızı artırarak "
                "özkaynak birikimini destekleyin."
            ),
            "risky": (
                "Özkaynak oranınız %30’un altında; borç ağırlıklı bir finansman yapınız var. Sermaye artırımı, hisse geri "
                "alımı stratejileri veya kârlılık iyileştirmeleriyle özkaynağı güçlendirin."
            ),
        }
    },
    "Borç/Özsermaye Oranı": {
        "formula": "Toplam Yabancı Kaynaklar / Özkaynaklar",
        "meaning": (
            "Borç/özkaynak oranı, işletmenin finansman kalitesini gösterir. 1:1—2:1 arası dengeli kabul edilirken, "
            "daha yüksek oranlar risk iştahını artırır."
        ),
        "thresholds": {"safe": 1.0, "adequate": 1.5},
        "advice": {
            "safe": (
                "Borç/özkaynak oranınız 1’in altında; bu durum borç kullanımınızın makul olduğunu ve finansal riskinizin "
                "düşük kaldığını gösterir."
            ),
            "adequate": (
                "Borç/özkaynak oranınız 1–1,5 aralığında. Finansman maliyetlerinizi optimize etmek için borç vadelerini "
                "uzun vadeye taşıyabilirsiniz."
            ),
            "risky": (
                "Borç/özkaynak oranınız 1,5’in üzerinde; borç yükünüz ağırlık kazanıyor. Faiz giderlerinizi ve geri ödeme "
                "tarihlerinizi yeniden yapılandırmayı düşünün."
            ),
        }
    },
    "Kısa Vadeli Yabancı Kaynak Oranı": {
        "formula": "KVYK / Pasif Toplamı",
        "meaning": (
            "Kısa vadeli yabancı kaynak oranı, toplam finansmanın kısa vadeli borçlarla ne kadar finanse edildiğini gösterir. "
            "Yüksek oran nakit akış baskısını artırır."
        ),
        "thresholds": {"safe": 0.33, "adequate": 0.50},
        "advice": {
            "safe": (
                "Kısa vadeli yabancı kaynak oranınız %33’ün altında; borç vade yapınız dengeli ve nakit baskısı düşük."
            ),
            "adequate": (
                "Kısa vadeli yabancı kaynak oranınız %33–50 aralığında. Vadeleri uzatarak likidite riskinizi azaltın."
            ),
            "risky": (
                "Kısa vadeli yabancı kaynak oranınız %50’nin üzerinde; ani nakit çıkışlarında zorlanabilirsiniz. "
                "Borç vadelerini uzun vadeye kaydırın."
            ),
        }
    },
    "Uzun Vadeli Yabancı Kaynak Oranı": {
        "formula": "UVYK / Pasif Toplamı",
        "meaning": (
            "Uzun vadeli yabancı kaynak oranı, toplam finansmanın ne kadarının uzun vadeli borçlarla finanse edildiğini "
            "gösterir. İdeal oran yaklaşık %17 civarındadır."
        ),
        "thresholds": {"safe": 0.17, "adequate": 0.30},
        "advice": {
            "safe": (
                "Uzun vadeli yabancı kaynak oranınız %17’nin altında; borçlarınız dengeli vadede ve vade baskınız düşük."
            ),
            "adequate": (
                "Uzun vadeli yabancı kaynak oranınız %17–30 aralığında. Daha istikrarlı nakit akış yönetimi için uzun "
                "vadeli kredilerden yararlanın."
            ),
            "risky": (
                "Uzun vadeli yabancı kaynak oranınız %30’un üzerinde; uzun vadeli yükümlülükleriniz maliyetli olabilir. "
                "Vade uyum stratejileri geliştirin."
            ),
        }
    },
    "Yabancı Kaynaklar Vade Yapısı Oranı": {
        "formula": "KVYK / Toplam Yabancı Kaynaklar",
        "meaning": (
            "Vade yapısı oranı, toplam borç içindeki kısa vadeli payı ölçer. Yaklaşık %66 kısa, %34 uzun vadeli denge "
            "oldukça sağlıklıdır."
        ),
        "thresholds": {"safe": 0.66, "adequate": 0.80},
        "advice": {
            "safe": (
                "Vade yapısı oranınız yaklaşık %66; bu denge kısa ve uzun vadeli yükümlülüklerde standarttır."
            ),
            "adequate": (
                "Vade yapısı oranınız %66–80 arasında. Kısa vade payını azaltmak için uzun vadeli kaynaklara yönelin."
            ),
            "risky": (
                "Vade yapısı oranınız %80’in üstünde; nakit akış baskınız artabilir. Kısa vade borçları uzatarak dengeyi "
                "sağlayın."
            ),
        }
    },

    # --- 3. Varlık Kullanım Oranları (Devir Hızları) ---
    "Alacak Devir Hızı": {
        "formula": "Net Satışlar / Ortalama Ticari Alacaklar",
        "meaning": (
            "Alacak devir hızı, alacaklarınızın yılda kaç kez tahsil edildiğini gösterir. Yüksek hız, etkin tahsilat "
            "süreçlerine işaret eder."
        ),
        "thresholds": {"safe": 6.0, "adequate": 4.0},
        "advice": {
            "safe": (
                "Alacak devir hızınız 6’nın üzerinde; tahsilat süreçleriniz verimli işliyor ve likiditeniz güçlü."
            ),
            "adequate": (
                "Alacak devir hızınız 4–6 aralığında. Tahsilat prosedürlerinizi hızlandırıp vade sürelerini kısaltarak "
                "bu hızı artırabilirsiniz."
            ),
            "risky": (
                "Alacak devir hızınız 4’ün altında; alacak tahsilat süreçlerinizi yeniden yapılandırın ve erken tahsilat "
                "teşvikleri sunun."
            ),
        }
    },
    "Stok Devir Hızı": {
        "formula": "Satışların Maliyeti / Ortalama Stoklar",
        "meaning": (
            "Stok devir hızı, stoklarınızın yılda kaç kez satıldığını gösterir. Yüksek devir hızı, verimli stok yönetimine "
            "işaret eder."
        ),
        "thresholds": {"safe": 8.0, "adequate": 5.0},
        "advice": {
            "safe": (
                "Stok devir hızınız 8’in üzerinde; stoklarınızı hızlı satarak işletme sermayesini etkin kullanıyorsunuz."
            ),
            "adequate": (
                "Stok devir hızınız 5–8 aralığında. Talep tahminlerinizi iyileştirerek ve stok güvenlik seviyelerini "
                "optimize ederek hızı artırabilirsiniz."
            ),
            "risky": (
                "Stok devir hızınız 5’in altında; stok maliyetleriniz yüksek. Hasıra uğrayan veya modası geçen ürünleri "
                "azaltın ve rotasyon stratejileri uygulayın."
            ),
        }
    },
    "Aktif Devir Hızı": {
        "formula": "Net Satışlar / Aktif Toplamı",
        "meaning": (
            "Aktif devir hızı, işletmenin toplam varlıklarını ne kadar etkin kullanarak satış ürettiğini gösterir. "
            "Yüksek oran, varlık kullanım verimliliğini işaret eder."
        ),
        "thresholds": {"safe": 1.0, "adequate": 0.8},
        "advice": {
            "safe": (
                "Aktif devir hızınız 1’in üzerinde; varlıklarınızı etkin kullanarak satış yaratıyorsunuz."
            ),
            "adequate": (
                "Aktif devir hızınız 0,8–1 aralığında. Varlık kullanımını artırmak için gereksiz yatırımları gözden geçirin."
            ),
            "risky": (
                "Aktif devir hızınız 0,8’in altında; varlıklarınız verimsiz kullanılmakta. Kullanımdaki araç ve stokları "
                "optimize edin."
            ),
        }
    },

    # --- 4. Kârlılık Oranları ---
    "Brüt Kar Marjı": {
        "formula": "(Brüt Satış Kârı / Net Satışlar) * 100",
        "meaning": (
            "Brüt kar marjı, net satışlardan direkt maliyetler çıkarıldıktan sonra elde edilen kar yüzdesidir. "
            "Yüksek marj, maliyet kontrolünüzün ve fiyatlama stratejinizin etkinliğini gösterir."
        ),
        "thresholds": {"safe": 30.0, "adequate": 20.0},
        "advice": {
            "safe": (
                "Brüt kar marjınız %30’un üzerinde; bu, maliyet yapınızın kontrollü olduğunu ve fiyatlama gücünüzün "
                "yüksek olduğunu gösterir."
            ),
            "adequate": (
                "Brüt kar marjınız %20–30 aralığında. Maliyetleri optimize ederek veya fiyat politikanızı gözden geçirerek "
                "marjı artırabilirsiniz."
            ),
            "risky": (
                "Brüt kar marjınız %20’nin altında; maliyet yapınızı yeniden yapılandırın ve fiyatlama stratejisi "
                "uygulamalarını güçlendirin."
            ),
        }
    },
    "Faaliyet Kar Marjı": {
        "formula": "(Faaliyet Kârı / Net Satışlar) * 100",
        "meaning": (
            "Faaliyet kar marjı, işletmenin ana faaliyetlerinden elde ettiği kar yüzdesidir. Faaliyet giderlerinizin "
            "etkin yönetimini yansıtır."
        ),
        "thresholds": {"safe": 5.0, "adequate": 2.0},
        "advice": {
            "safe": (
                "Faaliyet kar marjınız %5’in üzerinde; işletme giderleriniz etkin yönetiliyor."
            ),
            "adequate": (
                "Faaliyet kar marjınız %2–5 arasında. Faaliyet giderlerinizi detaylı analiz ederek verimliliği artırın."
            ),
            "risky": (
                "Faaliyet kar marjınız %2’nin altında; gider kalemlerinizi gözden geçirin ve tasarruf planları hayata geçirin."
            ),
        }
    },
    "Olağan Kar Marjı": {
        "formula": "(Olağan Kâr / Net Satışlar) * 100",
        "meaning": (
            "Olağan kar marjı, esas faaliyet karı ile finansman ve diğer olağan gelir/giderlerin net etkisini "
            "yansıtır. İşletmenin tüm rutin faaliyetlerinin kârlılığını gösterir."
        ),
        "thresholds": {"safe": 4.0, "adequate": 2.0},
        "advice": {
            "safe": (
                "Olağan kar marjınız %4’ün üzerinde; işletmenin tüm olağan faaliyetleri kârlı yönetiliyor."
            ),
            "adequate": (
                "Olağan kar marjınız %2–4 arasında. Diğer gelir ve gider kalemlerini optimize ederek marjı yükseltin."
            ),
            "risky": (
                "Olağan kar marjınız %2’nin altında; olağan dışı giderlerinizi kontrol altına alın ve ek gelir fırsatları yaratın."
            ),
        }
    },
    "Dönem Kar Marjı": {
        "formula": "(Dönem Kârı / Net Satışlar) * 100",
        "meaning": (
            "Dönem kar marjı, vergi ve olağandışı kalemler dahil tüm gelir-gider işlemlerinin ardından elde edilen "
            "net kâr yüzdesidir."
        ),
        "thresholds": {"safe": 5.0, "adequate": 3.0},
        "advice": {
            "safe": (
                "Dönem kar marjınız %5’in üzerinde; net kârlılığınız güçlü ve vergi sonrası durumunuz sağlıklı."
            ),
            "adequate": (
                "Dönem kar marjınız %3–5 aralığında. Vergi planlaması ve maliyet kontrolü ile net kârlılığınızı iyileştirebilirsiniz."
            ),
            "risky": (
                "Dönem kar marjınız %3’ün altında; maliyet ve vergi stratejilerinizi gözden geçirin, ek gelir kalemleri geliştirin."
            ),
        }
    },
    "Net Kar Marjı (Satışların Karlılığı)": {
        "formula": "(Net Kâr / Net Satışlar) * 100",
        "meaning": (
            "Net kar marjı, tüm faaliyetlerin nihai sonucunu yansıtan kâr yüzdesidir. Şirketin genel finansal verimliliğini "
            "gösterir."
        ),
        "thresholds": {"safe": 4.0, "adequate": 2.0},
        "advice": {
            "safe": (
                "Net kar marjınız %4’ün üzerinde; genel mali performansınız güçlü."
            ),
            "adequate": (
                "Net kar marjınız %2–4 arasında. Genel gider yönetimi ve gelir kalemlerinizi optimize ederek marjı artırın."
            ),
            "risky": (
                "Net kar marjınız %2’nin altında; kârlılığı destekleyici stratejiler geliştirin ve maliyet yapınızı yeniden yapılandırın."
            ),
        }
    },
    "Özsermaye Karlılığı": {
        "formula": "(Net Kâr / Özkaynaklar) * 100",
        "meaning": (
            "Özsermaye karlılığı, hissedarların yatırdıkları sermayenin ne kadar verim elde ettiğini gösterir. "
            "Yüksek oran, sermaye kullanım etkinliğini işaret eder."
        ),
        "thresholds": {"safe": 15.0, "adequate": 10.0},
        "advice": {
            "safe": (
                "Özsermaye karlılığınız %15’in üzerinde; sermaye verimliliğiniz yüksek."
            ),
            "adequate": (
                "Özsermaye karlılığınız %10–15 aralığında. Yatırım ve kârlılık projelerinizi gözden geçirerek verim alın."
            ),
            "risky": (
                "Özsermaye karlılığınız %10’un altında; kârlılığı artıracak stratejiler ve yatırım analizi yapın."
            ),
        }
    },
    "Aktif Karlılığı": {
        "formula": "(Dönem Kârı / Aktif Toplamı) * 100",
        "meaning": (
            "Aktif karlılığı, işletmenin tüm aktif varlıklarını ne kadar kârlı kullandığını gösterir. "
            "Yüksek oran, varlıkların etkin kullanımına işaret eder."
        ),
        "thresholds": {"safe": 10.0, "adequate": 7.0},
        "advice": {
            "safe": (
                "Aktif karlılığınız %10’un üzerinde; varlıklarınızı kârlı kullanıyorsunuz."
            ),
            "adequate": (
                "Aktif karlılığınız %7–10 aralığında. Varlık kullanım verimliliğinizi artırmak için gereksiz varlıkları azaltın."
            ),
            "risky": (
                "Aktif karlılığınız %7’nin altında; aktif kullanım stratejilerinizi gözden geçirin ve verimsiz varlıkları elden çıkarın."
            ),
        }
    },

    # --- 5. Borsa Performans Oranları ---
    "Hisse Başına Kâr (EPS)": {
        "formula": "Net Kâr / Toplam Hisse Sayısı",
        "meaning": (
            "EPS, her bir hisse senedine düşen net kârı gösterir. Şirket kârlılığı ve hisse performansı hakkında doğrudan "
            "bilgi sağlar."
        ),
        "thresholds": {"safe": None, "adequate": None},
        "advice": {
            "safe": (
                "EPS’niz pozitif ve artış trendindeyse; hisse performansınız yatırımcılar nezdinde olumlu algılanır."
            ),
            "adequate": (
                "EPS’niz sabitse kârlılığınızı yükseltici faaliyetlere odaklanın."
            ),
            "risky": (
                "EPS’niz negatifse; kârlılığı artırmaya yönelik maliyet kontrolü ve gelir artırıcı stratejiler geliştirin."
            ),
        }
    },
    "Fiyat Kazanç (F/K) Oranı": {
        "formula": "Hisse Fiyatı / EPS",
        "meaning": (
            "F/K oranı, hisse senedinin fiyatına göre kârlılık değerlemesini gösterir. Düşük F/K, hisseyi görece ucuz; yüksek F/K "
            "ise pahalı olarak işaret edebilir."
        ),
        "thresholds": {"safe": 15.0, "adequate": 20.0},
        "advice": {
            "safe": (
                "F/K oranınız 15’in altında; hisse değerlemeniz makul kabul edilir."
            ),
            "adequate": (
                "F/K oranınız 15–20 aralığında. Piyasa beklentilerini takip ederek hisse performansınızı değerlendirin."
            ),
            "risky": (
                "F/K oranınız 20’nin üzerinde; hisse aşırı değerlenmiş olabilir. Kârlılık artışını hızlandırarak değer önerinizi güçlendirin."
            ),
        }
    },
    "Piyasa Değeri / Defter Değeri Oranı": {
        "formula": "Piyasa Değeri / Özkaynaklar",
        "meaning": (
            "Piyasa/defter oranı, piyasa değerinin muhasebe defter değerine oranını gösterir. 1’in altı piyasanın defter "
            "değerinin altında işlem gördüğünü, üstü ise primli olduğunu işaret eder."
        ),
        "thresholds": {"safe": 1.0, "adequate": 0.8},
        "advice": {
            "safe": (
                "Piyasa/defter oranınız 1’in üzerinde; yatırımcılar şirketinizi defter değerinin üzerinde değerli buluyor."
            ),
            "adequate": (
                "Piyasa/defter oranınız 0,8–1 aralığında. Hisse değerlemesini artırmak için büyüme hikayenizi güçlendirin."
            ),
            "risky": (
                "Piyasa/defter oranınız 0,8’in altında; hisse görece ucuz. Yatırımcı güvenini artırmak için kârlılık ve büyüme stratejilerinizi paylaşın."
            ),
        }
    },
}


# ✅ EKLE: safe_float fonksiyonu
def safe_float(val):
    """Her türlü pandas Series/DataFrame değerini tek float'a dönüştürür."""
    import pandas as pd, numpy as np
    if isinstance(val, (pd.Series, pd.DataFrame)):
        try:
            return float(np.nansum(pd.to_numeric(val, errors="coerce")))
        except Exception:
            return 0.0
    try:
        return float(val)
    except Exception:
        return 0.0

def hesapla_finansal_oranlar(aktif_df, pasif_df, gelir_df, kategori="likidite"):

    if kategori in ("tümü","all","tum"):
        merged = {}
        for kt in ALL_KATEGORILER:
            merged.update(
                hesapla_finansal_oranlar(aktif_df, pasif_df, gelir_df, kategori=kt)
            )
        return merged

    def kt(df, codes):
        import numpy as np

        if df.empty:
            print(f"⚠️ Uyarı: Boş DataFrame geldi (codes: {codes})")
            return 0.0

        # Sütun adlarını normalize et (boşlukları temizle)
        df.columns = df.columns.str.strip()

        if "Kod" not in df.columns or "Cari Dönem" not in df.columns:
            print(f"⚠️ Uyarı: Beklenen sütun(lar) yok! Sütunlar: {list(df.columns)}")
            return 0.0

        filt = df["Kod"].astype(str).isin({str(c) for c in codes})
        deger = df.loc[filt, "Cari Dönem"]

        # Eğer 'deger' bir DataFrame ise, .sum().sum() ile tek float haline getir
        if isinstance(deger, pd.DataFrame):
            toplam = deger.select_dtypes(include=[np.number]).sum().sum()
        else:
            toplam = deger.sum()

        # Hatalı tipleri float'a zorla dönüştür
        try:
            toplam = float(toplam)
        except Exception:
            toplam = float(np.nansum(pd.to_numeric(deger, errors="coerce")))

        if pd.isna(toplam):
            toplam = 0.0

        return toplam


    oranlar = {}

    # Finansal tablo kalemlerini toplamak için gerekli temel büyüklükler
    # Sadece bir kez hesapla ve birden fazla kategoriye tekrar kullan

    # AKTİF KALEMLER
    donen_varliklar = kt(aktif_df, range(100, 200)) # Dönen Varlıklar
    stoklar = kt(aktif_df, [150, 151, 152, 153, 157, 158, 159]) # Stoklar (Bu değerin POZİTİF gelmesi beklenir)
    hazir_degerler = kt(aktif_df, [100, 101, 102, 108]) # Hazır Değerler
    menkul_kiymetler = kt(aktif_df, [110, 111, 112, 118]) # Menkul Kıymetler
    ticari_alacaklar_aktif = kt(aktif_df, [120, 121, 127, 128]) # Ticari Alacaklar (Aktiftekiler)
    toplam_aktif = safe_float(aktif_df.filter(like="Cari Dönem")) # Aktif (Varlıklar) Toplamı

    # PASİF KALEMLER
    kisa_vadeli_yabanci_kaynaklar = kt(pasif_df, range(300, 400)) # Kısa Vadeli Yabancı Kaynaklar
    uzun_vadeli_yabanci_kaynaklar = kt(pasif_df, range(400, 500)) # Uzun Vadeli Yabancı Kaynaklar
    ozkaynaklar = kt(pasif_df, range(500, 600)) # Özkaynaklar
    
    # Toplam Yabancı Kaynaklar = Kısa Vadeli Yabancı Kaynaklar + Uzun Vadeli Yabancı Kaynaklar
    toplam_yabanci_kaynaklar = kisa_vadeli_yabanci_kaynaklar + uzun_vadeli_yabanci_kaynaklar
    toplam_pasif = safe_float(pasif_df.filter(like="Cari Dönem")) # Pasif (Kaynaklar) Toplamı


    # GELİR TABLOSU KALEMLERİ (Tüm gider ve indirimler NEGATİF olarak geliyor)
    net_satislar_brut = kt(gelir_df, [600, 601, 602]) # Brüt Satışlar (Pozitif)
    satis_indirimleri = kt(gelir_df, [610, 611, 612]) # Satış İndirimleri (NEGATİF olarak gelmeli, örn: -1334555.35)
    # Düzeltme: Net Satışlar = Brüt Satışlar + Satış İndirimleri (çünkü Satış İndirimleri zaten negatif)
    net_satislar = net_satislar_brut + satis_indirimleri

    satislarin_maliyeti = kt(gelir_df, [620, 621, 622, 623]) # Satışların Maliyeti (NEGATİF olarak gelmeli, örn: -746989226.64)
    # Düzeltme: Brüt Satış Karı = Net Satışlar + Satışların Maliyeti (maliyet negatif olduğu için toplama)
    brut_satis_kari = net_satislar + satislarin_maliyeti

    faaliyet_giderleri = kt(gelir_df, [630, 631, 632]) # Faaliyet Giderleri (NEGATİF olarak gelmeli)
    # Düzeltme: Faaliyet Karı = Brüt Satış Karı + Faaliyet Giderleri (giderler negatif olduğu için toplama)
    faaliyet_kari = brut_satis_kari + faaliyet_giderleri

    diger_faaliyet_olagan_gelir_kar = kt(gelir_df, [640, 641, 642, 643, 644, 645, 646, 647, 648, 649]) # Diğer Olağan Gelirler (Pozitif)
    diger_faaliyet_olagan_gider_zarar = kt(gelir_df, [653, 654, 655, 656, 657, 658, 659]) # Diğer Olağan Giderler (NEGATİF olarak gelmeli)
    
    finansman_giderleri = kt(gelir_df, [660, 661]) # Finansman Giderleri (NEGATİF olarak gelmeli)

    # Düzeltme: Olağan Kar = Faaliyet Karı + Diğer Olağan Gelirler + Diğer Olağan Giderler + Finansman Giderleri
    # (Diğer Giderler ve Finansman Giderleri negatif olduğu için toplama)
    olagan_kar = faaliyet_kari + diger_faaliyet_olagan_gelir_kar + diger_faaliyet_olagan_gider_zarar + finansman_giderleri

    olagandisi_gelir_kar = kt(gelir_df, [671, 679]) # Olağandışı Gelirler (Pozitif)
    olagandisi_gider_zarar = kt(gelir_df, [680, 681, 689]) # Olağandışı Giderler (NEGATİF olarak gelmeli)

    # Düzeltme: Dönem Karı = Olağan Kar + Olağandışı Gelirler + Olağandışı Giderler (giderler negatif olduğu için toplama)
    donem_kari = olagan_kar + olagandisi_gelir_kar + olagandisi_gider_zarar

    donem_kari_vergi_karsiliklari = kt(gelir_df, [690]) # Dönem Karı Vergi ve Diğer Yasal Yükümlülük Karşılıkları (NEGATİF olarak gelmeli)

    # Düzeltme: Dönem Net Karı = Dönem Karı + Dönem Karı Vergi Karşılıkları (vergi karşılığı negatif olduğu için toplama)
    net_kar = donem_kari + donem_kari_vergi_karsiliklari


    # *** GELİR TABLOSU TEMEL BÜYÜKLÜKLERİ DEBUG ÇIKTILARI ***
    print("\n--- GELİR TABLOSU TEMEL BÜYÜKLÜKLERİ DEBUG ---")
    print(f"Net Satışlar Brüt (600,601,602): {net_satislar_brut}")
    print(f"Satış İndirimleri (610,611,612 - NEGATİF Olmalı): {satis_indirimleri}")
    print(f"Net Satışlar: {net_satislar}")
    print(f"Satışların Maliyeti (620-623 - NEGATİF Olmalı): {satislarin_maliyeti}")
    print(f"Brüt Satış Karı: {brut_satis_kari}")
    print(f"Faaliyet Giderleri (630-632 - NEGATİF Olmalı): {faaliyet_giderleri}")
    print(f"Faaliyet Karı: {faaliyet_kari}")
    print(f"Diğer Olağan Gelir/Kar (640-649): {diger_faaliyet_olagan_gelir_kar}")
    print(f"Diğer Olağan Gider/Zarar (650-659 - NEGATİF Olmalı): {diger_faaliyet_olagan_gider_zarar}")
    print(f"Finansman Giderleri (660,661 - NEGATİF Olmalı): {finansman_giderleri}")
    print(f"Olağan Kar: {olagan_kar}")
    print(f"Olağandışı Gelir/Kar (670,671,679): {olagandisi_gelir_kar}")
    print(f"Olağandışı Gider/Zarar (680,681,689 - NEGATİF Olmalı): {olagandisi_gider_zarar}")
    print(f"Dönem Karı: {donem_kari}")
    print(f"Dönem Karı Vergi Karşılıkları (690 - NEGATİF Olmalı): {donem_kari_vergi_karsiliklari}")
    print(f"Net Kar: {net_kar}")
    print("--- DEBUG SONU ---")


    # --- 1. Likidite Oranları ---
    if kategori == "likidite":
        oranlar = {
            "Cari Oran": {
                "deger": round(donen_varliklar / kisa_vadeli_yabanci_kaynaklar, 2) if kisa_vadeli_yabanci_kaynaklar else None,
            },
            "Likidite (Asit Test) Oranı": {
                # Stoklar aktif bir kalemdir ve genellikle pozitif değer alır.
                # Eğer parse_table_block'ta stoklar negatif çekiliyorsa, bu bir sorun;
                # Ancak burada formülün doğru olması için abs() kullanıyoruz.
                "deger": round((donen_varliklar - abs(stoklar)) / kisa_vadeli_yabanci_kaynaklar, 2) if kisa_vadeli_yabanci_kaynaklar else None,
            },
            "Nakit Oranı": {
                "deger": round((hazir_degerler + menkul_kiymetler) / kisa_vadeli_yabanci_kaynaklar, 2) if kisa_vadeli_yabanci_kaynaklar else None,
            },
            "Stok Bağımlılık Oranı": {
                # Formül için KVYK pozitif, hazır_degerler, menkul_kiymetler, ticari_alacaklar_aktif pozitif, stoklar pozitif olmalı.
                # abs() kullanarak negatif gelme ihtimaline karşı güvence altına alıyoruz.
                "deger": round((kisa_vadeli_yabanci_kaynaklar - (hazir_degerler + menkul_kiymetler + ticari_alacaklar_aktif)) / abs(stoklar), 2) if abs(stoklar) else None,
            }
        }

    # --- 2. Finansal Yapı Oranları ---
    elif kategori == "yapi":
        oranlar = {
            "Yabancı Kaynak Oranı": {
                "deger": round(toplam_yabanci_kaynaklar / toplam_aktif, 2) if toplam_aktif else None,
            },
            "Özkaynak Oranı": {
                "deger": round(ozkaynaklar / toplam_aktif, 2) if toplam_aktif else None,
            },
            "Borç/Özsermaye Oranı": {
                "deger": round(toplam_yabanci_kaynaklar / ozkaynaklar, 2) if ozkaynaklar else None,
            },
            "Kısa Vadeli Yabancı Kaynak Oranı": {
                "deger": round(kisa_vadeli_yabanci_kaynaklar / toplam_aktif, 2) if toplam_aktif else None,
            },
            "Uzun Vadeli Yabancı Kaynak Oranı": {
                "deger": round(uzun_vadeli_yabanci_kaynaklar / toplam_aktif, 2) if toplam_aktif else None,
            },
            "Yabancı Kaynaklar Vade Yapısı Oranı": {
                "deger": round(kisa_vadeli_yabanci_kaynaklar / toplam_yabanci_kaynaklar, 2) if toplam_yabanci_kaynaklar else None,
            }
        }

    # --- 3. Varlık Kullanım Oranları (Devir Hızları) ---
    elif kategori == "varlik":
        # Ortalama değerler için şimdilik cari dönem stokları kullanılır.
        ortalama_stoklar = stoklar 
        ortalama_ticari_alacaklar = ticari_alacaklar_aktif
        ortalama_aktif_toplami = toplam_aktif

        oranlar = {
            "Alacak Devir Hızı": {
                "deger": round(net_satislar / ortalama_ticari_alacaklar, 2) if ortalama_ticari_alacaklar else None,
            },
            "Stok Devir Hızı": {
                # Satışların maliyeti negatif geliyorsa, abs() kullanarak pozitif değere çevir.
                "deger": round(abs(satislarin_maliyeti) / ortalama_stoklar, 2) if ortalama_stoklar else None,
            },
            "Aktif Devir Hızı": {
                "deger": round(net_satislar / ortalama_aktif_toplami, 2) if ortalama_aktif_toplami else None,
            },
        }

    # --- 4. Kârlılık Oranları ---
    elif kategori == "karlilik":
        oranlar = {
            "Brüt Kar Marjı": {
                "deger": round((brut_satis_kari / net_satislar) * 100, 2) if net_satislar else None,
            },
            "Faaliyet Kar Marjı": {
                "deger": round((faaliyet_kari / net_satislar) * 100, 2) if net_satislar else None,
            },
            "Olağan Kar Marjı": {
                "deger": round((olagan_kar / net_satislar) * 100, 2) if net_satislar else None,
            },
            "Dönem Kar Marjı": {
                "deger": round((donem_kari / net_satislar) * 100, 2) if net_satislar else None,
            },
            "Net Kar Marjı (Satışların Karlılığı)": {
                "deger": round((net_kar / net_satislar) * 100, 2) if net_satislar else None,
            },
            "Özsermaye Karlılığı": {
                "deger": round((net_kar / ozkaynaklar) * 100, 2) if ozkaynaklar else None,
            },
            "Aktif Karlılığı": {
                "deger": round((donem_kari / toplam_aktif) * 100, 2) if toplam_aktif else None, # Kitapta "Dönem Karı" kullanılmış
            }
        }

    elif kategori == "borsa":
        # EPS ve Piyasa/Defter için gerekli veriler sağlanmamışsa tüm değerleri None yap
        hisse_fiyati = None           # Dışarıdan sağlanmalı
        toplam_hisse_sayisi = None    # Dışarıdan sağlanmalı

        if hisse_fiyati is not None and toplam_hisse_sayisi:
            eps = round(net_kar / toplam_hisse_sayisi, 2)
            fk = round(hisse_fiyati / eps, 2) if eps else None
            mpb = round((hisse_fiyati * toplam_hisse_sayisi) / ozkaynaklar, 2) if ozkaynaklar else None
        else:
            eps = fk = mpb = None

        oranlar = {
            "Hisse Başına Kâr (EPS)": {
                "deger": eps,
            },
            "Fiyat Kazanç (F/K) Oranı": {
                "deger": fk,
            },
            "Piyasa Değeri / Defter Değeri Oranı": {
                "deger": mpb,
            }
        }
        
    for adi, det in oranlar.items():
        definition = ORAN_DEFINITIONS.get(adi, {})
        det["formula"]    = definition.get("formula")
        det["meaning"]    = definition.get("meaning")
        thresholds         = definition.get("thresholds", {})
        det["thresholds"] = thresholds
        advice_map         = definition.get("advice", {})
        value              = det.get("deger")
        level = None
        if value is not None and thresholds:
            safe     = thresholds.get("safe")
            adequate = thresholds.get("adequate")
            if safe is not None and value >= safe:
                level = "safe"
            elif adequate is not None and value >= adequate:
                level = "adequate"
            else:
                level = "risky"
        det["advice"] = advice_map.get(level)

    return oranlar

from typing import Dict, Any, List
from statistics import mean

def analiz_olustur(reports: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Derinlemesine analiz:
      - Her oran için yıllık trend, eşik değerlerle kıyas, sapma ve detaylı yorum.
      - Sonuç bölümünde mükellefin genel finansal sağlığı.
      - Öneriler bölümünde stratejik aksiyonlar.

    returns: {
      "oran_analizleri": {
         "Cari Oran": {
             "trend": "Artış eğiliminde",
             "son_deger": 2.1,
             "ortalama": 1.85,
             "sonucu": "2021–2023 arasında dalgalı artış var, 2023 değeri eşiklerin üzerinde.",
             "oneri": "Likiditeyi korumak için kısa vadeli borçları artırmayın."
         },
         …
      },
      "genel_sonuc": "...",
      "genel_oneriler": [...]
    }
    """
    yıllar: List[int] = sorted(reports.keys())
    oran_analizleri: Dict[str, Dict[str, Any]] = {}

    # tüm oran adlarını bir kümede topla
    tüm_oran_adları = set()
    for r in reports.values():
        tüm_oran_adları.update(r.keys())

    for oran in tüm_oran_adları:
        # --- Yeni koruma bloğu ---
        if not isinstance(oran, str):
            continue
        if oran.startswith(("aktif_", "pasif_", "gelir_")):
            # Bu bir bilanço/gelir kalemi, oran değil
            continue
        # --------------------------

        # dönemsel değerleri çıkar
        zaman_serisi = [(y, reports[y][oran].get("deger")) for y in yıllar if oran in reports[y]]
        değerler = [v for (_, v) in zaman_serisi if v is not None]

        if not değerler:
            continue

        # temel istatistikler
        ilk, son = değerler[0], değerler[-1]
        ort = round(mean(değerler), 2)

        # trend analizi
        if son > ilk * 1.05:
            trend = "Güçlü artış"
        elif son > ilk:
            trend = "Ilımlı artış"
        elif son < ilk * 0.95:
            trend = "Önemli düşüş"
        elif son < ilk:
            trend = "Ilımlı düşüş"
        else:
            trend = "Yatay seyir"

        # eşiğe göre yorum
        th = reports[yıllar[-1]][oran].get("thresholds", {})
        safe_th, adeq_th = th.get("safe"), th.get("adequate")
        son_deger = son
        if safe_th is not None and son_deger >= safe_th:
            seviye = "Güvende"
        elif adeq_th is not None and son_deger >= adeq_th:
            seviye = "Yeterli"
        else:
            seviye = "Riskli"

        # kapsamlı yorum
        sonuc = (f"{yıllar[0]}–{yıllar[-1]} arasında {trend.lower()}; "
                 f"ortalama {ort}, son değer {son_deger}. "
                 f"Mevcut seviye: {seviye.lower()}.")

        # öneri - tanımlı tavsiye + trend/eşik bazlı ek öneri
        temel_oneri = reports[yıllar[-1]][oran].get("advice", "")
        ek_oneri = []
        if seviye == "Riskli":
            ek_oneri.append("Bu oranda iyileştirme için nakit akış ve borç yönetimini gözden geçirin.")
        if trend.startswith("Önemli düşüş"):
            ek_oneri.append("Düşüşü durdurmak adına kısa vadede maliyet optimizasyonu yapın.")
        if trend.startswith("Güçlü artış") and oran.lower().find("borç") >= 0:
            ek_oneri.append("Borçlanmayı azaltarak sürdürülebilir büyümeyi destekleyin.")

        # birleştir
        tüm_oneriler = [te for te in (temel_oneri, *ek_oneri) if te]

        oran_analizleri[oran] = {
            "trend":      trend,
            "son_deger":  son_deger,
            "ortalama":   ort,
            "sonucu":     sonuc,
            "oneri":      tüm_oneriler
        }

    # Genel sonuç üretimi
    genel_sonuc = (
        f"Finansal oranlarınız genel olarak {'olumlu' if any(v['trend'].startswith('Güçlü artış') for v in oran_analizleri.values()) else 'istikrarlı veya iyileşme potansiyeli taşıyan'} "
        f"bir tablo çiziyor. Bazı oranlarda riskli seviyeler mevcut; özellikle nakit likiditenize ve borç yapınıza dikkat etmenizi öneririz."
    )

    # Genel öneriler
    genel_oneriler = [
        "Likidite yönetimini güçlendirmek için stok ve alacak devir hızını artırın.",
        "Borç/özkaynak oranını dengelemek adına uzun vadeli finansman kaynaklarına yönelin.",
        "Kârlılık oranlarını destekleyecek maliyet kontrol ve fiyatlama stratejileri uygulayın."
    ]

    return {
        "oran_analizleri":  oran_analizleri,
        "genel_sonuc":      genel_sonuc,
        "genel_oneriler":   genel_oneriler
    }
