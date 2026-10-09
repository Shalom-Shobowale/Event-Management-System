// EventFlow - Core Application JavaScript

// ========================================
// Dark Mode
// ========================================

// function initializeDarkMode() {
//   try {
//     const saved = localStorage.getItem("darkMode");

//     const prefersDark = window.matchMedia(
//       "(prefers-color-scheme: dark)",
//     ).matches;

//     if (saved === "true" || (saved === null && prefersDark)) {
//       document.documentElement.classList.add("dark");
//     } else {
//       document.documentElement.classList.remove("dark");
//     }
//   } catch (error) {
//     console.error("Dark mode initialization failed:", error);
//   }
// }

function initializeDarkMode() {
  try {
    const saved = localStorage.getItem("darkMode");

    // Default to DARK if user hasn't chosen yet.
    // Only switch to light if the user has explicitly chosen light.
    if (saved === "false") {
      document.documentElement.classList.remove("dark");
    } else {
      // Default (no preference) OR explicit dark → dark mode
      document.documentElement.classList.add("dark");
    }
  } catch (error) {
    console.error("Dark mode initialization failed:", error);
    // On failure, default to dark
    document.documentElement.classList.add("dark");
  }
}

function toggleDarkMode() {
  const html = document.documentElement;

  const isDark = html.classList.toggle("dark");

  try {
    localStorage.setItem("darkMode", isDark ? "true" : "false");
  } catch (error) {
    console.error("Could not save dark mode preference:", error);
  }
}

// ========================================
// Sidebar
// ========================================

function openSidebar() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebar-overlay");

  if (!sidebar || !overlay) {
    console.error("Sidebar elements not found");
    return;
  }

  sidebar.classList.remove("-translate-x-full");
  overlay.classList.remove("hidden");
}

function closeSidebar() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebar-overlay");

  if (!sidebar || !overlay) {
    console.error("Sidebar elements not found");
    return;
  }

  sidebar.classList.add("-translate-x-full");
  overlay.classList.add("hidden");
}

function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");

  if (!sidebar) {
    console.error("Sidebar element not found");
    return;
  }

  if (sidebar.classList.contains("-translate-x-full")) {
    openSidebar();
  } else {
    closeSidebar();
  }
}

// ========================================
// Toast Notifications
// ========================================

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");

  if (!container) {
    return;
  }

  const icons = {
    success:
      '<svg class="w-4 h-4 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="#c6f24e" stroke-width="2">' +
      '<circle cx="12" cy="12" r="9"/>' +
      '<path d="M8 12l3 3 5-6"/>' +
      "</svg>",

    error:
      '<svg class="w-4 h-4 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="#ff4800" stroke-width="2">' +
      '<circle cx="12" cy="12" r="9"/>' +
      '<path d="M12 8v4M12 16h.01"/>' +
      "</svg>",

    warning:
      '<svg class="w-4 h-4 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="#ff7a3d" stroke-width="2">' +
      '<circle cx="12" cy="12" r="9"/>' +
      '<path d="M12 8v4M12 16h.01"/>' +
      "</svg>",

    info:
      '<svg class="w-4 h-4 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="#9b84ff" stroke-width="2">' +
      '<circle cx="12" cy="12" r="9"/>' +
      '<path d="M12 16v-4M12 8h.01"/>' +
      "</svg>",
  };

  const toast = document.createElement("div");

  toast.className = "ef-toast";
  toast.dataset.type = type || "info";

  toast.innerHTML =
    (icons[type] || icons.info) + "<span>" + message + "</span>";

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = "opacity .3s, transform .3s";

    toast.style.opacity = "0";
    toast.style.transform = "translateX(12px)";

    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 4200);
}

// ========================================
// Page Initialization
// ========================================

function initializeApp() {
  // ------------------------------------
  // Dark mode — skip pages that hard-lock a theme
  // ------------------------------------

  const isLockedTheme = document.documentElement.hasAttribute("data-theme");

  if (!isLockedTheme) {
    initializeDarkMode();

    // Theme toggles — desktop + mobile
    ["dark-mode-toggle", "dark-mode-toggle-mobile"].forEach(function (id) {
      const btn = document.getElementById(id);
      if (btn) {
        btn.addEventListener("click", toggleDarkMode);
      }
    });
  }

  // ------------------------------------
  // Sidebar
  // ------------------------------------

  const sidebarButton = document.getElementById("sidebar-toggle");

  if (sidebarButton) {
    sidebarButton.addEventListener("click", toggleSidebar);
  }

  // ------------------------------------
  // Sidebar overlay
  // ------------------------------------

  const sidebarOverlay = document.getElementById("sidebar-overlay");

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener("click", closeSidebar);
  }

  // ------------------------------------
  // Django messages
  // ------------------------------------

  const djangoMessages = document.querySelectorAll(
    "#django-messages .django-message",
  );

  djangoMessages.forEach((messageElement) => {
    const message = messageElement.dataset.message;

    const type = messageElement.dataset.type || "info";

    showToast(message, type);
  });
}

// ========================================
// Start Application
// ========================================

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeApp);
} else {
  initializeApp();
}

/* ==========================================================================
   Report modal — opens from any [data-target-type][data-target-id] trigger.

   IMPORTANT: this IIFE assumes the report modal HTML is in the DOM before
   app.js runs. base_dashboard.html must include _report_modal.html ABOVE
   <script src="app.js">. Do not reorder that include.
   ========================================================================== */
(function () {
  const modal = document.getElementById("report-modal");
  if (!modal) return;

  // ---- Element lookups ----
  const form = document.getElementById("report-form");
  const successBox = document.getElementById("report-success");
  const errorBox = document.getElementById("report-error");
  const categoryBox = document.getElementById("report-categories");
  const reasonInput = document.getElementById("report-reason");
  const charCount = document.getElementById("report-char-count");
  const submitBtn = document.getElementById("report-submit");
  const submitText = document.getElementById("report-submit-text");
  const submitSpinner = document.getElementById("report-submit-spinner");
  const targetLabelDisplay = document.getElementById("report-target-label");
  const targetTypeInput = document.getElementById("report-target-type");
  const targetIdInput = document.getElementById("report-target-id");
  const targetLabelInput = document.getElementById("report-target-label-input");

  // Categories valid per target type — mirrors reports/forms.py
  const CATEGORIES = {
    vendor: [
      ["fake_vendor", "Fake vendor"],
      ["scam", "Scam"],
      ["harassment", "Harassment"],
      ["inappropriate", "Inappropriate content"],
      ["other", "Something else"],
    ],
    event: [
      ["fake_event", "Fake event"],
      ["scam", "Scam"],
      ["harassment", "Harassment"],
      ["inappropriate", "Inappropriate content"],
      ["other", "Something else"],
    ],
    review: [
      ["harassment", "Harassment"],
      ["inappropriate", "Inappropriate content"],
      ["other", "Something else"],
    ],
    host: [
      ["harassment", "Harassment"],
      ["scam", "Scam"],
      ["inappropriate", "Inappropriate content"],
      ["other", "Something else"],
    ],
    message: [
      ["harassment", "Harassment"],
      ["scam", "Scam"],
      ["inappropriate", "Inappropriate content"],
      ["other", "Something else"],
    ],
    booking: [
      ["harassment", "Harassment"],
      ["scam", "Scam"],
      ["inappropriate", "Inappropriate content"],
      ["other", "Something else"],
    ],
  };

  // ---- Helpers ----

  function resetForm() {
    form.reset();
    errorBox.classList.add("hidden");
    errorBox.textContent = "";
    successBox.classList.add("hidden");
    form.classList.remove("hidden");
    charCount.textContent = "0";
    submitBtn.disabled = false;
    submitText.textContent = "Submit report";
    submitSpinner.classList.add("hidden");
  }

  function renderCategories(targetType) {
    categoryBox.innerHTML = "";
    const list = CATEGORIES[targetType] || [];
    list.forEach(([value, label]) => {
      const id = "report-cat-" + value;
      categoryBox.insertAdjacentHTML(
        "beforeend",
        `
        <label for="${id}"
               data-cat-label
               class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-white/5 hover:border-flame-600/40 hover:bg-flame-600/5 cursor-pointer transition-colors">
            <input type="radio"
                   id="${id}"
                   name="category"
                   value="${value}"
                   required
                   class="sr-only">
            <span data-cat-indicator
                  class="w-4 h-4 rounded-full border-2 border-ink-600 transition-colors flex-shrink-0"></span>
            <span class="text-sm text-ink-200">${label}</span>
        </label>
        `,
      );
    });
    syncCategorySelection();
  }

  function syncCategorySelection() {
    // Reset visual state for all rows
    categoryBox.querySelectorAll("[data-cat-label]").forEach((lbl) => {
      lbl.classList.remove("border-flame-600/60", "bg-flame-600/10");
    });
    categoryBox.querySelectorAll("[data-cat-indicator]").forEach((ind) => {
      ind.classList.remove("border-flame-500", "bg-flame-500/30");
      ind.classList.add("border-ink-600");
    });

    // Apply visual state for the checked row
    const checked = categoryBox.querySelector('input[name="category"]:checked');
    if (checked) {
      const label = checked.closest("[data-cat-label]");
      const indicator = label?.querySelector("[data-cat-indicator]");
      if (label) {
        label.classList.add("border-flame-600/60", "bg-flame-600/10");
      }
      if (indicator) {
        indicator.classList.remove("border-ink-600");
        indicator.classList.add("border-flame-500", "bg-flame-500/30");
      }
    }
  }

  // Wire the change listener AFTER syncCategorySelection is defined.
  categoryBox.addEventListener("change", function (e) {
    if (e.target.matches('input[name="category"]')) {
      syncCategorySelection();
    }
  });

  // ---- Modal open / close ----

  let lastFocusedElement = null;

  function open(trigger) {
    lastFocusedElement = trigger || document.activeElement;
    resetForm();

    const targetType = trigger.dataset.targetType;
    const targetId = trigger.dataset.targetId;
    const targetLabel = trigger.dataset.targetLabel || "this item";

    targetTypeInput.value = targetType;
    targetIdInput.value = targetId;
    targetLabelInput.value = targetLabel;
    targetLabelDisplay.textContent = targetLabel;

    renderCategories(targetType);

    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";

    setTimeout(() => {
      modal.focus();
      if (document.activeElement !== modal && reasonInput) {
        reasonInput.focus();
      }
    }, 50);
  }

  function close() {
    // Return focus before hiding — otherwise the browser warns about
    // aria-hidden on a focused element.
    if (modal.contains(document.activeElement)) {
      if (lastFocusedElement && document.body.contains(lastFocusedElement)) {
        lastFocusedElement.focus();
      } else if (document.activeElement && document.activeElement.blur) {
        document.activeElement.blur();
      }
    }
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  // ---- Event delegation: any [data-target-type] click opens the modal ----

  document.addEventListener("click", function (e) {
    const trigger = e.target.closest("[data-target-type][data-target-id]");
    if (trigger && !trigger.closest("#report-modal")) {
      e.preventDefault();
      open(trigger);
      return;
    }
    if (e.target.closest("[data-report-close]")) {
      e.preventDefault();
      close();
    }
  });

  // ---- ESC to close ----

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !modal.classList.contains("hidden")) {
      close();
    }
  });

  // ---- Char counter ----

  reasonInput.addEventListener("input", function () {
    charCount.textContent = reasonInput.value.length;
  });

  // ---- Submit via fetch ----

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    errorBox.classList.add("hidden");

    // Client-side min-length guard for a snappier UX
    const reasonValue = reasonInput.value.trim();
    if (reasonValue.length < 30) {
      errorBox.textContent = "Please write at least 30 characters.";
      errorBox.classList.remove("hidden");
      return;
    }

    // Require a category (not auto-selected anymore)
    if (!categoryBox.querySelector('input[name="category"]:checked')) {
      errorBox.textContent = "Please choose a category.";
      errorBox.classList.remove("hidden");
      return;
    }

    submitBtn.disabled = true;
    submitText.textContent = "Submitting…";
    submitSpinner.classList.remove("hidden");

    try {
      const res = await fetch(form.action, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
        body: new FormData(form),
        credentials: "same-origin",
      });
      const data = await res.json();

      if (data.ok) {
        form.classList.add("hidden");
        successBox.classList.remove("hidden");
      } else {
        errorBox.textContent = data.error || "Something went wrong.";
        errorBox.classList.remove("hidden");
        submitBtn.disabled = false;
        submitText.textContent = "Submit report";
        submitSpinner.classList.add("hidden");
      }
    } catch (err) {
      errorBox.textContent = "Network error. Please try again.";
      errorBox.classList.remove("hidden");
      submitBtn.disabled = false;
      submitText.textContent = "Submit report";
      submitSpinner.classList.add("hidden");
    }
  });
})();

/* ==========================================================================
   Password visibility toggle
   --------------------------------------------------------------------------
   Any <button class="password-toggle" data-target="inputId"> will toggle
   the visibility of the input with that ID.

   Markup (works everywhere, no per-page JS needed):
     <div class="relative">
       <input id="id_password" type="password" class="ef-input pr-12" />
       <button type="button"
               class="password-toggle absolute top-1/2 right-3 -translate-y-1/2 ..."
               data-target="id_password"
               aria-label="Show password">
         <svg class="w-4 h-4 eye-open" ...>...</svg>
         <svg class="w-4 h-4 eye-closed hidden" ...>...</svg>
       </button>
     </div>
   ========================================================================== */
(function () {
  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".password-toggle");
    if (!btn) return;

    e.preventDefault();

    const targetId = btn.dataset.target;
    if (!targetId) return;

    const input = document.getElementById(targetId);
    if (!input || input.tagName !== "INPUT") return;

    const isPassword = input.type === "password";
    input.type = isPassword ? "text" : "password";

    // Toggle eye icons
    const openEye = btn.querySelector(".eye-open");
    const closedEye = btn.querySelector(".eye-closed");
    if (openEye) openEye.classList.toggle("hidden", isPassword);
    if (closedEye) closedEye.classList.toggle("hidden", !isPassword);

    btn.setAttribute(
      "aria-label",
      isPassword ? "Hide password" : "Show password",
    );

    // Keep focus on the input so typing continues
    input.focus();
  });
})();
