// home.js
// Home page is rendered server-side (DB-backed) to preserve design and enable real actions.
// This file wires up the Featured Artisan "View Collection" + "Watch Story" modal video player.

(function () {
  function qs(sel) { return document.querySelector(sel); }

  // Normalize common video URL formats into an embeddable URL.
  // Returns null if the URL is missing or not safe/embeddable.
  function normalizeVideoUrl(raw) {
    if (!raw) return null;
    const url = String(raw).trim();
    if (!url) return null;

    // Only allow http(s) embeds to avoid accidentally iframing local routes (which can show 404 pages).
    if (!(url.startsWith("http://") || url.startsWith("https://"))) return null;

    // YouTube watch URL → embed
    // Examples:
    // - https://www.youtube.com/watch?v=VIDEO
    // - https://youtu.be/VIDEO
    // Keep existing /embed/ links as-is.
    try {
      const u = new URL(url);
      const host = u.hostname.replace(/^www\./, "");
      if (host === "youtube.com" || host === "m.youtube.com") {
        if (u.pathname === "/watch" && u.searchParams.get("v")) {
          return `https://www.youtube.com/embed/${u.searchParams.get("v")}`;
        }
        if (u.pathname.startsWith("/embed/")) {
          return url;
        }
      }
      if (host === "youtu.be") {
        const id = u.pathname.replace(/^\//, "").split("/")[0];
        if (id) return `https://www.youtube.com/embed/${id}`;
      }
    } catch (_) {
      // If URL parsing fails, treat as missing.
      return null;
    }

    // Otherwise assume the URL is already embeddable (e.g., Vimeo player link or direct MP4).
    return url;
  }

  function openModal(modalEl) {
    if (!modalEl) return;
    modalEl.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeModal(modalEl, contentEl) {
    if (!modalEl) return;
    modalEl.classList.add("hidden");
    document.body.style.overflow = "";
    if (contentEl) contentEl.innerHTML = ""; // stop video playback
  }

  document.addEventListener("DOMContentLoaded", function () {
    const viewBtn = qs("#artisanViewCollectionBtn");
    const watchBtn = qs("#artisanWatchStoryBtn");

    const modal = qs("#artisanStoryModal");
    const backdrop = qs("#artisanStoryBackdrop");
    const closeBtn = qs("#artisanStoryCloseBtn");
    const content = qs("#artisanStoryContent");

    // View Collection → go to shop filtered by artisan
    if (viewBtn) {
      viewBtn.addEventListener("click", function () {
        const artisanId = (viewBtn.getAttribute("data-artisan-id") || "").trim();
        if (artisanId) {
          window.location.href = `/shop?artisan=${encodeURIComponent(artisanId)}`;
        } else {
          window.location.href = "/shop";
        }
      });
    }

    // Watch Story → open modal with video player (or no-story message)
    if (watchBtn) {
      watchBtn.addEventListener("click", function (e) {
        // Safety: prevent any default navigation in case the element is ever changed to an <a>.
        if (e && typeof e.preventDefault === "function") e.preventDefault();

        const rawUrl = (watchBtn.getAttribute("data-video-url") || "").trim();
        const videoUrl = normalizeVideoUrl(rawUrl);

        if (content) {
          if (videoUrl) {
            // Add autoplay for embeds (works for YouTube embeds, ignored otherwise)
            const src = videoUrl.includes("?")
              ? `${videoUrl}&autoplay=1`
              : `${videoUrl}?autoplay=1`;

            content.innerHTML = `
              <div class="relative w-full overflow-hidden rounded-2xl bg-black" style="padding-top:56.25%">
                <iframe
                  src="${src}"
                  class="absolute inset-0 w-full h-full"
                  title="Artisan Story"
                  frameborder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowfullscreen
                ></iframe>
              </div>
            `;
          } else {
            content.innerHTML = `
              <div class="text-center py-20">
                <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#d4a373] text-[#d4a373] text-[10px] font-bold uppercase tracking-widest mb-6">
                  No Story Found
                </div>
                <h4 class="text-2xl font-bold text-heritage-green mb-3">No story found for this artisan.</h4>
                <p class="text-sm text-slate-600 max-w-md mx-auto">
                  This artisan hasn’t added a video story yet. Please check back later.
                </p>
              </div>
            `;
          }
        }

        openModal(modal);
      });
    }

    // Close controls
    if (closeBtn) closeBtn.addEventListener("click", function () { closeModal(modal, content); });
    if (backdrop) backdrop.addEventListener("click", function () { closeModal(modal, content); });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modal && !modal.classList.contains("hidden")) {
        closeModal(modal, content);
      }
    });

    // ---------------------------
    // Heritage Soundscape (single global audio player)
    // ---------------------------
    const trackList = document.querySelector("#soundTrackList");
    const trackEls = trackList ? Array.from(trackList.querySelectorAll(".sound-track")) : [];
    const visualizer = qs("#soundVisualizer");
    const coverImg = qs("#soundCoverImg");
    const playBtn = qs("#soundPlayBtn");
    const playIcon = qs("#soundPlayIcon");
    const progressCircle = qs("#soundProgressCircle");

    const audio = new Audio();
    audio.preload = "metadata";

    const LS_TRACK = "ob_sound_track_id";
    const LS_TIME = "ob_sound_time";

    let activeTrackId = null;
    let isPlaying = false;
    let lastStoreAt = 0;

    function fmtTime(sec) {
      const s = Math.max(0, Math.floor(Number(sec) || 0));
      const m = Math.floor(s / 60);
      const r = s % 60;
      return `${m}:${String(r).padStart(2, "0")}`;
    }

    function setIcon(playing) {
      if (!playIcon) return;
      playIcon.classList.toggle("fa-play", !playing);
      playIcon.classList.toggle("fa-pause", !!playing);
      // keep sizing consistent
      playIcon.classList.add("text-2xl");
    }

    function setProgress(pct) {
      if (!progressCircle) return;
      const c = 289; // ~2*pi*46 from SVG
      const p = Math.min(1, Math.max(0, pct || 0));
      progressCircle.style.strokeDasharray = String(c);
      progressCircle.style.strokeDashoffset = String(c * (1 - p));
    }

    function setTrackActive(el, active) {
      if (!el) return;

      // Root container classes
      el.classList.toggle("bg-[#064e3b]", active);
      el.classList.toggle("border-[#065f46]", active);
      el.classList.toggle("hover:bg-[#065f46]", active);
      el.classList.toggle("border-white/10", !active);
      el.classList.toggle("hover:bg-white/5", !active);

      // Icon bubble
      const iconWrap = el.querySelector(".w-10.h-10");
      if (iconWrap) {
        iconWrap.classList.toggle("bg-[#10b981]", active);
        iconWrap.classList.toggle("text-white", active);

        iconWrap.classList.toggle("border", !active);
        iconWrap.classList.toggle("border-white/20", !active);
        iconWrap.classList.toggle("text-white/60", !active);
        iconWrap.classList.toggle("group-hover:text-[#10b981]", !active);
        iconWrap.classList.toggle("group-hover:border-[#10b981]", !active);
      }

      const titleEl = el.querySelector("h4");
      if (titleEl) {
        titleEl.classList.toggle("text-white", active);
        titleEl.classList.toggle("text-white/80", !active);
        titleEl.classList.toggle("group-hover:text-white", !active);
      }

      const subEl = el.querySelector("p");
      if (subEl) {
        subEl.classList.toggle("text-emerald-200", active);
        subEl.classList.toggle("text-stone-500", !active);
        subEl.classList.toggle("group-hover:text-stone-400", !active);
      }

      const durEl = el.querySelector(".sound-duration");
      if (durEl) {
        durEl.classList.toggle("text-emerald-200", active);
        durEl.classList.toggle("text-stone-500", !active);
      }
    }

    function getTrackElById(id) {
      return trackEls.find(t => String(t.getAttribute("data-track-id")) === String(id)) || null;
    }

    function setActiveTrack(el, opts) {
      const options = opts || {};
      if (!el) return;

      const trackId = String(el.getAttribute("data-track-id") || "");
      const audioUrl = String(el.getAttribute("data-audio-url") || "");
      const coverUrl = String(el.getAttribute("data-cover-url") || "");

      // UI: active styling
      trackEls.forEach(x => setTrackActive(x, x === el));

      // Visualizer cover
      if (coverImg && coverUrl) coverImg.src = coverUrl;

      // Audio source
      if (trackId !== activeTrackId) {
        activeTrackId = trackId;
        try { localStorage.setItem(LS_TRACK, trackId); } catch (_) {}

        if (audioUrl) {
          audio.pause();
          isPlaying = false;
          setIcon(false);
          setProgress(0);
          audio.src = audioUrl;
          audio.load();

          // Restore time if available
          const savedTime = Number((function () {
            try { return localStorage.getItem(LS_TIME) || "0"; } catch (_) { return "0"; }
          })());

          if (options.restoreTime && savedTime > 0) {
            audio.addEventListener("loadedmetadata", function once() {
              audio.removeEventListener("loadedmetadata", once);
              if (audio.duration && savedTime < audio.duration) {
                audio.currentTime = savedTime;
              }
            });
          }
        }
      }

      if (options.autoplay) {
        audio.play().then(() => {
          isPlaying = true;
          setIcon(true);
        }).catch(() => {
          isPlaying = false;
          setIcon(false);
        });
      }
    }

    function togglePlayPause() {
      if (!audio.src) {
        // no track selected, choose first
        if (trackEls[0]) setActiveTrack(trackEls[0], { autoplay: true, restoreTime: true });
        return;
      }
      if (audio.paused) {
        audio.play().then(() => {
          isPlaying = true;
          setIcon(true);
        }).catch(() => {
          isPlaying = false;
          setIcon(false);
        });
      } else {
        audio.pause();
        isPlaying = false;
        setIcon(false);
      }
    }

    // Attach interactions
    if (trackEls.length) {
      trackEls.forEach(el => {
        el.addEventListener("click", function () {
          const same = String(el.getAttribute("data-track-id")) === String(activeTrackId);
          if (same) {
            togglePlayPause();
          } else {
            setActiveTrack(el, { autoplay: true, restoreTime: false });
          }
        });

        el.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            el.click();
          }
        });
      });

      // Initialize active from localStorage or first track
      let savedId = null;
      try { savedId = localStorage.getItem(LS_TRACK); } catch (_) { savedId = null; }
      const savedEl = savedId ? getTrackElById(savedId) : null;
      setActiveTrack(savedEl || trackEls[0], { autoplay: false, restoreTime: true });
      setIcon(false);
      setProgress(0);
    }

    // Note: #soundPlayBtn sits inside #soundVisualizer. If we don't stop propagation,
    // clicking the button would trigger BOTH handlers (button + visualizer) and
    // instantly toggle twice (play->pause), which looks like "it doesn't play".
    if (playBtn) playBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      togglePlayPause();
    });
    if (visualizer) visualizer.addEventListener("click", function () { togglePlayPause(); });

    // Keep progress ring in sync + persist resume position
    audio.addEventListener("timeupdate", function () {
      if (!audio.duration) {
        setProgress(0);
        return;
      }
      setProgress(audio.currentTime / audio.duration);

      const now = Date.now();
      if (now - lastStoreAt > 1500) {
        lastStoreAt = now;
        try { localStorage.setItem(LS_TIME, String(Math.floor(audio.currentTime))); } catch (_) {}
      }
    });

    audio.addEventListener("ended", function () {
      isPlaying = false;
      setIcon(false);
      setProgress(0);
    });
  });
})();
