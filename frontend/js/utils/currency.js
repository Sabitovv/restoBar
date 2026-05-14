/**
 * Create display (user-friendly) string cost for the cost in minimal currency unit.
 * Example: 1000 + KZT => ₸10.00
 * @param {*} costInMinimalUnit Cost in minimal unit (cents).
 * @returns Display cost string that may be used in the UI.
 */
export function toDisplayCost(costInMinimalUnit, currency = 'KZT') {
    const normalized = (currency || 'KZT').toUpperCase();
    try {
        return new Intl.NumberFormat(undefined, {
            style: 'currency',
            currency: normalized,
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        }).format((Number(costInMinimalUnit) || 0) / 100.0);
    } catch {
        return `${normalized} ${(Number(costInMinimalUnit) || 0) / 100.0}`;
    }
}
