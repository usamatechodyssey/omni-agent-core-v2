// frontend/visual_search_test.js

const VisualSearchTester = {
    config: {
        apiEndpoint: "",
    },
    elements: {},
    
    init: function(apiEndpoint) {
        this.config.apiEndpoint = apiEndpoint;
        this.elements = {
            apiKeyInput: document.getElementById('api-key-input'), // ID Changed
            fileInput: document.getElementById('image-upload-input'),
            searchButton: document.getElementById('search-button'),
            authStatus: document.getElementById('auth-status'),
            loader: document.getElementById('loader'),
            resultsContainer: document.getElementById('search-results-container'),
        };
        
        // Listeners
        this.elements.apiKeyInput.addEventListener('input', this._updateButtonState.bind(this));
        this.elements.fileInput.addEventListener('change', this._updateButtonState.bind(this));
        this.elements.searchButton.addEventListener('click', this._handleSearch.bind(this));
        
        this._updateButtonState();
    },
    
    _updateButtonState: function() {
        const apiKey = this.elements.apiKeyInput.value.trim();
        const file = this.elements.fileInput.files[0];
        
        // API Key 'omni_' se shuru hoti hai aur approx 30-40 chars hoti hai
        const isValidKey = apiKey.length > 20 && apiKey.startsWith("omni_");
        const canSearch = isValidKey && file;
        
        this.elements.searchButton.disabled = !canSearch;
        
        if (isValidKey) {
            this.elements.authStatus.style.borderLeftColor = '#27ae60';
            this.elements.authStatus.innerHTML = '<p style="color: #27ae60; margin:0"><strong>Status:</strong> Valid API Key Format ✅</p>';
        } else {
            this.elements.authStatus.style.borderLeftColor = '#bdc3c7';
            this.elements.authStatus.innerHTML = '<p style="color: #7f8c8d; margin:0"><strong>Status:</strong> Waiting for valid API Key...</p>';
        }
    },

    // --- 🔥 MAIN SEARCH LOGIC (API KEY UPDATE) 🔥 ---
    _handleSearch: async function() {
        const apiKey = this.elements.apiKeyInput.value.trim();
        const file = this.elements.fileInput.files[0];

        if (!apiKey || !file) return;

        this.elements.loader.style.display = 'block';
        this.elements.searchButton.disabled = true; // Prevent double click
        this.elements.resultsContainer.innerHTML = '';

        const formData = new FormData();
        formData.append('file', file);

        try {
            console.log("Sending request to:", this.config.apiEndpoint);
            
            const response = await fetch(this.config.apiEndpoint, {
                method: 'POST',
                headers: { 
                    // ✅ CHANGE: Use 'x-api-key' instead of 'Authorization'
                    'x-api-key': apiKey,
                    'Accept': 'application/json'
                    // Note: 'Content-Type' header mat lagana jab FormData bhej rahe ho, browser khud boundary set karega.
                },
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                // Handle specific Auth errors
                if (response.status === 401 || response.status === 403) {
                    throw new Error("Authentication Failed! Please check your API Key or Domain Settings.");
                }
                const errorDetail = data.detail || data.message || "Unknown server error";
                throw new Error(`Error ${response.status}: ${errorDetail}`);
            }

            this._renderResults(data.results);

        } catch (error) {
            this.elements.resultsContainer.innerHTML = `
                <div style="text-align:center; padding: 20px;">
                    <p style="color: #e74c3c; font-weight: bold; font-size: 1.2em;">❌ Search Failed</p>
                    <p style="color: #555;">${error.message}</p>
                </div>`;
            console.error("Visual Search Error:", error);
        } finally {
            this.elements.loader.style.display = 'none';
            this.elements.searchButton.disabled = false;
        }
    },

    _renderResults: function(results) {
        const container = this.elements.resultsContainer;
        container.innerHTML = '';

        if (!results || results.length === 0) {
            container.innerHTML = '<p class="info-message">🤷‍♂️ No matching products found.</p>';
            return;
        }

        results.forEach(item => {
            const card = document.createElement('div');
            card.className = 'result-card';
            
            const similarityScore = (item.similarity * 100).toFixed(1);
            const slug = item.slug || "#";
            
            // Image Fallback logic
            const imgUrl = item.image_path || "https://via.placeholder.com/200?text=No+Image";

            card.innerHTML = `
                <a href="/product/${slug}" target="_blank" style="text-decoration: none; color: inherit;">
                    <img src="${imgUrl}" alt="Product Image" onerror="this.src='https://via.placeholder.com/200?text=Error'">
                    <div class="card-content">
                        <span class="similarity-badge">${similarityScore}% Match</span>
                        <p style="margin-top: 10px; font-size: 0.9em; color: #555;">ID: ${item.product_id}</p>
                    </div>
                </a>
            `;
            container.appendChild(card);
        });
    }
};