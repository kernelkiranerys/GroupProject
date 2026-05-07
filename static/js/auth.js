document.addEventListener('DOMContentLoaded', function () {
  function activateTab(tabName) {
    document.querySelectorAll('.auth-panel').forEach(function (panel) {
      panel.classList.remove('auth-panel--active');
    });

    document.querySelectorAll('.auth-tab').forEach(function (tab) {
      tab.classList.remove('auth-tab--active');
    });

    var panel = document.getElementById(tabName);
    var tab = document.querySelector('.auth-tab[data-tab="' + tabName + '"]');

    if (panel) {
      panel.classList.add('auth-panel--active');
    }
    if (tab) {
      tab.classList.add('auth-tab--active');
    }
  }

  var authContainer = document.querySelector('.auth-container');
  var initialTab = authContainer ? authContainer.getAttribute('data-initial-tab') : 'login';
  if (!initialTab) {
    initialTab = 'login';
  }

  document.querySelectorAll('.auth-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      activateTab(this.getAttribute('data-tab'));
    });
  });

  activateTab(initialTab);
});
