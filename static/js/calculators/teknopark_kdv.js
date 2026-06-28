document.addEventListener("DOMContentLoaded", () => {
    const T = window.TesvikTools;
    const field = (id) => document.getElementById(id);

    const calculate = () => {
        const blockers = [];
        const reviews = [];
        const region = field("tkdvBolge").value;
        const income = field("tkdvKazanc").value;
        const production = field("tkdvUretim").value;
        const software = field("tkdvYazilim").value;
        const transaction = field("tkdvIslem").value;

        if (region === "hayir") blockers.push("Satıcının teknoloji geliştirme bölgesinde girişimci olmaması");
        if (income === "hayir") blockers.push("Faaliyetin kazanç istisnası kapsamında olmaması");
        if (production === "hayir") blockers.push("Yazılımın bölge dışında üretilmesi");
        if (["bakim", "donanim", "reklam"].includes(transaction)) blockers.push("Seçilen işlemin yazılım teslimi niteliğinde olmaması");

        if (region === "belirsiz") reviews.push("girişimci statüsü");
        if (income === "belirsiz") reviews.push("kazanç istisnası kaydı");
        if (["karma", "belirsiz"].includes(production)) reviews.push("üretim yerinin ayrıştırılması");
        if (software === "diger") reviews.push("yazılım türünün kanundaki listeyle uyumu");
        if (transaction === "karma") reviews.push("sözleşme bedelinin yazılım, donanım ve hizmet olarak ayrıştırılması");

        let status = "İstisnaya uygun görünüyor";
        let code = "223";
        let tax = "Hesaplanmaz";
        let explanation = "Temel şartlar sağlanıyor. İşlemin KDV beyannamesinde 223 koduyla gösterilmesi değerlendirilebilir.";
        let resultClass = "eligible";

        if (blockers.length) {
            status = "İstisna uygulanmaz";
            code = "Uygulanmaz";
            tax = "Hesaplanır";
            explanation = `${blockers.join("; ")} nedeniyle seçilen işlem istisna kapsamında görünmüyor.`;
            resultClass = "ineligible";
        } else if (reviews.length) {
            status = "Ayrıntılı kontrol gerekli";
            code = "Kontrol sonrası";
            tax = "Sonuca göre";
            explanation = `Şu konular netleştirilmelidir: ${reviews.join(", ")}.`;
            resultClass = "review";
        }

        T.text("tkdvStatus", status);
        T.text("tkdvCode", code);
        T.text("tkdvTax", tax);
        T.text("tkdvExplanation", explanation);
        field("tkdvResultBox").dataset.status = resultClass;
    };

    document.querySelectorAll("select").forEach((element) => element.addEventListener("change", calculate));
    T.initTabs();

    document.querySelectorAll("[data-tkdv-example]").forEach((button) => button.addEventListener("click", () => {
        const example = button.dataset.tkdvExample;
        field("tkdvBolge").value = "evet";
        field("tkdvKazanc").value = "evet";
        field("tkdvUretim").value = "evet";
        field("tkdvYazilim").selectedIndex = 2;
        field("tkdvIslem").value = example === "maintenance" ? "bakim" : example === "mixed" ? "karma" : "teslim";
        calculate();
        window.scrollTo({ top: 0, behavior: "smooth" });
    }));

    calculate();
});
