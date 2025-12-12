document.addEventListener('DOMContentLoaded', function() {
    const gameCards = document.querySelectorAll('.game-card');
    const filterButtons = document.querySelectorAll('.filter-btn');

    gameCards.forEach(card => {
        card.addEventListener('click', function() {
            const gameId = this.dataset.gameId;
            if (gameId) {
                window.location.href = `/games/${gameId}/trophies`;
            }
        });
        
        card.style.cursor = 'pointer';
    });

    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const isSort = this.dataset.sort !== undefined;
            const isFilter = this.dataset.filter !== undefined;

            if (isSort) {
                document.querySelectorAll('[data-sort]').forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                sortGames(this.dataset.sort);
            }

            if (isFilter) {
                document.querySelectorAll('[data-filter]').forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                filterGames(this.dataset.filter);
            }
        });
    });

    function sortGames(sortBy) {
        const gameList = document.querySelector('.game-list');
        const cards = Array.from(gameCards);

        cards.sort((a, b) => {
            switch(sortBy) {
                case 'alphabetical':
                    return a.dataset.name.localeCompare(b.dataset.name);
                case 'completion':
                    return parseFloat(b.dataset.completion) - parseFloat(a.dataset.completion);
                case 'trophies':
                    return parseInt(b.dataset.trophies) - parseInt(a.dataset.trophies);
                case 'recent':
                default:
                    return 0;
            }
        });

        cards.forEach(card => gameList.appendChild(card));
    }

    function filterGames(filterBy) {
        gameCards.forEach(card => {
            const shouldShow = filterBy === 'all' || card.dataset.filterCategory === filterBy;
            card.classList.toggle('hidden', !shouldShow);
        });
    }

    setTimeout(() => {
        const progressFills = document.querySelectorAll('.progress-fill');
        progressFills.forEach(fill => {
            const width = fill.style.width;
            fill.style.width = '0%';
            setTimeout(() => {
                fill.style.width = width;
            }, Math.random() * 500 + 100);
        });
    }, 100);
});