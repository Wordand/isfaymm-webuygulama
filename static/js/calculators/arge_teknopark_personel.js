document.addEventListener("DOMContentLoaded", () => {
    const T = window.TesvikTools;
    const rejim = document.getElementById("ptRejim");

    const calculate = () => {
        const isTechnopark = rejim.value === "4691";
        document.getElementById("ptNitelikWrap").classList.toggle("hidden", isTechnopark);
        const stopajRate = isTechnopark ? 1 : Number(document.getElementById("ptNitelik").value) / 100;
        const outsideRate = document.getElementById("ptMeslek").value === "bilisim" ? 1 : 0.75;
        const totalHours = Math.max(0, Number(document.getElementById("ptToplamSaat").value) || 0);
        const insideHours = Math.min(totalHours, Math.max(0, Number(document.getElementById("ptIceriSaat").value) || 0));
        const outsideHours = Math.max(0, Number(document.getElementById("ptDisariSaat").value) || 0);
        const eligibleOutside = Math.min(outsideHours, totalHours * outsideRate);
        const eligibleHours = Math.min(totalHours, insideHours + eligibleOutside);
        const workRate = totalHours > 0 ? eligibleHours / totalHours : 0;
        const ineligibleOutside = Math.max(0, outsideHours - eligibleOutside);
        const stopaj = T.get("ptGelirVergisi") * stopajRate * workRate;
        const sgk = T.get("ptSgk") * 0.50 * workRate;

        T.text("ptToplamTesvik", T.money(stopaj + sgk));
        T.text("ptCalismaOrani", T.percent(workRate * 100));
        T.text("ptStopajOrani", T.percent(stopajRate * 100));
        T.text("ptStopajTesviki", T.money(stopaj));
        T.text("ptSgkTesviki", T.money(sgk));
        T.text("ptDisSure", `${new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 1 }).format(ineligibleOutside)} saat`);

        const warnings = [];
        if (insideHours + outsideHours > totalHours) warnings.push("Girilen merkez içi ve dışı süre toplam çalışma süresini aşıyor; hesap toplam süreyle sınırlandı.");
        if (document.getElementById("ptPersonelTuru").value === "destek") {
            const argeCount = Number(document.getElementById("ptArgeSayisi").value) || 0;
            const supportCount = Number(document.getElementById("ptDestekSayisi").value) || 0;
            const companyTotal = argeCount + supportCount;
            const supportLimit = isTechnopark && companyTotal <= 15 ? 0.20 : 0.10;
            if (argeCount > 0 && supportCount > argeCount * supportLimit) warnings.push(`Destek personeli sayısı %${supportLimit * 100} sınırını aşıyor. Teşvik uygulanacak destek personeli işverence belirlenmelidir.`);
        }
        const warning = document.getElementById("ptWarning");
        warning.classList.toggle("hidden", warnings.length === 0);
        warning.textContent = warnings.join(" ");
    };

    document.querySelectorAll("input, select").forEach((el) => { el.addEventListener("input", calculate); el.addEventListener("change", calculate); });
    T.bindMoneyInputs(calculate); T.initTabs();
    document.querySelectorAll("[data-pt-example]").forEach((button) => button.addEventListener("click", () => {
        const type = button.dataset.ptExample;
        rejim.value = type;
        document.getElementById("ptNitelik").value = type === "5746" ? "80" : "95";
        document.getElementById("ptMeslek").value = type === "4691" ? "bilisim" : "diger";
        document.getElementById("ptPersonelTuru").value = "arge";
        T.set("ptGelirVergisi", 20000); T.set("ptSgk", 15000);
        document.getElementById("ptToplamSaat").value = 180;
        document.getElementById("ptIceriSaat").value = type === "4691" ? 0 : 45;
        document.getElementById("ptDisariSaat").value = type === "4691" ? 180 : 135;
        calculate(); window.scrollTo({ top: 0, behavior: "smooth" });
    }));
    calculate();
});
