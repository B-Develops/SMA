(function () {
  'use strict';

  if (!('serviceWorker' in navigator)) {
    console.log('Service Worker not supported');
    return;
  }

  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/static/sw.js')
      .then(function (registration) {
        console.log('SW registered:', registration.scope);
      })
      .catch(function (error) {
        console.log('SW registration failed:', error);
      });
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
        '<div class="install-desc">Tap the share button below, then select "Add to Home Screen".</div>' +
        '<button class="install-btn" onclick="window.location.href=\'/#install-instructions\'">Show Instructions</button>' +
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
      deferredPrompt.userChoice.then(function (choiceResult) {
        if (choiceResult.outcome === 'accepted') {
          console.log('User installed');
        }
        deferredPrompt = null;
        if (installBanner) installBanner.remove();
      });
    }
  };

  function showInstallHint() {
    if (installBanner || installHintDismissed) return;
    installBanner = createInstallBanner();
    setTimeout(function () {
      if (installBanner && installBanner.parentNode) {
        installBanner.classList.add('visible');
      }
    }, 100);
  }

  function dismissHint() {
    installHintDismissed = true;
    if (installBanner) installBanner.remove();
  }

  if (isMobile) {
    setTimeout(showInstallHint, 3000);
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;

    if (installBanner) return;
    installBanner = createInstallBanner();
    setTimeout(function () {
      if (installBanner && installBanner.parentNode) {
        installBanner.classList.add('visible');
      }
    }, 100);
  });

  function initImageLoaders() {
    var wrappers = document.querySelectorAll('.loader-wrapper.loader-wrapper-loading');
    if (!wrappers.length) return;

    var observer = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var wrapper = entry.target;
          var img = wrapper.querySelector('img');
          if (img) {
            if (img.complete) {
              wrapper.classList.remove('loader-wrapper-loading');
              wrapper.classList.add('loader-wrapper-loaded');
              img.classList.add('loaded');
            } else {
              img.addEventListener('load', function () {
                wrapper.classList.remove('loader-wrapper-loading');
                wrapper.classList.add('loader-wrapper-loaded');
                img.classList.add('loaded');
              });
            }
          }
          obs.unobserve(wrapper);
        }
      });
    }, { rootMargin: '100px' });

    wrappers.forEach(function (wrapper) {
      var img = wrapper.querySelector('img');
      if (img) {
        if (img.complete) {
          wrapper.classList.remove('loader-wrapper-loading');
          wrapper.classList.add('loader-wrapper-loaded');
          img.classList.add('loaded');
        } else {
          img.addEventListener('load', function () {
            wrapper.classList.remove('loader-wrapper-loading');
            wrapper.classList.add('loader-wrapper-loaded');
            img.classList.add('loaded');
          });
          observer.observe(wrapper);
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initImageLoaders);
  } else {
    initImageLoaders();
  }
})();
