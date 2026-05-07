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
