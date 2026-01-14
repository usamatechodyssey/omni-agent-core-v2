(function() {
    // ----------------------------------------------------
    // 1. CONFIGURATION: Security & Metadata
    // ----------------------------------------------------
    const scriptTag = document.currentScript;
    
    // Auth & Config
    const API_KEY = scriptTag.getAttribute("data-api-key"); 
    const API_URL = scriptTag.getAttribute("data-api-url");
    const THEME_COLOR = scriptTag.getAttribute("data-theme-color") || "#0084FF"; 

    if (!API_KEY || !API_URL) {
        console.error("OmniAgent Security Error: data-api-key or data-api-url is missing!");
        return;
    }

    const CHAT_SESSION_ID = "omni_session_" + Math.random().toString(36).slice(2, 11); 

    // ----------------------------------------------------
    // 2. STYLES: UI & Responsive Design (Tabs + Camera)
    // ----------------------------------------------------
    const style = document.createElement('style');
    style.innerHTML = `
        #omni-widget-container {
            position: fixed; bottom: 20px; right: 20px; z-index: 999999; 
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        #omni-chat-btn {
            background: ${THEME_COLOR}; color: white; border: none; padding: 15px; border-radius: 50%;
            cursor: pointer; box-shadow: 0 4px 15px rgba(0,0,0,0.3); width: 60px; height: 60px; font-size: 28px;
            display: flex; align-items: center; justify-content: center; transition: all 0.3s;
        }
        #omni-chat-btn:hover { transform: scale(1.1); }
        
        #omni-window {
            display: none; width: 380px; height: 600px; background: white; border-radius: 16px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.25); flex-direction: column; overflow: hidden;
            margin-bottom: 20px; animation: omniSlideUp 0.3s ease; border: 1px solid #e0e0e0;
        }
        
        @keyframes omniSlideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* --- Header & Tabs --- */
        #omni-header { background: ${THEME_COLOR}; padding: 15px; color: white; }
        .omni-title { font-weight: bold; font-size: 16px; display: flex; align-items: center; gap: 8px; }
        .omni-close { cursor: pointer; float: right; font-size: 24px; line-height: 16px; }

        .omni-tabs { display: flex; background: #f1f1f1; border-bottom: 1px solid #ddd; }
        .omni-tab { flex: 1; padding: 12px; text-align: center; cursor: pointer; font-size: 14px; font-weight: 600; color: #555; transition: 0.2s; }
        .omni-tab.active { background: white; color: ${THEME_COLOR}; border-bottom: 3px solid ${THEME_COLOR}; }

        /* --- Content Areas --- */
        .omni-view { display: none; flex: 1; flex-direction: column; overflow: hidden; }
        .omni-view.active { display: flex; }

        /* --- Chat View --- */
        #omni-messages { flex: 1; padding: 15px; overflow-y: auto; background: #f9f9f9; display: flex; flex-direction: column; gap: 10px; }
        .omni-msg { padding: 10px 14px; border-radius: 12px; max-width: 80%; font-size: 14px; line-height: 1.4; }
        .omni-msg.user { background: ${THEME_COLOR}; color: white; align-self: flex-end; border-bottom-right-radius: 2px; }
        .omni-msg.bot { background: #e9eff5; color: #333; align-self: flex-start; border-bottom-left-radius: 2px; }
        
        #omni-input-area { display: flex; border-top: 1px solid #eee; padding: 10px; background: white; }
        #omni-input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 20px; outline: none; }
        #omni-send { background: none; border: none; color: ${THEME_COLOR}; font-size: 20px; cursor: pointer; padding-left: 10px; }

        /* --- Visual Search View --- */
        #omni-visual-area { flex: 1; padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; overflow-y: auto; text-align: center; }
        #omni-upload-box { 
            border: 2px dashed #ccc; border-radius: 12px; padding: 30px; margin-bottom: 20px; 
            width: 80%; cursor: pointer; transition: 0.2s; background: #fafafa;
        }
        #omni-upload-box:hover { border-color: ${THEME_COLOR}; background: #f0f7ff; }
        #omni-file-input { display: none; }
        
        .omni-result-card { 
            display: flex; align-items: center; gap: 10px; background: white; border: 1px solid #eee; 
            padding: 10px; border-radius: 8px; width: 100%; margin-bottom: 10px; text-align: left;
            transition: 0.2s; text-decoration: none; color: inherit;
        }
        .omni-result-card:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .omni-result-img { width: 60px; height: 60px; object-fit: cover; border-radius: 6px; }
        
        .omni-loader { border: 3px solid #f3f3f3; border-top: 3px solid ${THEME_COLOR}; border-radius: 50%; width: 24px; height: 24px; animation: spin 1s linear infinite; margin: 20px auto; display: none; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    `;
    document.head.appendChild(style);

    // ----------------------------------------------------
    // 3. HTML STRUCTURE
    // ----------------------------------------------------
    const container = document.createElement('div');
    container.id = 'omni-widget-container';

    container.innerHTML = `
        <div id="omni-window">
            <div id="omni-header">
                <span class="omni-close" onclick="window.toggleOmni()">×</span>
                <div class="omni-title">
                    <span>🤖 AI Assistant</span>
                </div>
            </div>
            
            <div class="omni-tabs">
                <div class="omni-tab active" onclick="window.switchTab('chat')">💬 Chat</div>
                <div class="omni-tab" onclick="window.switchTab('visual')">📷 Visual Search</div>
            </div>

            <!-- CHAT VIEW -->
            <div id="omni-chat-view" class="omni-view active">
                <div id="omni-messages"></div>
                <div id="omni-input-area">
                    <input type="text" id="omni-input" placeholder="Ask anything..." autocomplete="off" />
                    <button id="omni-send">➤</button>
                </div>
            </div>

            <!-- VISUAL VIEW -->
            <div id="omni-visual-view" class="omni-view">
                <div id="omni-visual-area">
                    <div id="omni-upload-box" onclick="document.getElementById('omni-file-input').click()">
                        <div style="font-size:40px; margin-bottom:10px;">📤</div>
                        <p style="margin:0; color:#666;">Click to Upload Image</p>
                        <p style="margin:0; font-size:12px; color:#999;">Find similar products</p>
                    </div>
                    <input type="file" id="omni-file-input" accept="image/*">
                    <div id="omni-visual-loader" class="omni-loader"></div>
                    <div id="omni-visual-results" style="width:100%;"></div>
                </div>
            </div>
        </div>
        <button id="omni-chat-btn" onclick="window.toggleOmni()">💬</button>
    `;

    document.body.appendChild(container);

    // ----------------------------------------------------
    // 4. UI LOGIC (Toggle & Tabs)
    // ----------------------------------------------------
    window.toggleOmni = function() {
        const win = document.getElementById('omni-window');
        const isVisible = win.style.display === 'flex';
        win.style.display = isVisible ? 'none' : 'flex';
    };

    window.switchTab = function(tab) {
        document.querySelectorAll('.omni-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.omni-view').forEach(v => v.classList.remove('active'));

        if (tab === 'chat') {
            document.querySelector('.omni-tabs .omni-tab:nth-child(1)').classList.add('active');
            document.getElementById('omni-chat-view').classList.add('active');
        } else {
            document.querySelector('.omni-tabs .omni-tab:nth-child(2)').classList.add('active');
            document.getElementById('omni-visual-view').classList.add('active');
        }
    };

    // ----------------------------------------------------
    // 5. CHAT ENGINE
    // ----------------------------------------------------
    const chatInput = document.getElementById('omni-input');
    const sendBtn = document.getElementById('omni-send');
    const msgContainer = document.getElementById('omni-messages');

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        addMsg(text, 'user');
        chatInput.value = '';
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'omni-msg bot';
        loadingDiv.innerHTML = '...';
        msgContainer.appendChild(loadingDiv);
        msgContainer.scrollTop = msgContainer.scrollHeight;

        try {
            const response = await fetch(`${API_URL}/api/v1/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    session_id: CHAT_SESSION_ID,
                    api_key: API_KEY // Auth
                })
            });
            
            msgContainer.removeChild(loadingDiv);
            const data = await response.json();
            
            if (response.ok) {
                addMsg(data.response, 'bot');
            } else {
                addMsg("⚠️ Error: " + (data.detail || "Server error"), 'bot');
            }

        } catch (e) {
            if(loadingDiv.parentNode) msgContainer.removeChild(loadingDiv);
            addMsg("📡 Connection Error", 'bot');
        }
    }

    function addMsg(text, sender) {
        const div = document.createElement('div');
        div.className = `omni-msg ${sender}`;
        div.innerText = text; // Secure text insertion
        msgContainer.appendChild(div);
        msgContainer.scrollTop = msgContainer.scrollHeight;
    }

    sendBtn.onclick = sendMessage;
    chatInput.onkeypress = (e) => { if(e.key === 'Enter') sendMessage(); };

    // ----------------------------------------------------
    // 6. VISUAL SEARCH ENGINE
    // ----------------------------------------------------
    const fileInput = document.getElementById('omni-file-input');
    const visualLoader = document.getElementById('omni-visual-loader');
    const visualResults = document.getElementById('omni-visual-results');

    fileInput.onchange = async function() {
        const file = fileInput.files[0];
        if (!file) return;

        visualLoader.style.display = 'block';
        visualResults.innerHTML = '';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${API_URL}/api/v1/visual/search`, {
                method: 'POST',
                headers: { 
                    'x-api-key': API_KEY // Header Auth ✅
                },
                body: formData
            });

            const data = await response.json();
            visualLoader.style.display = 'none';

            if (!response.ok) {
                visualResults.innerHTML = `<p style="color:red; margin-top:20px;">Error: ${data.detail}</p>`;
                return;
            }

            if (!data.results || data.results.length === 0) {
                visualResults.innerHTML = '<p style="color:#777; margin-top:20px;">No similar products found.</p>';
                return;
            }

            // Render Results
            data.results.forEach(item => {
                const score = (item.similarity * 100).toFixed(0);
                const el = document.createElement('a');
                el.className = 'omni-result-card';
                el.href = `/product/${item.slug || '#'}`; // Dynamic link
                el.target = '_blank';
                el.innerHTML = `
                    <img src="${item.image_path}" class="omni-result-img" onerror="this.src='https://via.placeholder.com/60'">
                    <div>
                        <div style="font-weight:bold; font-size:14px;">Product Match</div>
                        <div style="font-size:12px; color:#27ae60;">${score}% Similarity</div>
                    </div>
                `;
                visualResults.appendChild(el);
            });

        } catch (e) {
            visualLoader.style.display = 'none';
            visualResults.innerHTML = '<p style="color:red;">Connection Failed</p>';
        }
    };

    // Initial Hello
    setTimeout(() => addMsg("Hi! I can help you find products by chatting or uploading an image.", "bot"), 1000);

})();