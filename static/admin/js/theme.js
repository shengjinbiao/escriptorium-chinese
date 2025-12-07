'use strict';

/**
 * Override Django's default theme toggle script to be resilient when
 * localStorage is unavailable (e.g. strict privacy mode or disabled cookies).
 */
(function () {
    window.addEventListener('load', function () {
        const storage = {
            get(key) {
                try {
                    return window.localStorage.getItem(key);
                } catch (err) {
                    console.warn('Theme preference storage unavailable.', err);
                    return null;
                }
            },
            set(key, value) {
                try {
                    window.localStorage.setItem(key, value);
                } catch (err) {
                    console.warn('Unable to persist theme preference.', err);
                }
            }
        };

        function safePrefersDark() {
            try {
                return window.matchMedia('(prefers-color-scheme: dark)').matches;
            } catch (err) {
                return false;
            }
        }

        function setTheme(mode) {
            if (!['light', 'dark', 'auto'].includes(mode)) {
                console.error(`Got invalid theme mode: ${mode}. Resetting to auto.`);
                mode = 'auto';
            }
            document.documentElement.dataset.theme = mode;
            storage.set('theme', mode);
        }

        function getCurrentTheme() {
            return storage.get('theme') || document.documentElement.dataset.theme || 'auto';
        }

        function cycleTheme() {
            const currentTheme = getCurrentTheme();
            const prefersDark = safePrefersDark();

            if (prefersDark) {
                if (currentTheme === 'auto') {
                    setTheme('light');
                } else if (currentTheme === 'light') {
                    setTheme('dark');
                } else {
                    setTheme('auto');
                }
            } else {
                if (currentTheme === 'auto') {
                    setTheme('dark');
                } else if (currentTheme === 'dark') {
                    setTheme('light');
                } else {
                    setTheme('auto');
                }
            }
        }

        function initTheme() {
            const currentTheme = getCurrentTheme();
            setTheme(currentTheme || 'auto');
        }

        const buttons = document.getElementsByClassName('theme-toggle');
        Array.from(buttons).forEach((btn) => {
            btn.addEventListener('click', cycleTheme);
            btn.classList.remove('theme-toggle--disabled');
        });

        initTheme();
    });
})();
