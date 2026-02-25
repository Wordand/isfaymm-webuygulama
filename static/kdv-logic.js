/**
 * KDV İade Takip Sistemi - Ortak Mantık ve Yardımcı Fonksiyonlar
 */

// Para birimi formatlama (1.234,56 formatında döner)
function formatMoney(amount) {
    if (amount === undefined || amount === null || isNaN(amount)) return '0,00';
    return Number(amount).toLocaleString('tr-TR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// YMM Rapor teslimine kalan gün sayısını hesaplar
function getReportRemainingDays(file) {
    if (!file || !file.date) return null;
    
    try {
        // DD.MM.YYYY formatını YYYY-MM-DD formatına çevir
        const parts = file.date.split('.');
        if (parts.length !== 3) return null;
        
        const startDate = new Date(`${parts[2]}-${parts[1]}-${parts[0]}`);
        const today = new Date();
        
        // Varsayılan: Yükleme tarihinden itibaren 6 ay
        const dueDate = new Date(startDate);
        dueDate.setMonth(dueDate.getMonth() + 6);
        
        const diffTime = dueDate - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        return diffDays > 0 ? diffDays : 0;
    } catch (e) {
        console.error("Gün hesaplama hatası:", e);
        return null;
    }
}

// Dashboard başlatma
async function initDashboard() {
    console.log("KDV Dashboard başlatılıyor...");
    
    // updateStats() dashboard.html içinde tanımlıdır
    if (typeof updateStats === 'function') {
        updateStats();
    }
    
    // Aktif dosyaları listele
    fetchActiveFiles();
}

// Aktif dosyaları getir ve listele (Dashboard için)
async function fetchActiveFiles() {
    const container = document.getElementById('filesListContainer');
    if (!container) return;
    
    // Yükleniyor spinner'ı göster
    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2 text-muted">Dosyalar yükleniyor...</p>
        </div>`;
    
    const userId = document.getElementById('dashboardPersonnelFilter')?.value || '';
    let apiUrl = '/api/kdv/files?active=1';
    if (userId) apiUrl += `&user_id=${userId}`;
    
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error('Sunucu hatası: ' + response.status);
        const files = await response.json();
        
        renderFilesList(files);
    } catch (error) {
        console.error('Aktif dosyalar yüklenirken hata:', error);
        container.innerHTML = `
            <div class="alert alert-danger rounded-4 p-4 border-0 shadow-sm">
                <i class="fa-solid fa-circle-exclamation me-2"></i>
                Veriler yüklenirken bir hata oluştu: ${error.message}
            </div>`;
    }
}

// Dosya listesini render et (Dashboard için)
function renderFilesList(files) {
    const container = document.getElementById('filesListContainer');
    if (!container) return;
    
    if (!files || files.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5 bg-white rounded-4 border shadow-sm">
                <i class="fa-solid fa-folder-open fs-1 mb-3 text-muted opacity-25"></i>
                <p class="text-secondary mb-0">Şu an takip edilen aktif dosya bulunmuyor.</p>
                <button class="btn btn-link fw-bold text-decoration-none mt-2" onclick="openNewFileModal()">Yeni bir tane ekle</button>
            </div>`;
        return;
    }
    
    let html = '<div class="row g-4">';
    files.forEach(file => {
        // Durum renkleri ve ikonları
        let statusClass = 'bg-primary';
        let statusIcon = 'fa-circle-dot';
        let cardStatusClass = 'card-status-info';
        
        const status = file.status || '';
        if (status.includes('Eksiklik')) {
            statusClass = 'bg-warning text-dark';
            statusIcon = 'fa-triangle-exclamation';
            cardStatusClass = 'card-status-warning';
        } else if (status.includes('Tamamlandı') || status.includes('Bitti')) {
            statusClass = 'bg-success';
            statusIcon = 'fa-check-double';
            cardStatusClass = 'card-status-success';
        } else if (status.includes('İptal') || status.includes('Red')) {
            statusClass = 'bg-danger';
            statusIcon = 'fa-xmark';
            cardStatusClass = 'card-status-danger'; 
        } else if (status.includes('Vergi Dairesi') || status.includes('Makam')) {
            statusClass = 'bg-info text-dark';
            statusIcon = 'fa-building-columns';
            cardStatusClass = 'card-status-info';
        }
        
        const periodStr = (file.period_year && file.period_month) ? `${file.period_year}-${file.period_month}` : (file.period || '-');

        html += `
            <div class="col-md-6 col-lg-4 col-xl-3">
                <div class="card h-100 border-0 shadow-sm rounded-4 overflow-hidden file-card-premium ${cardStatusClass} position-relative" 
                     onclick="window.location.href='/kdv-detay/${file.id}'" 
                     style="transition: all 0.3s ease; cursor: pointer; border: 1px solid rgba(0,0,0,0.03) !important; padding: 0;">
                    <div class="card-body p-4 d-flex flex-column" style="min-height: 200px;">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <span class="badge ${statusClass} rounded-pill px-3 py-2 small fw-bold shadow-sm">
                                <i class="fa-solid ${statusIcon} me-1 small"></i> ${file.status || 'İade dilekçesi girildi'}
                            </span>
                            <span class="badge bg-light text-secondary border rounded-pill px-2 py-1" style="font-size: 0.7rem;">
                                ${periodStr}
                            </span>
                        </div>
                        <h5 class="fw-bold text-dark mb-1 text-truncate" title="${file.client_name}" style="font-size: 1.05rem;">${file.client_name}</h5>
                        <p class="small text-secondary mb-3 text-truncate" style="font-size: 0.8rem;">${file.subject || '-'}</p>
                        
                        <div class="d-flex justify-content-between align-items-center mt-auto pt-3 border-top">
                            <div>
                                <small class="d-block text-muted fw-bold" style="font-size: 0.65rem; letter-spacing: 0.5px;">TALEP TUTARI</small>
                                <span class="fw-bold text-dark">₺ ${formatMoney(file.amount_request)}</span>
                            </div>
                            <div class="text-end">
                                <small class="d-block text-muted fw-bold" style="font-size: 0.65rem; letter-spacing: 0.5px;">MAKAM</small>
                                <span class="small fw-bold text-primary">${file.location || 'VD'}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}
