(() => {
    const themeButton = document.querySelector('#theme-toggle');
    const updateThemeButton = () => {
        const dark = document.documentElement.classList.contains('dark');
        themeButton?.setAttribute('aria-pressed', String(dark));
        themeButton?.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} mode`);
    };
    updateThemeButton();
    themeButton?.addEventListener('click', () => {
        const dark = document.documentElement.classList.toggle('dark');
        try { localStorage.setItem('reading-room-theme', dark ? 'dark' : 'light'); } catch (_) { /* Use the theme for this page. */ }
        updateThemeButton();
    });
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
        let saved;
        try { saved = localStorage.getItem('reading-room-theme'); } catch (_) { /* No saved preference. */ }
        if (!saved) { document.documentElement.classList.toggle('dark', event.matches); updateThemeButton(); }
    });
    document.querySelectorAll('[data-cover]').forEach((image) => {
        const showCover = () => { if (image.naturalWidth > 1) image.classList.add('is-loaded'); };
        image.addEventListener('load', showCover);
        image.addEventListener('error', () => image.remove());
        if (image.complete) showCover();
    });
    const tools = document.querySelector('[data-collection]');
    if (tools) {
        const grid = document.querySelector('[data-card-grid]');
        const cards = Array.from(grid.querySelectorAll('[data-card]'));
        const category = tools.querySelector('[data-category-filter]');
        const availability = tools.querySelector('[data-availability-filter]');
        const sort = tools.querySelector('[data-sort]');
        const search = tools.querySelector('[data-search]');
        const readerDirectory = tools.dataset.collection === 'students';
        const seen = new Set();
        Array.from(category.options).slice(1).forEach((option) => {
            if (!option.value || seen.has(option.value)) option.remove();
            else seen.add(option.value);
        });
        const update = () => {
            let visible = 0;
            cards.forEach((card) => {
                const matchesCategory = !category.value || card.dataset.category === category.value;
                const available = Number(card.dataset.available) > 0;
                const matchesAvailability = !availability?.value || (availability.value === 'available' ? available : !available);
                const text = `${card.dataset.title} ${card.dataset.category}`.toLocaleLowerCase();
                const matchesSearch = !readerDirectory || text.includes(search.value.trim().toLocaleLowerCase());
                card.hidden = !(matchesCategory && matchesAvailability && matchesSearch);
                if (!card.hidden) visible++;
            });
            const order = sort?.value || 'default';
            const ordered = [...cards];
            if (order === 'copies') ordered.sort((a, b) => Number(b.dataset.available) - Number(a.dataset.available));
            else if (order !== 'default') ordered.sort((a, b) => (a.dataset[order] || '').localeCompare(b.dataset[order] || '', undefined, { sensitivity: 'base' }));
            ordered.forEach((card) => grid.append(card));
            const noun = readerDirectory ? 'reader' : 'book';
            document.querySelector('[data-result-count]').textContent = `${visible} ${noun}${visible === 1 ? '' : 's'}`;
            document.querySelector('[data-filter-empty]').hidden = visible > 0 || cards.length === 0;
        };
        [category, availability, sort].filter(Boolean).forEach((field) => field.addEventListener('change', update));
        if (readerDirectory) search.addEventListener('input', update);
        document.querySelectorAll('[data-reset]').forEach((button) => button.addEventListener('click', () => {
            category.value = '';
            if (availability) availability.value = '';
            if (sort) sort.value = 'default';
            if (readerDirectory) search.value = '';
            update();
        }));
        update();
    }
    document.querySelector('#contact-form')?.addEventListener('submit', (event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const body = `${form.get('body')}\n\nFrom: ${form.get('name')}\nReply to: ${form.get('email')}`;
        window.location.href = `mailto:library@2456.com?subject=${encodeURIComponent('Library enquiry')}&body=${encodeURIComponent(body)}`;
        document.querySelector('#contact-status').textContent = 'Email draft requested. If no email app opens, contact library@2456.com directly.';
    });
})();
