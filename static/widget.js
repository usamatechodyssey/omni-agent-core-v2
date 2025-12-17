(function() {
    // ----------------------------------------------------
    // 1. CONFIGURATION: Script Tag se values uthana
    // ----------------------------------------------------
    const scriptTag = document.currentScript;
    
    const USER_ID = scriptTag.getAttribute("data-user-id"); 
    const API_URL = scriptTag.getAttribute("data-api-url");
    const THEME_COLOR = scriptTag.getAttribute("data-theme-color") || "#007bff";

    if (!USER_ID || !API_URL) {
        console.error("OmniAgent Widget Error: data-user-id or data-api-url is missing!");
        return;
    }

    // Modern way to generate unique ID (Fixing substr deprecated warning)
    const CHAT_SESSION_ID = "omni_session_" + Math.random().toString(36).slice(2, 11); 

    // ----------------------------------------------------
    // 2. STYLES: UI Design aur Position
    // ----------------------------------------------------
    const style = document.createElement('style');
    style.innerHTML = `
        #omni-widget-container {
            position: fixed; bottom: 20px; right: 20px; z-index: 9999; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            transition: all 0.3s;
        }
        #omni-chat-btn {
            background: ${THEME_COLOR}; color: white; border: none; padding: 15px; border-radius: 50%;
            cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.4); width: 60px; height: 60px; font-size: 24px;
            display: flex; align-items: center; justify-content: center;
        }
        #omni-chat-window {
            display: none; width: 350px; height: 500px; background: white; border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5); flex-direction: column; overflow: hidden;
            margin-bottom: 15px; transform-origin: bottom right; animation: fadeIn 0.3s ease-out;
        }
        #omni-header { 
            background: ${THEME_COLOR}; color: white; padding: 15px; font-weight: 600; display: flex; 
            justify-content: space-between; align-items: center; border-radius: 10px 10px 0 0; 
        }
        #omni-messages { flex: 1; padding: 10px; overflow-y: auto; background: #f0f0f0; }
        #omni-input-area { display: flex; border-top: 1px solid #ddd; }
        #omni-input { flex: 1; padding: 12px; border: none; outline: none; font-size: 14px; }
        #omni-send { background: white; border: none; color: ${THEME_COLOR}; font-weight: bold; cursor: pointer; padding: 0 15px; font-size: 18px; }
        .omni-msg { margin: 8px 0; padding: 10px 15px; border-radius: 15px; max-width: 80%; font-size: 14px; line-height: 1.4; }
        .omni-msg.user { background: ${THEME_COLOR}; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .omni-msg.bot { background: #e8e8e8; color: #333; margin-right: auto; border-bottom-left-radius: 2px; }
        
        @keyframes fadeIn { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }
    `;
    document.head.appendChild(style);

    // ----------------------------------------------------
    // 3. HTML Structure Banao
    // ----------------------------------------------------
    const container = document.createElement('div');
    container.id = 'omni-widget-container';

    const chatWindow = document.createElement('div');
    chatWindow.id = 'omni-chat-window';
    chatWindow.innerHTML = `
        <div id="omni-header">
            <span>Customer Support</span>
            <span style="cursor:pointer; font-size: 18px;" onclick="window.toggleOmniChat()">—</span>
        </div>
        <div id="omni-messages"></div>
        <div id="omni-input-area">
            <input type="text" id="omni-input" placeholder="Type your query..." />
            <button id="omni-send">➤</button>
        </div>
    `;

    const chatBtn = document.createElement('button');
    chatBtn.id = 'omni-chat-btn';
    chatBtn.innerHTML = '💬';
    
    // onClick ko addEventListener se theek kiya
    chatBtn.addEventListener('click', toggleOmniChat); 

    container.appendChild(chatWindow);
    container.appendChild(chatBtn);
    document.body.appendChild(container);

    // ----------------------------------------------------
    // 4. Logic Functions (Modern Event Listeners)
    // ----------------------------------------------------
    
    const inputField = document.getElementById('omni-input');
    const sendButton = document.getElementById('omni-send');

    window.toggleOmniChat = function() {
        const win = document.getElementById('omni-chat-window');
        const isVisible = win.style.display === 'flex';
        win.style.display = isVisible ? 'none' : 'flex';
        if (!isVisible) {
            inputField.focus();
        }
    };

    function addMessage(text, sender) {
        const msgs = document.getElementById('omni-messages');
        const div = document.createElement('div');
        div.className = `omni-msg ${sender}`;
        div.innerHTML = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color:white; text-decoration:underline;">$1</a>');
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
    }

    async function sendMessage() {
        const originalBtnText = sendButton.innerHTML;
        const text = inputField.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        inputField.value = '';
        inputField.disabled = true;
        sendButton.innerHTML = '...';
        sendButton.disabled = true;

        try {
            // Backend API Call
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
            addMessage(data.response, 'bot'); 
        } catch (error) {
            addMessage("Error: Could not connect to the Agent.", 'bot');
            console.error("OmniAgent API Error:", error);
        } finally {
            inputField.disabled = false;
            sendButton.innerHTML = originalBtnText;
            sendButton.disabled = false;
            inputField.focus();
        }
    }

    // Modern Event Listeners (Fixing deprecated 'onkeypress')
    sendButton.addEventListener('click', sendMessage);
    inputField.addEventListener('keypress', (e) => { 
        if(e.key === 'Enter') {
            sendMessage(); 
            e.preventDefault(); // Enter key ka default action roko
        }
    });
})();