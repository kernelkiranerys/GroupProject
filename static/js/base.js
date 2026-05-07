(function () {
  var savedTheme = localStorage.getItem('theme');
  if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
  }
})();

document.addEventListener('DOMContentLoaded', function () {
  var notificationContainer = document.querySelector('.notification-container');

if (typeof window.showNotification !== 'function') {
  window.showNotification = function showNotification(options) {
    const notificationContainer = document.querySelector('.notification-container');
    if (!notificationContainer) {
      return;
    }

    const {
      type = 'info',
      title,
      body,
      duration = 5000,
    } = options;

    const iconMap = {
      info: 'ℹ️',
      success: '☀️',
      warning: '⚠️',
      error: '🔌',
    };

    const notificationEl = document.createElement('div');
    notificationEl.className = 'notification notification--' + type;
    notificationEl.setAttribute('role', type === 'error' || type === 'warning' ? 'alert' : 'status');

    notificationEl.innerHTML =
      '<button class="notification__close" aria-label="Close">&times;</button>' +
      '<div class="notification__header">' +
        '<span class="notification__icon" aria-hidden="true">' + iconMap[type] + '</span>' +
        '<h3 class="notification__title">' + title + '</h3>' +
      '</div>' +
      '<div class="notification__body">' + body + '</div>';

    notificationContainer.appendChild(notificationEl);

    const close = function () {
      notificationEl.classList.add('notification--closing');
      notificationEl.addEventListener('animationend', function () {
        notificationEl.remove();
      }, { once: true });
    };

    const closeBtn = notificationEl.querySelector('.notification__close');
    if (closeBtn) {
      closeBtn.addEventListener('click', close);
    }

    if (duration > 0) {
      window.setTimeout(close, duration);
    }
  };
}

  var dropdowns = Array.from(document.querySelectorAll('.dropdown'));

  dropdowns.forEach(function (dropdown) {
    var button = dropdown.querySelector('.dropbtn');
    if (!button) {
      return;
    }

    button.addEventListener('click', function (event) {
      event.stopPropagation();

      var willOpen = !dropdown.classList.contains('dropdown--open');
      
      dropdowns.forEach(function (otherDropdown) {
        if (otherDropdown !== dropdown) {
          otherDropdown.classList.remove('dropdown--open');
          var otherButton = otherDropdown.querySelector('.dropbtn');
          if (otherButton) {
            otherButton.setAttribute('aria-expanded', 'false');
          }
        }
      });

      dropdown.classList.toggle('dropdown--open', willOpen);
      button.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    });
  });

  document.addEventListener('click', function (event) {
    if (event.target.closest('.dropdown')) {
      return;
    }

    dropdowns.forEach(function (dropdown) {
      dropdown.classList.remove('dropdown--open');
      var button = dropdown.querySelector('.dropbtn');
      if (button) {
        button.setAttribute('aria-expanded', 'false');
      }
    });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') {
      return;
    }

    dropdowns.forEach(function (dropdown) {
      dropdown.classList.remove('dropdown--open');
      var button = dropdown.querySelector('.dropbtn');
      if (button) {
        button.setAttribute('aria-expanded', 'false');
      }
    });
  });

  function applyThemeUI(theme) {
    var themeCards = document.querySelectorAll('.theme-option[data-theme-value]');
    themeCards.forEach(function (card) {
      var value = card.getAttribute('data-theme-value');
      var active = value === theme;
      card.classList.toggle('theme-option--active', active);
      card.setAttribute('aria-checked', active ? 'true' : 'false');
    });
  }

  applyThemeUI(document.documentElement.getAttribute('data-theme') || 'ocean-depth');
});
