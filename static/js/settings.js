document.addEventListener('DOMContentLoaded', function () {
  var themeCards = document.querySelectorAll('.theme-option[data-theme-value]');
  var lightThemes = ['light', 'arctic-frost'];

  function refreshThemeCards() {
    var theme = document.documentElement.getAttribute('data-theme') || 'dark';
    themeCards.forEach(function (card) {
      var themeValue = card.getAttribute('data-theme-value');
      var isActive = themeValue === theme;
      card.classList.toggle('theme-option--active', isActive);
      card.setAttribute('aria-checked', isActive ? 'true' : 'false');
    });
  }

  refreshThemeCards();

  themeCards.forEach(function (card) {
    card.addEventListener('click', function () {
      var nextTheme = card.getAttribute('data-theme-value') || 'ocean-depth';
      document.documentElement.setAttribute('data-theme', nextTheme);
      localStorage.setItem('theme', nextTheme);
      refreshThemeCards();

      var icon = document.getElementById('theme-icon');
      var label = document.getElementById('theme-label');
      var isLight = lightThemes.indexOf(nextTheme) !== -1;
      if (icon) {
        icon.textContent = isLight ? '🌙' : '☀️';
      }
      if (label) {
        label.textContent = 'Theme';
      }
    });
  });

  var tabs = document.querySelectorAll('.settings-nav__btn');
  var panes = document.querySelectorAll('.tab-pane');
  var avatarOptions = document.querySelectorAll('.avatar-option');
  var alerts = document.querySelectorAll('.settings-alert');
  var passwordToggles = document.querySelectorAll('.password-toggle');

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var target = tab.getAttribute('data-tab');

      tabs.forEach(function (item) {
        item.classList.remove('settings-nav__btn--active');
      });
      tab.classList.add('settings-nav__btn--active');

      panes.forEach(function (pane) {
        pane.style.display = pane.id === target ? 'block' : 'none';
      });
    });
  });

  if (tabs.length > 0) {
    tabs[0].click();
  }

  alerts.forEach(function (alertEl) {
    window.setTimeout(function () {
      alertEl.style.transition = 'opacity 260ms ease';
      alertEl.style.opacity = '0';
      window.setTimeout(function () {
        alertEl.remove();
      }, 260);
    }, 3600);
  });

  avatarOptions.forEach(function (option) {
    var input = option.querySelector('.avatar-radio');
    if (!input) {
      return;
    }

    option.addEventListener('mousedown', function () {
      option.dataset.wasChecked = input.checked ? '1' : '0';
    });

    option.addEventListener('click', function (event) {
      if (option.dataset.wasChecked === '1') {
        event.preventDefault();
        input.checked = false;
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

    input.addEventListener('change', function () {
      if (!input.checked) {
        return;
      }

      var avatarForm = option.closest('form');
      if (!avatarForm) {
        return;
      }

      if (typeof avatarForm.requestSubmit === 'function') {
        avatarForm.requestSubmit();
      } else {
        avatarForm.submit();
      }
    });
  });

  passwordToggles.forEach(function (toggleBtn) {
    var targetId = toggleBtn.getAttribute('data-target');
    var passwordInput = document.getElementById(targetId);
    if (!passwordInput) {
      return;
    }

    toggleBtn.addEventListener('click', function () {
      var showing = passwordInput.type === 'text';
      passwordInput.type = showing ? 'password' : 'text';
      toggleBtn.textContent = showing ? '*' : '•';
      toggleBtn.setAttribute('aria-label', showing ? 'Show current password' : 'Hide current password');
    });
  });

  var notificationForm = document.getElementById('notifications-form');
  if (notificationForm) {
    notificationForm.querySelectorAll('input[type="checkbox"]').forEach(function (checkbox) {
      checkbox.addEventListener('change', function () {
        notificationForm.submit();
      });
    });
  }
});
