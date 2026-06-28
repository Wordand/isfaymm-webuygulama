document.addEventListener("DOMContentLoaded", () => {
    const T = window.TesvikTools;

    const calculate = () => {
        const internalSpend = T.get("argeMalzeme") + T.get("argePersonel") + T.get("argeAmortisman") + T.get("argeGenel") + T.get("argeVergi");
        const externalDeclared = T.get("argeDisHizmet");
        const externalAllowed = Math.min(externalDeclared, internalSpend);
        const grant = T.get("argeHibe");
        const eligibleCurrent = Math.max(0, internalSpend + externalAllowed - grant);

        const carried = T.get("argeDevreden");
        const indexedCarry = carried * (1 + Math.max(0, T.get("argeYdo")) / 100);
        const priorSpend = T.get("argeOncekiHarcama");
        const additional = document.getElementById("argeIlaveKosul").value === "evet"
            ? Math.max(0, eligibleCurrent - priorSpend) * 0.50
            : 0;
        const totalAvailable = eligibleCurrent + indexedCarry + additional;
        const income = T.get("argeKazanc");
        const used = Math.min(totalAvailable, income);
        const newCarry = Math.max(0, totalAvailable - used);

        const obligationApplies = used >= 5000000;
        const investmentObligation = obligationApplies ? Math.min(used * 0.03, 100000000) : 0;

        T.text("argeUygunHarcama", T.money(eligibleCurrent));
        T.text("argeDisHizmetUygun", T.money(externalAllowed));
        T.text("argeEndeksli", T.money(indexedCarry));
        T.text("argeIlave", T.money(additional));
        T.text("argeToplam", T.money(totalAvailable));
        T.text("argeKullanilan", T.money(used));
        T.text("argeYeniDevreden", T.money(newCarry));
        T.text("argeYatirimYuk", obligationApplies ? T.money(investmentObligation) : "Doğmaz");

        const note = document.getElementById("argeLimitNote");
        const notes = [];
        if (externalDeclared > externalAllowed) notes.push(`Dış hizmetin ${T.money(externalDeclared - externalAllowed)} tutarındaki kısmı %50 sınırı nedeniyle hesaba alınmadı.`);
        if (obligationApplies) notes.push("Yıllık beyannamede kullanılan indirim 5.000.000 TL sınırına ulaştığı için %3 girişim sermayesi yatırım yükümlülüğü doğar.");
        note.classList.toggle("hidden", notes.length === 0);
        note.textContent = notes.join(" ");

        const baseUrl = document.getElementById("argeAsgariLink").getAttribute("href").split("?")[0];
        document.getElementById("argeAsgariLink").href = `${baseUrl}?arge=${encodeURIComponent(used.toFixed(2))}`;
    };

    document.querySelectorAll("input, select").forEach((el) => el.addEventListener("input", calculate));
    T.bindMoneyInputs(calculate);
    T.initTabs();

    document.querySelectorAll("[data-arge-example]").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll("[data-money]").forEach((input) => T.set(input.id, 0));
            document.getElementById("argeYdo").value = 0;
            document.getElementById("argeIlaveKosul").value = "hayir";
            const type = button.dataset.argeExample;
            if (type === "basic") {
                T.set("argeMalzeme", 900000); T.set("argePersonel", 2200000); T.set("argeAmortisman", 400000); T.set("argeGenel", 250000); T.set("argeKazanc", 5000000);
            } else if (type === "service") {
                T.set("argePersonel", 1000000); T.set("argeDisHizmet", 1800000); T.set("argeKazanc", 3000000);
            } else {
                T.set("argeMalzeme", 1200000); T.set("argePersonel", 3800000); T.set("argeAmortisman", 500000); T.set("argeKazanc", 4000000);
                T.set("argeDevreden", 1000000); T.set("argeOncekiHarcama", 4000000);
                document.getElementById("argeYdo").value = 25;
                document.getElementById("argeIlaveKosul").value = "evet";
            }
            calculate();
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    });

    calculate();
});
