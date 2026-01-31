function hesaplaIthalatKdv() {

    const cif = parseFloat(document.getElementById("cif").value) || 0;
    const gumruk = parseFloat(document.getElementById("gumruk").value) || 0;

    const gvOran = parseFloat(document.getElementById("gv").value) / 100 || 0;
    const igvOran = parseFloat(document.getElementById("igv").value) / 100 || 0;
    const kdvOran = parseFloat(document.getElementById("kdv").value) / 100 || 0;

    if (gumruk < cif) {
        Swal.fire({
            icon: "error",
            title: "Hatalı Giriş",
            text: "Toplam gümrük kıymeti CIF bedelinden küçük olamaz.",
        });
        return;
    }

    // 🔴 Gözetim farkı (tevsik edilemeyen tutar)
    const gozetimFarki = gumruk - cif;

    // Vergiler
    const gvYurtDisi = gozetimFarki * gvOran;
    const igvYurtDisi = gozetimFarki * igvOran;

    const gvCif = cif * gvOran;
    const igvCif = cif * igvOran;

    // ❌ İndirilemeyecek KDV
    const indirilemezMatrah = gozetimFarki + gvYurtDisi + igvYurtDisi;
    const indirilemezKdv = indirilemezMatrah * kdvOran;

    // ✅ İndirilebilecek KDV
    const indirilebilirMatrah = cif + gvCif + igvCif;
    const indirilebilirKdv = indirilebilirMatrah * kdvOran;

    // Sonuçlar
    document.getElementById("indirilebilirKdv").innerText =
        indirilebilirKdv.toLocaleString("tr-TR", { minimumFractionDigits: 2 });

    document.getElementById("indirilemezKdv").innerText =
        indirilemezKdv.toLocaleString("tr-TR", { minimumFractionDigits: 2 });

    document.getElementById("sonuc").classList.remove("d-none");

    // 🔍 Detay
    document.getElementById("gzetimFarki").innerText = gozetimFarki.toLocaleString("tr-TR", { minimumFractionDigits: 2 });
    document.getElementById("gvYurtDisi").innerText = gvYurtDisi.toLocaleString("tr-TR", { minimumFractionDigits: 2 });
    document.getElementById("igvYurtDisi").innerText = igvYurtDisi.toLocaleString("tr-TR", { minimumFractionDigits: 2 });
    document.getElementById("indirilemezMatrah").innerText = indirilemezMatrah.toLocaleString("tr-TR", { minimumFractionDigits: 2 });

    document.getElementById("detay").classList.remove("d-none");

    // ⚠️ MEVZUAT UYARISI – 46 No.lu Tebliğ 3/1-a
    const YMM_SINIR = 2600000; // bu değeri ileride config’ten de çekebiliriz
    const uyarıEl = document.getElementById("ymmUyari");
    uyarıEl.classList.add("d-none");
    uyarıEl.innerText = "";

    if (gumruk > YMM_SINIR) {
        uyarıEl.innerHTML =
            "⚠️ <strong>İthalat bedeli</strong>, 46 Sıra No.lu SMMM ve YMM Kanunu Genel Tebliği 3/1-a kapsamında belirlenen sınırı aştığından, " +
            "<strong>Özel Amaçlı YMM Raporu</strong> ibraz edilmesi gerekir. " +
            "Ancak ithalatın yapıldığı yıl için süresinde düzenlenmiş <strong>Tam Tasdik Sözleşmesi</strong> bulunması halinde ayrıca rapor aranmaz.";
        uyarıEl.classList.remove("d-none");
    } else {
        uyarıEl.innerHTML =
            "ℹ️ İthalat bedeli sınırın altında olduğundan, bu işleme ilişkin KDV’nin doğru indirim konusu yapılıp yapılmadığı " +
            "<strong>altışar aylık dönemleri izleyen ayın sonuna kadar vergi dairesine bildirilecektir</strong>.";
        uyarıEl.classList.remove("d-none");
    }
}
