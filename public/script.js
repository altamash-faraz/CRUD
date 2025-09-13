class CRUDApp {
    constructor() {
        this.baseURL = '/api/items';
        this.currentEditId = null;
        this.useLocalStorage = false;
        this.localStorageKey = 'crud_items';
        this.allItems = [];
        this.filteredItems = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkDatabaseConnection();
        this.loadItems();
    }

    async checkDatabaseConnection() {
        try {
            const response = await fetch('/api/items');
            if (response.status === 503) {
                this.useLocalStorage = true;
                this.showDatabaseWarning();
            }
        } catch (error) {
            this.useLocalStorage = true;
            this.showDatabaseWarning();
        }
    }

    showDatabaseWarning() {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'warning-message';
        warningDiv.innerHTML = `
            <strong>⚠️ Database Not Connected</strong><br>
            MongoDB is not running. Using local storage as fallback.<br>
            <small>Your data will be saved locally in your browser.</small>
        `;
        
        const container = document.querySelector('.container');
        container.insertBefore(warningDiv, container.firstChild);
    }

    bindEvents() {
        // Form submission
        document.getElementById('item-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmit();
        });

        // Cancel button
        document.getElementById('cancel-btn').addEventListener('click', () => {
            this.resetForm();
        });

        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadItems();
        });

        // Search functionality
        document.getElementById('search-input').addEventListener('input', (e) => {
            this.filterItems();
        });

        // Category filter
        document.getElementById('category-filter').addEventListener('change', (e) => {
            this.filterItems();
        });

        // Export functionality
        document.getElementById('export-btn').addEventListener('click', () => {
            this.exportData();
        });
    }

    async handleFormSubmit() {
        const formData = this.getFormData();
        
        if (!this.validateForm(formData)) {
            return;
        }

        try {
            if (this.currentEditId) {
                await this.updateItem(this.currentEditId, formData);
                this.showMessage('Item updated successfully!', 'success');
            } else {
                await this.createItem(formData);
                this.showMessage('Item created successfully!', 'success');
            }
            
            this.resetForm();
            this.loadItems();
        } catch (error) {
            this.showMessage(`Error: ${error.message}`, 'error');
        }
    }

    getFormData() {
        return {
            name: document.getElementById('name').value.trim(),
            description: document.getElementById('description').value.trim(),
            category: document.getElementById('category').value,
            price: document.getElementById('price').value
        };
    }

    validateForm(data) {
        if (!data.name || !data.description || !data.category || !data.price) {
            this.showMessage('Please fill in all fields', 'error');
            return false;
        }

        if (isNaN(data.price) || parseFloat(data.price) < 0) {
            this.showMessage('Please enter a valid price', 'error');
            return false;
        }

        return true;
    }

    async createItem(data) {
        if (this.useLocalStorage) {
            return this.createItemLocal(data);
        }
        
        const response = await fetch(this.baseURL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            if (response.status === 503) {
                // Database not connected, switch to local storage
                this.useLocalStorage = true;
                this.showDatabaseWarning();
                return this.createItemLocal(data);
            }
            throw new Error(error.error || 'Failed to create item');
        }

        return response.json();
    }

    createItemLocal(data) {
        const items = this.getLocalItems();
        const newItem = {
            _id: 'local_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
            ...data,
            price: parseFloat(data.price),
            createdAt: new Date().toISOString()
        };
        items.unshift(newItem);
        localStorage.setItem(this.localStorageKey, JSON.stringify(items));
        return Promise.resolve(newItem);
    }

    getLocalItems() {
        try {
            return JSON.parse(localStorage.getItem(this.localStorageKey) || '[]');
        } catch (error) {
            return [];
        }
    }

    async loadItems() {
        const container = document.getElementById('items-container');
        const loading = document.getElementById('loading');
        
        loading.style.display = 'block';
        container.innerHTML = '';

        try {
            let items;
            
            if (this.useLocalStorage) {
                items = this.getLocalItems();
            } else {
                const response = await fetch(this.baseURL);
                if (response.status === 503) {
                    // Database not connected, switch to local storage
                    this.useLocalStorage = true;
                    this.showDatabaseWarning();
                    items = this.getLocalItems();
                } else if (!response.ok) {
                    throw new Error('Failed to load items');
                } else {
                    items = await response.json();
                }
            }

            loading.style.display = 'none';
            this.allItems = items;
            this.filterItems();
        } catch (error) {
            loading.style.display = 'none';
            container.innerHTML = `
                <div class="error-message">
                    Error loading items: ${error.message}
                    ${this.useLocalStorage ? '<br><small>Using local storage fallback.</small>' : ''}
                </div>
            `;
        }
    }

    filterItems() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        const categoryFilter = document.getElementById('category-filter').value;
        
        this.filteredItems = this.allItems.filter(item => {
            const matchesSearch = !searchTerm || 
                item.name.toLowerCase().includes(searchTerm) ||
                item.description.toLowerCase().includes(searchTerm);
            
            const matchesCategory = !categoryFilter || item.category === categoryFilter;
            
            return matchesSearch && matchesCategory;
        });
        
        this.displayItems(this.filteredItems);
    }

    displayItems(items) {
        const container = document.getElementById('items-container');

        if (items.length === 0) {
            const hasFilters = document.getElementById('search-input').value || 
                              document.getElementById('category-filter').value;
            
            container.innerHTML = `
                <div class="empty-state">
                    <h3>${hasFilters ? 'No items match your search' : 'No items found'}</h3>
                    <p>${hasFilters ? 'Try adjusting your search criteria.' : 'Start by adding your first item using the form above.'}</p>
                    ${this.useLocalStorage ? '<small>Data will be saved locally in your browser.</small>' : ''}
                </div>
            `;
            return;
        }

        container.innerHTML = items.map(item => this.createItemCard(item)).join('');
    }

    exportData() {
        const dataToExport = this.useLocalStorage ? this.getLocalItems() : this.allItems;
        
        if (dataToExport.length === 0) {
            this.showMessage('No data to export', 'error');
            return;
        }

        // Create CSV content
        const headers = ['Name', 'Description', 'Category', 'Price', 'Created Date'];
        const csvContent = [
            headers.join(','),
            ...dataToExport.map(item => [
                `"${item.name}"`,
                `"${item.description}"`,
                `"${item.category}"`,
                item.price,
                new Date(item.createdAt).toLocaleDateString()
            ].join(','))
        ].join('\n');

        // Download CSV file
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `crud-items-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        
        this.showMessage('Data exported successfully!', 'success');
        } catch (error) {
            loading.style.display = 'none';
            container.innerHTML = `
                <div class="error-message">
                    Error loading items: ${error.message}
                    ${this.useLocalStorage ? '<br><small>Using local storage fallback.</small>' : ''}
                </div>
            `;
        }
    }

    createItemCard(item) {
        const createdDate = new Date(item.createdAt).toLocaleDateString();
        return `
            <div class="item-card">
                <div class="item-header">
                    <h3 class="item-name">${this.escapeHtml(item.name)}</h3>
                    <span class="item-price">$${parseFloat(item.price).toFixed(2)}</span>
                </div>
                <div class="item-category">${this.escapeHtml(item.category)}</div>
                <p class="item-description">${this.escapeHtml(item.description)}</p>
                <div class="item-meta">Created: ${createdDate}</div>
                <div class="item-actions">
                    <button class="edit-btn" onclick="app.editItem('${item._id}')">Edit</button>
                    <button class="delete-btn" onclick="app.deleteItem('${item._id}')">Delete</button>
                </div>
            </div>
        `;
    }

    async editItem(id) {
        try {
            let item;
            
            if (this.useLocalStorage) {
                const items = this.getLocalItems();
                item = items.find(i => i._id === id);
                if (!item) {
                    throw new Error('Item not found');
                }
            } else {
                const response = await fetch(`${this.baseURL}/${id}`);
                if (!response.ok) {
                    throw new Error('Failed to load item');
                }
                item = await response.json();
            }

            this.populateForm(item);
            this.currentEditId = id;
            
            // Scroll to form
            document.querySelector('.form-section').scrollIntoView({ 
                behavior: 'smooth' 
            });
        } catch (error) {
            this.showMessage(`Error: ${error.message}`, 'error');
        }
    }

    populateForm(item) {
        document.getElementById('item-id').value = item._id;
        document.getElementById('name').value = item.name;
        document.getElementById('description').value = item.description;
        document.getElementById('category').value = item.category;
        document.getElementById('price').value = item.price;
        
        document.getElementById('form-title').textContent = 'Edit Item';
        document.getElementById('submit-btn').textContent = 'Update Item';
        document.getElementById('cancel-btn').style.display = 'inline-block';
    }

    async updateItem(id, data) {
        if (this.useLocalStorage) {
            return this.updateItemLocal(id, data);
        }
        
        const response = await fetch(`${this.baseURL}/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            if (response.status === 503) {
                this.useLocalStorage = true;
                this.showDatabaseWarning();
                return this.updateItemLocal(id, data);
            }
            throw new Error(error.error || 'Failed to update item');
        }

        return response.json();
    }

    updateItemLocal(id, data) {
        const items = this.getLocalItems();
        const index = items.findIndex(item => item._id === id);
        if (index === -1) {
            throw new Error('Item not found');
        }
        
        items[index] = {
            ...items[index],
            ...data,
            price: parseFloat(data.price)
        };
        
        localStorage.setItem(this.localStorageKey, JSON.stringify(items));
        return Promise.resolve(items[index]);
    }

    async deleteItem(id) {
        if (!confirm('Are you sure you want to delete this item?')) {
            return;
        }

        try {
            if (this.useLocalStorage) {
                this.deleteItemLocal(id);
            } else {
                const response = await fetch(`${this.baseURL}/${id}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    if (response.status === 503) {
                        this.useLocalStorage = true;
                        this.showDatabaseWarning();
                        this.deleteItemLocal(id);
                    } else {
                        throw new Error('Failed to delete item');
                    }
                }
            }

            this.showMessage('Item deleted successfully!', 'success');
            this.loadItems();
        } catch (error) {
            this.showMessage(`Error: ${error.message}`, 'error');
        }
    }

    deleteItemLocal(id) {
        const items = this.getLocalItems();
        const filteredItems = items.filter(item => item._id !== id);
        localStorage.setItem(this.localStorageKey, JSON.stringify(filteredItems));
    }

    resetForm() {
        document.getElementById('item-form').reset();
        document.getElementById('item-id').value = '';
        this.currentEditId = null;
        
        document.getElementById('form-title').textContent = 'Add New Item';
        document.getElementById('submit-btn').textContent = 'Add Item';
        document.getElementById('cancel-btn').style.display = 'none';
        
        this.clearMessages();
    }

    showMessage(message, type) {
        this.clearMessages();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = type === 'success' ? 'success-message' : 'error-message';
        messageDiv.textContent = message;
        
        const formSection = document.querySelector('.form-section');
        formSection.insertBefore(messageDiv, formSection.firstChild);
        
        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                messageDiv.remove();
            }, 3000);
        }
    }

    clearMessages() {
        const messages = document.querySelectorAll('.success-message, .error-message');
        messages.forEach(msg => msg.remove());
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new CRUDApp();
});
