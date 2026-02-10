/**
 * KDV İade Takibi - Core Logic (Flask Integrated)
 */

const STATUS_STAGES = {
    'Listeler': [
        'Listeler hazırlanacak',
        'Listeler hazırlandı',
        'Listeler GİB\'e yüklendi',
        'İade dilekçesi girildi'
    ],
    'Tutar / Tahsilat': [
        'Nakit İade Tutarı hesaba geçti',
        'Teminat Tutarı hesaba geçti',
        'Teminat sonrası kalan tutar hesaba geçti',   
        'Mahsuben iade gerçekleşti',
        'Ön Kontrol Raporu Tutarı hesaba geçti',
        'Ön Kontrol Raporu Kalan Tutar hesaba geçti',
        'Tecil-Tekin gerçekleşti'
    ],
    'YMM Rapor Süreci': [
        'Karşıtlar gönderildi',
        'Karşıtlar tamamlandı',
        'Rapor onaylanacak',
        'Rapor onaylandı'
    ],
    'Vergi Dairesi (Süreç)': [
        'Kontrol Raporu oluştu',
        'Eksiklik yazısı geldi',
        'İzahat hazırlanıyor',
        'İzahat gönderildi'
    ],
    'Vergi Dairesi (Makam)': [
        'YMM Ofisinde',
        'Memurda',
        'Müdür Yardımcısında',
        'Müdürde',
        'Defterdarlıkta',
        'Muhasebede',
        'İade Tamamlandı'
    ]
};

const REFUND_TYPES = [
    'YMM/Nakit/Teminatlı',
    'YMM/Nakit',
    'YMM/Mahsup',
    'Kısmen Nakit / Kısmen Mahsup',
    'Mahsup',
    'Tecil Terkin'
];

async function initDashboard() {
    await updateStats();
    await fetchFiles();
    await populateMukellefDropdown();
    populateRefundTypes();
}

async function updateStats() {
    try {
        const response = await fetch('/api/kdv/stats');
        if (!response.ok) throw new Error('Stats fetch status: ' + response.status);
        const stats = await response.json();
        const activeCountEl = document.getElementById('stat-active-count');
        const pendingAmountEl = document.getElementById('stat-pending-amount');
        if (activeCountEl) activeCountEl.innerText = stats.count || 0;
        if (pendingAmountEl) pendingAmountEl.innerText = `₺ ${formatMoney(stats.total_amount)}`;
    } catch (e) {
        console.error('Stats fetch error:', e);
    }
}

async function fetchFiles() {
    const container = document.getElementById('filesListContainer');
    const urlParams = new URLSearchParams(window.location.search);
    const mukellefId = urlParams.get('mukellef');
    
    try {
        let apiUrl = '/api/kdv/files?active=1';
        if (mukellefId) {
            apiUrl += `&mukellef_id=${mukellefId}`;
        }
        const personnelFilter = document.getElementById('dashboardPersonnelFilter');
        if (personnelFilter && personnelFilter.value) {
            apiUrl += `&user_id=${personnelFilter.value}`;
        }

        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error('Files fetch status: ' + response.status);
        const files = await response.json();
        renderDashboardFiles(files);
        
        // If specific client selected, update header
        if (mukellefId && files.length > 0) {
            const headerEl = document.querySelector('.dashboard-header h1');
            if(headerEl) headerEl.innerHTML = `<span class="text-primary">${files[0].client_name}</span> - İade Dosyaları`;
        } else if (mukellefId && files.length === 0) {
             const headerEl = document.querySelector('.dashboard-header h1');
             if(headerEl) headerEl.innerHTML = `Seçili Mükellef - İade Dosyaları`;
        }

    } catch (e) {
        console.error('KDV Files Fetch Error:', e);
        if (container) container.innerHTML = `<div class="alert alert-danger rounded-4">Veriler yüklenirken bir hata oluştu: ${e.message}</div>`;
    }
}

function renderDashboardFiles(files) {
    const container = document.getElementById('filesListContainer');
    if (!files || files.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-folder2-open fs-1 text-secondary opacity-25"></i>
                <p class="mt-3 text-secondary">Aktif bir iade süreci bulunamadı.</p>
            </div>`;
        return;
    }

    container.innerHTML = files.map(f => {
        const remainingDays = getReportRemainingDays(f);
        const progress = calculateProgress(f.status);
        const pColor = getProgressColor(progress);

        const guaranteeBadge = f.is_guaranteed ? 
            `<span class="badge bg-pink-lite text-pink ms-2" style="font-size:10px;"><i class="bi bi-shield-check"></i> TEMİNATLI</span>` : '';

        const deadlineLabel = remainingDays !== null ? `
            <div class="deadline-label mt-1 ${remainingDays < 5 ? 'text-danger fw-bold' : 'text-primary'}" style="font-size:10px;">
                <i class="bi bi-clock"></i> ${remainingDays > 0 ? remainingDays + ' GÜN KALDI' : 'SÜRE DOLDU'}
            </div>` : '';

        return `
            <div class="operation-row-card p-3 mb-3 bg-white border rounded-4 d-flex align-items-center gap-4 cursor-pointer position-relative overflow-hidden shadow-sm"
                 onclick="window.location.href='/kdv-detay/${f.id}'">
                
                <div class="client-info-mini d-flex align-items-center gap-3" style="min-width: 250px;">
                    <div class="client-logo bg-primary text-white d-flex align-items-center justify-content-center rounded-3 fw-bold" style="width:48px; height:48px; font-size:1.2rem;">
                        ${f.client_name.substring(0, 2).toUpperCase()}
                    </div>
                    <div>
                        <div class="fw-bold text-dark d-flex align-items-center">
                            ${f.client_name}
                            ${guaranteeBadge}
                        </div>
                        <div class="small text-secondary fw-semibold">${f.period} | ${f.subject}</div>
                    </div>
                </div>

                <div class="status-progress flex-grow-1" style="min-width: 200px;">
                    <div class="d-flex justify-content-between align-items-end mb-2">
                        <div class="d-flex flex-direction-column">
                            <span class="small fw-bold text-uppercase">${f.status}</span>
                            ${f.location ? `<span class="opacity-50" style="font-size:10px;"><i class="bi bi-geo-alt"></i> ${f.location.toUpperCase()}</span>` : ''}
                        </div>
                        <span class="small fw-bold" style="color:${pColor}">%${progress}</span>
                    </div>
                    <div class="progress" style="height: 6px;">
                        <div class="progress-bar" style="width: ${progress}%; background-color: ${pColor}"></div>
                    </div>
                </div>

                <div class="financials text-end" style="min-width: 150px;">
                    <div class="small text-secondary text-uppercase fw-bold" style="font-size:10px;">Talep Tutarı</div>
                    <div class="h5 fw-bold mb-0">₺ ${formatMoney(f.amount_request)}</div>
                    ${deadlineLabel}
                </div>

                <div class="action-arrow">
                    <div class="detail-arrow-btn border rounded-circle d-flex align-items-center justify-content-center text-secondary" style="width:32px; height:32px;">
                        <i class="bi bi-chevron-right"></i>
                    </div>
                </div>

                <div class="row-hover-line position-absolute top-0 start-0 bottom-0 bg-primary" style="width:4px; display:none;"></div>
            </div>
        `;
    }).join('');
}

// --- Modals & Actions ---

async function populateMukellefDropdown() {
    const select = document.getElementById('modalClientId');
    if (!select) return;
    
    try {
        const response = await fetch('/api/kdv/all-mukellefs');
        const list = await response.json();
        
        select.innerHTML = '<option value="">Seçiniz...</option>';
        list.forEach(m => {
            select.innerHTML += `<option value="${m.id}">${m.unvan}</option>`;
        });
    } catch (e) {
        console.error('Mükellef listesi hatası:', e);
    }
}

function populateRefundTypes() {
    const select = document.getElementById('modalType');
    if (!select) return;
    
    select.innerHTML = '<option value="">Seçiniz...</option>';
    REFUND_TYPES.forEach(t => {
        select.innerHTML += `<option value="${t}">${t}</option>`;
    });
}

function openNewFileModal() {
    const modal = new bootstrap.Modal(document.getElementById('newFileModal'));
    initMonthSelector();
    modal.show();
}

const monthsList = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
let selectedMonths = [];

function initMonthSelector() {
    const container = document.getElementById('monthSelector');
    if (!container) return;
    
    selectedMonths = [];
    document.getElementById('modalPeriod').value = "";
    
    container.innerHTML = monthsList.map((m, i) => {
        const val = (i + 1).toString().padStart(2, '0');
        return `<button type="button" class="btn btn-outline-secondary btn-sm month-btn" data-val="${val}" onclick="toggleMonth(this)">${m}</button>`;
    }).join('');

    // Year change sync
    document.getElementById('modalYear').onchange = () => {
        const year = document.getElementById('modalYear').value;
        if (selectedMonths.length > 0) {
            document.getElementById('modalPeriod').value = selectedMonths.join('-') + '/' + year;
        }
    };
}

function toggleMonth(btn) {
    const val = btn.dataset.val;
    if (selectedMonths.includes(val)) {
        selectedMonths = selectedMonths.filter(m => m !== val);
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline-secondary');
    } else {
        selectedMonths.push(val);
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('btn-primary');
    }
    
    selectedMonths.sort();
    const year = document.getElementById('modalYear').value;
    if (selectedMonths.length > 0) {
        document.getElementById('modalPeriod').value = selectedMonths.join('-') + '/' + year;
    } else {
        document.getElementById('modalPeriod').value = "";
    }
}

function selectAllMonths() {
    selectedMonths = monthsList.map((_, i) => (i + 1).toString().padStart(2, '0'));
    document.querySelectorAll('.month-btn').forEach(btn => {
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('btn-primary');
    });
    const year = document.getElementById('modalYear').value;
    document.getElementById('modalPeriod').value = "01-12/" + year;
    // Special case for all months: use 01-12 format or actual list? 
    // User said "02-03-04/2025", so for all it should be "01-02-03-04-05-06-07-08-09-10-11-12/2025" or "01-12/2025".
    // I'll use the full list for consistency unless it's too long.
    document.getElementById('modalPeriod').value = selectedMonths.join('-') + '/' + year;
}

async function handleFileFormSubmit(e) {
    e.preventDefault();
    const data = {
        mukellef_id: document.getElementById('modalClientId').value,
        period: document.getElementById('modalPeriod').value,
        subject: document.getElementById('modalSubject').value,
        type: document.getElementById('modalType').value,
        amount_request: parseFloat(document.getElementById('modalAmount').value)
    };

    try {
        const response = await fetch('/api/kdv/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.status === 'success') {
            bootstrap.Modal.getInstance(document.getElementById('newFileModal')).hide();
            Swal.fire('Başarılı', 'Yeni dosya oluşturuldu.', 'success');
            initDashboard();
        } else {
            Swal.fire('Hata', result.message, 'error');
        }
    } catch (e) {
        Swal.fire('Hata', 'Sunucu ile iletişim hatası.', 'error');
    }
}

// --- Shared Helper Functions ---

function formatMoney(n) {
    if (typeof n !== 'number') n = parseFloat(n) || 0;
    return n.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getReportRemainingDays(file) {
    const isG = file.is_guaranteed || (file.type && file.type.toLowerCase().includes('teminat'));
    if (!isG) return null;
    
    const baseDate = file.guarantee_date || file.date;
    if (!baseDate) return null;
    
    // logic: date + 60 days
    const parts = baseDate.split('.');
    let startDate;
    if (parts.length === 3) {
        startDate = new Date(parts[2], parts[1]-1, parts[0]);
    } else {
        startDate = new Date(baseDate);
    }
    
    const targetDate = new Date(startDate.getTime() + (60 * 24 * 60 * 60 * 1000));
    const now = new Date();
    const diff = targetDate - now;
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function calculateProgress(status) {
    if (status.includes('Tamamlandı')) return 100;
    if (status.includes('Müdür')) return 85;
    if (status.includes('onaylandı')) return 80;
    if (status.includes('Rapor')) return 60;
    if (status.includes('Karşıtlar')) return 50;
    if (status.includes('Eksiklik')) return 40;
    if (status.includes('Yüklendi')) return 30;
    return 10;
}

function getProgressColor(progress) {
    if (progress >= 100) return '#10b981';
    if (progress >= 80) return '#8b5cf6';
    if (progress >= 50) return '#3b82f6';
    if (progress >= 30) return '#f59e0b';
    return '#94a3b8';
}
