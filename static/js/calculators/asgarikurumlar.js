document.addEventListener("DOMContentLoaded", () => {
    const T = window.TesvikTools;

    const deductionCatalog = [
        { id: "past_loss", label: "Geçmiş yıl zararları", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "participation", label: "İştirak kazançları istisnası (KVK 5/1-a)", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "emission", label: "Emisyon primi kazancı istisnası (KVK 5/1-ç)", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "fund_non_property", label: "Yatırım fonu/ortaklığı kazancı - taşınmaz dışı", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "risturn", label: "Risturn kazanç istisnası", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "sale_leaseback", label: "Sat-kirala-geri al kazanç istisnası", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "asset_lease", label: "Varlık kiralama kazanç istisnası", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "ship_registry", label: "Türk Uluslararası Gemi Sicili kazanç istisnası", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "free_zone", label: "Serbest bölge kazanç istisnası", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "technopark", label: "Teknopark kazanç istisnası (4691)", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "venture_fund", label: "Girişim sermayesi fonu indirimi", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "protected_workplace", label: "Korumalı işyeri indirimi", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "arge", label: "Ar-Ge ve tasarım indirimi (5746)", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "accounting_adjustment", label: "Matrahın doğru hesaplanmasına ilişkin düzeltme tutarı", effect: "deductible", group: "Asgari matrahtan düşülenler" },
        { id: "treaty_exemption", label: "Uluslararası anlaşma gereği Türkiye'de vergilenmeyen kazanç", effect: "deductible", group: "Asgari matrahtan düşülenler" },

        { id: "fund_property", label: "Yatırım fonu/ortaklığı taşınmaz kazancı", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "property_share_sale", label: "Taşınmaz, iştirak hissesi veya fon satış kazancı istisnası", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "bank_debt_transfer", label: "Bankaya/TMSF'ye borç nedeniyle devir kazancı istisnası", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "education", label: "Eğitim ve öğretim kazanç istisnası", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "foreign_fund", label: "Yabancı fon yönetici şirket kazanç istisnası", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "industrial_property", label: "Sınai mülkiyet hakları kazanç istisnası", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "kkm", label: "Kur korumalı mevduat kazanç istisnası", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "licensed_warehouse", label: "Ürün senedi kazanç istisnası", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "research_infrastructure", label: "Araştırma altyapısı kazanç istisnası", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "sponsorship", label: "Sponsorluk harcamaları indirimi", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "donation", label: "Bağış ve yardımlar indirimi", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "service_export", label: "Yurt dışına verilen hizmetlerden kazanç indirimi", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "cash_capital", label: "Nakdi sermaye artışı faiz indirimi", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "ifm", label: "İstanbul Finans Merkezi kazanç indirimi", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "investment_allowance", label: "Yatırım indirimi istisnası", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "technoventure", label: "Teknogirişim sermaye desteği indirimi", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },
        { id: "technokent_capital", label: "Teknokent sermaye desteği indirimi", effect: "nondeductible", group: "Asgari matrahtan düşülmeyenler" },

        { id: "foreign_participation", label: "Yurt dışı iştirak kazancı - vergi yükü hesabı", effect: "special", group: "Özel hesaplananlar" },
        { id: "foreign_share_sale", label: "Yurt dışı iştirak hissesi satış kazancı - vergi yükü hesabı", effect: "special", group: "Özel hesaplananlar" },
        { id: "foreign_branch", label: "Yurt dışı şube kazancı - vergi yükü hesabı", effect: "special", group: "Özel hesaplananlar" },
        { id: "foreign_construction", label: "Yurt dışı inşaat/onarım/teknik hizmet kazancı - vergi yükü hesabı", effect: "special", group: "Özel hesaplananlar" }
    ];

    const taxCreditCatalog = [
        { id: "export_credit", label: "İhracat kazancı oran indirimi nedeniyle alınmayan vergi" },
        { id: "production_credit", label: "Üretim kazancı oran indirimi nedeniyle alınmayan vergi" },
        { id: "ipo_credit", label: "Halka arz oran indirimi nedeniyle alınmayan vergi" },
        { id: "investment_credit", label: "2.8.2024 öncesi yatırım teşvik belgesine ait alınmayan vergi" },
        { id: "compliance_credit", label: "Vergiye uyumlu mükellef indirimi" }
    ];

    const examples = {
        1: { desc: "İndirim ve istisnası bulunmayan temel hesap.", profit: 1000000, kkeg: 200000, rows: [], credits: [] },
        2: { desc: "Ticari zarar KKEG nedeniyle pozitif kurum kazancına dönüşüyor.", profit: -1000000, kkeg: 1200000, rows: [], credits: [] },
        3: { desc: "İştirak, hisse satışı, Teknopark, Ar-Ge, nakdi sermaye ve geçmiş yıl zararı birlikte.", profit: 4000000, kkeg: 800000, rows: [
            ["participation", 2000000], ["property_share_sale", 800000], ["technopark", 500000], ["arge", 100000], ["cash_capital", 200000], ["past_loss", 400000]
        ], credits: [] },
        4: { desc: "Ar-Ge indirimi ve 2 Ağustos 2024 öncesi yatırım teşvik belgesi etkisi.", profit: 12500000, kkeg: 500000, rows: [
            ["bank_debt_transfer", 4000000], ["arge", 2000000], ["investment_allowance", 1000000]
        ], credits: [["investment_credit", 800000]] },
        5: { desc: "KKM istisnası, geçmiş yıl zararı ve yatırım teşvik belgesi birlikte.", profit: 15000000, kkeg: 0, rows: [
            ["kkm", 5000000], ["past_loss", 5000000]
        ], credits: [["investment_credit", 400000]] },
        6: { desc: "İhracat oran indirimi, serbest bölge, sınai mülkiyet ve nakdi sermaye indirimi.", profit: 10000000, kkeg: 1000000, rows: [
            ["free_zone", 1000000], ["industrial_property", 4000000], ["cash_capital", 2000000]
        ], credits: [["export_credit", 100000]] },
        7: { desc: "Yatırım fonu/ortaklığı kazancında taşınmaz gelirlerinin ayrıştırılması.", profit: 5000000, kkeg: 0, rows: [
            ["fund_non_property", 2000000], ["fund_property", 3000000]
        ], credits: [] },
        8: { desc: "Yurt dışı kazançlarda vergi yüküne göre asgari matrahtan düşülebilecek kısmın hesabı.", profit: 7000000, kkeg: 0, rows: [
            ["foreign_participation", 1000000, 1000000], ["foreign_construction", 800000, 500000], ["industrial_property", 4000000]
        ], credits: [] }
    };

    let selectedRows = [];
    let selectedCredits = [];
    let editingRow = null;
    let editingCredit = null;

    const itemById = (id) => deductionCatalog.find((item) => item.id === id);
    const creditById = (id) => taxCreditCatalog.find((item) => item.id === id);

    const fillSelects = () => {
        const select = document.getElementById("akvKalemSec");
        [...new Set(deductionCatalog.map((item) => item.group))].forEach((groupName) => {
            const group = document.createElement("optgroup");
            group.label = groupName;
            deductionCatalog.filter((item) => item.group === groupName).forEach((item) => {
                const option = document.createElement("option"); option.value = item.id; option.textContent = item.label; group.appendChild(option);
            });
            select.appendChild(group);
        });
        const creditSelect = document.getElementById("akvVergiKalemSec");
        taxCreditCatalog.forEach((item) => {
            const option = document.createElement("option"); option.value = item.id; option.textContent = item.label; creditSelect.appendChild(option);
        });
    };

    const effectMarkup = (row, item) => {
        if (item.effect === "deductible") return '<span class="effect-badge deductible">Düşülür</span>';
        if (item.effect === "nondeductible") return '<span class="effect-badge nondeductible">Düşülmez</span>';
        return `<span class="effect-badge special">${T.money(row.minimumAmount)} düşülür</span>`;
    };

    const renderRows = () => {
        const body = document.getElementById("akvKalemler");
        body.innerHTML = selectedRows.map((row, index) => {
            const item = itemById(row.id);
            return `<tr><td>${item.label}</td><td>${T.money(row.amount)}</td><td>${effectMarkup(row, item)}</td><td><div class="row-actions"><button type="button" data-edit-row="${index}" title="Düzenle"><i class="bi bi-pencil"></i></button><button type="button" data-remove-row="${index}" title="Sil"><i class="bi bi-trash"></i></button></div></td></tr>`;
        }).join("");
        document.getElementById("akvKalemBos").classList.toggle("hidden", selectedRows.length > 0);
    };

    const renderCredits = () => {
        const body = document.getElementById("akvVergiKalemler");
        body.innerHTML = selectedCredits.map((row, index) => {
            const item = creditById(row.id);
            return `<tr><td>${item.label}</td><td>${T.money(row.amount)}</td><td><span class="effect-badge deductible">Vergiden indirilir</span></td><td><div class="row-actions"><button type="button" data-edit-credit="${index}" title="Düzenle"><i class="bi bi-pencil"></i></button><button type="button" data-remove-credit="${index}" title="Sil"><i class="bi bi-trash"></i></button></div></td></tr>`;
        }).join("");
        document.getElementById("akvVergiKalemBos").classList.toggle("hidden", selectedCredits.length > 0);
    };

    const calculate = () => {
        const year = Number(document.getElementById("akvYil").value) || 2026;
        const startYear = Number(document.getElementById("akvKurulus").value) || 0;
        const firstThreePeriods = startYear > 0 && year >= startYear && year <= startYear + 2;
        const profitBeforeDeductions = T.get("akvTicariKar") + T.get("akvKkeg");
        const normalDeductions = selectedRows.reduce((sum, row) => sum + row.amount, 0);
        const minimumDeductions = selectedRows.reduce((sum, row) => {
            const effect = itemById(row.id).effect;
            return sum + (effect === "deductible" ? row.amount : effect === "special" ? row.minimumAmount : 0);
        }, 0);
        const taxCredits = selectedCredits.reduce((sum, row) => sum + row.amount, 0);
        const normalRate = Math.max(0, T.get("akvKvOrani")) / 100;
        const normalBase = Math.max(0, profitBeforeDeductions - normalDeductions);
        const normalTax = Math.max(0, normalBase * normalRate - taxCredits);
        const minimumBase = Math.max(0, profitBeforeDeductions - minimumDeductions);
        const minimumTax = firstThreePeriods ? 0 : Math.max(0, minimumBase * 0.10 - taxCredits);
        const payable = Math.max(normalTax, minimumTax);

        T.text("akvNormalMatrah", T.money(normalBase));
        T.text("akvNormalVergi", T.money(normalTax));
        T.text("akvAsgariMatrah", T.money(firstThreePeriods ? 0 : minimumBase));
        T.text("akvAsgariVergi", T.money(minimumTax));
        T.text("akvOdenecek", T.money(payable));
        T.text("akvDurum", minimumTax > normalTax ? "Asgari kurumlar vergisi" : "Normal kurumlar vergisi");

        const notice = document.getElementById("akvMuafiyet");
        notice.classList.toggle("hidden", !firstThreePeriods);
        if (firstThreePeriods) notice.textContent = `${startYear} yılında faaliyete başlayan kurum için ${year} hesap dönemi ilk üç hesap dönemi içinde olduğundan asgari kurumlar vergisi hesaplanmadı.`;
    };

    const resetRowBuilder = () => {
        document.getElementById("akvKalemSec").value = "";
        document.getElementById("akvKalemAra").value = "";
        document.querySelectorAll("#akvKalemSec option, #akvKalemSec optgroup").forEach((item) => { item.hidden = false; });
        T.set("akvKalemTutar", 0); T.set("akvKalemAsgari", 0);
        document.getElementById("akvOzelTutarWrap").classList.add("hidden");
        document.getElementById("akvKalemEkle").innerHTML = '<i class="bi bi-plus-lg"></i> Ekle';
        editingRow = null;
    };

    const resetCreditBuilder = () => {
        document.getElementById("akvVergiKalemSec").value = "";
        T.set("akvVergiKalemTutar", 0);
        document.getElementById("akvVergiKalemEkle").innerHTML = '<i class="bi bi-plus-lg"></i> Ekle';
        editingCredit = null;
    };

    document.getElementById("akvKalemSec").addEventListener("change", (event) => {
        const item = itemById(event.target.value);
        document.getElementById("akvOzelTutarWrap").classList.toggle("hidden", !item || item.effect !== "special");
    });

    document.getElementById("akvKalemAra").addEventListener("input", (event) => {
        const term = event.target.value.toLocaleLowerCase("tr-TR").trim();
        const select = document.getElementById("akvKalemSec");
        select.querySelectorAll("option").forEach((option) => {
            if (!option.value) return;
            option.hidden = term.length > 0 && !option.textContent.toLocaleLowerCase("tr-TR").includes(term);
        });
        select.querySelectorAll("optgroup").forEach((group) => {
            group.hidden = [...group.querySelectorAll("option")].every((option) => option.hidden);
        });
    });

    document.getElementById("akvKalemEkle").addEventListener("click", () => {
        const id = document.getElementById("akvKalemSec").value;
        const item = itemById(id);
        const amount = T.get("akvKalemTutar");
        if (!item || amount <= 0) return;
        const minimumAmount = item.effect === "special" ? Math.min(amount, T.get("akvKalemAsgari")) : item.effect === "deductible" ? amount : 0;
        const row = { id, amount, minimumAmount };
        const existingIndex = selectedRows.findIndex((existing, index) => existing.id === id && index !== editingRow);
        if (editingRow !== null) selectedRows[editingRow] = row;
        else if (existingIndex >= 0) selectedRows[existingIndex] = row;
        else selectedRows.push(row);
        resetRowBuilder(); renderRows(); calculate();
    });

    document.getElementById("akvVergiKalemEkle").addEventListener("click", () => {
        const id = document.getElementById("akvVergiKalemSec").value;
        const amount = T.get("akvVergiKalemTutar");
        if (!creditById(id) || amount <= 0) return;
        const row = { id, amount };
        const existingIndex = selectedCredits.findIndex((existing, index) => existing.id === id && index !== editingCredit);
        if (editingCredit !== null) selectedCredits[editingCredit] = row;
        else if (existingIndex >= 0) selectedCredits[existingIndex] = row;
        else selectedCredits.push(row);
        resetCreditBuilder(); renderCredits(); calculate();
    });

    document.getElementById("akvKalemler").addEventListener("click", (event) => {
        const edit = event.target.closest("[data-edit-row]");
        const remove = event.target.closest("[data-remove-row]");
        if (remove) { selectedRows.splice(Number(remove.dataset.removeRow), 1); renderRows(); calculate(); }
        if (edit) {
            editingRow = Number(edit.dataset.editRow);
            const row = selectedRows[editingRow]; const item = itemById(row.id);
            document.getElementById("akvKalemSec").value = row.id; T.set("akvKalemTutar", row.amount); T.set("akvKalemAsgari", row.minimumAmount);
            document.getElementById("akvOzelTutarWrap").classList.toggle("hidden", item.effect !== "special");
            document.getElementById("akvKalemEkle").innerHTML = '<i class="bi bi-check-lg"></i> Güncelle';
        }
    });

    document.getElementById("akvVergiKalemler").addEventListener("click", (event) => {
        const edit = event.target.closest("[data-edit-credit]");
        const remove = event.target.closest("[data-remove-credit]");
        if (remove) { selectedCredits.splice(Number(remove.dataset.removeCredit), 1); renderCredits(); calculate(); }
        if (edit) {
            editingCredit = Number(edit.dataset.editCredit);
            const row = selectedCredits[editingCredit]; document.getElementById("akvVergiKalemSec").value = row.id; T.set("akvVergiKalemTutar", row.amount);
            document.getElementById("akvVergiKalemEkle").innerHTML = '<i class="bi bi-check-lg"></i> Güncelle';
        }
    });

    const loadExample = (number) => {
        const example = examples[number];
        selectedRows = example.rows.map(([id, amount, minimumAmount = 0]) => ({ id, amount, minimumAmount: itemById(id).effect === "deductible" ? amount : minimumAmount }));
        selectedCredits = example.credits.map(([id, amount]) => ({ id, amount }));
        T.set("akvTicariKar", example.profit); T.set("akvKkeg", example.kkeg);
        document.getElementById("akvKurulus").value = 2020;
        resetRowBuilder(); resetCreditBuilder(); renderRows(); renderCredits(); calculate();
        window.scrollTo({ top: 0, behavior: "smooth" });
    };

    const exampleSelect = document.getElementById("akvOrnekSec");
    exampleSelect.addEventListener("change", () => { document.getElementById("akvOrnekAciklama").textContent = examples[exampleSelect.value].desc; });
    document.getElementById("akvOrnek").addEventListener("click", () => loadExample(exampleSelect.value));

    fillSelects();
    T.bindMoneyInputs(calculate);
    T.initTabs();
    document.querySelectorAll("#akvYil, #akvKurulus, #akvTicariKar, #akvKkeg, #akvKvOrani").forEach((el) => el.addEventListener("input", calculate));

    const params = new URLSearchParams(window.location.search);
    const technopark = Number(params.get("teknopark"));
    const arge = Number(params.get("arge"));
    if (Number.isFinite(technopark) && technopark > 0) selectedRows.push({ id: "technopark", amount: technopark, minimumAmount: technopark });
    if (Number.isFinite(arge) && arge > 0) selectedRows.push({ id: "arge", amount: arge, minimumAmount: arge });

    renderRows(); renderCredits(); calculate();
});
