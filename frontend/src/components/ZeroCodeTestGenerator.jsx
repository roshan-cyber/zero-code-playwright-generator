import React, { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CopyToClipboard } from 'react-copy-to-clipboard';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './ZeroCodeTestGenerator.css';

const ZeroCodeTestGenerator = () => {
  const apiBase = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
  const [environment, setEnvironment] = useState('Dev');
  const [role, setRole] = useState('MCS');
  const [language, setLanguage] = useState('TypeScript');
  const [loginUrl, setLoginUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [instructions, setInstructions] = useState('');
  const [pomCode, setPomCode] = useState('');
  const [testCode, setTestCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('pom');
  const [sessionEstablished, setSessionEstablished] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');
  const [authRequired, setAuthRequired] = useState(true);
  const [theme, setTheme] = useState('dark');
  const [showLLMSettings, setShowLLMSettings] = useState(false);

  // LLM Configuration state
  const [provider, setProvider] = useState('NVIDIA NIM');
  const [selectedModel, setSelectedModel] = useState('nvidia/nemotron-3-ultra-550b-a55b');
  const [userApiKey, setUserApiKey] = useState('');

  const languageOptions = [
    { value: 'TypeScript', label: 'TypeScript', pomFile: 'pageObjects.ts', testFile: 'testScenario.spec.ts', highlight: 'typescript' },
    { value: 'JavaScript', label: 'JavaScript', pomFile: 'pageObjects.js', testFile: 'testScenario.spec.js', highlight: 'javascript' },
    { value: 'Python', label: 'Python', pomFile: 'page_objects.py', testFile: 'test_suite.py', highlight: 'python' },
    { value: 'Java', label: 'Java', pomFile: 'PageObjects.java', testFile: 'TestScenario.java', highlight: 'java' },
  ];
  const currentLang = languageOptions.find(l => l.value === language) || languageOptions[0];

  // Model options per provider
  const modelOptions = {
    'NVIDIA NIM': [
      'nvidia/nemotron-3-ultra-550b-a55b',
      'nvidia/llama-3.1-405b-instruct'
    ],
    'OpenRouter': [
      'google/gemini-2.5-pro',
      'anthropic/claude-3.5-sonnet'
    ],
    'OpenAI': [
      'gpt-4o',
      'gpt-4-turbo'
    ],
    'Anthropic': [
      'claude-3-5-sonnet-latest'
    ]
  };

  // Update model when provider changes
  useEffect(() => {
    const models = modelOptions[provider] || [];
    setSelectedModel(models[0] || '');
  }, [provider]);

  const handleEstablishSession = useCallback(async () => {
    if (!loginUrl.trim() || !username.trim() || !password.trim()) {
      toast.error('Please fill Login URL, Username and Password');
      return;
    }
    setAuthLoading(true);
    setAuthError('');
    try {
      const resp = await fetch(`${apiBase}/create-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          environment,
          role,
          login_url: loginUrl.trim(),
          username: username.trim(),
          password: password.trim(),
          provider,
          model: selectedModel,
          user_api_key: userApiKey
        }),
      });
      const data = await resp.json();
      if (data.status === 'success') {
        setSessionEstablished(true);
        toast.success('Session established successfully!');
      } else {
        setAuthError(data.detail || 'Authentication failed');
        toast.error(data.detail || 'Authentication failed');
      }
    } catch (err) {
      const msg = err.message || 'Network error';
      setAuthError(msg);
      toast.error(msg);
    } finally {
      setAuthLoading(false);
    }
  }, [apiBase, environment, role, loginUrl, username, password, provider, selectedModel, userApiKey]);

  const handleGenerate = useCallback(async () => {
    if (!targetUrl.trim()) { toast.error('Please enter a target URL'); return; }
    if (!instructions.trim()) { toast.error('Please enter test instructions'); return; }

    setIsLoading(true);
    setErrorMsg('');
    setPomCode('');
    setTestCode('');

    try {
      const response = await fetch(`${apiBase}/generate-pom`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          environment,
          role,
          language,
          login_url: loginUrl.trim(),
          username: username.trim(),
          password: password.trim(),
          target_url: targetUrl.trim(),
          instructions: instructions.trim(),
          provider,
          model: selectedModel,
          user_api_key: userApiKey
        }),
      });
      const data = await response.json();
      if (data.pom_code && data.test_code) {
        setPomCode(data.pom_code);
        setTestCode(data.test_code);
        toast.success('POM and Test suite generated successfully!');
      } else {
        setErrorMsg(data.error || 'Unknown error occurred');
        toast.error(data.error || 'Generation failed');
      }
    } catch (err) {
      const msg = err.message || 'Network error';
      setErrorMsg(msg);
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  }, [apiBase, environment, role, language, loginUrl, username, password, targetUrl, instructions, provider, selectedModel, userApiKey]);

  const handleCopy = useCallback(() => {
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success('Copied to clipboard!');
  }, []);

  const clearAll = useCallback(() => {
    setEnvironment('Dev');
    setRole('MCS');
    setLanguage('TypeScript');
    setLoginUrl('');
    setUsername('');
    setPassword('');
    setTargetUrl('');
    setInstructions('');
    setPomCode('');
    setTestCode('');
    setErrorMsg('');
    setSessionEstablished(false);
    setAuthError('');
    setAuthRequired(true);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  }, []);

  const toggleLLMSettings = useCallback(() => {
    setShowLLMSettings(prev => !prev);
  }, []);

  const handleValidateAndClose = useCallback(() => {
    // Optionally validate the API key by calling a lightweight endpoint
    // For now just close the panel and show a toast
    toast.success('LLM configuration saved');
    setShowLLMSettings(false);
  }, []);

  const step1Disabled = isLoading || authLoading || sessionEstablished;
  const step2Disabled = isLoading || !(sessionEstablished || !authRequired);

  return (
    <div className="zctg-container" data-theme={theme}>
      <ToastContainer position="top-right" autoClose={3000} />

      <header className="zctg-header">
        <h1>Zero‑Code Playwright Generator</h1>
        <p className="subtitle">AI‑powered E2E test generation from natural language</p>
        <div className="header-actions">
          <button className="settings-btn" onClick={toggleLLMSettings} aria-label="LLM Settings">
            ⚙️
          </button>
          <button className="theme-toggle" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      {/* LLM Settings Modal */}
      <AnimatePresence>
        {showLLMSettings && (
          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowLLMSettings(false)}
          >
            <motion.div
              className="modal-card"
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              onClick={e => e.stopPropagation()}
            >
              <h2>LLM Configuration</h2>
              <div className="input-group">
                <label htmlFor="provider">API Provider</label>
                <select id="provider" value={provider} onChange={e=>setProvider(e.target.value)}>
                  <option value="NVIDIA NIM">NVIDIA NIM</option>
                  <option value="OpenRouter">OpenRouter</option>
                  <option value="OpenAI">OpenAI</option>
                  <option value="Anthropic">Anthropic</option>
                </select>
              </div>

              <div className="input-group">
                <label htmlFor="model">Model</label>
                <select id="model" value={selectedModel} onChange={e=>setSelectedModel(e.target.value)}>
                  { (modelOptions[provider] || []).map(m => <option key={m} value={m}>{m}</option>) }
                </select>
              </div>

              <div className="input-group">
                <label htmlFor="apiKey">Your API Key</label>
                <input
                  id="apiKey"
                  type="password"
                  value={userApiKey}
                  onChange={e=>setUserApiKey(e.target.value)}
                  placeholder="Enter your API key"
                />
              </div>

              <div className="action-buttons">
                <button className="btn-primary" onClick={handleValidateAndClose}>Validate & Close</button>
                <button className="btn-secondary" onClick={() => setShowLLMSettings(false)}>Cancel</button>
              </div>
</motion.div>
          </motion.div>
        )}
      </AnimatePresence>
      
      <main className="zctg-main">
        {/* ---------- STEP 1 : Authentication ---------- */}
        <section className="zctg-input-panel">
          <h2>Step 1 – Authentication</h2>

          <div className="input-group">
            <fieldset style={{border:'none', padding:0, marginBottom:'1rem'}}>
              <legend style={{fontWeight:600, marginBottom:'.5rem'}}>Authentication Mode</legend>
              <label style={{display:'flex', alignItems:'center', gap:'.5rem', marginRight:'1.5rem'}}>
                <input
                  type="radio"
                  name="authMode"
                  value={true}
                  checked={authRequired}
                  onChange={() => setAuthRequired(true)}
                  disabled={step1Disabled}
                />
                Authentication Required
              </label>
              <label style={{display:'flex', alignItems:'center', gap:'.5rem'}}>
                <input
                  type="radio"
                  name="authMode"
                  value={false}
                  checked={!authRequired}
                  onChange={() => setAuthRequired(false)}
                  disabled={step1Disabled}
                />
                No Authentication (Public Site)
              </label>
            </fieldset>
          </div>

          {authRequired && (
            <>
              <div className="input-group">
                <label htmlFor="environment">Environment</label>
                <select id="environment" value={environment} onChange={e=>setEnvironment(e.target.value)} disabled={step1Disabled}>
                  <option value="Dev">Dev</option><option value="QA">QA</option><option value="UAT">UAT</option>
                </select>
              </div>

              <div className="input-group">
                <label htmlFor="role">Role</label>
                <select id="role" value={role} onChange={e=>setRole(e.target.value)} disabled={step1Disabled}>
                  <option value="MCS">MCS</option><option value="PAT">PAT</option>
                  <option value="Manager">Manager</option><option value="BA">BA</option>
                </select>
              </div>
            </>
          )}

          <div className="input-group">
            <label htmlFor="language">Automation Language</label>
            <select id="language" value={language} onChange={e=>setLanguage(e.target.value)} disabled={step1Disabled}>
              {languageOptions.map(opt => (<option key={opt.value} value={opt.value}>{opt.label}</option>))}
            </select>
          </div>

          {authRequired && (
            <>
            <div className="input-group">
              <label htmlFor="loginUrl">Login URL</label>
              <input id="loginUrl" type="url" value={loginUrl} onChange={e=>setLoginUrl(e.target.value)}
                     placeholder="https://example.com/login" disabled={step1Disabled} />
            </div>

            <div className="input-group">
              <label htmlFor="username">Username</label>
              <input id="username" type="text" value={username} onChange={e=>setUsername(e.target.value)}
                     placeholder="your_username" disabled={step1Disabled} />
            </div>

            <div className="input-group">
              <label htmlFor="password">Password</label>
              <input id="password" type="password" value={password} onChange={e=>setPassword(e.target.value)}
                     placeholder="your_password" disabled={step1Disabled} />
            </div>

            <div className="action-buttons">
              <button className="btn-primary" onClick={handleEstablishSession}
                      disabled={authLoading || !loginUrl.trim() || !username.trim() || !password.trim()}>
                {authLoading ? <span className="btn-loading">Authenticating…</span> : 'Establish Active Session'}
              </button>
              <button className="btn-secondary" onClick={clearAll} disabled={isLoading || authLoading}>Clear All</button>
            </div>

            {authError && <div className="error-banner" role="alert"><strong>Error:</strong> {authError}</div>}
            {sessionEstablished && <div className="success-banner" role="status">✅ Session established successfully!</div>}
            </>
          )}
          {!authRequired && (
            <div className="action-buttons">
              <button className="btn-secondary" onClick={clearAll} disabled={isLoading || authLoading}>Clear All</button>
            </div>
          )}
        </section>

        {/* ---------- STEP 2 : Scraper Parameters ---------- */}
        <AnimatePresence mode="wait">
          {(sessionEstablished || !authRequired) && (
            <motion.section key="step2" initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-20}} className="zctg-input-panel">
              <h2>Step 2 – Scraper Parameters</h2>

              <div className="input-group">
                  <label htmlFor="targetUrl">Target Page URL</label>
                <input id="targetUrl" type="url" value={targetUrl} onChange={e=>setTargetUrl(e.target.value)}
                    placeholder="https://example.com/target-page" disabled={step2Disabled} />
              </div>

              <div className="input-group">
                <label htmlFor="instructions">Test Instructions (natural language)</label>
                <textarea id="instructions" value={instructions} onChange={e=>setInstructions(e.target.value)}
                          placeholder="e.g. open workorder, click “New”, fill required fields, submit, verify success toast"
                          rows={5} disabled={step2Disabled} />
              </div>

              <div className="action-buttons">
                <button className="btn-primary" onClick={handleGenerate}
                        disabled={step2Disabled || !targetUrl.trim() || !instructions.trim()}>
                  {isLoading ? <span className="btn-loading">Generating…</span> : `Generate ${currentLang.label} Suite`}
                </button>
              </div>

              {errorMsg && <div className="error-banner" role="alert"><strong>Error:</strong> {errorMsg}</div>}
            </motion.section>
          )}
        </AnimatePresence>

        {/* ---------- OUTPUT PANEL (right side) ---------- */}
        <AnimatePresence mode="wait">
          {(pomCode || testCode) && (
            <motion.aside key="output" initial={{opacity:0,x:30}} animate={{opacity:1,x:0}} exit={{opacity:0,x:-30}} className="zctg-output-panel">
              <div className="output-tabs">
                <button className={activeTab==='pom'?'active':''} onClick={()=>setActiveTab('pom')}>
                  Page Objects ({currentLang.pomFile})
                </button>
                <button className={activeTab==='test'?'active':''} onClick={()=>setActiveTab('test')}>
                  Test Suite ({currentLang.testFile})
                </button>
              </div>

              <div className="output-content">
                {activeTab==='pom' && pomCode && (
                  <CopyToClipboard text={pomCode} onCopy={handleCopy}>
                    <pre className="code-block"><code className={currentLang.highlight}>{pomCode}</code></pre>
                  </CopyToClipboard>
                )}
                {activeTab==='test' && testCode && (
                  <CopyToClipboard text={testCode} onCopy={handleCopy}>
                    <pre className="code-block"><code className={currentLang.highlight}>{testCode}</code></pre>
                  </CopyToClipboard>
                )}
              </div>

              <div className="copy-feedback">
                {activeTab==='pom' && pomCode && (
                  <CopyToClipboard text={pomCode} onCopy={handleCopy}>
                    <button className="btn-copy" aria-label="Copy POM">{copied?'✓ Copied!':`Copy ${currentLang.pomFile}`}</button>
                  </CopyToClipboard>
                )}
                {activeTab==='test' && testCode && (
                  <CopyToClipboard text={testCode} onCopy={handleCopy}>
                    <button className="btn-copy" aria-label="Copy Test">{copied?'✓ Copied!':`Copy ${currentLang.testFile}`}</button>
                  </CopyToClipboard>
                )}
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </main>

      <footer className="zctg-footer">
        <p>Powered by NVIDIA Nemotron‑3‑Ultra • FastAPI + Playwright + React</p>
      </footer>
    </div>
  );
};

export default ZeroCodeTestGenerator;