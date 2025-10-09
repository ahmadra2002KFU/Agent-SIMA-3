(function(){
        // Sidebar Toggle Functionality
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const mainContent = document.getElementById('main-content');
        const sidebarBackdrop = document.getElementById('sidebar-backdrop');

        // Check if we're on mobile
        function isMobile() {
          return window.innerWidth <= 768;
        }

        // Load sidebar state from localStorage (only for desktop)
        const sidebarCollapsed = !isMobile() && localStorage.getItem('sidebarCollapsed') === 'true';

        // Apply initial state
        if (sidebarCollapsed && !isMobile()) {
          sidebar.classList.add('sidebar-collapsed');
          mainContent.classList.add('main-expanded');
        } else if (isMobile()) {
          // On mobile, start with sidebar collapsed
          sidebar.classList.add('sidebar-collapsed');
        }

        // Update toggle button icon
        function updateToggleIcon() {
          const isCollapsed = sidebar.classList.contains('sidebar-collapsed');
          const icon = sidebarToggle.querySelector('.material-symbols-outlined');
          if (icon) {
            icon.textContent = isCollapsed ? 'menu_open' : 'menu';
          }
        }

        // Set initial icon
        updateToggleIcon();

        // Toggle function with smooth animation
        function toggleSidebar() {
          const isCollapsed = sidebar.classList.contains('sidebar-collapsed');
          const mobile = isMobile();

          if (isCollapsed) {
            // Expand sidebar
            sidebar.classList.remove('sidebar-collapsed');
            if (!mobile) {
              mainContent.classList.remove('main-expanded');
              localStorage.setItem('sidebarCollapsed', 'false');
            } else {
              // Show backdrop on mobile
              sidebarBackdrop.classList.add('active');
            }
          } else {
            // Collapse sidebar
            sidebar.classList.add('sidebar-collapsed');
            if (!mobile) {
              mainContent.classList.add('main-expanded');
              localStorage.setItem('sidebarCollapsed', 'true');
            } else {
              // Hide backdrop on mobile
              sidebarBackdrop.classList.remove('active');
            }
          }

          // Update icon to reflect new state
          updateToggleIcon();
        }

        // Add event listener to toggle button
        sidebarToggle.addEventListener('click', toggleSidebar);

        // Close sidebar when clicking backdrop on mobile
        sidebarBackdrop.addEventListener('click', () => {
          if (isMobile()) {
            sidebar.classList.add('sidebar-collapsed');
            sidebarBackdrop.classList.remove('active');
            updateToggleIcon();
          }
        });

        // Handle window resize
        window.addEventListener('resize', () => {
          const mobile = isMobile();
          if (mobile) {
            // On mobile, remove desktop classes and hide backdrop
            mainContent.classList.remove('main-expanded');
            sidebarBackdrop.classList.remove('active');
            if (!sidebar.classList.contains('sidebar-collapsed')) {
              sidebar.classList.add('sidebar-collapsed');
            }
          } else {
            // On desktop, restore saved state and hide backdrop
            sidebarBackdrop.classList.remove('active');
            const savedState = localStorage.getItem('sidebarCollapsed') === 'true';
            if (savedState) {
              sidebar.classList.add('sidebar-collapsed');
              mainContent.classList.add('main-expanded');
            } else {
              sidebar.classList.remove('sidebar-collapsed');
              mainContent.classList.remove('main-expanded');
            }
          }
          // Update icon after resize
          updateToggleIcon();
        });

        // Keyboard shortcut (Ctrl/Cmd + B)
        document.addEventListener('keydown', (e) => {
          if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
            e.preventDefault();
            toggleSidebar();
          }
        });

        // Main application variables
        const startView = document.getElementById('chat-start-view');
        const convoView = document.getElementById('chat-conversation-view');
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const fileInput = document.getElementById('file-upload');
        const welcomeDropzone = document.getElementById('welcome-dropzone');
        const welcomeUploadButton = document.getElementById('welcome-upload-button');
        const welcomeUploadStatus = document.getElementById('welcome-upload-status');
        const welcomeUploadPrompt = document.getElementById('welcome-upload-prompt');
        const defaultWelcomePrompt = welcomeUploadPrompt ? welcomeUploadPrompt.textContent : '';
        const uploadProgressContainer = document.getElementById('upload-progress-container');
        const uploadProgressBar = document.getElementById('upload-progress-bar');
        const uploadProgressPercent = document.getElementById('upload-progress-percent');
        const uploadProgressText = document.getElementById('upload-progress-text');
        const MIN_PROGRESS_VISIBLE_MS = 600;
        let dropzoneDragDepth = 0;
        let ws = null;
        let containers = null;
        let currentFile = null;
        let commentaryRevealTimer = null;
        let uploadProgressHideTimer = null;
        let uploadProgressIndeterminate = false;
        let uploadProgressProcessingShown = false;
        let uploadProgressStartTime = 0;

        function revealConversationView() {
          if (!startView || !convoView) return;
          if (!convoView.classList.contains('hidden')) {
            return;
          }
          startView.classList.add('hidden');
          convoView.classList.remove('hidden');
        }

        const ANALYSIS_PLACEHOLDER = 'Analyzing your request and generating response...';

        const WELCOME_STATUS_COLOR_CLASSES = [
          'text-gray-600',
          'dark:text-gray-300',
          'text-primary',
          'dark:text-blue-300',
          'text-amber-600',
          'dark:text-amber-400',
          'text-red-500',
          'dark:text-red-400'
        ];

        function setWelcomeStatus(message, variant = 'info') {
          if (!welcomeUploadStatus) return;
          WELCOME_STATUS_COLOR_CLASSES.forEach(cls => welcomeUploadStatus.classList.remove(cls));
          welcomeUploadStatus.textContent = message;
          welcomeUploadStatus.classList.remove('hidden');
          const variantMap = {
            info: ['text-gray-600', 'dark:text-gray-300'],
            success: ['text-primary', 'dark:text-blue-300'],
            pending: ['text-amber-600', 'dark:text-amber-400'],
            error: ['text-red-500', 'dark:text-red-400']
          };
          (variantMap[variant] || variantMap.info).forEach(cls => welcomeUploadStatus.classList.add(cls));
        }

        function updateWelcomeFileStatus(fileInfo) {
          if (!fileInfo) return;
          const summarySegments = [];
          if (typeof fileInfo.rows === 'number') summarySegments.push(`${fileInfo.rows.toLocaleString()} rows`);
          if (typeof fileInfo.columns === 'number') summarySegments.push(`${fileInfo.columns} columns`);
          if (typeof fileInfo.size_mb === 'number') summarySegments.push(`${fileInfo.size_mb} MB`);
          const summary = summarySegments.filter(Boolean).join(' | ');
          const message = summary ? `${fileInfo.filename} loaded | ${summary}` : `${fileInfo.filename} ready to explore`;
          if (welcomeUploadPrompt) {
            welcomeUploadPrompt.textContent = 'File uploaded - start exploring insights together.';
          }
          setWelcomeStatus(message, 'success');
          if (welcomeDropzone) {
            welcomeDropzone.classList.add('file-loaded');
          }
        }

        function setDropzoneActive(isActive) {
          if (!welcomeDropzone) return;
          if (isActive) {
            welcomeDropzone.classList.add('dropzone-active');
          } else {
            welcomeDropzone.classList.remove('dropzone-active');
          }
        }

        if (uploadProgressContainer) {
          uploadProgressContainer.setAttribute('aria-hidden', 'true');
        }

        function safeJsonParse(rawValue) {
          if (!rawValue) return {};
          if (typeof rawValue === 'object') return rawValue;
          try {
            return JSON.parse(rawValue);
          } catch (err) {
            return {};
          }
        }

        function startUploadProgress(filename) {
          if (!uploadProgressContainer) return;
          if (uploadProgressHideTimer) {
            clearTimeout(uploadProgressHideTimer);
            uploadProgressHideTimer = null;
          }
          uploadProgressProcessingShown = false;
          uploadProgressIndeterminate = false;
          uploadProgressStartTime = performance.now();
          uploadProgressContainer.classList.remove('hidden');
          uploadProgressContainer.setAttribute('aria-hidden', 'false');
          if (uploadProgressBar) {
            uploadProgressBar.classList.remove('animate-pulse');
            uploadProgressBar.style.width = '0%';
          }
          if (uploadProgressPercent) {
            uploadProgressPercent.textContent = '0%';
          }
          if (uploadProgressText) {
            uploadProgressText.textContent = filename ? `Uploading ${filename}...` : 'Uploading...';
          }
        }

        function updateUploadProgressDisplay(percent) {
          if (!uploadProgressContainer) return;
          const clamped = Math.max(0, Math.min(100, Math.round(percent)));
          if (uploadProgressProcessingShown) {
            return;
          }
          uploadProgressIndeterminate = false;
          if (uploadProgressBar) {
            uploadProgressBar.classList.remove('animate-pulse');
            uploadProgressBar.style.width = `${clamped}%`;
          }
          if (uploadProgressPercent) {
            uploadProgressPercent.textContent = `${clamped}%`;
          }
        }

        function setUploadProgressToIndeterminate(filename) {
          if (!uploadProgressContainer || uploadProgressIndeterminate || uploadProgressProcessingShown) return;
          uploadProgressIndeterminate = true;
          if (uploadProgressBar) {
            uploadProgressBar.classList.add('animate-pulse');
            uploadProgressBar.style.width = '60%';
          }
          if (uploadProgressPercent) {
            uploadProgressPercent.textContent = '--%';
          }
          if (uploadProgressText) {
            uploadProgressText.textContent = filename ? `Uploading ${filename}...` : 'Uploading...';
          }
        }

        function markUploadProcessing(message = 'Processing file...', label = 'Processing') {
          if (!uploadProgressContainer) return;
          uploadProgressProcessingShown = true;
          uploadProgressIndeterminate = false;
          if (uploadProgressBar) {
            uploadProgressBar.classList.remove('animate-pulse');
            uploadProgressBar.style.width = '100%';
          }
          if (uploadProgressPercent) {
            uploadProgressPercent.textContent = label;
          }
          if (uploadProgressText) {
            uploadProgressText.textContent = message;
          }
        }

        function hideUploadProgress(delay = 600) {
          if (!uploadProgressContainer) return;
          const requestedDelay = Number(delay);
          const elapsed = performance.now() - uploadProgressStartTime;
          const timeout = requestedDelay === 0
            ? 0
            : Math.max(requestedDelay || 0, Math.max(0, MIN_PROGRESS_VISIBLE_MS - elapsed));
          if (uploadProgressHideTimer) {
            clearTimeout(uploadProgressHideTimer);
          }
            uploadProgressHideTimer = setTimeout(() => {
            uploadProgressProcessingShown = false;
            uploadProgressIndeterminate = false;
            if (uploadProgressBar) {
              uploadProgressBar.classList.remove('animate-pulse');
              uploadProgressBar.style.width = '0%';
            }
            if (uploadProgressPercent) {
              uploadProgressPercent.textContent = '0%';
            }
            if (uploadProgressText) {
              uploadProgressText.textContent = 'Uploading...';
            }
            uploadProgressContainer.classList.add('hidden');
            uploadProgressContainer.setAttribute('aria-hidden', 'true');
            uploadProgressHideTimer = null;
          }, timeout);
        }



        if (welcomeUploadButton) {
          welcomeUploadButton.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (fileInput) {
              fileInput.click();
            }
          });
        }

        if (welcomeDropzone) {
          welcomeDropzone.addEventListener('click', (event) => {
            if (event.defaultPrevented) return;
            if (fileInput) {
              fileInput.click();
            }
          });

          welcomeDropzone.addEventListener('dragenter', (event) => {
            event.preventDefault();
            dropzoneDragDepth += 1;
            setDropzoneActive(true);
          });

          welcomeDropzone.addEventListener('dragover', (event) => {
            event.preventDefault();
            if (event.dataTransfer) {
              event.dataTransfer.dropEffect = 'copy';
            }
            setDropzoneActive(true);
          });

          welcomeDropzone.addEventListener('dragleave', (event) => {
            event.preventDefault();
            dropzoneDragDepth = Math.max(dropzoneDragDepth - 1, 0);
            if (dropzoneDragDepth === 0) {
              setDropzoneActive(false);
            }
          });

          welcomeDropzone.addEventListener('drop', (event) => {
            event.preventDefault();
            const files = event.dataTransfer ? event.dataTransfer.files : null;
            dropzoneDragDepth = 0;
            setDropzoneActive(false);
            if (files && files.length > 0) {
              const file = files[0];
              uploadFile(file);
            }
          });
        }

        function getAnalysisPre(container) {
          if (!container) return null;
          return container.querySelector('[data-role="analysis-content"]') || container.querySelector('pre');
        }

        function setAnalysisThinking(container, isThinking) {
          const skeleton = container ? container.querySelector('[data-role="analysis-skeleton"]') : null;
          const pre = getAnalysisPre(container);
          if (isThinking) {
            if (skeleton) {
              const computed = skeleton.dataset.originalDisplay || (typeof window !== 'undefined' ? window.getComputedStyle(skeleton).display : '') || 'grid';
              skeleton.dataset.originalDisplay = computed;
              skeleton.style.display = computed;
              skeleton.classList.remove('hidden');
            }
            if (pre) {
              pre.textContent = '';
              pre.classList.add('hidden');
              pre.dataset.isSkeleton = 'true';
            }
          } else {
            if (skeleton) {
              skeleton.classList.add('hidden');
              skeleton.style.display = 'none';
            }
            if (pre) {
              pre.classList.remove('hidden');
              if (pre.dataset) {
                delete pre.dataset.isSkeleton;
              }
            }
          }
        }

        function getCommentaryPre(container) {
          if (!container) return null;
          return container.querySelector('[data-role="commentary-content"]') || container.querySelector('pre');
        }


        function revealGeneratedCode() {
          if (containers && containers.generated_code && containers.generated_code.classList.contains('hidden')) {
            containers.generated_code.classList.remove('hidden');
          }
        }

        function revealCommentary() {
          if (containers && containers.result_commentary && containers.result_commentary.classList.contains('hidden')) {
            containers.result_commentary.classList.remove('hidden');
          }
        }
        function setCommentaryThinking(container, isThinking) {
          const skeleton = container ? container.querySelector('[data-role="commentary-skeleton"]') : null;
          const pre = getCommentaryPre(container);
          if (isThinking) {
            if (skeleton) {
              const computed = skeleton.dataset.originalDisplay || (typeof window !== 'undefined' ? window.getComputedStyle(skeleton).display : '') || 'grid';
              skeleton.dataset.originalDisplay = computed;
              skeleton.style.display = computed;
              skeleton.classList.remove('hidden');
            }
            if (pre) {
              pre.textContent = '';
              pre.classList.add('hidden');
              pre.dataset.isSkeleton = 'true';
            }
          } else {
            if (skeleton) {
              skeleton.classList.add('hidden');
              skeleton.style.display = 'none';
            }
            if (pre) {
              pre.classList.remove('hidden');
              if (pre.dataset) {
                delete pre.dataset.isSkeleton;
              }
            }
          }
        }

        function ensureCommentaryPending() {
          if (!containers || !containers.result_commentary) {
            return;
          }
          revealCommentary();
          const pre = getCommentaryPre(containers.result_commentary);
          if (pre && !(pre.textContent && pre.textContent.trim())) {
            setCommentaryThinking(containers.result_commentary, true);
          }
        }

        function scheduleCommentaryPendingReveal(delay = 250) {
          if (commentaryRevealTimer) {
            clearTimeout(commentaryRevealTimer);
          }
          commentaryRevealTimer = window.setTimeout(() => {
            commentaryRevealTimer = null;
            ensureCommentaryPending();
          }, delay);
        }

        function connectWS(){
          const proto = location.protocol === 'https:' ? 'wss' : 'ws';
          const base = location.host ? (proto + '://' + location.host) : 'ws://127.0.0.1:8010';
          ws = new WebSocket(base + '/ws');
          ws.onmessage = (ev)=>{
            try {
              const msg = JSON.parse(ev.data);
              if(msg.event === 'start'){
                // Don't switch views here - user message display already handled this
                // Create containers for the 5 fields (new order: analysis, code, viz, results, commentary)
                containers = {
                  generated_code: document.createElement('div'),
                  visualizations: document.createElement('div'),
                  initial_response: document.createElement('div'),
                  results_block: document.createElement('div'),
                  result_commentary: document.createElement('div')
                };

                if (commentaryRevealTimer) {
                  clearTimeout(commentaryRevealTimer);
                  commentaryRevealTimer = null;
                }

                // 1. Analysis (displayed FIRST)
                containers.initial_response.className = 'ai-response-card p-5 mb-4 rounded-xl relative z-10';
                containers.initial_response.innerHTML = `
                  <div class="section-title">
                    <span class="card-header-icon">
                      <span class="material-symbols-outlined text-sm text-primary dark:text-blue-300">analytics</span>
                    </span>
                    Analysis
                  </div>
                  <div class="analysis-thinking" data-role="analysis-wrapper">
                    <div class="thinking-lines" data-role="analysis-skeleton">
                      <div class="thinking-line"></div>
                      <div class="thinking-line short"></div>
                      <div class="dot-wave" aria-hidden="true"><span></span><span></span><span></span></div>
                    </div>
                    <pre class="content-text whitespace-pre-wrap hidden" data-role="analysis-content"></pre>
                  </div>
                `;

                // 2. Python Code Block (displayed SECOND)
                containers.generated_code.className = 'mb-4 relative z-10 hidden';
                containers.generated_code.innerHTML = `
                  <div class="code-block-container">
                    <div class="code-block-header">
                      <span class="code-block-language">Python</span>
                      <button class="code-block-copy-btn" onclick="copyCodeToClipboard(this)">
                        <span class="material-symbols-outlined" style="font-size: 14px;">content_copy</span>
                        Copy
                      </button>
                    </div>
                    <div class="code-block-content">
                      <pre><code class="language-python"></code></pre>
                    </div>
                  </div>
                `;

                // 3. Visualizations (displayed THIRD, conditionally)
                containers.visualizations.className = 'ai-response-card p-5 mb-4 rounded-xl relative z-10 hidden';
                containers.visualizations.innerHTML = `
                  <div class="section-title">
                    <span class="card-header-icon">
                      <span class="material-symbols-outlined text-sm text-primary dark:text-blue-300">bar_chart</span>
                    </span>
                    Visualizations
                  </div>
                  <div class="viz-container space-y-4"></div>
                `;

                // 4. Results Block (displayed FOURTH - NEW prominent results display)
                containers.results_block.className = 'ai-response-card p-6 mb-4 rounded-xl relative z-10 hidden';
                containers.results_block.innerHTML = `
                  <div class="section-title">
                    <span class="card-header-icon">
                      <span class="material-symbols-outlined text-sm text-primary dark:text-blue-300">check_circle</span>
                    </span>
                    Results
                  </div>
                  <!-- Skeleton Loader (shown during code execution) -->
                  <div id="results-skeleton" class="skeleton-results-container hidden">
                    <div class="skeleton-loader skeleton-value"></div>
                    <div class="skeleton-loader skeleton-label"></div>
                  </div>
                  <!-- Actual Results (shown after execution completes) -->
                  <div id="results-actual" class="results-content bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-700 p-6 rounded-lg border-2 border-primary dark:border-blue-400 mt-3 hidden">
                    <div class="text-4xl font-bold text-primary dark:text-blue-300 mb-2 font-mono" id="primary-result-value"></div>
                    <div class="text-sm text-gray-600 dark:text-gray-300" id="primary-result-label"></div>
                  </div>
                `;

                // 5. Commentary (displayed FIFTH)
                containers.result_commentary.className = 'ai-response-card p-5 mb-4 rounded-xl relative z-10 hidden';
                containers.result_commentary.innerHTML = `
                  <div class="section-title">
                    <span class="card-header-icon">
                      <span class="material-symbols-outlined text-sm text-primary dark:text-blue-300">description</span>
                    </span>
                    Commentary
                  </div>
                  <div class="commentary-thinking" data-role="commentary-wrapper">
                    <div class="thinking-lines" data-role="commentary-skeleton">
                      <div class="thinking-line"></div>
                      <div class="thinking-line short"></div>
                      <div class="dot-wave" aria-hidden="true"><span></span><span></span><span></span></div>
                    </div>
                    <pre class="content-text whitespace-pre-wrap hidden" data-role="commentary-content"></pre>
                  </div>
                `;

                // Append containers in NEW ORDER: Analysis â†’ Code â†’ Viz â†’ Results â†’ Commentary
                convoView.appendChild(containers.initial_response);
                convoView.appendChild(containers.generated_code);
                convoView.appendChild(containers.visualizations);
                convoView.appendChild(containers.results_block);
                convoView.appendChild(containers.result_commentary);
                setAnalysisThinking(containers.initial_response, true);
                setCommentaryThinking(containers.result_commentary, true);
                convoView.scrollTop = convoView.scrollHeight;
              } else if(msg.event === 'status' && containers && msg.field){
                if (msg.field === 'initial_response' && msg.status === 'analyzing') {
                  setAnalysisThinking(containers.initial_response, true);
                }
              } else if(msg.event === 'delta' && containers && msg.field && msg.delta){
                if (msg.field === 'generated_code') {
                  revealGeneratedCode();
                  const codeElement = containers[msg.field].querySelector('code');
                  if (codeElement) {
                    codeElement.textContent += msg.delta;
                  }
                  scheduleCommentaryPendingReveal();
                } else if (msg.field === 'initial_response') {
                  const preElement = getAnalysisPre(containers.initial_response);
                  if (preElement) {
                    const isPlaceholderChunk = msg.delta.includes(ANALYSIS_PLACEHOLDER);
                    if (isPlaceholderChunk) {
                      setAnalysisThinking(containers.initial_response, true);
                    } else {
                      const shouldSkip = preElement.dataset.isSkeleton && msg.delta.trim().length === 0;
                      if (!shouldSkip) {
                        if (preElement.dataset.isSkeleton) {
                          setAnalysisThinking(containers.initial_response, false);
                          preElement.textContent = '';
                        }
                        preElement.textContent += msg.delta;
                      }
                    }
                  }
                } else if (msg.field === 'result_commentary') {
                  if (commentaryRevealTimer) {
                    clearTimeout(commentaryRevealTimer);
                    commentaryRevealTimer = null;
                  }
                  ensureCommentaryPending();
                  const preElement = getCommentaryPre(containers.result_commentary);
                  if (preElement) {
                    const shouldSkip = preElement.dataset.isSkeleton && msg.delta.trim().length === 0;
                    if (!shouldSkip) {
                      if (preElement.dataset.isSkeleton) {
                        setCommentaryThinking(containers.result_commentary, false);
                        preElement.textContent = '';
                      }
                      preElement.textContent += msg.delta;
                    }
                  }
                } else if (containers[msg.field]) {
                  const preElement = containers[msg.field].querySelector('pre');
                  if (preElement) {
                    preElement.textContent += msg.delta;
                  }
                }
                convoView.scrollTop = convoView.scrollHeight;
              } else if(msg.event === 'replace' && containers && msg.field && msg.content !== undefined){
                // Replace the entire content (used to fix escape sequence issues)
                if (msg.field === 'generated_code') {
                  revealGeneratedCode();
                  const codeElement = containers[msg.field].querySelector('code');
                  if (codeElement) {
                    codeElement.textContent = msg.content;
                    // Apply syntax highlighting
                    Prism.highlightElement(codeElement);
                  }
                  ensureCommentaryPending();
                } else if (msg.field === 'initial_response') {
                  const preElement = getAnalysisPre(containers.initial_response);
                  if (preElement) {
                    setAnalysisThinking(containers.initial_response, false);
                    preElement.textContent = msg.content || '';
                  }
                } else if (msg.field === 'result_commentary') {
                  const preElement = getCommentaryPre(containers.result_commentary);
                  if (preElement) {
                    setCommentaryThinking(containers.result_commentary, false);
                    preElement.textContent = msg.content || '';
                  }
                } else if (containers[msg.field]) {
                  const preElement = containers[msg.field].querySelector('pre');
                  if (preElement) {
                    preElement.textContent = msg.content;
                  }
                }
                convoView.scrollTop = convoView.scrollHeight;
              } else if(msg.event === 'end' && msg.final){
                if (containers && containers.initial_response) {
                  setAnalysisThinking(containers.initial_response, false);
                }
                if (containers && containers.result_commentary) {
                  revealCommentary();
                  const commentaryPre = getCommentaryPre(containers.result_commentary);
                  if (commentaryPre && commentaryPre.textContent && commentaryPre.textContent.trim()) {
                    setCommentaryThinking(containers.result_commentary, false);
                  }
                }
                // Apply syntax highlighting to the final code
                if (containers && containers.generated_code) {
                  const codeElement = containers.generated_code.querySelector('code');
                  if (codeElement && codeElement.textContent.trim()) {
                    Prism.highlightElement(codeElement);
                  }
                }
                // Handle final response and extract visualizations
                handleFinalResponse(msg.final);
              }
            } catch(e){ console.error('WS message parse error', e); }
          };
          ws.onclose = ()=>{ ws = null; };
        }

        function sendMessage(){
          const text = (input.value || '').trim();
          if(!text) return;

          // Show user message immediately
          displayUserMessage(text);

          // Function to actually send the message
          const doSend = () => {
            if(ws && ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ message: text }));
              input.value = '';
              return true;
            }
            return false;
          };

          // Try to send immediately if WebSocket is open
          if(doSend()) {
            return;
          }

          // If WebSocket is not ready, establish connection and wait
          if(!ws || ws.readyState === WebSocket.CLOSED) {
            connectWS();
          }

          // Set up onopen handler to send when ready
          if(ws) {
            ws.onopen = () => {
              doSend();
            };
          }
        }

        function displayUserMessage(message) {
          // Switch to conversation view if not already shown
          if (!convoView.classList.contains('hidden')) {
            // Already in conversation view, just add the message
          } else {
            // First message - switch views
            startView.classList.add('hidden');
            convoView.classList.remove('hidden');
          }

          // Create user message container
          const userMessageDiv = document.createElement('div');
          userMessageDiv.className = 'mb-6 flex justify-end relative z-10 user-message';
          userMessageDiv.innerHTML = `
            <div class="user-message-bubble max-w-xs lg:max-w-md px-5 py-3.5 text-white rounded-2xl">
              <p class="text-sm leading-relaxed">${message}</p>
            </div>
          `;

          convoView.appendChild(userMessageDiv);
          convoView.scrollTop = convoView.scrollHeight;
        }

        function sendUploadRequest(formData, {onProgress, onIndeterminate, onUploadComplete} = {}) {
          return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/upload', true);
            xhr.responseType = 'json';

            let indeterminateNotified = false;

            if (xhr.upload) {
              xhr.upload.onprogress = (event) => {
                if (event.lengthComputable && typeof onProgress === 'function') {
                  const percent = (event.loaded / event.total) * 100;
                  onProgress(percent);
                } else if (!event.lengthComputable && typeof onIndeterminate === 'function' && !indeterminateNotified) {
                  indeterminateNotified = true;
                  onIndeterminate();
                }
              };
              xhr.upload.onloadend = () => {
                if (typeof onUploadComplete === 'function') {
                  onUploadComplete();
                }
              };
            }

            xhr.onload = () => {
              let payload = xhr.response;
              if (payload == null || payload === '') {
                payload = safeJsonParse(xhr.responseText);
              } else if (typeof payload === 'string') {
                payload = safeJsonParse(payload);
              }
              resolve({status: xhr.status, body: payload});
            };

            xhr.onerror = () => reject(new Error('Network error during upload'));
            xhr.onabort = () => reject(new Error('Upload aborted'));

            xhr.send(formData);
          });
        }

        async function uploadFile(file) {
          const formData = new FormData();
          formData.append('file', file);

          if (welcomeDropzone) {
            welcomeDropzone.classList.remove('file-loaded');
          }
          if (welcomeUploadPrompt) {
            welcomeUploadPrompt.textContent = 'Preparing your file for analysis...';
          }
          setWelcomeStatus(`Uploading ${file.name}...`, 'pending');
          startUploadProgress(file.name);

          try {
            const {status, body} = await sendUploadRequest(formData, {
              onProgress: (percent) => {
                const clamped = Math.max(0, Math.min(100, Math.round(percent)));
                updateUploadProgressDisplay(clamped);
                if (!uploadProgressProcessingShown) {
                  setWelcomeStatus(`Uploading ${file.name} (${clamped}%)`, 'pending');
                }
              },
              onIndeterminate: () => {
                if (!uploadProgressProcessingShown) {
                  setUploadProgressToIndeterminate(file.name);
                  setWelcomeStatus(`Uploading ${file.name}...`, 'pending');
                }
              },
              onUploadComplete: () => {
                markUploadProcessing(`Processing ${file.name}...`, 'Processing');
                setWelcomeStatus(`Processing ${file.name}...`, 'pending');
              }
            });

            const result = body || {};

            if (status >= 200 && status < 300) {
              markUploadProcessing(`${file.name} ready for analysis`, 'Complete');
              setWelcomeStatus(`${file.name} uploaded successfully`, 'success');

              currentFile = result.file_info;
              updateFileInfo(currentFile);
              revealConversationView();
              alert('File uploaded successfully!');
              hideUploadProgress(700);
            } else {
              const detail = result.detail || 'Unknown error';
              hideUploadProgress(0);
              setWelcomeStatus(`Could not upload ${file.name}: ${detail}`, 'error');
              if (welcomeUploadPrompt) {
                welcomeUploadPrompt.textContent = defaultWelcomePrompt || 'Drag and drop a file here, or click to browse your device.';
              }
              alert('Upload failed: ' + detail);
            }
          } catch (error) {
            hideUploadProgress(0);
            const message = error && error.message ? error.message : 'Unexpected error';
            setWelcomeStatus(`Upload error: ${message}`, 'error');
            if (welcomeUploadPrompt) {
              welcomeUploadPrompt.textContent = defaultWelcomePrompt || 'Drag and drop a file here, or click to browse your device.';
            }
            alert('Upload error: ' + message);
          } finally {
            if (fileInput) {
              fileInput.value = '';
            }
            dropzoneDragDepth = 0;
            setDropzoneActive(false);
          }
        }

        function updateFileInfo(fileInfo) {
          if (!fileInfo) return;

          updateWelcomeFileStatus(fileInfo);

          // Update the file info section in the sidebar
          const fileInfoSection = document.querySelector('.mb-6.p-4.bg-background-light');
          if (fileInfoSection) {
            const rowsSpan = fileInfoSection.querySelector('.flex:nth-child(1) .font-medium');
            const colsSpan = fileInfoSection.querySelector('.flex:nth-child(2) .font-medium');
            const sizeSpan = fileInfoSection.querySelector('.flex:nth-child(3) .font-medium');

            if (rowsSpan) rowsSpan.textContent = fileInfo.rows.toLocaleString();
            if (colsSpan) colsSpan.textContent = fileInfo.columns;
            if (sizeSpan) sizeSpan.textContent = fileInfo.size_mb + ' MB';
          }
        }

        function handleFinalResponse(finalResponse) {
          // Check if we need to fetch execution results for visualizations and results block
          if (finalResponse.generated_code && finalResponse.generated_code.trim()) {
            // Show skeleton loader and Results Block container
            const resultsBlock = containers.results_block;
            const skeleton = resultsBlock.querySelector('#results-skeleton');
            const actualResults = resultsBlock.querySelector('#results-actual');

            // Show the Results Block container and skeleton loader
            resultsBlock.classList.remove('hidden');
            skeleton.classList.remove('hidden');
            actualResults.classList.add('hidden');

            // Execute the code to get visualizations and results
            fetch('/execute-code', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({code: finalResponse.generated_code})
            })
            .then(response => response.json())
            .then(result => {
              // Hide skeleton loader
              skeleton.classList.add('hidden');

              if (result.status === 'success' && result.results) {
                displayVisualizations(result.results);
                displayResultsBlock(result.results);
              } else {
                // If execution failed, hide the Results Block entirely
                resultsBlock.classList.add('hidden');
              }
            })
            .catch(error => {
              console.error('Error executing code for visualizations:', error);
              // Hide skeleton and Results Block on error
              skeleton.classList.add('hidden');
              resultsBlock.classList.add('hidden');
            });
          }
        }

        function displayResultsBlock(results) {
          // Extract primary result from execution results
          let primaryResult = null;
          let primaryResultKey = null;

          // Look for the main result variable in priority order
          const priorityKeys = ['result', 'output', 'summary', 'analysis', 'answer'];
          for (const key of priorityKeys) {
            if (results.hasOwnProperty(key) && results[key] !== null && results[key] !== undefined) {
              primaryResult = results[key];
              primaryResultKey = key;
              break;
            }
          }

          // If we found a primary result, display it prominently
          if (primaryResult !== null && primaryResult !== undefined) {
            const resultsBlock = containers.results_block;
            const actualResults = resultsBlock.querySelector('#results-actual');
            const valueElement = resultsBlock.querySelector('#primary-result-value');
            const labelElement = resultsBlock.querySelector('#primary-result-label');

            // Format the result value
            let displayValue = primaryResult;
            if (typeof primaryResult === 'number') {
              // Format numbers nicely
              displayValue = primaryResult.toLocaleString(undefined, {
                maximumFractionDigits: 2
              });
            } else if (typeof primaryResult === 'object') {
              // For objects/arrays, show a summary
              if (Array.isArray(primaryResult)) {
                displayValue = `${primaryResult.length} items`;
              } else {
                displayValue = JSON.stringify(primaryResult, null, 2);
              }
            }

            valueElement.textContent = displayValue;
            labelElement.textContent = `Primary result from '${primaryResultKey}' variable`;

            // Show the actual results container (skeleton is already hidden by handleFinalResponse)
            actualResults.classList.remove('hidden');
            resultsBlock.classList.remove('hidden');
          } else {
            // No primary result found, hide the entire Results Block
            const resultsBlock = containers.results_block;
            resultsBlock.classList.add('hidden');
          }
        }

        function displayVisualizations(results) {
          const vizContainer = containers.visualizations.querySelector('.viz-container');
          // Clear previous visualizations to avoid stale/duplicate plots
          vizContainer.innerHTML = '';
          let hasViz = false;

          // Look for Plotly figures in results
          Object.keys(results).forEach(key => {
            if (key.includes('plotly_figure') && results[key].type === 'plotly_figure') {
              hasViz = true;

              // Create a div for this visualization
              const vizDiv = document.createElement('div');
              vizDiv.className = 'mb-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 relative z-10';
              vizDiv.style.animation = 'fadeInUp 0.4s ease-out';
              vizDiv.id = 'plot_' + Math.random().toString(36).substr(2, 9);

              // Add title with icon
              const title = document.createElement('div');
              title.className = 'flex items-center text-sm font-medium mb-3 text-gray-700 dark:text-gray-300';
              title.innerHTML = `
                <span class="card-header-icon mr-2">
                  <span class="material-symbols-outlined text-xs text-primary dark:text-blue-300">show_chart</span>
                </span>
                ${key.replace('plotly_figure_', '').replace(/_/g, ' ').toUpperCase()}
              `;
              vizDiv.appendChild(title);

              // Add plot container
              const plotDiv = document.createElement('div');
              plotDiv.id = vizDiv.id + '_plot';
              plotDiv.style.width = '100%';
              plotDiv.style.height = '400px';
              plotDiv.style.minHeight = '400px';
              vizDiv.appendChild(plotDiv);

              vizContainer.appendChild(vizDiv);

              // Render the Plotly figure
              try {
                const figData = JSON.parse(results[key].json);
                Plotly.newPlot(plotDiv.id, figData.data, figData.layout, {
                  responsive: true,
                  displayModeBar: true,
                  modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
                  displaylogo: false
                });
              } catch (error) {
                console.error('Error rendering Plotly figure:', error);
                plotDiv.innerHTML = '<p class="text-red-500">Error rendering visualization</p>';
              }
            }
          });

          // Show visualizations container if we have any
          if (hasViz) {
            containers.visualizations.classList.remove('hidden');
          }
        }

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keydown', (e)=>{
          if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); sendMessage(); }
        });

        fileInput.addEventListener('change', (e) => {
          const file = e.target.files[0];
          if (file) {
            uploadFile(file);
          }
        });

        // Premium Input Enhancements
        const inputContainer = document.getElementById('input-container');

        // Auto-resize textarea
        input.addEventListener('input', function() {
          this.style.height = 'auto';
          this.style.height = Math.min(this.scrollHeight, 128) + 'px'; // max 128px (max-h-32)

          // Toggle pulse animation on send button when content exists
          if (this.value.trim()) {
            sendBtn.classList.add('has-content');
          } else {
            sendBtn.classList.remove('has-content');
          }
        });

        // Focus/blur effects for input container
        input.addEventListener('focus', () => {
          inputContainer.classList.add('focused');
        });

        input.addEventListener('blur', () => {
          inputContainer.classList.remove('focused');
        });

        // Reset textarea height after sending
        const originalSendMessage = sendMessage;
        sendMessage = function() {
          originalSendMessage();
          input.style.height = 'auto';
          sendBtn.classList.remove('has-content');
        };

        // Load existing file info on page load
        fetch('/file-info')
          .then(response => response.json())
          .then(result => {
            if (result.status === 'success') {
              currentFile = result.file_info;
              updateFileInfo(currentFile);
              revealConversationView();
            }
          })
          .catch(error => console.log('No existing file'));
      })();

        // Load existing rules on page load
        loadRules();

        // Rules management functions
        function loadRules() {
          fetch('/rules')
            .then(response => response.json())
            .then(result => {
              if (result.status === 'success') {
                displayRules(result.rules);
              }
            })
            .catch(error => console.error('Error loading rules:', error));
        }

        function displayRules(rules) {
          const container = document.getElementById('rulesContainer');

          if (rules.length === 0) {
            container.innerHTML = '<p class="text-center">No custom rules defined</p>';
            return;
          }

          container.innerHTML = rules.map(rule => `
            <div class="flex justify-between items-start p-2 bg-gray-100 dark:bg-gray-600 rounded mb-2 relative z-10">
              <div class="flex-1 mr-2">
                <p class="text-xs break-words">${rule.text}</p>
                <span class="text-xs text-gray-400">${rule.category}</span>
              </div>
              <button onclick="deleteRule(${rule.id})" class="ml-2 text-red-500 hover:text-red-700 flex-shrink-0 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900 transition-colors">
                <span class="material-symbols-outlined text-sm">delete</span>
              </button>
            </div>
          `).join('');
        }

        function addRule() {
          const ruleText = prompt('Enter a new rule:');
          if (!ruleText || !ruleText.trim()) return;

          const category = prompt('Enter category (optional):', 'general') || 'general';

          fetch('/rules', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              text: ruleText.trim(),
              category: category.trim(),
              priority: 1
            })
          })
          .then(response => response.json())
          .then(result => {
            if (result.status === 'success') {
              loadRules(); // Reload rules
            } else {
              alert('Failed to add rule: ' + result.message);
            }
          })
          .catch(error => {
            console.error('Error adding rule:', error);
            alert('Failed to add rule');
          });
        }

        function deleteRule(ruleId) {
          if (!confirm('Are you sure you want to delete this rule?')) return;

          fetch(`/rules/${ruleId}`, {
            method: 'DELETE'
          })
          .then(response => response.json())
          .then(result => {
            if (result.status === 'success') {
              loadRules(); // Reload rules
            } else {
              alert('Failed to delete rule: ' + result.message);
            }
          })
          .catch(error => {
            console.error('Error deleting rule:', error);
            alert('Failed to delete rule');
          });
        }

        // Add event listener for add rule button
        document.getElementById('addRuleBtn').addEventListener('click', addRule);

        // Copy code to clipboard function
        function copyCodeToClipboard(button) {
          const codeBlock = button.closest('.code-block-container');
          const codeElement = codeBlock.querySelector('code');
          const code = codeElement.textContent;

          navigator.clipboard.writeText(code).then(() => {
            // Show feedback
            const originalText = button.innerHTML;
            button.innerHTML = '<span class="material-symbols-outlined" style="font-size: 14px;">check</span>Copied!';
            button.style.background = '#059669';

            setTimeout(() => {
              button.innerHTML = originalText;
              button.style.background = '';
            }, 2000);
          }).catch(err => {
            console.error('Failed to copy code: ', err);
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = code;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);

            // Show feedback
            const originalText = button.innerHTML;
            button.innerHTML = '<span class="material-symbols-outlined" style="font-size: 14px;">check</span>Copied!';
            button.style.background = '#059669';

            setTimeout(() => {
              button.innerHTML = originalText;
              button.style.background = '';
            }, 2000);
          });
        }

        // Make function globally available
        window.copyCodeToClipboard = copyCodeToClipboard;
        window.deleteRule = deleteRule;
        window.addRule = addRule;




