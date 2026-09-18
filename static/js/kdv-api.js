window.kdvFetch = function (input, options = {}) {
    const isRequest = input instanceof Request;
    const url = new URL(isRequest ? input.url : input, window.location.href);
    const method = (options.method || (isRequest ? input.method : 'GET')).toUpperCase();
    if (url.origin === window.location.origin && url.pathname.startsWith('/api/kdv/') &&
        !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        const token = document.querySelector('meta[name="csrf-token"]')?.content;
        if (!token) return Promise.reject(new Error('Sayfayı yenileyip tekrar deneyin.'));
        const headers = new Headers(options.headers || (isRequest ? input.headers : undefined));
        headers.set('X-CSRFToken', token);
        options = { ...options, headers };
    }
    return window.fetch(input, options);
};
