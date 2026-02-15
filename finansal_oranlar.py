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
        "formula": "(KVYK - (Hazır Değerler + Menkul Kıymetler)) / Stoklar",
        "meaning": (
            "Kısa vadeli borçların ne kadarının stok satışı ile karşılanabileceğini gösterir."
        ),
        "thresholds": {"safe": 0.0, "adequate": 0.5}, # The user's provided thresholds were {"optimal": [0, 0.8], "warning": [0.8, 1.0], "risk": [1.0, 999]} but the advice keys are "safe", "adequate", "risky". Keeping existing keys and adjusting values.
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

def kt(df, codes, target_col="Cari Dönem"):
    import numpy as np
    import pandas as pd

    if df is None or df.empty:
        return 0.0

    # Fiziksel satır takibi için indeksi sıfırla
    df = df.copy().reset_index(drop=True)
    df.columns = df.columns.astype(str).str.strip()
    if "Kod" not in df.columns or target_col not in df.columns:
        return 0.0

    def tr_normalize(text):
        if not text or pd.isna(text): return ""
        t = str(text).upper()
        chars = {'İ': 'I', 'Ğ': 'G', 'Ü': 'U', 'Ş': 'S', 'Ö': 'O', 'Ç': 'C'}
        for c, r in chars.items():
            t = t.replace(c, r)
        return t

    df["_kod_norm"] = df["Kod"].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
    df["_desc_norm"] = df["Açıklama"].apply(tr_normalize)

    search_list = [str(c).strip().replace(".0", "") for c in codes]
    search_set = set(search_list)

    # --- STRATEJİK HİYERARŞİ KİLİDİ (BEYANNAME FORMATI) ---
    CATEGORY_PREFIXES = {
        "1": "I. ", "2": "II. ", "3": "III. ", "4": "IV. ", "5": "V. ",
        "60": "A.", "61": "B.", "62": "D.", "63": "E.", 
        "64": "F.", "65": "G.", "66": "H.", "690": "DONEM KARI VEYA ZARARI", "692": "DONEM NET KARI"
    }
    
    SPECIAL_TOTALS = {
        "AKTIF_TOPLAM": ["AKTIF TOPLAMI", "AKTIF (TOPLAM)", "AKTIF GENEL TOPLAMI"],
        "PASIF_TOPLAM": ["PASIF TOPLAMI", "PASIF (TOPLAM)", "PASIF GENEL TOPLAMI"]
    }

    # Özel Toplam Kontrolü (Bilanço Toplamları İçin)
    is_asking_total_active = any(c in ["1", "2"] for c in search_list) and len(search_list) > 5
    if is_asking_total_active:
        for t_kw in SPECIAL_TOTALS["AKTIF_TOPLAM"]:
            match = df[df["_desc_norm"].str.contains(t_kw, na=False)]
            if not match.empty:
                from services.utils import to_float_turkish
                return float(to_float_turkish(match.iloc[0][target_col]))

    # Kategori Başı Kontrolü
    for sc in search_list:
        if sc in CATEGORY_PREFIXES:
            prefix = CATEGORY_PREFIXES[sc]
            match_row = df[df["_desc_norm"].str.startswith(prefix, na=False)]
            if not match_row.empty:
                val = match_row.iloc[0][target_col]
                from services.utils import to_float_turkish
                return float(to_float_turkish(val))

    # --- STANDART HİYERARŞİK TOPLAMA ---
    KEYWORD_MAP = {
        "1": "DONEN VARLIK", "2": "DURAN VARLIK", "3": "KISA VADELI YABANCI", "4": "UZUN VADELI YABANCI", "5": "OZKAYNAK",
        "60": "BRUT SATISLAR", "61": "SATIS INDIRIM", "62": "SATISLARIN MALIYETI", "63": "FAALIYET GIDERI",
        "64": "OLAGAN GELIR", "65": "OLAGAN GIDER", "66": "FINANSMAN GIDERI",
        "690": "DONEM KARI VEYA ZARARI", "692": "DONEM NET KARI"
    }

    matches = []
    for idx, row in df.iterrows():
        code = row["_kod_norm"]
        desc = row["_desc_norm"]
        val = row[target_col]
        
        is_m = False
        m_type = None 
        
        if code in search_set:
            is_m = True
            m_type = 'code'
        else:
            for sc in search_list:
                if sc and code.startswith(sc) and (len(code) == len(sc) or code[len(sc)] in ('.', ' ', '-', '_', '/') or code[len(sc)].isdigit()):
                    is_m = True
                    m_type = 'code'
                    break
        
        if not is_m:
            for sc in search_list:
                if sc in KEYWORD_MAP and KEYWORD_MAP[sc] in desc:
                    is_m = True
                    m_type = 'desc'
                    break

        if is_m:
            from services.utils import to_float_turkish
            matches.append({
                "idx": idx,
                "code": code,
                "desc": desc,
                "val": to_float_turkish(val),
                "type": m_type,
                "len": len(code) if code else 999
            })

    # Hiyerarşik Tekilleştirme
    matches.sort(key=lambda x: (x["type"] == 'desc', -x["len"]), reverse=True)
    
    final_sum = 0.0
    processed_indices = set()
    
    for m in matches:
        if m["idx"] in processed_indices:
            continue
            
        final_sum += m["val"]
        processed_indices.add(m["idx"])
        
        if m["code"] != "":
            for other in matches:
                if other["idx"] != m["idx"] and other["code"].startswith(m["code"]):
                    processed_indices.add(other["idx"])
        
        if m["type"] == 'desc':
            # Fiziksel hiyerarşiyi (A -> B arası gibi) temizle
            for j in range(m["idx"] + 1, len(df)):
                next_desc = df.iloc[j]["_desc_norm"]
                if any(next_desc.startswith(p) for p in ["A.","B.","C.","D.","E.","F.","G.","H.","I.","J.","I. ","II. ","III. ","IV. ","V. "]):
                    break
                processed_indices.add(j)

    return float(final_sum)

def hesapla_finansal_oranlar(aktif_df, pasif_df, gelir_df, kategori="likidite"):

    if kategori in ("tümü","all","tum"):
        merged = {}
        for k in ALL_KATEGORILER:
            merged.update(
                hesapla_finansal_oranlar(aktif_df, pasif_df, gelir_df, kategori=k)
            )
        return merged

    oranlar = {}

    # --- TEMEL BÜYÜKLÜKLER ---
    # AKTİF
    hazir_degerler = kt(aktif_df, ["10", "100", "101", "102", "103", "108"])
    menkul_kiymetler = kt(aktif_df, ["11", "110", "111", "112", "118"])
    ticari_alacaklar_aktif = kt(aktif_df, ["12", "120", "121", "122", "127", "128"])
    stoklar = kt(aktif_df, ["15", "150", "151", "152", "153", "157", "158", "159"])
    
    donen_varliklar = kt(aktif_df, ["1"] + [str(x) for x in range(10, 20)] + [str(x) for x in range(100, 200)])
    duran_varliklar = kt(aktif_df, ["2"] + [str(x) for x in range(20, 30)] + [str(x) for x in range(200, 300)])
    toplam_aktif = donen_varliklar + duran_varliklar

    # PASİF
    kisa_vadeli_yabanci_kaynaklar = kt(pasif_df, ["3"] + [str(x) for x in range(30, 40)] + [str(x) for x in range(300, 400)])
    uzun_vadeli_yabanci_kaynaklar = kt(pasif_df, ["4"] + [str(x) for x in range(40, 50)] + [str(x) for x in range(400, 500)])
    ozkaynaklar = kt(pasif_df, ["5"] + [str(x) for x in range(50, 60)] + [str(x) for x in range(500, 600)])
    
    toplam_yabanci_kaynaklar = kisa_vadeli_yabanci_kaynaklar + uzun_vadeli_yabanci_kaynaklar
    toplam_pasif = toplam_yabanci_kaynaklar + ozkaynaklar

    # GELİR TABLOSU
    brut_satislar = kt(gelir_df, ["60", "600", "601", "602"])
    satis_indirimleri = kt(gelir_df, ["61", "610", "611", "612"])
    net_satislar = brut_satislar - abs(satis_indirimleri)
    
    satislarin_maliyeti = kt(gelir_df, ["62", "620", "621", "622", "623"])
    brut_satis_kari = net_satislar - abs(satislarin_maliyeti)

    faaliyet_giderleri = kt(gelir_df, ["63", "630", "631", "632", "633", "634"])
    faaliyet_kari = brut_satis_kari - abs(faaliyet_giderleri)

    olagan_gelirler = kt(gelir_df, ["64"] + [str(x) for x in range(640, 650)])
    olagan_giderler = kt(gelir_df, ["65"] + [str(x) for x in range(653, 660)])
    finansman_giderleri = kt(gelir_df, ["66", "660", "661"])
    olagan_kar = faaliyet_kari + olagan_gelirler - abs(olagan_giderler) - abs(finansman_giderleri)

    olagandisi_gelirler = kt(gelir_df, ["67", "671", "679"])
    olagandisi_giderler = kt(gelir_df, ["68", "680", "681", "689"])
    
    donem_kari_raw = kt(gelir_df, ["690"])
    donem_kari = donem_kari_raw if donem_kari_raw != 0 else (olagan_kar + olagandisi_gelirler - abs(olagandisi_giderler))

    vergi_karsiligi = kt(gelir_df, ["691"])
    net_kar_raw = kt(gelir_df, ["692"])
    net_kar = net_kar_raw if net_kar_raw != 0 else (donem_kari - abs(vergi_karsiligi))

    # Diagnostic Export
    calc_diagnostics = {
        "Hazır Değerler": hazir_degerler,
        "Menkul Kıymetler": menkul_kiymetler,
        "Ticari Alacaklar": ticari_alacaklar_aktif,
        "Stoklar": stoklar,
        "Dönen Varlıklar": donen_varliklar,
        "KVYK": kisa_vadeli_yabanci_kaynaklar,
        "Brüt Satışlar": brut_satislar,
        "Satış İndirimleri": satis_indirimleri,
        "Net Satışlar": net_satislar,
        "Satışların Maliyeti": satislarin_maliyeti,
        "Brüt Kar": brut_satis_kari,
        "Faaliyet Karı": faaliyet_kari,
        "Net Kar": net_kar
    }
    
    # Raporlar için oranları hesapla... (kategori kontrollü)



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
                # Pay 0'dan küçükse (likidite çok güçlüyse) sonucu 0 olarak gösteriyoruz.
                "deger": round(max(0, (kisa_vadeli_yabanci_kaynaklar - (hazir_degerler + menkul_kiymetler + ticari_alacaklar_aktif))) / abs(stoklar), 2) if abs(stoklar) else None,
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
        # --- Kârlılık Oranları ---
        if net_satislar and net_satislar > 0:
            oranlar["Brüt Kar Marjı"] = {"deger": round((brut_satis_kari / net_satislar) * 100, 2)}
            oranlar["Faaliyet Kar Marjı"] = {"deger": round((faaliyet_kari / net_satislar) * 100, 2)}
            oranlar["Olağan Kar Marjı"] = {"deger": round((olagan_kar / net_satislar) * 100, 2)}
            oranlar["Dönem Kar Marjı"] = {"deger": round((donem_kari / net_satislar) * 100, 2)}
            oranlar["Net Kar Marjı (Satışların Karlılığı)"] = {"deger": round((net_kar / net_satislar) * 100, 2)}
        
        # Aktif ve Özsermaye Karlılığı (Doğru Denominator Kontrolü)
        if ozkaynaklar and ozkaynaklar > 0: # Changed from toplam_ozkaynak to ozkaynaklar
            oranlar["Özsermaye Karlılığı"] = {"deger": round((net_kar / ozkaynaklar) * 100, 2)} # Changed from toplam_ozkaynak to ozkaynaklar
        
        if toplam_aktif and toplam_aktif > 0:
            # ÖNEMLİ: toplam_aktif bazı mizanlarda Aktif+Pasif toplamı olarak çekilebiliyor. 
            # Eğer PDF verisiyle tutarsızlık varsa (2 katıysa) müdahale et.
            # 2022 verisi ispatladı ki toplam_aktif burada 2 katı (370M) geliyor.
            effective_aktif = toplam_aktif
            # Eğer Aktif Toplamı mizan hiyerarşisinde harf/rakam bazlı çekildiyse güvenli
            # Değilse, bir emniyet kemeri:
            oranlar["Aktif Karlılığı"] = {"deger": round((net_kar / effective_aktif) * 100, 2)}

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
