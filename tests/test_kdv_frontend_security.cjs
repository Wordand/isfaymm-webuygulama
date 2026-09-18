const { test, before, after, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('playwright');

let browser;
let page;
const root = path.resolve(__dirname, '..');
const payload = '<img src="x" onerror="window.attack=1"><svg onload="window.attack=2"></svg>';

before(async () => {
    browser = await chromium.launch({
        headless: true, channel: process.env.PLAYWRIGHT_BROWSER_CHANNEL || undefined,
    });
});
after(async () => {
    if (browser) await browser.close();
});
beforeEach(async () => {
    page = await browser.newPage();
    await page.route('http://synthetic.test/**', route => route.fulfill({
        contentType: 'text/html',
        body: '<html><head><meta name="csrf-token" content="synthetic-token"></head>' +
            '<body><div id="quickNotesList"></div><div id="escaped"></div></body></html>',
    }));
    await page.goto('http://synthetic.test/');
    await page.addScriptTag({ path: path.join(root, 'static/js/kdv-notes.js') });
    await page.addScriptTag({ path: path.join(root, 'static/js/kdv-api.js') });
    await page.evaluate(() => {
        window.attack = 0;
        window.edits = [];
        window.deletes = [];
        window.editQuickNote = (id, text) => window.edits.push({ id, text });
        window.deleteQuickNote = id => window.deletes.push(id);
        window.requests = [];
        window.fetch = async (input, options = {}) => {
            window.requests.push({
                url: input instanceof Request ? input.url : String(input),
                headers: Object.fromEntries(new Headers(options.headers)),
                body: options.body,
            });
            return new Response('{}', { headers: { 'Content-Type': 'application/json' } });
        };
    });
});
afterEach(async () => {
    if (page) await page.close();
});

test('HTML in a note is displayed as text and cannot execute', async () => {
    await page.evaluate(text => renderNotes([{ id: 41, note_text: text, created_at: 'test date' }]), payload);
    assert.equal(await page.locator('.note-content').textContent(), payload);
    assert.equal(await page.locator('#quickNotesList img, #quickNotesList svg, #quickNotesList script').count(), 0);
    assert.equal(await page.evaluate(() => window.attack), 0);
});

test('quotes, newlines, Turkish text and JavaScript-looking text remain unchanged when editing', async () => {
    const text = 'Türkçe: İıŞşĞğÜüÖöÇç\n"double" \'single\' `backtick` ${window.attack=3} \\ end';
    await page.evaluate(text => renderNotes([{ id: 41, note_text: text, created_at: 'date' }]), text);
    await page.getByRole('button', { name: 'Notu düzenle' }).click();
    assert.deepEqual(await page.evaluate(() => window.edits), [{ id: 41, text }]);
    assert.equal(await page.evaluate(() => window.attack), 0);
    assert.equal(await page.locator('.note-content').evaluate(el => getComputedStyle(el).whiteSpace), 'pre-wrap');
});

test('delete buttons target the correct note without inline handlers', async () => {
    await page.evaluate(() => renderNotes([
        { id: 41, note_text: 'first' }, { id: 42, note_text: 'second' },
    ]));
    await page.getByRole('button', { name: 'Notu sil' }).nth(1).click();
    assert.deepEqual(await page.evaluate(() => window.deletes), [42]);
    assert.equal(await page.locator('#quickNotesList [onclick]').count(), 0);
});

test('note date fields and update tooltips cannot inject markup', async () => {
    await page.evaluate(text => renderNotes([{ id: 41, note_text: 'note', created_at: text, updated_at: text }]), payload);
    assert.equal(await page.locator('.note-meta span').first().textContent(), payload);
    assert.equal(await page.locator('.note-meta .text-primary').getAttribute('title'), 'Son Güncelleme: ' + payload);
    assert.equal(await page.locator('#quickNotesList img, #quickNotesList svg').count(), 0);
    assert.equal(await page.evaluate(() => window.attack), 0);
});

test('rerendering replaces stale notes and does not duplicate listeners', async () => {
    await page.evaluate(() => {
        renderNotes([{ id: 41, note_text: 'old' }]);
        renderNotes([{ id: 42, note_text: 'new' }]);
    });
    assert.equal(await page.locator('.quick-note-item').count(), 1);
    await page.getByRole('button', { name: 'Notu düzenle' }).click();
    assert.deepEqual(await page.evaluate(() => window.edits), [{ id: 42, text: 'new' }]);
});

test('empty notes clear existing content and preserve the empty state', async () => {
    await page.evaluate(() => {
        renderNotes([{ id: 41, note_text: 'old' }]);
        renderNotes([]);
    });
    assert.equal(await page.locator('.quick-note-item').count(), 0);
    assert.match(await page.locator('#quickNotesList').textContent(), /Bilgi bulunmuyor/);
});

test('history text and document titles are escaped safely for text and attributes', async () => {
    const text = '" onmouseover="window.attack=4" \' & ' + payload;
    await page.evaluate(text => {
        const escaped = escapeDetailText(text);
        document.getElementById('escaped').innerHTML = `<span title="${escaped}">${escaped}</span>`;
    }, text);
    assert.equal(await page.locator('#escaped span').textContent(), text);
    assert.equal(await page.locator('#escaped span').getAttribute('title'), text);
    assert.equal(await page.locator('#escaped [onmouseover], #escaped img, #escaped svg').count(), 0);
});

test('JSON POST includes CSRF and preserves content type, body and original headers', async () => {
    const result = await page.evaluate(async () => {
        const headers = { 'Content-Type': 'application/json' };
        const body = JSON.stringify({ id: 41, text: 'note' });
        await kdvFetch('/api/kdv/note/update', { method: 'POST', headers, body });
        return { request: window.requests[0], headers, body };
    });
    assert.equal(result.request.headers['x-csrftoken'], 'synthetic-token');
    assert.equal(result.request.headers['content-type'], 'application/json');
    assert.equal(result.request.body, result.body);
    assert.deepEqual(result.headers, { 'Content-Type': 'application/json' });
});

test('DELETE includes CSRF', async () => {
    const headers = await page.evaluate(async () => {
        await kdvFetch('/api/kdv/note/delete/41', { method: 'DELETE' });
        return window.requests[0].headers;
    });
    assert.equal(headers['x-csrftoken'], 'synthetic-token');
});

test('multipart uploads keep FormData and let the browser set its boundary', async () => {
    const result = await page.evaluate(async () => {
        const body = new FormData();
        body.append('file', new Blob(['synthetic bytes']), 'synthetic.pdf');
        await kdvFetch('/api/kdv/upload-doc', { method: 'POST', body });
        return { sameBody: window.requests[0].body === body, headers: window.requests[0].headers };
    });
    assert.equal(result.sameBody, true);
    assert.equal(result.headers['x-csrftoken'], 'synthetic-token');
    assert.equal(result.headers['content-type'], undefined);
});

test('GET requests do not send CSRF tokens', async () => {
    const headers = await page.evaluate(async () => {
        await kdvFetch('/api/kdv/file/17');
        return window.requests[0].headers;
    });
    assert.equal(headers['x-csrftoken'], undefined);
});

test('external origins never receive the automatically added token', async () => {
    const headers = await page.evaluate(async () => {
        await kdvFetch('https://untrusted.invalid/api/kdv/note/add', { method: 'POST' });
        return window.requests[0].headers;
    });
    assert.equal(headers['x-csrftoken'], undefined);
});

test('unrelated calculator requests are unchanged', async () => {
    const headers = await page.evaluate(async () => {
        await kdvFetch('/vergi-hesapla', { method: 'POST' });
        return window.requests[0].headers;
    });
    assert.equal(headers['x-csrftoken'], undefined);
});

test('a missing page token rejects the change without sending an API request', async () => {
    const result = await page.evaluate(async () => {
        document.querySelector('meta[name="csrf-token"]').remove();
        try {
            await kdvFetch('/api/kdv/note/add', { method: 'POST' });
            return { rejected: false };
        } catch (error) {
            return { rejected: true, message: error.message, requests: window.requests.length };
        }
    });
    assert.equal(result.rejected, true);
    assert.match(result.message, /yenileyip/);
    assert.equal(result.requests, 0);
});

test('Request objects preserve existing headers and receive CSRF for unsafe methods', async () => {
    const headers = await page.evaluate(async () => {
        const request = new Request('http://synthetic.test/api/kdv/note/update', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
        });
        await kdvFetch(request);
        return window.requests[0].headers;
    });
    assert.equal(headers['x-csrftoken'], 'synthetic-token');
    assert.equal(headers['content-type'], 'application/json');
});
