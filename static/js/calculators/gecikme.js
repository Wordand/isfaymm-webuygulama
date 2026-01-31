document.addEventListener("DOMContentLoaded", () => {

    const borcInput = document.getElementById("borc");
    const borcTuruSelect = document.getElementById("borcTuru");
    const vadeInput = document.getElementById("vade");
    const odemeInput = document.getElementById("odeme");
    const hesaplaBtn = document.getElementById("hesaplaBtn");
    const logTableBody = document.querySelector("#gecikmeLogTable tbody");

    hesaplaBtn.addEventListener("click", () => {

        const borc = parseFloat(borcInput.value);
        const borcTuru = borcTuruSelect.value;
        const vade = vadeInput.value;
        const odeme = odemeInput.value;

        if (isNaN(borc) || borc <= 0 || !vade || !odeme) {
            Swal.fire("Uyarı", "Tüm alanlar eksiksiz ve doğru girilmelidir.", "warning");
            return;
        }

        if (borcTuru === "usulsuzluk") {
            Swal.fire(
                "Bilgi",
                "Usulsüzlük cezalarında gecikme zammı uygulanmaz (6183 md.51).",
                "info"
            );
            return;
        }

        fetch("/gecikme-zammi-hesapla", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                borc: borc,
                vade: vade,
                odeme: odeme,
                borc_turu: borcTuru
            })
        })
        .then(res => {
            if (!res.ok) throw new Error("Sunucu hatası");
            return res.json();
        })
        .then(data => {

            const gecikme = Number(data.gecikme_zammi).toLocaleString("tr-TR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });

            const toplam = Number(data.toplam_borc).toLocaleString("tr-TR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });

            Swal.fire({
                title: "Hesaplama Sonucu",
                html: `
                    <strong>Gecikme Zammı:</strong> ${gecikme} TL<br>
                    <strong>Toplam Borç:</strong> ${toplam} TL
                `,
                icon: "info"
            });

            const tr = document.createElement("tr");

            tr.innerHTML = `
                <td>${borcTuru.replace("_", " ").toUpperCase()}</td>
                <td>${borc.toLocaleString("tr-TR", { minimumFractionDigits: 2 })} TL</td>
                <td>${vade}</td>
                <td>${odeme}</td>
                <td class="text-danger fw-bold">${gecikme} TL</td>
                <td class="text-success fw-bold">${toplam} TL</td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-danger">Sil</button>
                </td>
            `;

            tr.querySelector("button").addEventListener("click", () => {
                tr.remove();
            });

            logTableBody.prepend(tr);
        })
        .catch(err => {
            Swal.fire("Hata", "Hesaplama sırasında bir hata oluştu.", "error");
            console.error(err);
        });
    });
});
