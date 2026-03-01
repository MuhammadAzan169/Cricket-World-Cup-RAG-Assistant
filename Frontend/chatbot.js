/* =============================================
   Cricket AI Chatbot — Full Page Interface
   Connected to FastAPI Backend
   ============================================= */

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : '';

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide icons
  lucide.createIcons();
  
  // Initialize chatbot
  initChatbot();
  
  // Focus on input
  setTimeout(() => {
    document.getElementById('chatbot-input')?.focus();
  }, 100);
});

function initChatbot() {
  const messagesContainer = document.getElementById('chat-messages');
  const form = document.getElementById('chatbot-form');
  const input = document.getElementById('chatbot-input');
  const sendBtn = document.getElementById('send-btn');
  const suggestionsContainer = document.getElementById('chat-suggestions');
  
  let isProcessing = false;
  
  // Quick action suggestions
  const quickActionsData = [
    'Who won the 2011 World Cup?',
    'Compare Kohli and Ponting',
    'Tell me about the 2019 final',
    "Dhoni's World Cup career",
    'Top run scorers across all WCs',
    'Best bowling figures',
    '2023 World Cup summary',
    'Most sixes in World Cups'
  ];
  
  // Initialize quick actions
  renderQuickActions();
  
  // Close button for welcome message
  const welcomeMsg = document.getElementById('welcome-message');
  const welcomeCloseBtn = document.getElementById('welcome-close-btn');
  if (welcomeCloseBtn && welcomeMsg) {
    welcomeCloseBtn.addEventListener('click', () => {
      welcomeMsg.classList.add('minimized');
    });
  }

  // Set up form submission
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (input.value.trim() && !isProcessing) {
      sendMessage(input.value.trim());
    }
  });
  
  // Input validation
  input.addEventListener('input', () => {
    const hasText = input.value.trim().length > 0;
    sendBtn.disabled = !hasText || isProcessing;
    sendBtn.style.opacity = (hasText && !isProcessing) ? '1' : '0.5';
  });
  
  // Enter key to send
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.value.trim() && !isProcessing) {
        sendMessage(input.value.trim());
      }
    }
  });
  
  function renderQuickActions() {
    suggestionsContainer.innerHTML = '';
    quickActionsData.forEach(action => {
      const btn = document.createElement('button');
      btn.className = 'suggestion-btn';
      btn.textContent = action;
      btn.addEventListener('click', () => {
        if (!isProcessing) sendMessage(action);
      });
      suggestionsContainer.appendChild(btn);
    });
  }
  
  async function sendMessage(text) {
    if (!text.trim() || isProcessing) return;
    
    isProcessing = true;
    sendBtn.disabled = true;
    sendBtn.style.opacity = '0.5';
    
    // Minimize welcome message on first user message
    const welcome = document.getElementById('welcome-message');
    if (welcome && !welcome.classList.contains('minimized')) {
      welcome.classList.add('minimized');
    }
    
    // Add user message
    addMessage('user', text.trim());
    
    // Clear input
    input.value = '';
    
    // Show typing indicator
    const typingEl = showTypingIndicator();
    
    try {
      // Call FastAPI backend
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text.trim() }),
        signal: AbortSignal.timeout(120000), // 2 min timeout
      });
      
      typingEl.remove();
      
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${response.status})`);
      }
      
      const data = await response.json();
      addMessage('bot', data.answer, data);
      
    } catch (error) {
      typingEl.remove();
      console.error('Chat error:', error);
      
      let errorMsg;
      if (error.name === 'TimeoutError' || error.name === 'AbortError') {
        errorMsg = '⏱️ The request timed out. The server might be processing a complex query — please try again.';
      } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorMsg = '🔌 Cannot connect to the server. Make sure the backend is running:\n\npython server.py\n\n(Server should be at http://localhost:8000)';
      } else {
        errorMsg = `⚠️ ${error.message}`;
      }
      addMessage('bot', errorMsg);
    } finally {
      isProcessing = false;
      sendBtn.disabled = false;
      sendBtn.style.opacity = '1';
      input.focus();
      
      // Scroll to bottom
      setTimeout(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }, 100);
    }
  }
  
  function addMessage(sender, text, metadata = null) {
    const msg = document.createElement('div');
    msg.className = `chat-msg ${sender}`;
    
    // Timestamp
    const time = new Date().toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
    
    // Format text: parse markdown-like formatting
    const formattedText = formatMarkdown(text);
    
    // Build metadata footer for bot messages
    let metaHtml = '';
    if (sender === 'bot' && metadata) {
      const parts = [];
      if (metadata.query_type) parts.push(`Type: ${metadata.query_type}`);
      if (metadata.search_results) parts.push(`Sources: ${metadata.search_results}`);
      if (metadata.processing_time) parts.push(`${metadata.processing_time}s`);
      if (parts.length > 0) {
        metaHtml = `<div class="chat-msg-meta" style="margin-top:0.5rem;font-size:0.7rem;color:var(--muted-foreground);opacity:0.6;">${parts.join(' · ')}</div>`;
      }
    }
    
    msg.innerHTML = `
      <div class="chat-msg-avatar">
        <i data-lucide="${sender === 'user' ? 'user' : 'bot'}" 
           style="width:14px;height:14px;color:${sender === 'user' ? 'var(--secondary)' : 'var(--accent)'}"></i>
      </div>
      <div class="chat-msg-bubble">
        <div class="chat-msg-text">${formattedText}</div>
        ${metaHtml}
        <div class="chat-msg-time">${time}</div>
      </div>
    `;
    
    messagesContainer.appendChild(msg);
    lucide.createIcons();
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Animation
    msg.style.animation = 'message-in 0.3s ease forwards';
  }
  
  function formatMarkdown(text) {
    if (!text) return '';
    
    let html = text;
    
    // Escape HTML entities
    html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    // Code blocks (``` ... ```)
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code (`text`)
    html = html.replace(/`([^`]+)`/g, '<code style="background:hsla(220,15%,18%,0.8);padding:0.15em 0.4em;border-radius:4px;font-size:0.88em;">$1</code>');
    
    // Tables — convert markdown tables to styled HTML
    html = html.replace(/((?:^\|.+\|$\n?)+)/gm, (match) => {
      const rows = match.trim().split('\n').filter(r => r.trim());
      if (rows.length < 2) return match;
      
      let tableHtml = '<div style="overflow-x:auto;margin:0.75rem 0;"><table style="width:100%;border-collapse:collapse;font-size:0.85rem;">';
      let isHeader = true;
      rows.forEach((row) => {
        // Skip separator rows (|---|---|)
        if (/^\|[\s\-:]+\|$/.test(row.trim())) {
          isHeader = false;
          return;
        }
        
        const cells = row.split('|').filter((c, i, arr) => i > 0 && i < arr.length - 1);
        const tag = isHeader ? 'th' : 'td';
        const style = isHeader 
          ? 'style="padding:0.5rem 0.75rem;border-bottom:2px solid hsla(42,55%,55%,0.3);text-align:left;color:var(--secondary);font-weight:600;"'
          : 'style="padding:0.4rem 0.75rem;border-bottom:1px solid hsla(220,15%,18%,0.5);text-align:left;"';
        
        tableHtml += '<tr>';
        cells.forEach(cell => {
          tableHtml += `<${tag} ${style}>${cell.trim()}</${tag}>`;
        });
        tableHtml += '</tr>';
        if (isHeader) isHeader = false;
      });
      tableHtml += '</table></div>';
      return tableHtml;
    });
    
    // Bold (**text**)
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Italic (*text*)
    html = html.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
    
    // Headings
    html = html.replace(/^#### (.+)$/gm, '<h4 style="color:var(--secondary);margin:0.75rem 0 0.25rem;font-size:0.95rem;">$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3 style="color:var(--secondary);margin:0.75rem 0 0.25rem;font-size:1rem;">$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h3 style="color:var(--secondary);margin:0.75rem 0 0.25rem;font-size:1.05rem;">$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2 style="color:var(--secondary);margin:0.75rem 0 0.25rem;font-size:1.1rem;">$1</h2>');
    
    // Horizontal rules
    html = html.replace(/^---$/gm, '<hr style="border:none;border-top:1px solid hsla(220,15%,18%,0.5);margin:0.75rem 0;">');
    
    // Bullet points (-, *, •)
    html = html.replace(/^[\u2022\-\*]\s+(.+)$/gm, '<li style="margin:0.2rem 0;padding-left:0.25rem;">$1</li>');
    // Wrap consecutive <li> in <ul>
    html = html.replace(/((?:<li[^>]*>.*?<\/li>\s*)+)/g, '<ul style="margin:0.5rem 0;padding-left:1.25rem;list-style:disc;">$1</ul>');
    
    // Numbered lists
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li style="margin:0.2rem 0;">$1</li>');
    
    // Double line breaks = paragraph breaks
    html = html.replace(/\n\n/g, '<br><br>');
    // Single line breaks
    html = html.replace(/\n/g, '<br>');
    
    return html;
  }
  
  function showTypingIndicator() {
    const typing = document.createElement('div');
    typing.className = 'chat-typing';
    typing.innerHTML = `
      <div class="chat-msg-avatar">
        <i data-lucide="bot" style="width:14px;height:14px;color:var(--accent)"></i>
      </div>
      <div class="typing-bubble">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    `;
    
    messagesContainer.appendChild(typing);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    lucide.createIcons();
    
    return typing;
  }
  
  // Make sendMessage globally available for initial query from URL params
  window.sendMessage = sendMessage;
}
