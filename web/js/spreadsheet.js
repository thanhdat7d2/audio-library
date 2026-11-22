// Spreadsheet import tab UI & handlers

function switchImportTab(tabName) {
    const singleTab = document.getElementById('import-tab-single');
    const sheetTab = document.getElementById('import-tab-spreadsheet');
    const btnSingle = document.getElementById('tab-btn-single');
    const btnSheet = document.getElementById('tab-btn-spreadsheet');

    if (tabName === 'spreadsheet') {
        singleTab.classList.add('hidden');
        sheetTab.classList.remove('hidden');
        btnSingle.classList.remove('active');
        btnSheet.classList.add('active');
    } else {
        sheetTab.classList.add('hidden');
        singleTab.classList.remove('hidden');
        btnSheet.classList.remove('active');
        btnSingle.classList.add('active');
    }
}

function setupSpreadsheetListeners() {
    document.getElementById('btn-download-template').addEventListener('click', async () => {
        const res = await window.pywebview.api.export_spreadsheet_template();
        if (res.status === 'success') alert('Template saved to: ' + res.path);
        else if (res.status === 'error') alert('Error saving template: ' + res.message);
    });

    document.getElementById('btn-select-spreadsheet').addEventListener('click', async () => {
        const path = await window.pywebview.api.select_spreadsheet_file();
        if (!path) return;
        selectedSpreadsheetPath = path;
        document.getElementById('selected-spreadsheet-name').innerText = path.split(/[\\/]/).pop();
        document.getElementById('spreadsheet-result-box').classList.add('hidden');

        const preview = await window.pywebview.api.preview_spreadsheet(path);
        if (preview.status !== 'success') {
            alert('Failed to read spreadsheet: ' + preview.message);
            document.getElementById('spreadsheet-preview-container').classList.add('hidden');
            return;
        }

        const mappedKeys = Object.keys(preview.mapped_columns || {}).join(', ');
        document.getElementById('spreadsheet-preview-meta').innerText =
            `${preview.total_rows} rows detected. Matched columns: ${mappedKeys || 'none'}`;

        const tbody = document.getElementById('spreadsheet-preview-body');
        tbody.innerHTML = '';
        (preview.preview_rows || []).forEach(r => {
            const audioCell = r.has_audio
                ? (r.audio_exists ? '<span class="pill-badge pill-entity-song">File Found</span>' : '<span class="pill-badge pill-no-audio">Path Missing</span>')
                : '<span class="pill-badge pill-no-audio">No Audio</span>';
            tbody.innerHTML += `
                <tr>
                    <td>${r.row}</td>
                    <td style="font-weight: 500;">${escapeHtml(r.song_name || '(missing)')}</td>
                    <td>${escapeHtml(r.main_artists || '-')}</td>
                    <td>${escapeHtml(r.album || '-')}</td>
                    <td>${escapeHtml(r.genres || '-')}</td>
                    <td>${renderTagPills(r.tags)}</td>
                    <td>${audioCell}</td>
                    <td><span class="linked-project-path">${escapeHtml(r.project_path || '-')}</span></td>
                </tr>
            `;
        });
        document.getElementById('spreadsheet-preview-container').classList.remove('hidden');
    });

    document.getElementById('btn-run-spreadsheet-import').addEventListener('click', async () => {
        if (!selectedSpreadsheetPath) return;
        const btn = document.getElementById('btn-run-spreadsheet-import');
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Importing...';

        try {
            const res = await window.pywebview.api.import_songs_from_spreadsheet(selectedSpreadsheetPath);
            const resultBox = document.getElementById('spreadsheet-result-box');
            resultBox.classList.remove('hidden');

            if (res.status === 'success') {
                let html = `
                    <strong>Import complete!</strong>
                    Imported <strong>${res.imported}</strong> of ${res.total_rows} rows
                    (${res.with_audio} with audio, ${res.without_audio} metadata-only, ${res.failed} failed).
                `;
                if (res.errors && res.errors.length > 0) {
                    html += '<ul class="import-error-list">' +
                        res.errors.map(err => `<li>Row ${err.row}: ${escapeHtml(err.message)}</li>`).join('') +
                        '</ul>';
                }
                resultBox.innerHTML = html;
                await refreshLibraryData();
            } else {
                resultBox.innerHTML = `<span style="color: #fca5a5;">Import error: ${escapeHtml(res.message)}</span>`;
            }
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-file-import"></i> Import All Rows';
        }
    });
}
