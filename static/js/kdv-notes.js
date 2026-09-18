function escapeDetailText(value) {
    const element = document.createElement('div');
    element.textContent = value == null ? '' : String(value);
    return element.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function renderNotes(notes) {
    const container = document.getElementById('quickNotesList');
    if (!container) return;
    container.replaceChildren();

    if (!notes || notes.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'text-muted small text-center py-2';
        empty.style.whiteSpace = 'pre-line';
        empty.textContent = 'Bilgi bulunmuyor.\n"+" butonuyla ekleyebilirsiniz.';
        container.append(empty);
        return;
    }

    const icon = (className) => {
        const element = document.createElement('i');
        element.className = className;
        element.setAttribute('aria-hidden', 'true');
        return element;
    };

    notes.forEach(note => {
        const item = document.createElement('div');
        item.className = 'quick-note-item p-3 mb-2 rounded-3 bg-light transition-all group-hover';

        const content = document.createElement('div');
        content.className = 'note-content small text-dark mb-1';
        content.style.lineHeight = '1.4';
        content.style.whiteSpace = 'pre-wrap';
        content.textContent = note.note_text;

        const meta = document.createElement('div');
        meta.className = 'note-meta d-flex gap-2 text-muted';
        meta.style.fontSize = '0.65rem';
        const created = document.createElement('span');
        created.append(icon('fa-regular fa-clock me-1'), document.createTextNode(note.created_at || ''));
        meta.append(created);

        if (note.updated_at) {
            const updated = document.createElement('span');
            updated.className = 'text-primary fw-bold';
            updated.title = 'Son Güncelleme: ' + note.updated_at;
            updated.append(icon('fa-solid fa-pen-nib me-1'), document.createTextNode('Güncellendi'));
            meta.append(updated);
        }

        const actions = document.createElement('div');
        actions.className = 'note-actions position-absolute top-0 end-0 p-2 group-hover-visible transition-all';
        const edit = document.createElement('button');
        edit.type = 'button';
        edit.className = 'btn btn-sm btn-link text-primary p-0 h-auto border-0 shadow-none';
        edit.title = 'Notu düzenle';
        edit.setAttribute('aria-label', edit.title);
        edit.append(icon('fa-solid fa-pen'));
        edit.addEventListener('click', () => editQuickNote(note.id, note.note_text));

        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'btn btn-sm btn-link text-danger p-0 h-auto border-0 ms-1 shadow-none';
        remove.title = 'Notu sil';
        remove.setAttribute('aria-label', remove.title);
        remove.append(icon('fa-solid fa-xmark'));
        remove.addEventListener('click', () => deleteQuickNote(note.id));

        actions.append(edit, remove);
        item.append(content, meta, actions);
        container.append(item);
    });
}
