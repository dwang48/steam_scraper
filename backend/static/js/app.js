/**
 * Steam游戏监控前端应用
 */

class SteamGameApp {
    constructor() {
        this.apiBase = '/api';
        this.currentPage = 1;
        this.pageSize = 20;
        this.currentFilter = 'all';
        this.currentSort = '-scraped_at';
        this.searchQuery = '';
        this.isLoading = false;
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.loadStats();
        await this.loadGames();
    }
    
    setupEventListeners() {
        // 搜索框事件
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', this.debounce((e) => {
            this.searchQuery = e.target.value;
            this.currentPage = 1;
            this.loadGames();
        }, 500));
        
        // 筛选按钮事件
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // 更新按钮状态
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                
                // 更新筛选条件
                this.currentFilter = e.target.dataset.filter;
                this.currentPage = 1;
                this.loadGames();
            });
        });
        
        // 排序选择事件
        const sortSelect = document.getElementById('sortSelect');
        sortSelect.addEventListener('change', (e) => {
            this.currentSort = e.target.value;
            this.currentPage = 1;
            this.loadGames();
        });
        
        // 模态框事件
        const modal = document.getElementById('gameModal');
        const closeModal = document.getElementById('closeModal');
        
        closeModal.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        window.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    async loadStats() {
        try {
            const response = await fetch(`${this.apiBase}/games/stats/`);
            const stats = await response.json();
            
            document.getElementById('totalGames').textContent = stats.total_games || 0;
            document.getElementById('newGames').textContent = stats.new_games || 0;
            document.getElementById('freeGames').textContent = stats.free_games || 0;
        } catch (error) {
            console.error('加载统计信息失败:', error);
        }
    }
    
    async loadGames() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading(true);
        
        try {
            let url = `${this.apiBase}/games/`;
            const params = new URLSearchParams({
                page: this.currentPage,
                ordering: this.currentSort,
            });
            
            // 添加搜索参数
            if (this.searchQuery.trim()) {
                params.append('search', this.searchQuery.trim());
            }
            
            // 根据筛选条件调整URL
            switch (this.currentFilter) {
                case 'new':
                    url = `${this.apiBase}/games/new_games/`;
                    break;
                case 'free':
                    url = `${this.apiBase}/games/free_games/`;
                    break;
                case 'sale':
                    url = `${this.apiBase}/games/on_sale/`;
                    break;
                default:
                    // 全部游戏，使用默认URL
                    break;
            }
            
            const response = await fetch(`${url}?${params}`);
            const data = await response.json();
            
            this.renderGames(data.results || []);
            this.renderPagination(data);
            
        } catch (error) {
            console.error('加载游戏数据失败:', error);
            this.showError('加载游戏数据失败，请稍后重试');
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
    }
    
    renderGames(games) {
        const gamesGrid = document.getElementById('gamesGrid');
        
        if (games.length === 0) {
            gamesGrid.innerHTML = `
                <div class="no-games">
                    <i class="fas fa-search" style="font-size: 3rem; color: #a0aec0; margin-bottom: 1rem;"></i>
                    <p style="color: #718096; font-size: 1.2rem;">未找到符合条件的游戏</p>
                </div>
            `;
            return;
        }
        
        gamesGrid.innerHTML = games.map(game => this.createGameCard(game)).join('');
        
        // 添加游戏卡片点击事件
        document.querySelectorAll('.game-card').forEach(card => {
            card.addEventListener('click', () => {
                this.showGameDetail(card.dataset.gameId);
            });
        });
    }
    
    createGameCard(game) {
        const priceHtml = this.createPriceHtml(game);
        const tagsHtml = game.tags?.slice(0, 3).map(tag => `<span class="tag">${tag}</span>`).join('') || '';
        const releaseDate = game.release_date ? new Date(game.release_date).toLocaleDateString('zh-CN') : '未知';
        const scrapedDate = new Date(game.scraped_at).toLocaleDateString('zh-CN');
        
        return `
            <div class="game-card" data-game-id="${game.id}">
                <img src="${game.header_image || '/static/images/placeholder.jpg'}" 
                     alt="${game.name}" 
                     class="game-image" 
                     onerror="this.src='/static/images/placeholder.jpg'">
                <div class="game-content">
                    <h3 class="game-title">${game.name}</h3>
                    <p class="game-developer">${game.developer || '未知开发商'}</p>
                    
                    <div class="game-price">
                        ${priceHtml}
                        ${game.is_new ? '<span class="new-badge">新游戏</span>' : ''}
                    </div>
                    
                    <div class="game-tags">
                        ${tagsHtml}
                    </div>
                    
                    <div class="game-meta">
                        <span>发布: ${releaseDate}</span>
                        <span>抓取: ${scrapedDate}</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    createPriceHtml(game) {
        if (game.is_free) {
            return '<span class="free-badge">免费</span>';
        }
        
        if (!game.price) {
            return '<span class="price-info">价格未知</span>';
        }
        
        const price = parseFloat(game.price);
        const finalPrice = parseFloat(game.final_price || game.price);
        const currency = game.currency || 'USD';
        
        if (game.discount_percent > 0) {
            return `
                <div class="price-info">
                    <span class="current-price">${finalPrice.toFixed(2)} ${currency}</span>
                    <span class="original-price">${price.toFixed(2)} ${currency}</span>
                </div>
                <span class="discount-badge">-${game.discount_percent}%</span>
            `;
        } else {
            return `
                <div class="price-info">
                    <span class="current-price">${price.toFixed(2)} ${currency}</span>
                </div>
            `;
        }
    }
    
    async showGameDetail(gameId) {
        try {
            const response = await fetch(`${this.apiBase}/games/${gameId}/`);
            const game = await response.json();
            
            const modal = document.getElementById('gameModal');
            const modalBody = document.getElementById('modalBody');
            
            modalBody.innerHTML = this.createGameDetailHtml(game);
            modal.style.display = 'block';
            
        } catch (error) {
            console.error('加载游戏详情失败:', error);
            this.showError('加载游戏详情失败');
        }
    }
    
    createGameDetailHtml(game) {
        const screenshotsHtml = game.screenshots?.length > 0 
            ? game.screenshots.map(url => `<img src="${url}" alt="游戏截图" class="screenshot">`).join('')
            : '<p>暂无截图</p>';
            
        const tagsHtml = game.tags?.length > 0 
            ? game.tags.map(tag => `<span class="tag">${tag}</span>`).join('')
            : '<p>暂无标签</p>';
            
        const platformsHtml = game.platforms?.length > 0 
            ? game.platforms.join(', ')
            : '未知';
            
        const languagesHtml = game.languages?.length > 0 
            ? game.languages.join(', ')
            : '未知';
        
        return `
            <div class="game-detail">
                <div class="game-detail-header">
                    <img src="${game.header_image || '/static/images/placeholder.jpg'}" 
                         alt="${game.name}" 
                         class="game-detail-image">
                    <div class="game-detail-overlay">
                        <h2 class="game-detail-title">${game.name}</h2>
                        <p class="game-detail-developer">${game.developer || '未知开发商'}</p>
                    </div>
                </div>
                
                <div class="game-detail-body">
                    <div class="game-detail-section">
                        <h3>游戏信息</h3>
                        <p><strong>发行商:</strong> ${game.publisher || '未知'}</p>
                        <p><strong>发布日期:</strong> ${game.release_date ? new Date(game.release_date).toLocaleDateString('zh-CN') : '未知'}</p>
                        <p><strong>支持平台:</strong> ${platformsHtml}</p>
                        <p><strong>支持语言:</strong> ${languagesHtml}</p>
                        <p><strong>价格:</strong> ${this.createPriceText(game)}</p>
                    </div>
                    
                    ${game.description ? `
                        <div class="game-detail-section">
                            <h3>游戏描述</h3>
                            <p>${game.description}</p>
                        </div>
                    ` : ''}
                    
                    <div class="game-detail-section">
                        <h3>游戏标签</h3>
                        <div class="game-tags">
                            ${tagsHtml}
                        </div>
                    </div>
                    
                    ${game.screenshots?.length > 0 ? `
                        <div class="game-detail-section">
                            <h3>游戏截图</h3>
                            <div class="game-screenshots">
                                ${screenshotsHtml}
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    createPriceText(game) {
        if (game.is_free) {
            return '免费';
        }
        
        if (!game.price) {
            return '价格未知';
        }
        
        const price = parseFloat(game.price);
        const finalPrice = parseFloat(game.final_price || game.price);
        const currency = game.currency || 'USD';
        
        if (game.discount_percent > 0) {
            return `${finalPrice.toFixed(2)} ${currency} (原价: ${price.toFixed(2)} ${currency}, 折扣: -${game.discount_percent}%)`;
        } else {
            return `${price.toFixed(2)} ${currency}`;
        }
    }
    
    renderPagination(data) {
        const pagination = document.getElementById('pagination');
        
        if (!data.count || data.count <= this.pageSize) {
            pagination.innerHTML = '';
            return;
        }
        
        const totalPages = Math.ceil(data.count / this.pageSize);
        const currentPage = this.currentPage;
        
        let paginationHtml = '';
        
        // 上一页按钮
        paginationHtml += `
            <button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="app.goToPage(${currentPage - 1})">
                <i class="fas fa-chevron-left"></i>
            </button>
        `;
        
        // 页码按钮
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        
        if (startPage > 1) {
            paginationHtml += `<button class="page-btn" onclick="app.goToPage(1)">1</button>`;
            if (startPage > 2) {
                paginationHtml += `<span class="page-ellipsis">...</span>`;
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `
                <button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="app.goToPage(${i})">
                    ${i}
                </button>
            `;
        }
        
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                paginationHtml += `<span class="page-ellipsis">...</span>`;
            }
            paginationHtml += `<button class="page-btn" onclick="app.goToPage(${totalPages})">${totalPages}</button>`;
        }
        
        // 下一页按钮
        paginationHtml += `
            <button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="app.goToPage(${currentPage + 1})">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;
        
        pagination.innerHTML = paginationHtml;
    }
    
    goToPage(page) {
        this.currentPage = page;
        this.loadGames();
        
        // 滚动到顶部
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
    
    showLoading(show) {
        const loading = document.getElementById('loading');
        loading.style.display = show ? 'block' : 'none';
    }
    
    showError(message) {
        // 简单的错误提示
        alert(message);
    }
}

// 初始化应用
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new SteamGameApp();
}); 