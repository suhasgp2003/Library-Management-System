(() => {
    const themeButton = document.querySelector('#theme-toggle');
    const updateThemeButton = () => {
        const dark = document.documentElement.classList.contains('dark');
        themeButton?.setAttribute('aria-pressed', String(dark));
        themeButton?.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} mode`);
        themeButton?.setAttribute('title', `Switch to ${dark ? 'light' : 'dark'} mode`);
    };
    updateThemeButton();
    themeButton?.addEventListener('click', () => {
        const dark = document.documentElement.classList.toggle('dark');
        try { localStorage.setItem('reading-room-theme', dark ? 'dark' : 'light'); } catch (_) { /* This page still supports toggling. */ }
        updateThemeButton();
    });
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
        let saved;
        try { saved = localStorage.getItem('reading-room-theme'); } catch (_) { /* No saved preference. */ }
        if (!saved) { document.documentElement.classList.toggle('dark', event.matches); updateThemeButton(); }
    });
    const accountMenu = document.querySelector('[data-account-menu]');
    const sidebarNavigation = document.querySelector('[data-sidebar-navigation]');
    const desktopNavigation = window.matchMedia('(min-width: 1024px)');
    const syncNavigation = () => { if (sidebarNavigation) sidebarNavigation.open = desktopNavigation.matches; };
    syncNavigation();
    desktopNavigation.addEventListener('change', syncNavigation);
    document.addEventListener('click', event => {
        if (accountMenu?.open && !accountMenu.contains(event.target)) accountMenu.open = false;
        if (!desktopNavigation.matches && sidebarNavigation?.open && !event.target.closest('.sidebar')) sidebarNavigation.open = false;
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && accountMenu?.open) {
            accountMenu.open = false;
            accountMenu.querySelector('summary').focus();
            event.preventDefault();
        } else if (event.key === 'Escape' && !desktopNavigation.matches && sidebarNavigation?.open) {
            sidebarNavigation.open = false;
            sidebarNavigation.querySelector('summary').focus();
            event.preventDefault();
        }
    });
    document.querySelectorAll('[data-cover]').forEach(image => {
        const showCover = () => { if (image.naturalWidth > 1) image.classList.add('is-loaded'); };
        image.addEventListener('load', showCover);
        image.addEventListener('error', () => image.remove());
        if (image.complete) showCover();
    });
    document.querySelector('#contact-form')?.addEventListener('submit', event => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const body = `${form.get('body')}\n\nFrom: ${form.get('name')}\nReply to: ${form.get('email')}`;
        window.location.href = `mailto:library@2456.com?subject=${encodeURIComponent('Library enquiry')}&body=${encodeURIComponent(body)}`;
        document.querySelector('#contact-status').textContent = 'Email draft requested. If no email app opens, contact library@2456.com directly.';
    });
})();
