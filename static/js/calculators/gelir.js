document.addEventListener("DOMContentLoaded", () => {

    const brutUcretInput = document.getElementById("brutUcret");
    const aySecimi = document.getElementById("aySecimi");
    const gelirTuruInput = document.getElementById("gelirTuru");
    const istisnaCheckbox = document.getElementById("asgariIstisna");

    /* TL format */
    brutUcretInput.addEventListener("input", function (e) {
        let val = e.target.value.replace(/[^\d]/g, "");
        if (!val) return;
        const number = parseFloat(val) / 100;
        e.target.value = number.toLocaleString("tr-TR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    });

    function gelirTuruKontrol() {
        const isUcret = gelirTuruInput.value === "ucret";
        istisnaCheckbox.disabled = !isUcret;
        if (!isUcret) {
            istisnaCheckbox.checked = false;
            aySecimi.value = "0";
            aySecimi.disabled = true;
        } else {
            aySecimi.disabled = !istisnaCheckbox.checked;
        }
    }

    gelirTuruInput.addEventListener("change", gelirTuruKontrol);
    istisnaCheckbox.addEventListener("change", gelirTuruKontrol);
    gelirTuruKontrol();

    document.getElementById("gelirVergisiForm").addEventListener("submit", async function (e) {
        e.preventDefault();

        const brut = parseFloat(
            brutUcretInput.value.replace(/\./g, "").replace(",", ".")
        ) || 0;

        const yil = parseInt(document.getElementById("yilInput").value);
        const ay = parseInt(aySecimi.value);
        const gelirTuru = gelirTuruInput.value;
        const istisna = istisnaCheckbox.checked;

        let oncekiMatrahlar = {};

        if (ay > 1 && gelirTuru === "ucret") {
            const ayAdlari = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"];
            let html = '<div style="text-align:left;">';

            for (let i = 0; i < ay - 1; i++) {
                html += `
                    <div class="mb-2">
                        <label>${ayAdlari[i]}</label>
                        <input type="text" class="swal2-input onceki" data-ay="${i+1}">
                    </div>`;
            }

            const { value } = await Swal.fire({
                title: "Önceki Ay Matrahları",
                html,
                confirmButtonText: "Devam",
                preConfirm: () => {
                    document.querySelectorAll(".onceki").forEach(inp => {
                        oncekiMatrahlar[inp.dataset.ay] =
                            parseFloat(inp.value.replace(/\./g,"").replace(",", ".")) || 0;
                    });
                    return true;
                }
            });

            if (!value) return;
        }

        fetch("/vergi-hesapla", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                brut,
                yil,
                ay,
                gelir_turu: gelirTuru,
                istisna,
                onceki_matrahlar: oncekiMatrahlar
            })
        })
        .then(r => r.json())
        .then(d => {
            if (d.error) {
                Swal.fire("Hata", d.error, "error");
                return;
            }

            Swal.fire({
                title: "Hesaplama Sonucu",
                html: `<b>Gelir Vergisi:</b> ${d.vergi.toLocaleString("tr-TR",{style:"currency",currency:"TRY"})}`,
                icon: "info"
            });

            const tbody = document.querySelector("#logTable tbody");
            const tr = document.createElement("tr");

            tr.innerHTML = `
                <td>${yil}</td>
                <td>${gelirTuru === "ucret" ? "Ücret" : "Ücret Dışı"}</td>
                <td>${brut.toLocaleString("tr-TR",{style:"currency",currency:"TRY"})}</td>
                <td class="text-center">${istisna ? "✔️" : "❌"}</td>
                <td>${ay === 0 ? "Yıllık" : ay}</td>
                <td class="text-danger fw-bold">${d.vergi.toLocaleString("tr-TR",{style:"currency",currency:"TRY"})}</td>
                <td class="text-success">${d.istisna ? d.istisna.toLocaleString("tr-TR",{style:"currency",currency:"TRY"}) : "-"}</td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-danger">Sil</button>
                </td>
            `;

            tr.querySelector("button").onclick = () => tr.remove();
            tbody.prepend(tr);
        })
        .catch(() => {
            Swal.fire("Hata", "Sunucu hatası oluştu", "error");
        });
    });
});
