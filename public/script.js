class CRUDApp {
    constructor() {
        this.baseURL = '/api/items';
        this.currentEditId = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadItems();
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
        const response = await fetch(this.baseURL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create item');
        }

        return response.json();
    }

    async loadItems() {
        const container = document.getElementById('items-container');
        const loading = document.getElementById('loading');
        
        loading.style.display = 'block';
        container.innerHTML = '';

        try {
            const response = await fetch(this.baseURL);
            if (!response.ok) {
                throw new Error('Failed to load items');
            }

            const items = await response.json();
            loading.style.display = 'none';

            if (items.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <h3>No items found</h3>
                        <p>Start by adding your first item using the form above.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = items.map(item => this.createItemCard(item)).join('');
        } catch (error) {
            loading.style.display = 'none';
            container.innerHTML = `
                <div class="error-message">
                    Error loading items: ${error.message}
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
            const response = await fetch(`${this.baseURL}/${id}`);
            if (!response.ok) {
                throw new Error('Failed to load item');
            }

            const item = await response.json();
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
        const response = await fetch(`${this.baseURL}/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to update item');
        }

        return response.json();
    }

    async deleteItem(id) {
        if (!confirm('Are you sure you want to delete this item?')) {
            return;
        }

        try {
            const response = await fetch(`${this.baseURL}/${id}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to delete item');
            }

            this.showMessage('Item deleted successfully!', 'success');
            this.loadItems();
        } catch (error) {
            this.showMessage(`Error: ${error.message}`, 'error');
        }
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
