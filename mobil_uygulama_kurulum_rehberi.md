# İSFA Mobil Uygulama & Web Entegrasyonu Kurulum Rehberi

Bu dosya, mobil uygulamanın (`isfa-mobile`) ve web backend (Flask) sunucusunun sorunsuz çalıştırılması, geliştirme aşamasındaki bağlantı sorunlarının çözümü ve bu projede yaptığımız düzeltmeleri kaydetmek amacıyla oluşturulmuştur. Yeni bir oturumda AI asistanına (Antigravity) bu dosyayı okumasını (veya referans almasını) söylerseniz, sıfırdan analiz yapmasına gerek kalmadan kaldığınız yerden hemen devam edebilir.

## 1. Çalıştırma Adımları (Geliştirme Ortamı)

Mobil uygulama webviev ile yerel bilgisayardaki (localhost) Flask sunucusuna bağlanmaktadır. Emülatörün yerel bilgisayara erişebilmesi için **ADB Tüneli (Reverse Port Forwarding)** kullanıyoruz. 

Baştan başlatmak için şu adımları sırayla izleyin:

### Adım 1: Flask Sunucusunu Başlatma
1. `webuygulama` dizininde terminali açın.
2. `python app.py` komutuyla sunucuyu başlatın.
   > *Not: Sunucu `0.0.0.0` üzerinde çalışacak şekilde yapılandırıldı, ancak `localhost:5000` üzerinden erişeceğiz.*

### Adım 2: ADB Port Yönlendirmesini (Tünel) Kurma
Emülatör açıldıktan (Android Studio Device Manager üzerinden başlatıldıktan) sonra, emülatörün 5000 portunu bilgisayarın 5000 portuna bağlamak için komut satırında şunu çalıştırın:
```bash
C:\Users\lalel\AppData\Local\Android\Sdk\platform-tools\adb.exe reverse tcp:5000 tcp:5000
```
*(Expo için gerekirse 8081 portu da benzer şekilde `adb reverse tcp:8081 tcp:8081` ile yönlendirilebilir).*

### Adım 3: Expo ile Mobil Uygulamayı Başlatma
1. `webuygulama/isfa-mobile` klasöründe yeni bir terminal açın.
2. `npx expo start --android` komutunu çalıştırın.
3. Uygulama emülatörde açılacak ve sorunsuz bir şekilde Flask `localhost:5000`'e bağlanacaktır.

---

## 2. Karşılaştığımız Sorunlar ve Yapılan Düzeltmeler

Oturumumuz boyunca çözülen kritik hatalar ve mimari kararlar aşağıdadır:

### a. Bağlantı Sorunları (Timeout & Siyah Ekran)
- **Sorun:** Emülatör `127.0.0.1`'e gitmeye çalıştığında kendi içine bağlanıyordu. `10.0.2.2` kullanıldığında ise Windows Firewall takılıyordu. WebView siyah ekran veriyordu.
- **Çözüm:** `isfa-mobile/src/api/config.js` içinde API adresi `localhost:5000` olarak bırakıldı. Yerine Windows Güvenlik Duvarı'nı aşmak için **ADB Reverse TCP** tüneli kullanıldı.

### b. Windows Konsol Encoding (Emoji) Çökmeleri
- **Sorun:** `routes/indirimlikurumlar.py` içindeki debug `print()` komutlarında bulunan emojiler (🔔, 🚀) Windows (Watchdog) ortamında `UnicodeEncodeError` oluşturup serverı çökertiyordu.
- **Çözüm:** Emojiler Python route dosyalarından temizlendi ve `app.py` dosyasının en üstüne `sys.stdout.reconfigure(encoding='utf-8')` komutu eklendi.

### c. Syntax Hataları (Unexpected Indent & Blueprint Bozulmaları)
- **Sorun:** Dosyalar düzenlenirken oluşan `('', , '/')` gibi hatalı Blueprint tanımları Flask'ın açılmasını engelliyordu.
- **Çözüm:** `admin_routes.py`, `calculators.py` ve `mobile_api.py` gibi dosyalardaki bozuk Blueprint satırları düzeltildi ve girintileme sorunları giderildi.

### d. Mobil Görünüm (UI) Webview Optimizasyonu
- **Sorun:** Mobil uygulamadaki WebView üzerinden "İndirimli Kurumlar" ekranına girildiğinde, masaüstü (kocaman) görünüyor ve çok fazla boşluk/buton içeriyordu.
- **Çözüm:** URL'ye `?source=mobile` parametresi gönderilerek Flask tarafında `hide_ui=True` (Navbar ve Footer kısımları) devreye alındı. Ayrıca `indirimlikurumlar.html` içerisine `{% if hide_ui %}` kondisyonu ile **Mobile App Overrides (CSS)** eklendi. (Tab menüsü scrolable yapıldı, header sadeleştirildi, boşluklar sıfırlandı).

---

## 3. Asistan İçin Not (Agent Context)
**Sevgili Antigravity / AI Asistanı:** Eğer yeni bir oturumda uyandırıldıysan ve kullanıcı bu dosyayı referans verdiyse, bilmelisin ki:
- Proje kökü: `c:\Users\lalel\Desktop\webuygulama\webuygulama`
- Mobil uygulama klasörü: `...\isfa-mobile`
- Mobil WebView'lar backend Flask'a (`localhost:5000`) bağlanır; ADB reverse işlemi zaruridir.
- Emülatörde eski "İSFA Mobil" uygulaması `com.isfa.app` paket adıyla mevcuttu ve ADB ile silindi, artık mevcut Expo yapısına (`isfa-mobile`) odaklanıyoruz.
- Frontend (Web) kısmındaki stil düzeltmeleri için `hide_ui` flag'inin mobil uygulamada WebView üzerinden geldiğini (`?source=mobile`) unutma!
