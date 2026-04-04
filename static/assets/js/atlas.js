// atlas.js - Heritage Map logic (ported from provided index.html)
let GI_DATA = {};

// Elements
const mapHost = document.getElementById("mapHost");
const loading = document.getElementById("loading");

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

const btnDistrictName = document.getElementById("btnDistrictName");
const viewProductsContainer = document.getElementById("viewProductsContainer");

// Helpers
function norm(s) { return (s || "").trim(); }
function toKey(s) { return norm(s).toLowerCase(); }

async function fetchGIData() {
    try {
        const res = await fetch('/api/atlas/districts');
        if (!res.ok) throw new Error("Failed to load atlas dataset");
        const dataArr = await res.json();

        GI_DATA = {};
        dataArr.forEach(item => {
            if (item && item.zilla) GI_DATA[toKey(item.zilla)] = item;
        });
    } catch (err) {
        console.error("Data Load Error:", err);
        if (giStory) giStory.textContent = "Error loading database. Please ensure the Atlas API is available.";
    }
}

function hideInfo() {
    if (!emptyState || !contentState) return;
    emptyState.style.opacity = "1";
    emptyState.style.transform = "translateX(0)";
    emptyState.style.pointerEvents = "auto";

    contentState.style.opacity = "0";
    contentState.style.transform = "translateX(2rem)";
    contentState.style.pointerEvents = "none";
}

function showInfo(districtName) {
    const name = norm(districtName);
    const key = toKey(name);

    if (districtTitle) districtTitle.textContent = name || "Unknown";
    if (districtIdDisplay) districtIdDisplay.textContent = `ID: ${name.substring(0,3).toUpperCase()}-${Math.floor(100 + Math.random()*900)}`;

    const info = GI_DATA[key];

    if (info) {
        if (giTitle) {
            giTitle.textContent = info.product;
            giTitle.style.color = "#f3e5ab";
        }
        if (giStory) giStory.innerHTML = info.story || "";
        if (giCategory) giCategory.textContent = (info.category || "General");

        if (info.product === "No Official GI Product") {
            if (giTitle) giTitle.style.color = "#64748b";
            if (categoryBadge) {
                categoryBadge.textContent = "Not Listed";
                categoryBadge.className = "text-[10px] font-bold text-slate-500 uppercase tracking-widest";
            }
            if (viewProductsContainer) viewProductsContainer.classList.add("hidden");
        } else {
            if (categoryBadge) {
                categoryBadge.textContent = "GI Certified";
                categoryBadge.className = "text-[10px] font-bold text-yellow-500 uppercase tracking-widest";
            }

            if (btnDistrictName) btnDistrictName.textContent = name;
            if (viewProductsContainer) {
                viewProductsContainer.classList.remove("hidden");
                const btn = viewProductsContainer.querySelector("button");
                // Always make the CTA clickable for GI-listed districts.
                // We route to the shop page and let the backend filter by district.
                if (btn) {
                    const url = `/shop?district=${encodeURIComponent(name)}`;
                    btn.onclick = () => { window.location.href = url; };
                }
            }
        }
    } else {
        if (giTitle) {
            giTitle.textContent = "No Official GI Product";
            giTitle.style.color = "#64748b";
        }
        if (giStory) giStory.textContent = "Currently, this district does not have an officially registered Geographical Indication (GI) product of Bangladesh.";
        if (giCategory) giCategory.textContent = "N/A";
        if (categoryBadge) {
            categoryBadge.textContent = "Not Listed";
            categoryBadge.className = "text-[10px] font-bold text-slate-500 uppercase tracking-widest";
        }
        if (viewProductsContainer) viewProductsContainer.classList.add("hidden");
    }

    if (!emptyState || !contentState) return;
    emptyState.style.opacity = "0";
    emptyState.style.transform = "translateX(-2rem)";
    emptyState.style.pointerEvents = "none";

    contentState.style.opacity = "1";
    contentState.style.transform = "translateX(0)";
    contentState.style.pointerEvents = "auto";
}

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
    if (!mapHost) return;

    await fetchGIData();

    try {
        const res = await fetch('/static/assets/maps/geoBoundaries-BGD-ADM2.svg');
        let svgText;

        if (res.ok) {
            svgText = await res.text();
        } else {
            svgText = `<div class="flex items-center justify-center h-full text-slate-500 text-xs">Map file 'geoBoundaries-BGD-ADM2.svg' not found. Please add it to your project folder.</div>`;
        }

        mapHost.innerHTML = svgText;
        if (loading) loading.remove();

        const svg = mapHost.querySelector("svg");
        if (!svg) return;

        if (!svg.getAttribute("viewBox")) {
            const w = svg.getAttribute("width") || 800;
            const h = svg.getAttribute("height") || 1000;
            svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
        }
        svg.removeAttribute("width");
        svg.removeAttribute("height");

        const paths = svg.querySelectorAll("path");
        buildLabels(svg, paths);

        if (toggleLabels) {
            toggleLabels.addEventListener("change", () => {
                if (toggleLabels.checked) mapHost.classList.add("labels-visible");
                else mapHost.classList.remove("labels-visible");
            });
        }

        paths.forEach(p => {
            p.addEventListener("click", (e) => {
                e.stopPropagation();
                clearActive(svg);
                p.classList.add("active");
                showInfo(getDistrictName(p));
            });
        });

        if (resetBtn) {
            resetBtn.addEventListener("click", () => {
                clearActive(svg);
                if (toggleLabels) toggleLabels.checked = false;
                mapHost.classList.remove("labels-visible");
                hideInfo();
            });
        }

        // Clicking outside: deselect
        mapHost.addEventListener("click", () => {
            clearActive(svg);
            hideInfo();
        });

    } catch (err) {
        mapHost.innerHTML = `<div class="text-red-400 p-4 border border-red-500/20 rounded bg-red-500/10">System Error: ${err.message}</div>`;
    }
}

// Auto init on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    // Only run if the home page contains the map
    if (document.getElementById("mapHost") && (document.getElementById("heritage-map") || window.location.pathname === '/heritage-atlas')) {
        initMap();
    }
});
