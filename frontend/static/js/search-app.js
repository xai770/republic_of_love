/**
 * search-app.js — Search page application logic
 * Extracted from search.html to separate Jinja config injection from JS logic.
 * Config injected via window.SearchConfig (set inline in search.html).
 */
(function() {
    const LANG = window.SearchConfig.lang;
    const I18N = window.SearchConfig.i18n;

    // Translate a domain name from API (German) to current language
    function tDomain(name) { return I18N.domains[name] || name; }
    // Translate a QL level to current language
    function tQL(level) { return I18N.ql[level] || ('Level ' + level); }
    // Translate a Bundesland name to current language
    const BUNDESLAND_EN = {
        'Baden-Württemberg': 'Baden-Württemberg',
        'Bayern': 'Bavaria',
        'Berlin': 'Berlin',
        'Brandenburg': 'Brandenburg',
        'Bremen': 'Bremen',
        'Hamburg': 'Hamburg',
        'Hessen': 'Hesse',
        'Mecklenburg-Vorpommern': 'Mecklenburg-Vorpommern',
        'Niedersachsen': 'Lower Saxony',
        'Nordrhein-Westfalen': 'North Rhine-Westphalia',
        'Rheinland-Pfalz': 'Rhineland-Palatinate',
        'Saarland': 'Saarland',
        'Sachsen': 'Saxony',
        'Sachsen-Anhalt': 'Saxony-Anhalt',
        'Schleswig-Holstein': 'Schleswig-Holstein',
        'Thüringen': 'Thuringia',
        'Sonstiges': 'Other',
    };
    function tState(name) { return LANG === 'en' ? (BUNDESLAND_EN[name] || name) : name; }

    // ============================================================
    // STATE
    // ============================================================
    const STORAGE_KEY = 'turing_search_state';

    const state = {
        domains: [],     // selected KLDB 2-digit codes
        ql: [],          // selected QL levels [1-4]
        geoLocations: [],   // [{lat, lon, radius_km, label}] — supports multiple cities
        professions: [],     // berufenet_name strings clicked from sector tree
        // data from last response
        data: null,
        // profile scope (inferred from CV — used for /enrich scoring)
        profileId: null,
        // Bundesland filter
        states: [],
        // City filter (hierarchical: selected via location tree)
        cities: [],       // [{state, city}] selected city entries
        // Tree data caches
        sectorTree: null,
        locationTree: null,
        // Tree open/collapsed states
        openSectors: new Set(),
        openStates: new Set(),
        // Sort state for trees {field: 'name'|'count', dir: 'asc'|'desc'}
        sectorSort: { field: 'count', dir: 'desc' },
        locationSort: { field: 'count', dir: 'desc' },
        // Tab state
        activeTab: 'situation',
        // Situation questionnaire answers {confidence, openness, hours, environment, intention}
        situationContext: {},
        // Direction tile zoom state: null = all sectors, sectorName = zoomed in
        directionZoom: null,
    };

    /** Persist filter-relevant parts of state to localStorage. */
    function saveState() {
        try {
            const snap = {
                domains: state.domains,
                ql: state.ql,
                geoLocations: state.geoLocations,
                professions: state.professions,
                states: state.states,
                cities: state.cities,
                activeTab: state.activeTab,
                _ts: Date.now(),
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(snap));
        } catch(e) { /* quota / private-mode */ }
    }

    /**
     * Restore filter state from localStorage.
     * Returns true if meaningful filters were restored.
     */
    function restoreState() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return false;
            const snap = JSON.parse(raw);
            // Expire after 24 hours of inactivity
            if (snap._ts && (Date.now() - snap._ts > 24 * 60 * 60 * 1000)) {
                localStorage.removeItem(STORAGE_KEY);
                return false;
            }
            let restored = false;
            if (snap.domains && snap.domains.length)       { state.domains = snap.domains; restored = true; }
            if (snap.ql && snap.ql.length)                 { state.ql = snap.ql; restored = true; }
            if (snap.geoLocations && snap.geoLocations.length) { state.geoLocations = snap.geoLocations; restored = true; }
            if (snap.professions && snap.professions.length)   { state.professions = snap.professions; restored = true; }
            if (snap.states && snap.states.length)         { state.states = snap.states; restored = true; }
            if (snap.cities && snap.cities.length)         { state.cities = snap.cities; restored = true; }
            if (snap.activeTab) state.activeTab = snap.activeTab;
            return restored;
        } catch(e) { return false; }
    }

    // ============================================================
    // TAB SWITCHING
    // ============================================================
    const VALID_TABS = ['situation', 'direction', 'level', 'location', 'opportunities', 'power'];
    let mapNeedsInvalidate = true;  // first switch to location/power must fix Leaflet

    function switchTab(tabName) {
        if (!VALID_TABS.includes(tabName)) return;
        state.activeTab = tabName;

        // Update tab buttons
        document.querySelectorAll('.search-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        // Update tab content panels
        document.querySelectorAll('.tab-content').forEach(panel => {
            panel.classList.toggle('active', panel.dataset.tab === tabName);
        });

        // Fix Leaflet when map becomes visible (location or power tab)
        if ((tabName === 'location' || tabName === 'power') && typeof map !== 'undefined' && map) {
            setTimeout(() => {
                const mapEl = document.getElementById('search-map');
                if (!mapEl || mapEl.offsetWidth === 0) return;
                map.invalidateSize();
                map.setView(map.getCenter());
                // Re-render heatmap/markers now that canvas has real dimensions
                if (state.data) {
                    try { renderHeatmap(state.data.heatmap); } catch(_) {}
                    try { renderMarkers(state.data.markers); } catch(_) {}
                    try { renderBundeslandOverlay(); } catch(_) {}
                }
            }, 100);
            // Second pass for slow layouts
            setTimeout(() => {
                const mapEl = document.getElementById('search-map');
                if (mapEl && mapEl.offsetWidth > 0) map.invalidateSize();
            }, 500);
            mapNeedsInvalidate = false;
        }

        saveState();
    }

    // Wire tab bar clicks (event delegation)
    document.getElementById('search-tabs').addEventListener('click', function(e) {
        const tab = e.target.closest('.search-tab');
        if (!tab) return;
        switchTab(tab.dataset.tab);
    });

    // ============================================================
    // SITUATION QUESTIONNAIRE
    // ============================================================
    const SQ_QUESTIONS = ['search_mode', 'field_change', 'intention'];

    async function loadSituationContext() {
        try {
            const res = await fetch('/api/search/situation');
            if (!res.ok) return;
            const data = await res.json();
            state.situationContext = data || {};
            renderSituationCards();
        } catch(e) {
            console.warn('Failed to load situation context:', e);
        }
    }

    async function saveSituationAnswer(question, value) {
        state.situationContext[question] = value;
        renderSituationCards();
        try {
            await fetch('/api/search/situation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [question]: value }),
            });
        } catch(e) {
            console.warn('Failed to save situation answer:', e);
        }
    }

    function renderSituationCards() {
        SQ_QUESTIONS.forEach(q => {
            const card = document.getElementById('sq-' + q);
            const collapsed = document.getElementById('sqc-' + q);
            const expanded = document.getElementById('sqe-' + q);
            const valueEl = document.getElementById('sqv-' + q);
            const checkEl = card ? card.querySelector('.sq-check') : null;
            if (!card) return;

            const val = state.situationContext[q];
            const hasAnswer = val != null && val !== '';

            card.classList.toggle('answered', hasAnswer);
            if (checkEl) checkEl.textContent = hasAnswer ? '✓' : '○';

            // Update summary value from the selected option text
            if (hasAnswer && valueEl) {
                const optBtn = expanded ? expanded.querySelector(`.sq-option[data-value="${val}"]`) : null;
                valueEl.textContent = optBtn ? optBtn.textContent.trim() : val;
            } else if (valueEl) {
                valueEl.textContent = '—';
            }

            // Mark selected option
            if (expanded) {
                expanded.querySelectorAll('.sq-option').forEach(btn => {
                    btn.classList.toggle('selected', btn.dataset.value === String(val));
                });
            }
        });
    }

    function expandSituationCard(question) {
        SQ_QUESTIONS.forEach(q => {
            const collapsed = document.getElementById('sqc-' + q);
            const expanded = document.getElementById('sqe-' + q);
            if (!collapsed || !expanded) return;
            if (q === question) {
                collapsed.style.display = 'none';
                expanded.style.display = '';
            } else {
                collapsed.style.display = '';
                expanded.style.display = 'none';
            }
        });
    }

    function collapseSituationCard(question) {
        const collapsed = document.getElementById('sqc-' + question);
        const expanded = document.getElementById('sqe-' + question);
        if (collapsed) collapsed.style.display = '';
        if (expanded) expanded.style.display = 'none';
    }

    function advanceToNextQuestion(currentQuestion) {
        const idx = SQ_QUESTIONS.indexOf(currentQuestion);
        // Find the next unanswered question
        for (let i = idx + 1; i < SQ_QUESTIONS.length; i++) {
            if (state.situationContext[SQ_QUESTIONS[i]] == null) {
                expandSituationCard(SQ_QUESTIONS[i]);
                return;
            }
        }
        // All answered — collapse current
        collapseSituationCard(currentQuestion);
    }

    // Wire situation card interactions (event delegation on the container)
    const situationContainer = document.querySelector('.situation-container');
    if (situationContainer) {
        // Click an option
        situationContainer.addEventListener('click', function(e) {
            const optBtn = e.target.closest('.sq-option');
            if (optBtn) {
                const question = optBtn.closest('.sq-options').dataset.question;
                const value = optBtn.dataset.value;
                saveSituationAnswer(question, value);
                // Collapse this card and advance to next
                setTimeout(() => advanceToNextQuestion(question), 200);
                return;
            }

            // Click skip
            const skipBtn = e.target.closest('.sq-skip');
            if (skipBtn) {
                const card = skipBtn.closest('.situation-card');
                if (card) {
                    const question = card.dataset.question;
                    collapseSituationCard(question);
                    advanceToNextQuestion(question);
                }
                return;
            }

            // Click adjust button → expand this card
            const adjustBtn = e.target.closest('.sq-adjust');
            if (adjustBtn) {
                const card = adjustBtn.closest('.situation-card');
                if (card) expandSituationCard(card.dataset.question);
                return;
            }

            // Click collapsed row → expand this card
            const collapsedRow = e.target.closest('.sq-collapsed');
            if (collapsedRow) {
                const card = collapsedRow.closest('.situation-card');
                if (card) expandSituationCard(card.dataset.question);
                return;
            }
        });
    }

    // ============================================================
    // MAP SETUP
    // ============================================================
    const map = L.map('search-map', {
        center: [51.1657, 10.4515],  // Germany center
        zoom: 6,
        zoomControl: true,
        scrollWheelZoom: true,
    });

    // Tile layer — OpenStreetMap.DE (German labels)
    const tileUrl = 'https://tile.openstreetmap.de/{z}/{x}/{y}.png';
    let tileLayer = L.tileLayer(tileUrl, {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> Mitwirkende',
        maxZoom: 18,
    }).addTo(map);

    // Dedicated pane for heatmap — semi-transparent so tiles show through
    map.createPane('heatPane');
    map.getPane('heatPane').style.zIndex = 350;
    map.getPane('heatPane').style.opacity = '0.45';

    let heatLayer = null;
    let geoLayers = [];   // [{marker, circle}] parallel to state.geoLocations
    let markerLayer = null;

    // Click on map = ADD a new geo location (multi-location support)
    map.on('click', async function(e) {
        const lat = Math.round(e.latlng.lat * 100) / 100;
        const lon = Math.round(e.latlng.lng * 100) / 100;
        const radius_km = parseInt(document.getElementById('radius-select').value) || null;
        state.geoLocations.push({lat, lon, radius_km, label: `${lat}, ${lon}`});
        updateGeoLayers();
        doSearch();
    });

    function updateGeoLayers() {
        // Remove all existing geo layers from the map
        geoLayers.forEach(({marker, circle}) => {
            if (marker) map.removeLayer(marker);
            if (circle) map.removeLayer(circle);
        });
        geoLayers = [];
        state.geoLocations.forEach(g => {
            const marker = L.circleMarker([g.lat, g.lon], {
                radius: 6, color: '#e74c3c', fillColor: '#e74c3c', fillOpacity: 0.8, weight: 2
            }).addTo(map);
            let circle = null;
            if (g.radius_km) {
                circle = L.circle([g.lat, g.lon], {
                    radius: g.radius_km * 1000,
                    color: '#3498db', fillColor: '#3498db', fillOpacity: 0.08,
                    weight: 2, dashArray: '5,5'
                }).addTo(map);
            }
            geoLayers.push({marker, circle});
        });
    }

    // Radius dropdown change — applies to all active geo locations
    document.getElementById('radius-select').addEventListener('change', async function() {
        const radius_km = parseInt(this.value) || null;
        // Keep power tab dropdown in sync
        const rp = document.getElementById('radius-select-power');
        if (rp) rp.value = this.value;
        state.geoLocations = state.geoLocations.map(g => ({...g, radius_km}));
        updateGeoLayers();
        if (state.geoLocations.length > 0) {
            doSearch();
        }
    });

    // ============================================================
    // CITY SEARCH (simple geocoding via Nominatim)
    // ============================================================
    let cityTimeout = null;
    const cityInput = document.getElementById('city-search');
    const cityDropdown = document.createElement('div');
    cityDropdown.className = 'city-dropdown';
    cityInput.parentElement.appendChild(cityDropdown);

    cityInput.addEventListener('input', function() {
        clearTimeout(cityTimeout);
        const q = this.value.trim();
        if (q.length < 2) { cityDropdown.innerHTML = ''; return; }
        cityTimeout = setTimeout(() => geocodeCity(q), 400);
    });

    async function geocodeCity(q) {
        try {
            const res = await fetch(`/api/geo/search?q=${encodeURIComponent(q)}`);
            const results = await res.json();
            cityDropdown.innerHTML = results.map(r =>
                `<div class="city-option" data-lat="${r.lat}" data-lon="${r.lon}">${r.display_name.split(',').slice(0,2).join(',')}</div>`
            ).join('');
        } catch(e) {
            cityDropdown.innerHTML = '';
        }
    }

    cityDropdown.addEventListener('click', async function(e) {
        const opt = e.target.closest('.city-option');
        if (!opt) return;
        const lat   = parseFloat(opt.dataset.lat);
        const lon   = parseFloat(opt.dataset.lon);
        const radius_km = parseInt(document.getElementById('radius-select').value) || 50;
        const label = opt.textContent.trim();
        state.geoLocations.push({lat, lon, radius_km, label});
        cityInput.value = '';    // clear input — ready for a second city
        cityDropdown.innerHTML = '';
        map.setView([lat, lon], 10);
        updateGeoLayers();
        doSearch();
    });

    // Close dropdown on outside click
    document.addEventListener('click', function(e) {
        if (!cityInput.contains(e.target) && !cityDropdown.contains(e.target)) {
            cityDropdown.innerHTML = '';
        }
        // Also close power tab dropdown
        if (cityInputPower && !cityInputPower.contains(e.target) && !cityDropdownPower.contains(e.target)) {
            cityDropdownPower.innerHTML = '';
        }
    });

    // ============================================================
    // POWER TAB — city search + radius (mirrors primary controls)
    // ============================================================
    const cityInputPower = document.getElementById('city-search-power');
    const radiusSelectPower = document.getElementById('radius-select-power');
    let cityDropdownPower = null;
    let cityTimeoutPower = null;

    if (cityInputPower) {
        cityDropdownPower = document.createElement('div');
        cityDropdownPower.className = 'city-dropdown';
        cityInputPower.parentElement.appendChild(cityDropdownPower);

        cityInputPower.addEventListener('input', function() {
            clearTimeout(cityTimeoutPower);
            const q = this.value.trim();
            if (q.length < 2) { cityDropdownPower.innerHTML = ''; return; }
            cityTimeoutPower = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/geo/search?q=${encodeURIComponent(q)}`);
                    const results = await res.json();
                    cityDropdownPower.innerHTML = results.map(r =>
                        `<div class="city-option" data-lat="${r.lat}" data-lon="${r.lon}">${r.display_name.split(',').slice(0,2).join(',')}</div>`
                    ).join('');
                } catch(e) {
                    cityDropdownPower.innerHTML = '';
                }
            }, 400);
        });

        cityDropdownPower.addEventListener('click', function(e) {
            const opt = e.target.closest('.city-option');
            if (!opt) return;
            const lat = parseFloat(opt.dataset.lat);
            const lon = parseFloat(opt.dataset.lon);
            const radius_km = parseInt((radiusSelectPower || document.getElementById('radius-select')).value) || 50;
            const label = opt.textContent.trim();
            state.geoLocations.push({lat, lon, radius_km, label});
            cityInputPower.value = '';
            cityDropdownPower.innerHTML = '';
            map.setView([lat, lon], 10);
            updateGeoLayers();
            doSearch();
        });
    }

    if (radiusSelectPower) {
        radiusSelectPower.addEventListener('change', function() {
            const radius_km = parseInt(this.value) || null;
            // Keep primary dropdown in sync
            document.getElementById('radius-select').value = this.value;
            state.geoLocations = state.geoLocations.map(g => ({...g, radius_km}));
            updateGeoLayers();
            if (state.geoLocations.length > 0) doSearch();
        });
    }

    // ============================================================
    // QL STRIP (compact horizontal bar — top of left panel)
    // ============================================================
    const QL_COLORS = { 1: '#95a5a6', 2: '#3498db', 3: '#e67e22', 4: '#e74c3c', 0: '#999' };

    function renderQLStrip(levels) {
        const locale = LANG === 'de' ? 'de-DE' : 'en-US';
        const html = (!levels || levels.length === 0) ? '' : levels.filter(l => l.level > 0).map(l => {
            const selected = state.ql.length === 0 || state.ql.includes(l.level);
            const dimmed = state.ql.length > 0 && !selected;
            const color = QL_COLORS[l.level] || '#999';
            return `<button class="ql-chip ${dimmed ? 'dimmed' : ''} ${selected && state.ql.length > 0 ? 'selected' : ''}"
                     data-level="${l.level}" style="--ql-color:${color}">
                <span class="ql-chip-dot" style="background:${color}"></span>
                <span class="ql-chip-label">${tQL(l.level)}</span>
                <span class="ql-chip-count">${l.count.toLocaleString(locale)}</span>
            </button>`;
        }).join('');
        // Render to both primary (tab 3) and power (tab 6) QL strips
        ['ql-strip', 'ql-strip-power'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = html;
        });
    }

    // QL chip click handler — shared by both strips (event delegation)
    function handleQLClick(e) {
        const chip = e.target.closest('.ql-chip');
        if (!chip) return;
        const level = parseInt(chip.dataset.level);
        const idx = state.ql.indexOf(level);
        if (idx >= 0) { state.ql.splice(idx, 1); } else { state.ql.push(level); }
        doSearch();
    }
    document.getElementById('ql-strip').addEventListener('click', handleQLClick);
    const qlPower = document.getElementById('ql-strip-power');
    if (qlPower) qlPower.addEventListener('click', handleQLClick);

    // ============================================================
    // SECTOR TREE (left panel — sector→profession hierarchy)
    // ============================================================
    function renderSectorTree(data) {
        if (!data) return;
        state.sectorTree = data;
        const locale = LANG === 'de' ? 'de-DE' : 'en-US';
        const searchVal = (document.getElementById('sector-search').value || '').toLowerCase();

        let sectors = [...data.sectors];

        // Apply search filter
        if (searchVal) {
            sectors = sectors.map(s => {
                const nameMatch = tDomain(s.name).toLowerCase().includes(searchVal);
                const filteredProfs = s.professions.filter(p => {
                    const pName = (LANG === 'en' && p.name_en) ? p.name_en : p.name;
                    return pName.toLowerCase().includes(searchVal);
                });
                if (nameMatch || filteredProfs.length > 0) {
                    return { ...s, professions: nameMatch ? s.professions : filteredProfs };
                }
                return null;
            }).filter(Boolean);
        }

        // Apply sort
        const { field, dir } = state.sectorSort;
        sectors.sort((a, b) => {
            let cmp = field === 'name'
                ? tDomain(a.name).localeCompare(tDomain(b.name))
                : b.count - a.count;
            return dir === 'asc' ? -cmp : cmp;
        });

        let html = '';
        if (sectors.length === 0) {
            html = '<div class="panel-empty">—</div>';
        } else {
            const allInScope = state.domains.length === 0;
            html = sectors.map(s => {
                const selected = !allInScope && s.codes.some(c => state.domains.includes(c));
                const dimmed = !allInScope && !selected;
                const isOpen = state.openSectors.has(s.name) || (searchVal && !dimmed);
                const tint = allInScope ? 'tint-all' : '';

                let profsHtml = '';
                if (isOpen) {
                    let profs = [...s.professions];
                    profs.sort((a, b) => field === 'name'
                        ? a.name.localeCompare(b.name)
                        : b.count - a.count);
                    if (dir === 'asc') profs.reverse();

                    profsHtml = profs.slice(0, 30).map(p => {
                        const pName = (LANG === 'en' && p.name_en) ? p.name_en : p.name;
                        const pSelected = state.professions.includes(p.name);
                        return `<div class="tree-child ${pSelected ? 'selected' : ''}" data-type="profession" data-name="${p.name}">
                            <span class="tree-child-name">${pName}</span>
                            <span class="tree-child-count">${p.count.toLocaleString(locale)}</span>
                        </div>`;
                    }).join('');
                    if (s.professions.length > 30) {
                        profsHtml += `<div class="tree-child tree-more">+${s.professions.length - 30} more</div>`;
                    }
                }

                return `<div class="tree-parent-group ${selected ? 'selected' : ''} ${dimmed ? 'dimmed' : ''} ${tint}">
                    <div class="tree-parent" data-type="sector" data-codes="${s.codes.join(',')}" data-name="${s.name}">
                        <span class="tree-chevron ${isOpen ? 'open' : ''}">${s.professions.length > 0 ? '▸' : ''}</span>
                        <span class="tree-dot" style="background:${s.color}"></span>
                        <span class="tree-parent-name">${tDomain(s.name)}</span>
                        <span class="tree-parent-count">${s.count.toLocaleString(locale)}</span>
                    </div>
                    <div class="tree-children ${isOpen ? 'open' : ''}">${profsHtml}</div>
                </div>`;
            }).join('');
        }

        // Render to power tab sector tree only (Direction tab uses tiles)
        const powerEl = document.getElementById('sector-tree-power');
        if (powerEl) powerEl.innerHTML = html;
    }

    // Sector tree click handler — shared
    function handleSectorTreeClick(e) {
        const parent = e.target.closest('.tree-parent');
        const child = e.target.closest('.tree-child');

        if (child && child.dataset.type === 'profession') {
            const name = child.dataset.name;
            const idx = state.professions.indexOf(name);
            if (idx >= 0) { state.professions.splice(idx, 1); } else { state.professions.push(name); }
            doSearch();
            return;
        }

        if (parent) {
            const chevron = parent.querySelector('.tree-chevron');
            if (e.target === chevron || e.target.closest('.tree-chevron')) {
                // Toggle expand/collapse
                const name = parent.dataset.name;
                if (state.openSectors.has(name)) { state.openSectors.delete(name); }
                else { state.openSectors.add(name); }
                renderSectorTree(state.sectorTree);
                return;
            }
            // Click on the row = toggle domain selection
            const codes = parent.dataset.codes.split(',');
            const allSelected = codes.every(c => state.domains.includes(c));
            if (allSelected) {
                state.domains = state.domains.filter(c => !codes.includes(c));
            } else {
                codes.forEach(c => { if (!state.domains.includes(c)) state.domains.push(c); });
            }
            doSearch();
        }
    }
    document.getElementById('sector-tree').addEventListener('click', handleSectorTreeClick);
    const sectorPower = document.getElementById('sector-tree-power');
    if (sectorPower) sectorPower.addEventListener('click', handleSectorTreeClick);

    // Sector search box
    document.getElementById('sector-search').addEventListener('input', function() {
        renderSectorTree(state.sectorTree);
        renderDirectionTiles();
    });
    const sectorSearchPower = document.getElementById('sector-search-power');
    if (sectorSearchPower) sectorSearchPower.addEventListener('input', function() {
        renderSectorTree(state.sectorTree);
    });

    // ============================================================
    // DIRECTION TILES (Tab 2 — two-level sector → profession grid)
    // ============================================================
    function renderDirectionTiles() {
        const data = state.sectorTree;
        if (!data) return;
        const tilesEl = document.getElementById('direction-tiles');
        const breadcrumb = document.getElementById('direction-breadcrumb');
        const crumbCurrent = document.getElementById('direction-crumb-current');
        if (!tilesEl) return;

        const locale = LANG === 'de' ? 'de-DE' : 'en-US';
        const searchVal = (document.getElementById('sector-search').value || '').toLowerCase();
        const allInScope = state.domains.length === 0;

        // Find the max count for proportional bars
        const maxCount = Math.max(...data.sectors.map(s => s.count), 1);

        if (state.directionZoom) {
            // --- Level 2: Professions in a sector ---
            const sector = data.sectors.find(s => s.name === state.directionZoom);
            if (!sector) {
                // Sector no longer in data (filter change) — reset to Level 1
                state.directionZoom = null;
                renderDirectionTiles();
                return;
            }

            breadcrumb.style.display = '';
            crumbCurrent.textContent = tDomain(sector.name);

            let profs = [...sector.professions];
            // Apply search filter to professions
            if (searchVal) {
                profs = profs.filter(p => {
                    const pName = (LANG === 'en' && p.name_en) ? p.name_en : p.name;
                    return pName.toLowerCase().includes(searchVal);
                });
            }
            // Sort by count descending
            profs.sort((a, b) => b.count - a.count);

            const sectorSelected = !allInScope && sector.codes.some(c => state.domains.includes(c));
            const profMax = Math.max(...profs.map(p => p.count), 1);

            // Sector header tile (select-all)
            let html = `<div class="direction-tile sector-header-tile ${sectorSelected ? 'selected' : ''}"
                              style="--dt-color:${sector.color}"
                              data-action="toggle-sector" data-codes="${sector.codes.join(',')}" data-name="${sector.name}">
                <span class="tree-dot" style="background:${sector.color}; width:10px; height:10px; border-radius:50%; flex-shrink:0;"></span>
                <span class="dt-name">${tDomain(sector.name)}</span>
                <span class="dt-stats">
                    <span class="dt-count">${sector.count.toLocaleString(locale)} ${I18N.direction_positions}</span>
                    ${sector.fresh ? `<span class="dt-fresh">+${sector.fresh} ${I18N.direction_new_this_week}</span>` : ''}
                </span>
                <span class="dt-select-label">${I18N.direction_select_all}</span>
            </div>`;

            if (profs.length === 0) {
                html += '<div class="panel-empty">—</div>';
            } else {
                html += profs.map(p => {
                    const pName = (LANG === 'en' && p.name_en) ? p.name_en : p.name;
                    const pSelected = state.professions.includes(p.name);
                    const pct = Math.max(2, Math.round(p.count / profMax * 100));
                    return `<div class="direction-tile prof-tile ${pSelected ? 'selected' : ''}"
                                 style="--dt-color:${sector.color}"
                                 data-action="toggle-profession" data-name="${p.name}">
                        <div class="dt-name">${pName}</div>
                        <div class="dt-stats">
                            <span class="dt-count">${p.count.toLocaleString(locale)}</span>
                            ${p.fresh ? `<span class="dt-fresh">+${p.fresh}</span>` : ''}
                        </div>
                        <div class="dt-bar-track"><div class="dt-bar-fill" style="width:${pct}%"></div></div>
                    </div>`;
                }).join('');
            }

            tilesEl.innerHTML = html;
        } else {
            // --- Level 1: All sectors ---
            breadcrumb.style.display = 'none';

            let sectors = [...data.sectors];
            // Apply search filter
            if (searchVal) {
                sectors = sectors.filter(s => {
                    const nameMatch = tDomain(s.name).toLowerCase().includes(searchVal);
                    const profMatch = s.professions.some(p => {
                        const pName = (LANG === 'en' && p.name_en) ? p.name_en : p.name;
                        return pName.toLowerCase().includes(searchVal);
                    });
                    return nameMatch || profMatch;
                });
            }
            // Sort by count descending
            sectors.sort((a, b) => b.count - a.count);

            if (sectors.length === 0) {
                tilesEl.innerHTML = '<div class="panel-empty">—</div>';
                return;
            }

            tilesEl.innerHTML = sectors.map(s => {
                const selected = !allInScope && s.codes.some(c => state.domains.includes(c));
                const dimmed = !allInScope && !selected;
                const pct = Math.max(2, Math.round(s.count / maxCount * 100));
                return `<div class="direction-tile ${selected ? 'selected' : ''} ${dimmed ? 'dimmed' : ''}"
                             style="--dt-color:${s.color}"
                             data-action="zoom-sector" data-codes="${s.codes.join(',')}" data-name="${s.name}">
                    <div class="dt-name">${tDomain(s.name)}</div>
                    <div class="dt-stats">
                        <span class="dt-count">${s.count.toLocaleString(locale)} ${I18N.direction_positions}</span>
                        ${s.fresh ? `<span class="dt-fresh">+${s.fresh} ${I18N.direction_new_this_week}</span>` : ''}
                    </div>
                    <div class="dt-bar-track"><div class="dt-bar-fill" style="width:${pct}%"></div></div>
                </div>`;
            }).join('');
        }
    }

    // Direction tiles click handler
    document.getElementById('direction-tiles').addEventListener('click', function(e) {
        const tile = e.target.closest('.direction-tile');
        if (!tile) return;

        const action = tile.dataset.action;

        if (action === 'zoom-sector') {
            // Level 1 → Level 2: zoom into the sector
            state.directionZoom = tile.dataset.name;
            renderDirectionTiles();
            return;
        }

        if (action === 'toggle-sector') {
            // Toggle the whole sector's domain codes
            const codes = tile.dataset.codes.split(',');
            const allSelected = codes.every(c => state.domains.includes(c));
            if (allSelected) {
                state.domains = state.domains.filter(c => !codes.includes(c));
            } else {
                codes.forEach(c => { if (!state.domains.includes(c)) state.domains.push(c); });
            }
            doSearch();
            return;
        }

        if (action === 'toggle-profession') {
            const name = tile.dataset.name;
            const idx = state.professions.indexOf(name);
            if (idx >= 0) { state.professions.splice(idx, 1); } else { state.professions.push(name); }
            doSearch();
            return;
        }
    });

    // Back breadcrumb click
    document.getElementById('direction-back').addEventListener('click', function(e) {
        e.preventDefault();
        state.directionZoom = null;
        renderDirectionTiles();
    });

    // ============================================================
    // LOCATION TREE (right panel — Bundesland→City hierarchy)
    // ============================================================
    function renderLocationTree(data) {
        if (!data) return;
        state.locationTree = data;
        const locale = LANG === 'de' ? 'de-DE' : 'en-US';
        const searchVal = (document.getElementById('location-search').value || '').toLowerCase();

        let locations = [...data.locations];

        // Apply search filter
        if (searchVal) {
            locations = locations.map(loc => {
                const stateMatch = tState(loc.state).toLowerCase().includes(searchVal);
                const filteredCities = loc.cities.filter(c =>
                    c.city.toLowerCase().includes(searchVal)
                );
                if (stateMatch || filteredCities.length > 0) {
                    return { ...loc, cities: stateMatch ? loc.cities : filteredCities };
                }
                return null;
            }).filter(Boolean);
        }

        // Apply sort
        const { field, dir } = state.locationSort;
        locations.sort((a, b) => {
            let cmp = field === 'name'
                ? tState(a.state).localeCompare(tState(b.state))
                : b.count - a.count;
            return dir === 'asc' ? -cmp : cmp;
        });

        let html = '';
        if (locations.length === 0) {
            html = '<div class="panel-empty">—</div>';
        } else {
            const allInScope = state.states.length === 0 && state.cities.length === 0;
            html = locations.map(loc => {
                const stateSelected = !allInScope && (state.states.includes(loc.state)
                    || state.cities.some(c => c.state === loc.state));
                const dimmed = !allInScope && !stateSelected;
                const isOpen = state.openStates.has(loc.state) || (searchVal && !dimmed);
                const tint = allInScope ? 'tint-all' : '';

                let citiesHtml = '';
                if (isOpen) {
                    let cities = [...loc.cities];
                    cities.sort((a, b) => field === 'name'
                        ? a.city.localeCompare(b.city)
                        : b.count - a.count);
                    if (dir === 'asc') cities.reverse();

                    citiesHtml = cities.map(c => {
                        const cSelected = state.cities.some(sc => sc.state === loc.state && sc.city === c.city);
                        return `<div class="tree-child ${cSelected ? 'selected' : ''}" data-type="city" data-state="${loc.state}" data-city="${c.city}" data-lat="${c.lat || ''}" data-lon="${c.lon || ''}">
                            <span class="tree-child-name">${c.city}</span>
                            <span class="tree-child-count">${c.count.toLocaleString(locale)}</span>
                        </div>`;
                    }).join('');
                    if (loc.total_cities > loc.cities.length) {
                        citiesHtml += `<div class="tree-child tree-show-more" data-state="${loc.state}" data-offset="${loc.cities.length}">
                            +${loc.total_cities - loc.cities.length} more…
                        </div>`;
                    }
                }

                return `<div class="tree-parent-group ${stateSelected ? 'selected' : ''} ${dimmed ? 'dimmed' : ''} ${tint}">
                    <div class="tree-parent" data-type="state" data-state="${loc.state}">
                        <span class="tree-chevron ${isOpen ? 'open' : ''}">${loc.total_cities > 0 ? '▸' : ''}</span>
                        <span class="tree-parent-name">${tState(loc.state)}</span>
                        <span class="tree-parent-count">${loc.count.toLocaleString(locale)}</span>
                    </div>
                    <div class="tree-children ${isOpen ? 'open' : ''}">${citiesHtml}</div>
                </div>`;
            }).join('');
        }

        // Render to both primary (tab 4) and power (tab 6) location trees
        ['location-tree', 'location-tree-power'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = html;
        });
    }

    // Location tree click handler — shared
    async function handleLocationTreeClick(e) {
        const showMore = e.target.closest('.tree-show-more');
        if (showMore) {
            const st = showMore.dataset.state;
            const offset = parseInt(showMore.dataset.offset) || 10;
            const body = {};
            if (state.domains.length > 0) body.domains = state.domains;
            try {
                const res = await fetch(`/api/search/location-tree/cities?state=${encodeURIComponent(st)}&offset=${offset}&limit=10`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (res.ok) {
                    const data = await res.json();
                    const loc = state.locationTree.locations.find(l => l.state === st);
                    if (loc && data.cities) {
                        loc.cities = [...loc.cities, ...data.cities];
                    }
                    renderLocationTree(state.locationTree);
                }
            } catch(err) { console.warn('Load more cities failed:', err); }
            return;
        }

        const child = e.target.closest('.tree-child');
        const parent = e.target.closest('.tree-parent');

        if (child && child.dataset.type === 'city') {
            const entry = { state: child.dataset.state, city: child.dataset.city };
            const idx = state.cities.findIndex(c => c.state === entry.state && c.city === entry.city);
            if (idx >= 0) { state.cities.splice(idx, 1); } else { state.cities.push(entry); }
            if (!state.states.includes(entry.state) && state.cities.some(c => c.state === entry.state)) {
                state.states.push(entry.state);
            }
            doSearch();
            return;
        }

        if (parent) {
            const chevron = parent.querySelector('.tree-chevron');
            if (e.target === chevron || e.target.closest('.tree-chevron')) {
                const st = parent.dataset.state;
                if (state.openStates.has(st)) { state.openStates.delete(st); }
                else { state.openStates.add(st); }
                renderLocationTree(state.locationTree);
                return;
            }
            const st = parent.dataset.state;
            const idx = state.states.indexOf(st);
            if (idx >= 0) {
                state.states.splice(idx, 1);
                state.cities = state.cities.filter(c => c.state !== st);
            } else {
                state.states.push(st);
            }
            doSearch();
        }
    }
    document.getElementById('location-tree').addEventListener('click', handleLocationTreeClick);
    const locPower = document.getElementById('location-tree-power');
    if (locPower) locPower.addEventListener('click', handleLocationTreeClick);

    // Location search box
    document.getElementById('location-search').addEventListener('input', function() {
        renderLocationTree(state.locationTree);
    });
    const locSearchPower = document.getElementById('location-search-power');
    if (locSearchPower) locSearchPower.addEventListener('input', function() {
        renderLocationTree(state.locationTree);
    });

    // ============================================================
    // TREE SORTING (column header clicks)
    // ============================================================
    document.querySelectorAll('.tree-sortable').forEach(el => {
        el.addEventListener('click', function() {
            const panel = this.dataset.panel;
            const field = this.dataset.sort;
            const sortState = panel === 'sector' ? state.sectorSort : state.locationSort;

            // Tri-state cycle: count-desc → name-asc → count-desc
            if (sortState.field === field) {
                sortState.dir = sortState.dir === 'desc' ? 'asc' : 'desc';
            } else {
                sortState.field = field;
                sortState.dir = field === 'name' ? 'asc' : 'desc';
            }

            // Update arrow indicators
            document.querySelectorAll(`.tree-sortable[data-panel="${panel}"] .sort-arrow`).forEach(a => a.textContent = '↕');
            this.querySelector('.sort-arrow').textContent = sortState.dir === 'asc' ? '↑' : '↓';

            if (panel === 'sector') renderSectorTree(state.sectorTree);
            else renderLocationTree(state.locationTree);
        });
    });

    // ============================================================
    // HEATMAP
    // ============================================================
    const HEAT_GRADIENT = {
        0.0: 'rgba(240,244,255,0.0)',
        0.15: 'rgba(147,197,253,0.5)',
        0.35: 'rgba(59,130,246,0.65)',
        0.55: 'rgba(34,197,94,0.75)',
        0.75: 'rgba(250,204,21,0.85)',
        0.90: 'rgba(249,115,22,0.9)',
        1.0:  'rgba(239,68,68,1.0)'
    };

    function renderHeatmap(points) {
        // Skip when map is in a hidden tab (0-size canvas crashes leaflet.heat)
        const mapEl = document.getElementById('search-map');
        if (mapEl && mapEl.offsetWidth === 0) return;

        if (!points || points.length === 0) {
            if (heatLayer) { map.removeLayer(heatLayer); heatLayer = null; }
            return;
        }

        // Use 90th percentile for max to prevent outlier dominance
        const weights = points.map(p => p[2]).sort((a, b) => a - b);
        const p90 = weights[Math.floor(weights.length * 0.9)] || 1;
        const maxW = Math.max(p90 * 1.5, 1);

        if (heatLayer) {
            // REUSE existing canvas — avoids Firefox canvas GC leak
            heatLayer.setLatLngs(points);
            heatLayer.setOptions({ max: maxW });
        } else {
            heatLayer = L.heatLayer(points, {
                radius: 18,
                blur: 22,
                maxZoom: 13,
                minOpacity: 0.12,
                max: maxW,
                pane: 'heatPane',
                gradient: HEAT_GRADIENT,
            }).addTo(map);
        }
    }

    // ============================================================
    // MAP MARKERS (individual postings)
    // ============================================================
    const MARKER_MIN_ZOOM = 8;  // markers appear at city level

    function markerRadius(zoom) {
        if (zoom <= 8) return 4;
        if (zoom <= 10) return 5;
        if (zoom <= 12) return 6;
        return 7;
    }

    function renderMarkers(markers) {
        if (markerLayer) { markerLayer.clearLayers(); map.removeLayer(markerLayer); markerLayer = null; }
        if (!markers || markers.length === 0) return;

        const zoom = map.getZoom();
        markerLayer = L.layerGroup();
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const markerColor = isDark ? '#60a5fa' : '#2563eb';
        const borderColor = isDark ? '#93c5fd' : '#1d4ed8';
        const textColor = isDark ? '#e2e8f0' : '#1e293b';

        markers.forEach(m => {
            const cm = L.circleMarker([m.lat, m.lon], {
                radius: markerRadius(zoom),
                color: borderColor,
                fillColor: markerColor,
                fillOpacity: 0.8,
                weight: 1.5,
            });

            // Tooltip on hover
            const title = m.t || 'Untitled';
            const employer = m.e ? `<br><span style="color:${isDark ? '#94a3b8' : '#64748b'}">${m.e}</span>` : '';
            const city = m.c ? `<br><span style="color:${isDark ? '#94a3b8' : '#64748b'}; font-size:11px">📍 ${m.c}</span>` : '';
            cm.bindTooltip(
                `<strong style="color:${textColor}">${title}</strong>${employer}${city}`,
                {
                    direction: 'top',
                    offset: [0, -8],
                    className: 'posting-marker-tooltip'
                }
            );

            // Click → open posting detail modal
            cm.on('click', function(e) {
                L.DomEvent.stopPropagation(e);
                openPostingDetail(m.id);
            });

            markerLayer.addLayer(cm);
        });

        // Show markers only when zoomed to city level or closer
        if (zoom >= MARKER_MIN_ZOOM) {
            markerLayer.addTo(map);
        }
        updateZoomHint(zoom);
    }

    // Toggle markers + resize on zoom (single consolidated handler)
    map.on('zoomend', function() {
        const zoom = map.getZoom();
        updateZoomBadge(zoom);
        // Posting markers
        if (markerLayer) {
            if (zoom >= MARKER_MIN_ZOOM && !map.hasLayer(markerLayer)) {
                markerLayer.addTo(map);
            } else if (zoom < MARKER_MIN_ZOOM && map.hasLayer(markerLayer)) {
                map.removeLayer(markerLayer);
            }
            if (map.hasLayer(markerLayer)) {
                const r = markerRadius(zoom);
                markerLayer.eachLayer(function(layer) { layer.setRadius(r); });
            }
        }
        // City markers
        if (cityMarkerLayer) {
            if (zoom >= 7 && !map.hasLayer(cityMarkerLayer)) {
                cityMarkerLayer.addTo(map);
            } else if (zoom < 7 && map.hasLayer(cityMarkerLayer)) {
                map.removeLayer(cityMarkerLayer);
            }
        }
        updateZoomHint(zoom);
    });

    // --- Zoom level badge (bottom-left overlay) ---
    const zoomBadge = L.DomUtil.create('div', 'zoom-badge');
    zoomBadge.style.cssText = 'position:absolute;bottom:28px;left:10px;z-index:800;background:rgba(0,0,0,0.55);color:#fff;padding:2px 7px;border-radius:4px;font-size:11px;font-family:system-ui,sans-serif;pointer-events:none;';
    document.getElementById('search-map').appendChild(zoomBadge);
    function updateZoomBadge(z) { zoomBadge.textContent = 'Zoom ' + z; }
    updateZoomBadge(map.getZoom());

    // --- Hint when zoomed out ---
    const zoomHint = L.DomUtil.create('div', 'zoom-hint');
    zoomHint.style.cssText = 'position:absolute;bottom:28px;left:50%;transform:translateX(-50%);z-index:800;background:rgba(0,0,0,0.6);color:#e2e8f0;padding:4px 12px;border-radius:6px;font-size:11px;font-family:system-ui,sans-serif;pointer-events:none;opacity:0;transition:opacity 0.3s;white-space:nowrap;';
    zoomHint.textContent = '🔍 Zoom in to see job markers';
    document.getElementById('search-map').appendChild(zoomHint);
    function updateZoomHint(z) { zoomHint.style.opacity = (z < MARKER_MIN_ZOOM && markerLayer) ? '1' : '0'; }

    // ============================================================
    // BUNDESLAND GEOJSON OVERLAY + CITY MARKERS
    // ============================================================
    let bundeslandLayer = null;
    let bundeslandGeoData = null;
    let cityMarkerLayer = null;

    // Load GeoJSON once at startup
    fetch('/static/geo/bundeslaender.geojson')
        .then(r => r.json())
        .then(data => {
            bundeslandGeoData = data;
            renderBundeslandOverlay();
        })
        .catch(e => console.warn('GeoJSON load failed:', e));

    function bundeslandStyleFn(feature) {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const name = feature.properties.name;
        const hasSelection = state.states.length > 0;
        const isSelected = state.states.includes(name);
        if (hasSelection && isSelected) {
            return {
                color: isDark ? '#60a5fa' : '#2563eb',
                weight: 2.5,
                fillColor: isDark ? '#3b82f6' : '#3b82f6',
                fillOpacity: 0.18,
                dashArray: null,
            };
        } else if (hasSelection) {
            return {
                color: isDark ? '#475569' : '#cbd5e1',
                weight: 1,
                fillColor: isDark ? '#334155' : '#e2e8f0',
                fillOpacity: 0.06,
                dashArray: '3,3',
            };
        }
        return {
            color: isDark ? '#475569' : '#93c5fd',
            weight: 1,
            fillColor: isDark ? '#1e3a5f' : '#dbeafe',
            fillOpacity: 0.10,
            dashArray: null,
        };
    }

    function renderBundeslandOverlay() {
        if (!bundeslandGeoData) return;

        if (bundeslandLayer) {
            // REUSE existing layer — just update styles (avoids GeoJSON re-parse + SVG churn)
            bundeslandLayer.setStyle(bundeslandStyleFn);
            return;
        }

        // First call: create the layer once
        bundeslandLayer = L.geoJSON(bundeslandGeoData, {
            style: bundeslandStyleFn,
            onEachFeature: function(feature, layer) {
                const name = feature.properties.name;
                layer.bindTooltip('', { sticky: true, className: 'bundesland-tooltip' });

                layer.on('click', function(e) {
                    L.DomEvent.stopPropagation(e);
                    const idx = state.states.indexOf(name);
                    if (idx >= 0) {
                        state.states.splice(idx, 1);
                        state.cities = state.cities.filter(c => c.state !== name);
                    } else {
                        state.states.push(name);
                    }
                    doSearch();
                });
                layer.on('mouseover', function(e) {
                    const loc = state.locationTree?.locations?.find(l => l.state === name);
                    const count = loc ? loc.count.toLocaleString(LANG === 'de' ? 'de-DE' : 'en-US') : '—';
                    layer.setTooltipContent(`<strong>${tState(name)}</strong><br>${count} ${LANG === 'de' ? 'Stellen' : 'posts'}`);
                    layer.openTooltip(e.latlng);
                    if (!state.states.includes(name)) {
                        layer.setStyle({ fillOpacity: 0.22, weight: 2 });
                    }
                });
                layer.on('mouseout', function() {
                    layer.closeTooltip();
                    bundeslandLayer.resetStyle(layer);
                });
            },
        }).addTo(map);

        bundeslandLayer.bringToBack();
    }

    function renderCityMarkers() {
        if (cityMarkerLayer) { cityMarkerLayer.clearLayers(); map.removeLayer(cityMarkerLayer); cityMarkerLayer = null; }
        if (!state.locationTree || !state.locationTree.locations) return;

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        cityMarkerLayer = L.layerGroup();

        state.locationTree.locations.forEach(loc => {
            if (!loc.cities) return;
            loc.cities.forEach(c => {
                if (!c.lat || !c.lon) return;
                const isSelected = state.cities.some(sc => sc.state === loc.state && sc.city === c.city);
                const baseColor = isSelected
                    ? (isDark ? '#f59e0b' : '#d97706')
                    : (isDark ? '#60a5fa' : '#3b82f6');
                const r = isSelected ? 6 : 4;
                const opacity = isSelected ? 0.95 : 0.55;

                const cm = L.circleMarker([c.lat, c.lon], {
                    radius: r,
                    color: baseColor,
                    fillColor: baseColor,
                    fillOpacity: opacity,
                    weight: isSelected ? 2 : 1,
                    pane: 'markerPane',
                });

                const locale = LANG === 'de' ? 'de-DE' : 'en-US';
                cm.bindTooltip(`<strong>${c.city}</strong><br>${c.count.toLocaleString(locale)} ${LANG === 'de' ? 'Stellen' : 'posts'}`, {
                    direction: 'top', offset: [0, -6],
                });

                cm.on('click', function(e) {
                    L.DomEvent.stopPropagation(e);
                    const entry = { state: loc.state, city: c.city };
                    const idx = state.cities.findIndex(sc => sc.state === entry.state && sc.city === entry.city);
                    if (idx >= 0) { state.cities.splice(idx, 1); } else { state.cities.push(entry); }
                    if (!state.states.includes(loc.state) && state.cities.some(sc => sc.state === loc.state)) {
                        state.states.push(loc.state);
                    }
                    doSearch();
                });

                cityMarkerLayer.addLayer(cm);
            });
        });

        // Only show city dots at reasonable zoom
        if (map.getZoom() >= 7) {
            cityMarkerLayer.addTo(map);
        }
    }

    // ============================================================
    // ACTIVE FILTER PILLS — three grouped frames
    // Group 1: Role & Profile (profile + domains + professions) — all OR
    // Group 2: Qualification — all OR
    // Group 3: Location (states + geo) — all OR
    // Between groups: AND (implicit — separate frames make this clear visually)
    // ============================================================

    function renderFilterPills() {
        const container = document.getElementById('active-filters');
        const orLabel = LANG === 'de' ? 'oder' : 'or';

        function renderGroup(groupClass, label, pills) {
            if (pills.length === 0) return '';
            const inner = pills.reduce((acc, pill, i) =>
                i === 0 ? [pill] : [...acc, `<span class="filter-op-or">${orLabel}</span>`, pill], []);
            return `<div class="filter-group ${groupClass}">
                <span class="filter-group-label">${label}</span>
                ${inner.join('')}
            </div>`;
        }

        // Group 1: Role & Profile (hierarchical: Sector > Profession)
        const g1 = [];
        if (state.domains.length > 0) {
            const names = new Set();
            for (const code of state.domains) {
                for (const [name, codes] of Object.entries(window._domainMap || {})) {
                    if (codes.includes(code)) names.add(name);
                }
            }
            names.forEach(name => {
                // Check if any professions are selected under this domain
                const domainProfs = state.professions.filter(p => {
                    if (!state.sectorTree) return false;
                    const sector = state.sectorTree.sectors.find(s => s.name === name);
                    return sector && sector.professions.some(sp => sp.name === p);
                });
                if (domainProfs.length > 0) {
                    // Show hierarchical pills: Sector > Profession
                    domainProfs.forEach(prof => {
                        const displayProf = (state._profDisplayNames && state._profDisplayNames[prof]) || prof;
                        g1.push(`<span class="filter-pill profession-pill" data-type="profession" data-name="${prof}">
                            ${tDomain(name)} › ${displayProf} <button class="pill-remove" data-type="profession" data-name="${prof}">×</button>
                        </span>`);
                    });
                } else {
                    g1.push(`<span class="filter-pill domain-pill" data-type="domain" data-name="${name}">
                        ${tDomain(name)} <button class="pill-remove" data-type="domain" data-name="${name}">×</button>
                    </span>`);
                }
            });
        }
        // Professions not under a selected domain
        state.professions.forEach(name => {
            const alreadyShown = g1.some(html => html.includes(`data-name="${name}"`));
            if (!alreadyShown) {
                const displayName = (state._profDisplayNames && state._profDisplayNames[name]) || name;
                g1.push(`<span class="filter-pill profession-pill" data-type="profession" data-name="${name}">
                    💼 ${displayName} <button class="pill-remove" data-type="profession" data-name="${name}">×</button>
                </span>`);
            }
        });

        // Group 2: Qualification
        const g2 = [];
        state.ql.forEach(level => {
            g2.push(`<span class="filter-pill ql-pill" data-type="ql" data-level="${level}">
                ${tQL(level)} <button class="pill-remove" data-type="ql" data-level="${level}">×</button>
            </span>`);
        });

        // Group 3: Location (hierarchical: Bundesland > City)
        const g3 = [];
        state.states.forEach(stateName => {
            // Check if any cities are selected under this state
            const stateCities = state.cities.filter(c => c.state === stateName);
            if (stateCities.length > 0) {
                stateCities.forEach(c => {
                    g3.push(`<span class="filter-pill city-pill" data-type="city" data-state="${c.state}" data-city="${c.city}">
                        ${tState(stateName)} › ${c.city} <button class="pill-remove" data-type="city" data-state="${c.state}" data-city="${c.city}">×</button>
                    </span>`);
                });
            } else {
                g3.push(`<span class="filter-pill state-pill" data-type="state" data-name="${stateName}">
                    🗺 ${tState(stateName)} <button class="pill-remove" data-type="state" data-name="${stateName}">×</button>
                </span>`);
            }
        });
        state.geoLocations.forEach((g, idx) => {
            const rPart = g.radius_km
                ? ` <button class="pill-radius-cycle" data-idx="${idx}" title="Click to change radius">(${g.radius_km} km)</button>`
                : '';
            g3.push(`<span class="filter-pill geo-pill" data-type="geo" data-idx="${idx}">
                📍 ${g.label || g.lat + ', ' + g.lon}${rPart} <button class="pill-remove" data-type="geo" data-idx="${idx}">×</button>
            </span>`);
        });

        const g1label = LANG === 'de' ? '💼 Beruf & Profil' : '💼 Role & Profile';
        const g2label = LANG === 'de' ? '⭐ Qualifikation' : '⭐ Qualification';
        const g3label = LANG === 'de' ? '📍 Ort' : '📍 Location';

        container.innerHTML = [
            renderGroup('fg-subject', g1label, g1),
            renderGroup('fg-ql', g2label, g2),
            renderGroup('fg-location', g3label, g3),
        ].filter(Boolean).join('');
    }

    document.getElementById('active-filters').addEventListener('click', async function(e) {
        // Radius cycling — click (n km) in geo pill to cycle 10→25→50→100 (per location)
        if (e.target.closest('.pill-radius-cycle')) {
            const RADIUS_STEPS = [10, 25, 50, 100];
            const btn = e.target.closest('.pill-radius-cycle');
            const gIdx = parseInt(btn.dataset.idx) || 0;
            const g = state.geoLocations[gIdx];
            if (g) {
                const stepIdx = RADIUS_STEPS.indexOf(g.radius_km);
                g.radius_km = RADIUS_STEPS[(stepIdx + 1) % RADIUS_STEPS.length];
                document.getElementById('radius-select').value = g.radius_km;
                updateGeoLayers();
                renderFilterPills();
                doSearch();
            }
            return;
        }

        const btn = e.target.closest('.pill-remove');
        if (!btn) return;
        const type = btn.dataset.type;
        if (type === 'domain') {
            const name = btn.dataset.name;
            const codes = (window._domainMap || {})[name] || [];
            state.domains = state.domains.filter(c => !codes.includes(c));
            // Also remove professions under this domain
            if (state.sectorTree) {
                const sector = state.sectorTree.sectors.find(s => s.name === name);
                if (sector) {
                    const profNames = sector.professions.map(p => p.name);
                    state.professions = state.professions.filter(p => !profNames.includes(p));
                }
            }
        } else if (type === 'ql') {
            const level = parseInt(btn.dataset.level);
            state.ql = state.ql.filter(l => l !== level);
        } else if (type === 'state') {
            const name = btn.dataset.name;
            state.states = state.states.filter(s => s !== name);
            state.cities = state.cities.filter(c => c.state !== name);
        } else if (type === 'city') {
            const st = btn.dataset.state;
            const city = btn.dataset.city;
            state.cities = state.cities.filter(c => !(c.state === st && c.city === city));
            // If no more cities for this state, check if state should be removed
            if (!state.cities.some(c => c.state === st)) {
                // Keep the state selected if it was explicitly selected
            }
        } else if (type === 'profession') {
            const name = btn.dataset.name;
            state.professions = state.professions.filter(p => p !== name);
        } else if (type === 'geo') {
            const gIdx = parseInt(btn.dataset.idx);
            state.geoLocations.splice(gIdx, 1);
            updateGeoLayers();
            if (state.geoLocations.length === 0) cityInput.value = '';
        }
        doSearch();
    });

    // ============================================================
    // TOTAL + FRESHNESS
    // ============================================================
    function renderTotal(total, landscapeTotal) {
        const locale = LANG === 'de' ? 'de-DE' : 'en-US';
        const totalStr = total.toLocaleString(locale);
        const hasOf = landscapeTotal && landscapeTotal !== total;
        const ofWord = LANG === 'de' ? 'von' : 'of';
        const ofStr = hasOf ? `${ofWord} ${landscapeTotal.toLocaleString(locale)}` : '';

        // Primary total display
        const el = document.getElementById('search-total');
        if (el) {
            const numEl = el.querySelector('.total-number');
            if (numEl) numEl.textContent = totalStr;
        }
        const ofEl = document.getElementById('total-of');
        if (ofEl) {
            ofEl.textContent = ofStr;
            ofEl.style.display = hasOf ? '' : 'none';
        }
        // Power tab total
        const elP = document.getElementById('search-total-power');
        if (elP) {
            const numP = elP.querySelector('.total-number');
            if (numP) numP.textContent = totalStr;
        }
    }

    function renderFreshness(count) {
        const badge = document.getElementById('freshness-badge');
        if (count > 0) {
            badge.style.display = '';
            const locale = LANG === 'de' ? 'de-DE' : 'en-US';
            document.getElementById('fresh-count').textContent = count.toLocaleString(locale);
        } else {
            badge.style.display = 'none';
        }
    }

    // ============================================================
    // INTELLIGENCE PANEL — sparkline + state/profession rankings
    // ============================================================
    let _lastSparklineDays = null;

    function renderSparkline(days, _retries) {
        _lastSparklineDays = days;
        _drawSparklineOn(days, 'sparkline-canvas', 'intel-activity', _retries);
        _drawSparklineOn(days, 'sparkline-canvas-power', 'intel-activity-power', _retries);
    }

    function _drawSparklineOn(days, canvasId, sectionId, _retries) {
        const canvas = document.getElementById(canvasId);
        const section = document.getElementById(sectionId);
        if (!canvas || !section) return;
        if (!days || days.length === 0) { section.style.display = 'none'; return; }
        section.style.display = '';

        // HiDPI canvas sizing
        const rect = canvas.getBoundingClientRect();
        // Guard: if panel hasn't laid out yet, retry after a short delay
        if (rect.width < 10 && (_retries || 0) < 5) {
            setTimeout(() => _drawSparklineOn(days, canvasId, sectionId, (_retries || 0) + 1), 200);
            return;
        }
        const dpr = window.devicePixelRatio || 1;
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        const ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);
        const W = rect.width, H = rect.height;

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const gridColor = isDark ? 'rgba(148,163,184,0.15)' : 'rgba(100,116,139,0.12)';
        const weekColor = isDark ? 'rgba(148,163,184,0.30)' : 'rgba(100,116,139,0.25)';
        const textCol = isDark ? '#94a3b8' : '#94a3b8';

        // Layout: left margin for Y-axis, bottom for date labels
        const marginL = 36, marginB = 16, marginT = 4, marginR = 4;
        const plotW = W - marginL - marginR;
        const plotH = H - marginT - marginB;

        const maxCount = Math.max(...days.map(d => d.count), 1);

        // --- Y-axis steps ---
        // Pick nice step: 1,2,5,10,20,50,100,200,500,1000,2000,5000,10000,...
        function niceStep(max) {
            const rough = max / 3;
            const mag = Math.pow(10, Math.floor(Math.log10(rough)));
            const residual = rough / mag;
            if (residual <= 1.5) return mag;
            if (residual <= 3.5) return 2 * mag;
            if (residual <= 7.5) return 5 * mag;
            return 10 * mag;
        }
        const step = niceStep(maxCount);
        const yMax = Math.ceil(maxCount / step) * step;

        ctx.font = '9px system-ui, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';

        // Draw Y-axis grid lines + labels
        for (let v = 0; v <= yMax; v += step) {
            const y = marginT + plotH - (v / yMax) * plotH;
            // Grid line
            ctx.strokeStyle = gridColor;
            ctx.lineWidth = 0.7;
            ctx.beginPath();
            ctx.moveTo(marginL, y);
            ctx.lineTo(W - marginR, y);
            ctx.stroke();
            // Label
            const label = v >= 1000 ? (v / 1000) + 'k' : v.toString();
            ctx.fillStyle = textCol;
            ctx.fillText(label, marginL - 4, y);
        }

        // Build data points in plot area
        const points = days.map((d, i) => ({
            x: marginL + (i / (days.length - 1)) * plotW,
            y: marginT + plotH - (d.count / yMax) * plotH,
            count: d.count,
            date: d.date,
        }));

        // --- Vertical grid lines ---
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        days.forEach((d, i) => {
            const x = points[i].x;
            const dt = new Date(d.date + 'T00:00:00');
            const dow = dt.getDay(); // 0=Sun, 1=Mon

            if (dow === 1) {
                // Monday — solid week line + date label
                ctx.strokeStyle = weekColor;
                ctx.lineWidth = 1;
                ctx.setLineDash([]);
                ctx.beginPath();
                ctx.moveTo(x, marginT);
                ctx.lineTo(x, marginT + plotH);
                ctx.stroke();
                // Date label
                const lbl = dt.getDate() + '.' + (dt.getMonth() + 1) + '.';
                ctx.fillStyle = textCol;
                ctx.font = '8px system-ui, sans-serif';
                ctx.fillText(lbl, x, marginT + plotH + 3);
            } else {
                // Other days — dotted lines
                ctx.strokeStyle = gridColor;
                ctx.lineWidth = 0.5;
                ctx.setLineDash([2, 3]);
                ctx.beginPath();
                ctx.moveTo(x, marginT);
                ctx.lineTo(x, marginT + plotH);
                ctx.stroke();
            }
        });
        ctx.setLineDash([]);

        // --- Color interpolation: grey (old/left) → green (recent/right) ---
        // Older postings fade to grey, recent ones vivid green
        const greyR = isDark ? 100 : 160, greyG = isDark ? 116 : 174, greyB = isDark ? 139 : 185;
        const greenR = isDark ? 74 : 34, greenG = isDark ? 222 : 197, greenB = isDark ? 128 : 94;
        function lerpColor(t) {
            const r = Math.round(greyR + (greenR - greyR) * t);
            const g = Math.round(greyG + (greenG - greyG) * t);
            const b = Math.round(greyB + (greenB - greyB) * t);
            return [r, g, b];
        }

        // --- Gradient fill under the line (left-to-right fade) ---
        ctx.beginPath();
        ctx.moveTo(points[0].x, marginT + plotH);
        points.forEach(p => ctx.lineTo(p.x, p.y));
        ctx.lineTo(points[points.length - 1].x, marginT + plotH);
        ctx.closePath();
        const grad = ctx.createLinearGradient(points[0].x, 0, points[points.length - 1].x, 0);
        const [gr0, gg0, gb0] = lerpColor(0);
        const [gr1, gg1, gb1] = lerpColor(1);
        grad.addColorStop(0, `rgba(${gr0},${gg0},${gb0},0.08)`);
        grad.addColorStop(0.5, `rgba(${Math.round((gr0+gr1)/2)},${Math.round((gg0+gg1)/2)},${Math.round((gb0+gb1)/2)},0.18)`);
        grad.addColorStop(1, `rgba(${gr1},${gg1},${gb1},0.30)`);
        ctx.fillStyle = grad;
        ctx.fill();

        // --- Fading line: draw segment-by-segment with interpolated color ---
        ctx.lineWidth = 2;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        for (let i = 1; i < points.length; i++) {
            const t = i / (points.length - 1); // 0 = old, 1 = recent
            const [cr, cg, cb] = lerpColor(t);
            const segColor = `rgb(${cr},${cg},${cb})`;
            const prev = points[i - 1], curr = points[i];
            const cpx = (prev.x + curr.x) / 2;
            ctx.beginPath();
            ctx.moveTo(prev.x, prev.y);
            ctx.bezierCurveTo(cpx, prev.y, cpx, curr.y, curr.x, curr.y);
            ctx.strokeStyle = segColor;
            // Subtle glow only on recent half
            if (t > 0.5) {
                ctx.shadowColor = segColor;
                ctx.shadowBlur = 3 * t;
            } else {
                ctx.shadowBlur = 0;
            }
            ctx.stroke();
        }
        ctx.shadowBlur = 0;

        // --- Hover tooltip ---
        // Store points on canvas for hover handler (avoids closure leak on re-render)
        canvas._sparklinePoints = points;
        if (!canvas._sparklineHover) {
            canvas._sparklineHover = true;
            canvas.addEventListener('mousemove', function(e) {
                const pts = canvas._sparklinePoints;
                if (!pts || !pts.length) return;
                const br = canvas.getBoundingClientRect();
                const mx = e.clientX - br.left;
                let closest = pts[0], minDist = 9999;
                for (const p of pts) {
                    const dist = Math.abs(p.x - mx);
                    if (dist < minDist) { minDist = dist; closest = p; }
                }
                canvas.title = closest.date + ': ' + closest.count.toLocaleString();
            });
        }
    }

    async function loadIntelligence() {
        if (intelligenceAbort) intelligenceAbort.abort();
        intelligenceAbort = new AbortController();
        try {
            const body = { days: 30 };
            if (state.domains.length > 0) body.domains = state.domains;
            if (state.ql.length > 0) body.ql = state.ql;
            if (state.states.length > 0) body.states = state.states;
            if (state.professions.length > 0) body.professions = state.professions;
            if (state.geoLocations.length > 0)
                body.geo_locations = state.geoLocations.map(g => ({lat: g.lat, lon: g.lon, radius_km: g.radius_km}));
            const res = await fetch('/api/search/intelligence', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: intelligenceAbort.signal,
            });
            if (!res.ok) return;
            const data = await res.json();
            renderSparkline(data.activity);
        } catch(e) {
            if (e.name !== 'AbortError') console.warn('Intelligence load failed:', e);
        }
    }

    // ============================================================
    // HIERARCHY TREE LOADERS
    // ============================================================
    let sectorTreeAbort = null;
    let locationTreeAbort = null;
    let intelligenceAbort = null;
    let resultsAbort = null;

    async function loadSectorTree() {
        if (sectorTreeAbort) sectorTreeAbort.abort();
        sectorTreeAbort = new AbortController();
        try {
            const body = {};
            if (state.states.length > 0) body.states = state.states;
            if (state.ql.length > 0) body.ql = state.ql;
            const res = await fetch('/api/search/sector-tree', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: sectorTreeAbort.signal,
            });
            if (res.ok) {
                const data = await res.json();
                // Build domain map for pills
                window._domainMap = {};
                data.sectors.forEach(s => { window._domainMap[s.name] = s.codes; });
                renderSectorTree(data);
                renderDirectionTiles();
                // Re-render pills now that _domainMap is available
                // (first doSearch renders pills before this async call completes)
                renderFilterPills();
            }
        } catch(e) {
            if (e.name !== 'AbortError') console.warn('Sector tree load failed:', e);
        }
    }

    async function loadLocationTree() {
        if (locationTreeAbort) locationTreeAbort.abort();
        locationTreeAbort = new AbortController();
        try {
            const body = {};
            if (state.domains.length > 0) body.domains = state.domains;
            const res = await fetch('/api/search/location-tree', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: locationTreeAbort.signal,
            });
            if (res.ok) {
                const data = await res.json();
                renderLocationTree(data);
                renderCityMarkers();
            }
        } catch(e) {
            if (e.name !== 'AbortError') console.warn('Location tree load failed:', e);
        }
    }

    // ============================================================
    // MAIN SEARCH
    // ============================================================
    let searchPending = false;
    let searchQueued = false;
    let searchDebounceTimer = null;
    let previewAbort = null;

    function doSearch() {
        // Debounce: coalesce rapid-fire calls into one after 250ms of calm
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(_doSearchNow, 250);
    }

    async function _doSearchNow() {
        if (searchPending) { searchQueued = true; return; }
        searchPending = true;

        // Abort any in-flight preview request
        if (previewAbort) previewAbort.abort();
        previewAbort = new AbortController();

        const body = {};
        if (state.domains.length > 0) body.domains = state.domains;
        if (state.ql.length > 0) body.ql = state.ql;
        if (state.states.length > 0) body.states = state.states;
        if (state.professions.length > 0) body.professions = state.professions;
        if (state.geoLocations.length > 0)
            body.geo_locations = state.geoLocations.map(g => ({lat: g.lat, lon: g.lon, radius_km: g.radius_km}));

        try {
            const res = await fetch('/api/search/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: previewAbort.signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            state.data = data;

            // Render QL strip from preview data
            renderQLStrip(data.by_ql);
            try { renderHeatmap(data.heatmap); } catch(_) {}
            try { renderMarkers(data.markers); } catch(_) {}
            renderTotal(data.total, data.landscape_total);
            renderFreshness(data.fresh_count);
            renderFilterPills();
            try { renderBundeslandOverlay(); } catch(_) {}

            // Force map tile refresh after render (only if map visible)
            setTimeout(() => { const m = document.getElementById('search-map'); if (m && m.offsetWidth > 0) map.invalidateSize(); }, 50);

            // Load cross-filtered panels in parallel (each has its own AbortController)
            await Promise.allSettled([
                loadSectorTree(),
                loadLocationTree(),
                loadIntelligence(),
            ]);

            // Load matching postings as result tiles
            loadResults(true);

            // Track filter state for Mira context
            if (typeof trackEvent === 'function') {
                trackEvent('search_filter', {
                    domains: state.domains,
                    ql: state.ql,
                    city: state.geoLocations.length > 0 ? state.geoLocations[0].label : null,
                    radius: state.geoLocations.length > 0 ? state.geoLocations[0].radius_km : null,
                    results: data.total
                });
            }
            // Persist filters so the user returns to the same view
            saveState();
        } catch(e) {
            if (e.name !== 'AbortError') console.error('Search failed:', e);
        } finally {
            searchPending = false;
            if (searchQueued) {
                searchQueued = false;
                _doSearchNow();
            }
        }
    }

    // ============================================================
    // SEARCH RESULTS — tiles / rolodex
    // ============================================================
    let resultsOffset = 0;
    let resultsLoading = false;
    let currentPostingId = null;
    let pendingInterest = null;

    function buildFilterBody() {
        const body = {};
        if (state.domains.length > 0) body.domains = state.domains;
        if (state.ql.length > 0) body.ql = state.ql;
        if (state.states.length > 0) body.states = state.states;
        if (state.professions.length > 0) body.professions = state.professions;
        if (state.geoLocations.length > 0)
            body.geo_locations = state.geoLocations.map(g => ({lat: g.lat, lon: g.lon, radius_km: g.radius_km}));
        return body;
    }

    async function loadResults(reset) {
        if (resultsLoading && !reset) return;
        if (reset && resultsAbort) resultsAbort.abort();
        resultsAbort = new AbortController();
        resultsLoading = true;

        if (reset) resultsOffset = 0;

        const grid = document.getElementById('search-results-grid');
        const section = document.getElementById('search-results-section');
        const showMore = document.getElementById('results-show-more');

        if (reset) {
            grid.innerHTML = `<div class="results-loading">${I18N.results_loading}</div>`;
            section.style.display = '';
        }

        const body = buildFilterBody();
        body.offset = resultsOffset;
        body.limit = 20;
        if (state.profileId) body.score = true;

        try {
            const res = await fetch('/api/search/results', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: resultsAbort.signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            if (reset) grid.innerHTML = '';

            // Title + sort indicator
            document.getElementById('results-title').textContent = I18N.results_title;
            const sortEl = document.getElementById('results-sort-indicator');
            if (data.sort === 'score') {
                sortEl.textContent = '🎯 ' + I18N.results_sort_score;
                sortEl.style.display = '';
            } else if (state.profileId) {
                sortEl.textContent = '🕐 ' + I18N.results_sort_recency;
                sortEl.style.display = '';
            } else {
                sortEl.style.display = 'none';
            }

            // Profile results are now OR'd server-side via profile_ids.
            // Just use whatever the server returned.
            let allResults = data.results;

            if (allResults.length === 0 && resultsOffset === 0) {
                grid.innerHTML = `<div class="results-empty">${I18N.results_none}</div>`;
                showMore.style.display = 'none';
                resultsLoading = false;
                return;
            }

            const locale = LANG === 'de' ? 'de-DE' : 'en-US';
            allResults.forEach(p => {
                const tile = document.createElement('div');
                tile.className = 'result-tile';
                tile.dataset.postingId = p.posting_id;
                if (p.interested === true) tile.classList.add('tile-interested');
                if (p.interested === false) tile.classList.add('tile-not-interested');

                const isNew = p.first_seen && (Date.now() - new Date(p.first_seen).getTime()) < 7 * 86400000;
                const dateStr = p.first_seen ? new Date(p.first_seen).toLocaleDateString(locale) : '';
                const scorePct = (p.score != null) ? Math.round(p.score * 100) : null;
                const scoreBadge = scorePct != null
                    ? `<span class="tile-score-badge" title="Match ${scorePct}%">🎯 ${scorePct}%</span>`
                    : '';

                tile.innerHTML = `
                    <div class="tile-header">
                        ${scoreBadge}
                        <span class="tile-domain-dot" style="background:${p.domain_color};" title="${tDomain(p.domain)}"></span>
                        <span class="tile-ql-badge">${tQL(p.ql_level)}</span>
                        ${isNew ? `<span class="tile-new-badge">${I18N.results_new}</span>` : ''}
                        ${p.interested === true ? '<span class="tile-interest-icon" title="' + I18N.interest_already_yes + '">👍</span>' : ''}
                        ${p.interested === false ? '<span class="tile-interest-icon" title="' + I18N.interest_already_no + '">👎</span>' : ''}
                    </div>
                    <h3 class="tile-title">${escHtml(p.job_title)}</h3>
                    ${p.employer ? `<div class="tile-employer">${escHtml(p.employer)}</div>` : ''}
                    ${p.location ? `<div class="tile-location">📍 ${escHtml(p.location)}</div>` : ''}
                    ${p.summary ? `<div class="tile-summary">${escHtml(p.summary).substring(0, 150)}${p.summary.length > 150 ? '…' : ''}</div>` : ''}
                    <div class="tile-footer">
                        <span class="tile-date">${dateStr}</span>
                        <button class="tile-details-btn">${I18N.results_view_details}</button>
                    </div>
                `;
                grid.appendChild(tile);
            });

            resultsOffset += data.results.length;
            if (data.has_more) {
                showMore.style.display = '';
                document.getElementById('btn-show-more').textContent = I18N.results_show_more;
            } else {
                showMore.style.display = 'none';
            }

            // Sync results to power tab grid
            const powerGrid = document.getElementById('search-results-grid-power');
            if (powerGrid) powerGrid.innerHTML = grid.innerHTML;
            const powerTitle = document.getElementById('results-title-power');
            if (powerTitle) powerTitle.textContent = I18N.results_title;
        } catch(e) {
            if (e.name === 'AbortError') return;
            console.error('Results failed:', e);
            if (reset) grid.innerHTML = `<div class="results-empty">${I18N.network_error}</div>`;
        } finally {
            resultsLoading = false;
        }
    }

    function escHtml(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    // Click on tile → open detail
    document.getElementById('search-results-grid').addEventListener('click', function(e) {
        const btn = e.target.closest('.tile-details-btn');
        const tile = e.target.closest('.result-tile');
        if (btn && tile) {
            openPostingDetail(parseInt(tile.dataset.postingId));
        }
    });

    // Same handler for power tab results grid
    const powerResultsGrid = document.getElementById('search-results-grid-power');
    if (powerResultsGrid) {
        powerResultsGrid.addEventListener('click', function(e) {
            const btn = e.target.closest('.tile-details-btn');
            const tile = e.target.closest('.result-tile');
            if (btn && tile) {
                openPostingDetail(parseInt(tile.dataset.postingId));
            }
        });
    }

    // Show more
    document.getElementById('btn-show-more').addEventListener('click', function() {
        loadResults(false);
    });

    // ============================================================
    // PROFILE SCOPE — infer domain/QL/geo from CV on load
    // ============================================================
    async function initProfileScope() {
        try {
            const res = await fetch('/api/search/profile-scope');
            if (!res.ok) return;
            const data = await res.json();
            if (!data.available) return;

            // Remember profile_id for later /enrich calls
            state.profileId = data.profile_id || null;

            // Pre-select domains inferred from title / desired_roles
            if (data.domains && data.domains.length > 0 && state.domains.length === 0) {
                state.domains = data.domains;
            }

            // Pre-select QL range from experience_level
            if (data.ql && data.ql.length > 0 && state.ql.length === 0) {
                state.ql = data.ql;
            }

            // Pre-apply profile location as geo filter
            if (data.location && state.geoLocations.length === 0) {
                await applyProfileLocation(data.location);
                return;   // applyProfileLocation calls doSearch()
            }
        } catch(e) {
            console.warn('Profile scope init failed:', e);
        }
    }

    async function applyProfileLocation(cityName) {
        try {
            const res = await fetch(`/api/geo/search?q=${encodeURIComponent(cityName)}`);
            const results = await res.json();
            if (!results.length) { renderFilterPills(); return; }
            const r = results[0];
            const lat      = parseFloat(r.lat);
            const lon      = parseFloat(r.lon);
            const radius_km = parseInt(document.getElementById('radius-select').value) || 50;
            state.geoLocations.push({lat, lon, radius_km, label: cityName});
            cityInput.value = '';
            map.setView([lat, lon], 10);
            updateGeoLayers();
            doSearch();
        } catch(e) {
            console.warn('Profile location geocode failed:', e);
            renderFilterPills();
        }
    }

    // ============================================================
    // POSTING DETAIL MODAL
    // ============================================================
    async function openPostingDetail(postingId) {
        currentPostingId = postingId;
        const overlay = document.getElementById('posting-modal-overlay');
        const body = document.getElementById('posting-modal-body');
        const interestBar = document.getElementById('posting-interest-bar');

        body.innerHTML = `<div class="results-loading">${I18N.results_loading}</div>`;
        overlay.classList.add('open');
        document.body.style.overflow = 'hidden';

        // Reset interest bar
        document.getElementById('interest-prompt').textContent = I18N.interest_prompt;
        document.getElementById('btn-interested').textContent = I18N.interest_yes;
        document.getElementById('btn-not-interested').textContent = I18N.interest_no;
        document.getElementById('interest-reason-row').style.display = 'none';
        document.getElementById('interest-feedback').style.display = 'none';
        document.getElementById('interest-reason').placeholder = I18N.interest_reason_placeholder;
        pendingInterest = null;

        try {
            const res = await fetch(`/api/search/posting/${postingId}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const p = await res.json();

            const locale = LANG === 'de' ? 'de-DE' : 'en-US';
            const seenDate = p.first_seen ? new Date(p.first_seen).toLocaleDateString(locale) : '';
            const lastDate = p.last_seen ? new Date(p.last_seen).toLocaleDateString(locale) : '';

            let html = `
                <div class="detail-header">
                    <span class="tile-domain-dot" style="background:${p.domain_color}; width:14px; height:14px;"></span>
                    <span class="detail-domain">${tDomain(p.domain)}</span>
                    <span class="detail-ql">${p.ql_label}</span>
                </div>
                <h2 class="detail-title">${escHtml(p.job_title)}</h2>
            `;

            // Info grid
            const infoRows = [];
            if (p.employer) infoRows.push([I18N.detail_employer, escHtml(p.employer) + (p.employer_industry ? ` <span class="detail-dim">(${escHtml(p.employer_industry)})</span>` : '')]);
            if (p.location) infoRows.push([I18N.detail_location, escHtml(p.location)]);
            if (p.start_date) infoRows.push([I18N.detail_start_date, escHtml(p.start_date)]);
            if (p.contract_type) infoRows.push([I18N.detail_contract, escHtml(p.contract_type)]);
            if (p.work_hours) infoRows.push([I18N.detail_hours, escHtml(p.work_hours)]);
            if (p.source) infoRows.push([I18N.detail_source, escHtml(p.source)]);
            if (seenDate) infoRows.push([I18N.detail_seen_since, seenDate + (lastDate && lastDate !== seenDate ? ` — ${lastDate}` : '')]);

            if (infoRows.length) {
                html += `<div class="detail-info-grid">` +
                    infoRows.map(([label, val]) => `<div class="detail-info-label">${label}</div><div class="detail-info-value">${val}</div>`).join('') +
                `</div>`;
            }

            // Summary
            if (p.summary) {
                html += `<div class="detail-section">
                    <h4>${I18N.detail_summary}</h4>
                    <p>${escHtml(p.summary)}</p>
                </div>`;
            }

            // Description
            if (p.job_description) {
                html += `<div class="detail-section">
                    <h4>${I18N.detail_description}</h4>
                    <div class="detail-description">${escHtml(p.job_description)}</div>
                </div>`;
            }

            // External link
            if (p.external_url) {
                html += `<div class="detail-actions">
                    <a href="${p.external_url}" target="_blank" rel="noopener" class="btn-external-link">${I18N.results_external} ↗</a>
                </div>`;
            }

            body.innerHTML = html;

            // Show existing interest state
            if (p.interested === true) {
                showInterestState(true);
            } else if (p.interested === false) {
                showInterestState(false);
            }
        } catch(e) {
            body.innerHTML = `<div class="results-empty">${I18N.network_error}</div>`;
        }
    }

    function closePostingModal() {
        const overlay = document.getElementById('posting-modal-overlay');
        overlay.classList.remove('open');
        document.body.style.overflow = '';
        currentPostingId = null;
    }

    document.getElementById('posting-modal-close').addEventListener('click', closePostingModal);
    document.getElementById('posting-modal-overlay').addEventListener('click', function(e) {
        if (e.target === this) closePostingModal();
    });
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && document.getElementById('posting-modal-overlay').classList.contains('open')) {
            closePostingModal();
        }
    });

    // ============================================================
    // INTEREST FEEDBACK
    // ============================================================
    document.getElementById('btn-interested').addEventListener('click', function() {
        pendingInterest = true;
        document.getElementById('interest-reason-row').style.display = 'flex';
        document.getElementById('interest-reason').focus();
        this.classList.add('active');
        document.getElementById('btn-not-interested').classList.remove('active');
        // Can submit immediately (reason is optional)
        submitInterest();
    });

    document.getElementById('btn-not-interested').addEventListener('click', function() {
        pendingInterest = false;
        document.getElementById('interest-reason-row').style.display = 'flex';
        document.getElementById('interest-reason').focus();
        this.classList.add('active');
        document.getElementById('btn-interested').classList.remove('active');
        // Show reason input but don't submit yet — reason is more valuable for "not interested"
    });

    document.getElementById('btn-interest-submit').addEventListener('click', submitInterest);
    document.getElementById('interest-reason').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); submitInterest(); }
    });

    async function submitInterest() {
        if (pendingInterest === null || !currentPostingId) return;
        const reason = document.getElementById('interest-reason').value.trim() || null;

        try {
            const res = await fetch('/api/search/interest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    posting_id: currentPostingId,
                    interested: pendingInterest,
                    reason: reason,
                }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            showInterestState(pendingInterest);

            // Update tile in grid
            const tile = document.querySelector(`.result-tile[data-posting-id="${currentPostingId}"]`);
            if (tile) {
                tile.classList.remove('tile-interested', 'tile-not-interested');
                tile.classList.add(pendingInterest ? 'tile-interested' : 'tile-not-interested');
                // Update interest icon
                tile.querySelectorAll('.tile-interest-icon').forEach(i => i.remove());
                const header = tile.querySelector('.tile-header');
                if (header) {
                    const icon = document.createElement('span');
                    icon.className = 'tile-interest-icon';
                    icon.textContent = pendingInterest ? '👍' : '👎';
                    icon.title = pendingInterest ? I18N.interest_already_yes : I18N.interest_already_no;
                    header.appendChild(icon);
                }
            }
        } catch(e) {
            console.error('Interest save failed:', e);
        }
    }

    function showInterestState(interested) {
        document.getElementById('interest-reason-row').style.display = 'none';
        const fb = document.getElementById('interest-feedback');
        fb.style.display = '';
        fb.textContent = I18N.interest_saved;
        fb.className = 'interest-feedback ' + (interested ? 'interest-positive' : 'interest-negative');

        document.getElementById('btn-interested').classList.toggle('active', interested === true);
        document.getElementById('btn-not-interested').classList.toggle('active', interested === false);
    }

    // ============================================================
    // PANEL MAXIMIZE / RESTORE
    // ============================================================
    document.querySelectorAll('.panel-maximize-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const panelId = this.dataset.panel;

            // Results grid — special case (fixed overlay)
            if (panelId === 'results') {
                const section = document.getElementById('search-results-section');
                const isMax = section.classList.toggle('maximized');
                this.textContent = isMax ? '⊗' : '⛶';
                this.title = isMax ? 'Restore' : 'Maximize';
                return;
            }

            const panels = document.querySelector('.search-panels');
            const panel = panels.querySelector('.' + panelId);
            if (!panel) return;

            const wasMax = panel.classList.contains('maximized');

            // Remove all maximized states
            panels.querySelectorAll('.search-panel').forEach(p => p.classList.remove('maximized'));
            panels.classList.remove('has-maximized');
            panels.querySelectorAll('.panel-maximize-btn').forEach(b => {
                b.textContent = '⛶'; b.title = 'Maximize';
            });

            if (!wasMax) {
                panel.classList.add('maximized');
                panels.classList.add('has-maximized');
                this.textContent = '⊗';
                this.title = 'Restore';
            }

            // Leaflet needs to know the map container resized
            setTimeout(() => { map.invalidateSize(); }, 100);
        });
    });

    // ============================================================
    // FILTER ACTIONS — reload from profile, clear, load saved, save
    // ============================================================

    // 1. Reload defaults from profile
    document.getElementById('btn-reload-profile').addEventListener('click', async function() {
        const feedback = document.getElementById('save-feedback');
        try {
            // Clear current filters first
            state.domains = [];
            state.ql = [];
            state.geoLocations = [];
            state.professions = [];
            state.states = [];
            state.cities = [];
            saveState();

            // Re-init from profile scope
            await initProfileScope();
            doSearch();
            feedback.textContent = I18N.profile_reloaded || '✓';
            feedback.className = 'save-feedback success';
        } catch(e) {
            feedback.textContent = I18N.save_error;
            feedback.className = 'save-feedback error';
        }
        setTimeout(() => { feedback.textContent = ''; }, 3000);
    });

    // 2. Clear all filters
    document.getElementById('btn-clear-filters').addEventListener('click', function() {
        state.domains = [];
        state.ql = [];
        state.geoLocations = [];
        state.professions = [];
        state.states = [];
        state.cities = [];
        saveState();
        // Clear geo layers
        updateGeoLayers();
        // Reset map view to Germany center
        map.setView([51.1657, 10.4515], 6);
        doSearch();
    });

    // 3. Load saved search
    document.getElementById('btn-load-saved').addEventListener('click', async function() {
        const feedback = document.getElementById('save-feedback');
        try {
            // Clear current state first
            state.domains = [];
            state.ql = [];
            state.geoLocations = [];
            state.professions = [];
            state.states = [];
            state.cities = [];

            await loadSavedSearch();
            doSearch();
            feedback.textContent = I18N.load_success || '✓ Loaded';
            feedback.className = 'save-feedback success';
        } catch(e) {
            feedback.textContent = I18N.save_error;
            feedback.className = 'save-feedback error';
        }
        setTimeout(() => { feedback.textContent = ''; }, 3000);
    });

    // ============================================================
    // SAVE SEARCH
    // ============================================================
    document.getElementById('btn-save-search').addEventListener('click', async function() {
        const body = {};
        if (state.domains.length > 0) body.domains = state.domains;
        if (state.ql.length > 0) body.ql = state.ql;
        if (state.states.length > 0) body.states = state.states;
        if (state.professions.length > 0) body.professions = state.professions;
        // Multi-location (full list) + legacy single-location for backward compat
        if (state.geoLocations.length > 0) {
            body.lat      = state.geoLocations[0].lat;
            body.lon      = state.geoLocations[0].lon;
            body.radius_km = state.geoLocations[0].radius_km;
            body.geo_locations = state.geoLocations.map(g => ({lat: g.lat, lon: g.lon, radius_km: g.radius_km}));
        }

        const feedback = document.getElementById('save-feedback');
        try {
            const res = await fetch('/api/search/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json();
                feedback.textContent = err.error || I18N.save_error;
                feedback.className = 'save-feedback error';
            } else {
                feedback.textContent = I18N.save_success;
                feedback.className = 'save-feedback success';
            }
        } catch(e) {
            feedback.textContent = I18N.network_error;
            feedback.className = 'save-feedback error';
        }
        setTimeout(() => { feedback.textContent = ''; }, 3000);
    });

    // ============================================================
    // LOAD SAVED SEARCH + AUTO-SEED FROM PROFILE
    // ============================================================
    async function loadSavedSearch() {
        try {
            const res = await fetch('/api/search/saved');
            if (!res.ok) return;
            const data = await res.json();
            if (data.search_params) {
                const sp = data.search_params;
                if (sp.domains) state.domains = sp.domains;
                if (sp.ql) state.ql = sp.ql;
                if (sp.states) state.states = sp.states;
                if (sp.professions) state.professions = sp.professions;
                // Prefer multi-location array, fall back to legacy single lat/lon
                if (sp.geo_locations && sp.geo_locations.length > 0) {
                    state.geoLocations = sp.geo_locations.map(g => ({lat: g.lat, lon: g.lon, radius_km: g.radius_km || 50, label: ''}));
                    const first = sp.geo_locations[0];
                    document.getElementById('radius-select').value = first.radius_km || 50;
                    map.setView([first.lat, first.lon], 10);
                    updateGeoLayers();
                } else if (sp.lat != null && sp.lon != null) {
                    const radius_km = sp.radius_km || 50;
                    state.geoLocations.push({lat: sp.lat, lon: sp.lon, radius_km, label: ''});
                    document.getElementById('radius-select').value = radius_km;
                    map.setView([sp.lat, sp.lon], 10);
                    updateGeoLayers();
                }
            }
        } catch(e) {
            console.warn('Could not load saved search:', e);
        }
    }

    // ============================================================
    // MIRA CHAT WIDGET — Smart FAB pattern
    // ============================================================
    const miraState = {
        isOpen: false,
        hasGreeted: false,
        usesDu: null,
        history: [],
        idleTimer: null,
    };

    function openMiraChat() {
        const widget = document.getElementById('mira-widget');
        miraState.isOpen = true;
        widget.classList.add('open');
        widget.classList.remove('mira-idle');
        resetMiraIdleTimer();
        if (!miraState.hasGreeted) {
            loadMiraGreeting();
            miraState.hasGreeted = true;
        }
        setTimeout(() => document.getElementById('mira-input').focus(), 300);
    }

    function closeMiraChat() {
        const widget = document.getElementById('mira-widget');
        miraState.isOpen = false;
        widget.classList.remove('open', 'mira-idle');
        clearTimeout(miraState.idleTimer);
    }

    function toggleMiraChat() {
        if (miraState.isOpen) closeMiraChat(); else openMiraChat();
    }

    // Idle transparency — after 5s without hover/interaction, dim the chat
    function resetMiraIdleTimer() {
        const widget = document.getElementById('mira-widget');
        widget.classList.remove('mira-idle');
        clearTimeout(miraState.idleTimer);
        if (!miraState.isOpen) return;
        miraState.idleTimer = setTimeout(() => {
            if (miraState.isOpen) widget.classList.add('mira-idle');
        }, 5000);
    }

    // Click outside = close
    document.addEventListener('mousedown', function(e) {
        const widget = document.getElementById('mira-widget');
        if (miraState.isOpen && !widget.contains(e.target)) {
            closeMiraChat();
        }
    });

    // Reset idle on any interaction within the widget
    document.addEventListener('DOMContentLoaded', () => {
        const widget = document.getElementById('mira-widget');
        ['mouseenter', 'mousemove', 'click', 'keydown'].forEach(evt => {
            widget.addEventListener(evt, resetMiraIdleTimer);
        });
    });

    function loadMiraGreeting() {
        addMiraMessage(I18N.mira_greeting, false);
    }

    function addMiraMessage(content, isUser) {
        const container = document.getElementById('mira-messages');
        const msg = document.createElement('div');
        msg.className = `mira-message ${isUser ? 'user' : 'mira'}`;
        msg.textContent = content;
        // Cost transparency hint on assistant messages
        if (!isUser && window.CostHints) {
            const hint = CostHints.create('mira_message', window.SearchConfig.userLang === 'en' ? 'en' : 'de');
            if (hint) { hint.classList.add('cost-hint-block'); msg.appendChild(hint); }
        }
        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
    }

    function showMiraTyping() {
        const container = document.getElementById('mira-messages');
        const typing = document.createElement('div');
        typing.className = 'mira-typing'; typing.id = 'mira-typing';
        typing.innerHTML = '<span></span><span></span><span></span>';
        container.appendChild(typing);
        container.scrollTop = container.scrollHeight;
    }

    function hideMiraTyping() {
        const el = document.getElementById('mira-typing'); if (el) el.remove();
    }

    async function sendMiraMessage() {
        const input = document.getElementById('mira-input');
        const text = input.value.trim();
        if (!text) return;
        addMiraMessage(text, true);
        input.value = ''; input.style.height = 'auto';

        if (miraState.usesDu === null) {
            if (/\b(du|dein|dich|dir)\b/i.test(text)) miraState.usesDu = true;
            else if (/\b(Sie|Ihr|Ihnen|Ihre)\b/.test(text)) miraState.usesDu = false;
        }

        showMiraTyping();
        miraState.history.push({ role: 'user', content: text });

        try {
            const response = await fetch('/api/mira/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, uses_du: miraState.usesDu, history: miraState.history.slice(0, -1) })
            });
            hideMiraTyping();
            if (response.ok) {
                const data = await response.json();
                addMiraMessage(data.reply, false);
                miraState.history.push({ role: 'assistant', content: data.reply });
                if (miraState.history.length > 20) miraState.history = miraState.history.slice(-20);

                // Apply search filter actions if present
                if (data.actions && window.applyMiraFilters) {
                    window.applyMiraFilters(data.actions);
                }
            } else {
                addMiraMessage(I18N.mira_error, false);
                miraState.history.pop();
            }
        } catch (error) {
            hideMiraTyping();
            addMiraMessage(I18N.mira_offline, false);
            miraState.history.pop();
        }
    }

    function handleMiraKeydown(event) {
        if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMiraMessage(); }
    }

    // Wire up all Mira button handlers via addEventListener (not onclick)
    function wireMiraHandlers() {
        const fabBtn = document.getElementById('mira-fab-btn');
        const minBtn = document.getElementById('mira-minimize-btn');
        const sendBtn = document.getElementById('mira-send-btn');
        const miraInput = document.getElementById('mira-input');

        if (fabBtn) fabBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleMiraChat();
        });
        if (minBtn) minBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            closeMiraChat();
        });
        if (sendBtn) sendBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            sendMiraMessage();
        });
        if (miraInput) {
            miraInput.addEventListener('keydown', handleMiraKeydown);
            miraInput.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 100) + 'px';
            });
            miraInput.addEventListener('focus', () => {
                cancelMiraAutoCollapse();
                resetMiraIdleTimer();
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wireMiraHandlers);
    } else {
        wireMiraHandlers();
    }

    // Trigger Mira greeting: vibrate FAB, auto-open, then auto-collapse after 4s
    // If user interacts (hovers/clicks/types), cancel the auto-collapse
    let miraAutoCollapseTimer = null;

    function cancelMiraAutoCollapse() {
        if (miraAutoCollapseTimer) {
            clearTimeout(miraAutoCollapseTimer);
            miraAutoCollapseTimer = null;
        }
    }

    function triggerMiraGreeting() {
        const widget = document.getElementById('mira-widget');
        const fab = widget.querySelector('.mira-fab');
        miraState.hasGreeted = true;

        // Check if Mira should stay closed (yogi ignored her 3+ times)
        fetch('/api/mira/greeting')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data && data.suppress_greeting) return; // grumpy yogi — stay closed

                // Cancel auto-collapse on any user interaction with the widget
                ['mouseenter', 'click', 'keydown'].forEach(evt => {
                    widget.addEventListener(evt, cancelMiraAutoCollapse, { once: false });
                });

                setTimeout(() => {
                    fab.classList.add('mira-incoming');
                    setTimeout(() => {
                        fab.classList.remove('mira-incoming');
                        openMiraChat();
                        // Auto-collapse after 4s so user sees greeting but it clears for QL panel
                        miraAutoCollapseTimer = setTimeout(() => {
                            if (miraState.isOpen) closeMiraChat();
                        }, 4000);
                    }, 1200);
                }, 800);
            })
            .catch(() => {
                // On error, still greet (fallback)
                setTimeout(() => {
                    fab.classList.add('mira-incoming');
                    setTimeout(() => {
                        fab.classList.remove('mira-incoming');
                        openMiraChat();
                        miraAutoCollapseTimer = setTimeout(() => {
                            if (miraState.isOpen) closeMiraChat();
                        }, 4000);
                    }, 1200);
                }, 800);
            });
    }

    // ============================================================
    // INIT
    // ============================================================
    async function init() {
        await loadSavedSearch();
        
        // Apply Mira search filters from URL params (e.g. from dashboard chat)
        const urlParams = new URLSearchParams(window.location.search);
        const hasMiraParams = urlParams.has('domains') || urlParams.has('lat') || urlParams.has('ql');
        if (hasMiraParams) {
            const miraFilters = {};
            if (urlParams.has('domains')) miraFilters.domains = urlParams.get('domains').split(',');
            if (urlParams.has('ql')) miraFilters.ql = urlParams.get('ql').split(',').map(Number);
            if (urlParams.has('lat') && urlParams.has('lon')) {
                miraFilters.lat = parseFloat(urlParams.get('lat'));
                miraFilters.lon = parseFloat(urlParams.get('lon'));
                miraFilters.radius_km = parseInt(urlParams.get('radius_km') || '50');
                if (urlParams.has('city')) miraFilters.city = urlParams.get('city');
            }
            window.applyMiraFilters({ set_filters: miraFilters });
            // Clean URL without reloading
            window.history.replaceState({}, '', '/search');
        }
        
        // Restore previous filter state from localStorage — but only when
        // no Mira URL params overrode the state above
        let hadSaved = false;
        if (!hasMiraParams) {
            hadSaved = restoreState();

            // If geo was restored, redraw map layers + set radius dropdown
            if (hadSaved && state.geoLocations.length > 0) {
                const g0 = state.geoLocations[0];
                document.getElementById('radius-select').value = String(g0.radius_km || 50);
                map.setView([g0.lat, g0.lon], 10);
                updateGeoLayers();
            }
        }

        // Restore active tab (or default to 'situation')
        switchTab(state.activeTab || 'situation');

        // Load situation questionnaire answers from API
        loadSituationContext();

        // Load profile scope (infer domain/QL/geo from CV) — only fills
        // empty slots, so restored filters take priority
        await initProfileScope();
        doSearch();
        // Fix Leaflet tile rendering — force recalculation after layout resolves
        // Only invalidate if the map is currently visible (on location or power tab)
        setTimeout(() => {
            const mapEl = document.getElementById('search-map');
            if (mapEl && mapEl.offsetWidth > 0) {
                map.invalidateSize(); map.setView(map.getCenter());
            }
        }, 200);
        setTimeout(() => {
            const mapEl = document.getElementById('search-map');
            if (mapEl && mapEl.offsetWidth > 0) map.invalidateSize();
        }, 1000);
        // Watch for container resize (window resize, sidebar toggle)
        if (window.ResizeObserver) {
            const mapEl = document.getElementById('search-map');
            const ro = new ResizeObserver(() => { if (mapEl.offsetWidth > 0) map.invalidateSize(); });
            ro.observe(mapEl);
            // Also watch the panels container (catches grid reflow on zoom)
            const panels = document.querySelector('.search-panels');
            if (panels) ro.observe(panels);
            // Re-render sparkline when right panel resizes (e.g. layout shift)
            const sparkEl = document.getElementById('intel-activity');
            if (sparkEl) {
                let _sparkTimer;
                new ResizeObserver(() => {
                    clearTimeout(_sparkTimer);
                    _sparkTimer = setTimeout(() => {
                        if (_lastSparklineDays) renderSparkline(_lastSparklineDays);
                    }, 100);
                }).observe(sparkEl);
            }
        }
        // Browser zoom triggers 'resize' — Leaflet needs invalidateSize
        let _zoomTimer;
        window.addEventListener('resize', function() {
            clearTimeout(_zoomTimer);
            _zoomTimer = setTimeout(() => {
                const m = document.getElementById('search-map');
                if (m && m.offsetWidth > 0) { map.invalidateSize(); map.setView(map.getCenter()); }
            }, 150);
        });
        // Vibrate + open Mira
        triggerMiraGreeting();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Sidebar toggle
    window.toggleSidebar = function() {
        document.getElementById('sidebar').classList.toggle('open');
    };

    // Expose for sidebar toggle
    window.toggleMiraChat = toggleMiraChat;

    // ============================================================
    // MIRA FILTER ACTIONS — exposed for chat response handling
    // ============================================================
    window.applyMiraFilters = function(actions) {
        if (!actions || !actions.set_filters) return;
        const filters = actions.set_filters;
        let changed = false;

        // Set domains
        if (filters.domains && Array.isArray(filters.domains)) {
            state.domains = filters.domains;
            changed = true;
        }

        // Set qualification levels
        if (filters.ql && Array.isArray(filters.ql)) {
            state.ql = filters.ql;
            changed = true;
        }

        // Set city/location
        if (filters.lat != null && filters.lon != null) {
            const radius_km = filters.radius_km || 50;
            const label = filters.city || '';
            state.geoLocations.push({lat: filters.lat, lon: filters.lon, radius_km, label});

            // Update city input display
            const cityInput = document.getElementById('city-search');
            if (cityInput && filters.city) {
                cityInput.value = '';
            }

            // Update radius dropdown
            const radiusSelect = document.getElementById('radius-select');
            if (radiusSelect) {
                radiusSelect.value = String(radius_km);
            }
            const radiusSelectPower = document.getElementById('radius-select-power');
            if (radiusSelectPower) {
                radiusSelectPower.value = String(radius_km);
            }

            // Pan map and draw circles
            map.setView([filters.lat, filters.lon], 10);
            updateGeoLayers();
            changed = true;
        }

        if (changed) {
            doSearch();
            // Ensure map tiles reload after filter-driven view change
            setTimeout(() => { const m = document.getElementById('search-map'); if (m && m.offsetWidth > 0) map.invalidateSize(); }, 200);
        }
    };
})();
