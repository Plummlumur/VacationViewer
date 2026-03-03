/**
 * VacationViewer – Auto-rotation, pause/play, and accessibility logic.
 *
 * Reads configuration from body data-config attribute.
 * Rotates between month pages, announces changes via aria-live,
 * and respects prefers-reduced-motion.
 */

(function () {
    "use strict";

    // --- Configuration ---
    var body = document.body;
    var config = { rotation_seconds: 10, refresh_minutes: 5 };

    try {
        var raw = body.getAttribute("data-config");
        if (raw) {
            config = JSON.parse(raw);
        }
    } catch (e) {
        console.warn("Failed to parse config:", e);
    }

    var rotationMs = (config.rotation_seconds || 10) * 1000;
    var refreshMs = (config.refresh_minutes || 5) * 60 * 1000;

    // --- Reduced Motion Check ---
    var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // --- DOM References ---
    var pages = document.querySelectorAll(".month-page");
    var announceEl = document.getElementById("rotation-announce");
    var toggleBtn = document.getElementById("rotation-toggle");
    var prevBtn = document.getElementById("rotation-prev");
    var nextBtn = document.getElementById("rotation-next");
    var selectEl = document.getElementById("rotation-month-select");
    var currentIndex = 0;
    var paused = false;
    var rotationTimer = null;

    // --- Page Display ---
    function showPage(index) {
        pages.forEach(function (page, i) {
            if (i === index) {
                page.classList.add("month-page--active");
            } else {
                page.classList.remove("month-page--active");
            }
        });

        // Announce current month to screen readers
        if (announceEl && pages[index]) {
            var label = pages[index].getAttribute("data-month-label") || "";
            var pageNum = index + 1;
            announceEl.textContent = label + " (" + pageNum + " von " + pages.length + ")";
        }

        // Keep dropdown select in sync
        if (selectEl) {
            selectEl.value = index.toString();
        }
    }

    function nextPage() {
        if (pages.length <= 1) return;
        currentIndex = (currentIndex + 1) % pages.length;
        showPage(currentIndex);
    }

    function prevPage() {
        if (pages.length <= 1) return;
        currentIndex = (currentIndex - 1 + pages.length) % pages.length;
        showPage(currentIndex);
    }

    function resetRotationTimer() {
        if (!paused && rotationTimer) {
            stopRotation();
            startRotation();
        }
    }

    // --- Rotation Control ---
    function startRotation() {
        if (rotationTimer) return;
        rotationTimer = setInterval(nextPage, rotationMs);
    }

    function stopRotation() {
        if (rotationTimer) {
            clearInterval(rotationTimer);
            rotationTimer = null;
        }
    }

    // --- Pause/Play Toggle (WCAG 2.2.2) ---
    if (toggleBtn) {
        toggleBtn.addEventListener("click", function () {
            paused = !paused;

            if (paused) {
                stopRotation();
                toggleBtn.setAttribute("aria-pressed", "true");
                toggleBtn.setAttribute("aria-label", "Automatische Rotation fortsetzen");
                toggleBtn.querySelector(".rotation-btn__icon").innerHTML = "&#x25B6;"; // ▶
            } else {
                startRotation();
                toggleBtn.setAttribute("aria-pressed", "false");
                toggleBtn.setAttribute("aria-label", "Automatische Rotation pausieren");
                toggleBtn.querySelector(".rotation-btn__icon").innerHTML = "&#x23F8;"; // ⏸
            }
        });

        // Keyboard support: Enter and Space already handled by <button>,
        // but ensure no default scroll on Space
        toggleBtn.addEventListener("keydown", function (e) {
            if (e.key === " ") {
                e.preventDefault();
            }
        });
    }

    if (selectEl) {
        selectEl.addEventListener("change", function (e) {
            var newIndex = parseInt(e.target.value, 10);
            if (!isNaN(newIndex) && newIndex >= 0 && newIndex < pages.length) {
                currentIndex = newIndex;
                showPage(currentIndex);
                resetRotationTimer();
            }
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener("click", function () {
            prevPage();
            resetRotationTimer();
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener("click", function () {
            nextPage();
            resetRotationTimer();
        });
    }

    // --- Start Rotation ---
    if (pages.length > 1) {
        if (prefersReducedMotion) {
            // Respect reduced motion: don't auto-rotate, user can navigate manually
            paused = true;
            if (toggleBtn) {
                toggleBtn.setAttribute("aria-pressed", "true");
                toggleBtn.setAttribute("aria-label", "Automatische Rotation fortsetzen");
                toggleBtn.querySelector(".rotation-btn__icon").innerHTML = "&#x25B6;";
            }
        } else {
            startRotation();
        }
    }

    // --- Auto-Refresh ---
    setTimeout(function () {
        location.reload();
    }, refreshMs);

    console.log(
        "VacationViewer: rotation=" + config.rotation_seconds + "s, " +
        "refresh=" + config.refresh_minutes + "min, " +
        "pages=" + pages.length + ", " +
        "reducedMotion=" + prefersReducedMotion
    );
})();
