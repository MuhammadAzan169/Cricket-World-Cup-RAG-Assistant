/* =============================================
   Cricket AI Chatbot — Full Page Interface
   Connected to FastAPI Backend
   FIXED: Race conditions, duplicate handlers, robust initialization
   ============================================= */

// Use global API_BASE if already defined (from script.js), else detect
if (typeof API_BASE === 'undefined') {
  var API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? window.location.protocol + '//' + window.location.hostname + ':8000'
    : '';
}

document.addEventListener('DOMContentLoaded', function() {
  // Initialize Lucide icons
  if (typeof lucide !== 'undefined') lucide.createIcons();

  // Initialize chatbot
  initChatbot();

  // Focus on input
  setTimeout(function() {
    var inp = document.getElementById('chatbot-input');
    if (inp) inp.focus();
  }, 100);
});

function initChatbot() {
  var messagesContainer = document.getElementById('chat-messages');
  var form = document.getElementById('chatbot-form');
  var input = document.getElementById('chatbot-input');
  var sendBtn = document.getElementById('send-btn');
  var suggestionsContainer = document.getElementById('chat-suggestions');

  if (!messagesContainer || !form || !input || !sendBtn) return;

  var isProcessing = false;

  // Quick action suggestions
  var quickActionsData = [
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
  var welcomeMsg = document.getElementById('welcome-message');
  var welcomeCloseBtn = document.getElementById('welcome-close-btn');
  if (welcomeCloseBtn && welcomeMsg) {
    welcomeCloseBtn.addEventListener('click', function() {
      welcomeMsg.classList.add('minimized');
    });
  }

  // Set up form submission (single handler, no duplicates)
  form.addEventListener('submit', function(e) {
    e.preventDefault();
    if (input.value.trim() && !isProcessing) {
      sendMessage(input.value.trim());
    }
  });

  // Input validation
  input.addEventListener('input', function() {
    var hasText = input.value.trim().length > 0;
    sendBtn.disabled = !hasText || isProcessing;
    sendBtn.style.opacity = (hasText && !isProcessing) ? '1' : '0.5';
  });

  // Enter key to send (no duplicate — form submit handles it)
  // Removed redundant keydown listener since form already catches Enter

  function renderQuickActions() {
    if (!suggestionsContainer) return;
    suggestionsContainer.innerHTML = '';
    quickActionsData.forEach(function(action) {
      var btn = document.createElement('button');
      btn.className = 'suggestion-btn';
      btn.textContent = action;
      btn.addEventListener('click', function() {
        if (!isProcessing) sendMessage(action);
      });
      suggestionsContainer.appendChild(btn);
    });
  }

  function sendMessage(text) {
    if (!text || !text.trim() || isProcessing) return;

    isProcessing = true;
    sendBtn.disabled = true;
    sendBtn.style.opacity = '0.5';

    // Minimize welcome message on first user message
    var welcome = document.getElementById('welcome-message');
    if (welcome && !welcome.classList.contains('minimized')) {
      welcome.classList.add('minimized');
    }

    // Add user message
    addMessage('user', text.trim());

    // Clear input
    input.value = '';

    // Show typing indicator
    var typingEl = showTypingIndicator();

    // Call FastAPI backend
    fetch(API_BASE + '/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text.trim() }),
      signal: AbortSignal.timeout ? AbortSignal.timeout(120000) : undefined
    })
    .then(function(response) {
      if (typingEl && typingEl.parentNode) typingEl.remove();

      if (!response.ok) {
        return response.json().catch(function() { return {}; }).then(function(errData) {
          throw new Error(errData.detail || 'Server error (' + response.status + ')');
        });
      }

      return response.json();
    })
    .then(function(data) {
      if (data && data.answer) {
        addMessage('bot', data.answer, data);
      }
    })
    .catch(function(error) {
      if (typingEl && typingEl.parentNode) typingEl.remove();
      console.error('Chat error:', error);

      var errorMsg;
      if (error.name === 'TimeoutError' || error.name === 'AbortError') {
        errorMsg = '⏱️ The request timed out. The server might be processing a complex query — please try again.';
      } else if (error.message && (error.message.indexOf('Failed to fetch') !== -1 || error.message.indexOf('NetworkError') !== -1)) {
        errorMsg = '🔌 Cannot connect to the server. Make sure the backend is running:\n\npython server.py\n\n(Server should be at http://localhost:8000)';
      } else {
        errorMsg = '⚠️ ' + (error.message || 'An unexpected error occurred');
      }
      addMessage('bot', errorMsg);
    })
    .finally(function() {
      isProcessing = false;
      sendBtn.disabled = false;
      sendBtn.style.opacity = '1';
      input.focus();

      // Scroll to bottom
      setTimeout(function() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }, 100);
    });
  }

  function addMessage(sender, text, metadata) {
    var msg = document.createElement('div');
    msg.className = 'chat-msg ' + sender;

    // Timestamp
    var time = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });

    // Format text: use shared formatMarkdown if available
    var formattedText = (typeof formatMarkdown === 'function') ? formatMarkdown(text) : escapeAndFormat(text);

    // Build metadata footer for bot messages
    var metaHtml = '';
    if (sender === 'bot' && metadata) {
      var parts = [];
      if (metadata.query_type) parts.push('Type: ' + metadata.query_type);
      if (metadata.search_results) parts.push('Sources: ' + metadata.search_results);
      if (metadata.processing_time) parts.push(metadata.processing_time + 's');
      if (parts.length > 0) {
        metaHtml = '<div class="chat-msg-meta">' + parts.join(' · ') + '</div>';
      }
    }

    msg.innerHTML =
      '<div class="chat-msg-avatar">' +
        '<i data-lucide="' + (sender === 'user' ? 'user' : 'bot') + '" ' +
           'style="width:14px;height:14px;color:' + (sender === 'user' ? 'var(--secondary)' : 'var(--accent)') + '"></i>' +
      '</div>' +
      '<div class="chat-msg-bubble">' +
        '<div class="chat-msg-text">' + formattedText + '</div>' +
        metaHtml +
        '<div class="chat-msg-time">' + time + '</div>' +
      '</div>';

    messagesContainer.appendChild(msg);
    if (typeof lucide !== 'undefined') lucide.createIcons();

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Fallback formatter if formatMarkdown not loaded
  function escapeAndFormat(text) {
    if (!text) return '';
    var html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  function showTypingIndicator() {
    var typing = document.createElement('div');
    typing.className = 'chat-typing';
    typing.innerHTML =
      '<div class="chat-msg-avatar">' +
        '<i data-lucide="bot" style="width:14px;height:14px;color:var(--accent)"></i>' +
      '</div>' +
      '<div class="typing-bubble">' +
        '<div class="typing-dots">' +
          '<span></span><span></span><span></span>' +
        '</div>' +
      '</div>';

    messagesContainer.appendChild(typing);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    if (typeof lucide !== 'undefined') lucide.createIcons();

    return typing;
  }

  // Make sendMessage globally available for initial query from URL params
  window.sendMessage = sendMessage;
}
