document.addEventListener("DOMContentLoaded", () => {
    const T = window.TesvikTools;
    const activity = document.getElementById("teknoFaaliyet");

    const updateConditionalFields = () => {
        const mode = activity.value;
        document.getElementById("serialField").classList.toggle("hidden", mode !== "seri");
        document.getElementById("qualifiedField").classList.toggle("hidden", mode !== "ip");
        document.getElementById("totalSpendField").classList.toggle("hidden", mode !== "ip");
        if (mode !== "normal") document.getElementById("teknoAdvanced").open = true;
    };

    const calculate = () => {
        const totalIncome = T.get("teknoGelir");
        const excludedIncome = Math.min(totalIncome, T.get("teknoKapsamDisi"));
        const eligibleIncome = Math.max(0, totalIncome - excludedIncome);
        const profit = Math.max(0, eligibleIncome - T.get("teknoDogrudanGider") - T.get("teknoOrtakGider"));
        const mode = activity.value;
        let exemptionRatio = 1;

        if (mode === "seri") {
            exemptionRatio = Math.min(1, Math.max(0, T.get("teknoIpPayi") / 100));
        } else if (mode === "ip") {
            const qualified = T.get("teknoNitelikli");
            const totalSpend = T.get("teknoToplamHarcama");
            exemptionRatio = totalSpend > 0 ? Math.min(1, (qualified * 1.30) / totalSpend) : 0;
        }

        const exemption = profit * exemptionRatio;
        const taxBenefit = exemption * Math.max(0, T.get("teknoKvOrani")) / 100;
        const obligationApplies = exemption >= 5000000;
        const investmentObligation = obligationApplies ? Math.min(exemption * 0.03, 100000000) : 0;

        T.text("teknoUygunGelir", T.money(eligibleIncome));
        T.text("teknoFaaliyetKazanci", T.money(profit));
        T.text("teknoIstisnaOrani", T.percent(exemptionRatio * 100));
        T.text("teknoIstisna", T.money(exemption));
        T.text("teknoVergiAvantaji", T.money(taxBenefit));
        T.text("teknoYatirimYuk", obligationApplies ? T.money(investmentObligation) : "Doğmaz");

        const note = document.getElementById("teknoLimitNote");
        note.classList.toggle("hidden", !obligationApplies);
        if (obligationApplies) {
            note.textContent = "Yıllık beyannamede yararlanılan istisna 5.000.000 TL sınırına ulaştığı için %3 girişim sermayesi yatırım yükümlülüğü doğar. Yıllık yükümlülük 100.000.000 TL ile sınırlıdır.";
        }

        const baseUrl = document.getElementById("teknoAsgariLink").getAttribute("href").split("?")[0];
        document.getElementById("teknoAsgariLink").href = `${baseUrl}?teknopark=${encodeURIComponent(exemption.toFixed(2))}`;
    };

    activity.addEventListener("change", () => { updateConditionalFields(); calculate(); });
    document.querySelectorAll("input, select").forEach((el) => el.addEventListener("input", calculate));
    T.bindMoneyInputs(calculate);
    T.initTabs();

    document.querySelectorAll("[data-tekno-example]").forEach((button) => {
        button.addEventListener("click", () => {
            const type = button.dataset.teknoExample;
            if (type === "basic") {
                activity.value = "normal";
                T.set("teknoGelir", 5000000); T.set("teknoKapsamDisi", 0); T.set("teknoDogrudanGider", 1600000); T.set("teknoOrtakGider", 400000);
            } else if (type === "serial") {
                activity.value = "seri";
                T.set("teknoGelir", 12000000); T.set("teknoKapsamDisi", 0); T.set("teknoDogrudanGider", 5000000); T.set("teknoOrtakGider", 1000000);
                document.getElementById("teknoIpPayi").value = 35;
            } else {
                activity.value = "ip";
                T.set("teknoGelir", 8000000); T.set("teknoKapsamDisi", 0); T.set("teknoDogrudanGider", 1000000); T.set("teknoOrtakGider", 0);
                T.set("teknoNitelikli", 105000); T.set("teknoToplamHarcama", 150000);
            }
            updateConditionalFields(); calculate();
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    });

    updateConditionalFields();
    calculate();
});
