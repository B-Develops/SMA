(function () {
  'use strict';

  if (!('serviceWorker' in navigator)) return;

  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/static/sw.js')
      .then(function (r) { console.log('SW registered:', r.scope); })
      .catch(function (e) { console.log('SW registration failed:', e); });
  });

  var deferredPrompt;
  var installBanner = null;
  var installHintDismissed = false;

  var isIOS = /iPhone|iPad|iPod/.test(navigator.userAgent);
  var isAndroid = /Android/.test(navigator.userAgent);
  var isMobile = isIOS || isAndroid;

  function createInstallBanner() {
    var banner = document.createElement('div');
    banner.id = 'pwa-install-prompt';
    banner.className = 'install-prompt';

    if (isMobile) {
      banner.innerHTML =
        '<button class="install-dismiss" onclick="this.parentElement.remove()">×</button>' +
        '<div class="install-title">Add to Home Screen</div>' +
        '<div class="install-desc">Tap the share button, then select "Add to Home Screen".</div>' +
        '<button class="install-btn secondary" onclick="this.parentElement.remove()">Got it</button>';
    } else {
      banner.innerHTML =
        '<button class="install-dismiss" onclick="this.parentElement.remove()">×</button>' +
        '<div class="install-title">Install Sarkin Mota Autos</div>' +
        '<div class="install-desc">Install our app for faster access and offline browsing.</div>' +
        '<button class="install-btn" onclick="handlePWAInstall()">Install</button>' +
        '<button class="install-btn secondary" onclick="this.parentElement.remove()">Not now</button>';
    }

    document.body.appendChild(banner);
    return banner;
  }

  window.handlePWAInstall = function () {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then(function (r) {
        if (r.outcome === 'accepted') console.log('User installed');
        deferredPrompt = null;
        if (installBanner) installBanner.remove();
      });
    }
  };

  function showInstallHint() {
    if (installBanner || installHintDismissed) return;
    installBanner = createInstallBanner();
    setTimeout(function () {
      if (installBanner && installBanner.parentNode) installBanner.classList.add('visible');
    }, 100);
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (!installBanner) {
      installBanner = createInstallBanner();
      setTimeout(function () {
        if (installBanner && installBanner.parentNode) installBanner.classList.add('visible');
      }, 100);
    }
  });

  if (isMobile) {
    setTimeout(showInstallHint, 3000);
  }
})();
