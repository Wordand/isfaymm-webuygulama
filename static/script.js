function handleKVUpload(event) {

    const file = event.target.files[0];
    if (!file) return;

    Swal.fire({ title: 'Yükleniyor…', allowOutsideClick: false, didOpen: () => Swal.showLoading() });
    const fd = new FormData();
    fd.append('kv_pdf', file);

    fetch('/indirimlikurumlar/upload-kv-beyan', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(handlePDFResponse)
        .catch(err => {
            Swal.close();
            console.error(err);
            Swal.fire('Sunucu Hatası', 'PDF yüklenirken bir sorun oluştu', 'error');
        });
}



// --------------------------------------------------
// SweetAlert2 kısa mesaj fonksiyonu
// --------------------------------------------------
function showSwalMessage(type, title, text) {
    Swal.fire({
        icon: type,
        title: title,
        text: text,
        timer: 3000,
        toast: true,
        position: "top-end",
        showConfirmButton: false
    });
}

// --------------------------------------------------
// Belge üzerine yazma (global RPC çağrısı örneği)
// --------------------------------------------------
function uploadOverwrite(msg) {
    const overwriteForm = new FormData();
    overwriteForm.append("unvan", msg.unvan);
    overwriteForm.append("donem", msg.donem);
    overwriteForm.append("belge_turu", msg.belge_turu);
    overwriteForm.append("dosya", msg.dosya);

    fetch("/yeniden-yukle", {
        method: "POST",
        body: overwriteForm
    })
        .then(res => res.json())
        .then(data => {
            showSwalMessage(data.status, data.title, data.message);
            if (data.status === "success") {
                setTimeout(() => location.reload(), 1500);
            }
        })
        .catch(err => {
            Swal.fire({
                icon: "error",
                title: "Üzerine Yazma Hatası",
                text: `Belge üzerine yazılırken bir hata oluştu: ${err}`
            });
            console.error("Üzerine yazma hatası:", err);
        });
}

// --------------------------------------------------
// Sidebar toggle & no-sidebar-layout kontrolü
// --------------------------------------------------
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const body = document.body;
    const mobileOverlay = document.getElementById('mobile-overlay');
    const toggleBtn = document.querySelector('.toggle-btn');

    if (body.classList.contains('no-sidebar-layout')) return;

    if (window.innerWidth > 768) {
        sidebar.classList.toggle('collapsed');
        localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        if (toggleBtn) toggleBtn.setAttribute('aria-expanded', sidebar.classList.contains('collapsed'));
    } else {
        body.classList.toggle('mobile-menu-open');
        if (body.classList.contains('mobile-menu-open')) {
            mobileOverlay.style.display = 'block';
            setTimeout(() => mobileOverlay.style.opacity = '1', 10);
        } else {
            mobileOverlay.style.opacity = '0';
            setTimeout(() => mobileOverlay.style.display = 'none', 300);
        }
        if (toggleBtn) toggleBtn.setAttribute('aria-expanded', body.classList.contains('mobile-menu-open'));
    }
}



window.addEventListener('DOMContentLoaded', () => {

    const kvInput = document.getElementById('kvUploadInput');


    if (kvInput) {
        kvInput.addEventListener('change', handleKVUpload);
    }
});


// Teşvik belgeleri silme formları (AJAX)
document.querySelectorAll('.delete-tesvik-form').forEach(formElement => {
    formElement.addEventListener('submit', async event => {
        event.preventDefault();
        Swal.fire({
            title: "Emin misiniz?",
            text: "Bu belge silinecek. Bu işlem geri alınamaz!",
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: "#d33",
            cancelButtonColor: "#3085d6",
            confirmButtonText: "Evet, sil!",
            cancelButtonText: "İptal"
        }).then(async result => {
            if (result.isConfirmed) {
                try {
                    const response = await fetch(formElement.action, {
                        method: 'POST',
                        body: new FormData(formElement)
                    });
                    const data = await response.json();
                    showSwalMessage(data.status, data.title, data.message);
                    if (data.status === "success") {
                        const row = formElement.closest('tr');
                        if (row) row.remove();
                    }
                } catch (err) {
                    console.error('Belge silme hatası:', err);
                    showSwalMessage('error', 'Hata!', 'Belge silinirken bir sorun oluştu.');
                }
            }
        });
    });
});


// --------------------------------------------------
// Window resize: responsive sidebar
// --------------------------------------------------
window.addEventListener('resize', () => {
    const sidebar = document.getElementById('sidebar');
    const body = document.body;
    const toggleBtn = document.querySelector('.toggle-btn');
    const mobileOverlay = document.getElementById('mobile-overlay');

    if (body.classList.contains('no-sidebar-layout')) {
        sidebar.classList.add('hidden-initial');
        if (toggleBtn) toggleBtn.style.display = 'none';
        body.classList.remove('mobile-menu-open');
        mobileOverlay.style.display = 'none';
        mobileOverlay.style.opacity = '0';
        return;
    }

    if (window.innerWidth > 768) {
        body.classList.remove('mobile-menu-open');
        mobileOverlay.style.display = 'none';
        mobileOverlay.style.opacity = '0';
        const collapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (collapsed) {
            sidebar.classList.add('collapsed');
            if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
        } else {
            sidebar.classList.remove('collapsed');
            if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
        }
    } else {
        sidebar.classList.remove('collapsed');
        if (toggleBtn) toggleBtn.setAttribute('aria-expanded', body.classList.contains('mobile-menu-open'));
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const draggables = document.querySelectorAll('.draggable');
    const dropzones = document.querySelectorAll('.dropzone');
    const btnFA = document.getElementById('btnFA');
    const btnKDV = document.getElementById('btnKDV');
    const faInputs = document.getElementById('faInputs');
    const kdvInput = document.getElementById('kdvPeriodsInput');

    // Durumu güncelle: gizli input'lar + buton enable/disable
    function updateState() {
        if (!faInputs || !kdvInput || !btnFA || !btnKDV) return;
        faInputs.innerHTML = '';
        const faYears = [...document.querySelectorAll('#faYears li:not(.placeholder)')]
            .map(li => li.textContent.trim());
        faYears.forEach(year => {
            const inp = document.createElement('input');
            inp.type = 'hidden';
            inp.name = 'donemler';
            inp.value = year;
            faInputs.appendChild(inp);
        });

        // 2) KDV dönemleri CSV olarak sakla
        const kdvPeriods = [...document.querySelectorAll('#kdvPeriods li:not(.placeholder)')]
            .map(li => li.textContent.trim());
        kdvInput.value = kdvPeriods.join(',');

        // 3) Buton durumları
        btnFA.disabled = faYears.length === 0;
        btnKDV.disabled = kdvPeriods.length === 0;
    }

    // Eğer dropzone boşaldıysa placeholder ekle
    function ensurePlaceholder(zone) {
        if (zone.querySelectorAll('li:not(.placeholder)').length === 0
            && !zone.querySelector('.placeholder')) {
            const ph = document.createElement('li');
            ph.className = 'placeholder text-muted text-center';
            ph.textContent = 'Buraya sürükleyebilirsiniz';
            zone.appendChild(ph);
        }
    }

    // Sürüklenebilirleri ayarla
    draggables.forEach(item => {
        item.addEventListener('dragstart', e => {
            e.dataTransfer.setData('text/plain', item.textContent.trim());
        });
    });

    // Bırakma bölgelerini ayarla
    dropzones.forEach(zone => {
        zone.addEventListener('dragover', e => e.preventDefault());
        zone.addEventListener('drop', e => {
            e.preventDefault();
            const text = e.dataTransfer.getData('text/plain');
            const isFA = zone.id === 'faYears';
            const isKDV = zone.id === 'kdvPeriods';

            // Format kontrolleri
            const yearRe = /^\d{4}$/;
            const monthYearRe = /^[^\/]+ \/ \d{4}$/;
            if (isFA && !yearRe.test(text)) return;
            if (isKDV && !monthYearRe.test(text)) return;

            // Aynısı eklenmiş mi?
            if (![...zone.children].some(li => li.textContent.trim() === text)) {
                // varsa placeholder’ı sil
                zone.querySelectorAll('.placeholder').forEach(ph => ph.remove());
                // yeni <li> ekle
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.textContent = text;
                li.style.cursor = 'pointer';
                // tıklayınca silinsin
                li.addEventListener('click', () => {
                    li.remove();
                    ensurePlaceholder(zone);
                    updateState();
                });
                zone.appendChild(li);
                updateState();
            }
        });
    });

    // ilk yüklemede placeholder varsa temizle / butonları güncelle
    document.querySelectorAll('.dropzone').forEach(zone => {
        // eğer başlangıçta içine otomatik placeholder koyduysak sorun yok
        ensurePlaceholder(zone);
    });
    updateState();
});
