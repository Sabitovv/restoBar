/**
 * Create items from the provided data and template and append them to container,
 * when all child image are loaded. This function was developed specifically for the lists
 * with images.
 * @param {string} containerSelector The selector of the parent container, where items should be placed.
 * @param {string} templateSelector The selector of the item's <template>.
 * @param {string} loadableImageSelector The selector for the image placed somewher in <template>.
 * @param {Array} data Array of items.
 * @param {*} templateSetup Lambda for custom template filling, e.g. setting CSS, text, etc.
 */
export function replaceShimmerContent(containerSelector, templateSelector, loadableImageSelector, data, templateSetup) {
    if (!Array.isArray(data) || data.length === 0) {
        fillContainer(containerSelector, []);
        return;
    }

    let templateHtml = $(templateSelector).html();
    let imageLoaded = 0;
    const imageShouldBeLoaded = data.length;
    let filledTemplates = [];

    const markReady = () => {
        imageLoaded++;
        if (imageLoaded >= imageShouldBeLoaded) {
            fillContainer(containerSelector, filledTemplates);
        }
    };

    data.forEach(dataItem => {
        let filledTemplate = $(templateHtml);
        templateSetup(filledTemplate, dataItem);

        const imageElement = filledTemplate.find(loadableImageSelector);
        const src = imageElement.attr('src');

        imageElement.on('load', markReady);
        imageElement.on('error', markReady);

        if (!src) {
            markReady();
        }

        filledTemplates.push(filledTemplate);
    });
}

/**
 * Replace existing container elements with the new ones.
 * @param {string} selector Parent container selector.
 * @param {*} elements Instances of elements in any format, supported by jQuery.append() method.
 */
export function fillContainer(selector, elements) {
    let container = $(selector);
    container.empty();
    elements.forEach(el => container.append(el));
}

/**
 * Load image with shimmer effect while loading.
 * @param {*} imageElement jQuery element of the image.
 * @param {*} imageUrl Image URL to load.
 */
export function loadImage(imageElement, imageUrl) {
    if (imageElement != null) {
        if (!imageElement.hasClass('shimmer')) {
            imageElement.addClass('shimmer');
        }
        imageElement.attr('src', imageUrl);
        imageElement.on('load', () => imageElement.removeClass('shimmer'));
    }
}
