document.addEventListener('DOMContentLoaded', function() {
    const filterButtons = document.querySelectorAll('.filter-btn-compact');
    const trophyEntries = document.querySelectorAll('.trophy-entry');

    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            const filterValue = this.dataset.filter;
            
            trophyEntries.forEach(entry => {
                const shouldShow = filterEntries(entry, filterValue);
                entry.classList.toggle('hidden', !shouldShow);
            });
        });
    });

    function filterEntries(entry, filter) {
        switch(filter) {
            case 'all':
                return true;
            case 'unlocked':
                return entry.classList.contains('unlocked');
            case 'locked':
                return entry.classList.contains('locked');
            case 'platinum':
            case 'gold':
            case 'silver':
            case 'bronze':
                return entry.dataset.rarity === filter && entry.classList.contains('unlocked');
            default:
                return true;
        }
    }

    setTimeout(() => {
        const progressFill = document.querySelector('.progress-fill-compact');
        if (progressFill) {
            const width = progressFill.style.width;
            progressFill.style.width = '0%';
            setTimeout(() => {
                progressFill.style.width = width;
            }, 300);
        }
    }, 100);
});