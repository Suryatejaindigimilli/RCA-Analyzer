import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import {
  FiSend, FiGithub, FiCode, FiCpu, FiFileText, FiRefreshCw,
  FiTrash2, FiZap, FiX, FiSearch, FiBook, FiBookOpen
} from 'react-icons/fi';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [repoUrl, setRepoUrl] = useState('');
  const [showLoadModal, setShowLoadModal] = useState(true);
  const [repoLoaded, setRepoLoaded] = useState(false);
  const [repoInfo, setRepoInfo] = useState(null);
  const [repoStats, setRepoStats] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (repoLoaded) {
      axios.get(`${API_BASE}/api/suggested-questions`)
        .then(res => setSuggestedQuestions(res.data.questions))
        .catch(() => {});
    }
  }, [repoLoaded]);

  const addMessage = (role, content, extras = {}) => {
    setMessages(prev => [...prev, {
      id: Date.now().toString() + Math.random(),
      role, content, timestamp: new Date().toISOString(),
      ...extras
    }]);
  };

  const loadRepository = async (url) => {
    setIsLoading(true);
    addMessage('user', `Loading repository: ${url}`);
    try {
      const response = await axios.post(`${API_BASE}/api/load-repo`, { repo_url: url });
      setRepoInfo(response.data.repo_info);
      setRepoStats(response.data.stats);
      setRepoLoaded(true);
      setShowLoadModal(false);
      addMessage('assistant',
        `**Repository loaded successfully!**\n\n` +
        `**Statistics:**\n` +
        `- Files indexed: ${response.data.stats.files_indexed}\n` +
        `- Code chunks: ${response.data.stats.total_chunks}\n` +
        `- Total lines: ${response.data.stats.total_lines}\n` +
        `- Languages: ${Object.entries(response.data.stats.languages).slice(0, 5).map(([l, c]) => `${l} (${c})`).join(', ')}\n\n` +
        `I'm ready! Ask me anything about the codebase.`,
        { isRepoLoaded: true }
      );
    } catch (error) {
      addMessage('assistant',
        `**Failed to load repository**: ${error.response?.data?.detail || error.message}\n\n` +
        `Please check the URL is valid and the repo is public.`,
        { isError: true }
      );
    } finally {
      setIsLoading(false);
    }
  };

  const loadDemo = async () => {
    setIsLoading(true);
    addMessage('user', 'Loading demo repository');
    try {
      const response = await axios.post(`${API_BASE}/api/demo`);
      setRepoInfo(response.data.repo_info);
      setRepoStats(response.data.stats);
      setRepoLoaded(true);
      setShowLoadModal(false);
      addMessage('assistant',
        `**Demo repository loaded!**\n\n` +
        `Stats: ${response.data.stats.files_indexed} files, ${response.data.stats.total_chunks} chunks, ${response.data.stats.total_lines} lines.\n\n` +
        `Ask me anything about the codebase!`,
        { isRepoLoaded: true }
      );
    } catch (error) {
      addMessage('assistant', `Demo failed: ${error.message}`, { isError: true });
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (messageText = null) => {
    const text = messageText || input;
    if (!text.trim() || isLoading) return;

    addMessage('user', text);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/api/chat`, { message: text });
      addMessage('assistant', response.data.response, {
        references: response.data.references || []
      });
    } catch (error) {
      addMessage('assistant',
        `Error: ${error.response?.data?.detail || error.message}\n\nMake sure you've loaded a repository first.`,
        { isError: true }
      );
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = async () => {
    try {
      await axios.post(`${API_BASE}/api/clear`);
      setMessages([]);
      setRepoLoaded(false);
      setRepoInfo(null);
      setRepoStats(null);
      setShowLoadModal(true);
    } catch (error) {
      console.error('Clear failed:', error);
    }
  };

  return (
    <div className="app">
      <div className="bg-animation">
        <div className="bg-gradient-1"></div>
        <div className="bg-gradient-2"></div>
        <div className="bg-gradient-3"></div>
      </div>

      {sidebarOpen && repoLoaded && (
        <aside className="sidebar open">
          <div className="sidebar-header">
            <div className="logo-container">
              <div className="logo-icon"><FiCpu /></div>
              <div className="logo-text">
                <div className="logo-title">Codebase AI</div>
                <div className="logo-subtitle">Repository Chatbot</div>
              </div>
            </div>
          </div>

          {repoInfo && (
            <div className="sidebar-section">
              <div className="section-label">LOADED REPOSITORY</div>
              <div className="repo-card">
                <div className="repo-name"><FiGithub /> {repoInfo.name}</div>
                {repoInfo.description && <div className="repo-description">{repoInfo.description}</div>}
                <div className="repo-meta">
                  <span className="repo-badge">{repoInfo.platform}</span>
                </div>
              </div>
            </div>
          )}

          {repoStats && (
            <div className="sidebar-section">
              <div className="section-label">STATISTICS</div>
              <div className="stat-card">
                <div className="stat-icon"><FiFileText /></div>
                <div className="stat-info">
                  <div className="stat-value">{repoStats.files_indexed}</div>
                  <div className="stat-label">Files</div>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon"><FiCode /></div>
                <div className="stat-info">
                  <div className="stat-value">{repoStats.total_chunks}</div>
                  <div className="stat-label">Chunks</div>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon"><FiBook /></div>
                <div className="stat-info">
                  <div className="stat-value">{repoStats.total_lines || 0}</div>
                  <div className="stat-label">Lines</div>
                </div>
              </div>
            </div>
          )}

          {repoStats?.languages && (
            <div className="sidebar-section">
              <div className="section-label">LANGUAGES</div>
              <div className="languages-list">
                {Object.entries(repoStats.languages).slice(0, 6).map(([lang, count]) => (
                  <div key={lang} className="language-item">
                    <span className="lang-name">{lang}</span>
                    <span className="lang-count">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="sidebar-section">
            <button className="sidebar-btn" onClick={clearChat}>
              <FiTrash2 /> Load New Repository
            </button>
          </div>

          <div className="sidebar-footer">
            <div className="footer-title">Harris IoT Ideathon 2026</div>
          </div>
        </aside>
      )}

      <main className="main-content">
        <header className="top-bar">
          <div className="top-bar-left">
            {!sidebarOpen && repoLoaded && (
              <button className="icon-btn" onClick={() => setSidebarOpen(true)}>
                <FiCode />
              </button>
            )}
            <div className="chat-title">
              <div className="title-main">
                {repoLoaded ? repoInfo?.name : 'Codebase AI Chatbot'}
              </div>
              <div className="title-sub">
                <span className="status-dot"></span>
                {isLoading ? 'Thinking...' : (repoLoaded ? 'Ready' : 'Awaiting repository')}
              </div>
            </div>
          </div>
          <div className="top-bar-right">
            {repoLoaded && (
              <button className="icon-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
                {sidebarOpen ? <FiX /> : <FiCode />}
              </button>
            )}
          </div>
        </header>

        <div className="messages-container">
          {messages.length === 0 && !repoLoaded && (
            <div className="welcome-screen">
              <div className="welcome-icon"><FiCode /></div>
              <h1>Codebase-Aware AI Chatbot</h1>
              <p>Chat with any GitHub or Bitbucket repository</p>
              <button className="cta-button" onClick={() => setShowLoadModal(true)}>
                <FiGithub /> Load a Repository
              </button>
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isLoading && (
            <div className="message-row assistant">
              <div className="avatar assistant-avatar"></div>
              <div className="message-content-wrapper">
                <div className="message-bubble assistant loading">
                  <div className="typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                  <div className="loading-text">Analyzing...</div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {repoLoaded && suggestedQuestions.length > 0 && !isLoading && (
          <div className="suggestions-container">
            <div className="suggestions-label">Suggested questions:</div>
            <div className="suggestions-list">
              {suggestedQuestions.slice(0, 4).map((q, i) => (
                <button key={i} className="suggestion-btn" onClick={() => sendMessage(q)} disabled={isLoading}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {repoLoaded && (
          <div className="input-container">
            <div className="input-wrapper">
              <textarea
                className="message-input"
                placeholder="Ask anything about the codebase..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                rows={1}
                disabled={isLoading}
              />
              <button className="send-btn" onClick={() => sendMessage()} disabled={!input.trim() || isLoading}>
                {isLoading ? <FiRefreshCw className="spinning" /> : <FiSend />}
              </button>
            </div>
            <div className="input-hint">
              <kbd>Enter</kbd> send - <kbd>Shift+Enter</kbd> new line
            </div>
          </div>
        )}
      </main>

      {showLoadModal && (
        <LoadRepoModal
          repoUrl={repoUrl}
          setRepoUrl={setRepoUrl}
          onLoad={loadRepository}
          onDemo={loadDemo}
          onClose={() => repoLoaded && setShowLoadModal(false)}
          isLoading={isLoading}
        />
      )}
    </div>
  );
}

function LoadRepoModal({ repoUrl, setRepoUrl, onLoad, onDemo, onClose, isLoading }) {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (repoUrl.trim()) onLoad(repoUrl);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {onClose && <button className="modal-close" onClick={onClose}></button>}
        <div className="modal-icon"><FiGithub /></div>
        <h2>Load a Repository</h2>
        <p className="modal-subtitle">Provide a GitHub or Bitbucket URL</p>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <FiGithub className="input-icon" />
            <input
              type="text"
              className="repo-input"
              placeholder="https://github.com/owner/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              disabled={isLoading}
              autoFocus
            />
          </div>
          <button type="submit" className="modal-btn primary" disabled={!repoUrl.trim() || isLoading}>
            {isLoading ? <><FiRefreshCw className="spinning" /> Loading...</> : <><FiSearch /> Analyze</>}
          </button>
        </form>

        <div className="modal-divider"><span>OR</span></div>

        <button className="modal-btn demo" onClick={onDemo} disabled={isLoading}>
          <FiZap /> Try Demo Repository
        </button>

        <div className="supported-platforms">
          <span>Supports:</span>
          <span className="platform-badge"><FiGithub /> GitHub</span>
          <span className="platform-badge"><FiCode /> Bitbucket</span>
        </div>

        <div className="examples">
          <div className="examples-label">Examples:</div>
          <div className="example-item" onClick={() => setRepoUrl('https://github.com/fastapi/fastapi')}>
            https://github.com/fastapi/fastapi
          </div>
          <div className="example-item" onClick={() => setRepoUrl('https://github.com/facebook/react')}>
            https://github.com/facebook/react
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const copyToClipboard = () => navigator.clipboard.writeText(message.content);

  return (
    <div className={`message-row ${message.role} animate-fade-in`}>
      <div className={`avatar ${isUser ? 'user-avatar' : 'assistant-avatar'}`}>
        {isUser ? '' : <FiCpu />}
      </div>
      <div className="message-content-wrapper">
        <div className="message-meta">
          <span className="message-author">{isUser ? 'You' : 'Codebase AI'}</span>
          <span className="message-time">{new Date(message.timestamp).toLocaleTimeString()}</span>
        </div>
        <div className={`message-bubble ${message.role} ${message.isError ? 'error' : ''}`}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (<code className={className} {...props}>{children}</code>);
              }
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {message.references && message.references.length > 0 && (
          <div className="references-section">
            <div className="references-label"><FiBookOpen /> Code References ({message.references.length})</div>
            {message.references.map((ref, i) => (
              <details key={i} className="reference-item">
                <summary>
                  <FiFileText />
                  <span className="ref-path">{ref.file_path}</span>
                  <span className="ref-lines">L{ref.lines}</span>
                  <span className="ref-type">{ref.chunk_type}</span>
                </summary>
                <div className="reference-preview">
                  <div className="ref-name">{ref.name}</div>
                  <pre><code>{ref.preview}</code></pre>
                </div>
              </details>
            ))}
          </div>
        )}

        <div className="message-actions">
          <button className="action-btn" onClick={copyToClipboard}>Copy</button>
        </div>
      </div>
    </div>
  );
}

export default App;
