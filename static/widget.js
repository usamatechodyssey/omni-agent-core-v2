(function() {
    // ----------------------------------------------------
    // 1. CONFIGURATION: Security & Metadata
    // ----------------------------------------------------
    const scriptTag = document.currentScript;
    
    // Ab hum User ID nahi, balki secure API Key mangenge 🔑
    const API_KEY = scriptTag.getAttribute("data-api-key"); 
    const API_URL = scriptTag.getAttribute("data-api-url");
    const THEME_COLOR = scriptTag.getAttribute("data-theme-color") || "#FF0000"; // Default Red for your theme

    if (!API_KEY || !API_URL) {
        console.error("OmniAgent Security Error: data-api-key or data-api-url is missing!");
        return;
    }

    const CHAT_SESSION_ID = "omni_session_" + Math.random().toString(36).slice(2, 11); 

    // ----------------------------------------------------
    // 2. STYLES: UI & Responsive Design
    // ----------------------------------------------------
    const style = document.createElement('style');
    style.innerHTML = `
        #omni-widget-container {
            position: fixed; bottom: 20px; right: 20px; z-index: 999999; 
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        #omni-chat-btn {
            background: ${THEME_COLOR}; color: white; border: none; padding: 15px; border-radius: 50%;
            cursor: pointer; box-shadow: 0 4px 15px rgba(0,0,0,0.3); width: 60px; height: 60px; font-size: 24px;
            display: flex; align-items: center; justify-content: center; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        #omni-chat-btn:hover { transform: scale(1.1) rotate(5deg); }
        
        #omni-chat-window {
            display: none; width: 370px; height: 550px; background: white; border-radius: 16px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.2); flex-direction: column; overflow: hidden;
            margin-bottom: 20px; border: 1px solid #f0f0f0; animation: omniSlideUp 0.4s ease;
        }
        
        @keyframes omniSlideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        #omni-header { 
            background: ${THEME_COLOR}; color: white; padding: 18px; font-weight: 600; display: flex; 
            justify-content: space-between; align-items: center; letter-spacing: 0.5px;
        }
        #omni-messages { flex: 1; padding: 20px; overflow-y: auto; background: #ffffff; display: flex; flex-direction: column; }
        #omni-input-area { display: flex; border-top: 1px solid #eee; background: #fff; padding: 10px; }
        #omni-input { flex: 1; padding: 12px; border: 1px solid #eee; border-radius: 25px; outline: none; font-size: 14px; background: #f8f9fa; }
        #omni-send { background: transparent; border: none; color: ${THEME_COLOR}; font-weight: bold; cursor: pointer; padding: 0 12px; font-size: 22px; }
        
        .omni-msg { margin: 10px 0; padding: 12px 16px; border-radius: 18px; max-width: 85%; font-size: 14px; line-height: 1.5; word-wrap: break-word; position: relative; }
        .omni-msg.user { background: ${THEME_COLOR}; color: white; align-self: flex-end; border-bottom-right-radius: 2px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .omni-msg.bot { background: #f0f2f5; color: #1c1e21; align-self: flex-start; border-bottom-left-radius: 2px; }
        
        /* Custom Scrollbar */
        #omni-messages::-webkit-scrollbar { width: 5px; }
        #omni-messages::-webkit-scrollbar-track { background: #f1f1f1; }
        #omni-messages::-webkit-scrollbar-thumb { background: #ccc; border-radius: 10px; }
    `;
    document.head.appendChild(style);

    // ----------------------------------------------------
    // 3. UI LOGIC: Global Toggle Function
    // ----------------------------------------------------
    window.toggleOmniChat = function() {
        const win = document.getElementById('omni-chat-window');
        if (!win) return;
        const isVisible = win.style.display === 'flex';
        win.style.display = isVisible ? 'none' : 'flex';
        if (!isVisible) {
            document.getElementById('omni-input').focus();
        }
    };

    // ----------------------------------------------------
    // 4. HTML STRUCTURE: Dynamic Insertion
    // ----------------------------------------------------
    const container = document.createElement('div');
    container.id = 'omni-widget-container';

    container.innerHTML = `
        <div id="omni-chat-window">
            <div id="omni-header">
                <div style="display:flex; align-items:center; gap:10px;">
                    <div style="width:10px; height:10px; background:#2ecc71; border-radius:50%;"></div>
                    <span>AI Knowledge Assistant</span>
                </div>
                <span style="cursor:pointer; font-size: 24px; font-weight:300;" onclick="window.toggleOmniChat()">×</span>
            </div>
            <div id="omni-messages"></div>
            <div id="omni-input-area">
                <input type="text" id="omni-input" placeholder="Type a message..." autocomplete="off" />
                <button id="omni-send">➤</button>
            </div>
        </div>
        <button id="omni-chat-btn" onclick="window.toggleOmniChat()">💬</button>
    `;

    document.body.appendChild(container);

    // ----------------------------------------------------
    // 5. CHAT ENGINE: Fetch & Security Headers
    // ----------------------------------------------------
    const inputField = document.getElementById('omni-input');
    const sendButton = document.getElementById('omni-send');
    const messagesContainer = document.getElementById('omni-messages');

    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `omni-msg ${sender}`;
        // URL auto-linking logic
        div.innerHTML = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color:inherit; text-decoration:underline;">$1</a>');
        messagesContainer.appendChild(div);
        messagesContainer.scrollTo({ top: messagesContainer.scrollHeight, behavior: 'smooth' });
    }

    async function sendMessage() {
        const text = inputField.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        inputField.value = '';
        
        // Loading dots logic
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'omni-msg bot';
        loadingDiv.innerHTML = '<span class="omni-dots">...</span>';
        messagesContainer.appendChild(loadingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            const response = await fetch(`${API_URL}/api/v1/chat`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: text,
                    session_id: CHAT_SESSION_ID,
                    api_key: API_KEY // 🔑 Secure Auth
                })
            });

            const data = await response.json();
            messagesContainer.removeChild(loadingDiv);

            if (response.status === 401) {
                addMessage("🚫 Security Error: Invalid API Key.", 'bot');
            } else if (response.status === 403) {
                addMessage("🚫 Security Error: Domain not authorized.", 'bot');
            } else {
                addMessage(data.response || "I couldn't process that. Please try again.", 'bot'); 
            }

        } catch (error) {
            if (loadingDiv.parentNode) messagesContainer.removeChild(loadingDiv);
            addMessage("📡 Connection lost. Is the AI server online?", 'bot');
            console.error("OmniAgent API Error:", error);
        }
    }

    // Event Listeners
    sendButton.addEventListener('click', sendMessage);
    inputField.addEventListener('keypress', (e) => { 
        if(e.key === 'Enter') { sendMessage(); }
    });

    // Initial Welcome (AI Persona)
    setTimeout(() => {
        addMessage("Hello! I am your AI assistant. How can I help you today?", "bot");
    }, 1500);

})();