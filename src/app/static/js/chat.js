class ChatApp {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.userId = this.getUserId();
        this.md = window.markdownit();
        this.messageCount = 0;
        this.isProcessing = false;
        this.hasInitialized = false;
        this.eventHandlers = new Map(); // Track handlers to prevent duplicates
        
        this.init();
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    getUserId() {
        let userId = localStorage.getItem('cob_chat_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('cob_chat_user_id', userId);
        }
        return userId;
    }
    
    init() {
        if (this.hasInitialized) return;
        this.hasInitialized = true;
        
        this.bindEvents();
        this.loadChatHistory();
        this.initTheme();
        
        console.log('ChatApp initialized with user:', this.userId);
    }
    
    bindEvents() {
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        
        if (!messageInput || !sendButton) {
            console.error('Input elements not found!');
            return;
        }
        
        // Clear ALL existing event listeners by cloning elements
        const newSendButton = sendButton.cloneNode(true);
        sendButton.parentNode.replaceChild(newSendButton, sendButton);
        
        // Bind input events
        messageInput.oninput = () => this.autoResizeTextarea();
        messageInput.onkeydown = (e) => this.handleKeyDown(e);
        
        // Bind send button - single event listener
        newSendButton.onclick = () => {
            if (!this.isProcessing) {
                this.sendMessage();
            }
        };
        
        // Quick actions - clean binding
        document.querySelectorAll('.quick-action').forEach(action => {
            const newAction = action.cloneNode(true);
            action.parentNode.replaceChild(newAction, action);
            
            newAction.onclick = () => {
                const actionType = newAction.dataset.action;
                this.handleQuickAction(actionType);
            };
        });
        
        // Suggestion chips
        document.querySelectorAll('.chip').forEach(chip => {
            const newChip = chip.cloneNode(true);
            chip.parentNode.replaceChild(newChip, chip);
            
            newChip.onclick = () => {
                const text = newChip.dataset.text;
                messageInput.value = text;
                this.autoResizeTextarea();
                messageInput.focus();
            };
        });
        
        // Clear chat
        const clearBtn = document.getElementById('clearChat');
        if (clearBtn) {
            const newClearBtn = clearBtn.cloneNode(true);
            clearBtn.parentNode.replaceChild(newClearBtn, clearBtn);
            newClearBtn.onclick = () => this.clearChat();
        }
        
        // Toggle theme
        const themeBtn = document.getElementById('toggleTheme');
        if (themeBtn) {
            const newThemeBtn = themeBtn.cloneNode(true);
            themeBtn.parentNode.replaceChild(newThemeBtn, themeBtn);
            newThemeBtn.onclick = () => this.toggleTheme();
        }
        
        // Back to welcome
        const backBtn = document.getElementById('backToWelcome');
        if (backBtn) {
            const newBackBtn = backBtn.cloneNode(true);
            backBtn.parentNode.replaceChild(newBackBtn, backBtn);
            newBackBtn.onclick = () => this.showWelcomeScreen();
        }
    }
    
    autoResizeTextarea() {
        const textarea = document.getElementById('messageInput');
        if (!textarea) return;
        
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    }
    
    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey && !this.isProcessing) {
            e.preventDefault();
            this.sendMessage();
        }
    }
    
    handleQuickAction(actionType) {
        const actions = {
            greeting: 'Hello',
            appointment: 'I want to book an appointment',
            support: 'I need technical support',
            product: 'Tell me about your products'
        };
        
        if (actions[actionType]) {
            this.showChatScreen();
            setTimeout(() => {
                this.sendMessage(actions[actionType]);
            }, 200);
        }
    }
    
    async sendMessage(customMessage = null) {
        if (this.isProcessing) {
            console.log('Already processing...');
            return;
        }
        
        const messageInput = document.getElementById('messageInput');
        const message = customMessage || (messageInput ? messageInput.value.trim() : '');
        
        if (!message) return;
        
        // Set processing flag immediately
        this.isProcessing = true;
        
        // Clear input immediately
        if (!customMessage && messageInput) {
            messageInput.value = '';
            messageInput.style.height = 'auto';
        }
        
        try {
            // Show chat screen if not visible
            this.showChatScreen();
            
            // Add user message
            this.addMessage(message, 'user');
            
            // Show typing indicator
            this.showTypingIndicator(true);
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    user_id: this.userId,
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Hide typing indicator
            this.showTypingIndicator(false);
            
            // Add bot response
            if (data.response) {
                this.addMessage(data.response, 'bot');
                this.extractQuickReplies(data.response);
                this.saveToHistory(message, data.response);
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.showTypingIndicator(false);
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        } finally {
            // Always release the lock
            this.isProcessing = false;
        }
    }
    
    addMessage(text, sender) {
        const messagesList = document.getElementById('messagesList');
        if (!messagesList) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Parse markdown for bot messages
        if (sender === 'bot' && (text.includes('**') || text.includes('*') || text.includes('`') || text.includes('#'))) {
            try {
                contentDiv.innerHTML = this.md.render(text);
            } catch (e) {
                console.error('Error parsing markdown:', e);
                contentDiv.textContent = text;
            }
        } else {
            contentDiv.textContent = text;
        }
        
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        timestampDiv.textContent = this.getCurrentTime();
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timestampDiv);
        messagesList.appendChild(messageDiv);
        
        // Smooth scroll to bottom with delay
        requestAnimationFrame(() => {
            messagesList.scrollTop = messagesList.scrollHeight;
        });
        
        this.messageCount++;
    }
    
    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    showTypingIndicator(show) {
        const indicator = document.getElementById('typingIndicator');
        if (!indicator) return;
        
        indicator.style.display = show ? 'flex' : 'none';
        
        if (show) {
            const messagesList = document.getElementById('messagesList');
            if (messagesList) {
                requestAnimationFrame(() => {
                    messagesList.scrollTop = messagesList.scrollHeight;
                });
            }
        }
    }
    
    extractQuickReplies(response) {
        const quickRepliesContainer = document.getElementById('quickReplies');
        if (!quickRepliesContainer) return;
        
        quickRepliesContainer.innerHTML = '';
        
        if (!response) return;
        
        const lines = response.split('\n');
        const quickReplyLines = lines.filter(line => {
            const trimmed = line.trim();
            return (/^[1-6]\.\s+.+$/.test(trimmed) || 
                    /^•\s+.+$/.test(trimmed) || 
                    /^-\s+.+$/.test(trimmed) ||
                    /^\*\s+.+$/.test(trimmed));
        });
        
        if (quickReplyLines.length > 0) {
            quickReplyLines.slice(0, 6).forEach(line => {
                const button = document.createElement('button');
                button.className = 'quick-reply-btn';
                button.type = 'button';
                
                let text = line.trim()
                    .replace(/^[1-6]\.\s+/, '')
                    .replace(/^•\s+/, '')
                    .replace(/^-\s+/, '')
                    .replace(/^\*\s+/, '')
                    .replace(/\*\*/g, '')
                    .trim();
                
                button.textContent = text;
                
                button.onclick = () => {
                    if (!this.isProcessing) {
                        const numberMatch = line.match(/^([1-6])\./);
                        if (numberMatch) {
                            this.sendMessage(numberMatch[1]);
                        } else {
                            this.sendMessage(text);
                        }
                    }
                };
                
                quickRepliesContainer.appendChild(button);
            });
        }
    }
    
    saveToHistory(userMessage, botResponse) {
        try {
            const history = JSON.parse(localStorage.getItem('cob_chat_history') || '[]');
            
            history.push({
                user: userMessage,
                bot: botResponse,
                timestamp: new Date().toISOString()
            });
            
            if (history.length > 50) {
                history.splice(0, history.length - 50);
            }
            
            localStorage.setItem('cob_chat_history', JSON.stringify(history));
        } catch (e) {
            console.error('Error saving to history:', e);
        }
    }
    
    loadChatHistory() {
        try {
            const history = JSON.parse(localStorage.getItem('cob_chat_history') || '[]');
            
            if (history.length > 0) {
                this.showChatScreen();
                
                setTimeout(() => {
                    history.forEach(entry => {
                        this.addMessage(entry.user, 'user');
                        this.addMessage(entry.bot, 'bot');
                    });
                }, 100);
            }
        } catch (e) {
            console.error('Error loading chat history:', e);
        }
    }
    
    clearChat() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            localStorage.removeItem('cob_chat_history');
            
            const messagesList = document.getElementById('messagesList');
            const quickReplies = document.getElementById('quickReplies');
            if (messagesList) messagesList.innerHTML = '';
            if (quickReplies) quickReplies.innerHTML = '';
            
            this.messageCount = 0;
            this.showWelcomeScreen();
        }
    }
    
    toggleTheme() {
        const body = document.body;
        const themeBtn = document.getElementById('toggleTheme');
        const icon = themeBtn ? themeBtn.querySelector('i') : null;
        
        if (body.classList.contains('dark-mode')) {
            body.classList.remove('dark-mode');
            if (icon) icon.className = 'fas fa-moon';
            localStorage.setItem('cob_chat_theme', 'light');
        } else {
            body.classList.add('dark-mode');
            if (icon) icon.className = 'fas fa-sun';
            localStorage.setItem('cob_chat_theme', 'dark');
        }
    }
    
    showChatScreen() {
        const welcomeScreen = document.getElementById('welcomeScreen');
        const chatMessages = document.getElementById('chatMessages');
        
        if (welcomeScreen) welcomeScreen.style.display = 'none';
        if (chatMessages) {
            chatMessages.style.display = 'flex';
            
            // Ensure messages list is scrolled to bottom
            const messagesList = document.getElementById('messagesList');
            if (messagesList) {
                requestAnimationFrame(() => {
                    messagesList.scrollTop = messagesList.scrollHeight;
                });
            }
        }
        
        setTimeout(() => {
            const messageInput = document.getElementById('messageInput');
            if (messageInput) messageInput.focus();
        }, 100);
    }
    
    showWelcomeScreen() {
        const welcomeScreen = document.getElementById('welcomeScreen');
        const chatMessages = document.getElementById('chatMessages');
        
        if (welcomeScreen) welcomeScreen.style.display = 'flex';
        if (chatMessages) chatMessages.style.display = 'none';
    }
    
    initTheme() {
        try {
            const savedTheme = localStorage.getItem('cob_chat_theme') || 'light';
            const themeBtn = document.getElementById('toggleTheme');
            const icon = themeBtn ? themeBtn.querySelector('i') : null;
            
            if (savedTheme === 'dark') {
                document.body.classList.add('dark-mode');
                if (icon) icon.className = 'fas fa-sun';
            }
        } catch (e) {
            console.error('Error initializing theme:', e);
        }
    }
}

// Initialize only once when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeChatApp);
} else {
    initializeChatApp();
}

function initializeChatApp() {
    if (!window.chatApp && !window.chatAppInitialized) {
        window.chatAppInitialized = true;
        window.chatApp = new ChatApp();
        console.log('COB Chat App initialized successfully');
    }
}