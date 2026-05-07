document.addEventListener('DOMContentLoaded', function () {
  var dark = document.getElementById('theme-opt-dark');
  var light = document.getElementById('theme-opt-light');

  if (!dark || !light) {
    return;
  }

  function refreshUI() {
    var theme = document.documentElement.getAttribute('data-theme') || 'dark';
    dark.classList.toggle('theme-option--active', theme === 'dark');
    light.classList.toggle('theme-option--active', theme === 'light');
  }

  function setTheme(nextTheme) {
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('theme', nextTheme);
    refreshUI();

    var icon = document.getElementById('theme-icon');
    var label = document.getElementById('theme-label');
    if (icon) {
      icon.textContent = nextTheme === 'dark' ? '☀️' : '🌙';
    }
    if (label) {
      label.textContent = nextTheme === 'dark' ? 'Light Mode' : 'Dark Mode';
    }
  }

  refreshUI();

  dark.addEventListener('click', function () {
    setTheme('dark');
  });

  light.addEventListener('click', function () {
    setTheme('light');
  });
});

// Ensure change-password form always submits (defensive fix)
document.addEventListener('DOMContentLoaded', function () {
  try {
    var changeBtn = document.querySelector('button[name="change-password-submit"]');
    if (!changeBtn) return;
    var pwForm = changeBtn.closest('form');
    if (!pwForm) return;

    // If other code prevents the click/submission, force it and avoid double submits
    changeBtn.addEventListener('click', function (ev) {
      try {
        // allow native submit if the button is type=submit
        if (changeBtn.type && changeBtn.type.toLowerCase() === 'submit') {
          // disable briefly to avoid double-clicks
          changeBtn.disabled = true;
          setTimeout(function () { changeBtn.disabled = false; }, 3000);
          return;
        }
        ev.preventDefault();
        changeBtn.disabled = true;
        pwForm.submit();
      } catch (e) { console.error('pw submit handler', e); }
    }, { passive: false });
  } catch (e) { }
});
