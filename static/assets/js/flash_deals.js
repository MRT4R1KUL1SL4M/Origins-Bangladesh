// flash_deals.js
// Dedicated Flash Deals page renderer (curated demo items used on Home)

const flashSaleItems = [
  { name: "Nakshi Kantha Wall Art", cat: "Decor", price: 120, oldPrice: 180, img: "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&q=80&w=600", off: "33%" },
  { name: "Dhakai Jamdani Saree", cat: "Apparel", price: 450, oldPrice: 600, img: "https://images.unsplash.com/photo-1610189012700-3479a5e2d1d8?auto=format&fit=crop&q=80&w=600", off: "25%" },
  { name: "Rajshahi Silk Scarf", cat: "Accessory", price: 95, oldPrice: 140, img: "https://images.unsplash.com/photo-1583394838336-acd977730f90?auto=format&fit=crop&q=80&w=600", off: "32%" },
  { name: "Shatranji Table Runner", cat: "Home", price: 45, oldPrice: 60, img: "https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&q=80&w=600", off: "20%" },
  { name: "Terracotta Planter", cat: "Pottery", price: 28, oldPrice: 40, img: "https://images.unsplash.com/photo-1540206395-688085723adb?auto=format&fit=crop&q=80&w=600", off: "30%" },
  { name: "Jute Tote Bag", cat: "Fashion", price: 35, oldPrice: 50, img: "https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?auto=format&fit=crop&q=80&w=600", off: "30%" },
  { name: "Brass Puja Thali", cat: "Metal", price: 80, oldPrice: 110, img: "https://images.unsplash.com/photo-1606103920295-9a091573f160?auto=format&fit=crop&q=80&w=600", off: "27%" },
  { name: "Manipuri Shawl", cat: "Winter", price: 150, oldPrice: 200, img: "https://images.unsplash.com/photo-1542332213-31f87348057f?auto=format&fit=crop&q=80&w=600", off: "25%" },
  { name: "Bamboo Lamp Shade", cat: "Lighting", price: 55, oldPrice: 85, img: "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?auto=format&fit=crop&q=80&w=600", off: "35%" },
  { name: "Khadi Panjabi Fabric", cat: "Textile", price: 70, oldPrice: 90, img: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&q=80&w=600", off: "22%" }
];

function money(v){
  return "$" + Number(v).toFixed(0);
}

const grid = document.getElementById("flashDealsGrid");
if (grid){
  flashSaleItems.forEach((item, index) => {
    const card = document.createElement("div");
    card.className = "bg-pearl p-3 rounded-2xl border border-[#d4a373]/20 card-shadow group cursor-pointer relative reveal-up";
    card.style.transitionDelay = `${index * 40}ms`;
    card.innerHTML = `
      <div class="relative overflow-hidden rounded-xl aspect-[4/5] mb-3 img-pan-container">
        <img src="${item.img}" class="w-full h-full object-cover" alt="${item.name}">
        <span class="absolute top-2 left-2 bg-heritage-maroon text-cream text-[9px] font-bold px-2 py-1 rounded-full z-20">-${item.off}</span>

        <div class="absolute inset-0 bg-heritage-green/80 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-all duration-300 flex flex-col items-center justify-center gap-2 z-10">
          <a href="/shop" class="bg-heritage-gold text-cream px-4 py-2 rounded-full text-[9px] font-bold uppercase tracking-widest hover:bg-[#b58556] transition shadow-lg w-28 btn-animate transform translate-y-4 group-hover:translate-y-0 duration-500 delay-100 text-center">Add to Cart</a>
          <a href="/shop" class="bg-[#f8f5f1] text-heritage-green px-4 py-2 rounded-full text-[9px] font-bold uppercase tracking-widest hover:bg-[#eae5db] transition shadow-lg w-28 btn-animate transform translate-y-4 group-hover:translate-y-0 duration-500 delay-200 text-center">View Details</a>
        </div>
      </div>

      <div class="px-1 pb-1">
        <p class="text-[10px] text-heritage-maroon font-bold uppercase tracking-widest">${item.cat}</p>
        <h3 class="font-bold text-sm mt-1 line-clamp-2 text-heritage-green">${item.name}</h3>
        <div class="flex items-center gap-2 mt-2">
          <span class="text-heritage-green font-black">${money(item.price)}</span>
          <span class="text-xs text-gray-500 line-through">${money(item.oldPrice)}</span>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
}
