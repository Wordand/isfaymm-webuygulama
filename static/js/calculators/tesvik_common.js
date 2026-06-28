window.TesvikTools = (() => {
    const number = (value) => {
        if (typeof value === "number") return Number.isFinite(value) ? value : 0;
        const clean = String(value || "").replace(/\s/g, "").replace(/\./g, "").replace(",", ".").replace(/[^0-9.-]/g, "");
        const parsed = Number(clean);
        return Number.isFinite(parsed) ? parsed : 0;
    };

    const money = (value) => new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: "TRY",
        minimumFractionDigits: 2
    }).format(Number(value) || 0);

    const percent = (value) => `%${new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(Number(value) || 0)}`;

    const get = (id) => number(document.getElementById(id)?.value);
    const set = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.value = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(value || 0);
    };
    const text = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };

    const bindMoneyInputs = (calculate) => {
        document.querySelectorAll("[data-money]").forEach((input) => {
            input.addEventListener("focus", () => {
                const value = number(input.value);
                input.value = value ? String(value).replace(".", ",") : "";
            });
            input.addEventListener("blur", () => {
                input.value = new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(number(input.value));
            });
            input.addEventListener("input", calculate);
            if (!input.value) input.value = "0,00";
        });
    };

    const initTabs = () => {
        document.querySelectorAll("[data-tab-button]").forEach((button) => {
            button.addEventListener("click", () => {
                const group = button.closest(".incentive-wrap") || document;
                group.querySelectorAll("[data-tab-button]").forEach((item) => item.classList.remove("active"));
                group.querySelectorAll("[data-tab-panel]").forEach((item) => item.classList.add("hidden"));
                button.classList.add("active");
                group.querySelector(`[data-tab-panel="${button.dataset.tabButton}"]`)?.classList.remove("hidden");
            });
        });
    };

    return { number, money, percent, get, set, text, bindMoneyInputs, initTabs };
})();
