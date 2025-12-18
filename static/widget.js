(function() {
    // ----------------------------------------------------
    // 1. CONFIGURATION
    // ----------------------------------------------------
    const scriptTag = document.currentScript;
    
    const USER_ID = scriptTag.getAttribute("data-user-id"); 
    const API_URL = scriptTag.getAttribute("data-api-url");
    const THEME_COLOR = scriptTag.getAttribute("data-theme-color") || "#007bff";

    if (!USER_ID || !API_URL) {
        console.error("OmniAgent Widget Error: data-user-id or data-api-url is missing!");
        return;
    }

    const CHAT_SESSION_ID = "omni_session_" + Math.random().toString(36).slice(2, 11); 

    // ----------------------------------------------------
    // 2. STYLES
    // ----------------------------------------------------
    const style = document.createElement('style');
    style.innerHTML = `
        #omni-widget-container {
            position: fixed; bottom: 20px; right: 20px; z-index: 999999; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        #omni-chat-btn {
            background: ${THEME_COLOR}; color: white; border: none; padding: 15px; border-radius: 50%;
            cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.4); width: 60px; height: 60px; font-size: 24px;
            display: flex; align-items: center; justify-content: center; transition: transform 0.2s;
        }
        #omni-chat-btn:hover { transform: scale(1.1); }
        #omni-chat-window {
            display: none; width: 350px; height: 500px; background: white; border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5); flex-direction: column; overflow: hidden;
            margin-bottom: 15px; border: 1px solid #ddd;
        }
        #omni-header { 
            background: ${THEME_COLOR}; color: white; padding: 15px; font-weight: 600; display: flex; 
            justify-content: space-between; align-items: center;
        }
        #omni-messages { flex: 1; padding: 15px; overflow-y: auto; background: #f9f9f9; display: flex; flex-direction: column; }
        #omni-input-area { display: flex; border-top: 1px solid #ddd; background: white; }
        #omni-input { flex: 1; padding: 12px; border: none; outline: none; font-size: 14px; }
        #omni-send { background: transparent; border: none; color: ${THEME_COLOR}; font-weight: bold; cursor: pointer; padding: 0 15px; font-size: 20px; }
        .omni-msg { margin: 8px 0; padding: 10px 14px; border-radius: 15px; max-width: 85%; font-size: 14px; word-wrap: break-word; }
        .omni-msg.user { background: ${THEME_COLOR}; color: white; align-self: flex-end; border-bottom-right-radius: 2px; }
        .omni-msg.bot { background: #eef2f7; color: #333; align-self: flex-start; border-bottom-left-radius: 2px; border: 1px solid #d1d9e6; }
    `;
    document.head.appendChild(style);

    // ----------------------------------------------------
    // 3. UI LOGIC (Pehle Define Karen)
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
    // 4. HTML STRUCTURE
    // ----------------------------------------------------
    const container = document.createElement('div');
    container.id = 'omni-widget-container';

    container.innerHTML = `
        <div id="omni-chat-window">
            <div id="omni-header">
                <span>AI Support Agent</span>
                <span style="cursor:pointer; font-size: 22px; line-height: 20px;" onclick="window.toggleOmniChat()">×</span>
            </div>
            <div id="omni-messages"></div>
            <div id="omni-input-area">
                <input type="text" id="omni-input" placeholder="Ask me anything..." autocomplete="off" />
                <button id="omni-send">➤</button>
            </div>
        </div>
        <button id="omni-chat-btn" onclick="window.toggleOmniChat()">💬</button>
    `;

    document.body.appendChild(container);

    // ----------------------------------------------------
    // 5. CHAT FUNCTIONALITY
    // ----------------------------------------------------
    const inputField = document.getElementById('omni-input');
    const sendButton = document.getElementById('omni-send');
    const messagesContainer = document.getElementById('omni-messages');

    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `omni-msg ${sender}`;
        div.innerHTML = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color:inherit; text-decoration:underline;">$1</a>');
        messagesContainer.appendChild(div);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async function sendMessage() {
        const text = inputField.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        inputField.value = '';
        
        // Show Loading State
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'omni-msg bot';
        loadingDiv.innerHTML = '...';
        messagesContainer.appendChild(loadingDiv);

        try {
            const response = await fetch(`${API_URL}/api/v1/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    session_id: CHAT_SESSION_ID,
                    user_id: USER_ID 
                })
            });
            const data = await response.json();
            messagesContainer.removeChild(loadingDiv);
            addMessage(data.response || data.message || "No response received", 'bot'); 
        } catch (error) {
            messagesContainer.removeChild(loadingDiv);
            addMessage("Connection error. Please try again.", 'bot');
            console.error("OmniAgent API Error:", error);
        }
    }

    sendButton.addEventListener('click', sendMessage);
    inputField.addEventListener('keypress', (e) => { 
        if(e.key === 'Enter') { sendMessage(); }
    });

    // Welcome Message
    setTimeout(() => {
        addMessage("Hello! How can I assist you with the SDD-RI Book today?", "bot");
    }, 1000);

})();