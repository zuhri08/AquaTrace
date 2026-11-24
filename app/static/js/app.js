(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("staff-navigation");
    const menuButton = document.querySelector(".menu-toggle");
    const scrim = document.querySelector(".sidebar-scrim");
    const closeNavigation = () => {
      if (!sidebar || !menuButton || !scrim) return;
      sidebar.classList.remove("is-open");
      scrim.hidden = true;
      menuButton.setAttribute("aria-expanded", "false");
    };
    if (sidebar && menuButton && scrim) {
      menuButton.addEventListener("click", () => {
        const isOpen = sidebar.classList.toggle("is-open");
        scrim.hidden = !isOpen;
        menuButton.setAttribute("aria-expanded", String(isOpen));
      });
      scrim.addEventListener("click", closeNavigation);
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeNavigation();
      });
    }

    const dialog = document.getElementById("confirm-dialog");
    if (dialog && typeof dialog.showModal === "function") {
      let pendingForm = null;
      document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
          if (form.dataset.confirmed === "true") {
            form.dataset.confirmed = "false";
            return;
          }
          event.preventDefault();
          pendingForm = form;
          const message = document.getElementById("confirm-message");
          if (message) message.textContent = form.dataset.confirm;
          dialog.showModal();
        });
      });
      dialog.addEventListener("close", () => {
        if (dialog.returnValue === "confirm" && pendingForm) {
          pendingForm.dataset.confirmed = "true";
          pendingForm.requestSubmit();
        }
        pendingForm = null;
      });
    }
  });
})();
