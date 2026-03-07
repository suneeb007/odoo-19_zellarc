(function () {
    "use strict";

    function updateStatButtons(root) {
        root = root || document;
        // Ensure we have an Element to call querySelectorAll on. MutationObserver
        // can pass Text nodes or other node types where querySelectorAll
        // isn't available. Fallback to the parent element or document.
        var elRoot = root;
        if (!elRoot || typeof elRoot.querySelectorAll !== 'function') {
            if (elRoot && elRoot.nodeType === Node.TEXT_NODE && elRoot.parentElement) {
                elRoot = elRoot.parentElement;
            } else if (elRoot && elRoot.nodeType === Node.ELEMENT_NODE) {
                // already good
            } else {
                elRoot = document;
            }
        }
        var nodes = elRoot.querySelectorAll('.oe_stat_button .o_stat_value');
        nodes.forEach(function (node) {
            var txt = (node.textContent || '').trim();
            var n = parseInt(txt, 10);
            node.classList.remove('stat-zero', 'stat-positive');
            if (!isNaN(n)) {
                if (n === 0) {
                    node.classList.add('stat-zero');
                } else if (n >= 1) {
                    node.classList.add('stat-positive');
                }
            }
        });
    }

    function init() {
        // initial run
        updateStatButtons(document);

        // observe changes to stat buttons (counts update dynamically)
        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (m) {
                if (m.type === 'childList' || m.type === 'characterData' || m.type === 'subtree') {
                    updateStatButtons(m.target);
                }
            });
        });
        observer.observe(document.body, { subtree: true, childList: true, characterData: true });
        // also update on ajax complete (fallback)
        document.addEventListener('DOMContentLoaded', function () { updateStatButtons(document); });
    }

    // wait for the web client to be ready
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(init, 0);
    } else {
        document.addEventListener('DOMContentLoaded', init);
    }
})();
