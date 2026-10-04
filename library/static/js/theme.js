(() => {
    let preference;
    try { preference = localStorage.getItem('reading-room-theme'); } catch (_) { /* Storage may be blocked. */ }
    const dark = preference ? preference === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.classList.toggle('dark', dark);
})();
