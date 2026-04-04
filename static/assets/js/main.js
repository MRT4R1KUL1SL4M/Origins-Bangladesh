// main.js - global behaviors (ported from original index.html)

// =====================
// BUYER GLOBAL MENU DRAWER
// =====================
function _toggleBuyerMenuDrawer(open) {
    const drawer = document.getElementById('buyerMenuDrawer');
    const overlay = document.getElementById('buyerMenuOverlay');
    if (!drawer || !overlay) return;
    const shouldOpen = (open === undefined) ? drawer.classList.contains('-translate-x-full') : !!open;

    if (shouldOpen) {
        overlay.classList.remove('hidden');
        drawer.classList.remove('-translate-x-full');
        drawer.setAttribute('aria-hidden', 'false');
        // Render lucide icons if available
        try { if (window.lucide) window.lucide.createIcons(); } catch (e) {}
    } else {
        overlay.classList.add('hidden');
        drawer.classList.add('-translate-x-full');
        drawer.setAttribute('aria-hidden', 'true');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('buyerMenuToggle');
    const overlay = document.getElementById('buyerMenuOverlay');
    const drawer = document.getElementById('buyerMenuDrawer');
    if (btn) {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            _toggleBuyerMenuDrawer(true);
        });
    }
    if (overlay) {
        overlay.addEventListener('click', () => _toggleBuyerMenuDrawer(false));
    }
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') _toggleBuyerMenuDrawer(false);
    });
    // Prevent clicks inside drawer from closing anything else
    if (drawer) {
        drawer.addEventListener('click', (e) => e.stopPropagation());
    }
});


// Cinematic Scroll Animation Observer
        const observerOptions = {
            threshold: 0.1,
            rootMargin: "0px 0px -50px 0px"
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Select elements to animate
        document.querySelectorAll('.reveal-up, .reveal-left, .reveal-right, .reveal-scale').forEach(el => {
            observer.observe(el);
        });

        // GI Tag Verification (real)
        async function verifyProduct() {
            const input = document.getElementById('giCodeInput');
            const btn = document.querySelector('button[onclick="verifyProduct()"]');
            const result = document.getElementById('verify-result');
            const icon = document.getElementById('verify-result-icon');
            const text = document.getElementById('verify-result-text');

            if (!input || !btn || !result || !icon || !text) return;

            const code = (input.value || '').trim();
            if (!code) {
                result.classList.remove('hidden');
                result.className = 'mt-6 p-4 rounded-xl text-center border text-sm font-semibold bg-rose-50 border-rose-200 text-rose-900';
                icon.innerHTML = '<i class="fa-solid fa-circle-xmark"></i>';
                text.textContent = 'Please enter a GI tag code.';
                return;
            }

            const originalContent = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i> Verifying...';

            try {
                const res = await fetch('/api/gi/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code })
                });
                const data = await res.json();

                result.classList.remove('hidden');

                if (data && data.ok) {
                    const suspicious = !!data.suspicious;
                    result.className = 'mt-6 p-4 rounded-xl text-center border text-sm font-semibold ' +
                        (suspicious ? 'bg-amber-50 border-amber-200 text-amber-900' : 'bg-emerald-50 border-emerald-200 text-emerald-900');
                    icon.innerHTML = suspicious
                        ? '<i class="fa-solid fa-triangle-exclamation"></i>'
                        : '<i class="fa-solid fa-circle-check"></i>';

                    const p = data.data && data.data.product ? data.data.product : null;
                    const title = p && p.title ? ` — ${p.title}` : '';
                    text.textContent = (data.message || 'Verified.') + title;
                } else {
                    const status = (data && data.status) || 'error';
                    result.className = 'mt-6 p-4 rounded-xl text-center border text-sm font-semibold bg-rose-50 border-rose-200 text-rose-900';
                    icon.innerHTML = '<i class="fa-solid fa-circle-xmark"></i>';

                    let label = data && data.message ? data.message : 'Unable to verify this code.';
                    if (status === 'revoked') label = data.message || 'This GI tag has been revoked.';
                    if (status === 'not_found') label = data.message || 'No match found in our registry.';
                    if (status === 'invalid_format') label = data.message || 'Invalid code format.';
                    text.textContent = label;
                }
            } catch (e) {
                result.classList.remove('hidden');
                result.className = 'mt-6 p-4 rounded-xl text-center border text-sm font-semibold bg-rose-50 border-rose-200 text-rose-900';
                icon.innerHTML = '<i class="fa-solid fa-circle-xmark"></i>';
                text.textContent = 'Verification service unavailable. Please try again.';
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalContent;
            }
        }

        // Allow Enter key to trigger verification in the home section
        document.addEventListener('DOMContentLoaded', () => {
            const input = document.getElementById('giCodeInput');
            if (!input) return;
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    verifyProduct();
                }
            });
        });


        // Live Count Animation with Intersection Observer
        const countObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const counter = entry.target;
                    const target = +counter.getAttribute('data-target');
                    const duration = 2000; // ms
                    const increment = target / (duration / 30);
                    
                    let count = 0;
                    const updateCount = () => {
                        count += increment;
                        if (count < target) {
                            counter.innerText = Math.ceil(count).toLocaleString() + (target > 100 ? '+' : '');
                            setTimeout(updateCount, 30);
                        } else {
                            counter.innerText = target.toLocaleString() + (target > 100 ? '+' : '');
                        }
                    };
                    updateCount();
                    countObserver.unobserve(counter);
                }
            });
        }, observerOptions);

        document.querySelectorAll('.counter').forEach(el => {
            countObserver.observe(el);
        });

        // =====================
        //  PASSWORD EYE TOGGLE (Global)
        // =====================
        function initPasswordToggles() {
            document.querySelectorAll('[data-password-toggle]').forEach(btn => {
                const wrap = btn.closest('div') || btn.parentElement;
                const input = wrap ? wrap.querySelector('[data-password-field]') : null;
                if (!input) return;
                const eyeOpen = btn.querySelector('[data-eye-open]');
                const eyeClosed = btn.querySelector('[data-eye-closed]');

                btn.addEventListener('click', () => {
                    const isHidden = input.type === 'password';
                    input.type = isHidden ? 'text' : 'password';
                    if (eyeOpen && eyeClosed) {
                        eyeOpen.classList.toggle('hidden', isHidden);
                        eyeClosed.classList.toggle('hidden', !isHidden);
                    }
                    btn.setAttribute('aria-label', isHidden ? 'Hide' : 'Show');
                });
            });
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initPasswordToggles);
        } else {
            initPasswordToggles();
        }

        // Flash Sale Duration Display
        let flashSaleCountdownTimer = null;

        function padCountdown(value) {
            return String(Math.max(0, Math.floor(Number(value) || 0))).padStart(2, '0');
        }

        function parseFallbackDurationSeconds(rawText) {
            const text = String(rawText || '').trim();
            if (!text) return 0;
            let total = 0;
            const hours = text.match(/(\d+)\s*h/i);
            const minutes = text.match(/(\d+)\s*m/i);
            const seconds = text.match(/(\d+)\s*s/i);
            if (hours) total += Number(hours[1]) * 3600;
            if (minutes) total += Number(minutes[1]) * 60;
            if (seconds) total += Number(seconds[1]);
            if (total > 0) return total;
            if (/^\d+$/.test(text)) return Number(text);
            return 0;
        }

        function formatCountdown(totalSeconds) {
            const safeSeconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
            const hours = Math.floor(safeSeconds / 3600);
            const minutes = Math.floor((safeSeconds % 3600) / 60);
            const seconds = safeSeconds % 60;
            return {
                hours: padCountdown(hours),
                minutes: padCountdown(minutes),
                seconds: padCountdown(seconds),
                text: `${hours}h ${padCountdown(minutes)}m ${padCountdown(seconds)}s`,
            };
        }

        function animateCountdownCell(cell, nextValue) {
            if (!cell) return;
            const value = String(nextValue);
            if (cell.dataset.value === value) return;
            cell.dataset.value = value;
            cell.textContent = value;
            cell.classList.remove('flash-tick');
            void cell.offsetWidth;
            cell.classList.add('flash-tick');
            window.setTimeout(() => cell.classList.remove('flash-tick'), 240);
        }

        function renderCountdownElement(element, formatted) {
            const hoursCell = element.querySelector('[data-unit="hours"]');
            const minutesCell = element.querySelector('[data-unit="minutes"]');
            const secondsCell = element.querySelector('[data-unit="seconds"]');

            if (hoursCell || minutesCell || secondsCell) {
                animateCountdownCell(hoursCell, formatted.hours);
                animateCountdownCell(minutesCell, formatted.minutes);
                animateCountdownCell(secondsCell, formatted.seconds);
                element.setAttribute('aria-label', `Flash sale countdown ${formatted.hours} hours ${formatted.minutes} minutes ${formatted.seconds} seconds`);
                return;
            }

            element.innerText = formatted.text;
        }

        function inferCountdownWindow(startDate, startTime, endDate, endTime) {
            const today = new Date();
            const safeStartDate = String(startDate || '').trim() || today.toISOString().slice(0, 10);
            const safeEndDate = String(endDate || '').trim() || safeStartDate;
            const safeStartTime = String(startTime || '').trim();
            const safeEndTime = String(endTime || '').trim();
            if (!safeStartTime || !safeEndTime) return { startAt: null, endAt: null };
            const startAt = new Date(`${safeStartDate}T${safeStartTime}:00`);
            let endAt = new Date(`${safeEndDate}T${safeEndTime}:00`);
            if (Number.isNaN(startAt.getTime()) || Number.isNaN(endAt.getTime())) return { startAt: null, endAt: null };
            if (endAt.getTime() <= startAt.getTime()) {
                endAt = new Date(endAt.getTime() + 24 * 60 * 60 * 1000);
            }
            return { startAt, endAt };
        }

        async function resolveCountdownConfig(element) {
            const rawConfig = {
                live: (element.getAttribute('data-live') || '').trim(),
                startAt: (element.getAttribute('data-start-at') || '').trim(),
                endAt: (element.getAttribute('data-end-at') || '').trim(),
                startDate: (element.getAttribute('data-start-date') || '').trim(),
                endDate: (element.getAttribute('data-end-date') || '').trim(),
                startTime: (element.getAttribute('data-start-time') || '').trim(),
                endTime: (element.getAttribute('data-end-time') || '').trim(),
                fallbackText: (element.getAttribute('data-fallback-text') || '').trim() || '0h 00m 00s',
                durationSeconds: Number(element.getAttribute('data-duration-seconds') || 0),
                remainingSeconds: Number(element.getAttribute('data-remaining-seconds') || 0),
                liveStartedAt: (element.getAttribute('data-live-started-at') || '').trim(),
            };

            try {
                const response = await fetch('/api/artisan-hour', { cache: 'no-store' });
                const data = await response.json();
                if (response.ok && data && data.ok) {
                    rawConfig.live = String(data.live ?? rawConfig.live);
                    rawConfig.startAt = (data.start_at || rawConfig.startAt || '').trim();
                    rawConfig.endAt = (data.end_at || rawConfig.endAt || '').trim();
                    rawConfig.startDate = (data.start_date || rawConfig.startDate || '').trim();
                    rawConfig.endDate = (data.end_date || rawConfig.endDate || '').trim();
                    rawConfig.startTime = (data.start || rawConfig.startTime || '').trim();
                    rawConfig.endTime = (data.end || rawConfig.endTime || '').trim();
                    rawConfig.fallbackText = (data.total_hours_display || rawConfig.fallbackText || '0h 00m 00s').trim();
                    rawConfig.durationSeconds = Number(data.duration_seconds || rawConfig.durationSeconds || 0);
                    rawConfig.remainingSeconds = Number(data.remaining_seconds || rawConfig.remainingSeconds || 0);
                    rawConfig.liveStartedAt = (data.live_started_at || rawConfig.liveStartedAt || '').trim();
                }
            } catch (error) {
                console.warn('Flash countdown config fetch failed:', error);
            }

            let startAt = rawConfig.startAt ? new Date(rawConfig.startAt) : null;
            let endAt = rawConfig.endAt ? new Date(rawConfig.endAt) : null;
            let liveStartedAt = rawConfig.liveStartedAt ? new Date(rawConfig.liveStartedAt) : null;
            if (!(startAt instanceof Date) || Number.isNaN(startAt?.getTime?.())) startAt = null;
            if (!(endAt instanceof Date) || Number.isNaN(endAt?.getTime?.())) endAt = null;
            if (!(liveStartedAt instanceof Date) || Number.isNaN(liveStartedAt?.getTime?.())) liveStartedAt = null;

            if (!startAt || !endAt) {
                const inferred = inferCountdownWindow(rawConfig.startDate, rawConfig.startTime, rawConfig.endDate, rawConfig.endTime);
                startAt = startAt || inferred.startAt;
                endAt = endAt || inferred.endAt;
            }

            const fallbackSeconds = parseFallbackDurationSeconds(rawConfig.fallbackText);
            const durationSeconds = Number(rawConfig.durationSeconds) > 0
                ? Number(rawConfig.durationSeconds)
                : (startAt && endAt ? Math.max(0, Math.floor((endAt.getTime() - startAt.getTime()) / 1000)) : fallbackSeconds);
            const remainingSeconds = Number(rawConfig.remainingSeconds) > 0
                ? Number(rawConfig.remainingSeconds)
                : durationSeconds;

            return {
                live: rawConfig.live === 'true' || rawConfig.live === '1',
                startAt,
                endAt,
                liveStartedAt,
                durationSeconds,
                remainingSeconds,
                fallbackSeconds: durationSeconds || fallbackSeconds,
            };
        }

        async function startCountdown() {
            const element = document.getElementById('countdown');
            if (!element) return;

            if (flashSaleCountdownTimer) {
                clearInterval(flashSaleCountdownTimer);
                flashSaleCountdownTimer = null;
            }

            const config = await resolveCountdownConfig(element);
            const hasLiveStart = config.liveStartedAt instanceof Date && !Number.isNaN(config.liveStartedAt.getTime());
            let remainingSeconds = config.live ? (config.remainingSeconds || config.durationSeconds || config.fallbackSeconds) : (config.durationSeconds || config.fallbackSeconds);

            const renderCountdown = async () => {
                if (remainingSeconds <= 0) {
                    renderCountdownElement(element, formatCountdown(0));
                    if (flashSaleCountdownTimer) {
                        clearInterval(flashSaleCountdownTimer);
                        flashSaleCountdownTimer = null;
                    }
                    const flashSection = document.getElementById('flash-sale');
                    if (flashSection && config.live) {
                        flashSection.classList.add('hidden');
                    }
                    return;
                }

                renderCountdownElement(element, formatCountdown(remainingSeconds));
                remainingSeconds -= 1;
            };

            await renderCountdown();
            if (config.live || (config.endAt instanceof Date && !Number.isNaN(config.endAt.getTime())) || (hasLiveStart && config.durationSeconds > 0)) {
                flashSaleCountdownTimer = setInterval(renderCountdown, 1000);
            }
        }

// =====================
        //  GLOBAL STATE
        // =====================
        let GI_DATA = {}; 

        // =====================
        //  UI Elements
        // =====================
        const mapHost = document.getElementById("mapHost");
        const loading = document.getElementById("loading");
        
        // Info Card Elements
        const emptyState = document.getElementById("emptyState");
        const contentState = document.getElementById("contentState");
        
        const districtTitle = document.getElementById("districtTitle");
        const giTitle = document.getElementById("giTitle");
        const giStory = document.getElementById("giStory");
        const giCategory = document.getElementById("giCategory");
        const categoryBadge = document.getElementById("categoryBadge");
        const districtIdDisplay = document.getElementById("districtIdDisplay");
        
        const toggleLabels = document.getElementById("toggleLabels");
        const resetBtn = document.getElementById("resetBtn");
        
        // New Buttons
        const btnDistrictName = document.getElementById("btnDistrictName");
        const viewProductsContainer = document.getElementById("viewProductsContainer");

        // =====================
        //  Helper: Normalize Strings
        // =====================
        function norm(s) { return (s || "").trim(); }
        function toKey(s) { return norm(s).toLowerCase(); }

        // =====================
        //  FETCH DATA
        // =====================
        async function fetchGIData() {
            try {
                const res = await fetch('/static/assets/data/districts.json');
                if (!res.ok) throw new Error("Failed to load districts.json");
                
                const dataArr = await res.json();
                
                // Transform array into object map for easier lookup
                // Key will be lowercase 'zilla' name for fuzzy matching
                GI_DATA = {};
                dataArr.forEach(item => {
                    if(item.zilla) {
                        GI_DATA[toKey(item.zilla)] = item;
                    }
                });
                
                console.log("GI Data Loaded:", Object.keys(GI_DATA).length, "districts");

            } catch (err) {
                console.error("Data Load Error:", err);
                if(giStory) giStory.textContent = "Error loading database. Please ensure districts.json is present.";
            }
        }

        // =====================
        //  State Management
        // =====================
        function showInfo(districtName) {
            const name = norm(districtName);
            const key = toKey(name);
            
            // Basic Update
            if(districtTitle) districtTitle.textContent = name || "Unknown";
            if(districtIdDisplay) districtIdDisplay.textContent = `ID: ${name.substring(0,3).toUpperCase()}-${Math.floor(100 + Math.random()*900)}`;

            // Lookup Data
            const info = GI_DATA[key];
            
            if (info) {
                if(giTitle) {
                    giTitle.textContent = info.product;
                    giTitle.style.color = "#f3e5ab"; // Gold text
                }
                if(giStory) giStory.innerHTML = info.story;
                if(giCategory) giCategory.textContent = info.category || "General";
                
                // Update styling based on content
                if(info.product === "No Official GI Product") {
                    if(giTitle) giTitle.style.color = "#64748b"; // Slate text
                    if(categoryBadge) {
                        categoryBadge.textContent = "Not Listed";
                        categoryBadge.className = "text-[10px] font-bold text-slate-500 uppercase tracking-widest";
                    }
                } else {
                    if(categoryBadge) {
                        categoryBadge.textContent = "GI Certified";
                        categoryBadge.className = "text-[10px] font-bold text-yellow-500 uppercase tracking-widest";
                    }
                }
                
            } else {
                // Fallback if district not in JSON
                if(giTitle) {
                    giTitle.textContent = "Data Unavailable";
                    giTitle.style.color = "#64748b";
                }
                if(giStory) giStory.innerHTML = `No data found in database for <b class="text-white">${name}</b>.`;
                if(giCategory) giCategory.textContent = "N/A";
                if(categoryBadge) categoryBadge.textContent = "Unknown";
            }
            
            // Update Button Text + CTA Action
            if (btnDistrictName) btnDistrictName.innerText = name;

            if (viewProductsContainer) {
                // Option 1 behavior: always show the CTA for any selected district.
                // Even if there are no products yet, the user can still navigate to the
                // filtered Shop page and see the empty-state + "View all products".
                const shouldShowCTA = !!name && name !== "Unknown";
                if (shouldShowCTA) {
                    viewProductsContainer.classList.remove("hidden");
                    const btn = viewProductsContainer.querySelector("button");
                    if (btn) {
                        // Ensure this button never behaves like a form submitter
                        btn.type = "button";
                        const url = `/shop?district=${encodeURIComponent(name)}`;
                        btn.onclick = () => { window.location.href = url; };
                    }
                } else {
                    viewProductsContainer.classList.add("hidden");
                    const btn = viewProductsContainer.querySelector("button");
                    if (btn) btn.onclick = null;
                }
            }

            // Animation: Reveal Content
            if(emptyState) {
                emptyState.style.opacity = "0";
                emptyState.style.pointerEvents = "none";
            }
            
            if(contentState) {
                contentState.classList.remove("translate-x-8", "opacity-0", "pointer-events-none");
                contentState.classList.add("translate-x-0", "opacity-100");
            }
        }

        function hideInfo() {
            // Show Empty State
            if(emptyState) {
                emptyState.style.opacity = "1";
                emptyState.style.pointerEvents = "auto";
            }
            
            // Hide Content
            if(contentState) {
                contentState.classList.add("translate-x-8", "opacity-0", "pointer-events-none");
                contentState.classList.remove("translate-x-0", "opacity-100");
            }
            
            if(viewProductsContainer) viewProductsContainer.classList.add("hidden");
        }

        // =====================
        //  Map Helpers
        // =====================
        function clearActive(svg) {
            svg.querySelectorAll("path.active").forEach(p => p.classList.remove("active"));
        }

        function getDistrictName(path) {
            let name = path.getAttribute("data-name") || 
                        path.getAttribute("data-district") || 
                        path.getAttribute("name");

            if (!name) {
                const t = path.querySelector("title");
                if (t && t.textContent) name = t.textContent;
            }
            if (!name) name = path.getAttribute("id");

            return norm(name);
        }

        function buildLabels(svg, paths) {
            let layer = svg.querySelector("#labelLayer");
            if (!layer) {
                layer = document.createElementNS("http://www.w3.org/2000/svg", "g");
                layer.setAttribute("id", "labelLayer");
                svg.appendChild(layer);
            }
            layer.innerHTML = "";

            paths.forEach(p => {
                const district = getDistrictName(p);
                if (!district) return;

                const bb = p.getBBox();
                if (bb.width < 15 || bb.height < 15) return;

                const x = bb.x + bb.width / 2;
                const y = bb.y + bb.height / 2;

                const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
                t.setAttribute("x", x);
                t.setAttribute("y", y);
                t.setAttribute("text-anchor", "middle");
                t.setAttribute("dominant-baseline", "middle");
                t.classList.add("district-label");
                t.textContent = district;

                layer.appendChild(t);
            });

            return layer;
        }

        async function initMap() {
            // 1. Load Data
            await fetchGIData();

            // 2. Load Map
            try {
                const res = await fetch("/static/assets/maps/geoBoundaries-BGD-ADM2.svg");
                let svgText;
                
                if (res.ok) {
                    svgText = await res.text();
                } else {
                    // Fallback Placeholder if SVG missing (minimal fallback to show container)
                    svgText = `<div class="flex items-center justify-center h-full text-slate-500 text-xs">Map file 'geoBoundaries-BGD-ADM2.svg' not found. Please add it to your project folder.</div>`;
                }

                if(mapHost) {
                    mapHost.innerHTML = svgText;
                    if (loading) loading.remove();

                    const svg = mapHost.querySelector("svg");
                    if (!svg) return;

                    // Ensure ViewBox
                    if (!svg.getAttribute("viewBox")) {
                        const w = svg.getAttribute("width") || 800;
                        const h = svg.getAttribute("height") || 1000;
                        svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
                    }
                    svg.removeAttribute("width");
                    svg.removeAttribute("height");

                    const paths = svg.querySelectorAll("path");
                    const labelLayer = buildLabels(svg, paths);
                    
                    // Toggle Logic
                    if(toggleLabels) {
                        toggleLabels.addEventListener("change", () => {
                            if (toggleLabels.checked) {
                                mapHost.classList.add("labels-visible");
                            } else {
                                mapHost.classList.remove("labels-visible");
                            }
                        });
                    }

                    // Click Logic
                    paths.forEach(p => {
                        p.addEventListener("click", (e) => {
                            e.stopPropagation();
                            clearActive(svg);
                            p.classList.add("active");
                            showInfo(getDistrictName(p));
                        });
                    });

                    // Reset
                    if(resetBtn) {
                        resetBtn.addEventListener("click", () => {
                            clearActive(svg);
                            if(toggleLabels) toggleLabels.checked = false;
                            mapHost.classList.remove("labels-visible");
                            hideInfo();
                        });
                    }
                }

            } catch (err) {
                if(mapHost) mapHost.innerHTML = `<div class="text-red-400 p-4 border border-red-500/20 rounded bg-red-500/10">System Error: ${err.message}</div>`;
            }
        }

        // --- GLOBAL MAP LOGIC ---
        const destinations = [
            { name: "London", x: 280, y: 150 },
            { name: "New York", x: 100, y: 220 }, 
            { name: "Toronto", x: 140, y: 180 },
            { name: "Tokyo", x: 880, y: 220 }, 
            { name: "Seoul", x: 820, y: 230 },
            { name: "Beijing", x: 750, y: 200 }, 
            { name: "Bangkok", x: 630, y: 400 },
            { name: "Singapore", x: 610, y: 520 }, 
            { name: "Sydney", x: 900, y: 550 },
            { name: "Dubai", x: 420, y: 320 },
            { name: "Riyadh", x: 400, y: 350 },
            { name: "Berlin", x: 320, y: 160 }
        ];

        function initGlobalMap() {
            const mapSvg = document.getElementById('interactive-global-map');
            if(!mapSvg) return;

            const connectionLayer = document.getElementById('global-map-connections') || mapSvg;
            connectionLayer.innerHTML = '';

            const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
            const safeDestination = (dest) => ({
                ...dest,
                x: clamp(dest.x, 52, 948),
                y: clamp(dest.y, 52, 548)
            });

            function createConnection(rawDest, index) {
                const dest = safeDestination(rawDest);
                setTimeout(() => {
                    const startX = 500;
                    const startY = 300;
                    const midX = (startX + dest.x) / 2;
                    const midY = clamp(((startY + dest.y) / 2) - 90, 70, 520);
                    const pathData = `M ${startX} ${startY} Q ${midX} ${midY} ${dest.x} ${dest.y}`;

                    const line = document.createElementNS("http://www.w3.org/2000/svg", "path");
                    line.setAttribute("d", pathData);
                    line.setAttribute("class", "connection-line");
                    line.style.opacity = "0.1";
                    connectionLayer.appendChild(line);

                    const packet = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                    packet.setAttribute("r", "2");
                    packet.setAttribute("fill", "#fff");
                    packet.setAttribute("filter", "url(#glow)");
                    packet.style.cssText = `offset-path: path('${pathData}'); animation: travelPath ${2 + Math.random() * 2}s ease-in-out infinite;`;
                    connectionLayer.appendChild(packet);

                    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");

                    const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                    ring.setAttribute("cx", dest.x);
                    ring.setAttribute("cy", dest.y);
                    ring.setAttribute("r", "3");
                    ring.setAttribute("fill", "none");
                    ring.setAttribute("stroke", "#00F0FF");
                    ring.setAttribute("stroke-width", "1");
                    ring.setAttribute("opacity", "0.6");
                    const anim = document.createElementNS("http://www.w3.org/2000/svg", "animate");
                    anim.setAttribute("attributeName", "r");
                    anim.setAttribute("values", "3;8;3");
                    anim.setAttribute("dur", "2s");
                    anim.setAttribute("repeatCount", "indefinite");
                    ring.appendChild(anim);
                    g.appendChild(ring);

                    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                    dot.setAttribute("cx", dest.x);
                    dot.setAttribute("cy", dest.y);
                    dot.setAttribute("r", "2");
                    dot.setAttribute("fill", "#fff");
                    g.appendChild(dot);

                    connectionLayer.appendChild(g);
                }, index * 150);
            }

            destinations.forEach((dest, i) => createConnection(dest, i));
        }


        function initAutoFadeSlider(containerId, slideSelector, intervalMs) {
            const container = document.getElementById(containerId);
            if (!container) return;

            const slides = Array.from(container.querySelectorAll(slideSelector));
            if (slides.length <= 1) {
                slides.forEach((slide, index) => slide.classList.toggle('is-active', index === 0));
                return;
            }

            let current = slides.findIndex((slide) => slide.classList.contains('is-active'));
            if (current < 0) current = 0;

            slides.forEach((slide, index) => slide.classList.toggle('is-active', index === current));

            window.setInterval(() => {
                slides[current].classList.remove('is-active');
                current = (current + 1) % slides.length;
                slides[current].classList.add('is-active');
            }, Math.max(1000, Number(intervalMs) || 2000));
        }

        function initHomeShowcaseSlider() {
            initAutoFadeSlider('homeProductShowcase', '.home-product-slide', 3000);
        }

        function initHomeCouponSlider() {
            initAutoFadeSlider('homeCouponShowcase', '.home-coupon-slide', 7000);
        }

        async function copyTextToClipboard(text) {
            const value = String(text || '').trim();
            if (!value) return false;
            try {
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(value);
                    return true;
                }
            } catch (error) {
                console.warn('Clipboard API failed, falling back.', error);
            }

            try {
                const tempInput = document.createElement('textarea');
                tempInput.value = value;
                tempInput.setAttribute('readonly', 'readonly');
                tempInput.style.position = 'fixed';
                tempInput.style.opacity = '0';
                document.body.appendChild(tempInput);
                tempInput.focus();
                tempInput.select();
                const success = document.execCommand('copy');
                document.body.removeChild(tempInput);
                return success;
            } catch (error) {
                console.warn('Fallback copy failed.', error);
                return false;
            }
        }

        function initCouponCopyButtons() {
            const status = document.getElementById('couponCopyStatus');
            let toastTimer = null;

            document.querySelectorAll('.copy-coupon-btn').forEach((button) => {
                button.addEventListener('click', async () => {
                    const code = button.getAttribute('data-code') || '';
                    const copied = await copyTextToClipboard(code);

                    if (status) {
                        status.textContent = copied ? `${code} copied` : 'Copy failed';
                        status.classList.add('show');
                        clearTimeout(toastTimer);
                        toastTimer = window.setTimeout(() => {
                            status.classList.remove('show');
                        }, 1800);
                    }
                });
            });
        }

        window.addEventListener("load", () => {
            startCountdown();
            initHomeShowcaseSlider();
            initHomeCouponSlider();
            initCouponCopyButtons();
            initMap();
            initGlobalMap();
        });


// =====================
// Navbar: Currency switch (UI only)
// =====================
document.addEventListener("DOMContentLoaded", () => {
    const currencyDisplay = document.getElementById("currency-display");
    const saved = localStorage.getItem("currency") || "USD";
    if (currencyDisplay) currencyDisplay.textContent = saved;

    document.querySelectorAll(".currency-option").forEach((el) => {
        el.addEventListener("click", (e) => {
            const href = el.getAttribute("href") || "#";
            const cur = el.getAttribute("data-currency") || "USD";
            // If link is server-driven (/set-currency/...), allow navigation.
            if (href === "#") {
                e.preventDefault();
            }

            localStorage.setItem("currency", cur);
            if (currencyDisplay) currencyDisplay.textContent = cur;
        });
    });
});
