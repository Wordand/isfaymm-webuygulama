
  const AKTIF_YIL = 2026;

  const VERGI_PARAMETRELERI = {
    2026: {
      kiraIstisnasi: 58000,
      gencGirisimciLimit: 400000,
      ariziKazancLimit: 350000,
      esnafMuaflikLimit: 1900000,
      sosyalIcerikLimit: 5300000,
      telifLimit: 5300000,
      degerArtisiLimit: 150000,
      ucretCokluLimit: 190000,
      ucretToplamLimit: 5300000,
      yemekYardimiLimit: 300,
      ulasimYardimiLimit: 158,
      kiraTavanSiniri: 1500000,
      dilimler: [150000, 380000, 1000000, 5300000],
      oranlar: [0.15, 0.20, 0.27, 0.35, 0.40],
      kumuplatifMatrahlar: [22500, 68500, 235900, 1740900]
    },
    2027: {
      kiraIstisnasi: 85000,
      gencGirisimciLimit: 550000,
      ariziKazancLimit: 480000,
      esnafMuaflikLimit: 2600000,
      sosyalIcerikLimit: 7200000,
      telifLimit: 7200000,
      degerArtisiLimit: 220000,
      ucretCokluLimit: 250000,
      ucretToplamLimit: 7200000,
      yemekYardimiLimit: 420,
      ulasimYardimiLimit: 220,
      kiraTavanSiniri: 2200000,
      dilimler: [200000, 500000, 1400000, 7200000],
      oranlar: [0.15, 0.20, 0.27, 0.35, 0.40],
      kumuplatifMatrahlar: [30000, 90000, 333000, 2363000]
    }
  };

  const params = VERGI_PARAMETRELERI[AKTIF_YIL];

  let activeTabId = 'tab-{{ active_tab }}';

  /* ── Persona Kart Seçimi ── */
  function selectPersona(tabId, rowMadde) {
    // Sekmeyi değiştir
    let btnId = 'tabBtnIstisnalar';
    if (tabId === 'tab-muafliklar') btnId = 'tabBtnMuafliklar';
    else if (tabId === 'tab-indirimler') btnId = 'tabBtnIndirimler';
    else if (tabId === 'tab-beyan-tarife') btnId = 'tabBtnBeyanTarife';
    
    const btn = document.getElementById(btnId);
    if (btn) switchTab(tabId, btn);
    
    // Arama kutusunu temizle
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.value = '';
    filterItems();
    
    // Satırı bul ve aç
    setTimeout(() => {
      const rowId = 'row-' + rowMadde.replace(' ', '_').replace('/', '_');
      const rowEl = document.getElementById(rowId);
      if (rowEl) {
        rowEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Eğer zaten açık değilse tetikle
        const next = rowEl.nextElementSibling;
        if (!next || !next.classList.contains('expanded')) {
          rowEl.click();
        }
      }
    }, 150);
  }

  /* ── Sekme geçişleri ── */
  function switchTab(tabId, btn) {
    activeTabId = tabId;
    
    // Tab buton sınıflarını güncelle
    document.querySelectorAll('.kvi-tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    // Tab panellerini göster/gizle
    document.querySelectorAll('.kvi-tab-content').forEach(pane => {
      if (pane.id === tabId) {
        pane.classList.remove('d-none');
      } else {
        pane.classList.add('d-none');
      }
    });

    // Açık olan tüm açıklama kutularını kapat
    document.querySelectorAll('.kvi-description-collapse').forEach(el => {
      el.classList.remove('expanded');
      el.style.maxHeight = '0px';
    });
    document.querySelectorAll('.kvi-row').forEach(row => {
      row.classList.remove('active-row');
      const icon = row.querySelector('.kvi-toggle-icon');
      if (icon) icon.classList.replace('bi-chevron-up', 'bi-chevron-down');
    });
    
    filterItems();
  }

  /* ── Arama filtresi ── */
  function filterItems() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    const query = searchInput.value.toLowerCase().trim();
    const activePanel = document.getElementById(activeTabId);
    const rows = activePanel.querySelectorAll('.kvi-row');
    
    let visibleCount = 0;
    
    rows.forEach(row => {
      const name = row.querySelector('.kvi-row-name').textContent.toLowerCase();
      const number = row.querySelector('.kvi-row-number').textContent.toLowerCase();
      
      // Arama kelimesi satır adı ya da yasal madde adında geçiyorsa göster
      if (name.includes(query) || number.includes(query)) {
        row.classList.remove('d-none');
        const next = row.nextElementSibling;
        if (next && next.classList.contains('kvi-description-collapse')) {
          next.classList.remove('d-none');
        }
        visibleCount++;
      } else {
        row.classList.add('d-none');
        const next = row.nextElementSibling;
        if (next && next.classList.contains('kvi-description-collapse')) {
          next.classList.add('d-none');
        }
      }
    });
    
    const countEl = document.getElementById('itemCount');
    if (query === "") {
      countEl.textContent = `Toplam ${visibleCount} kayıt listeleniyor.`;
    } else {
      countEl.textContent = `Arama sonucunda ${visibleCount} kayıt bulundu.`;
    }
  }



  /* ── İstisna Uygunluk Sihirbazı Logic ── */
  let wizType = '';
  function wizardSelectType(type) {
    wizType = type;
    document.querySelectorAll('.wizard-step').forEach(el => el.classList.add('d-none'));
    
    if (type === 'kira') {
      document.getElementById('step-2-kira').classList.remove('d-none');
    } else if (type === 'girisim') {
      document.getElementById('step-2-girisim').classList.remove('d-none');
    } else if (type === 'telif') {
      document.getElementById('step-2-telif').classList.remove('d-none');
    } else if (type === 'sosyal') {
      document.getElementById('step-2-sosyal').classList.remove('d-none');
    } else if (type === 'esnaf') {
      document.getElementById('step-2-esnaf').classList.remove('d-none');
    } else if (type === 'ucret') {
      document.getElementById('step-2-ucret').classList.remove('d-none');
    }
  }

  function wizardGoBack(step) {
    document.querySelectorAll('.wizard-step').forEach(el => el.classList.add('d-none'));
    document.getElementById('step-1').classList.remove('d-none');
  }

  function wizardEvaluateKira() {
    const amt = parseFloat(document.getElementById('wizardKiraAmount').value) || 0;
    const hasActive = document.getElementById('wizardKiraActiveYes').checked;
    const totalOverLimit = document.getElementById('wizardKiraTotalYes').checked;
    
    if (hasActive) {
      showWizardResult(
        'bi-x-circle-fill text-danger',
        'Kira İstisnasından Yararlanamazsınız',
        'Yasal mevzuata göre, yıllık beyanname ile bildirilmesi gereken ticari, zirai veya serbest meslek kazancınız bulunduğundan 2026 yılı için belirlenen 58.000 TL kira gelir istisnasından yararlanamazsınız.',
        'Kira hasılatınızın tamamını beyan etmeli ve vergisini ödemelisiniz. İstisna hakkı sıfırlanacaktır.',
        '<strong>Beyanname Verilmesi Zorunludur.</strong> (GVK Md. 21 uyarınca, ticari, zirai veya mesleki kazancını yıllık beyannameyle bildirenler kira istisnasından yararlanamaz ve tüm kira gelirini beyannameye dahil etmek zorundadır.)',
        'Konut kiralarında kiracı gerçek kişi olduğunda <strong>stopaj (tevkifat) yapılmaz</strong>. Ancak işyeri kirası olsaydı GVK Md. 94/5-a uyarınca %20 stopaj yapılacaktı.'
      );
    } else if (totalOverLimit) {
      showWizardResult(
        'bi-x-circle-fill text-danger',
        'Limit Aşımı Nedeniyle İstisna Uygulanamaz',
        '2026 takvim yılı içinde elde ettiğiniz tüm brüt gelirlerinizin (ücret, kira, faiz, temettü vb.) toplamı 1.500.000 TL sınırını aştığından konut kira gelirleri istisnasından yararlanma hakkınız bulunmamaktadır.',
        'Mart ayında vereceğiniz kira beyannamesinde 58.000 TL istisna tutarını düşmeden, hasılatın tamamı üzerinden vergi hesaplamalısınız.',
        '<strong>Beyanname Verilmesi Zorunludur.</strong> (GVK Md. 21 uyarınca, diğer brüt gelirleri toplamı 1.500.000 TL\'yi aşanlar istisnadan faydalanamaz ve beyanname vermelidir.)',
        'Konut kiralarında <strong>vergi tevkifatı (stopaj) uygulanmaz</strong>.'
      );
    } else if (amt <= 58000) {
      showWizardResult(
        'bi-check-circle-fill text-success',
        'Kira İstisnası Kapsamındasınız (Vergi Beyanı Gerekmez)',
        `Yıllık mesken kira geliriniz (${amt.toLocaleString('tr-TR')} TL), 2026 yılı yasal istisna limiti olan 58.000 TL sınırının altında kalmaktadır.`,
        'Herhangi bir beyanname vermenize veya gelir vergisi ödemenize gerek yoktur. Bu tutar tamamen vergiden muaftır.',
        '<strong>Beyanname Verilmez.</strong> (GVK Md. 86/1-a uyarınca, istisna hadleri içinde kalan kazanç ve iratlar için beyanname verilmez, diğer gelirler için beyanname verilse dahi bu gelir dahil edilmez.)',
        'Konut kiralarında <strong>vergi tevkifatı (stopaj) uygulanmaz</strong>.'
      );
    } else {
      const netMatrah = amt - 58000;
      showWizardResult(
        'bi-info-circle-fill text-warning',
        'Kira Beyannamesi Vermelisiniz',
        `Kira geliriniz (${amt.toLocaleString('tr-TR')} TL), 58.000 TL yasal istisna sınırını aşmaktadır. Ancak şartları sağladığınız için istisna hakkınız bulunmaktadır.`,
        `Mart ayında beyanname vermelisiniz. İstisna tutarı düşüldükten sonra kalan net matrah (${netMatrah.toLocaleString('tr-TR')} TL) üzerinden kademeli vergi tarifesine göre gelir vergisi hesaplanacaktır.`,
        '<strong>Beyanname Verilmesi Zorunludur.</strong> (Limit aşımı nedeniyle yıllık beyanname verilmesi yasal bir yükümlülüktür.)',
        'Konut kiralarında <strong>vergi tevkifatı (stopaj) uygulanmaz</strong>.'
      );
    }
  }

  function wizardEvaluateGirisim() {
    const ageValid = document.getElementById('wizGencAge').checked;
    const firstValid = document.getElementById('wizGencFirst').checked;
    const activeValid = document.getElementById('wizGencActive').checked;
    const inheritInvalid = document.getElementById('wizGencInherit').checked;
    
    if (ageValid && firstValid && activeValid && !inheritInvalid) {
      showWizardResult(
        'bi-check-circle-fill text-success',
        'Genç Girişimci İstisnası Şartlarını Karşılıyorsunuz!',
        'Tebrikler! Mükellefiyet başlangıç tarihiniz itibarıyla aranan tüm şartları eksiksiz bir şekilde sağlıyorsunuz.',
        'Mükellefiyet başlangıcından itibaren 3 vergilendirme dönemi boyunca elde edeceğiniz ticari veya mesleki kazançlarınızın yıllık 400.000 TL\'lik kısmı gelir vergisinden tamamen istisna olacaktır. Ayrıca 1 yıl boyunca Bağ-Kur primleriniz devlet tarafından ödenecektir.',
        '<strong>Yıllık Beyanname Verilir ancak 400.000 TL\'lik Kısım Düşülür.</strong> (GVK Mükerrer Md. 20 uyarınca, beyanname verilir ancak istisna tutarı kazançtan indirilir. Aşan kısım vergilendirilir.)',
        'Faaliyet alanınıza göre müşterilerinizin yapacağı ödemelerden stopaj yapılabilir (örn. serbest meslekte GVK Md. 94/2-b uyarınca %20 stopaj). Beyannamede bu stopajlar mahsup edilebilir.'
      );
    } else {
      let reasons = [];
      if (!ageValid) reasons.push("İşe başlama tarihinde 29 yaş sınırını doldurmuş olmanız");
      if (!firstValid) reasons.push("İlk defa vergi mükellefiyeti açıyor olmamanız");
      if (!activeValid) reasons.push("İşin başında bilfiil çalışmıyor veya sevk/idare etmiyor olmanız");
      if (inheritInvalid) reasons.push("İşletmeyi 1. derece yakınlarınızdan devralmış olmanız");
      
      showWizardResult(
        'bi-x-circle-fill text-danger',
        'Genç Girişimci İstisnası Uygulanamaz',
        `Aşağıdaki kriter(ler) nedeniyle genç girişimci vergi desteğinden yararlanamazsınız:<br><br><ul class="text-start mx-auto d-inline-block ps-4 mb-0">${reasons.map(r => `<li>${r}</li>`).join('')}</ul>`,
        'Genel vergi mükellefiyeti şartları geçerli olacak ve elde ettiğiniz kazancın tamamı GVK Madde 103 vergi tarifesine göre vergilendirilecektir.',
        '<strong>Yıllık Beyanname Verilmesi Zorunludur.</strong> (İstisna hakkı olmadığı için kazancın tamamı beyan edilmelidir.)',
        'Serbest meslek faaliyetlerinde GVK Md. 94/2-b uyarınca yapılan ödemelerden <strong>%20 vergi tevkifatı (stopaj)</strong> yapılır. Ticari kazançlarda genel stopaj yoktur.'
      );
    }
  }

  function wizardEvaluateTelif() {
    const hasCert = document.getElementById('wizardTelifCertYes').checked;
    const amt = parseFloat(document.getElementById('wizardTelifAmount').value) || 0;
    
    if (!hasCert) {
      showWizardResult(
        'bi-x-circle-fill text-danger',
        'Tescil Eksikliği - İstisna Uygulanamaz',
        'Elde ettiğiniz telif kazancının yasal istisna kapsamında değerlendirilebilmesi için eser niteliğinde olması ve Kültür ve Turizm Bakanlığı\'nden telif/tescil belgesi alınmış olması yasal bir zorunluluktur.',
        'Kültür Bakanlığı Telif Hakları Genel Müdürlüğü\'ne başvurarak tescil belgesi temin ettikten sonra istisna hakkınızı kullanabilirsiniz.',
        '<strong>Beyanname Verilmesi Zorunludur.</strong> (Telif tescili olmayan kazançlar istisna kapsamında olmadığından serbest meslek kazancı olarak yıllık beyannameyle beyan edilmelidir.)',
        'GVK Md. 94/2-b uyarınca tescilsiz serbest meslek ödemelerinden <strong>%20 vergi tevkifatı (stopaj)</strong> kesilir.'
      );
    } else if (amt <= 5300000) {
      showWizardResult(
        'bi-check-circle-fill text-success',
        'Telif Kazancı İstisnası Kapsamındasınız',
        `Telif kazancınız (${amt.toLocaleString('tr-TR')} TL), 2026 yılı beyan sınırı olan 5.300.000 TL limitinin altında kalmaktadır.`,
        'Gelirinizin tamamı gelir vergisinden istisnadır. Yıllık beyanname vermenize gerek yoktur. Eserlerinizi satın alanların yapacağı stopaj (%17) nihai verginiz olacaktır.',
        '<strong>Beyanname Verilmez.</strong> (GVK Md. 86/1-a uyarınca, istisna sınırları altında kalan telif kazançları için yıllık beyanname verilmez, stopaj nihai vergidir.)',
        'GVK Md. 94/2-a uyarınca telif hakkı ödemelerinden <strong>%17 vergi tevkifatı (stopaj)</strong> kesilir.'
      );
    } else {
      showWizardResult(
        'bi-info-circle-fill text-warning',
        'Yıllık Beyanname Vermek Zorundasınız',
        `Telif kazancınız (${amt.toLocaleString('tr-TR')} TL), 2026 yılı yasal beyan limiti olan 5.300.000 TL sınırını aşmaktadır.`,
        'Elde ettiğiniz telif gelirinin tamamını yıllık gelir vergisi beyannamesi ile beyan etmelisiniz. Yıl içinde ödediğiniz %17 stopajlar beyannamede hesaplanan vergiden mahsup edilecektir.',
        '<strong>Beyanname Verilmesi Zorunludur.</strong> (GVK Md. 86 uyarınca, telif kazançları toplamı 103. maddedeki tarifenin 4. gelir dilimini (2026 yılı için 5.300.000 TL) aşarsa yıllık beyanname verilmesi zorunludur.)',
        'GVK Md. 94/2-a uyarınca ödemelerden <strong>%17 stopaj (tevkifat)</strong> yapılmaya devam eder. Kesilen bu vergiler yıllık beyannamede hesaplanan vergiden mahsup edilir.'
      );
    }
  }

  function wizardEvaluateSosyal() {
    const hasBank = document.getElementById('wizardSosyalBankYes').checked;
    const amt = parseFloat(document.getElementById('wizardSosyalAmount').value) || 0;
    
    if (!hasBank) {
      showWizardResult(
        'bi-x-circle-fill text-danger',
        'Banka Şartı İhlali - İstisna Uygulanamaz',
        'Sosyal içerik üreticiliği ve mobil uygulama vergi istisnasının en temel şartı, Türkiye\'de kurulu bir bankada bu faaliyet için özel bir ticari hesap açılmasıdır.',
        'Hemen bir banka şubesine giderek ticari hesap açtırmalı ve bu hesabı vergi dairesine bildirmelisiniz. Hesaptan otomatik yapılacak %15 stopaj kesintisi haricinde hiçbir şekilde hasılat tahsil edilmemelidir.',
        '<strong>Beyanname Verilmesi Zorunludur.</strong> (Yasal ticari hesap açılmadığı için istisna hakkı kaybolur ve ticari kazanç olarak yıllık beyanname zorunluluğu doğar.)',
        'İstisna dışı kalındığı için genel hükümlere göre fatura kesilmeli ve vergilendirilmelidir.'
      );
    } else if (amt <= 5300000) {
      showWizardResult(
        'bi-check-circle-fill text-success',
        'Sosyal Medya İstisnası Kapsamındasınız',
        `Yıllık hasılatınız (${amt.toLocaleString('tr-TR')} TL), 2026 yılı beyan limiti olan 5.300.000 TL sınırının altındadır.`,
        'Banka hesabınıza gelen tüm hasılat üzerinden bankanın yapacağı %15 stopaj kesintisi nihai vergilendirmenizdir. Yıllık gelir vergisi beyannamesi vermeniz gerekmez.',
        '<strong>Beyanname Verilmez.</strong> (GVK Mükerrer Md. 20/B uyarınca, 5.300.000 TL beyan sınırını aşmayan hasılatlar için yıllık beyanname verilmez, diğer gelirler için verilse dahi dahil edilmez.)',
        'GVK Md. 94 uyarınca banka tarafından hesaba gelen tüm hasılat üzerinden <strong>%15 vergi tevkifatı (stopaj)</strong> kesilir.'
      );
    } else {
      showWizardResult(
        'bi-info-circle-fill text-warning',
        'Stopaj İstisnası Aşılmış - Beyan Zorunlu',
        `Yıllık hasılatınız (${amt.toLocaleString('tr-TR')} TL), 2026 yılı beyan limiti olan 5.300.000 TL sınırını aşmıştır.`,
        'Tüm gelirlerinizi yıllık gelir vergisi beyannamesi ile beyan etmelisiniz. Banka tarafından kesilen %15 stopaj tutarları hesaplanan vergiden düşülecektir.',
        '<strong>Beyanname Verilmesi Zorunludur.</strong> (GVK Mükerrer Md. 20/B uyarınca, yıllık brüt hasılat 103. madde 4. dilimini aşarsa yıllık beyanname verilmesi zorunludur.)',
        'Banka tarafından yapılan <strong>%15 stopaj (tevkifat)</strong> kesintisi devam eder. Bu tutarlar beyannamede mahsup edilecektir.'
      );
    }
  }

  function wizardEvaluateEsnaf() {
    const isHome = document.getElementById('wizardEsnafHomeYes').checked;
    const noShop = document.getElementById('wizardEsnafShopNo').checked;
    const hasBank = document.getElementById('wizardEsnafBankYes').checked;
    const amt = parseFloat(document.getElementById('wizardEsnafAmount').value) || 0;
    
    if (!isHome || !noShop) {
      showWizardResult(
        'bi-x-circle-fill text-danger',
        'Esnaf Muaflığından Yararlanamazsınız',
        'Dışarıdan hazır alıp satanlar veya ayrı bir iş yeri açıp endüstriyel boyutta imalat yapanlar ev hanımlarına ve küçük sanatkarlara tanınan Esnaf Muaflığı (GVK Md. 9) kapsamına girmez.',
        'Ticari işletme kaydı açtırarak fatura kesmeli ve gerçek usulde gelir vergisi mükellefi olmalısınız.',
        '<strong>Beyanname Verilmesi Zorunludur.</strong> (Esnaf muaflığı dışı kalındığı için ticari kazanç mükellefi olarak beyanname verilmelidir.)',
        'Ticari kazançlarda genel stopaj uygulanmaz.'
      );
    } else if (!hasBank) {
      showWizardResult(
        'bi-x-circle-fill text-danger',
        'Banka Hesabı Zorunlu',
        'Evde üretilen ürünlerin internetten satışındaki esnaf muaflığı için Türkiye\'de kurulu bir bankada ticari hesap açılması yasal bir zorunluluktur.',
        'Hemen ticari hesap açmalı ve bu hesabı vergi dairenize sunarak esnaf muafiyet belgesi almalısınız.',
        '<strong>Beyanname Verilmez (Ancak Banka Hesabı Açılana Kadar Satış Yapılamaz).</strong>',
        'Banka hesabı olmadığı için stopaj uygulanamamaktadır.'
      );
    } else if (amt <= 1900000) {
      showWizardResult(
        'bi-check-circle-fill text-success',
        'İnternet Satışı Esnaf Muaflığı Kapsamındasınız',
        `Yıllık hasılatınız (${amt.toLocaleString('tr-TR')} TL), 2026 yılı tavan limiti olan 1.900.000 TL sınırının altındadır.`,
        'Banka hesabınıza yatan paralardan banka tarafından %4 (%1\'den fazla işçi çalıştırıyorsanız %2) stopaj kesintisi yapılır. Başka bir vergi ve beyan zorunluluğunuz yoktur.',
        '<strong>Beyanname Verilmez.</strong> (GVK Md. 9 uyarınca, esnaf muaflığı kapsamındaki bu gelirler için yıllık beyanname verilmez.)',
        'GVK Md. 94/13-a uyarınca banka tarafından hesabınıza gelen bedellerden <strong>%4 vergi tevkifatı (stopaj)</strong> kesilir. En az 1 işçi çalıştırılıyorsa bu tevkifat oranı **%2** olarak uygulanır.'
      );
    } else {
      showWizardResult(
        'bi-info-circle-fill text-warning',
        'Muafiyet Sınırı Aşılmıştır',
        `Yıllık e-ticaret hasılatınız (${amt.toLocaleString('tr-TR')} TL), 2026 yılı tavan limiti olan 1.900.000 TL sınırını aşmıştır.`,
        'Gelecek takvim yılı başından itibaren esnaf muaflığınız sona erer ve gerçek usulde vergi mükellefiyeti açtırmak zorunda kalırsınız.',
        '<strong>Cari Yılda Beyanname Verilmez, Gelecek Yıl Zorunlu Olur.</strong> (Limit aşımı durumunda muafiyet gelecek yıl başından itibaren son bulur.)',
        'Cari yılda banka tarafından yapılan <strong>%4 (%2) stopaj kesintisi</strong> devam eder. Gelecek yıl gerçek usulde faturalı vergilendirmeye geçilecektir.'
      );
    }
  }

  function wizardEvaluateUcret(ucretType) {
    if (ucretType === 'madenci') {
      showWizardResult(
        'bi-check-circle-fill text-success',
        'Yer Altı Çalışmalarında %100 İstisna',
        'Toprak altı işletmesi olan madenlerde cevher üretimi ve doğrudan ilgili işlerde çalışanların münhasıran yer altında çalıştıkları sürelere ait ücretleri gelir vergisinden tamamen istisnadır.',
        'Bu istisna için herhangi bir limit yoktur. Yer altında geçirilen tüm sürelerin ücreti vergiden istisnadır.',
        '<strong>Beyanname Verilmez.</strong> (GVK Md. 86/1-a uyarınca, gelir vergisinden tamamen istisna olan yer altı maden işçisi ücretleri yıllık beyannameye dahil edilmez.)',
        'GVK Md. 23/3 uyarınca yer altında geçen sürelere ait ücretlerden <strong>%0 vergi tevkifatı (stopaj)</strong> uygulanır.'
      );
    } else if (ucretType === 'havacilik') {
      showWizardResult(
        'bi-check-circle-fill text-success',
        'Havacılık Sektörü İstisnası (%70)',
        'Yerli sivil havacılık şirketlerinde veya Türk Hava Kurumu\'nda çalışan pilot ve kabin memurlarına ödenen aylık ücretlerin %70\'i gelir vergisinden istisnadır.',
        'Kalan %30 üzerinden vergi kesintisi işverence yapılır. Aylık bordro hesaplamasında otomatik olarak dikkate alınır.',
        '<strong>%70 İstisna Kısmı İçin Beyanname Verilmez.</strong> (Vergiye tabi kalan %30\'luk kısım tek işverenden ise ve 5.300.000 TL\'yi aşmıyorsa beyannameye dahil edilmez.)',
        'Vergiye tabi %30\'luk kısım üzerinden işveren tarafından GVK Md. 94/1 uyarınca kademeli tarifeye göre <strong>gelir vergisi tevkifatı</strong> yapılır.'
      );
    } else if (ucretType === 'sektorel') {
      showWizardResult(
        'bi-info-circle-fill text-warning',
        'Sosyal Yardım İstisna Limitleri (2026)',
        'İşverenler tarafından çalışanlara sağlanan ayni ve nakdi sosyal yardımların vergi istisnası limitleri şu şekildedir:',
        '<ul><li><strong>Yemek Yardımı:</strong> Günlük 300 TL\'ye kadar vergisizdir.</li><li><strong>Ulaşım Kartı/Bileti:</strong> Günlük 158 TL\'ye kadar vergisizdir.</li><li><strong>Kreş Yardımı (Kadın Çalışan):</strong> Çocuk başına brüt asgari ücretin %50\'sine kadar vergisizdir.</li></ul>',
        '<strong>İstisna Limitleri Altındaki Yardımlar İçin Beyanname Verilmez.</strong> (Sosyal yardımların istisna tutarları beyanname dışıdır. Aşan kısımlar ücret geliri olarak beyan sınırlarında dikkate alınır.)',
        'Limitleri aşmayan sosyal yardımlardan <strong>vergi tevkifatı yapılmaz</strong>. Aşan kısımlardan ise kademeli tarifeye göre stopaj kesilir.'
      );
    }
  }

  function wizardEvaluateUcretTek() {
    const amt = parseFloat(document.getElementById('wizardUcretTekAmount').value) || 0;
    if (amt <= params.ucretToplamLimit) {
      showWizardResult(
        'bi-check-circle-fill text-success',
        'Tek İşveren Ücret İstisnası (Beyanname Gerekmez)',
        `Yıllık brüt ücret geliriniz (${amt.toLocaleString('tr-TR')} TL), ${AKTIF_YIL} yılı tek işveren beyan sınırı olan ${params.ucretToplamLimit.toLocaleString('tr-TR')} TL limitinin altında kalmaktadır.`,
        'İşvereniniz tarafından yıl içinde yapılan stopajlar nihai verginizdir. Yıllık gelir vergisi beyannamesi vermenize gerek yoktur.',
        `<strong>Beyanname Verilmez.</strong> (GVK Md. 86/1-b uyarınca, tek işverenden tevkif suretiyle vergilendirilmiş ve 103. madde 4. dilimini (${AKTIF_YIL} yılı için ${params.ucretToplamLimit.toLocaleString('tr-TR')} TL) aşmayan ücretler beyan edilmez.)`,
        'İşvereniniz tarafından GVK Md. 94/1 uyarınca kademeli vergi tarifesine göre <strong>%15 ila %40</strong> arasında değişen oranlarda gelir vergisi tevkifatı (stopaj) yapılmıştır.'
      );
    } else {
      showWizardResult(
        'bi-info-circle-fill text-warning',
        'Yıllık Beyanname Vermek Zorundasınız',
        `Yıllık brüt ücret geliriniz (${amt.toLocaleString('tr-TR')} TL), ${AKTIF_YIL} yılı beyan sınırı olan ${params.ucretToplamLimit.toLocaleString('tr-TR')} TL limitini aşmaktadır.`,
        'Mart ayında yıllık gelir vergisi beyannamesi vermeniz zorunludur. Yıl içinde kesilen stopajlar beyannamede hesaplanan vergiden mahsup edilecektir (düşülecektir).',
        `<strong>Beyanname Verilmesi Zorunludur.</strong> (GVK Md. 86/1-b uyarınca, tek işverenden alınmış olsa dahi 103. madde 4. dilimini (${AKTIF_YIL} yılı için ${params.ucretToplamLimit.toLocaleString('tr-TR')} TL) aşan ücretler için beyanname verilir.)`,
        'İşvereniniz tarafından GVK Md. 94/1 uyarınca yapılan tevkifatlar beyannamede hesaplanan vergiden mahsup edilir.'
      );
    }
  }

  function wizardEvaluateUcretCok() {
    const first = parseFloat(document.getElementById('wizardUcretCokFirst').value) || 0;
    const others = parseFloat(document.getElementById('wizardUcretCokOthers').value) || 0;
    const total = first + others;
    
    if (others > 190000 || total > 5300000) {
      showWizardResult(
        'bi-info-circle-fill text-warning',
        'Yıllık Beyanname Vermek Zorundasınız',
        `Birinciden sonraki işverenden aldığınız ücretler toplamı (${others.toLocaleString('tr-TR')} TL) 190.000 TL beyan sınırını ${others > 190000 ? 'aşmaktadır' : 'aşmamakla birlikte, toplam brüt geliriniz 5.300.000 TL sınırını aşmaktadır'}.`,
        'Mart ayında tüm işverenlerden elde ettiğiniz ücret gelirlerinizin tamamını yıllık gelir vergisi beyannamesi ile beyan etmeniz gerekmektedir. Yıl içinde kesilen stopajlar mahsup edilecektir.',
        '<strong>Beyanname Verilmesi Zorunludur.</strong> (GVK Md. 86/1-b uyarınca, birden sonraki işverenden alınan ücretlerin toplamı 2. dilim tutarını (2026 yılı için 190.000 TL) veya tüm ücretlerin toplamı 4. dilim tutarını (2026 yılı için 5.300.000 TL) aşarsa tamamı beyan edilir.)',
        'Tüm işverenleriniz tarafından GVK Md. 94/1 uyarınca kademeli tarifeye göre ayrı ayrı vergi tevkifatı yapılmıştır. Bu tevkifatlar beyannamede mahsup edilecektir.'
      );
    } else {
      showWizardResult(
        'bi-check-circle-fill text-success',
        'Beyanname Vermeniz Gerekmez',
        `Birinciden sonraki işverenden aldığınız ücretler toplamı (${others.toLocaleString('tr-TR')} TL) 190.000 TL beyan sınırının altında olup, toplam brüt geliriniz de 5.300.000 TL'yi aşmamaktadır.`,
        'İşverenler tarafından yıl içinde yapılan vergi kesintileri nihai verginizdir. Yıllık beyanname vermenize gerek yoktur.',
        '<strong>Beyanname Verilmez.</strong> (GVK Md. 86/1-b uyarınca, birden fazla işverenden ücret alınsa dahi şartlar aşılmadığı sürece ücretler beyannameye dahil edilmez.)',
        'İşverenleriniz tarafından GVK Md. 94/1 uyarınca kademeli tarifeye göre vergi tevkifatı yapılmıştır.'
      );
    }
  }

  function showWizardResult(iconClass, title, desc, advice, beyannameText = 'Beyanname yükümlülüğü bulunmamaktadır.', tevkifatText = 'Bu kazanç üzerinden stopaj/tevkifat yapılmaz.') {
    document.querySelectorAll('.wizard-step').forEach(el => el.classList.add('d-none'));
    const res = document.getElementById('wizard-result');
    res.classList.remove('d-none');
    
    document.getElementById('wizardResultIcon').innerHTML = `<i class="bi ${iconClass}" style="font-size: 4rem;"></i>`;
    document.getElementById('wizardResultTitle').textContent = title;
    document.getElementById('wizardResultDesc').innerHTML = desc;
    document.getElementById('wizardResultAdvice').innerHTML = advice;
    
    // Yeni eklenen alanlar
    document.getElementById('wizardResultBeyanname').innerHTML = beyannameText;
    document.getElementById('wizardResultTevkifat').innerHTML = tevkifatText;
  }

  /* ── Detaylı açıklama metinleri (Yasal Kanun Metinleri) ── */
  function getDescriptionText(name, madde) {
    let detail = "";
    
    if (madde === "Madde 9") {
      detail = `
        <div class="row g-3">
          <div class="col-12"><p class="text-dark fw-bold fs-5 mb-2"><i class="bi bi-shop me-2 text-danger"></i>Esnaf Muaflığından Kimler Yararlanabilir?</p></div>
          <div class="col-md-6">
            <div class="p-3 rounded-3 border bg-white h-100">
              <span class="badge-danger-custom mb-2">Gezici &amp; Küçük Sanat Erbabı</span>
              <ul class="ps-3 mb-0 text-dark" style="font-size: 1.08rem; line-height: 1.7;" style="font-size: 1.08rem; line-height: 1.7;">
                <li>İş yeri açmadan gezici olarak perakende ticaret yapanlar.</li>
                <li>Gezici muslukçu, çilingir, ayakkabı tamircisi, berber vb. küçük zanaatkarlar.</li>
                <li>Motorsuz nakil vasıtası işletenler veya hayvanla nakliyecilik yapanlar.</li>
              </ul>
            </div>
          </div>
          <div class="col-md-6">
            <div class="p-3 rounded-3 border bg-white h-100">
              <span class="badge-danger-custom mb-2">Geleneksel &amp; Sanatsal Değerler</span>
              <ul class="ps-3 mb-0 text-dark" style="font-size: 1.08rem; line-height: 1.7;" style="font-size: 1.08rem; line-height: 1.7;">
                <li>Kaybolmaya yüz tutan geleneksel el sanatları kolları.</li>
                <li>Bakır işlemeciliği, çini ve çömlek yapımı, sedef kakma, ahşap oyma vb. geleneksel üretim yapanlar.</li>
              </ul>
            </div>
          </div>
          <div class="col-md-6">
            <div class="p-3 rounded-3 border bg-white h-100">
              <span class="badge-danger-custom mb-2">Evde Üretim &amp; E-Ticaret</span>
              <p class="text-dark mb-2" style="font-size: 1.08rem; line-height: 1.7;">Evlerde dikiş, nakış, mutfak aletleri vb. ile imal edilen ürünleri dükkan açmadan internetten satanlar.</p>
              <div class="alert alert-danger py-2 px-3 mb-0 rounded-3" style="font-size: 1.05rem; line-height: 1.6;">
                <strong>2026 Muafiyet Sınırı:</strong> Yıllık brüt asgari ücret tutarı (<strong>1.900.000 TL</strong>). Banka hesabı üzerinden <strong>%4 (%2 istihdamlı)</strong> stopaj kesintisi yapılır.
              </div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="p-3 rounded-3 border bg-white h-100">
              <span class="badge-danger-custom mb-2">Çatı Güneş Enerjisi</span>
              <p class="text-dark mb-0" style="font-size: 1.08rem; line-height: 1.7;">Konut çatılarında kurulan azami <strong>50 kW</strong> kurulu güce kadar olan yenilenebilir enerji tesislerinden yapılan elektrik satışları vergiden muaftır.</p>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 15") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-danger-custom fs-6 px-3 py-2"><i class="bi bi-shield-check me-2"></i>Kişisel Muafiyet</span>
          </div>
          <p class="fs-5 fw-bold text-dark mb-2">Yabancı Diplomatların Gelir Vergisi Muafiyeti</p>
          <p class="text-dark mb-3">Yabancı devletlerin Türkiye'deki elçi, maslahatgüzar, konsolosları ile elçilik/konsolosluk mensubu yabancı uyruklu memurları, bu sıfatlarından dolayı vergilendirilmezler.</p>
          <div class="alert alert-danger py-2 px-3 mb-0 rounded-3" style="font-size: 1.05rem; line-height: 1.6;">
            <strong>Kapsam Dışı:</strong> Bu muafiyet, diplomatların Türkiye'de elde ettikleri <strong>menkul sermaye iratları (faiz, kâr payı vb.)</strong> üzerinden kesilen stopaj vergisini kapsamaz.
          </div>
        </div>
      `;
    } else if (madde === "Madde 16") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-globe me-2"></i>Karşılıklılık Şartıyla İstisna</span>
          </div>
          <p class="fs-5 fw-bold text-dark mb-2">Diplomatik Temsilcilik Çalışanlarının Ücret İstisnası</p>
          <p class="text-dark mb-3">Türkiye'deki yabancı elçilik ve konsolosluklarda çalışan memur ve hizmetlilerin, yalnızca bu görevlerinden elde ettikleri ücret gelirleri <strong>gelir vergisinden istisnadır</strong>.</p>
          <div class="p-3 bg-light rounded-3 border-start border-warning border-3">
            <h6 class="fw-bold text-dark mb-1"><i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>Mütekabiliyet (Karşılıklılık) Koşulu:</h6>
            <p class="text-dark mb-0 small">İstisnanın uygulanması, ilgili yabancı devletin de kendi ülkesindeki Türk temsilcilik personeline benzer bir gelir vergisi istisnası tanımasına bağlıdır.</p>
          </div>
        </div>
      `;
    } else if (madde === "Madde 17") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-rocket me-2"></i>Teknogirişim Şirketleri</span>
          </div>
          <p class="fs-5 fw-bold text-dark mb-2">Çalışanlara Pay Senedi Verilmesinde Ücret İstisnası</p>
          <p class="text-dark mb-3">Sanayi ve Teknoloji Bakanlığı kriterlerine göre teknogirişim şirketi sayılan işverenlerin, çalışanlarına bedelsiz veya indirimli verdiği pay senetlerinin rayiç değerinin <strong>yıllık brüt ücretin iki katını</strong> aşmayan kısmı vergiden istisnadır.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3">
                <h6 class="fw-bold text-dark"><i class="bi bi-calendar-check text-success me-2"></i>Vergi Muafiyet Oranları (Elde Tutma Süresi)</h6>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.05rem; line-height: 1.7;">
                  <li class="mb-1"><strong>2 yıldan az tutulursa:</strong> İstisna iptal edilir (Vergi gecikme faiziyle işverenden tahsil edilir).</li>
                  <li class="mb-1"><strong>3-4 yıl elde tutulursa:</strong> %75 istisna avantajı korunur.</li>
                  <li class="mb-1"><strong>5-6 yıl elde tutulursa:</strong> %25 istisna avantajı korunur.</li>
                  <li class="mb-1"><strong>6 yılı aşarsa:</strong> %100 istisna avantajı kalıcı olur.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 18") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-palette-fill me-2"></i>Telif ve Sanat Eseri İstisnası</span>
          </div>
          <p class="fs-5 fw-bold text-dark mb-2">Yazar, Sanatçı ve Yazılımcıların Telif Hakları</p>
          <p class="text-dark mb-3">Müellif, mütercim, heykeltraş, ressam, bestekâr, bilgisayar yazılımcısı ve mucitlerin; ürettikleri şiir, roman, yazılım, video vb. eserlerin satışı veya hak devrinden elde ettikleri gelirler vergisinden istisnadır.</p>
          <div class="alert alert-warning py-3 px-3 mb-0 rounded-3" style="font-size: 1.05rem; line-height: 1.6;">
            <strong>2026 Yılı Beyan Sınırı:</strong> Yıllık kazanç toplamı <strong>5.300.000 TL</strong> limitini aşarsa bu kazançlar yıllık beyannameyle beyan edilmek zorundadır.
          </div>
        </div>
      `;
    } else if (madde === "Madde 20") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-book-fill me-2"></i>Özel Eğitim Kurumları</span>
          </div>
          <p class="fs-5 fw-bold text-dark mb-2">Eğitim ve Öğretim İşletmeleri Kazanç İstisnası</p>
          <p class="text-dark mb-3">Özel okul öncesi eğitim, ilköğretim, orta öğretim okulları ile özel kreş ve gündüz bakımevlerinin işletilmesinden elde edilen kazançlar vergilendirilmez.</p>
          <div class="p-3 bg-light rounded-3 border-start border-warning border-3">
            <h6 class="fw-bold text-dark mb-1"><i class="bi bi-calendar-check-fill text-warning me-2"></i>İstisna Süresi:</h6>
            <p class="text-dark mb-0">Kreş ve okulların faaliyete geçtiği dönemden itibaren <strong>5 vergilendirme dönemi (5 yıl)</strong> boyunca gelir vergisinden tamamen istisnadır.</p>
          </div>
        </div>
      `;
    } else if (madde === "Mükerrer Madde 20") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-rocket-takeoff-fill me-2"></i>Genç Girişimciler</span>
          </div>
          <p class="fs-5 fw-bold text-dark mb-2">Genç Girişimcilerde Kazanç İstisnası</p>
          <p class="text-dark mb-3">İlk defa gelir vergisi mükellefiyeti tesis ettiren ve işe başlama tarihinde 29 yaşını doldurmamış tam mükelleflerin kazançları 3 yıl boyunca istisna kapsamındadır.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-cash-coin text-success me-2"></i>İstisna Tutarı</h6>
                <p class="text-dark mb-0">Her takvim yılı için elde edilen kazancın yıllık <strong>400.000 TL</strong>'lik kısmı gelir vergisinden istisnadır.</p>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-card-checklist text-danger me-2"></i>Temel Şartlar</h6>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.05rem; line-height: 1.7;">
                  <li>İşe başlamanın kanuni süresinde bildirilmesi.</li>
                  <li>Kendi işinde bilfiil çalışılması veya sevk/idare edilmesi.</li>
                  <li>Mevcut bir işletmenin akrabalardan devralınmamış olması.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Mükerrer Madde 20/B") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-youtube me-2"></i>Sosyal Medya ve Mobil Uygulamalar</span>
          </div>
          <p class="fs-5 fw-bold text-dark mb-2">Sosyal İçerik Üreticiliği ve Mobil Uygulama Geliştirme İstisnası</p>
          <p class="text-dark mb-3">İnternetten paylaşılan metin, ses, video gibi sosyal içerikler ile mobil cihazlar için uygulama geliştirenlerin kazançları gelir vergisinden istisnadır.</p>
          <div class="p-3 bg-light rounded-3 border-start border-warning border-3 mb-3">
            <h6 class="fw-bold text-dark mb-1"><i class="bi bi-bank me-2 text-warning"></i>Kolay Stopaj Sistemi:</h6>
            <p class="text-dark mb-0">Türkiye'de kurulu bir bankada ticari hesap açılması ve tüm hasılatın bu hesaptan tahsil edilmesi durumunda, banka tarafından <strong>%15 stopaj</strong> kesilir ve başka beyanname verilmez.</p>
          </div>
          <div class="alert alert-warning py-2 px-3 mb-0 rounded-3 small">
            <strong>2026 Beyan Sınırı:</strong> Yıllık hasılat toplamı <strong>5.300.000 TL</strong> limitini aşarsa bu kazançlar yıllık beyannameye dahil edilir.
          </div>
        </div>
      `;
    } else if (madde === "Mükerrer Madde 20/C") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-flower1 me-2"></i>Tarım Sektörü</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Tarımsal Destekleme Ödemeleri İstisnası</p>
          <p class="text-dark mb-3">Kamu kurum ve kuruluşları tarafından çiftçilere yapılan her türlü tarımsal destekleme ödemeleri gelir vergisinden tamamen istisnadır ve beyannameye dahil edilmez.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-patch-check-fill text-success me-2"></i>Kapsamdaki Destekler</h6>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.05rem; line-height: 1.7;">
                  <li>Mazot, gübre ve toprak analizi destekleri</li>
                  <li>Fark ödemesi (prim) ve buzağı/besi destekleri</li>
                  <li>Organik tarım ve iyi tarım uygulamaları destekleri</li>
                  <li>Düşük faizli kredi sübvansiyon ödemeleri</li>
                </ul>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-shield-check text-success me-2"></i>Vergi ve Stopaj Statüsü</h6>
                <p class="text-dark mb-0 small">Destekleme ödemelerinden <strong>%0 stopaj</strong> kesilir. Çiftçilerin başka gelirleri nedeniyle yıllık beyanname vermesi durumunda dahi bu ödemeler beyannameye ve matraha dahil edilmez.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Mükerrer Madde 20/D") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-send-fill me-2"></i>Yurt Dışı Kazançları</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Yurt Dışından Elde Edilen Kazanç ve İratlar İstisnası</p>
          <p class="text-dark mb-3">Türkiye'ye yerleşen ve yerleşmeden önceki son 3 takvim yılında Türkiye'de ikametgahı veya vergi mükellefiyeti bulunmayan kişilerin, Türkiye dışından elde ettikleri tüm kazançlar <strong>20 yıl boyunca</strong> gelir vergisinden istisnadır.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Yararlanma Şartları</h6>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.05rem; line-height: 1.7;">
                  <li>Türkiye'ye yerleşmeden önceki son 3 yılda Türkiye'de mükellef olmamak.</li>
                  <li>Yalnızca Türkiye dışındaki ülkelerden elde edilen kazançlar için geçerlidir.</li>
                  <li><strong>Süre Sınırı:</strong> Türkiye'ye yerleşilen tarihten itibaren tam 20 takvim yılı sürer.</li>
                </ul>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-info-circle text-primary me-2"></i>Kapsam İçi Gelirler</h6>
                <p class="text-dark mb-0 small">Yurt dışındaki gayrimenkullerden elde edilen kira gelirleri, yurt dışı iştirak kâr payları, yurt dışı faiz gelirleri ve yurt dışı menkul kıymet satış kazançları istisna kapsamındadır.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 21") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-house-door me-2"></i>Kira Gelirleri</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Mesken Kira Geliri İstisnası</p>
          <p class="text-dark mb-3">Binaların konut (mesken) olarak kiraya verilmesinden elde edilen yıllık kira hasılatının 2026 takvim yılı için <strong>58.000 TL</strong>'si vergilendirilmez. İstisna sınırının altındaki kira gelirleri için beyanname verilmez.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-x-circle-fill text-danger me-2"></i>İstisnadan Yararlanamayanlar</h6>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.05rem; line-height: 1.7;">
                  <li>Ticari, zirai veya mesleki kazancını beyanname ile bildirenler.</li>
                  <li>Brüt ücret, kira, faiz ve temettü gelirleri toplamı 2026 yılı için <strong>1.500.000 TL</strong>'yi aşanlar bu haktan yararlanamaz.</li>
                </ul>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-people-fill text-success me-2"></i>Ortaklık ve Birden Çok Konut Durumu</h6>
                <p class="text-dark mb-0 small">Kiralık konut hisseli ise 58.000 TL limit her bir ortak için ayrı ayrı uygulanır. Bir mükellefin birden fazla konuttan kira geliri olması durumunda, istisna hakkı sadece tek bir konut geliri için (tek kez) kullanılabilir.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 22") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-pie-chart me-2"></i>Kâr Payı &amp; Temettü</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Menkul Sermaye İratlarında Vergi İstisnaları</p>
          <p class="text-dark mb-3">Yatırım ve ortaklık kazançlarında sağlanan vergi istisnaları şunlardır:</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Kâr Payı Yarısı İstisnası</h6>
                <p class="text-dark mb-2 small">Tam mükellef şirketlerden elde edilen kâr paylarının (temettü) <strong>yarısı</strong> gelir vergisinden istisnadır.</p>
                <div class="alert alert-warning py-1 px-2 mb-0 small" style="font-size:0.78rem;">
                  <strong>Beyan Sınırı:</strong> Kalan yarısı 2026 yılı beyan sınırı olan <strong>190.000 TL</strong>'yi aşarsa beyan edilir. Kesilen %10 stopajın tamamı mahsup edilir.
                </div>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-safe2 text-success me-2"></i>Yurt Dışı Temettü İstisnası</h6>
                <p class="text-dark mb-0 small">Yurt dışındaki şirketlerin en az <strong>%20</strong> sermayesine sahip olunması, kâr payının elde edildiği takvim yılı beyanname vadesine kadar Türkiye'ye transfer edilmesi şartıyla yarısı istisnadır.</p>
              </div>
            </div>
            <div class="col-12">
              <div class="p-3 bg-light rounded-3">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-shield-lock-fill text-primary me-2"></i>Uzun Vadeli Yıllık Gelir Sigortaları</h6>
                <p class="text-dark mb-0 small">En az 10 yıl süreli veya ömür boyu yapılan tek primli yıllık gelir sigortalarından yapılan ödemelerin içerdiği irat tutarlarının tamamı vergiden istisnadır. Erken çıkışlarda stopaj cezası uygulanır.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 23") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-success-custom fs-6 px-3 py-2"><i class="bi bi-briefcase me-2"></i>Maaş &amp; Ücret Kazançları</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Ücret Gelirlerinde Vergi İstisnaları</p>
          <div class="row g-3" style="max-height: 500px; overflow-y: auto;">
            <div class="col-12"><p class="text-dark fw-semibold mb-2">Gelir Vergisi Kanunu kapsamında ücret gelirleri ve sağlanan menfaatlerde uygulanan istisnalar:</p></div>
            
            <!-- Grup 1: Genel ve Sosyal Ücret İstisnaları -->
            <div class="col-md-6">
              <div class="p-3 rounded border bg-white h-100">
                <span class="badge-success-custom mb-2">Genel &amp; Sosyal Haklar</span>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.05rem; line-height: 1.7;" style="list-style-type: decimal;">
                  <li class="mb-2"><strong>Halı ve Kilim İşçileri (Bent 1):</strong> Nüfusu 5.000'i aşmayan yerlerde el halısı ve kilimi dokuyan işçilerin ücretleri.</li>
                  <li class="mb-2"><strong>Ev Hizmetlileri Ücretleri (Bent 6):</strong> Evlerde çalışan hizmetçilerin ücretleri istisnadır (mürebbiyeler hariç).</li>
                  <li class="mb-2"><strong>Öğrenci, Hükümlü ve Düşkünler (Bent 7):</strong> Sanat okulu, cezaevi ve darülaceze atölyelerinde çalışanlara verilen ücretler.</li>
                  <li class="mb-2"><strong>Çırakların Ücretleri (Bent 12):</strong> 3308 sayılı Kanuna tabi çırakların asgari ücreti aşmayan ücretleri.</li>
                  <li class="mb-2"><strong>Asgari Ücret İstisnası (Bent 18):</strong> Çalışanların net asgari ücrete isabet eden aylık ücret tutarları tamamen gelir vergisinden istisnadır.</li>
                </ul>
              </div>
            </div>

            <!-- Grup 2: Sosyal Yardım & Yan Ödemeler -->
            <div class="col-md-6">
              <div class="p-3 rounded border bg-white h-100">
                <span class="badge-warning-custom mb-2">Sosyal &amp; Yan Ödemeler</span>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.05rem; line-height: 1.7;" style="list-style-type: decimal;">
                  <li class="mb-2"><strong>Günlük Yemek Bedeli (Bent 8):</strong> İş yerinde yemek verilmeyen durumlarda günlük yemek bedelinin 2026 yılı için <strong>300 TL</strong>'ye kadar olan kısmı istisnadır.</li>
                  <li class="mb-2"><strong>Konut Tedariki (Bent 9):</strong> Madenlerde/fabrikalarda çalışanlara ve memurlara sağlanan brüt <strong>100 m²</strong>'yi aşmayan lojman tahsisleri vergisizdir.</li>
                  <li class="mb-2"><strong>Ulaşım Gideri (Bent 10):</strong> İşverence taşıma sağlanmayan hallerde, günlük toplu taşıma kartı/bileti olarak ödenen <strong>158 TL</strong>'ye kadar olan kısım istisnadır.</li>
                  <li class="mb-2"><strong>Kreş Yardımı (Bent 16):</strong> Kadın çalışanlar için çocuk başına brüt asgari ücretin <strong>%50</strong>'sini aşmayan kreş ödemeleri istisnadır.</li>
                </ul>
              </div>
            </div>

            <!-- Grup 3: Sektörel & Özel Görevler -->
            <div class="col-md-6">
              <div class="p-3 rounded border bg-white h-100">
                <span class="badge-info-custom mb-2">Sektörel &amp; Özel Görevler</span>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.05rem; line-height: 1.7;" style="list-style-type: decimal;">
                  <li class="mb-2"><strong>Muaf Esnaf Yanında Çalışanlar (Bent 2):</strong> Gelir vergisinden muaf esnafların veya çiftçilerin yanında çalışan işçilerin ücretleri istisnadır.</li>
                  <li class="mb-2"><strong>Yer Altı Maden İşçileri (Bent 3):</strong> Toprak altı maden işletmelerinde yer altında geçen sürelere ait ücretlerin tamamı vergisizdir.</li>
                  <li class="mb-2"><strong>Köy Hizmetlileri &amp; Bekçiler (Bent 5):</strong> Köy bütçesinden ödenen muhtar, katip, korucu, imam, bekçi ücretleri ile çiftçi mallarını koruma bekçilerinin ücretleri.</li>
                  <li class="mb-2"><strong>Amatör Sporcular &amp; Hakemler (Bent 15):</strong> Yüz ve daha az işçi çalıştıranlarda 1, yüzden fazla işçi çalıştıranlarda 2 amatör sporcuya ödenen ücretler vergisizdir.</li>
                  <li class="mb-2"><strong>Pilot ve Kabin Memurları (Bent 17):</strong> Yerli sivil havacılık şirketlerinde uçuş personeline ödenen aylık ücretlerin <strong>%70</strong>'i gelir vergisinden istisnadır.</li>
                </ul>
              </div>
            </div>

            <!-- Grup 4: Uluslararası & Nitelikli Hizmetler -->
            <div class="col-md-6">
              <div class="p-3 rounded border bg-white h-100">
                <span class="badge-danger-custom mb-2">Uluslararası &amp; Nitelikli</span>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.05rem; line-height: 1.7;" style="list-style-type: decimal;">
                  <li class="mb-2"><strong>Sandık &amp; Emekli Aylıkları (Bent 11 &amp; 13):</strong> Emekli sandıkları ve SSK geçici 20. md sandıklarınca bağlanan aylıklar ile yurt dışı sandıklardan ödenen emekli aylıkları.</li>
                  <li class="mb-2"><strong>Dar Mükellef İşveren Döviz Ödemeleri (Bent 14):</strong> Dar mükellef şirketlerin yurt dışı kazançlarından çalışanlarına döviz olarak ödedikleri ücretler.</li>
                  <li class="mb-2"><strong>Yurt Dışı Şantiye Ücretleri (Bent 19):</strong> Yurt dışı inşaat, onarım, montaj ve teknik hizmetlerde çalışan ve ücreti yurt dışı kazançtan dövizle ödenen personelin ücretleri istisnadır.</li>
                  <li class="mb-2"><strong>Nitelikli Hizmet Personeli (Bent 20):</strong> Nitelikli hizmet merkezlerinde çalışanların ücretlerinin brüt asgari ücretin <strong>3 katına</strong> (İstanbul Finans Merkezinde ve endüstri bölgelerinde <strong>5 katına</strong>) kadar olan kısmı istisnadır.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 24") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-wallet2 me-2"></i>Yolluk &amp; Harcırah</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Gider Karşılıklarında Vergi İstisnası</p>
          <p class="text-dark mb-3">Harcırah Kanununa tabi kurumlardan veya özel firmalardan çalışanlara görev gereği seyahatlerinde verilen gündelikler, yolluklar ve fiili yol giderleri gelir vergisinden istisnadır.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Devlet Memurları Harcırahları</h6>
                <p class="text-dark mb-0 small">Harcırah Kanunu uyarınca memurlara ödenen yol gideri, taşıma gideri, yer değiştirme masrafı ve gündeliklerin tamamı gelir vergisinden muaftır.</p>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-exclamation-circle-fill text-warning me-2"></i>Özel Sektör Çalışanları Limiti</h6>
                <p class="text-dark mb-0 small">Özel sektör çalışanlarına ödenen harcırah gündeliklerinin, devlet memurlarına ödenen en yüksek gündelik tutarını (müsteşar gündeliği) aşmayan kısmı vergisizdir. Aşan kısım ücret olarak vergilendirilir.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 25") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-heart-pulse me-2"></i>Tazminat &amp; Kıdem</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Tazminat ve Yardımlarda İstisnalar</p>
          <p class="text-dark mb-3">Çalışanlara iş sözleşmelerinin sonlanması, sağlık sorunları veya ölüm gibi nedenlerle ödenen yasal tazminatlar vergilendirilmez.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-briefcase text-success me-2"></i>Kıdem Tazminatı ve İkale Ödemeleri</h6>
                <p class="text-dark mb-0 small">İş Kanununa göre ödenen kıdem tazminatlarının yasal tavanı aşmayan tutarlarının tamamı ile ikale (karşılıklı anlaşma) kapsamındaki kıdem tazminatı payları vergiden istisnadır. Kıdem tavanını aşan ödemeler ücret gibi vergilendirilir.</p>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-shield-fill text-danger me-2"></i>Diğer Yardımlar ve Nafakalar</h6>
                <p class="text-dark mb-0 small">İş kazası veya meslek hastalığı sonucu verilen tazminatlar, işsizlik maaşları, işe başlatmama tazminatları, yetim/dul yardımları ile yasal nafaka ödemelerinin tamamı vergisizdir.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 26") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-award me-2"></i>Şehit &amp; Gazi Hakları</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Vatan Hizmetleri Yardımlarında İstisna</p>
          <p class="text-dark mb-3">Harp malullüğü zamları, şehitlerin dul ve yetimlerine yapılan ödemeler ile vatan hizmetleri tertibinden bağlanan gazi aylıkları ve mükafatlar gelir vergisinden tamamen istisnadır.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-star-fill text-warning"></i>Vatani Hizmet Aylıkları</h6>
                <p class="text-dark mb-0 small">İstiklal Madalyası şeref aylıkları ile gazilere ve şehit ailelerine bağlanan tüm aylıklar vergiden istisnadır.</p>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-cash text-success"></i>Sosyal Yardımlar</h6>
                <p class="text-dark mb-0 small">Devlet tarafından şehit yakınları ve gazilerin barınma, eğitim ve sağlık ihtiyaçları için yapılan her türlü ayni ve nakdi yardımlar vergi dışıdır.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 27") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-tools me-2"></i>İş Kıyafetleri &amp; İaşe</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Teçhizat ve Tayın Bedellerinde İstisna</p>
          <p class="text-dark mb-3">İşin gereği olarak personele sağlanan iş kıyafetleri ile askeri ve güvenlik personeline sağlanan yiyecek yardımları vergisizdir.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-shield-fill text-success"></i>Demirbaş ve Üniformalar</h6>
                <p class="text-dark mb-0 small">Hizmet erbabına iş yerinde giyilmek üzere işveren tarafından verilen ve işten ayrılınca geri alınan giyim eşyaları ile baret, tulum ve diğer iş koruma araçları vergisizdir.</p>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-egg-fried text-success"></i>Tayın ve Eğitim Yardımı</h6>
                <p class="text-dark mb-0 small">Askeri personele, emniyet teşkilatına ve orman muhafaza memurlarına verilen tayın bedelleri ile öğrencilere sağlanan yurt ve yemek imkanları istisnadır.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 28") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-mortarboard me-2"></i>Eğitim &amp; Burs</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Tahsil ve Tatbikat Ödemelerinde İstisna</p>
          <p class="text-dark mb-3">Öğrencilere eğitim, burs, barınma ve geçim gideri olarak ödenen paralar ile stajyer öğrencilere verilen tatbikat ücretleri gelir vergisinden tamamen istisnadır.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-check-circle-fill text-success"></i>Öğrenci Bursları</h6>
                <p class="text-dark mb-0 small">Resmi daireler, dernekler, vakıflar veya şirketler tarafından öğrencilere tahsil, geçim ve yurt dışı staj için verilen burslar vergi dışıdır.</p>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-briefcase-fill text-success"></i>Staj ve Pratik Eğitim</h6>
                <p class="text-dark mb-0 small">Mesleki okullarda veya üniversitelerde okuyan öğrencilerin staj, tatbikat ve pratik eğitimleri sırasında aldıkları ücretler gelir vergisinden istisnadır.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 29") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-trophy me-2"></i>Teşvik Ödülleri</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Teşvik İkramiye ve Mükafatları İstisnası</p>
          <p class="text-dark mb-3">Bilimsel, tarımsal, sanatsal veya memleket yararına diğer işleri teşvik etmek amacıyla verilen ödüller, amatör sporcu ödülleri ile amatör lig hakem ücretleri vergisizdir.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-award-fill text-warning"></i>Bilim ve Sanat Ödülleri</h6>
                <p class="text-dark mb-0 small">İlim, fen, güzel sanatlar ve tarımı teşvik amacıyla hükümet veya hayır kurumlarınca verilen ödüller vergiden istisnadır.</p>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-dribbble text-success"></i>Amatör Spor Hakemleri</h6>
                <p class="text-dark mb-0 small">Amatör sporculara verilen ödüller ile amatör lig müsabakalarını yöneten hakemlere ödenen maç ücretleri vergisizdir (profesyonel lig hakemleri hariç).</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 30") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-shop-window me-2"></i>Sergi &amp; Panayır</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Sergi ve Panayır İstisnası</p>
          <p class="text-dark mb-3">Dar mükellefiyete tabi kişilerin (yurt dışı mukimleri), hükümet müsaadesiyle açılan uluslararası sergi ve panayırlarda yaptıkları ticari veya serbest meslek kazançları vergiden istisnadır.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-globe me-2"></i>Uluslararası Fuarlar</h6>
                <p class="text-dark mb-0 small">Türkiye'de daimi temsilcilik veya işyeri açmaksızın uluslararası fuarlarda stant açan dar mükelleflerin bu satışlardan doğan gelirleri istisnadır.</p>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2"><i class="bi bi-shield-check text-success"></i>Daimi Temsilci Şartı</h6>
                <p class="text-dark mb-0 small">İstisnadan yararlanabilmek için Türkiye'de daimi bir iş yeri veya temsilci bulunmaması gerekmektedir. Aksi takdirde vergi mükellefiyeti başlar.</p>
              </div>
            </div>
          </div>
        </div>
      `;

    } else if (madde === "Mükerrer Madde 80") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-arrow-up-right-circle me-2"></i>Değer Artış Kazancı</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Değer Artışı Kazançlarında İstisna</p>
          <p class="text-dark mb-3">Mal ve hakların elden çıkarılmasından (satış, devir, trampa, takas, kamulaştırma vb.) doğan kazançlar değer artışı kazancıdır.</p>
          
          <div class="alert alert-danger py-2 px-3 mb-3 rounded-3" style="font-size: 1.05rem; line-height: 1.6;" style="font-size: 1.05rem; line-height: 1.6;">
            <i class="bi bi-info-circle-fill me-2"></i><strong>2026 Yılı İstisna Limiti:</strong> Bir takvim yılında elde edilen değer artışı kazancının (menkul kıymet satışları hariç) <strong>150.000 TL</strong>'si gelir vergisinden istisnadır. Taksi, dolmuş, minibüs ve umum servis plakası satış kazançlarının ise <strong>tamamı</strong> istisnadır.
          </div>

          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2" style="font-size: 1.15rem;"><i class="bi bi-check-circle-fill text-success me-2"></i>Vergi Dışı Tutulan Haller (Hariçler)</h6>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.08rem; line-height: 1.7;">
                  <li class="mb-2"><strong>İvazsız İktisaplar:</strong> Miras veya bağış yoluyla edinilen tüm mal ve hakların satışı (süreye bakılmaksızın vergisizdir).</li>
                  <li class="mb-2"><strong>2 Yıllık Hisse Senetleri:</strong> Tam mükellef şirketlere ait olan ve 2 yıldan fazla süreyle elde tutulan hisse senetlerinin satışı.</li>
                  <li class="mb-2"><strong>5 Yıl Sonrası Gayrimenkul:</strong> Satın alınan gayrimenkullerin 5 tam yıl geçtikten sonra satılması.</li>
                </ul>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2" style="font-size: 1.15rem;"><i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>Vergiye Tabi Başlıca Durumlar</h6>
                <ul class="ps-3 mb-0 text-dark" style="font-size: 1.08rem; line-height: 1.7;">
                  <li class="mb-2">5 yıl içinde satılan gayrimenkuller.</li>
                  <li class="mb-2">Menkul kıymetler ve diğer sermaye piyasası araçlarının satışı.</li>
                  <li class="mb-2">Telif hakları ve ihtira beratlarının müellifleri/mirasçıları dışındaki üçüncü kişilerce satışı.</li>
                  <li class="mb-2">Ortaklık haklarının/hisselerinin elden çıkarılması.</li>
                  <li class="mb-2">Faaliyeti durdurulan bir işletmenin kısmen veya tamamen satılması.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 82") {
      detail = `
        <div class="p-4 rounded-3 border-0 bg-white">
          <div class="d-flex align-items-center mb-3">
            <span class="badge-warning-custom fs-6 px-3 py-2"><i class="bi bi-clock-history me-2"></i>Arızi Kazançlar</span>
          </div>
          <p class="fs-4 fw-bold text-dark mb-2">Arızi Kazançlarda İstisna</p>
          <p class="text-dark mb-3">Süreklilik göstermeyen, arızi olarak gerçekleştirilen faaliyetlerden elde edilen vergiye tabi kazançlardır.</p>
          
          <div class="alert alert-warning py-2 px-3 mb-3 rounded-3" style="font-size: 1.05rem; line-height: 1.6;" style="font-size: 1.05rem; line-height: 1.6;">
            <i class="bi bi-info-circle-fill me-2"></i><strong>2026 Yılı İstisna Limiti:</strong> Arızi kazançlar toplamının <strong>350.000 TL</strong>'lik kısmı gelir vergisinden istisnadır. (İşe hiç başlamama veya ihaleye girmeme karşılığı alınan bedeller bu istisnanın dışındadır ve tamamı vergilendirilir.)
          </div>

          <div class="row g-3">
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2" style="font-size: 1.15rem;"><i class="bi bi-list-stars me-2 text-primary"></i>Kapsamdaki Arızi Kazançlar</h6>
                <ul class="ps-3 mb-0 text-dark" style="list-style-type: decimal; font-size: 1.08rem; line-height: 1.7;">
                  <li class="mb-2">Arızi olarak ticari işlemlere aracılık yapılması (tavassut).</li>
                  <li class="mb-2">Ticari/zirai veya mesleki faaliyetin durdurulması/terk edilmesi karşılığında alınan bedeller.</li>
                  <li class="mb-2">Gayrimenkullerin tahliyesi veya kiracılık hakkının devri karşılığında alınan peştemallıklar/tazminatlar.</li>
                  <li class="mb-2">Arızi serbest meslek faaliyetleri (tek seferlik danışmanlık vb.).</li>
                  <li class="mb-2">Terk edilen işlerle ilgili sonradan tahsil edilen alacaklar (şüpheli/değersiz alacak tahsilleri dahil).</li>
                </ul>
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-3 bg-light rounded-3 h-100">
                <h6 class="fw-bold text-dark mb-2" style="font-size: 1.15rem;"><i class="bi bi-calculator me-2 text-success"></i>Safi Kazanç Nasıl Hesaplanır?</h6>
                <p class="text-dark mb-0" style="font-size: 1.08rem; line-height: 1.7;">Elde edilen hasılattan, varsa belgelendirilen maliyet bedeli, tahliye/satış giderleri ve tevsik edilmek şartıyla yapılan diğer giderlerin indirilmesiyle net arızi kazanç tespit edilir. Kalan tutardan 350.000 TL istisna düşülür.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 31") {
      detail = `
        <div class="row g-3">
          <div class="col-12"><p class="text-dark mb-2 small">Çallışma gücü kayıp oranlarına göre çalışanların aylık vergi matrahından düşülen engellilik indirimleri:</p></div>
          <div class="col-md-4">
            <div class="p-3 rounded border bg-white text-center h-100">
              <span class="badge-info-custom mb-2">1. Derece (%80+)</span>
              <h5 class="fw-bold mb-0 text-dark">12.000 TL</h5>
              <span class="text-dark small">Aylık Matrahtan Düşülür</span>
            </div>
          </div>
          <div class="col-md-4">
            <div class="p-3 rounded border bg-white text-center h-100">
              <span class="badge-info-custom mb-2">2. Derece (%60+)</span>
              <h5 class="fw-bold mb-0 text-dark">7.000 TL</h5>
              <span class="text-dark small">Aylık Matrahtan Düşülür</span>
            </div>
          </div>
          <div class="col-md-4">
            <div class="p-3 rounded border bg-white text-center h-100">
              <span class="badge-info-custom mb-2">3. Derece (%40+)</span>
              <h5 class="fw-bold mb-0 text-dark">3.000 TL</h5>
              <span class="text-dark small">Aylık Matrahtan Düşülür</span>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 89") {
      detail = `
        <div class="p-4 rounded-4 bg-light border-0 shadow-inner" style="max-height: 600px; overflow-y: auto;">
          <h5 class="fw-bold text-dark mb-3"><i class="bi bi-file-earmark-text text-primary me-2"></i>Madde 89: Diğer İndirimler</h5>
          <p class="text-dark mb-4" style="font-size: 1.05rem; line-height: 1.7;">
            Gelir vergisi matrahının tespitinde, yıllık beyannamede bildirilecek gelirlerden aşağıdaki indirimler yasal kurallar çerçevesinde yapılabilir:
          </p>

          <div class="accordion accordion-flush rounded-3 overflow-hidden border" id="madde89Accordion">
            
            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-1">
                  1. Şahıs ve Hayat Sigorta Primleri
                </button>
              </h2>
              <div id="m89-bent-1" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Beyan edilen gelirin <strong>%15'ini</strong> ve asgari ücretin yıllık tutarını (2026 yılı için <strong>228.000 TL</strong>) aşmamak şartıyla; mükellefin şahsına, eşine ve küçük çocuklarına ait hayat sigortalarına ödenen primlerin <strong>%50'si</strong> ile ölüm, kaza, hastalık, sağlık, engellilik, analık, doğum ve tahsil gibi şahıs sigorta primlerinin <strong>%100'ü</strong> matrahtan indirilebilir. Sigorta şirketinin merkezi Türkiye'de olmalıdır.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-2">
                  2. Eğitim ve Sağlık Harcamaları
                </button>
              </h2>
              <div id="m89-bent-2" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Beyan edilen gelirin <strong>%10'unu</strong> aşmaması, Türkiye'de yapılması ve gelir veya kurumlar vergisi mükellefiyeti bulunan gerçek veya tüzel kişilerden alınacak fatura/vesikalarla belgelenmesi şartıyla mükellefin kendisi, eşi ve küçük çocuklarına ilişkin yapılan eğitim ve sağlık harcamaları.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-3">
                  3. Engellilik İndirimi (Serbest Meslek / Hizmet Erbabı)
                </button>
              </h2>
              <div id="m89-bent-3" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Serbest meslek faaliyetinde bulunan engellilerin beyan edilen gelirlerine, 31 inci maddede yer alan esaslara göre hesaplanan yıllık engellilik indirimi uygulanır. Bu indirimden bakmakla yükümlü olduğu engelli kişi bulunan serbest meslek erbabı ile ücretli çalışanlar da yararlanır.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-4">
                  4. Kamu Kurumu, Kamu Derneği ve Vakıf Bağışları
                </button>
              </h2>
              <div id="m89-bent-4" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Genel ve özel bütçeli kamu idareleri, il özel idareleri, belediyeler, köyler ile kamu yararına çalışan dernekler ve Cumhurbaşkanınca vergi muafiyeti tanınan vakıflara yapılan bağış ve yardımların beyan edilecek gelirin <strong>%5'ini</strong> (kalkınmada öncelikli yöreler için %10'unu) aşmayan kısmı makbuz karşılığı indirilir.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-5">
                  5. Eğitim, Sağlık, İbadethane Tesisleri Yapım Bağışları
                </button>
              </h2>
              <div id="m89-bent-5" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Kamu idarelerine, belediyelere bağışlanan okul, sağlık tesisi, öğrenci yurdu, çocuk yuvası, huzurevi, rehabilitasyon merkezi, ibadethaneler ve Diyanet denetimindeki din eğitimi tesislerinin inşası için yapılan harcamalar veya yapılan her türlü bağış ve nakdi/ayni yardımların <strong>%100'ü (tamamı)</strong> sınırsız olarak matrahtan düşülür.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-6">
                  6. Gıda Bankacılığı Bağışları
                </button>
              </h2>
              <div id="m89-bent-6" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Fakirlere yardım amacıyla gıda bankacılığı faaliyetinde bulunan Darülacezeye, vakıf ve derneklere Maliye Bakanlığınca belirlenen usul çerçevesinde bağışlanan gıda, temizlik, giyecek ve yakacak maddelerinin maliyet bedelinin <strong>%100'ü (tamamı)</strong> beyannameden indirilebilir.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-7">
                  7. Kültür ve Sanat Faaliyetleri Sponsorluk ve Bağışları
                </button>
              </h2>
              <div id="m89-bent-7" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Kültür ve sanat faaliyetlerine ilişkin ticari olmayan organizasyonların yapılmasına, kütüphane, müze, sanat galerisi yapım/modernizasyonuna, arkeolojik kazılara, nadir eserlerin korunması gibi Kültür ve Turizm Bakanlığınca desteklenen harcamalar ile bu amaçla yapılan bağış ve yardımların <strong>%100'ü (tamamı)</strong> beyannamede indirilir.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-8">
                  8. Sponsorluk Harcamaları
                </button>
              </h2>
              <div id="m89-bent-8" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  3289 sayılı Gençlik ve Spor Genel Müdürlüğü Kanunu ile TFF Kanunu kapsamında yapılan spor sponsorluk harcamalarının; <strong>amatör spor dalları için %100'ü (tamamı)</strong>, <strong>profesyonel spor dalları için %50'si</strong> beyan edilen gelirden indirilir.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-10">
                  10. Cumhurbaşkanlığınca Başlatılan Yardım Kampanyaları
                </button>
              </h2>
              <div id="m89-bent-10" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Cumhurbaşkanınca başlatılan veya desteklenen ulusal yardım kampanyalarına (deprem, yangın, sel vb. AFAD koordinasyonundaki kampanyalar) makbuz karşılığı yapılan ayni ve nakdi bağışların <strong>%100'ü (tamamı)</strong> sınırsız olarak indirilebilir.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-11">
                  11. Darülaceze, Kızılay ve Yeşilay Nakdi Bağışları
                </button>
              </h2>
              <div id="m89-bent-11" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  İktisadi işletmeleri hariç olmak üzere; Darülacezeye, Türkiye Kızılay Derneğine ve Türkiye Yeşilay Cemiyetine makbuz karşılığında yapılan nakdi bağış ve yardımların <strong>%100'ü (tamamı)</strong> beyannamede indirilir.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-12">
                  12. Girişim Sermayesi Fonu
                </button>
              </h2>
              <div id="m89-bent-12" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Vergi Usul Kanununun 325/A maddesine göre girişim sermayesi fonu olarak ayrılan tutarların beyan edilen gelirin <strong>%10'unu</strong> aşmayan kısmı indirim konusu yapılabilir.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-13">
                  13. Yurt Dışına Sunulan Hizmet İşletmeleri Kazanç İndirimi
                </button>
              </h2>
              <div id="m89-bent-13" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Yabancılara Türkiye'de verilen ve yurt dışında yararlanılan yazılım, tasarım, mühendislik, veri saklama, çağrı merkezi vb. hizmetlerden elde edilen kazancın beyanname verme tarihine kadar Türkiye'ye getirilmesi şartıyla <strong>%100'ü</strong> (Cumhurbaşkanı kararı uyarınca oran %100 olarak uygulanmaktadır) indirilir.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-14">
                  14. Korumalı İşyeri İndirimi
                </button>
              </h2>
              <div id="m89-bent-14" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Korumalı işyerlerinde istihdam edilen zihinsel/ruhsal engelli çalışanlar için yapılan ücret ödemelerinin <strong>%100'ü</strong> oranında indirim uygulanır. Yıllık indirim her bir çalışan için brüt asgari ücretin %150'sini aşamaz.
                </div>
              </div>
            </div>

            <div class="accordion-item bg-white">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed fw-bold text-dark" type="button" data-bs-toggle="collapse" data-bs-target="#m89-bent-16">
                  16. E-Ticaret Mikro İhracat Kazanç İndirimi
                </button>
              </h2>
              <div id="m89-bent-16" class="accordion-collapse collapse" data-bs-parent="#madde89Accordion">
                <div class="accordion-body text-dark" style="font-size: 1rem; line-height: 1.6;">
                  Hızlı kargo taşımacılığı yapan şirketler aracılığıyla düzenlenen ETGB ile gerçekleştirilen mal ihracatı kapsamında elde edilen kazancın <strong>%50'si</strong>, sigortalı olma ve çalışan sayısı şartlarını yerine getirmek kaydıyla indirilir. (Yıllık 400.000 TL - 2.400.000 TL arasındaki hasılat dilimlerine göre kendisinin sigortalı olması ve en az 1-3 ortalama tam zamanlı işçi çalıştırma kuralları mevcuttur).
                </div>
              </div>
            </div>

          </div>
        </div>
      `;
    } else if (madde === "Madde 86") {
      detail = `
        <div class="row g-3">
          <div class="col-12"><p class="text-dark mb-2 small">Gelirlerin hangi durumlarda beyannameye dahil edilmeyeceğini veya toplanmayacağını belirleyen yıllık limit ve kurallar:</p></div>
          <div class="col-md-6">
            <div class="p-3 rounded border bg-white h-100">
              <span class="badge-success-custom mb-2">Tek İşverenden Alınan Ücret</span>
              <p class="text-dark mb-0">Tek işverenden alınan tevkif edilmiş ücretlerde yıllık gelir <strong>5.300.000 TL</strong> sınırını aşmadığı sürece beyanname verilmez.</p>
            </div>
          </div>
          <div class="col-md-6">
            <div class="p-3 rounded border bg-white h-100">
              <span class="badge-success-custom mb-2">Birden Fazla İşverenden Ücret</span>
              <p class="text-dark mb-0">Birden sonraki işverenden alınan ücretlerin toplamı <strong>400.000 TL</strong>'yi ve toplam ücret geliri <strong>5.300.000 TL</strong>'yi aşmıyorsa beyanname verilmez.</p>
            </div>
          </div>
          <div class="col-md-6">
            <div class="p-3 rounded border bg-white h-100">
              <span class="badge-success-custom mb-2">Tevkifatsız Faiz &amp; Kira Geliri</span>
              <p class="text-dark mb-0">Stopaj ve istisna uygulamasına konu olmayan (örneğin yurt dışı faiz geliri, stopajsız işyeri kirası) gelirlerin toplamı yıllık <strong>22.000 TL</strong> limitini aşmıyorsa beyan edilmez.</p>
            </div>
          </div>
          <div class="col-md-6">
            <div class="p-3 rounded border bg-white h-100">
              <span class="badge-success-custom mb-2">Dar Mükellefler</span>
              <p class="text-dark mb-0">Türkiye'de tamamı vergi kesintisi (stopaj) yoluyla vergilendirilmiş ücret, kira, faiz veya serbest meslek kazancı olan dar mükellefler beyanname vermezler.</p>
            </div>
          </div>
        </div>
      `;
    } else if (madde === "Madde 103") {
      detail = `
        <div class="legal-text-box" style="max-height: 400px; overflow-y: auto;">
          <p class="text-dark small mb-3">Gelir vergisine tabi gelirler aşağıdaki oranlar çerçevesinde vergilendirilir:</p>

          <div class="mb-3">
            <h6 class="fw-bold text-danger">2026 Takvim Yılı Tarifesi (332 Seri No.lu Genel Tebliğ)</h6>
            <table class="table table-sm table-bordered table-striped small mb-0">
              <thead class="table-light">
                <tr><th>Gelir Dilimi Tutarı</th><th class="text-center">Oran</th></tr>
              </thead>
              <tbody>
                <tr><td>190.000 TL'ye kadar</td><td class="text-center fw-bold">%15</td></tr>
                <tr><td>400.000 TL'nin 190.000 TL'si için 28.500 TL, fazlası</td><td class="text-center fw-bold">%20</td></tr>
                <tr><td>1.000.000 TL'nin 400.000 TL'si için 70.500 TL (Ücretlilerde 1.500.000 TL'nin 400.000 TL'si için 70.500 TL), fazlası</td><td class="text-center fw-bold">%27</td></tr>
                <tr><td>5.300.000 TL'nin 1.000.000 TL'si için 232.500 TL (Ücretlilerde 5.300.000 TL'nin 1.500.000 TL'si için 367.500 TL), fazlası</td><td class="text-center fw-bold">%35</td></tr>
                <tr><td>5.300.000 TL'den fazlasının 5.300.000 TL'si için 1.737.500 TL (Ücretlilerde 5.300.000 TL'den fazlasının 5.300.000 TL'si için 1.697.500 TL), fazlası</td><td class="text-center fw-bold">%40</td></tr>
              </tbody>
            </table>
          </div>

          <div class="mb-3">
            <h6 class="fw-bold text-secondary">2025 Takvim Yılı Tarifesi (329 Seri No.lu Genel Tebliğ)</h6>
            <table class="table table-sm table-bordered table-striped small mb-0">
              <thead class="table-light">
                <tr><th>Gelir Dilimi Tutarı</th><th class="text-center">Oran</th></tr>
              </thead>
              <tbody>
                <tr><td>158.000 TL'ye kadar</td><td class="text-center fw-bold">%15</td></tr>
                <tr><td>330.000 TL'nin 158.000 TL'si için 23.700 TL, fazlası</td><td class="text-center fw-bold">%20</td></tr>
                <tr><td>800.000 TL'nin 330.000 TL'si için 58.100 TL (Ücretlilerde 1.200.000 TL'nin 330.000 TL'si için 58.100 TL), fazlası</td><td class="text-center fw-bold">%27</td></tr>
                <tr><td>4.300.000 TL'nin 800.000 TL'si için 185.000 TL (Ücretlilerde 4.300.000 TL'nin 1.200.000 TL'si için 293.000 TL), fazlası</td><td class="text-center fw-bold">%35</td></tr>
                <tr><td>4.300.000 TL'den fazlasının 4.300.000 TL'si için 1.410.000 TL (Ücretlilerde 4.300.000 TL'den fazlasının 4.300.000 TL'si için 1.378.000 TL), fazlası</td><td class="text-center fw-bold">%40</td></tr>
              </tbody>
            </table>
          </div>

          <div class="mb-3">
            <h6 class="fw-bold text-secondary">2024 Takvim Yılı Tarifesi (324 Seri No.lu Genel Tebliğ)</h6>
            <table class="table table-sm table-bordered table-striped small mb-0">
              <thead class="table-light">
                <tr><th>Gelir Dilimi Tutarı</th><th class="text-center">Oran</th></tr>
              </thead>
              <tbody>
                <tr><td>110.000 TL'ye kadar</td><td class="text-center fw-bold">%15</td></tr>
                <tr><td>230.000 TL'nin 110.000 TL'si için 16.500 TL, fazlası</td><td class="text-center fw-bold">%20</td></tr>
                <tr><td>580.000 TL'nin 230.000 TL'si için 40.500 TL (Ücretlilerde 870.000 TL'nin 230.000 TL'si için 40.500 TL), fazlası</td><td class="text-center fw-bold">%27</td></tr>
                <tr><td>3.000.000 TL'nin 580.000 TL'si için 135.000 TL (Ücretlilerde 3.000.000 TL'nin 870.000 TL'si için 213.300 TL), fazlası</td><td class="text-center fw-bold">%35</td></tr>
                <tr><td>3.000.000 TL'den fazlasının 3.000.000 TL'si için 982.000 TL (Ücretlilerde 3.000.000 TL'den fazlasının 3.000.000 TL'si için 958.800 TL), fazlası</td><td class="text-center fw-bold">%40</td></tr>
              </tbody>
            </table>
          </div>

          <div class="mb-3">
            <h6 class="fw-bold text-secondary">2023 Takvim Yılı Tarifesi (323 Seri No.lu Genel Tebliğ)</h6>
            <table class="table table-sm table-bordered table-striped small mb-0">
              <thead class="table-light">
                <tr><th>Gelir Dilimi Tutarı</th><th class="text-center">Oran</th></tr>
              </thead>
              <tbody>
                <tr><td>70.000 TL'ye kadar</td><td class="text-center fw-bold">%15</td></tr>
                <tr><td>150.000 TL'nin 70.000 TL'si için 10.500 TL, fazlası</td><td class="text-center fw-bold">%20</td></tr>
                <tr><td>370.000 TL'nin 150.000 TL'si için 26.500 TL (Ücretlilerde 550.000 TL'nin 150.000 TL'si için 26.500 TL), fazlası</td><td class="text-center fw-bold">%27</td></tr>
                <tr><td>1.900.000 TL'nin 370.000 TL'si için 85.900 TL (Ücretlilerde 1.900.000 TL'nin 550.000 TL'si için 134.500 TL), fazlası</td><td class="text-center fw-bold">%35</td></tr>
                <tr><td>1.900.000 TL'den fazlasının 1.900.000 TL'si için 621.400 TL (Ücretlilerde 1.900.000 TL'den fazlasının 1.900.000 TL'si için 607.000 TL), fazlası</td><td class="text-center fw-bold">%40</td></tr>
              </tbody>
            </table>
          </div>

          <div class="mb-3">
            <h6 class="fw-bold text-secondary">2022 Takvim Yılı Tarifesi (317 Seri No.lu Genel Tebliğ)</h6>
            <table class="table table-sm table-bordered table-striped small mb-0">
              <thead class="table-light">
                <tr><th>Gelir Dilimi Tutarı</th><th class="text-center">Oran</th></tr>
              </thead>
              <tbody>
                <tr><td>32.000 TL'ye kadar</td><td class="text-center fw-bold">%15</td></tr>
                <tr><td>70.000 TL'nin 32.000 TL'si için 4.800 TL, fazlası</td><td class="text-center fw-bold">%20</td></tr>
                <tr><td>170.000 TL'nin 70.000 TL'si için 12.400 TL (Ücretlilerde 250.000 TL'nin 70.000 TL'si için 12.400 TL), fazlası</td><td class="text-center fw-bold">%27</td></tr>
                <tr><td>880.000 TL'nin 170.000 TL'si için 39.400 TL (Ücretlilerde 880.000 TL'nin 250.000 TL'si için 61.000 TL), fazlası</td><td class="text-center fw-bold">%35</td></tr>
                <tr><td>880.000 TL'den fazlasının 880.000 TL'si için 287.900 TL (Ücretlilerde 880.000 TL'den fazlasının 880.000 TL'si için 281.500 TL), fazlası</td><td class="text-center fw-bold">%40</td></tr>
              </tbody>
            </table>
          </div>

          <div class="mb-3">
            <h6 class="fw-bold text-secondary">2021 Takvim Yılı Tarifesi (313 Seri No.lu Genel Tebliğ)</h6>
            <table class="table table-sm table-bordered table-striped small mb-0">
              <thead class="table-light">
                <tr><th>Gelir Dilimi Tutarı</th><th class="text-center">Oran</th></tr>
              </thead>
              <tbody>
                <tr><td>24.000 TL'ye kadar</td><td class="text-center fw-bold">%15</td></tr>
                <tr><td>53.000 TL'nin 24.000 TL'si için 3.600 TL, fazlası</td><td class="text-center fw-bold">%20</td></tr>
                <tr><td>130.000 TL'nin 53.000 TL'si için 9.400 TL (Ücretlilerde 190.000 TL'nin 53.000 TL'si için 9.400 TL), fazlası</td><td class="text-center fw-bold">%27</td></tr>
                <tr><td>650.000 TL'nin 130.000 TL'si için 30.190 TL (Ücretlilerde 650.000 TL'nin 190.000 TL'si için 46.390 TL), fazlası</td><td class="text-center fw-bold">%35</td></tr>
                <tr><td>650.000 TL'den fazlasının 650.000 TL'si için 212.190 TL (Ücretlilerde 650.000 TL'den fazlasının 650.000 TL'si için 207.390 TL), fazlası</td><td class="text-center fw-bold">%40</td></tr>
              </tbody>
            </table>
          </div>

          <div class="mb-3">
            <h6 class="fw-bold text-secondary">2020 Takvim Yılı Tarifesi (310 Seri No.lu Genel Tebliğ)</h6>
            <table class="table table-sm table-bordered table-striped small mb-0">
              <thead class="table-light">
                <tr><th>Gelir Dilimi Tutarı</th><th class="text-center">Oran</th></tr>
              </thead>
              <tbody>
                <tr><td>22.000 TL'ye kadar</td><td class="text-center fw-bold">%15</td></tr>
                <tr><td>49.000 TL'nin 22.000 TL'si için 3.300 TL, fazlası</td><td class="text-center fw-bold">%20</td></tr>
                <tr><td>120.000 TL'nin 49.000 TL'si için 8.700 TL (Ücretlilerde 180.000 TL'nin 49.000 TL'si için 8.700 TL), fazlası</td><td class="text-center fw-bold">%27</td></tr>
                <tr><td>600.000 TL'nin 120.000 TL'si için 27.870 TL (Ücretlilerde 600.000 TL'nin 180.000 TL'si için 44.070 TL), fazlası</td><td class="text-center fw-bold">%35</td></tr>
                <tr><td>600.000 TL'den fazlasının 600.000 TL'si için 195.870 TL (Ücretlilerde 600.000 TL'den fazlasının 600.000 TL'si için 191.070 TL), fazlası</td><td class="text-center fw-bold">%40</td></tr>
              </tbody>
            </table>
          </div>

        </div>
      `;
    } else {
      detail = `
        <div class="p-3 rounded border bg-white">
          <p class="text-dark mb-0">${name} kazanç kalemi, Gelir Vergisi Kanunu kapsamında beyannamede dikkate alınabilecek yasal indirim, muafiyet ve istisnalar arasında yer almaktadır.</p>
        </div>
      `;
    }
    
    return `
      <div class="p-3 rounded-3" style="background-color: #f8fafc; border-left: 4px solid #64748b;">
        <div style="font-size:1.05rem; line-height: 1.7; color: #1e293b;">${detail}</div>
      </div>
    `;
  }

  /* ── Açıklama kutusunu göster/gizle ── */
  function toggleDescription(row, name, madde) {
    let nextEl = row.nextElementSibling;
    
    if (!nextEl || !nextEl.classList.contains('kvi-description-collapse')) {
      const collapseDiv = document.createElement('div');
      collapseDiv.className = 'kvi-description-collapse';
      
      const contentDiv = document.createElement('div');
      contentDiv.className = 'kvi-description-content';
      contentDiv.innerHTML = getDescriptionText(name, madde);
      
      collapseDiv.appendChild(contentDiv);
      row.parentNode.insertBefore(collapseDiv, row.nextSibling);
      nextEl = collapseDiv;
    }
    
    const wasExpanded = nextEl.classList.contains('expanded');
    const toggleIcon = row.querySelector('.kvi-toggle-icon');
    
    // Aktif tabdaki diğer tüm açık kutuları kapat
    const activeTab = row.closest('.kvi-tab-content');
    activeTab.querySelectorAll('.kvi-description-collapse.expanded').forEach(el => {
      if (el !== nextEl) {
        el.classList.remove('expanded');
        el.style.maxHeight = '0px';
        const siblingRow = el.previousElementSibling;
        siblingRow.classList.remove('active-row');
        const siblingIcon = siblingRow.querySelector('.kvi-toggle-icon');
        if (siblingIcon) {
          siblingIcon.classList.replace('bi-chevron-up', 'bi-chevron-down');
        }
      }
    });
    
    if (!wasExpanded) {
      nextEl.classList.add('expanded');
      row.classList.add('active-row');
      if (toggleIcon) {
        toggleIcon.classList.replace('bi-chevron-down', 'bi-chevron-up');
      }
      nextEl.style.maxHeight = nextEl.scrollHeight + 'px';
    } else {
      nextEl.classList.remove('expanded');
      row.classList.remove('active-row');
      if (toggleIcon) {
        toggleIcon.classList.replace('bi-chevron-up', 'bi-chevron-down');
      }
      nextEl.style.maxHeight = '0px';
    }
  }


  // ── İNDİRİMLER SİHİRBAZI LOGIC ──
  let indirimType = '';
  function selectIndirimType(type) {
    indirimType = type;
    document.querySelectorAll('.wizard-step-indirim').forEach(el => el.classList.add('d-none'));
    const targetStep = document.getElementById('wiz-indirim-step-2-' + type);
    if (targetStep) targetStep.classList.remove('d-none');
  }

  function indirimGoBack(reset = 0) {
    document.querySelectorAll('.wizard-step-indirim').forEach(el => el.classList.add('d-none'));
    if (reset) {
      document.getElementById('wizIndirimSigortaGelir').value = '';
      document.getElementById('wizIndirimSigortaPrim').value = '';
      document.getElementById('wizIndirimEgitimGelir').value = '';
      document.getElementById('wizIndirimEgitimTutar').value = '';
      document.getElementById('wizIndirimBagisGelir').value = '';
      document.getElementById('wizIndirimBagisTutar').value = '';
      document.getElementById('wiz-indirim-step-1').classList.remove('d-none');
    } else {
      document.getElementById('wiz-indirim-step-1').classList.remove('d-none');
    }
  }

  function showIndirimResult(iconClass, title, desc, advice) {
    document.querySelectorAll('.wizard-step-indirim').forEach(el => el.classList.add('d-none'));
    const resultIcon = document.getElementById('wizIndirimResultIcon');
    resultIcon.className = 'wizard-result-icon mx-auto mb-4 ' + iconClass;
    document.getElementById('wizIndirimResultTitle').textContent = title;
    document.getElementById('wizIndirimResultDesc').innerHTML = desc;
    document.getElementById('wizIndirimResultAdvice').innerHTML = advice;
    document.getElementById('wiz-indirim-result').classList.remove('d-none');
  }

  function evaluateIndirimEngellilik() {
    const deg = document.querySelector('input[name="wizIndirimEngellilikDegree"]:checked').value;
    let monthly = 0;
    let annual = 0;
    if (deg === '1') { monthly = 12000; annual = 144000; }
    else if (deg === '2') { monthly = 6000; annual = 72000; }
    else if (deg === '3') { monthly = 3000; annual = 36000; }

    showIndirimResult(
      'bi-heart-pulse-fill text-danger',
      `${deg}. Derece Engellilik İndirimi`,
      `Seçtiğiniz dereceye göre 2026 yılı aylık vergi indirimi tutarınız <strong>${monthly.toLocaleString('tr-TR')} TL</strong>'dir.`,
      `Yıllık beyannamenizden düşebileceğiniz toplam engellilik indirimi tutarı: <strong>${annual.toLocaleString('tr-TR')} TL</strong> (GVK Madde 31).`
    );
  }

  function evaluateIndirimSigorta() {
    const gelir = parseFloat(document.getElementById('wizIndirimSigortaGelir').value) || 0;
    const prim = parseFloat(document.getElementById('wizIndirimSigortaPrim').value) || 0;
    if (gelir <= 0 || prim <= 0) {
      alert('Lütfen geçerli brüt gelir ve prim tutarları girin.');
      return;
    }
    const limitGelir = gelir * 0.15;
    const limitAsgari = 228000; 
    const finalLimit = Math.min(limitGelir, limitAsgari);
    const deductible = Math.min(prim, finalLimit);

    showIndirimResult(
      'bi-shield-fill-check text-primary',
      'Şahıs Sigortası İndirim Sonucu',
      `Beyan edilen gelirinizin %15'i (${limitGelir.toLocaleString('tr-TR')} TL) ile yıllık brüt asgari ücret limiti (${limitAsgari.toLocaleString('tr-TR')} TL) karşılaştırılmıştır.`,
      `Ödediğiniz primden beyannamede düşebileceğiniz net tutar: <strong>${deductible.toLocaleString('tr-TR')} TL</strong> (GVK Madde 89/1).`
    );
  }

  function evaluateIndirimEgitim() {
    const gelir = parseFloat(document.getElementById('wizIndirimEgitimGelir').value) || 0;
    const tutar = parseFloat(document.getElementById('wizIndirimEgitimTutar').value) || 0;
    const isTr = document.getElementById('wizIndirimEgitimTr').checked;
    
    if (gelir <= 0 || tutar <= 0) {
      alert('Lütfen geçerli brüt gelir ve harcama tutarları girin.');
      return;
    }
    if (!isTr) {
      showIndirimResult(
        'bi-x-circle-fill text-danger',
        'İndirim Uygulanamaz (Yurt Dışı Harcaması)',
        'Eğitim ve sağlık harcamalarının beyannameden düşülebilmesi için harcamanın Türkiye\'de yapılması ve faturalandırılması yasal zorunluluktur.',
        'Harcama yurt dışında yapıldığı veya mükellef olmayan kurumlardan fatura alındığı için <strong>0 TL</strong> indirim uygulanır.'
      );
      return;
    }
    const limit = gelir * 0.10;
    const deductible = Math.min(tutar, limit);

    showIndirimResult(
      'bi-book-fill text-success',
      'Eğitim & Sağlık İndirimi Sonucu',
      `Gelirinizin %10 limiti (${limit.toLocaleString('tr-TR')} TL) ile yaptığınız harcama karşılaştırılmıştır.`,
      `Beyannamede düşebileceğiniz net tutar: <strong>${deductible.toLocaleString('tr-TR')} TL</strong> (GVK Madde 89/2).`
    );
  }

  function evaluateIndirimBagis() {
    const gelir = parseFloat(document.getElementById('wizIndirimBagisGelir').value) || 0;
    const tutar = parseFloat(document.getElementById('wizIndirimBagisTutar').value) || 0;
    const type = document.querySelector('input[name="wizIndirimBagisType"]:checked').value;

    if (gelir <= 0 || tutar <= 0) {
      alert('Lütfen geçerli brüt gelir ve bağış tutarları girin.');
      return;
    }

    let deductible = 0;
    let desc = '';
    if (type === '5') {
      const limit = gelir * 0.05;
      deductible = Math.min(tutar, limit);
      desc = `Kamu yararına çalışan derneklere yapılan bağışlarda brüt gelirinizin %5'i (${limit.toLocaleString('tr-TR')} TL) kadar sınır uygulanır.`;
    } else {
      deductible = tutar;
      desc = `Kamu kurumlarına yapılan ve yasa kapsamında tamamı indirilebilen bağışlarda herhangi bir limit uygulanmaz.`;
    }

    showIndirimResult(
      'bi-hand-thumbs-up-fill text-warning',
      'Bağış & Yardım İndirim Sonucu',
      desc,
      `Beyannamede matrahtan düşebileceğiniz net bağış tutarı: <strong>${deductible.toLocaleString('tr-TR')} TL</strong> (GVK Madde 89/4).`
    );
  }

  // ── MUAFLIKLAR SİHİRBAZI LOGIC ──
  let muafType = '';
  function selectMuafType(type) {
    muafType = type;
    document.querySelectorAll('.wizard-step-muaf').forEach(el => el.classList.add('d-none'));
    
    if (type === 'eticaret') {
      document.getElementById('wiz-muaf-step-2-eticaret').classList.remove('d-none');
    } else if (type === 'gunes') {
      document.getElementById('wiz-muaf-step-2-gunes').classList.remove('d-none');
    } else {
      document.getElementById('wiz-muaf-step-2-gezici').classList.remove('d-none');
    }
  }

  function muafiyetGoBack(reset = 0) {
    document.querySelectorAll('.wizard-step-muaf').forEach(el => el.classList.add('d-none'));
    if (reset) {
      document.getElementById('wizMuafEticaretAmt').value = '';
      document.getElementById('wizMuafGunesKw').value = '';
      document.getElementById('wiz-muaf-step-1').classList.remove('d-none');
    } else {
      document.getElementById('wiz-muaf-step-1').classList.remove('d-none');
    }
  }

  function showMuafResult(iconClass, title, desc, advice) {
    document.querySelectorAll('.wizard-step-muaf').forEach(el => el.classList.add('d-none'));
    const resultIcon = document.getElementById('wizMuafResultIcon');
    resultIcon.className = 'wizard-result-icon mx-auto mb-4 ' + iconClass;
    document.getElementById('wizMuafResultTitle').textContent = title;
    document.getElementById('wizMuafResultDesc').innerHTML = desc;
    document.getElementById('wizMuafResultAdvice').innerHTML = advice;
    document.getElementById('wiz-muaf-result').classList.remove('d-none');
  }

  function evaluateMuafEticaret() {
    const isHome = document.getElementById('wizMuafEticaretHome').checked;
    const noMachine = document.getElementById('wizMuafEticaretNoMachine').checked;
    const hasBank = document.getElementById('wizMuafEticaretBank').checked;
    const amt = parseFloat(document.getElementById('wizMuafEticaretAmt').value) || 0;

    if (!isHome || !noMachine) {
      showMuafResult(
        'bi-x-circle-fill text-danger',
        'Esnaf Muaflığı Kapsamı Dışındasınız',
        'Ayrı bir iş yeri açanlar, sanayi tipi makine kullananlar veya dışarıdan hazır alıp satanlar esnaf muaflığından yararlanamaz.',
        'Ticari işletme mükellefiyeti tesis ettirmeli ve fatura kesmelisiniz. Yıllık beyanname zorunludur.'
      );
    } else if (!hasBank) {
      showMuafResult(
        'bi-x-circle-fill text-danger',
        'Banka Hesabı Açılması Zorunludur',
        'Evde internetten ürün satışlarında muafiyetin en temel yasal şartı bankada ticari hesap açılmasıdır.',
        'Türkiye\'de kurulu bir bankada hesap açıp vergi dairesine bildirmelisiniz. Aksi takdirde muafiyet hakkınız kaybolur.'
      );
    } else if (amt <= 1900000) {
      showMuafResult(
        'bi-check-circle-fill text-success',
        'Vergiden Muaf Esnaf Kapsamındasınız',
        `Yıllık hasılatınız (${amt.toLocaleString('tr-TR')} TL), 2026 yılı yasal tavanı olan 1.900.000 TL sınırının altındadır.`,
        'Banka hesabınıza gelen hasılat üzerinden banka tarafından <strong>%4 stopaj</strong> kesilir (En az 1 işçi çalıştırıyorsanız stopaj <strong>%2</strong> olarak uygulanır). Yıllık beyanname vermezsiniz.'
      );
    } else {
      showMuafResult(
        'bi-info-circle-fill text-warning',
        'Hasılat Limiti Aşılmış',
        `Yıllık hasılatınız (${amt.toLocaleString('tr-TR')} TL), 2026 yılı tavanı olan 1.900.000 TL sınırını aşmıştır.`,
        'Gelecek yıl başından itibaren esnaf muaflığınız sona erer. Gerçek usulde ticari kazanç mükellefi olmanız gerekir.'
      );
    }
  }

  function evaluateMuafGunes() {
    const kw = parseFloat(document.getElementById('wizMuafGunesKw').value) || 0;
    if (kw <= 0) {
      alert('Lütfen kurulu güç değerini girin.');
      return;
    }
    if (kw <= 50) {
      showMuafResult(
        'bi-sun-fill text-warning',
        'Yenilenebilir Enerji Esnaf Muaflığı',
        `Kurulu gücünüz (${kw} kW), yasal 50 kW sınırının altındadır. Dağıtım şirketlerine satılan fazla elektrik geliriniz vergiden muaftır.`,
        'Herhangi bir beyanname vermezsiniz ve vergi ödemezsiniz (GVK Madde 9/9).'
      );
    } else {
      showMuafResult(
        'bi-info-circle-fill text-danger',
        'Muafiyet Sınırı Aşılmıştır (Kurulu Güç)',
        `Kurulu gücünüz (${kw} kW), yasal 50 kW sınırını aşmaktadır. Bu durum esnaf muaflığı dışındadır.`,
        'Genel hükümlere göre ticari işletme kaydı açtırarak gelir vergisi beyannamesi vermeniz gerekir.'
      );
    }
  }

  function evaluateMuafGezici() {
    const noShop = document.getElementById('wizMuafGeziciNoShop').checked;
    const isSelf = document.getElementById('wizMuafGeziciSelf').checked;

    if (noShop && isSelf) {
      showMuafResult(
        'bi-check-circle-fill text-success',
        'Gezici Esnaf Muaflığı Kapsamındasınız',
        'Sabit bir dükkan açmadan kendi emeğinizle gezici olarak perakende zanaat işleri yapıyorsunuz.',
        'GVK Madde 9/1 uyarınca gelir vergisinden muafsınız. Yıllık beyanname vermenize gerek yoktur.'
      );
    } else {
      showMuafResult(
        'bi-x-circle-fill text-danger',
        'Esnaf Muaflığı Kriterleri Uyuşmuyor',
        'Sabit dükkanı olanlar veya yanlarında sürekli eleman çalıştıranlar GVK Madde 9 küçük esnaf muaflığından yararlanamaz.',
        'Gerçek usulde gelir vergisi mükellefi olarak beyanname vermeniz zorunludur.'
      );
    }
  }

  // ── BEYAN & TARİFE SİHİRBAZI LOGIC ──
  let beyanType = '';
  function selectBeyanType(type) {
    beyanType = type;
    document.querySelectorAll('.wizard-step-beyan').forEach(el => el.classList.add('d-none'));
    
    const title = document.getElementById('wizBeyanStep2Title');
    const label = document.getElementById('wizBeyanStep2Label');
    const help = document.getElementById('wizBeyanStep2Help');
    const extra = document.getElementById('wizBeyanExtraFields');
    
    extra.classList.add('d-none');
    
    if (type === 'kira') {
      title.textContent = 'Kira Geliri Bilgisi';
      label.textContent = 'Yıllık Toplam Brüt Kira Geliriniz (TL):';
      help.textContent = `${AKTIF_YIL} yılı mesken kira istisna limiti ${params.kiraIstisnasi.toLocaleString('tr-TR')} TL\'dir. İş yeri kiralarında stopaj kesintisi uygulanır.`;
    } else if (type === 'telif') {
      title.textContent = 'Telif Kazanç Bilgisi';
      label.textContent = 'Yıllık Toplam Telif Hasılatınız (TL):';
      help.textContent = `GVK Madde 18 kapsamında tescilli telif gelirlerinde ${AKTIF_YIL} yılı beyanname sınırı ${params.telifLimit.toLocaleString('tr-TR')} TL\'dir.`;
    } else if (type === 'ucret_tek') {
      title.textContent = 'Tek İşverenden Ücret Geliri';
      label.textContent = 'Yıllık Toplam Brüt Ücretiniz (TL):';
      help.textContent = `Tek işverenden alınan tevkifatlı ücretlerde ${AKTIF_YIL} yılı beyan sınırı ${params.ucretToplamLimit.toLocaleString('tr-TR')} TL\'dir.`;
    } else if (type === 'ucret_cok') {
      title.textContent = 'Çoklu İşverenden Ücret Geliri';
      label.textContent = 'En Yüksek Ücret Aldığınız (Birinci) İşverenden Brüt Ücretiniz (TL):';
      help.textContent = `GVK Madde 86/1-b uyarınca, 2. işverenden alınan ücretlerin toplamı ${params.ucretCokluLimit.toLocaleString('tr-TR')} TL\'yi veya toplam brüt ücret ${params.ucretToplamLimit.toLocaleString('tr-TR')} TL\'yi aşarsa beyanname zorunludur.`;
      extra.classList.remove('d-none');
    } else if (type === 'deger_artisi') {
      title.textContent = 'Değer Artış Kazancı';
      label.textContent = 'Gayrimenkul/Hisse Satışından Doğan Net Kârınız (TL):';
      help.textContent = `${AKTIF_YIL} yılı değer artış kazancı istisna limiti ${params.degerArtisiLimit.toLocaleString('tr-TR')} TL\'dir. 5 yıldan fazla elde tutulan gayrimenkul satışı muaftır.`;
    } else if (type === 'arizi') {
      title.textContent = 'Arızi Kazanç Bilgisi';
      label.textContent = 'Süreklilik Arz Etmeyen Kazancınız (TL):';
      help.textContent = `${AKTIF_YIL} yılı arızi kazanç istisna limiti ${params.ariziKazancLimit.toLocaleString('tr-TR')} TL\'dir.`;
    }
    
    document.getElementById('wiz-beyan-step-2').classList.remove('d-none');
  }

  function beyanGoBack(reset = 0) {
    document.querySelectorAll('.wizard-step-beyan').forEach(el => el.classList.add('d-none'));
    if (reset) {
      document.getElementById('wizBeyanAmt').value = '';
      document.getElementById('wizBeyanAmt2').value = '';
      document.getElementById('wiz-beyan-step-1').classList.remove('d-none');
    } else {
      document.getElementById('wiz-beyan-step-1').classList.remove('d-none');
    }
  }

  function calculateGvProgressive(amount) {
    const p = VERGI_PARAMETRELERI[AKTIF_YIL];
    let tax = 0;
    if (amount <= p.dilimler[0]) {
      tax = amount * p.oranlar[0];
    } else if (amount <= p.dilimler[1]) {
      tax = p.kumuplatifMatrahlar[0] + (amount - p.dilimler[0]) * p.oranlar[1];
    } else if (amount <= p.dilimler[2]) {
      tax = p.kumuplatifMatrahlar[1] + (amount - p.dilimler[1]) * p.oranlar[2];
    } else if (amount <= p.dilimler[3]) {
      tax = p.kumuplatifMatrahlar[2] + (amount - p.dilimler[2]) * p.oranlar[3];
    } else {
      tax = p.kumuplatifMatrahlar[3] + (amount - p.dilimler[3]) * p.oranlar[4];
    }
    return Math.round(tax);
  }

  function showBeyanResult(iconClass, title, desc, statusText, taxText, advice) {
    document.querySelectorAll('.wizard-step-beyan').forEach(el => el.classList.add('d-none'));
    const resultIcon = document.getElementById('wizBeyanResultIcon');
    resultIcon.className = 'wizard-result-icon mx-auto mb-4 ' + iconClass;
    document.getElementById('wizBeyanResultTitle').textContent = title;
    document.getElementById('wizBeyanResultDesc').innerHTML = desc;
    document.getElementById('wizBeyanResultStatus').innerHTML = statusText;
    document.getElementById('wizBeyanResultTax').innerHTML = taxText;
    document.getElementById('wizBeyanResultAdvice').innerHTML = advice;
    document.getElementById('wiz-beyan-result').classList.remove('d-none');
  }

  function evaluateBeyanVergi() {
    const amt1 = parseFloat(document.getElementById('wizBeyanAmt').value) || 0;
    const amt2 = parseFloat(document.getElementById('wizBeyanAmt2').value) || 0;

    if (amt1 <= 0 && beyanType !== 'ucret_cok') {
      alert('Lütfen geçerli bir kazanç tutarı girin.');
      return;
    }

    if (beyanType === 'kira') {
      const istisna = 58000;
      if (amt1 <= istisna) {
        showBeyanResult(
          'bi-check-circle-fill text-success',
          'Beyanname Verilmez',
          `Kira geliriniz (${amt1.toLocaleString('tr-TR')} TL), 2026 yılı mesken kira istisnası olan 58.000 TL sınırının altındadır.`,
          '<strong>Beyanname Verilmez.</strong> (İstisna sınırının altındaki konut kira gelirleri için yıllık beyanname verilmez.)',
          '<strong>0 TL</strong>',
          'GVK Madde 21 kapsamında herhangi bir gelir vergisi beyannamesi veya vergi yükümlülüğünüz yoktur.'
        );
      } else {
        const taxable = amt1 - istisna;
        const tax = calculateGvProgressive(taxable);
        showBeyanResult(
          'bi-info-circle-fill text-warning',
          'Beyanname Verilmesi Zorunludur',
          `Kira geliriniz (${amt1.toLocaleString('tr-TR')} TL), 2026 yılı mesken kira istisnası olan 58.000 TL sınırını aşmıştır.`,
          '<strong>Beyanname Verilir.</strong> (58.000 TL istisna düşülerek kalan kısım beyan edilir.)',
          `<strong>${tax.toLocaleString('tr-TR')} TL</strong> (Tahmini, istisna düşülmüş matrah üzerinden hesaplanan)`,
          `GVK Madde 21 uyarınca 58.000 TL istisna düşüldükten sonra kalan <strong>${taxable.toLocaleString('tr-TR')} TL</strong> matrah üzerinden vergi tarifesine göre gelir vergisi hesaplanır.`
        );
      }
    } else if (beyanType === 'telif') {
      const limit = 5300000;
      if (amt1 <= limit) {
        const stopaj = amt1 * 0.17;
        showBeyanResult(
          'bi-check-circle-fill text-success',
          'Beyanname Verilmez (Stopaj Nihai Vergidir)',
          `Telif geliriniz (${amt1.toLocaleString('tr-TR')} TL), 2026 yılı beyanname sınırı olan 5.300.000 TL limitinin altındadır.`,
          '<strong>Beyanname Verilmez.</strong> (GVK Md. 18 uyarınca, sınır altı telif gelirleri beyannameye dahil edilmez.)',
          `<strong>${stopaj.toLocaleString('tr-TR')} TL</strong> (%17 Stopaj kesintisi olarak ödenmiştir)`,
          'Ödemeyi yapanların kestiği %17 stopaj nihai vergilendirmenizdir. Yıllık beyanname verme yükümlülüğünüz yoktur.'
        );
      } else {
        const tax = calculateGvProgressive(amt1);
        const stopaj = amt1 * 0.17;
        const netTax = Math.max(0, tax - stopaj);
        showBeyanResult(
          'bi-info-circle-fill text-warning',
          'Beyanname Verilmesi Zorunludur',
          `Telif geliriniz (${amt1.toLocaleString('tr-TR')} TL), 2026 yılı beyanname sınırı olan 5.300.000 TL limitini aşmıştır.`,
          '<strong>Beyanname Verilir.</strong> (Telif kazancının tamamı yıllık beyannameye dahil edilmek zorundadır.)',
          `<strong>${netTax.toLocaleString('tr-TR')} TL</strong> (Hesaplanan: ${tax.toLocaleString('tr-TR')} TL, Kesilen Stopaj: ${stopaj.toLocaleString('tr-TR')} TL)`,
          `GVK Madde 18 uyarınca 5.300.000 TL limit aşımında gelir beyan edilir ve yıl içinde kesilen %17 vergilendirici stopaj mahsup edilir.`
        );
      }
    } else if (beyanType === 'ucret_tek') {
      const limit = 5300000;
      if (amt1 <= limit) {
        showBeyanResult(
          'bi-check-circle-fill text-success',
          'Beyanname Verilmez',
          `Maaş geliriniz (${amt1.toLocaleString('tr-TR')} TL), 2026 yılı beyanname sınırı olan 5.300.000 TL limitinin altındadır.`,
          '<strong>Beyanname Verilmez.</strong> (Tek işverenden tevkifatlı alınan ve limiti aşmayan ücretler için beyanname verilmez.)',
          '<strong>0 TL</strong> (Yıl içinde işveren tarafından stopaj olarak kesilmiştir)',
          'GVK Madde 86/1-b uyarınca tek işverenden alınan tevkifatlı ücret gelirleri 5.300.000 TL sınırını aşmadıkça beyannameye tabi değildir.'
        );
      } else {
        const tax = calculateGvProgressive(amt1);
        showBeyanResult(
          'bi-info-circle-fill text-warning',
          'Beyanname Verilmesi Zorunludur',
          `Maaş geliriniz (${amt1.toLocaleString('tr-TR')} TL), 2026 yılı beyanname sınırı olan 5.300.000 TL limitini aşmıştır.`,
          '<strong>Beyanname Verilir.</strong> (Ücretin tamamı beyan edilerek tarife uygulanır.)',
          `<strong>Beyannamede Hesaplanır</strong> (İşverence yıl içinde kesilen stopajlar beyannamede hesaplanan vergiden düşülür)`,
          'GVK Madde 86/1-b uyarınca tek işverenden de alınsa 5.300.000 TL sınırını aşan ücretler için beyanname verilir.'
        );
      }
    } else if (beyanType === 'ucret_cok') {
      const limit1 = 190000;
      const limitTotal = 5300000;
      const total = amt1 + amt2;

      if (amt2 > limit1 || total > limitTotal) {
        showBeyanResult(
          'bi-info-circle-fill text-danger',
          'Beyanname Verilmesi Zorunludur',
          `Birinci işveren harici ücretleriniz (${amt2.toLocaleString('tr-TR')} TL), 190.000 TL sınırını aşmıştır veya toplam ücretiniz (${total.toLocaleString('tr-TR')} TL) 5.300.000 TL sınırını aşmıştır.`,
          '<strong>Beyanname Verilir.</strong> (GVK Md. 86/1-b uyarınca iki işverenden alınan ücretler beyan edilmelidir.)',
          '<strong>Beyannamede Hesaplanır</strong> (Yıl içinde kesilen tüm stopajlar hesaplanan vergiden düşülür)',
          'Birinciden sonraki işverenden alınan ücretlerin toplamı 190.000 TL sınırını aştığından veya toplam ücret 5.300.000 TL\'yi geçtiğinden beyanname zorunludur.'
        );
      } else {
        showBeyanResult(
          'bi-check-circle-fill text-success',
          'Beyanname Verilmez',
          `Birinci işveren harici ücretleriniz (${amt2.toLocaleString('tr-TR')} TL) 190.000 TL sınırının altında ve toplam ücretiniz (${total.toLocaleString('tr-TR')} TL) 5.300.000 TL sınırını aşmamaktadır.`,
          '<strong>Beyanname Verilmez.</strong> (İkinci işverenden alınan tevkifatlı ücret sınırı aşmadığı için beyanname gerekmez.)',
          '<strong>0 TL</strong>',
          'GVK Madde 86/1-b kapsamında tevkif suretiyle vergilendirilmiş ücretlerin beyannameye dahil edilmesine gerek yoktur.'
        );
      }
    } else if (beyanType === 'deger_artisi') {
      const istisna = 150000;
      if (amt1 <= istisna) {
        showBeyanResult(
          'bi-check-circle-fill text-success',
          'Beyanname Verilmez',
          `Değer artış kazancınız (${amt1.toLocaleString('tr-TR')} TL), 2026 yılı istisnası olan 150.000 TL sınırının altındadır.`,
          '<strong>Beyanname Verilmez.</strong> (İstisna sınırının altındaki değer artış kazançları beyan edilmez.)',
          '<strong>0 TL</strong>',
          'GVK Mükerrer Madde 80 kapsamında herhangi bir gelir vergisi beyanname zorunluluğunuz bulunmamaktadır.'
        );
      } else {
        const taxable = amt1 - istisna;
        const tax = calculateGvProgressive(taxable);
        showBeyanResult(
          'bi-info-circle-fill text-warning',
          'Beyanname Verilmesi Zorunludur',
          `Değer artış kazancınız (${amt1.toLocaleString('tr-TR')} TL), 2026 yılı istisnası olan 150.000 TL sınırını aşmıştır.`,
          '<strong>Beyanname Verilir.</strong> (İstisna düşülerek kalan kısım beyan edilir.)',
          `<strong>${tax.toLocaleString('tr-TR')} TL</strong> (İstisna düşülmüş matrah üzerinden hesaplanan)`,
          `GVK Mükerrer Madde 80 uyarınca 150.000 TL istisna düşüldükten sonra kalan <strong>${taxable.toLocaleString('tr-TR')} TL</strong> matrah üzerinden gelir vergisi hesaplanır.`
        );
      }
    } else if (beyanType === 'arizi') {
      const istisna = 350000;
      if (amt1 <= istisna) {
        showBeyanResult(
          'bi-check-circle-fill text-success',
          'Beyanname Verilmez',
          `Arızi kazancınız (${amt1.toLocaleString('tr-TR')} TL), 2026 yılı istisnası olan 350.000 TL sınırının altındadır.`,
          '<strong>Beyanname Verilmez.</strong> (İstisna sınırının altındaki arızi kazançlar beyan edilmez.)',
          '<strong>0 TL</strong>',
          'GVK Madde 82 kapsamında herhangi bir gelir vergisi beyanname zorunluluğunuz bulunmamaktadır.'
        );
      } else {
        const taxable = amt1 - istisna;
        const tax = calculateGvProgressive(taxable);
        showBeyanResult(
          'bi-info-circle-fill text-warning',
          'Beyanname Verilmesi Zorunludur',
          `Arızi kazancınız (${amt1.toLocaleString('tr-TR')} TL), 2026 yılı istisnası olan 350.000 TL sınırını aşmıştır.`,
          '<strong>Beyanname Verilir.</strong> (İstisna düşülerek kalan kısım beyan edilir.)',
          `<strong>${tax.toLocaleString('tr-TR')} TL</strong> (İstisna düşülmüş matrah üzerinden hesaplanan)`,
          `GVK Madde 82 uyarınca 350.000 TL istisna düşüldükten sonra kalan <strong>${taxable.toLocaleString('tr-TR')} TL</strong> matrah üzerinden gelir vergisi hesaplanır.`
        );
      }
    }
  }

  // İlk yüklemede toplam kalem sayısını göster
  document.addEventListener('DOMContentLoaded', () => {
    filterItems();
  });
