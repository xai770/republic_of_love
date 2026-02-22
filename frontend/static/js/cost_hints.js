/**
 * cost_hints.js — Transparent AI compute-cost hints
 *
 * Shows yogis what each AI action costs Talent Yoga to operate.
 * This is NOT what we charge — it's what it actually costs us.
 * Purpose: shared reality, not billing justification.
 *
 * Compute costs from billing_assumptions.yaml Section D.
 * Update when hardware or models change.
 */
(function () {
    'use strict';

    // Real compute cost per event type (in EUR, from GPU amortization + electricity)
    const COMPUTE_COSTS = {
        mira_message:  0.003,   // ~1.3 sec inference
        cv_extraction: 0.05,    // ~22 sec multi-pass
        cover_letter:  0.03,    // ~13 sec generation
        match_report:  0.02,    // ~9 sec analysis
        profile_embed: 0.002,   // ~0.8 sec embedding
    };

    /**
     * Format a cost value as a human-readable string.
     * €0.003 → "less than 1 cent"
     * €0.05  → "about 5 cents"
     * €0.22  → "about €0.22"
     */
    function formatComputeCost(eurValue) {
        if (eurValue < 0.01) return { en: 'less than 1 cent', de: 'weniger als 1 Cent' };
        const cents = Math.round(eurValue * 100);
        if (cents === 1) return { en: 'about 1 cent', de: 'etwa 1 Cent' };
        if (cents < 100) return { en: `about ${cents} cents`, de: `etwa ${cents} Cent` };
        return {
            en: `about €${eurValue.toFixed(2)}`,
            de: `etwa ${eurValue.toFixed(2).replace('.', ',')} €`,
        };
    }

    /**
     * Create a cost-hint DOM element.
     * Returns a <span> with class "cost-hint" styled subtly.
     */
    function createHintElement(eventType, lang) {
        lang = lang || (document.documentElement.lang === 'en' ? 'en' : 'de');
        const cost = COMPUTE_COSTS[eventType];
        if (cost === undefined) return null;

        const label = formatComputeCost(cost);
        const text = lang === 'en'
            ? `⚡ This cost Talent Yoga ${label.en} to compute`
            : `⚡ Das hat Talent Yoga ${label.de} Rechenleistung gekostet`;

        const span = document.createElement('span');
        span.className = 'cost-hint';
        span.textContent = text;
        span.title = lang === 'en'
            ? 'Real infrastructure cost — we show this for transparency, not billing.'
            : 'Echte Infrastrukturkosten — wir zeigen dies aus Transparenz, nicht zur Abrechnung.';
        return span;
    }

    /**
     * Create a cost-hint for a combined action (e.g. match_report + cover_letter).
     */
    function createCombinedHint(eventTypes, lang) {
        lang = lang || (document.documentElement.lang === 'en' ? 'en' : 'de');
        let total = 0;
        for (const et of eventTypes) {
            total += COMPUTE_COSTS[et] || 0;
        }
        if (total === 0) return null;

        const label = formatComputeCost(total);
        const text = lang === 'en'
            ? `⚡ This cost Talent Yoga ${label.en} to compute`
            : `⚡ Das hat Talent Yoga ${label.de} Rechenleistung gekostet`;

        const span = document.createElement('span');
        span.className = 'cost-hint';
        span.textContent = text;
        span.title = lang === 'en'
            ? 'Real infrastructure cost — we show this for transparency, not billing.'
            : 'Echte Infrastrukturkosten — wir zeigen dies aus Transparenz, nicht zur Abrechnung.';
        return span;
    }

    /**
     * Sum the compute cost for a list of usage events.
     * events: [{event_type: 'mira_message', ...}, ...]
     * Returns total in EUR.
     */
    function sumComputeCosts(events) {
        let total = 0;
        for (const ev of events) {
            total += COMPUTE_COSTS[ev.event_type] || 0;
        }
        return total;
    }

    // Inject minimal styles if not already present
    if (!document.getElementById('cost-hint-styles')) {
        const style = document.createElement('style');
        style.id = 'cost-hint-styles';
        style.textContent = `
            .cost-hint {
                display: inline-block;
                font-size: 11px;
                color: #94a3b8;
                margin-top: 4px;
                letter-spacing: 0.01em;
                cursor: help;
            }
            .cost-hint:hover {
                color: #64748b;
            }
            .cost-hint-block {
                display: block;
                text-align: right;
                margin-top: 2px;
            }
        `;
        document.head.appendChild(style);
    }

    // Public API
    window.CostHints = {
        COMPUTE_COSTS: COMPUTE_COSTS,
        format: formatComputeCost,
        create: createHintElement,
        createCombined: createCombinedHint,
        sum: sumComputeCosts,
    };
})();
