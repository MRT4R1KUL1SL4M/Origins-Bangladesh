
const noop=()=>{};
const fakeEl=()=>({classList:{add:noop,remove:noop,toggle:noop,contains:()=>false},style:{},appendChild:noop,remove:noop,focus:noop,value:'',src:'',textContent:'',innerHTML:'',addEventListener:noop,querySelector:()=>fakeEl(),querySelectorAll:()=>[],dataset:{}});
global.window=global;
global.window.addEventListener=noop;
global.document={getElementById:(id)=>fakeEl(),querySelector:(s)=>fakeEl(),querySelectorAll:(s)=>[],createElement:(t)=>fakeEl(),addEventListener:(ev,cb)=>{ if(ev==='DOMContentLoaded'){ global._domcb=cb; } }};
global.fetch=async (...args)=>({ok:true,json:async()=>({data:{orders:[],transactions:[],artisan_hour:{}, messages:[], profile_settings:{}, revenue_analytics:[], logs:[]}})});
global.FormData = class { append(){} };
global.prompt=()=>null;
global.confirm=()=>true;
global.setTimeout=(cb)=>0;
global.setInterval=(cb)=>0;
global.console=console;

        window.__ADMIN_DASHBOARD__ = {};
        
        // --- Models & Data ---
        const MENU_STRUCTURE = [
            { title: "Overview", items: [{ id: "dashboard", label: "Dashboard", icon: "ph-squares-four" }, { id: "analytics", label: "Analytics Suite", icon: "ph-chart-pie-slice" }] },
            { title: "Artisan Management", id: "group-artisan", icon: "ph-users", items: [{ id: "sellers", label: "Artisan Directory", icon: "ph-address-book" }, { id: "verification", label: "Verification Hub", icon: "ph-shield-check" }, { id: "messages", label: "Communications", icon: "ph-chats-teardrop" }] },
            { title: "Product & Heritage", id: "group-product", icon: "ph-package", items: [{ id: "products", label: "Product Catalog", icon: "ph-stack" }, { id: "qc", label: "Quality Control", icon: "ph-clipboard-text" }, { id: "gi-verify", label: "GI Certification", icon: "ph-medal" }] },
            { title: "Commerce Engine", id: "group-sales", icon: "ph-tote", items: [{ id: "orders", label: "Order Logistics", icon: "ph-truck" }, { id: "flash-sale", label: "The Artisan's Hour", icon: "ph-lightning" }] },
            { title: "Financials", id: "group-finance", icon: "ph-money", items: [{ id: "finance", label: "Ledger & Payouts", icon: "ph-bank" }, { id: "commission", label: "Commission Logic", icon: "ph-percent" }] },
            { title: "Platform & Content", id: "group-content", icon: "ph-devices", items: [{ id: "todays-artisan", label: "Featured Artisan", icon: "ph-star" }, { id: "site-content", label: "Site Experience", icon: "ph-monitor" }, { id: "journal", label: "Heritage Journal", icon: "ph-scroll" }, { id: "content-team", label: "Editorial Team", icon: "ph-users-three" }, { id: "coupons", label: "Coupon Codes", icon: "ph-ticket" }] },
            { title: "Governance", id: "group-safety", icon: "ph-shield-warning", items: [{ id: "users", label: "User Accounts", icon: "ph-user-gear" }, { id: "moderation", label: "Disputes & Reviews", icon: "ph-gavel" }, { id: "logs", label: "Audit Logs", icon: "ph-clock-counter-clockwise" }] }
        ];

        let MOCK_SELLERS = [
            { id: 1, name: "Karim Handicrafts", email: "karim@crafts.com", type: "Nakshi Kantha", status: "Active", district: "Jessore", rating: 4.8, sales: 120, img: "https://api.dicebear.com/7.x/initials/svg?seed=Karim&backgroundColor=FAF8F5&textColor=C27803" },
            { id: 2, name: "Heritage Pottery", email: "contact@heritagepottery.bd", type: "Pottery", status: "Active", district: "Comilla", rating: 4.9, sales: 85, img: "https://api.dicebear.com/7.x/initials/svg?seed=Heritage&backgroundColor=FAF8F5&textColor=C27803" },
            { id: 3, name: "Tarik Artisan Shop", email: "titarek@gmail.com", type: "Textile", status: "Pending Verification", district: "Kaliganj", rating: 4.2, sales: 0, img: "https://api.dicebear.com/7.x/initials/svg?seed=Tarik&backgroundColor=FAF8F5&textColor=C27803" }
        ];

        let MOCK_PRODUCTS = [
            { id: 101, name: "Premium Jamdani Saree", price: 12500, stock: 12, sold: 45, seller: "Jamdani Palace", seller_mail: "info@jamdani.com", status: "Live", gi_status: "Certified", img: "ph-package" },
            { id: 102, name: "Terracotta Flower Vase", price: 450, stock: 50, sold: 120, seller: "Heritage Pottery", seller_mail: "contact@heritage.bd", status: "Live", gi_status: "None", img: "ph-potted-plant" },
            { id: 103, name: "Handwoven Saree", price: 2200, stock: 5, sold: 2, seller: "Taant Ghor", seller_mail: "taant@ghor.com", status: "Draft", gi_status: "Pending", img: "ph-image" }
        ];

        let MOCK_ORDERS = [
            { id: "ORD-9921", customer: "Rahat Khan", email: "rahat@gmail.com", items: "1x Jamdani Saree", total: 12500, trxId: "TRX-7738229", status: "Processing", date: "Today, 10:30 AM" },
            { id: "ORD-9920", customer: "Sadia Islam", email: "sadia@outlook.com", items: "2x Clay Pot", total: 900, trxId: "TRX-7738231", status: "Shipped", date: "Yesterday, 4:15 PM" },
            { id: "ORD-9919", customer: "Michael D.", email: "michael@corp.com", items: "1x Silk Scarf", total: 3200, trxId: "TRX-7738100", status: "Delivered", date: "12 May, 11:00 AM" }
        ];

        let MOCK_FLASH_REQ = [
            { id: 1, product: "Nakshi Kantha", seller: "Karim Handicrafts", old_price: 3500, new_price: 2600, status: "Pending" },
            { id: 2, product: "Brass Lamp", seller: "Metal Works BD", old_price: 1200, new_price: 900, status: "Pending" },
            { id: 3, product: "Muslin Scarf", seller: "Dhaka Weaves", old_price: 4500, new_price: 3100, status: "Pending" }
        ];

        let MOCK_JOURNAL = [
            { id: 1, title: "The Art of Muslin Revival", author: "Sarah Kabir", date: "May 10, 2026", status: "Published", views: "12.4k", img: "https://images.unsplash.com/photo-1606294719268-9ee22378939c?q=80&w=2070&auto=format&fit=crop" },
            { id: 2, title: "Pottery Villages of Comilla", author: "Rafiq Ahmed", date: "May 12, 2026", status: "Draft", views: "-", img: "https://images.unsplash.com/photo-1493106641515-6b5631de4bb9?q=80&w=2069&auto=format&fit=crop" },
            { id: 3, title: "Legacy of Jamdani Weavers", author: "Admin", date: "Apr 28, 2026", status: "Published", views: "8.1k", img: "https://images.unsplash.com/photo-1621252179027-94459d278660?q=80&w=2000&auto=format&fit=crop" }
        ];

        let MOCK_GI_REQUESTS = [
            { id: 1, product: "Khadi Panjabi", district: "Cumilla", seller: "Tarik Artisan Shop", status: "Pending", date: "2 days ago" },
            { id: 2, product: "Muslin Fabric", district: "Dhaka", seller: "Weavers of Bengal", status: "Pending", date: "5 hours ago" }
        ];

        let MOCK_VERIFICATIONS = [ { id: 3, name: "Tarik Artisan Shop", loc: "Kaliganj, Gazipur", time: "2 days ago", docs: 3, status: "Pending" } ];
        let MOCK_QC = [ { id: 103, title: "Handwoven Saree", seller: "Taant Ghor", date: "Today, 09:12 AM" }, { id: 102, title: "Clay Vase", seller: "Heritage Pottery", date: "Yesterday, 14:30 PM" }, { id: 104, title: "Nakshi Kantha Frame", seller: "Karim Handicrafts", date: "Apr 28, 2026" } ];
        let MOCK_TEAM = [ { id: 1, name:'Sarah Kabir', role:'Senior Editor', art:24, email: 'sarah@origins.bd' }, { id: 2, name:'Rafiq Ahmed', role:'Contributor', art:8, email: 'rafiq@origins.bd' } ];
        let MOCK_USERS = [ { id: 1, name: "Rahat Khan", email: "rahat@gmail.com", role: "Buyer", status: "Active", time: "2 hours ago" }, { id: 2, name: "Sadia Islam", email: "sadia@gmail.com", role: "Buyer", status: "Active", time: "1 day ago" }, { id: 3, name: "Tanvir Hasan", email: "tanvir.h@yahoo.com", role: "Merchant", status: "Banned", time: "1 week ago" } ];
        let MOCK_DISPUTES = [ { id: "ORD-9921", issue: "Buyer claims product damaged upon arrival. Seller requested unboxing video.", priority: "High", status: "Open" }, { id: "ORD-9915", issue: "Wrong item delivered (Saree instead of Panjabi).", priority: "Medium", status: "Open" } ];
        let MOCK_TRANSACTIONS = [
            { id: "TRX-7738229", date: "May 14", time: "10:45 AM", type: "Order Payment", amount: 13000, method: "Bkash", status: "Completed", party: "Rahat Khan", email: "rahat@gmail.com" },
            { id: "TRX-7738231", date: "May 13", time: "09:15 PM", type: "Order Payment", amount: 850, method: "Nagad", status: "Completed", party: "Sadia Islam", email: "sadia@outlook.com" },
            { id: "TRX-7738210", date: "May 12", time: "11:20 AM", type: "Payout", amount: -45000, method: "Bank Transfer", status: "Processing", party: "Jamdani Palace", email: "info@jamdani.com" }
        ];

        let MOCK_COUPONS = [
            { id: 1, code: "EID26", discount: "15%", type: "Percentage", limit: "Unlimited", used: 145, expires: "2026-06-30", isNewUser: false, status: "Active" },
            { id: 2, code: "WELCOME", discount: "Free Delivery", type: "Free Delivery", limit: 1000, used: 84, expires: "Never", isNewUser: true, status: "Active" },
            { id: 3, code: "WINTER10", discount: "10%", type: "Percentage", limit: 50, used: 50, expires: "2025-12-31", isNewUser: false, status: "Paused" }
        ];

        let ADMIN_USER = {
            name: "OB Admin",
            email: "admin@origins.com",
            pic: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='-32 -32 320 320'%3E%3Cpath d='M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8ZM72,96a56,56,0,1,1,56,56A56.06,56.06,0,0,1,72,96Z' fill='%23A39A8E'/%3E%3C/svg%3E"
        };
        
        let FEATURED_ARTISAN = {
            name: "Heritage Pottery",
            desc: "Master of Terracotta • Comilla",
            rating: "4.9 ★",
            prods: "85+",
            since: "2018",
            img: "https://images.unsplash.com/photo-1493106641515-6b5631de4bb9?q=80&w=2069&auto=format&fit=crop"
        };
        
        let heroHeadlineText = "Threads of\nTradition,\nWoven with Soul.";
        let heroSubtext = "Discover the authenticity of Bengal. Bring home artifacts that carry a millennium of history.";
        let heroImageUrl = "https://images.unsplash.com/photo-1621252179027-94459d278660?auto=format&fit=crop&q=80&w=1200";

        // --- Core & State ---
        let currentView = 'dashboard';
        let flashSaleStatus = "Inactive";
        let flashStartDate = ''; let flashEndDate = ''; let flashStartTime = '14:00'; let flashEndTime = '16:00';

        const DEFAULT_ADMIN_PIC = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='-32 -32 320 320'%3E%3Cpath d='M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8ZM72,96a56,56,0,1,1,56,56A56.06,56.06,0,0,1,72,96Z' fill='%23A39A8E'/%3E%3C/svg%3E";

        function hydrateFromPayload(payload) {
            const data = payload || {};
            window.__ADMIN_DASHBOARD__ = data;
            MOCK_SELLERS = data.sellers || [];
            MOCK_PRODUCTS = data.products || [];
            MOCK_ORDERS = (data.orders || []).map(o => ({...o, id: String(o.order_id || o.id).replace(/^ORD-/, '')}));
            MOCK_FLASH_REQ = (data.artisan_hour && data.artisan_hour.requests) || [];
            MOCK_JOURNAL = data.journal || [];
            MOCK_GI_REQUESTS = data.gi_requests || [];
            MOCK_VERIFICATIONS = (data.verification || []).map(v => ({...v, time: v.created_at || v.time || ''}));
            MOCK_QC = data.qc || [];
            MOCK_TEAM = data.team || [];
            MOCK_USERS = data.users || [];
            MOCK_DISPUTES = data.disputes || [];
            MOCK_TRANSACTIONS = data.transactions || [];
            window.MOCK_TRANSACTIONS = MOCK_TRANSACTIONS;
            MOCK_COUPONS = data.coupons || [];
            ADMIN_USER = {
                name: (data.profile_settings && data.profile_settings.admin_name) || ADMIN_USER.name,
                email: (data.profile_settings && data.profile_settings.email) || ADMIN_USER.email,
                pic: (data.profile_settings && data.profile_settings.pic) || DEFAULT_ADMIN_PIC,
            };
            FEATURED_ARTISAN = data.featured_artisan || FEATURED_ARTISAN;
            heroHeadlineText = (data.site_experience && data.site_experience.hero_headline) || heroHeadlineText;
            heroSubtext = (data.site_experience && data.site_experience.hero_subtext) || heroSubtext;
            heroImageUrl = (data.site_experience && data.site_experience.hero_image) || heroImageUrl;
            flashSaleStatus = (data.artisan_hour && data.artisan_hour.live) ? 'Active' : 'Inactive';
            flashStartTime = (data.artisan_hour && data.artisan_hour.start) || flashStartTime;
            flashEndTime = (data.artisan_hour && data.artisan_hour.end) || flashEndTime;
            const _nameEl = document.getElementById('sidebar-admin-name');
            const _picEl = document.getElementById('sidebar-admin-pic');
            if (_nameEl) _nameEl.textContent = ADMIN_USER.name;
            if (_picEl) _picEl.src = ADMIN_USER.pic;
        }

        async function adminApi(url, options = {}) {
            const cfg = { ...options };
            if (!(cfg.body instanceof FormData)) {
                cfg.headers = { 'Content-Type': 'application/json', ...(cfg.headers || {}) };
            }
            const res = await fetch(url, cfg);
            const data = await res.json().catch(() => ({}));
            if (!res.ok || data.ok === false) throw new Error(data.error || 'request_failed');
            return data;
        }

        async function refreshAdminData(render = true) {
            try {
                const resp = await adminApi('/api/admin/dashboard/data');
                hydrateFromPayload(resp.data || {});
                if (render) renderMainContent();
            } catch (e) {
                console.error(e);
            }
        }

        hydrateFromPayload(window.__ADMIN_DASHBOARD__ || {});
        let expandedMenus = []; // All closed by default
        let menuNotifications = { 'verification': true, 'qc': true, 'moderation': true }; // Notification states
        let activeChatId = 1;
        let activeDetailId = null; 
        let currentModalAction = null; let currentModalId = null;
        let editingCouponId = null;

        // --- Custom Toast System ---
        function showToast(message, type = 'success') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            
            let bgClass, borderClass, iconHtml, textClass;
            if (type === 'success') {
                bgClass = 'bg-[#1A1614]'; borderClass = 'border-[#C27803]/30'; iconHtml = '<i class="ph-fill ph-check-circle text-[#C27803] text-lg"></i>'; textClass = 'text-white';
            } else if (type === 'info') {
                bgClass = 'bg-blue-50'; borderClass = 'border-blue-200'; iconHtml = '<i class="ph-fill ph-info text-blue-600 text-lg"></i>'; textClass = 'text-blue-900';
            } else {
                bgClass = 'bg-white'; borderClass = 'border-red-100'; iconHtml = '<i class="ph-fill ph-warning-circle text-red-500 text-lg"></i>'; textClass = 'text-red-700';
            }
            
            toast.className = `toast flex items-center gap-3 px-5 py-3.5 rounded-xl text-[13px] font-medium premium-shadow border ${bgClass} ${borderClass}`;
            toast.innerHTML = `${iconHtml} <span class="${textClass}">${message}</span>`;
            container.appendChild(toast);
            setTimeout(() => { toast.classList.add('hiding'); setTimeout(() => toast.remove(), 400); }, 3000);
        }

        // --- Logout Flow ---
        function openLogoutModal() { document.getElementById('logout-modal').classList.remove('hidden'); }
        function closeLogoutModal() { document.getElementById('logout-modal').classList.add('hidden'); }
        function confirmLogout() {
            closeLogoutModal();
            showToast("Signing out securely...", "success");
            setTimeout(() => { window.location.reload(); }, 1000);
        }

        // --- Action Handlers ---
        window.triggerExport = (type) => showToast(`${type} generated & downloaded successfully!`, 'success');
        window.updateSellerStatus = (id, newStatus) => { const s = MOCK_SELLERS.find(x => x.id === id); if(s) { s.status = newStatus; renderMainContent(); showToast(`Seller status updated to ${newStatus}`); } };
        window.updateProductStatus = (id, status) => { const p = MOCK_PRODUCTS.find(x => x.id === id); if(p) { p.status = status; renderMainContent(); showToast("Inventory status synced."); } };
        window.addProductPrompt = () => { const name = prompt("Enter New Product Name:"); if(name) { MOCK_PRODUCTS.unshift({ id: Date.now(), name: name, price: 0, stock: 0, sold: 0, seller: "New Vendor", seller_mail: "-", status: "Draft", gi_status: "None", img: "ph-package" }); renderMainContent(); showToast("Draft created successfully."); } };
        window.updateOrderStatus = (id, status) => { const o = MOCK_ORDERS.find(x => x.id === id); if(o) { o.status = status; renderMainContent(); showToast("Logistics status updated."); } };
        
        // Deep linking handlers
        window.viewSellerDocs = (id) => { activeDetailId = id; setActiveView('seller-details'); };
        window.viewQCInfo = (id) => { activeDetailId = id; setActiveView('qc-details'); };
        window.viewGIDocs = (id) => { activeDetailId = id; setActiveView('gi-details'); };
        
        window.approveVerificationDirect = async (id) => { MOCK_VERIFICATIONS = MOCK_VERIFICATIONS.filter(v => v.id !== id); MOCK_SELLERS = MOCK_SELLERS.map(s => s.id === id ? { ...s, status: 'Active' } : s); showToast("Identity verified and approved."); setActiveView('verification'); };
        window.approveQCDirect = (id) => { MOCK_QC = MOCK_QC.filter(q => q.id !== id); showToast("Product passed QC.", "success"); setActiveView('qc'); };
        window.approveGIDirect = (id) => { MOCK_GI_REQUESTS = MOCK_GI_REQUESTS.filter(r => r.id !== id); showToast("Geographical Indication certified.", "success"); setActiveView('gi-verify'); };

        window.approveFlashSale = (id) => { MOCK_FLASH_REQ = MOCK_FLASH_REQ.filter(r => r.id !== id); showToast("Lot approved for Artisan's Hour."); renderMainContent(); };
        window.updateFlashSchedule = async () => {
            const start_date = document.getElementById('flash-start-date').value; const start = document.getElementById('flash-start-time').value;
            const end_date = document.getElementById('flash-end-date').value; const end = document.getElementById('flash-end-time').value;
            if(!start_date || !start || !end_date || !end) return showToast("Please complete schedule bounds.", "error");
            flashStartDate = start_date; flashStartTime = start; flashEndDate = end_date; flashEndTime = end;
            showToast("Drop schedule synchronized."); renderMainContent();
        };
        window.selectTodaysArtisan = async (id) => { 
            const s = MOCK_SELLERS.find(x => x.id === id); if(!s) return;
            FEATURED_ARTISAN = { name: s.name, desc: `${s.type} • ${s.district}`, rating: `${Number(s.rating || 4.8).toFixed(1)} ★`, prods: `${s.sales || 0}+`, since: '2023', img: s.img };
            showToast(`${s.name} spotlighted.`); renderMainContent(); 
        };
        window.triggerFileDrop = () => document.getElementById('hidden-file-input').click();
        window.publishSiteUpdates = async () => {
            heroHeadlineText = (document.getElementById('site-hero-headline') || {}).value || heroHeadlineText;
            heroSubtext = (document.getElementById('site-hero-subtext') || {}).value || heroSubtext;
            heroImageUrl = (document.getElementById('site-hero-image-url') || {}).value || heroImageUrl;
            renderMainContent();
            showToast('Frontend aesthetics published!'); 
        };
        window.viewJournal = (id) => {
            const post = MOCK_JOURNAL.find(p => p.id === id);
            if(post) {
                const newTitle = prompt(`Editing Journal Title:`, post.title);
                if (newTitle !== null && newTitle.trim() !== '') { post.title = newTitle.trim(); showToast("Editorial saved."); renderMainContent(); }
            }
        };
        window.createBlankDraft = () => { const title = prompt("Enter Draft Title:"); if(title !== null) { MOCK_JOURNAL.unshift({ id: Date.now(), title: title || "Untitled Draft", author: "Admin", date: "Just Now", status: "Draft", views: "0", img: "https://images.unsplash.com/photo-1455390582262-044cdead2708?q=80&w=2073&auto=format&fit=crop" }); renderMainContent(); } };
        window.addNewJournal = () => { const title = prompt("Enter New Article Title:"); if(title && title.trim() !== '') { MOCK_JOURNAL.unshift({ id: Date.now(), title: title, author: "Admin", date: "Just Now", status: "Draft", views: "0", img: "https://images.unsplash.com/photo-1606294719268-9ee22378939c?q=80&w=2070&auto=format&fit=crop" }); renderMainContent(); } else if (title !== null) { showToast("Title cannot be empty.", "error"); } };
        window.inviteTeamMember = () => { const name = prompt("Enter new member's name:"); if(name && name.trim() !== '') { MOCK_TEAM.unshift({id: Date.now(), name: name, role: 'Editor', art: 0, email: name.toLowerCase().replace(' ', '.')+'@origins.bd'}); renderMainContent(); } };
        window.deleteTeamMember = (id) => { MOCK_TEAM = MOCK_TEAM.filter(m => m.id !== id); renderMainContent(); };
        window.toggleUserBan = (id) => { const u = MOCK_USERS.find(x => x.id === id); if(u) { u.status = u.status === 'Active' ? 'Banned' : 'Active'; renderMainContent(); showToast("User access modified."); } };
        window.resolveDispute = (id, act) => { MOCK_DISPUTES = MOCK_DISPUTES.filter(d => d.id !== id); showToast(`Case #${id} ${act}.`); renderMainContent(); };
        window.sendChatMessage = () => { 
            const inp = document.getElementById('chat-input-field'); const text = inp.value.trim(); 
            if(text) { 
                document.getElementById('chat-messages-box').innerHTML += `<div class="flex gap-4 flex-row-reverse fade-in"><div class="w-8 h-8 bg-[#C27803] rounded-full flex items-center justify-center text-white text-xs font-serif font-medium self-end mb-1">A</div><div class="bg-[#1A1614] text-white py-3 px-4 bubble-sent premium-shadow max-w-[80%] text-[13px] leading-relaxed border border-[#C27803]/30">${text}</div></div>`; 
                inp.value = ''; const box = document.getElementById('chat-messages-box'); box.scrollTop = box.scrollHeight;
            } 
        };

        window.saveAdminProfile = () => {
            const newName = document.getElementById('admin-edit-name').value.trim();
            if(!newName) return showToast("Name field cannot be empty.", "error");
            ADMIN_USER.name = newName;
            document.getElementById('sidebar-admin-name').textContent = newName;
            document.getElementById('profile-page-name').textContent = newName;
            showToast("Identity updated."); renderMainContent();
        };

        window.saveAdminPassword = () => {
            const curr = document.getElementById('admin-curr-pass').value; const newP = document.getElementById('admin-new-pass').value; const confP = document.getElementById('admin-conf-pass').value;
            if(!curr || !newP || !confP) return showToast("Fill all fields.", "error");
            if(newP.length < 8) return showToast("Min 8 characters required.", "error");
            if(newP !== confP) return showToast("Passkey mismatch.", "error");
            showToast("Credentials rotated successfully.");
            document.getElementById('admin-curr-pass').value = ''; document.getElementById('admin-new-pass').value = ''; document.getElementById('admin-conf-pass').value = '';
        };

        window.togglePasswordVisibility = (id) => {
            const input = document.getElementById(id); const icon = document.getElementById(id + '-icon');
            if (input.type === 'password') { input.type = 'text'; icon.className = 'ph-duotone ph-eye-slash text-lg'; } 
            else { input.type = 'password'; icon.className = 'ph-duotone ph-eye text-lg'; }
        };

        window.updateProfilePicPreview = (input) => {
            if(input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    ADMIN_USER.pic = e.target.result;
                    document.getElementById('sidebar-admin-pic').src = e.target.result;
                    renderMainContent();
                    showToast("Portrait updated.");
                }
                reader.readAsDataURL(input.files[0]);
            }
        };

        document.getElementById('hidden-file-input')?.addEventListener('change', (e) => {
            const file = e.target.files && e.target.files[0]; if (!file) return;
            heroImageUrl = URL.createObjectURL(file);
            const preview = document.getElementById('site-hero-preview'); if (preview) preview.src = heroImageUrl;
        });

        // --- Coupon Logic ---
        window.toggleCouponFields = () => {
            const type = document.getElementById('new-coupon-type').value;
            document.getElementById('coupon-value-container').style.display = type === 'Free Delivery' ? 'none' : 'block';
            
            const limitType = document.getElementById('new-coupon-limit-type').value;
            document.getElementById('new-coupon-limit').style.display = limitType === 'Custom' ? 'block' : 'none';
            
            const expiryType = document.getElementById('new-coupon-expiry-type').value;
            document.getElementById('new-coupon-date').style.display = expiryType === 'Custom' ? 'block' : 'none';
        };

        window.openCreateCouponModal = () => {
            editingCouponId = null;
            document.getElementById('coupon-modal-title').textContent = "Create New Coupon";
            document.getElementById('coupon-action-btn').textContent = "Generate Code";
            
            // Reset fields
            document.getElementById('new-coupon-code').value = '';
            document.getElementById('new-coupon-type').value = 'Percentage';
            document.getElementById('new-coupon-discount').value = '';
            document.getElementById('new-coupon-new-user').checked = false;
            document.getElementById('new-coupon-limit-type').value = 'Unlimited';
            document.getElementById('new-coupon-limit').value = '';
            document.getElementById('new-coupon-expiry-type').value = 'Never';
            document.getElementById('new-coupon-date').value = '';
            
            toggleCouponFields();
            document.getElementById('coupon-modal').classList.remove('hidden');
        };

        window.openEditCouponModal = (id) => {
            editingCouponId = id;
            const c = MOCK_COUPONS.find(x => x.id === id);
            if(!c) return;

            document.getElementById('coupon-modal-title').textContent = "Edit Coupon Details";
            document.getElementById('coupon-action-btn').textContent = "Save Changes";
            
            document.getElementById('new-coupon-code').value = c.code;
            document.getElementById('new-coupon-type').value = c.type;
            
            if(c.type !== 'Free Delivery') {
                document.getElementById('new-coupon-discount').value = parseFloat(c.discount.replace(/[^\d.]/g, ''));
            }
            
            document.getElementById('new-coupon-new-user').checked = c.isNewUser || false;
            
            if(c.limit === 'Unlimited') {
                document.getElementById('new-coupon-limit-type').value = 'Unlimited';
            } else {
                document.getElementById('new-coupon-limit-type').value = 'Custom';
                document.getElementById('new-coupon-limit').value = c.limit;
            }
            
            if(c.expires === 'Never') {
                document.getElementById('new-coupon-expiry-type').value = 'Never';
            } else {
                document.getElementById('new-coupon-expiry-type').value = 'Custom';
                document.getElementById('new-coupon-date').value = c.expires;
            }
            
            toggleCouponFields();
            document.getElementById('coupon-modal').classList.remove('hidden');
        };

        window.closeCouponModal = () => document.getElementById('coupon-modal').classList.add('hidden');

        window.saveCoupon = () => {
            const code = document.getElementById('new-coupon-code').value.trim().toUpperCase();
            const type = document.getElementById('new-coupon-type').value;
            const discountVal = document.getElementById('new-coupon-discount').value.trim();
            const isNewUser = document.getElementById('new-coupon-new-user').checked;
            
            const limitType = document.getElementById('new-coupon-limit-type').value;
            const limit = limitType === 'Unlimited' ? 'Unlimited' : (parseInt(document.getElementById('new-coupon-limit').value) || 100);
            
            const expiryType = document.getElementById('new-coupon-expiry-type').value;
            const expires = expiryType === 'Never' ? 'Never' : document.getElementById('new-coupon-date').value;

            if(!code || (type !== 'Free Delivery' && !discountVal) || (expiryType === 'Custom' && !expires)) {
                return showToast("Please complete all promotion details.", "error");
            }

            let discountFormatted = type === 'Free Delivery' ? 'Free Delivery' : (type === 'Percentage' ? `${discountVal}%` : `BDT ${discountVal}`);

            if(editingCouponId) {
                const c = MOCK_COUPONS.find(x => x.id === editingCouponId);
                if(c) {
                    c.code = code;
                    c.type = type;
                    c.discount = discountFormatted;
                    c.isNewUser = isNewUser;
                    c.limit = limit;
                    c.expires = expires;
                    
                    // Auto-pause logic check on edit
                    if(c.limit !== 'Unlimited' && c.used >= c.limit) {
                        c.status = 'Paused';
                    }
                }
                showToast("Coupon updated successfully.", "success");
            } else {
                MOCK_COUPONS.unshift({
                    id: Date.now(),
                    code: code,
                    discount: discountFormatted,
                    type: type,
                    limit: limit,
                    used: 0,
                    expires: expires,
                    isNewUser: isNewUser,
                    status: "Active"
                });
                showToast("Promotion code generated successfully.", "success");
            }
            
            closeCouponModal();
            renderMainContent();
        };

        window.toggleCouponStatus = (id) => {
            const c = MOCK_COUPONS.find(x => x.id === id);
            if(c) {
                if(c.limit !== 'Unlimited' && c.used >= c.limit && c.status === 'Paused') {
                    return showToast("Cannot activate: Usage limit has been reached. Please edit the limit.", "error");
                }
                c.status = c.status === 'Active' ? 'Paused' : 'Active';
                renderMainContent();
                showToast(`Coupon ${c.code} is now ${c.status.toLowerCase()}.`);
            }
        };

        window.deleteCoupon = (id) => {
            MOCK_COUPONS = MOCK_COUPONS.filter(c => c.id !== id);
            renderMainContent();
            showToast("Coupon permanently removed.", "success");
        };

        // --- UI Building ---
        function renderSidebar() {
            const container = document.getElementById('sidebar-menu'); let html = '';
            MENU_STRUCTURE.forEach(group => {
                if (group.items && !group.id) {
                    group.items.forEach(item => {
                        const isActive = currentView === item.id || (item.id === 'verification' && currentView === 'seller-details') || (item.id === 'qc' && currentView === 'qc-details') || (item.id === 'gi-verify' && currentView === 'gi-details');
                        const activeClass = isActive ? 'bg-[#C27803]/10 text-[#C27803] font-medium border-l-[3px] border-[#C27803]' : 'text-[#A39A8E] hover:text-[#C27803] hover:bg-white/5 border-l-[3px] border-transparent';
                        html += `<button onclick="setActiveView('${item.id}')" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-r-xl mb-1 transition-all duration-300 group ${activeClass}"><i class="ph-duotone ${item.icon} text-xl ${isActive ? 'text-[#C27803]' : 'text-[#A39A8E] group-hover:text-[#C27803]'} transition-colors"></i><span class="text-[13px] tracking-wide">${item.label}</span></button>`;
                    });
                } else {
                    const isActiveGroup = group.items.some(i => i.id === currentView || (i.id === 'verification' && currentView === 'seller-details') || (i.id === 'qc' && currentView === 'qc-details') || (i.id === 'gi-verify' && currentView === 'gi-details'));
                    const isOpen = expandedMenus.includes(group.id) || isActiveGroup;
                    html += `<div class="mb-2 mt-4"><button onclick="toggleMenu('${group.id}')" class="w-full flex items-center justify-between px-2 py-2 rounded-lg text-[#D6D0C4] hover:text-white transition-all group ${isOpen ? 'active text-white' : ''}"><div class="flex items-center gap-2"><span class="text-[9px] font-bold uppercase tracking-[0.1em] ${isActiveGroup ? 'text-[#C27803]' : 'text-[#6B635A]'} transition-colors">${group.title}</span></div><i class="ph-bold ph-caret-down text-[#6B635A] text-[10px] rotate-icon group-hover:text-[#A39A8E]"></i></button><div class="submenu ${isOpen ? 'open' : ''} pl-1 pr-1 space-y-0.5 mt-1">${group.items.map(item => { 
                        const isActiveSub = currentView === item.id || (item.id === 'verification' && currentView === 'seller-details') || (item.id === 'qc' && currentView === 'qc-details') || (item.id === 'gi-verify' && currentView === 'gi-details');
                        const activeSubClass = isActiveSub ? 'bg-[#C27803]/15 text-[#C27803] font-medium' : 'text-[#A39A8E] hover:text-white hover:bg-white/5'; 
                        const hasNotif = (item.id === 'verification' || item.id === 'qc' || item.id === 'moderation') && menuNotifications[item.id];
                        return `<button onclick="setActiveView('${item.id}')" class="w-full text-left px-3 py-2 rounded-xl text-[13px] transition-all flex items-center gap-3 ${activeSubClass}"><i class="ph-duotone ${item.icon} text-[18px]"></i> <span>${item.label}</span>${hasNotif ? '<span class="ml-auto w-1.5 h-1.5 rounded-full bg-red-500/80"></span>' : ''}</button>`; 
                    }).join('')}</div></div>`;
                }
            });
            container.innerHTML = html;
        }

        function toggleMenu(id) { expandedMenus.includes(id) ? expandedMenus = expandedMenus.filter(m => m !== id) : expandedMenus.push(id); renderSidebar(); }
        function setActiveView(id) { 
            currentView = id; 
            activeDetailId = null; 
            if(menuNotifications[id]) menuNotifications[id] = false; // Clear notification
            renderSidebar(); 
            renderMainContent(); 
            window.scrollTo({top:0, behavior:'smooth'}); 
        }

        function renderHeader(title, desc, actionHtml = '') {
            return `<header class="flex justify-between items-end mb-12 fade-in pb-8 border-b border-[#E8E3DB]/60"><div><h2 class="text-4xl font-normal text-[#1A1614] tracking-tight font-serif mb-2">${title}</h2><p class="text-[#6B635A] text-[13px] font-medium tracking-wide">${desc}</p></div><div class="flex items-center gap-4">${actionHtml}<div class="h-6 w-px bg-[#E8E3DB] mx-1"></div><button class="p-2.5 bg-transparent border border-[#E8E3DB] rounded-full text-[#6B635A] hover:text-[#C27803] hover:border-[#C27803] hover:bg-white transition-all relative group"><i class="ph-duotone ph-bell text-xl"></i><span class="absolute top-0 right-0 w-2.5 h-2.5 bg-[#C27803] rounded-full border-2 border-[var(--brand-bg)] group-hover:border-white transition-colors"></span></button></div></header>`;
        }

        function renderMainContent() {
            const container = document.getElementById('main-content');
            const renderers = { 
                'dashboard': renderDashboard, 'analytics': renderAnalytics, 'sellers': renderSellers, 
                'verification': renderVerification, 'seller-details': () => renderSellerDetails(activeDetailId),
                'messages': renderMessages, 'products': renderProducts, 
                'qc': renderProductQC, 'qc-details': () => renderQCDetails(activeDetailId),
                'gi-verify': renderGIVerification, 'gi-details': () => renderGIDetails(activeDetailId),
                'orders': renderOrders, 'flash-sale': renderFlashSale, 'finance': renderFinance, 
                'commission': renderCommissions, 'todays-artisan': renderTodaysArtisan, 'site-content': renderSiteContent, 
                'journal': renderJournal, 'content-team': renderContentTeam, 'coupons': renderCoupons,
                'users': renderUserManagement, 'moderation': renderModeration, 'logs': renderLogs, 'profile': renderProfile 
            };
            container.innerHTML = renderers[currentView] ? renderers[currentView]() : renderDashboard();
        }

        // Modal Handlers (Note)
        function openNoteModal(action, id) {
            currentModalAction = action; currentModalId = id;
            const modal = document.getElementById('note-modal'); const title = document.getElementById('modal-title'); const btn = document.getElementById('modal-action-btn');
            title.textContent = action === 'reject' ? 'Reject Request' : 'Request Resubmission';
            btn.innerHTML = action === 'reject' ? 'Confirm Rejection' : 'Send Request';
            btn.className = action === 'reject' ? "px-6 py-2.5 bg-red-600 text-white rounded-xl text-sm font-medium hover:bg-red-700 transition-colors shadow-sm" : "px-6 py-2.5 bg-[#C27803] text-white rounded-xl text-sm font-medium hover:bg-[#A36502] transition-colors shadow-sm";
            document.getElementById('modal-note').value = ''; modal.classList.remove('hidden');
        }
        function closeNoteModal() { document.getElementById('note-modal').classList.add('hidden'); }
        function submitModalAction() {
            const note = document.getElementById('modal-note').value;
            if(!note) { showToast("Please document the reason.", "error"); return; }
            showToast(`${currentModalAction === 'reject' ? 'Rejection' : 'Resubmission'} logged successfully.`);
            
            if(currentView === 'verification' || currentView === 'seller-details') { MOCK_VERIFICATIONS = MOCK_VERIFICATIONS.filter(v => v.id !== currentModalId); setActiveView('verification'); } 
            else if(currentView === 'qc' || currentView === 'qc-details') { MOCK_QC = MOCK_QC.filter(q => q.id !== currentModalId); setActiveView('qc'); } 
            else if(currentView === 'gi-verify' || currentView === 'gi-details') { MOCK_GI_REQUESTS = MOCK_GI_REQUESTS.filter(r => r.id !== currentModalId); setActiveView('gi-verify'); } 
            else if(currentView === 'flash-sale') { MOCK_FLASH_REQ = MOCK_FLASH_REQ.filter(r => r.id !== currentModalId); renderMainContent(); }
            closeNoteModal(); 
        }

        async function toggleFlashSaleStatus() { const nextLive = flashSaleStatus !== "Active"; flashSaleStatus = nextLive ? "Active" : "Inactive"; showToast(`Artisan's Hour is now ${flashSaleStatus === "Active" ? 'LIVE' : 'OFFLINE'}.`); renderMainContent(); }

        // --- DETAILED VIEWS ---
        function renderSellerDetails(id) { 
            const v = MOCK_VERIFICATIONS.find(x => x.id === id); if(!v) return setActiveView('verification'); 
            return `<button onclick="setActiveView('verification')" class="mb-6 flex items-center gap-2 text-xs font-semibold text-[#A39A8E] hover:text-[#C27803] transition-colors fade-in"><i class="ph-bold ph-arrow-left"></i> Back to Hub</button><div class="flex justify-between items-end mb-10 fade-in pb-6 border-b border-[#E8E3DB]"><h2 class="text-3xl font-serif text-[#1A1614] mb-2">Merchant Dossier</h2><div class="flex gap-2"><button onclick="openNoteModal('reject', ${v.id})" class="px-5 py-2.5 bg-white border border-[#E8E3DB] text-red-600 rounded-xl font-medium text-[13px] hover:bg-red-50 hover:border-red-200 transition-colors">Reject</button><button onclick="openNoteModal('resubmit', ${v.id})" class="px-5 py-2.5 bg-white border border-[#E8E3DB] text-[#6B635A] rounded-xl font-medium text-[13px] hover:bg-[#FAF8F5] hover:text-[#C27803] hover:border-[#C27803]/30 transition-colors">Request Revision</button><button onclick="approveVerificationDirect(${v.id})" class="px-5 py-2.5 bg-[#C27803] text-white rounded-xl font-medium text-[13px] hover:bg-[#A36502] transition-colors shadow-lg shadow-[#C27803]/20">Approve</button></div></div>`;
        }
        function renderQCDetails(id) { 
            const q = MOCK_QC.find(x => x.id === id); if(!q) return setActiveView('qc'); 
            return `<button onclick="setActiveView('qc')" class="mb-6 flex items-center gap-2 text-xs font-semibold text-[#A39A8E] hover:text-[#C27803] transition-colors fade-in"><i class="ph-bold ph-arrow-left"></i> Back to QC</button><div class="flex justify-between items-end mb-10 fade-in pb-6 border-b border-[#E8E3DB]"><h2 class="text-3xl font-serif text-[#1A1614] mb-2">Quality Inspection</h2><div class="flex gap-2"><button onclick="openNoteModal('reject', ${q.id})" class="px-5 py-2.5 bg-white border border-[#E8E3DB] text-red-600 rounded-xl font-medium text-[13px] hover:bg-red-50 hover:border-red-200 transition-colors">Reject</button><button onclick="openNoteModal('resubmit', ${q.id})" class="px-5 py-2.5 bg-white border border-[#E8E3DB] text-[#6B635A] rounded-xl font-medium text-[13px] hover:bg-[#FAF8F5] hover:text-[#C27803] hover:border-[#C27803]/30 transition-colors">Request Changes</button><button onclick="approveQCDirect(${q.id})" class="px-5 py-2.5 bg-[#C27803] text-white rounded-xl font-medium text-[13px] hover:bg-[#A36502] transition-colors shadow-lg shadow-[#C27803]/20">Pass QC</button></div></div>`;
        }
        function renderGIDetails(id) { 
            const req = MOCK_GI_REQUESTS.find(x => x.id === id); if(!req) return setActiveView('gi-verify'); 
            return `<button onclick="setActiveView('gi-verify')" class="mb-6 flex items-center gap-2 text-xs font-semibold text-[#A39A8E] hover:text-[#C27803] transition-colors fade-in"><i class="ph-bold ph-arrow-left"></i> Back to GI Registry</button><div class="flex justify-between items-end mb-10 fade-in pb-6 border-b border-[#E8E3DB]"><h2 class="text-3xl font-serif text-[#1A1614] mb-2">GI Dossier</h2><div class="flex gap-2"><button onclick="openNoteModal('reject', ${req.id})" class="px-5 py-2.5 bg-white border border-[#E8E3DB] text-red-600 rounded-xl font-medium text-[13px] hover:bg-red-50 hover:border-red-200 transition-colors">Deny</button><button onclick="openNoteModal('resubmit', ${req.id})" class="px-5 py-2.5 bg-white border border-[#E8E3DB] text-[#6B635A] rounded-xl font-medium text-[13px] hover:bg-[#FAF8F5] hover:text-[#C27803] hover:border-[#C27803]/30 transition-colors">More Evidence</button><button onclick="approveGIDirect(${req.id})" class="px-5 py-2.5 bg-[#C27803] text-white rounded-xl font-medium text-[13px] hover:bg-[#A36502] transition-colors shadow-lg shadow-[#C27803]/20">Grant GI</button></div></div>`;
        }

        // --- CORE VIEWS ---
        function renderDashboard() {
            const revenueData = (window.__ADMIN_DASHBOARD__.revenue_analytics && window.__ADMIN_DASHBOARD__.revenue_analytics.length)
                ? window.__ADMIN_DASHBOARD__.revenue_analytics
                : [{month:'N/A', revenue:0},{month:'N/A', revenue:0},{month:'N/A', revenue:0},{month:'N/A', revenue:0},{month:'N/A', revenue:0},{month:'N/A', revenue:0}];
            const maxRevenue = Math.max(...revenueData.map(x => Number(x.revenue || 0) / 1000), 1);
            const revenueBars = revenueData.map((entry) => {
                const r = Number(entry.revenue || 0) / 1000;
                const h = Math.max(8, Math.round((r / maxRevenue) * 100));
                return `<div class="w-full relative group h-full flex flex-col justify-end">
                            <div class="absolute bottom-0 w-full bg-[#1A1614] rounded-t-md opacity-80 group-hover:opacity-100 group-hover:bg-[#C27803] transition-all bar-fill" style="--h: ${h}%"></div>
                            <div class="opacity-0 group-hover:opacity-100 absolute -top-8 left-1/2 -translate-x-1/2 text-[10px] font-mono text-[#C27803] font-bold transition-opacity bg-white px-2 py-1 rounded border border-[#E8E3DB] shadow-sm z-10">BDT ${r}k</div>
                        </div>`;
            }).join('');
            const revenueLabels = revenueData.map(x => `<span>${(x.month || '').slice(5) || 'N/A'}</span>`).join('');
            const tasks = [
                {l:'Dispute Review', c:`${MOCK_DISPUTES.length} Open`, a:'ph-warning-circle', t:'red', link:'moderation'},
                {l:'Identity Verifications', c:`${MOCK_VERIFICATIONS.length} Pending`, a:'ph-shield-check', t:'amber', link:'verification'},
                {l:'QC Inspections', c:`${MOCK_QC.length} Pending`, a:'ph-clipboard-text', t:'blue', link:'qc'}
            ];
            const taskCards = tasks.map(task => `
                <div onclick="setActiveView('${task.link}')" class="flex items-center justify-between py-3 border-b border-[#FAF8F5] last:border-0 group cursor-pointer hover:px-2 transition-all">
                    <div class="flex items-center gap-4">
                        <div class="p-2 rounded-lg bg-${task.t}-50 text-${task.t}-600 group-hover:bg-${task.t}-100 transition-colors"><i class="ph-duotone ${task.a} text-lg"></i></div>
                        <div><span class="text-[13px] font-medium text-[#1A1614] block group-hover:text-[#C27803] transition-colors">${task.l}</span><span class="text-[10px] text-[#A39A8E] mt-0.5 block uppercase tracking-widest">${task.c}</span></div>
                    </div>
                    <i class="ph-bold ph-caret-right text-xs text-[#E8E3DB] group-hover:text-[#C27803] transition-colors"></i>
                </div>`).join('');
            return `
                ${renderHeader('Executive Dashboard', 'Real-time ecosystem overview.')}
                <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10 fade-in">
                    ${[{l:'Total Revenue',v:(window.__ADMIN_DASHBOARD__.summary?.revenue_fmt || 'BDT 0'),s:'From live orders',i:'ph-chart-line-up',c:'border-b-[3px] border-b-[#C27803]'},{l:'Registered Artisans',v:String(window.__ADMIN_DASHBOARD__.summary?.artisans || 0),s:'DB synced',i:'ph-users',c:'border-b border-b-[#E8E3DB]'},{l:'GI Certifications',v:String(window.__ADMIN_DASHBOARD__.summary?.gi_products || 0),s:'Verified products',i:'ph-seal-check',c:'border-b border-b-[#E8E3DB]'},{l:'Pending Orders',v:String(window.__ADMIN_DASHBOARD__.summary?.orders || 0),s:'Commerce engine',i:'ph-package',c:'border-b border-b-[#E8E3DB]'}].map(k=>`
                        <div class="bg-white rounded-2xl p-6 relative overflow-hidden group ${k.c} shadow-[0_4px_24px_-8px_rgba(0,0,0,0.04)] hover:shadow-[0_8px_32px_-8px_rgba(194,120,3,0.15)] transition-all cursor-default hover:-translate-y-1">
                            <div class="flex justify-between items-start mb-6">
                                <p class="text-[11px] font-medium text-[#6B635A] tracking-wide">${k.l}</p>
                                <i class="ph-duotone ${k.i} text-xl text-[#C27803] opacity-80 group-hover:opacity-100 transition-opacity"></i>
                            </div>
                            <h3 class="text-3xl font-serif text-[#1A1614] mb-2 font-normal group-hover:text-[#C27803] transition-colors">${k.v}</h3>
                            <p class="text-[10px] uppercase font-bold tracking-wider text-[#A39A8E]">${k.s}</p>
                        </div>`).join('')}
                </div>
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 fade-in-delayed">
                    <div class="lg:col-span-2 bg-white p-8 rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] hover-lift">
                        <div class="flex justify-between items-center mb-10">
                            <div><h3 class="font-serif text-xl text-[#1A1614]">Revenue Trajectory</h3></div>
                            <select class="bg-transparent border border-[#E8E3DB] rounded-lg px-3 py-1.5 text-[12px] font-medium text-[#6B635A] focus:outline-none focus:border-[#C27803] cursor-pointer hover:text-[#C27803] transition-colors"><option>Last 7 Days</option></select>
                        </div>
                        <div class="h-56 flex items-end justify-between gap-4">${revenueBars}</div>
                        <div class="flex justify-between mt-4 text-[10px] font-mono text-[#A39A8E] px-1">${revenueLabels}</div>
                    </div>
                    <div class="bg-white p-8 rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] flex flex-col hover-lift">
                        <div class="mb-6"><h3 class="font-serif text-xl text-[#1A1614]">Action Queue</h3></div>
                        <div class="space-y-3 flex-1">${taskCards}</div>
                    </div>
                </div>`;
        }

        function renderAnalytics() {
            return `
                ${renderHeader('Analytics Suite', 'Data-driven insights for strategic growth.', '<button onclick="triggerExport(\'PDF Report\')" class="bg-white border border-[#E8E3DB] text-[#1A1614] px-5 py-2.5 rounded-full text-[13px] font-medium flex items-center gap-2 hover:bg-[#FAF8F5] hover:text-[#C27803] hover:border-[#C27803]/30 transition-all hover-lift"><i class="ph-bold ph-download-simple"></i> Download PDF</button>')}
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 fade-in">
                    <div class="lg:col-span-2 bg-white p-8 rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] hover-lift group">
                        <div class="flex justify-between items-center mb-8">
                            <h3 class="font-serif text-xl text-[#1A1614] group-hover:text-[#C27803] transition-colors">Traffic Sources</h3>
                            <select class="bg-transparent border border-[#E8E3DB] rounded-lg px-3 py-1.5 text-[12px] font-medium text-[#6B635A] focus:outline-none focus:border-[#C27803] cursor-pointer hover:text-[#C27803] transition-colors"><option>This Month</option></select>
                        </div>
                        <div class="space-y-6">
                            ${[{label: 'Organic Search (Google, Bing)', val: 65, color: 'bg-[#1A1614]'}, {label: 'Social Media (Facebook, Instagram)', val: 20, color: 'bg-[#C27803]'}, {label: 'Direct Referral & Others', val: 15, color: 'bg-[#E8E3DB]'}].map(s => `
                                <div>
                                    <div class="flex justify-between text-[13px] font-medium mb-2.5"><span class="text-[#6B635A]">${s.label}</span><span class="text-[#1A1614] font-mono">${s.val}%</span></div>
                                    <div class="w-full bg-[#FAF8F5] h-2.5 rounded-full overflow-hidden border border-[#E8E3DB]/50"><div class="${s.color} h-full rounded-full" style="width: ${s.val}%"></div></div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="bg-white p-8 rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] flex flex-col items-center justify-center text-center hover-lift group">
                        <div class="w-36 h-36 pie-chart mb-8 premium-shadow group-hover:scale-105 transition-transform"></div>
                        <h3 class="font-serif text-xl text-[#1A1614] mb-3 group-hover:text-[#C27803] transition-colors">Device Breakdown</h3>
                        <div class="flex gap-6 text-[12px] font-medium text-[#6B635A]"><span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-[#1A1614]"></span> Mobile</span><span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-[#C27803]"></span> Desktop</span></div>
                    </div>
                    <div class="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-6 mt-2">
                        ${[{l:'Conversion Rate', v:'3.2%', t:'+0.4%'}, {l:'Avg. Session Duration', v:'4m 12s', t:'+12s'}, {l:'Bounce Rate', v:'42%', t:'-2.1%'}].map(k=>`
                            <div class="bg-white p-7 rounded-3xl border border-[#E8E3DB] hover-lift group">
                                <p class="text-[11px] font-medium text-[#6B635A] tracking-wide mb-3">${k.l}</p>
                                <div class="flex items-end gap-3"><h3 class="text-3xl font-serif text-[#1A1614] group-hover:text-[#C27803] transition-colors">${k.v}</h3><span class="text-[11px] font-bold text-emerald-600 mb-1.5 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">${k.t}</span></div>
                            </div>
                        `).join('')}
                    </div>
                </div>`;
        }

        function renderSellers() {
            return `
                ${renderHeader('Artisan Directory', 'Manage all registered sellers.', '<button onclick="triggerExport(\'CSV Dataset\')" class="bg-white border border-[#E8E3DB] text-[#1A1614] px-5 py-2.5 rounded-full font-medium text-[13px] flex items-center gap-2 hover:bg-[#FAF8F5] hover:text-[#C27803] hover:border-[#C27803]/30 transition-all hover-lift"><i class="ph-bold ph-download-simple"></i> Export Data</button>')}
                <div class="bg-white rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] overflow-hidden fade-in">
                    <div class="p-5 border-b border-[#FAF8F5]"><div class="relative max-w-sm"><i class="ph-regular ph-magnifying-glass absolute left-4 top-1/2 -translate-y-1/2 text-[#A39A8E] group-focus-within:text-[#C27803] transition-colors"></i><input type="text" placeholder="Search artisans..." class="w-full pl-10 pr-4 py-2.5 bg-[#FAF8F5] border border-transparent rounded-xl text-[13px] focus:bg-white focus:border-[#C27803]/30 focus:outline-none transition-all placeholder:text-[#A39A8E] text-[#1A1614]"></div></div>
                    <table class="w-full text-left">
                        <thead class="text-[10px] font-bold text-[#A39A8E] uppercase tracking-widest border-b border-[#FAF8F5]"><tr><th class="px-8 py-4 font-normal">Profile</th><th class="px-6 py-4 font-normal">Location</th><th class="px-6 py-4 font-normal">Status</th><th class="px-6 py-4 text-right font-normal">Actions</th></tr></thead>
                        <tbody class="divide-y divide-[#FAF8F5]">
                            ${MOCK_SELLERS.map(s => `
                                <tr class="hover:bg-[#FAF8F5]/50 transition-colors group">
                                    <td class="px-8 py-4"><div class="flex items-center gap-4"><img src="${s.img}" class="w-10 h-10 rounded-full bg-[#FAF8F5] border border-[#E8E3DB] group-hover:border-[#C27803]/50 transition-colors"><div class="flex flex-col"><div class="font-medium text-[13px] text-[#1A1614] group-hover:text-[#C27803] transition-colors">${s.name}</div><div class="text-[11px] text-[#A39A8E] mt-0.5">${s.email}</div></div></div></td>
                                    <td class="px-6 py-4 text-[13px] text-[#6B635A]">${s.district}</td>
                                    <td class="px-6 py-4"><span class="flex items-center gap-1.5 text-[11px] font-medium text-[#1A1614] bg-white border border-[#E8E3DB] px-2.5 py-1 rounded w-fit"><span class="w-1.5 h-1.5 rounded-full ${s.status === 'Active' ? 'bg-emerald-500' : s.status === 'Banned' ? 'bg-red-500' : 'bg-amber-500'}"></span> ${s.status}</span></td>
                                    <td class="px-6 py-4 text-right">
                                        ${s.status === 'Banned' ? `<button onclick="updateSellerStatus(${s.id}, 'Active')" class="text-emerald-600 hover:text-white border border-transparent hover:border-emerald-600 hover:bg-emerald-600 px-3 py-1.5 rounded-lg font-medium text-[12px] transition-all">Unban</button>` : `<button onclick="updateSellerStatus(${s.id}, 'Banned')" class="text-[#1A1614] border border-[#E8E3DB] hover:text-white hover:bg-red-600 hover:border-red-600 px-3 py-1.5 rounded-lg font-medium text-[12px] transition-all">Ban</button>`}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>`;
        }

        function renderVerification() {
            return `
                ${renderHeader('Verification Hub', 'Review identity and business documents.')}
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 fade-in">
                    ${MOCK_VERIFICATIONS.length > 0 ? MOCK_VERIFICATIONS.map(v => `
                    <div class="bg-white p-8 rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] flex flex-col justify-between hover-lift min-h-[220px] group">
                        <div class="flex justify-between items-start mb-6">
                            <div><h3 class="font-serif text-xl text-[#1A1614] mb-1 group-hover:text-[#C27803] transition-colors">${v.name}</h3><p class="text-[11px] text-[#A39A8E] uppercase tracking-widest">${v.loc}</p></div>
                            <span class="text-[10px] font-mono text-amber-700 bg-amber-50 border border-amber-100 px-2.5 py-1 rounded-md">Pending</span>
                        </div>
                        <div class="flex items-center gap-2 mb-6 text-[13px] text-[#6B635A] bg-[#FAF8F5] p-3 rounded-xl border border-[#E8E3DB] w-fit"><i class="ph-duotone ph-files text-[#C27803] text-lg"></i> <span class="font-medium">${v.docs} Documents Submitted</span></div>
                        <button onclick="showToast('Opening Document Viewer...', 'info')" class="w-full py-2.5 mb-4 bg-[#FAF8F5] border border-[#E8E3DB] text-[#1A1614] rounded-xl text-[12px] font-medium hover:bg-white hover:border-[#C27803]/30 transition-all flex items-center justify-center gap-2"><i class="ph-bold ph-eye"></i> View Documents</button>
                        <div class="grid grid-cols-3 gap-2">
                            <button onclick="openNoteModal('reject', ${v.id})" class="py-2.5 bg-white border border-[#E8E3DB] text-red-600 rounded-xl text-[12px] font-medium hover:bg-red-50 hover:border-red-200 transition-colors">Reject</button>
                            <button onclick="openNoteModal('resubmit', ${v.id})" class="py-2.5 bg-white border border-[#E8E3DB] text-[#6B635A] rounded-xl text-[12px] font-medium hover:bg-[#FAF8F5] hover:text-[#C27803] transition-colors">Request Fix</button>
                            <button onclick="approveVerificationDirect(${v.id})" class="py-2.5 bg-[#1A1614] text-white rounded-xl text-[12px] font-medium hover:bg-[#C27803] transition-colors shadow-sm">Approve</button>
                        </div>
                    </div>`).join('') : '<div class="col-span-2 text-center text-[#A39A8E] py-20 font-serif text-lg border border-dashed border-[#E8E3DB] rounded-3xl bg-white"><i class="ph-duotone ph-shield-check text-4xl mb-3 text-[#E8E3DB]"></i><br>No pending verifications.</div>'}
                </div>`;
        }

        function renderMessages() {
            window.renderActiveChat = (id) => { activeChatId = id; document.getElementById('chat-view').innerHTML = document.getElementById(id===1 ? 'chat-1' : 'chat-2').innerHTML; };
            return `
                ${renderHeader('Communications', 'Direct messaging with artisans.')}
                <div class="bg-white rounded-3xl border border-[#E8E3DB] h-[700px] flex overflow-hidden shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] fade-in">
                    <!-- Sidebar -->
                    <div class="w-[320px] border-r border-[#E8E3DB] bg-white flex flex-col">
                        <div class="p-6 border-b border-[#FAF8F5]">
                            <div class="relative"><i class="ph-regular ph-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-[#A39A8E]"></i><input type="text" placeholder="Search..." class="w-full pl-9 pr-3 py-2 bg-[#FAF8F5] border border-transparent rounded-lg text-[13px] focus:bg-white focus:outline-none focus:border-[#C27803]/30 transition-all text-[#1A1614]"></div>
                        </div>
                        <div class="flex-1 overflow-y-auto">
                            <div onclick="renderActiveChat(1)" class="p-4 border-b border-[#FAF8F5] hover:bg-[#FAF8F5] cursor-pointer transition-colors bg-[#FAF8F5]/50 relative group"><div class="absolute left-0 top-0 bottom-0 w-1 bg-[#C27803] rounded-r"></div><div class="flex justify-between items-start mb-1"><h4 class="font-medium text-[13px] text-[#1A1614] group-hover:text-[#C27803] transition-colors">Karim Handicrafts</h4><span class="text-[10px] text-[#A39A8E]">10:30 AM</span></div><p class="text-[12px] truncate text-[#6B635A]">Regarding the payout delay...</p></div>
                            <div onclick="renderActiveChat(2)" class="p-4 border-b border-[#FAF8F5] hover:bg-[#FAF8F5] cursor-pointer transition-colors group"><div class="flex justify-between items-start mb-1"><h4 class="font-medium text-[13px] text-[#1A1614] group-hover:text-[#C27803] transition-colors">Heritage Pottery</h4><span class="text-[10px] text-[#A39A8E]">Yesterday</span></div><p class="text-[12px] truncate text-[#A39A8E]">Can I update my GI cert?</p></div>
                        </div>
                    </div>
                    <!-- Main Chat -->
                    <div class="flex-1 flex flex-col bg-[#FAF8F5]/30 relative" id="chat-view">
                        <div class="p-6 border-b border-[#E8E3DB] bg-white flex justify-between items-center"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-full bg-[#FAF8F5] border border-[#E8E3DB] flex items-center justify-center font-serif text-[#C27803]">KH</div><div><h3 class="font-medium text-[14px] text-[#1A1614]">Karim Handicrafts</h3><p class="text-[10px] text-emerald-600 mt-0.5 font-medium flex items-center gap-1"><span class="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span> Online</p></div></div><button class="text-[#A39A8E] hover:text-[#C27803] transition-colors"><i class="ph-duotone ph-info text-xl"></i></button></div>
                        <div class="flex-1 p-8 overflow-y-auto space-y-6" id="chat-messages-box">
                            <div class="flex gap-3"><div class="w-8 h-8 rounded-full bg-white border border-[#E8E3DB] flex items-center justify-center text-[10px] font-serif text-[#1A1614] self-end mb-1">KH</div><div class="bg-white border border-[#E8E3DB] py-3 px-4 bubble-received max-w-[70%] text-[13px] text-[#1A1614] shadow-sm leading-relaxed">Hello Admin, I have a query regarding my payout #TRX-8821. It still shows processing.</div></div>
                            <div class="flex gap-3 flex-row-reverse"><div class="w-8 h-8 bg-[#C27803] rounded-full flex items-center justify-center text-white text-[10px] font-serif self-end mb-1">A</div><div class="bg-[#1A1614] text-[#D6D0C4] py-3 px-4 bubble-sent shadow-sm max-w-[70%] text-[13px] leading-relaxed border border-[#C27803]/30">Hi Karim! Let me check that for you immediately. It usually takes 24-48 hours.</div></div>
                        </div>
                        <div class="p-5 border-t border-[#E8E3DB] bg-white"><div class="flex gap-2 items-center"><button onclick="document.getElementById('hidden-file-input').click()" class="p-2 text-[#A39A8E] hover:text-[#C27803] transition-colors"><i class="ph-duotone ph-paperclip text-xl"></i></button><input type="text" id="chat-input-field" onkeypress="if(event.key === 'Enter') sendChatMessage()" placeholder="Type your message..." class="flex-1 bg-[#FAF8F5] border border-transparent rounded-full py-2.5 px-4 text-[13px] focus:bg-white focus:outline-none focus:border-[#C27803]/30 transition-all text-[#1A1614]"><button onclick="sendChatMessage()" class="p-2.5 bg-[#1A1614] text-white rounded-full hover:bg-[#C27803] transition-colors"><i class="ph-fill ph-paper-plane-right text-sm"></i></button></div></div>
                    </div>
                </div>
                <!-- Hidden Templates -->
                <div id="chat-1" class="hidden"><div class="p-6 border-b border-[#E8E3DB] bg-white flex justify-between items-center"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-full bg-[#FAF8F5] border border-[#E8E3DB] flex items-center justify-center font-serif text-[#C27803]">KH</div><div><h3 class="font-medium text-[14px] text-[#1A1614]">Karim Handicrafts</h3><p class="text-[10px] text-emerald-600 mt-0.5 font-medium flex items-center gap-1"><span class="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span> Online</p></div></div></div><div class="flex-1 p-8 overflow-y-auto space-y-6" id="chat-messages-box"><div class="flex gap-3"><div class="w-8 h-8 rounded-full bg-white border border-[#E8E3DB] flex items-center justify-center text-[10px] font-serif text-[#1A1614] self-end mb-1">KH</div><div class="bg-white border border-[#E8E3DB] py-3 px-4 bubble-received max-w-[70%] text-[13px] text-[#1A1614] shadow-sm">Query regarding payout #TRX-8821.</div></div><div class="flex gap-3 flex-row-reverse"><div class="w-8 h-8 bg-[#C27803] rounded-full flex items-center justify-center text-white text-[10px] font-serif self-end mb-1">A</div><div class="bg-[#1A1614] text-[#D6D0C4] py-3 px-4 bubble-sent shadow-sm max-w-[70%] text-[13px] border border-[#C27803]/30">Checking now...</div></div></div><div class="p-5 border-t border-[#E8E3DB] bg-white"><div class="flex gap-2 items-center"><button onclick="document.getElementById('hidden-file-input').click()" class="p-2 text-[#A39A8E] hover:text-[#C27803] transition-colors"><i class="ph-duotone ph-paperclip text-xl"></i></button><input type="text" id="chat-input-field" onkeypress="if(event.key === 'Enter') sendChatMessage()" placeholder="Type your message..." class="flex-1 bg-[#FAF8F5] border border-transparent rounded-full py-2.5 px-4 text-[13px] focus:bg-white focus:outline-none focus:border-[#C27803]/30 transition-all text-[#1A1614]"><button onclick="sendChatMessage()" class="p-2.5 bg-[#1A1614] text-white rounded-full hover:bg-[#C27803] transition-colors"><i class="ph-fill ph-paper-plane-right text-sm"></i></button></div></div></div>
                <div id="chat-2" class="hidden"><div class="p-6 border-b border-[#E8E3DB] bg-white flex justify-between items-center"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-full bg-[#FAF8F5] border border-[#E8E3DB] flex items-center justify-center font-serif text-[#C27803]">HP</div><div><h3 class="font-medium text-[14px] text-[#1A1614]">Heritage Pottery</h3><p class="text-[10px] text-[#A39A8E] mt-0.5 font-medium flex items-center gap-1"><span class="w-1.5 h-1.5 bg-[#A39A8E] rounded-full"></span> Offline</p></div></div></div><div class="flex-1 p-8 overflow-y-auto space-y-6" id="chat-messages-box"><div class="flex gap-3"><div class="w-8 h-8 rounded-full bg-white border border-[#E8E3DB] flex items-center justify-center text-[10px] font-serif text-[#1A1614] self-end mb-1">HP</div><div class="bg-white border border-[#E8E3DB] py-3 px-4 bubble-received max-w-[70%] text-[13px] text-[#1A1614] shadow-sm">Hi, can I update my GI certificate?</div></div></div><div class="p-5 border-t border-[#E8E3DB] bg-white"><div class="flex gap-2 items-center"><button onclick="document.getElementById('hidden-file-input').click()" class="p-2 text-[#A39A8E] hover:text-[#C27803] transition-colors"><i class="ph-duotone ph-paperclip text-xl"></i></button><input type="text" id="chat-input-field" onkeypress="if(event.key === 'Enter') sendChatMessage()" placeholder="Type your message..." class="flex-1 bg-[#FAF8F5] border border-transparent rounded-full py-2.5 px-4 text-[13px] focus:bg-white focus:outline-none focus:border-[#C27803]/30 transition-all text-[#1A1614]"><button onclick="sendChatMessage()" class="p-2.5 bg-[#1A1614] text-white rounded-full hover:bg-[#C27803] transition-colors"><i class="ph-fill ph-paper-plane-right text-sm"></i></button></div></div></div>
            `;
        }

        function renderProducts() {
            return `
                ${renderHeader('Product Catalog', 'Inventory overview.', '<button onclick="addProductPrompt()" class="bg-[#1A1614] text-white px-5 py-2.5 rounded-full text-[13px] font-medium flex items-center gap-2 hover:bg-[#C27803] transition-colors hover-lift shadow-lg shadow-black/10"><i class="ph-bold ph-plus"></i> New Draft</button>')}
                <div class="bg-white rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] overflow-hidden fade-in">
                    <table class="w-full text-left">
                        <thead class="text-[10px] font-bold text-[#A39A8E] uppercase tracking-widest border-b border-[#FAF8F5]"><tr><th class="px-8 py-5 font-normal">Item</th><th class="px-6 py-5 font-normal">Origin</th><th class="px-6 py-5 font-normal">Price</th><th class="px-6 py-5 font-normal text-right">Status</th></tr></thead>
                        <tbody class="divide-y divide-[#FAF8F5]">
                            ${MOCK_PRODUCTS.map(p => `
                                <tr class="hover:bg-[#FAF8F5]/50 transition-colors group">
                                    <td class="px-8 py-5"><div class="flex items-center gap-4"><div class="w-10 h-10 bg-white border border-[#E8E3DB] rounded-lg flex items-center justify-center text-[#A39A8E] group-hover:border-[#C27803]/50 transition-colors"><i class="ph-duotone ${p.img} text-lg group-hover:text-[#C27803] transition-colors"></i></div><div><div class="font-medium text-[13px] text-[#1A1614] group-hover:text-[#C27803] transition-colors">${p.name}</div>${p.gi_status === 'Certified' ? '<span class="text-[9px] text-[#C27803] uppercase tracking-wider font-bold bg-[#C27803]/10 px-2 py-0.5 rounded mt-1 inline-block border border-[#C27803]/20">GI Certified</span>' : ''}</div></div></td>
                                    <td class="px-6 py-5"><div class="text-[13px] text-[#6B635A]">${p.seller}</div><div class="text-[10px] text-[#A39A8E] mt-0.5">${p.seller_mail}</div></td>
                                    <td class="px-6 py-5 font-mono text-[13px] text-[#1A1614] font-medium">BDT ${p.price.toLocaleString()}</td>
                                    <td class="px-6 py-5 text-right"><select onchange="updateProductStatus(${p.id}, this.value)" class="bg-white border border-[#E8E3DB] text-[11px] font-medium text-[#1A1614] rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#C27803] cursor-pointer shadow-sm hover:border-[#C27803]/50 transition-colors"><option ${p.status === 'Live' ? 'selected' : ''}>Live</option><option ${p.status === 'Draft' ? 'selected' : ''}>Draft</option><option ${p.status === 'Hidden' ? 'selected' : ''}>Hidden</option></select></td>
                                </tr>`).join('')}
                        </tbody>
                    </table>
                </div>`;
        }

        function renderProductQC() {
            return `
                ${renderHeader('Quality Control', 'Maintain marketplace standards.')}
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 fade-in">
                    ${MOCK_QC.map(q => `
                        <div class="bg-white p-7 rounded-3xl border border-[#E8E3DB] premium-shadow flex flex-col hover-lift group">
                            <div class="flex gap-4 mb-6">
                                <div class="w-14 h-14 bg-[#FAF8F5] border border-[#E8E3DB] rounded-xl flex items-center justify-center group-hover:border-[#C27803]/40 transition-colors"><i class="ph-duotone ph-package text-2xl text-[#A39A8E] group-hover:text-[#C27803] transition-colors"></i></div>
                                <div><h4 class="font-serif font-medium text-lg text-[#1A1614] mb-0.5 group-hover:text-[#C27803] transition-colors">${q.title}</h4><p class="text-[10px] text-[#A39A8E] uppercase tracking-widest font-mono">By ${q.seller}</p><p class="text-[10px] text-[#A39A8E] mt-1">${q.date}</p></div>
                            </div>
                            <button onclick="showToast('Opening Technical Specifications...', 'info')" class="w-full py-2.5 mb-4 bg-[#FAF8F5] border border-[#E8E3DB] text-[#1A1614] rounded-xl text-[12px] font-medium hover:bg-white hover:border-[#C27803]/30 transition-all flex items-center justify-center gap-2"><i class="ph-bold ph-magnifying-glass"></i> View QC Docs</button>
                            <div class="mt-auto grid grid-cols-3 gap-2">
                                <button onclick="openNoteModal('reject', ${q.id})" class="py-2 bg-white border border-[#E8E3DB] text-red-600 rounded-xl text-[12px] font-medium hover:bg-red-50 hover:border-red-200 transition-colors">Reject</button>
                                <button onclick="openNoteModal('resubmit', ${q.id})" class="py-2 bg-white border border-[#E8E3DB] text-[#6B635A] rounded-xl text-[12px] font-medium hover:bg-[#FAF8F5] hover:text-[#C27803] transition-colors">Resubmit</button>
                                <button onclick="approveQCDirect(${q.id})" class="py-2 bg-[#1A1614] text-white rounded-xl text-[12px] font-medium hover:bg-[#C27803] transition-colors shadow-sm">Approve</button>
                            </div>
                        </div>
                    `).join('')}
                </div>`;
        }

        function renderGIVerification() {
            return `
                ${renderHeader('GI Certification', 'Protect regional authenticity.')}
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8 fade-in">
                    ${MOCK_GI_REQUESTS.map(req => `
                        <div class="bg-white p-8 rounded-3xl border border-[#E8E3DB] premium-shadow flex flex-col hover-lift group">
                            <div class="flex justify-between items-start mb-6">
                                <div class="flex items-center gap-4">
                                    <div class="w-12 h-12 bg-amber-50 rounded-xl flex items-center justify-center text-[#C27803] border border-amber-100/50"><i class="ph-duotone ph-medal text-2xl"></i></div>
                                    <div><h4 class="font-serif font-medium text-lg text-[#1A1614] mb-0.5 group-hover:text-[#C27803] transition-colors">${req.product}</h4><p class="text-[11px] font-mono uppercase tracking-widest text-[#A39A8E]"><i class="ph-fill ph-map-pin"></i> ${req.district}</p></div>
                                </div>
                                <span class="bg-[#FAF8F5] text-[#6B635A] text-[9px] px-2.5 py-1 rounded font-bold uppercase tracking-widest border border-[#E8E3DB]">Pending</span>
                            </div>
                            <div class="bg-[#FAF8F5] rounded-xl p-4 mb-4 border border-[#E8E3DB]/50">
                                <div class="flex items-center justify-between"><div class="flex items-center gap-3"><div class="w-8 h-8 bg-white rounded-full flex items-center justify-center font-serif text-[#1A1614] text-xs border border-[#E8E3DB]">${req.seller.charAt(0)}</div><span class="text-[13px] font-medium text-[#1A1614]">${req.seller}</span></div><span class="text-[10px] text-[#A39A8E]">${req.date}</span></div>
                            </div>
                            <button onclick="showToast('Opening GI Evidence Dossier...', 'info')" class="w-full py-2.5 mb-4 bg-white border border-[#E8E3DB] text-[#1A1614] rounded-xl text-[12px] font-medium hover:bg-[#FAF8F5] hover:border-[#C27803]/30 transition-all flex items-center justify-center gap-2 shadow-sm"><i class="ph-bold ph-books"></i> View Dossier</button>
                            <div class="mt-auto grid grid-cols-3 gap-2">
                                <button onclick="openNoteModal('reject', ${req.id})" class="py-2.5 bg-white border border-[#E8E3DB] text-red-600 rounded-xl text-[12px] font-medium hover:bg-red-50 hover:border-red-200 transition-colors">Deny</button>
                                <button onclick="openNoteModal('resubmit', ${req.id})" class="py-2.5 bg-white border border-[#E8E3DB] text-[#6B635A] rounded-xl text-[12px] font-medium hover:bg-[#FAF8F5] hover:text-[#C27803] transition-colors">Resubmit</button>
                                <button onclick="approveGIDirect(${req.id})" class="py-2.5 bg-[#1A1614] text-white rounded-xl text-[12px] font-medium hover:bg-[#C27803] transition-colors shadow-sm">Grant GI</button>
                            </div>
                        </div>
                    `).join('')}
                </div>`;
        }

        function renderOrders() {
            return `
                ${renderHeader('Logistics', 'Manage shipments.', '<button onclick="triggerExport(\'Manifest\')" class="bg-white border border-[#E8E3DB] text-[#1A1614] px-5 py-2.5 rounded-full text-[13px] font-medium hover:bg-[#FAF8F5] hover:text-[#C27803] hover:border-[#C27803]/30 transition-all hover-lift"><i class="ph-bold ph-download-simple"></i> Export Manifest</button>')}
                <div class="bg-white rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] overflow-hidden fade-in">
                    <table class="w-full text-left">
                        <thead class="text-[10px] font-bold text-[#A39A8E] uppercase tracking-widest border-b border-[#FAF8F5]"><tr><th class="px-8 py-5 font-normal">Order ID</th><th class="px-6 py-5 font-normal">Customer</th><th class="px-6 py-5 font-normal">Total Amount</th><th class="px-6 py-5 font-normal text-right">Status</th></tr></thead>
                        <tbody class="divide-y divide-[#FAF8F5]">
                            ${MOCK_ORDERS.map(o => `
                                <tr class="hover:bg-[#FAF8F5]/50 transition-colors group">
                                    <td class="px-8 py-5"><div class="font-medium text-[13px] text-[#1A1614] group-hover:text-[#C27803] transition-colors">${o.id}</div><div class="text-[11px] text-[#A39A8E] mt-0.5 font-mono">${o.date}</div></td>
                                    <td class="px-6 py-5"><div class="text-[13px] text-[#6B635A]">${o.customer}</div><div class="text-[10px] text-[#A39A8E] mt-0.5">${o.email}</div></td>
                                    <td class="px-6 py-5 font-mono text-[13px] text-[#1A1614] font-medium">BDT ${o.total.toLocaleString()}</td>
                                    <td class="px-6 py-5 text-right"><span class="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded bg-white border ${o.status === 'Delivered' ? 'border-emerald-200 text-emerald-600 bg-emerald-50/50' : o.status === 'Processing' ? 'border-amber-200 text-amber-600 bg-amber-50/50' : 'border-blue-200 text-blue-600 bg-blue-50/50'}">${o.status}</span></td>
                                </tr>`).join('')}
                        </tbody>
                    </table>
                </div>`;
        }

        function renderFlashSale() {
            return `
                ${renderHeader("Artisan's Hour", 'Curated exclusive drops.', '<button onclick="toggleFlashSaleStatus()" class="bg-[#1A1614] text-white px-6 py-2.5 rounded-full text-[13px] font-medium hover:bg-[#C27803] transition-colors hover-lift shadow-lg shadow-[#C27803]/10">' + (flashSaleStatus === "Active" ? "End Drop" : "Go Live") + '</button>')}
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 fade-in">
                    <!-- Status Panel -->
                    <div class="lg:col-span-4 bg-[#1A1614] rounded-3xl p-8 text-white relative overflow-hidden shadow-[0_12px_32px_-12px_rgba(26,22,20,0.5)] flex flex-col justify-between border border-[#C27803]/20">
                        <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5"></div>
                        <div class="absolute top-0 right-0 w-64 h-64 bg-[#C27803]/15 rounded-full blur-[80px] -mr-10 -mt-10 pointer-events-none"></div>
                        
                        <div class="relative z-10 flex justify-between items-start mb-12">
                            <h3 class="font-serif text-2xl font-light tracking-wide text-[#C27803]">Event Status</h3>
                            <div class="flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full ${flashSaleStatus === "Active" ? "bg-emerald-400 premium-glow" : "bg-[#6B635A]"}"></span>
                                <span class="text-[10px] uppercase font-mono tracking-widest text-[#D6D0C4]">${flashSaleStatus}</span>
                            </div>
                        </div>
                        <div class="relative z-10 space-y-6">
                            <div>
                                <label class="text-[10px] uppercase tracking-widest text-[#A39A8E] mb-2 block">Opening Time</label>
                                <input type="time" id="flash-start-time" value="${flashStartTime}" class="bg-transparent border-b border-white/20 text-xl font-serif text-white w-full pb-2 focus:outline-none focus:border-[#C27803] transition-colors">
                            </div>
                            <div>
                                <label class="text-[10px] uppercase tracking-widest text-[#A39A8E] mb-2 block">Closing Time</label>
                                <input type="time" id="flash-end-time" value="${flashEndTime}" class="bg-transparent border-b border-white/20 text-xl font-serif text-white w-full pb-2 focus:outline-none focus:border-[#C27803] transition-colors">
                            </div>
                            <!-- Hidden date fields to keep data logic intact -->
                            <input type="date" id="flash-start-date" value="${new Date().toISOString().split('T')[0]}" class="hidden"><input type="date" id="flash-end-date" value="${new Date().toISOString().split('T')[0]}" class="hidden">
                            <button onclick="updateFlashSchedule()" class="w-full py-3 mt-4 text-[13px] font-medium text-[#1A1614] bg-[#C27803] text-white rounded-xl hover:bg-[#A36502] transition-colors shadow-lg shadow-[#C27803]/20">Sync Schedule</button>
                        </div>
                    </div>

                    <!-- Queue -->
                    <div class="lg:col-span-8 bg-white rounded-3xl p-8 border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] flex flex-col min-h-[400px]">
                        <div class="flex justify-between items-center mb-6 pb-6 border-b border-[#FAF8F5]">
                            <h3 class="font-serif text-2xl text-[#1A1614]">Drop Queue</h3>
                            <span class="text-[11px] font-medium text-[#A39A8E] bg-[#FAF8F5] px-3 py-1 rounded border border-[#E8E3DB]">${MOCK_FLASH_REQ.length} Items</span>
                        </div>
                        <div class="flex-1 overflow-y-auto space-y-3 pr-2">
                            ${MOCK_FLASH_REQ.length > 0 ? MOCK_FLASH_REQ.map(req => `
                                <div class="flex items-center justify-between p-4 rounded-2xl bg-white border border-[#E8E3DB] hover:border-[#C27803]/40 transition-all group shadow-sm hover:shadow-md">
                                    <div class="flex items-center gap-4">
                                        <div class="w-10 h-10 rounded-lg bg-[#FAF8F5] border border-[#E8E3DB] flex items-center justify-center text-[#A39A8E] group-hover:text-[#C27803] transition-colors"><i class="ph-duotone ph-lightning text-lg"></i></div>
                                        <div><h4 class="font-medium text-[14px] text-[#1A1614] mb-0.5 group-hover:text-[#C27803] transition-colors">${req.product}</h4><p class="text-[11px] text-[#A39A8E]">${req.seller}</p></div>
                                    </div>
                                    <div class="text-right">
                                        <p class="text-[10px] text-[#A39A8E] line-through mb-0.5 font-mono">BDT ${req.old_price}</p>
                                        <p class="text-lg font-serif text-[#C27803] font-medium">BDT ${req.new_price}</p>
                                    </div>
                                    <div class="flex gap-2">
                                        <button onclick="approveFlashSale(${req.id})" class="px-4 py-2 bg-[#1A1614] text-white text-[12px] font-medium rounded-lg hover:bg-[#C27803] transition-colors shadow-sm">Approve</button>
                                        <button onclick="openNoteModal('reject', ${req.id})" class="px-4 py-2 bg-white border border-[#E8E3DB] text-red-600 text-[12px] font-medium rounded-lg hover:bg-red-50 hover:border-red-200 transition-colors">Reject</button>
                                    </div>
                                </div>
                            `).join('') : '<div class="text-center text-[#A39A8E] py-10 font-serif border border-dashed border-[#E8E3DB] rounded-2xl">Queue is empty.</div>'}
                        </div>
                    </div>
                </div>`;
        }

        function renderFinance() { 
            return `
                ${renderHeader('Finance & Ledger', 'Capital flows and payouts.', '<button class="bg-white border border-[#E8E3DB] text-[#1A1614] px-5 py-2.5 rounded-full text-[13px] font-medium hover:bg-[#FAF8F5] transition-colors flex items-center gap-2 hover-lift"><i class="ph-bold ph-download-simple"></i> Download Statement</button>')}
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 fade-in">
                    <div class="lg:col-span-2 bg-white rounded-3xl border border-[#E8E3DB] premium-shadow overflow-hidden">
                        <div class="p-7 border-b border-[#FAF8F5] flex justify-between items-center"><h3 class="font-serif font-medium text-xl text-[#1A1614]">Recent Ledger</h3></div>
                        <table class="w-full text-left">
                            <thead class="bg-[#FAF8F5] text-[10px] font-bold text-[#A39A8E] uppercase tracking-widest border-b border-[#E8E3DB]"><tr><th class="px-6 py-4 font-normal">Reference</th><th class="px-6 py-4 font-normal">Entity</th><th class="px-6 py-4 font-normal text-right">Amount</th><th class="px-6 py-4 font-normal text-center">Status</th></tr></thead>
                            <tbody class="divide-y divide-[#FAF8F5]">
                                ${MOCK_TRANSACTIONS.map(t => `<tr class="hover:bg-[#FAF8F5]/50 transition-colors group"><td class="px-6 py-4"><div class="font-medium text-[#1A1614] text-[13px] mb-0.5 group-hover:text-[#C27803] transition-colors">${t.id}</div><div class="text-[10px] font-mono text-[#A39A8E] uppercase">${t.method} • ${t.date}</div></td><td class="px-6 py-4"><div class="font-medium text-[13px] text-[#6B635A]">${t.party}</div><div class="text-[10px] text-[#A39A8E] mt-0.5">${t.email}</div></td><td class="px-6 py-4 text-right font-mono font-medium text-[13px] ${t.amount < 0 ? 'text-red-600' : 'text-emerald-600'}">${t.amount < 0 ? '' : '+ '}BDT ${Math.abs(t.amount).toLocaleString()}</td><td class="px-6 py-4 text-center"><span class="bg-white border ${t.status === 'Completed' ? 'border-emerald-200 text-emerald-600' : 'border-amber-200 text-amber-600'} px-2.5 py-1 rounded text-[10px] uppercase tracking-widest font-bold shadow-sm">${t.status}</span></td></tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                    <div class="bg-[#1A1614] rounded-3xl p-8 text-white relative overflow-hidden shadow-[0_12px_32px_-12px_rgba(26,22,20,0.5)] border border-[#C27803]/20">
                        <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5"></div>
                        <h3 class="font-serif text-xl font-light text-[#C27803] mb-8 relative z-10">Pending Disbursements</h3>
                        <div class="space-y-4 relative z-10">
                            <div class="bg-white/5 border border-white/10 p-5 rounded-2xl flex flex-col gap-3 hover:bg-white/10 transition-colors">
                                <div class="flex justify-between items-start">
                                    <div><p class="text-[14px] font-medium text-white mb-0.5">Jamdani Palace</p><p class="text-[10px] text-[#A39A8E] font-mono">Bank Transfer</p></div>
                                    <p class="text-lg font-serif text-white">BDT 45,000</p>
                                </div>
                                <div class="flex gap-2 mt-2">
                                    <button onclick="showToast('Payout authorized.', 'success')" class="flex-1 py-2 bg-[#C27803] text-white rounded-lg text-[12px] font-medium hover:bg-[#A36502] transition-colors">Authorize</button>
                                    <button onclick="showToast('Payout placed on hold.', 'error')" class="px-4 py-2 border border-white/20 text-[#D6D0C4] rounded-lg text-[12px] font-medium hover:bg-white/10 transition-colors">Hold</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>`; 
        }

        function renderCommissions() { 
            return `
                ${renderHeader('Platform Commissions', 'Transparent revenue model.')}
                <div class="bg-white rounded-3xl border border-[#E8E3DB] premium-shadow mb-10 flex flex-col md:flex-row divide-y md:divide-y-0 md:divide-x divide-[#E8E3DB] fade-in">
                    <div class="flex-1 p-10 flex flex-col items-center justify-center text-center group hover:bg-[#FAF8F5]/50 transition-colors">
                        <p class="text-[10px] font-mono text-[#A39A8E] uppercase tracking-widest mb-3 group-hover:text-[#C27803] transition-colors">Gross Yield</p>
                        <h3 class="text-4xl font-serif text-[#1A1614] font-normal">BDT 1.2L</h3>
                    </div>
                    <div class="flex-1 p-10 flex flex-col items-center justify-center text-center group hover:bg-[#FAF8F5]/50 transition-colors">
                        <p class="text-[10px] font-mono text-[#A39A8E] uppercase tracking-widest mb-3 group-hover:text-[#C27803] transition-colors">Current Cycle</p>
                        <h3 class="text-4xl font-serif text-[#1A1614] font-normal">BDT 45k</h3>
                    </div>
                    <div class="flex-1 p-10 flex flex-col items-center justify-center text-center bg-[#FAF8F5]">
                        <p class="text-[10px] font-mono text-[#C27803] uppercase tracking-widest mb-3 font-bold">In Escrow</p>
                        <h3 class="text-4xl font-serif text-[#C27803] font-medium">BDT 12k</h3>
                    </div>
                </div>
                <div class="max-w-3xl mx-auto fade-in-delayed bg-white p-8 rounded-3xl border border-[#E8E3DB] shadow-sm">
                    <h4 class="font-serif text-xl text-[#1A1614] mb-6 border-b border-[#FAF8F5] pb-4">Standard Logic</h4>
                    <div class="space-y-2">
                        <div class="flex justify-between items-center py-4 border-b border-[#FAF8F5] group">
                            <span class="text-[14px] text-[#1A1614] font-medium group-hover:text-[#C27803] transition-colors">Standard Artifact Sales</span>
                            <span class="font-mono text-[14px] text-[#6B635A] bg-[#FAF8F5] px-3 py-1 rounded-lg border border-[#E8E3DB]">10.0%</span>
                        </div>
                        <div class="flex justify-between items-center py-4 group border-b border-[#FAF8F5] last:border-0">
                            <span class="text-[14px] text-[#1A1614] font-medium flex items-center gap-2 group-hover:text-[#C27803] transition-colors"><i class="ph-duotone ph-medal text-[#C27803] text-lg"></i> GI Certified Artifact Sales</span>
                            <span class="font-mono text-[14px] text-[#C27803] bg-[#C27803]/10 px-3 py-1 rounded-lg border border-[#C27803]/20 font-bold">8.0%</span>
                        </div>
                    </div>
                </div>`; 
        }

        function renderTodaysArtisan() {
            return `
                ${renderHeader("Featured Artisan", 'Spotlight a master craftsman on the storefront.')}
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 fade-in">
                    <!-- Current Active -->
                    <div class="lg:col-span-2 relative overflow-hidden rounded-3xl shadow-[0_12px_32px_-12px_rgba(26,22,20,0.5)] group h-[500px] border border-[#E8E3DB]">
                        <img src="${FEATURED_ARTISAN.img}" class="absolute inset-0 w-full h-full object-cover transition-transform duration-[1.5s] ease-out group-hover:scale-105">
                        <div class="absolute inset-0 bg-gradient-to-t from-[#1A1614] via-[#1A1614]/40 to-transparent"></div>
                        <div class="relative z-10 p-10 h-full flex flex-col justify-end">
                            <div class="flex items-center gap-3 mb-4"><span class="bg-[#C27803] text-white text-[10px] font-bold px-3 py-1.5 rounded uppercase tracking-widest shadow-lg flex items-center gap-1.5 border border-[#C27803]"><span class="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span> Spotlight Live</span></div>
                            <h2 class="text-4xl font-serif text-white mb-2 leading-tight">${FEATURED_ARTISAN.name}</h2>
                            <p class="text-[#D6D0C4] text-[15px] mb-8 font-medium tracking-wide flex items-center gap-2"><i class="ph-duotone ph-map-pin text-[#C27803]"></i> ${FEATURED_ARTISAN.desc}</p>
                            <div class="grid grid-cols-3 gap-4 bg-[#1A1614]/80 backdrop-blur-md p-5 rounded-2xl border border-white/10 max-w-lg"><div><p class="text-[10px] text-[#A39A8E] uppercase tracking-widest font-mono mb-1">Rating</p><p class="text-xl font-serif text-[#C27803]">${FEATURED_ARTISAN.rating}</p></div><div><p class="text-[10px] text-[#A39A8E] uppercase tracking-widest font-mono mb-1">Artifacts</p><p class="text-xl font-serif text-white">${FEATURED_ARTISAN.prods}</p></div><div><p class="text-[10px] text-[#A39A8E] uppercase tracking-widest font-mono mb-1">Since</p><p class="text-xl font-serif text-white">${FEATURED_ARTISAN.since}</p></div></div>
                        </div>
                    </div>

                    <!-- Selection Panel -->
                    <div class="bg-white p-8 rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] flex flex-col h-[500px]">
                        <div class="mb-6 pb-6 border-b border-[#FAF8F5]"><h3 class="font-serif text-xl text-[#1A1614] mb-1">Selection Queue</h3><p class="text-[12px] text-[#A39A8E]">Top-rated artisans eligible for spotlight.</p></div>
                        <div class="flex-1 overflow-y-auto space-y-2 pr-2">
                            ${MOCK_SELLERS.map(s => `
                                <div class="flex items-center gap-4 p-4 rounded-2xl bg-white border border-[#E8E3DB] hover:border-[#C27803]/40 cursor-pointer group transition-all shadow-sm hover:shadow-md">
                                    <img src="${s.img}" class="w-12 h-12 rounded-full bg-[#FAF8F5] border border-[#E8E3DB]">
                                    <div class="flex-1"><h4 class="font-medium text-[13px] text-[#1A1614] group-hover:text-[#C27803] transition-colors mb-0.5">${s.name}</h4><div class="flex items-center gap-1.5 text-[11px] font-medium text-[#A39A8E]"><span class="text-[#C27803]"><i class="ph-fill ph-star"></i> ${s.rating}</span><span>• ${s.district}</span></div></div>
                                    <button onclick="selectTodaysArtisan(${s.id})" class="bg-[#FAF8F5] text-[#1A1614] border border-[#E8E3DB] px-3 py-1.5 rounded-lg text-[11px] font-medium group-hover:bg-[#C27803] group-hover:text-white group-hover:border-[#C27803] transition-all">Select</button>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>`;
        }

        function renderJournal() {
            return `
                ${renderHeader('Heritage Journal', 'Curate stories that define our culture.', '<button onclick="addNewJournal()" class="bg-[#1A1614] text-white px-5 py-2.5 rounded-full font-medium text-[13px] shadow-lg hover:bg-[#C27803] transition-colors flex items-center gap-2 hover-lift"><i class="ph-bold ph-pen-nib"></i> Compose Story</button>')}
                
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 fade-in">
                    ${MOCK_JOURNAL.map(post => `
                        <div onclick="viewJournal(${post.id})" class="group cursor-pointer hover-lift bg-white rounded-3xl border border-[#E8E3DB] overflow-hidden shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)]">
                            <div class="relative h-48 overflow-hidden">
                                <img src="${post.img}" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105">
                                <div class="absolute top-4 left-4"><span class="bg-white/90 backdrop-blur-sm text-[#1A1614] text-[9px] font-bold px-2.5 py-1 rounded border border-[#E8E3DB] uppercase tracking-widest">${post.status}</span></div>
                            </div>
                            <div class="p-6">
                                <h3 class="font-serif text-lg text-[#1A1614] leading-snug mb-3 group-hover:text-[#C27803] transition-colors">${post.title}</h3>
                                <div class="flex items-center justify-between text-[11px] text-[#A39A8E] font-medium border-t border-[#FAF8F5] pt-4 mt-2">
                                    <span>${post.date}</span>
                                    <span class="flex items-center gap-1"><i class="ph-duotone ph-eye text-[#C27803]"></i> ${post.views}</span>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                    
                    <div onclick="createBlankDraft()" class="h-full min-h-[300px] rounded-3xl border-2 border-dashed border-[#E8E3DB] bg-[#FAF8F5]/50 flex flex-col items-center justify-center text-[#A39A8E] hover:bg-white hover:border-[#C27803]/40 hover:text-[#C27803] transition-all cursor-pointer group hover-lift shadow-sm">
                        <div class="w-14 h-14 rounded-full bg-white border border-[#E8E3DB] flex items-center justify-center mb-4 group-hover:border-[#C27803]/30 group-hover:shadow-md transition-all"><i class="ph-duotone ph-plus text-2xl"></i></div>
                        <span class="font-medium text-[13px] tracking-wide">Start Blank Draft</span>
                    </div>
                </div>`;
        }

        function renderContentTeam() {
            return `
                ${renderHeader('Editorial Team', 'The voices behind the heritage.', '<button onclick="inviteTeamMember()" class="bg-white border border-[#E8E3DB] text-[#1A1614] px-5 py-2.5 rounded-full font-medium text-[13px] hover:bg-[#FAF8F5] hover:text-[#C27803] hover:border-[#C27803]/30 transition-all flex items-center gap-2 hover-lift"><i class="ph-bold ph-user-plus"></i> Invite Writer</button>')}
                
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 fade-in">
                    ${MOCK_TEAM.map(m => `
                        <div class="bg-white p-6 rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] flex items-center justify-between hover:border-[#C27803]/30 transition-all group hover-lift">
                            <div class="flex items-center gap-4">
                                <div class="w-12 h-12 bg-[#FAF8F5] border border-[#E8E3DB] rounded-full flex items-center justify-center font-serif text-[#1A1614] text-lg group-hover:bg-[#C27803]/10 group-hover:text-[#C27803] transition-colors group-hover:border-[#C27803]/20">${m.name.charAt(0)}</div>
                                <div><h4 class="font-medium text-[#1A1614] text-[14px] mb-0.5 group-hover:text-[#C27803] transition-colors">${m.name}</h4><p class="text-[10px] font-mono text-[#A39A8E]">${m.email}</p></div>
                            </div>
                            <div class="text-right">
                                <p class="text-[9px] font-bold uppercase tracking-widest text-[#C27803] mb-1">${m.role}</p>
                                <p class="text-[11px] text-[#6B635A] font-medium"><i class="ph-duotone ph-article"></i> ${m.art}</p>
                            </div>
                            <button onclick="deleteTeamMember(${m.id})" class="absolute top-2 right-2 p-2 text-[#E8E3DB] hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"><i class="ph-bold ph-x"></i></button>
                        </div>
                    `).join('')}
                </div>`;
        }

        // --- NEW COUPON MODULE ---
        function renderCoupons() {
            return `
                ${renderHeader('Coupon Management', 'Generate and monitor promotional codes.', '<button onclick="openCreateCouponModal()" class="bg-[#1A1614] text-white px-5 py-2.5 rounded-full text-[13px] font-medium flex items-center gap-2 hover:bg-[#C27803] transition-colors hover-lift shadow-lg shadow-black/10"><i class="ph-bold ph-plus"></i> Create Coupon</button>')}
                
                <div class="bg-white rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] overflow-hidden fade-in">
                    <table class="w-full text-left">
                        <thead class="text-[10px] font-bold text-[#A39A8E] uppercase tracking-widest border-b border-[#FAF8F5]">
                            <tr>
                                <th class="px-8 py-5 font-normal">Code & Details</th>
                                <th class="px-6 py-5 font-normal">Discount</th>
                                <th class="px-6 py-5 font-normal">Usage & Expiry</th>
                                <th class="px-6 py-5 font-normal">Status</th>
                                <th class="px-6 py-5 font-normal text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-[#FAF8F5]">
                            ${MOCK_COUPONS.map(c => `
                                <tr class="hover:bg-[#FAF8F5]/50 transition-colors group">
                                    <td class="px-8 py-5">
                                        <div class="flex items-center gap-4">
                                            <div class="w-10 h-10 rounded-lg bg-[#FAF8F5] border border-[#E8E3DB] flex items-center justify-center text-[#A39A8E] group-hover:text-[#C27803] group-hover:border-[#C27803]/40 transition-colors">
                                                <i class="ph-duotone ph-ticket text-xl"></i>
                                            </div>
                                            <div>
                                                <div class="flex items-center gap-2">
                                                    <span class="font-bold text-[14px] font-mono text-[#1A1614] tracking-wide group-hover:text-[#C27803] transition-colors">${c.code}</span>
                                                    ${c.isNewUser ? '<span class="text-[9px] font-bold uppercase tracking-widest text-[#C27803] bg-[#C27803]/10 border border-[#C27803]/20 px-1.5 py-0.5 rounded">New Users Only</span>' : ''}
                                                </div>
                                                <div class="text-[10px] text-[#A39A8E] uppercase tracking-wider mt-1">${c.type}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td class="px-6 py-5 font-serif text-lg text-[#1A1614] font-medium">${c.discount}</td>
                                    <td class="px-6 py-5">
                                        <div class="text-[12px] text-[#6B635A] font-medium"><i class="ph-duotone ph-users text-[#A39A8E]"></i> ${c.used} / ${c.limit === 'Unlimited' ? '∞' : c.limit} used</div>
                                        <div class="text-[10px] text-[#A39A8E] mt-1"><i class="ph-duotone ph-calendar text-[#A39A8E]"></i> Expires: ${c.expires}</div>
                                    </td>
                                    <td class="px-6 py-5">
                                        <span class="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest bg-white border ${c.status === 'Active' ? 'border-emerald-200 text-emerald-600' : 'border-amber-200 text-amber-600'} px-2.5 py-1 rounded w-fit shadow-sm">
                                            <span class="w-1.5 h-1.5 rounded-full ${c.status === 'Active' ? 'bg-emerald-500' : 'bg-amber-500'}"></span> ${c.status}
                                        </span>
                                    </td>
                                    <td class="px-6 py-5 text-right">
                                        <div class="flex items-center justify-end gap-2">
                                            <button onclick="openEditCouponModal(${c.id})" class="text-[#6B635A] border border-transparent hover:border-[#E8E3DB] hover:bg-[#FAF8F5] px-2 py-1.5 rounded-lg transition-all" title="Edit Coupon">
                                                <i class="ph-bold ph-pencil-simple text-sm"></i>
                                            </button>
                                            <button onclick="toggleCouponStatus(${c.id})" class="text-[#6B635A] border border-[#E8E3DB] hover:text-[#C27803] hover:border-[#C27803] hover:bg-[#FAF8F5] px-3 py-1.5 rounded-lg font-medium text-[11px] transition-all">
                                                ${c.status === 'Active' ? 'Pause' : 'Activate'}
                                            </button>
                                            <button onclick="deleteCoupon(${c.id})" class="text-red-500 border border-transparent hover:border-red-200 hover:bg-red-50 px-2 py-1.5 rounded-lg transition-all" title="Delete">
                                                <i class="ph-bold ph-trash text-sm"></i>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        function renderUserManagement() {
            return `
                ${renderHeader('User Accounts', 'Centralized user governance.', '<button onclick="triggerExport(\'User Report\')" class="bg-white border border-[#E8E3DB] text-[#1A1614] px-5 py-2.5 rounded-full font-medium text-[13px] hover:bg-[#FAF8F5] hover:text-[#C27803] hover:border-[#C27803]/30 transition-all flex items-center gap-2 hover-lift"><i class="ph-bold ph-download-simple"></i> Export Ledger</button>')}
                
                <div class="bg-white rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] overflow-hidden fade-in">
                    <table class="w-full text-left">
                        <thead class="text-[10px] font-bold text-[#A39A8E] uppercase tracking-widest border-b border-[#FAF8F5]">
                            <tr><th class="px-8 py-5 font-normal">Identity</th><th class="px-6 py-5 font-normal">Role</th><th class="px-6 py-5 font-normal">Standing</th><th class="px-6 py-5 font-normal text-right">Controls</th></tr>
                        </thead>
                        <tbody class="divide-y divide-[#FAF8F5]">
                            ${MOCK_USERS.map(u => `
                            <tr class="hover:bg-[#FAF8F5]/50 transition-colors group">
                                <td class="px-8 py-4"><div class="flex items-center gap-4"><div class="w-9 h-9 rounded-full bg-[#FAF8F5] border border-[#E8E3DB] text-[#1A1614] flex items-center justify-center font-serif text-[12px] group-hover:border-[#C27803]/50 group-hover:text-[#C27803] transition-colors">${u.name.charAt(0)}</div><div><div class="font-medium text-[13px] text-[#1A1614] mb-0.5 group-hover:text-[#C27803] transition-colors">${u.name}</div><div class="text-[11px] text-[#A39A8E]">${u.email}</div></div></div></td>
                                <td class="px-6 py-4"><span class="px-2.5 py-1 rounded bg-white text-[#6B635A] border border-[#E8E3DB] text-[10px] font-bold uppercase tracking-widest">${u.role}</span></td>
                                <td class="px-6 py-4">
                                    <span class="px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-widest bg-white border ${u.status === 'Active' ? 'border-emerald-200 text-emerald-600' : 'border-red-200 text-red-600'} flex w-fit items-center gap-1.5 shadow-sm">
                                        <span class="w-1.5 h-1.5 ${u.status === 'Active' ? 'bg-emerald-500' : 'bg-red-500'} rounded-full"></span> ${u.status}
                                    </span>
                                </td>
                                <td class="px-6 py-4 text-right"><button onclick="toggleUserBan(${u.id})" class="text-[#1A1614] hover:text-white font-medium text-[12px] border border-[#E8E3DB] hover:border-[#1A1614] bg-white hover:bg-[#1A1614] px-3 py-1.5 rounded-lg transition-all shadow-sm">${u.status === 'Active' ? 'Revoke Access' : 'Restore'}</button></td>
                            </tr>`).join('')}
                        </tbody>
                    </table>
                </div>`;
        }

        function renderModeration() {
            return `
                ${renderHeader('Dispute Resolution', 'Fairness and safety center.')}
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 fade-in">
                    <div class="bg-white p-8 rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] hover-lift">
                        <div class="flex items-center justify-between mb-8 pb-4 border-b border-[#FAF8F5]"><h3 class="font-serif text-xl text-[#1A1614]">Active Cases</h3><span class="bg-[#C27803]/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest text-[#C27803] rounded border border-[#C27803]/20">${MOCK_DISPUTES.length} Open</span></div>
                        <div class="space-y-4">
                            ${MOCK_DISPUTES.length > 0 ? MOCK_DISPUTES.map(d => `
                            <div class="p-5 bg-white border border-[#E8E3DB] rounded-2xl flex flex-col gap-4 shadow-sm hover:border-[#C27803]/40 transition-colors group">
                                <div class="flex justify-between items-start"><div><h4 class="font-medium text-[#1A1614] text-[14px] group-hover:text-[#C27803] transition-colors">Order ${d.id}</h4><p class="text-[12px] text-[#6B635A] mt-1 leading-relaxed">${d.issue}</p></div><span class="text-[9px] font-bold uppercase tracking-widest bg-[#FAF8F5] text-${d.priority==='High'?'red-600':'amber-600'} px-2 py-1 rounded border border-[#E8E3DB]">${d.priority}</span></div>
                                <div class="flex gap-2 mt-1"><button onclick="resolveDispute('${d.id}', 'Refunded')" class="flex-1 py-2 bg-[#1A1614] text-white rounded-lg text-[12px] font-medium hover:bg-[#C27803] transition-colors shadow-sm">Authorize Refund</button><button onclick="resolveDispute('${d.id}', 'Dismissed')" class="flex-1 py-2 bg-white border border-[#E8E3DB] text-[#6B635A] rounded-lg text-[12px] font-medium hover:bg-[#FAF8F5] hover:text-[#C27803] transition-colors">Dismiss</button></div>
                            </div>
                            `).join('') : '<div class="text-center py-10 text-[#A39A8E] font-serif border border-dashed border-[#E8E3DB] rounded-2xl">No open disputes.</div>'}
                        </div>
                    </div>

                    <div class="bg-white p-8 rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] hover-lift flex flex-col">
                        <div class="flex items-center justify-between mb-8 pb-4 border-b border-[#FAF8F5]"><h3 class="font-serif text-xl text-[#1A1614]">Flagged Content</h3></div>
                        <div class="flex-1 flex flex-col items-center justify-center text-center py-10 text-[#A39A8E] border border-dashed border-[#E8E3DB] rounded-2xl bg-[#FAF8F5]/30">
                            <i class="ph-duotone ph-shield-check text-4xl mb-3 text-[#E8E3DB]"></i>
                            <p class="font-serif text-[#1A1614] text-lg mb-1">Community is safe.</p>
                            <p class="text-[12px]">No content violations reported.</p>
                        </div>
                    </div>
                </div>`;
        }

        function renderLogs() { 
            const logs = (window.__ADMIN_DASHBOARD__.logs && window.__ADMIN_DASHBOARD__.logs.length)
                ? window.__ADMIN_DASHBOARD__.logs
                : [{time:'--', date:'--', user:'System', action:'No audit logs yet', icon:'ph-clock-counter-clockwise', color:'text-[#C27803]', bg:'bg-[#C27803]/10', border:'border-[#C27803]/20'}];
            const logCards = logs.map((l) => `
                <div class="relative pl-8 group">
                    <div class="absolute -left-3 top-0 w-6 h-6 bg-white border border-[#E8E3DB] rounded-full flex items-center justify-center shadow-sm group-hover:border-[#C27803] transition-colors"><div class="w-2 h-2 rounded-full ${(l.color || 'text-[#C27803]').replace('text-', 'bg-')}"></div></div>
                    <div class="bg-white border border-[#E8E3DB] p-4 rounded-2xl shadow-sm hover:shadow-[0_10px_20px_-5px_rgba(194,120,3,0.1)] hover:border-[#C27803]/30 transition-all flex items-center justify-between">
                        <div class="flex items-center gap-4">
                            <div class="w-10 h-10 ${l.bg || 'bg-[#C27803]/10'} ${l.border || 'border-[#C27803]/20'} border rounded-xl flex items-center justify-center ${l.color || 'text-[#C27803]'}"><i class="ph-duotone ${l.icon || 'ph-clock-counter-clockwise'} text-lg"></i></div>
                            <div>
                                <p class="text-[13px] text-[#1A1614] font-medium mb-0.5 group-hover:text-[#C27803] transition-colors">${l.action || 'No audit logs yet'}</p>
                                <p class="text-[11px] text-[#A39A8E]"><span class="font-mono">${l.date || '--'} • ${l.time || '--'}</span> <span class="mx-1 text-[#E8E3DB]">•</span> <span class="text-[#6B635A]">User: ${l.user || 'System'}</span></p>
                            </div>
                        </div>
                        <button class="text-[#E8E3DB] hover:text-[#C27803] transition-colors"><i class="ph-bold ph-caret-right text-lg"></i></button>
                    </div>
                </div>`).join('');
            return `
                ${renderHeader('System Audit Logs', 'Forensic trail of administrative events.')}
                <div class="max-w-4xl mx-auto fade-in pt-6">
                    <div class="bg-white rounded-3xl border border-[#E8E3DB] p-8 shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)]">
                        <div class="relative border-l-[2px] border-[#FAF8F5] ml-4 space-y-8 py-4">${logCards}</div>
                    </div>
                </div>`; 
        }

        function renderProfile() { 
            return `
                ${renderHeader('Profile Settings', 'Manage your executive identity.')}
                <div class="max-w-5xl mx-auto fade-in">
                    <div class="bg-white rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] overflow-hidden">
                        <div class="flex flex-col md:flex-row">
                            <!-- Left: General -->
                            <div class="flex-1 p-10 md:border-r border-[#E8E3DB] relative overflow-hidden group">
                                <div class="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-[#FAF8F5] to-transparent z-0"></div>
                                <h3 class="font-serif text-2xl text-[#1A1614] mb-8 relative z-10 flex items-center gap-2"><i class="ph-duotone ph-identification-card text-[#C27803]"></i> Identity</h3>
                                <div class="flex items-center gap-6 mb-10 relative z-10">
                                    <div class="relative group/pic cursor-pointer" onclick="document.getElementById('hidden-profile-upload').click()">
                                        <img src="${ADMIN_USER.pic}" class="w-24 h-24 rounded-full border-4 border-white shadow-md object-cover bg-[#FAF8F5] group-hover/pic:border-[#C27803] transition-colors" id="settings-pic">
                                        <div class="absolute inset-0 bg-[#1A1614]/50 rounded-full flex items-center justify-center opacity-0 group-hover/pic:opacity-100 transition-opacity"><i class="ph-bold ph-camera text-white text-xl"></i></div>
                                    </div>
                                    <div><p class="text-[14px] text-[#1A1614] font-medium mb-1">Display Portrait</p><p class="text-[11px] text-[#A39A8E]">PNG or JPG under 2MB.</p></div>
                                </div>
                                <div class="space-y-6 relative z-10">
                                    <div>
                                        <label class="text-[10px] text-[#A39A8E] font-mono uppercase tracking-widest">Full Name</label>
                                        <input type="text" id="admin-edit-name" value="${ADMIN_USER.name}" class="w-full minimal-input text-[14px] text-[#1A1614] font-medium hover:border-[#C27803]/50">
                                    </div>
                                    <div>
                                        <div class="flex justify-between items-center"><label class="text-[10px] text-[#A39A8E] font-mono uppercase tracking-widest">Email Address</label><i class="ph-fill ph-lock-key text-[#C27803]"></i></div>
                                        <input type="email" id="admin-edit-email" value="${ADMIN_USER.email}" class="w-full minimal-input text-[14px] text-[#A39A8E] font-medium cursor-not-allowed bg-transparent" readonly disabled>
                                        <p class="text-[10px] text-[#C27803] mt-2 font-mono">Email is strictly managed by platform admins.</p>
                                    </div>
                                    <button onclick="saveAdminProfile()" class="px-6 py-2.5 bg-[#1A1614] text-white rounded-full text-[13px] font-medium hover:bg-[#C27803] transition-colors mt-6 shadow-md shadow-black/10">Save Changes</button>
                                </div>
                            </div>
                            <!-- Right: Security -->
                            <div class="flex-1 p-10 bg-[#FAF8F5]/50 relative overflow-hidden">
                                <h3 class="font-serif text-2xl text-[#1A1614] mb-8 relative z-10 flex items-center gap-2"><i class="ph-duotone ph-shield-check text-[#C27803]"></i> Security</h3>
                                <div class="space-y-8 relative z-10">
                                    <div>
                                        <label class="text-[10px] text-[#A39A8E] font-mono uppercase tracking-widest">Current Passkey</label>
                                        <div class="relative">
                                            <input type="password" id="admin-curr-pass" placeholder="••••••••" class="w-full minimal-input text-[14px] text-[#1A1614] font-mono pr-10 hover:border-[#C27803]/50">
                                            <button onclick="togglePasswordVisibility('admin-curr-pass')" class="absolute right-0 top-1/2 -translate-y-1/2 text-[#A39A8E] hover:text-[#C27803] transition-colors"><i id="admin-curr-pass-icon" class="ph-regular ph-eye text-lg"></i></button>
                                        </div>
                                    </div>
                                    <div class="grid grid-cols-2 gap-4">
                                        <div>
                                            <label class="text-[10px] text-[#A39A8E] font-mono uppercase tracking-widest">New Passkey</label>
                                            <div class="relative">
                                                <input type="password" id="admin-new-pass" placeholder="••••••••" class="w-full minimal-input text-[14px] text-[#1A1614] font-mono pr-10 hover:border-[#C27803]/50">
                                                <button onclick="togglePasswordVisibility('admin-new-pass')" class="absolute right-0 top-1/2 -translate-y-1/2 text-[#A39A8E] hover:text-[#C27803] transition-colors"><i id="admin-new-pass-icon" class="ph-regular ph-eye text-lg"></i></button>
                                            </div>
                                        </div>
                                        <div>
                                            <label class="text-[10px] text-[#A39A8E] font-mono uppercase tracking-widest">Confirm Passkey</label>
                                            <div class="relative">
                                                <input type="password" id="admin-conf-pass" placeholder="••••••••" class="w-full minimal-input text-[14px] text-[#1A1614] font-mono pr-10 hover:border-[#C27803]/50">
                                                <button onclick="togglePasswordVisibility('admin-conf-pass')" class="absolute right-0 top-1/2 -translate-y-1/2 text-[#A39A8E] hover:text-[#C27803] transition-colors"><i id="admin-conf-pass-icon" class="ph-regular ph-eye text-lg"></i></button>
                                            </div>
                                        </div>
                                    </div>
                                    <button onclick="saveAdminPassword()" class="px-6 py-2.5 bg-white border border-[#E8E3DB] text-[#1A1614] rounded-full text-[13px] font-medium hover:bg-[#1A1614] hover:border-[#1A1614] hover:text-white transition-colors mt-6 shadow-sm">Update Passkey</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <input type="file" id="hidden-profile-upload" class="hidden" accept="image/*" onchange="updateProfilePicPreview(this)">
            `; 
        }

        function renderSiteContent() {
            return `
                ${renderHeader('Site Experience', 'Direct the visual narrative of the storefront.')}
                <div class="max-w-7xl mx-auto fade-in">
                    <div class="bg-white rounded-3xl border border-[#E8E3DB] shadow-[0_4px_24px_-8px_rgba(0,0,0,0.02)] overflow-hidden flex flex-col xl:flex-row">
                        <!-- Controls -->
                        <div class="w-full xl:w-[35%] p-8 border-b xl:border-b-0 xl:border-r border-[#E8E3DB] bg-[#FAF8F5]/30">
                            <h3 class="font-serif text-2xl text-[#1A1614] mb-8 flex items-center gap-2"><i class="ph-duotone ph-image text-[#C27803]"></i> Hero Banner</h3>
                            <div class="space-y-6">
                                <div onclick="triggerFileDrop()" class="aspect-video bg-white rounded-2xl border border-dashed border-[#E8E3DB] flex flex-col items-center justify-center text-[#A39A8E] cursor-pointer hover:border-[#C27803] hover:bg-[#FAF8F5] transition-all group shadow-sm">
                                    <i class="ph-regular ph-upload-simple text-3xl mb-2 group-hover:text-[#C27803] transition-colors"></i>
                                    <span class="text-[10px] font-mono uppercase tracking-widest group-hover:text-[#C27803] transition-colors">Upload New Image</span>
                                </div>
                                <div>
                                    <label class="block text-[10px] font-mono text-[#A39A8E] uppercase tracking-widest mb-2">Headline</label>
                                    <textarea id="site-hero-headline" oninput="document.getElementById('preview-headline').textContent = this.value" class="w-full minimal-input text-[15px] font-serif font-medium text-[#1A1614] h-20 resize-none leading-relaxed hover:border-[#C27803]/50 focus:border-[#C27803]">${heroHeadlineText}</textarea>
                                </div>
                                <div>
                                    <label class="block text-[10px] font-mono text-[#A39A8E] uppercase tracking-widest mb-2">Subtext</label>
                                    <textarea id="site-hero-subtext" oninput="document.getElementById('preview-subtext').textContent = this.value" class="w-full minimal-input text-[13px] text-[#6B635A] h-20 resize-none leading-relaxed hover:border-[#C27803]/50 focus:border-[#C27803]">${heroSubtext}</textarea>
                                </div>
                                <div class="hidden"><input id="site-hero-image-url" type="text" value="${heroImageUrl}"></div>
                                <div class="pt-4"><button onclick="publishSiteUpdates()" class="w-full py-3 bg-[#1A1614] text-white rounded-full text-[13px] font-medium hover:bg-[#C27803] transition-colors shadow-lg shadow-black/10">Publish to Storefront</button></div>
                            </div>
                        </div>
                        <!-- Premium Preview (Based on Provided Hero Code) -->
                        <div class="w-full xl:w-[65%] bg-[#E8E3DB]/30 p-8 flex items-center justify-center">
                            <div class="w-full max-w-4xl bg-white rounded-2xl shadow-[0_20px_40px_-10px_rgba(0,0,0,0.1)] overflow-hidden border border-[#E8E3DB]">
                                <!-- Browser Top Bar -->
                                <div class="bg-[#FAF8F5] px-4 py-3 border-b border-[#E8E3DB] flex items-center">
                                    <div class="browser-dots flex"><span></span><span></span><span></span></div>
                                    <div class="mx-auto bg-white border border-[#E8E3DB] rounded text-[9px] font-mono text-[#A39A8E] px-4 py-1">origins-heritage.bd</div>
                                </div>
                                <!-- Mockup Content (Actual Live Code Format) -->
                                <div class="relative py-12 px-8 overflow-hidden bg-[#f8f5f1] h-[500px] overflow-y-auto">
                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
                                        <!-- Left Content -->
                                        <div class="order-2 md:order-1 relative z-10">
                                            <div class="mb-4">
                                                <span class="inline-block px-3 py-1 bg-[#eae5db] text-[#0f2e26] text-[8px] font-bold uppercase tracking-widest rounded-full border border-[#d4a373]/30">
                                                    <span class="w-1.5 h-1.5 rounded-full bg-red-600 inline-block mr-1.5 animate-pulse"></span>Bangladesh's GI Heritage
                                                </span>
                                            </div>
                                            <h1 id="preview-headline" class="text-3xl lg:text-4xl font-bold mb-4 leading-[1.1] text-[#0f2e26] whitespace-pre-line font-serif">${heroHeadlineText}</h1>
                                            <p id="preview-subtext" class="text-[12px] text-slate-700 mb-6 max-w-sm leading-relaxed">${heroSubtext}</p>
                                            <div class="flex flex-wrap gap-3">
                                                <button class="px-5 py-2.5 bg-[#0f2e26] text-[#f8f5f1] text-[11px] font-medium rounded-full shadow-lg shadow-emerald-900/20 flex items-center gap-2 group">
                                                    Explore Collection <i class="ph-bold ph-arrow-right group-hover:translate-x-1 transition-transform"></i>
                                                </button>
                                                <button class="px-5 py-2.5 bg-transparent border border-[#0f2e26] text-[#0f2e26] text-[11px] font-bold rounded-full flex items-center gap-2 group hover:bg-[#0f2e26] hover:text-[#f8f5f1] transition-colors">
                                                    <span class="w-4 h-4 rounded-full bg-[#0f2e26] text-[#f8f5f1] flex items-center justify-center group-hover:bg-[#f8f5f1] group-hover:text-[#0f2e26] transition-colors"><i class="ph-fill ph-hammer text-[8px]"></i></span> Become an Artisan
                                                </button>
                                            </div>
                                        </div>
                                        <!-- Right Image -->
                                        <div class="order-1 md:order-2 relative">
                                            <div class="aspect-[4/5] relative rounded-[2rem] overflow-hidden shadow-2xl border-[3px] border-[#fffaf5]">
                                                <img id="site-hero-preview" src="${heroImageUrl}" class="absolute inset-0 w-full h-full object-cover">
                                                <div class="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent pointer-events-none"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>`;
        }


        async function withRefresh(message, fn, fallbackMessage = 'Saved.') {
            try {
                await fn();
                await refreshAdminData();
                showToast(message || fallbackMessage, 'success');
            } catch (e) {
                showToast(e.message || 'Action failed', 'error');
            }
        }

        window.updateSellerStatus = (id, newStatus) => withRefresh(`Seller status updated to ${newStatus}.`, () => adminApi(`/api/admin/sellers/${id}/status`, { method: 'POST', body: JSON.stringify({ status: newStatus }) }));
        window.updateProductStatus = (id, status) => withRefresh('Inventory status synced.', () => adminApi(`/api/admin/products/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) }));
        window.updateOrderStatus = (id, status) => withRefresh('Logistics status updated.', () => adminApi(`/api/admin/orders/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) }));
        window.approveVerificationDirect = (id) => withRefresh('Identity verified and approved.', () => adminApi(`/api/admin/verification/${id}/action`, { method: 'POST', body: JSON.stringify({ action: 'approve' }) }), 'Identity verified and approved.');
        window.approveQCDirect = (id) => withRefresh('Product passed QC.', () => adminApi(`/api/admin/qc/${id}/action`, { method: 'POST', body: JSON.stringify({ action: 'approve' }) }));
        window.approveGIDirect = (id) => withRefresh('Geographical indication certified.', () => adminApi(`/api/admin/gi/${id}/action`, { method: 'POST', body: JSON.stringify({ action: 'approve' }) }));
        window.approveFlashSale = (id) => withRefresh("Lot approved for Artisan's Hour.", () => adminApi(`/api/admin/gi/${id}/action`, { method: 'POST', body: JSON.stringify({ action: 'approve' }) }));
        window.updateFlashSchedule = async () => {
            const start_date = document.getElementById('flash-start-date').value; const start = document.getElementById('flash-start-time').value;
            const end_date = document.getElementById('flash-end-date').value; const end = document.getElementById('flash-end-time').value;
            if(!start_date || !start || !end_date || !end) return showToast('Please complete schedule bounds.', 'error');
            await withRefresh('Drop schedule synchronized.', () => adminApi('/api/admin/artisan-hour/schedule', { method: 'POST', body: JSON.stringify({ start_date, start, end_date, end }) }));
        };
        window.toggleFlashSaleStatus = async () => {
            const nextLive = flashSaleStatus !== 'Active';
            await withRefresh(`Artisan's Hour is now ${nextLive ? 'LIVE' : 'OFFLINE'}.`, () => adminApi('/api/admin/artisan-hour/status', { method: 'POST', body: JSON.stringify({ live: nextLive }) }));
        };
        window.selectTodaysArtisan = (id) => withRefresh('Featured artisan updated.', () => adminApi('/api/admin/featured-artisan', { method: 'POST', body: JSON.stringify({ seller_id: id }) }));
        window.publishSiteUpdates = async () => {
            heroHeadlineText = (document.getElementById('site-hero-headline') || {}).value || heroHeadlineText;
            heroSubtext = (document.getElementById('site-hero-subtext') || {}).value || heroSubtext;
            heroImageUrl = (document.getElementById('site-hero-image-url') || {}).value || heroImageUrl;
            await withRefresh('Frontend aesthetics published!', () => adminApi('/api/admin/site-experience', { method: 'POST', body: JSON.stringify({ headline: heroHeadlineText, subtext: heroSubtext, image_url: heroImageUrl }) }));
        };
        window.viewJournal = async (id) => {
            const post = MOCK_JOURNAL.find(p => p.id === id);
            if (!post) return;
            const newTitle = prompt('Editing Journal Title:', post.title);
            if (newTitle !== null && newTitle.trim() !== '') {
                await withRefresh('Editorial saved.', () => adminApi(`/api/admin/journal/${id}`, { method: 'PUT', body: JSON.stringify({ title: newTitle.trim(), body_html: '<p>Updated from admin panel.</p>', publish: post.status === 'Published' }) }));
            }
        };
        window.createBlankDraft = async () => {
            const title = prompt('Enter Draft Title:');
            if (title !== null) await withRefresh('Draft created successfully.', () => adminApi('/api/admin/journal', { method: 'POST', body: JSON.stringify({ title: title || 'Untitled Draft' }) }));
        };
        window.addNewJournal = async () => {
            const title = prompt('Enter New Article Title:');
            if (title && title.trim() !== '') await withRefresh('Draft created successfully.', () => adminApi('/api/admin/journal', { method: 'POST', body: JSON.stringify({ title: title.trim() }) }));
            else if (title !== null) showToast('Title cannot be empty.', 'error');
        };
        window.inviteTeamMember = async () => {
            const name = prompt("Enter new member's name:");
            if (name && name.trim() !== '') await withRefresh('Team member invited.', () => adminApi('/api/admin/team', { method: 'POST', body: JSON.stringify({ name: name.trim() }) }));
        };
        window.deleteTeamMember = (id) => withRefresh('Team member removed.', () => adminApi(`/api/admin/team/${id}`, { method: 'DELETE' }));
        window.toggleUserBan = (id) => withRefresh('User access modified.', () => adminApi(`/api/admin/users/${id}/toggle`, { method: 'POST' }));
        window.resolveDispute = (id, act) => withRefresh(`Case #${id} ${act}.`, () => adminApi(`/api/admin/disputes/${id}/resolve`, { method: 'POST', body: JSON.stringify({ action: act }) }));
        window.sendChatMessage = async () => {
            const inp = document.getElementById('chat-input-field'); const text = inp.value.trim();
            const thread = (window.__ADMIN_DASHBOARD__.messages || [])[activeChatId] || (window.__ADMIN_DASHBOARD__.messages || [])[0];
            if (text && thread) {
                await withRefresh('Message delivered.', () => adminApi('/api/admin/messages', { method: 'POST', body: JSON.stringify({ seller_id: thread.id || thread.seller_id, subject: thread.subject || `Message for ${thread.seller}`, body: text }) }));
                inp.value = '';
            }
        };
        window.saveAdminProfile = async () => {
            const newName = document.getElementById('admin-edit-name').value.trim();
            if(!newName) return showToast('Name field cannot be empty.', 'error');
            await withRefresh('Identity updated.', () => adminApi('/api/admin/profile', { method: 'POST', body: JSON.stringify({ name: newName }) }));
        };
        window.saveAdminPassword = async () => {
            const curr = document.getElementById('admin-curr-pass').value; const newP = document.getElementById('admin-new-pass').value; const confP = document.getElementById('admin-conf-pass').value;
            if(!curr || !newP || !confP) return showToast('Fill all fields.', 'error');
            if(newP.length < 6) return showToast('Min 6 characters required.', 'error');
            if(newP !== confP) return showToast('Passkey mismatch.', 'error');
            await withRefresh('Credentials rotated successfully.', () => adminApi('/api/admin/profile/password', { method: 'POST', body: JSON.stringify({ current_password: curr, new_password: newP }) }));
            document.getElementById('admin-curr-pass').value = ''; document.getElementById('admin-new-pass').value = ''; document.getElementById('admin-conf-pass').value = '';
        };
        window.updateProfilePicPreview = async (input) => {
            if(input.files && input.files[0]) {
                const fd = new FormData(); fd.append('avatar', input.files[0]);
                try {
                    const resp = await adminApi('/api/admin/profile/avatar', { method: 'POST', body: fd });
                    ADMIN_USER.pic = resp.url || ADMIN_USER.pic;
                    document.getElementById('sidebar-admin-pic').src = ADMIN_USER.pic;
                    renderMainContent();
                    showToast('Portrait updated.', 'success');
                    await refreshAdminData(false);
                } catch (e) {
                    showToast(e.message || 'Upload failed', 'error');
                }
            }
        };
        async function refreshLogsOnly() {
            try {
                const r = await adminApi('/api/admin/logs');
                window.__ADMIN_DASHBOARD__.logs = r.logs || [];
            } catch (e) { console.error(e); }
        }
        window.addEventListener('error', (e) => { console.error('Admin dashboard runtime error:', e.error || e.message); });

        // Init
        document.addEventListener('DOMContentLoaded', async () => {
            renderSidebar();
            renderMainContent();
            await refreshAdminData(false);
            renderSidebar();
            renderMainContent();
            setInterval(() => refreshAdminData(false), 30000);
        });
    
console.log('loaded script OK');
if (global._domcb) { Promise.resolve(global._domcb()).then(()=>console.log('dom ok')).catch(e=>{console.error('dom fail',e); process.exit(1);}); }
