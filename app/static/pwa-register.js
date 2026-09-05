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
  var dismissBtn = null;

  function createInstallBanner() {
    var banner = document.createElement('div');
    banner.id = 'pwa-install-prompt';
    banner.className = 'install-prompt';
    banner.innerHTML =
      '<button class="install-dismiss" onclick="this.parentElement.remove()">×</button>' +
      '<div class="install-title">Install Sarkin Mota Autos</div>' +
      '<div class="install-desc">Install our app for faster access and offline browsing.</div>' +
      '<button class="install-btn" onclick="handleInstall()">Install</button>' +
      '<button class="install-btn secondary" onclick="this.parentElement.parentElement.remove()">Not now</button>';
    document.body.appendChild(banner);
    return banner;
  }

  window.handleInstall = function () {
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
    var images = document.querySelectorAll('img[data-src]:not(.loaded)');
    var observer = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var img = entry.target;
          var wrapper = img.closest('.loader-wrapper');
          if (wrapper) wrapper.classList.add('loaded');
          img.src = img.getAttribute('data-src') || img.src;
          img.classList.add('loaded');
          img.removeAttribute('data-src');
          obs.unobserve(img);
        }
      });
    }, { rootMargin: '100px' });

    images.forEach(function (img) {
      observer.observe(img);
    });

    var loadedImages = document.querySelectorAll('img:not([data-src])');
    loadedImages.forEach(function (img) {
      var wrapper = img.closest('.loader-wrapper');
      if (wrapper && img.complete) {
        wrapper.classList.add('loaded');
        img.classList.add('loaded');
      } else if (wrapper) {
        img.addEventListener('load', function () {
          wrapper.classList.add('loaded');
          img.classList.add('loaded');
        });
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initImageLoaders);
  } else {
    initImageLoaders();
  }
})();
