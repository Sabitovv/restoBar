// Set base URL depending on your environment.
// Don't forget to add it to allowed origins on backend.
const baseUrl = '';

function getPreferredLang() {
    const saved = String(localStorage.getItem('preferredLang') || '').toLowerCase();
    if (saved === 'kk' || saved === 'ru' || saved === 'en') {
        return saved;
    }
    const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
    if (tgLang === 'kk' || tgLang === 'ru' || tgLang === 'en') {
        return tgLang;
    }
    const short = String(tgLang || '').slice(0, 2).toLowerCase();
    if (short === 'kk' || short === 'ru' || short === 'en') {
        return short;
    }
    return 'ru';
}

function getPreferredCurrency() {
    const saved = localStorage.getItem('preferredCurrency');
    if (saved && /^[A-Z]{3}$/.test(saved)) {
        return saved;
    }
    return 'KZT';
}

function withContext(endpoint) {
    const sep = endpoint.includes('?') ? '&' : '?';
    return `${endpoint}${sep}lang=${encodeURIComponent(getPreferredLang())}&currency=${encodeURIComponent(getPreferredCurrency())}`;
}

/**
 * Performs GET request.
 * @param {string} endpoint API endpoint path, e.g. '/info'.
 * @param {*} onSuccess Callback on successful request.
 */
export function get(endpoint, onSuccess) {
    $.ajax({
        url: baseUrl + withContext(endpoint),
        dataType: "json",
        success: result => onSuccess(result)
    });
}

/**
 * Performs POST request.
 * @param {string} endpoint API endpoint path, e.g. '/order'.
 * @param {string} data Request body in JSON format.
 * @param {*} onResult Callback on request result. In case of success, returns
 *                      result = { ok: true, data: <data-from-backend> }, otherwise
 *                      result = { ok: false, error: 'Something went wrong' }.
 */
export function post(endpoint, data, onResult) {
    $.ajax({
        type: 'POST',
        url: baseUrl + endpoint,
        data: data,
        contentType: 'application/json; charset=utf-8',
        dataType: 'json',
        success: result => onResult({ ok: true, data: result}),
        error: xhr => onResult({ ok: false, error: 'Something went wrong.'})
    })
}
