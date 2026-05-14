import { Route } from "../routing/route.js";
import { navigateTo } from "../routing/router.js";
import { get } from "../requests/requests.js";
import { TelegramSDK } from "../telegram/telegram.js";
import { loadImage, replaceShimmerContent } from "../utils/dom.js";
import { Cart } from "../cart/cart.js";
import { toDisplayCost } from "../utils/currency.js";

/**
 * Page for displaying main page content, e.g. cafe info, categories, some menu sections.
 */
export class MainPage extends Route {
    #dayOrder = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
    #dayLabels = { mon: 'Пн', tue: 'Вт', wed: 'Ср', thu: 'Чт', fri: 'Пт', sat: 'Сб', sun: 'Вс' };

    constructor() {
        super('root', '/pages/main.html')
    }

    load(params) {
        const portionCount = Cart.getPortionCount()
        if (portionCount > 0) {
            TelegramSDK.showMainButton(
                `MY CART • ${this.#getDisplayPositionCount(portionCount)}`,
                () => navigateTo('cart')
            )
        } else {
            TelegramSDK.hideMainButton();
        }
        
        this.#loadCafeInfo()
        this.#loadCategories();
        this.#loadPopularMenu();
        this.#setupLanguageSelector();
        this.#setupCurrencySelector();
        this.#renderMobileCartCta();
        Cart.onItemsChangeListener = () => this.#renderMobileCartCta();
    }

    onClose() {
        Cart.onItemsChangeListener = null;
    }

    #setupCurrencySelector() {
        const selector = $('#currency-selector');
        if (!selector || selector.length === 0) {
            return;
        }
        const current = localStorage.getItem('preferredCurrency') || 'KZT';
        this.#setActiveSegment(selector, 'currency', current);
        selector.off('click', 'button').on('click', 'button', (event) => {
            event.preventDefault();
            const next = String($(event.currentTarget).data('currency') || 'KZT').toUpperCase();
            localStorage.setItem('preferredCurrency', next);
            this.#setActiveSegment(selector, 'currency', next);
            this.#loadCategories();
            this.#loadPopularMenu();
        });
    }

    #setupLanguageSelector() {
        const selector = $('#language-selector');
        if (!selector || selector.length === 0) {
            return;
        }
        const tgLang = String(window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code || '').slice(0, 2).toLowerCase();
        const current = (localStorage.getItem('preferredLang') || tgLang || 'ru').toLowerCase();
        const nextLang = current === 'kk' || current === 'en' ? current : 'ru';
        this.#setActiveSegment(selector, 'lang', nextLang);
        selector.off('click', 'button').on('click', 'button', (event) => {
            event.preventDefault();
            const next = String($(event.currentTarget).data('lang') || 'ru').toLowerCase();
            localStorage.setItem('preferredLang', next);
            this.#setActiveSegment(selector, 'lang', next);
            this.#loadCafeInfo();
            this.#loadCategories();
            this.#loadPopularMenu();
        });
    }

    #setActiveSegment(selector, type, activeValue) {
        selector.find('button').each((_, element) => {
            const button = $(element);
            const value = String(button.data(type) || '').toUpperCase();
            const target = String(activeValue || '').toUpperCase();
            button.toggleClass('active', value === target);
            button.attr('aria-selected', value === target ? 'true' : 'false');
        });
    }

    #renderMobileCartCta() {
        const cartCta = $('#mobile-cart-cta');
        if (!cartCta || cartCta.length === 0) {
            return;
        }
        const cartItems = Cart.getItems();
        if (cartItems.length === 0) {
            cartCta.hide();
            return;
        }
        const totalCount = Cart.getPortionCount();
        const totalCost = cartItems.reduce((sum, item) => sum + item.variant.cost * item.quantity, 0);
        const currency = cartItems[0]?.variant?.currency || 'KZT';
        cartCta.text(`${totalCount} items · ${toDisplayCost(totalCost, currency)} · Open cart`);
        cartCta.off('click').on('click', () => navigateTo('cart'));
        cartCta.show();
    }

    #loadCafeInfo() {
        get('/info', (cafeInfo) => {
            this.#fillCafeInfo(cafeInfo);
        });
    }
    
    #loadCategories() {
        get('/categories', (categories) => {
            this.#fillCategories(categories);
        })
    }
    
    #loadPopularMenu() {
        get('/menu/popular', (popularMenu) => {
            this.#fillPopularMenu(popularMenu);
        });
    }
    
    #fillCafeInfo(cafeInfo) {
        loadImage($('#cafe-logo'), cafeInfo.logoImage);
        loadImage($('#cafe-cover'), cafeInfo.coverImage);

        const cafeInfoTemplate = $('#cafe-info-template').html();
        const filledCafeInfoTemplate = $(cafeInfoTemplate);
        filledCafeInfoTemplate.find('#cafe-name').text(cafeInfo.name);
        filledCafeInfoTemplate.find('#cafe-kitchen-categories').text(cafeInfo.kitchenCategories);
        filledCafeInfoTemplate.find('#cafe-rating').text(cafeInfo.rating);
        filledCafeInfoTemplate.find('#cafe-cooking-time').text(cafeInfo.cookingTime);
        filledCafeInfoTemplate.find('#cafe-status').text(cafeInfo.status);
        this.#fillWorkingHours(filledCafeInfoTemplate, cafeInfo.workingHours || {});
        $('#cafe-info').empty();
        $('#cafe-info').append(filledCafeInfoTemplate);
    }

    #fillWorkingHours(container, workingHours) {
        const normalized = this.#normalizeWorkingHours(workingHours);
        const nowStatus = this.#buildNowStatus(normalized);
        container.find('#cafe-working-hours-now').text(nowStatus);
        const list = container.find('#cafe-working-hours-list');
        list.empty();
        const dayKeys = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
        const todayKey = dayKeys[new Date().getDay()];
        const today = normalized[todayKey];
        const todayLabel = this.#dayLabels[todayKey] || 'Сегодня';
        const todayText = today && today.isOpen ? `${today.openAt}-${today.closeAt}` : 'Выходной';
        list.append(`<div class="cafe-working-hours-row"><span>${todayLabel}</span><strong>${todayText}</strong></div>`);
    }

    #normalizeWorkingHours(workingHours) {
        const result = {};
        this.#dayOrder.forEach((day) => {
            const value = workingHours?.[day] || {};
            result[day] = {
                isOpen: Boolean(value.isOpen),
                openAt: value.openAt || '09:00',
                closeAt: value.closeAt || '22:00',
            };
        });
        return result;
    }

    #buildNowStatus(workingHours) {
        const dayKeys = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
        const now = new Date();
        const todayKey = dayKeys[now.getDay()];
        const today = workingHours[todayKey];
        if (!today || !today.isOpen) return 'Сейчас закрыто';

        const current = now.getHours() * 60 + now.getMinutes();
        const [openH, openM] = String(today.openAt || '09:00').split(':').map(Number);
        const [closeH, closeM] = String(today.closeAt || '22:00').split(':').map(Number);
        const openMinutes = (openH * 60) + openM;
        const closeMinutes = (closeH * 60) + closeM;

        if (current >= openMinutes && current < closeMinutes) {
            return `Открыто сейчас · до ${today.closeAt}`;
        }
        return `Сейчас закрыто · откроется в ${today.openAt}`;
    }
    
    #fillCategories(categories) {
        $('#cafe-section-categories-title').removeClass('shimmer');
        replaceShimmerContent(
            '#cafe-categories',
            '#cafe-category-template',
            '#cafe-category-icon',
            categories,
            (template, cafeCategory) => {
                template.attr('id', cafeCategory.id);
                template.css('background-color', cafeCategory.backgroundColor);
                template.find('#cafe-category-icon').attr('src', cafeCategory.icon || 'icons/icon-transparent.svg');
                template.find('#cafe-category-name').text(cafeCategory.name);
                template.on('click', () => {
                    const params = JSON.stringify({'id': cafeCategory.id});
                    navigateTo('category', params);
                });
            }
        )
    }
    
    #fillPopularMenu(popularMenu) {
        $('#cafe-section-popular-title').removeClass('shimmer');
        replaceShimmerContent(
            '#cafe-section-popular',
            '#cafe-item-template',
            '#cafe-item-image',
            popularMenu,
            (template, cafeItem) => {
                template.attr('id', cafeItem.name);
                loadImage(template.find('#cafe-item-image'), cafeItem.image || 'icons/icon-transparent.svg');
                template.find('#cafe-item-name').text(cafeItem.name);
                template.find('#cafe-item-description').text(cafeItem.description);
                template.on('click', () => {
                    const params = JSON.stringify({'id': cafeItem.id});
                    navigateTo('details', params);
                });
            }
        )
    }

    #getDisplayPositionCount(positionCount) {
        return positionCount == 1 ? `${positionCount} POSITION` : `${positionCount} POSITIONS`;
    }

}
