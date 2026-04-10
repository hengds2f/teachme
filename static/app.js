document.addEventListener('DOMContentLoaded', () => {
    
    // Global Math Renderer
    function renderMath() {
        if (typeof renderMathInElement === 'function') {
            renderMathInElement(document.body, {
                delimiters: [
                    {left: "$$", right: "$$", display: true},
                    {left: "$", right: "$", display: false},
                    {left: "\\(", right: "\\)", display: false},
                    {left: "\\[", right: "\\]", display: true},
                    {left: "[", right: "]", display: true} // Fallback for raw square brackets
                ],
                throwOnError : false
            });
        }
    }

    // 0. Auto-Recovery Logic (Session Restoration)
    const urlParams = new URLSearchParams(window.location.search);
    const isNewSubject = urlParams.get('new') === '1';
    const hasUserId = urlParams.has('user_id');

    if (isNewSubject) {
        localStorage.removeItem('teachme_curriculum');
        console.log("New Subject requested. Clearing local cache.");
    }

    if (document.getElementById('setupForm') && !isNewSubject && !hasUserId) {
        // ONLY SYNC if we aren't already identified by a Google session
        const savedData = localStorage.getItem('teachme_curriculum');
        if (savedData) {
            const data = JSON.parse(savedData);
            // Hide setup form and show loader
            document.getElementById('setupForm').style.display = 'none';
            const loader = document.getElementById('loader');
            loader.classList.remove('loader-hidden');
            loader.querySelector('p').innerText = "Restoring your last academic session...";
            
            fetch('/api/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(syncData => {
                if (syncData.status === 'success') {
                    renderMath();
                    window.location.href = '/?user_id=' + syncData.user_id;
                }
            })
            .catch(err => {
                console.error("Auto-recovery failed", err);
                // If restore fails, allow user to try manual setup
                document.getElementById('setupForm').style.display = 'block';
                loader.classList.add('loader-hidden');
            });
            
            // Exit early while we recover
            return;
        }
    }

    // Setup Form Logic
    const setupForm = document.getElementById('setupForm');
    if (setupForm) {
        setupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const subject = document.getElementById('subject').value;
            const level = document.getElementById('level').value;
            const goal = document.getElementById('goal').value;
            const background = document.getElementById('background').value;
            
            setupForm.style.display = 'none';
            document.getElementById('loader').classList.remove('loader-hidden');
            
            try {
                const response = await fetch('/api/setup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ subject, level, goal, background, style: '' })
                });
                
                const data = await response.json();
                if (data.status === 'success') {
                    // SAVE TO LOCAL STORAGE FOR OFFLINE-FIRST PERSISTENCE
                    localStorage.setItem('teachme_curriculum', JSON.stringify({
                        subject: data.subject,
                        level: data.level,
                        topics: data.topics
                    }));
                    window.location.href = '/?user_id=' + data.user_id;
                } else {
                    alert('Error creating curriculum. Please try again.');
                    setupForm.style.display = 'block';
                    document.getElementById('loader').classList.add('loader-hidden');
                }
            } catch (err) {
                console.error(err);
                alert('Network error.');
                setupForm.style.display = 'block';
                document.getElementById('loader').classList.add('loader-hidden');
            }
        });
    }

    // 2. Dashboard Stats & Recommendation
    if (document.querySelector('.curriculum-grid-container')) {
        updateDashboardStats();
    }

    function updateDashboardStats() {
        const cards = document.querySelectorAll('.topic-card');
        const completed = document.querySelectorAll('.topic-card.completed').length;
        const total = cards.length;
        const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

        const progressFill = document.getElementById('progress-fill');
        const progressPercent = document.getElementById('progress-percent');
        if (progressFill) progressFill.style.width = percent + '%';
        if (progressPercent) progressPercent.innerText = percent + '%';

        // Recommendation Logic: First non-completed card
        const nextTopic = Array.from(cards).find(c => !c.classList.contains('completed'));
        const recArea = document.getElementById('recommendation-area');
        if (nextTopic && recArea) {
            recArea.classList.remove('loader-hidden');
            document.getElementById('rec-title').innerText = nextTopic.querySelector('h3').innerText;
            document.getElementById('rec-desc').innerText = nextTopic.querySelector('p').innerText;
            document.getElementById('rec-link').href = nextTopic.href;
        }
    }

    // 3. Session Summary Flow
    const endSessionBtn = document.getElementById('endSessionBtn');
    const summaryModal = document.getElementById('summaryModal');
    if (endSessionBtn && summaryModal) {
        endSessionBtn.addEventListener('click', async () => {
            summaryModal.classList.remove('modal-hidden');
            summaryModal.style.display = 'flex';
            const body = document.getElementById('summary-body');
            body.innerHTML = '<div class="spinner"></div><p>Generating Academic Report...</p>';

            try {
                const res = await fetch('/api/session/summary');
                const data = await res.json();
                body.innerHTML = data.summary_html;
            } catch (e) {
                body.innerHTML = '<p>Error generating summary. You have made excellent progress!</p>';
            }
        });

        document.getElementById('closeSummary').addEventListener('click', () => {
            summaryModal.style.display = 'none';
        });
    }

    // Topic Guide Chunk Generation
    const learningContainer = document.getElementById('learning-container');
    if (learningContainer) {
        initTopicGuide();

        function initTopicGuide() {
            const chunksArea = document.getElementById('chunks-area');
            const roadmapSteps = document.querySelectorAll('.roadmap-step');
            
            // Highlight existing steps
            const loadedTypes = Array.from(chunksArea.querySelectorAll('.chunk-box')).map(c => {
                const label = c.querySelector('.chunk-label').innerText.toLowerCase();
                return label;
            });
            
            roadmapSteps.forEach(step => {
                const type = step.id.replace('step-', '');
                const isLoaded = loadedTypes.some(lt => lt.includes(type) || (type === 'concept' && lt.includes('use case')));
                if (isLoaded) {
                    step.classList.add('active');
                }
            });

            // AUTO-TRIGGER first concept if empty
            if (chunksArea.children.length === 0) {
                const conceptBtn = document.querySelector('.dynamic-btn[data-type="concept"]');
                if (conceptBtn) {
                    console.log("Auto-initializing topic with first Use Case & Concept...");
                    conceptBtn.click();
                }
            }
        }

        const topicId = learningContainer.dataset.topicId;
        const chunksArea = document.getElementById('chunks-area');
        const chunkControls = document.getElementById('chunk-controls');
        const chunkLoader = document.getElementById('chunk-loader');
        
        // Dynamic chunk generation buttons
        document.querySelectorAll('.dynamic-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const chunkType = btn.dataset.type;
                
                chunkControls.style.display = 'none';
                chunkLoader.classList.remove('loader-hidden');
                chunkLoader.scrollIntoView({ behavior: 'smooth' });
                
                try {
                    const response = await fetch('/api/chunk/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ topic_id: topicId, chunk_type: chunkType })
                    });
                    
                    const data = await response.json();
                    if (data.content_html) {
                        const newChunkBox = document.createElement('div');
                        newChunkBox.className = `chunk-box chunk-${data.type}`;
                        const labelText = data.type === 'check' ? 'RETRIEVAL PRACTICE' : data.type.toUpperCase();
                        newChunkBox.innerHTML = `
                            <div class="chunk-label">${labelText}</div>
                            <div class="chunk-content">${data.content_html}</div>
                        `;
                        chunksArea.appendChild(newChunkBox);
                        newChunkBox.scrollIntoView({ behavior: 'smooth' });
                        
                        // Update roadmap
                        const step = document.getElementById(`step-${data.type}`);
                        if (step) step.classList.add('active');

                        // AUTOMATED RETRIEVAL INTERLEAVING
                        if (data.type === 'concept' || data.type === 'example') {
                            checkInterleaving();
                        }
                        renderMath();
                    }
                } catch (err) {
                    console.error('Error generating chunk:', err);
                    alert("Failed to generate content.");
                } finally {
                    chunkLoader.classList.add('loader-hidden');
                    chunkControls.style.display = 'block';
                }
            });
        });

        function checkInterleaving() {
            const chunks = Array.from(chunksArea.querySelectorAll('.chunk-box'));
            let informationalCount = 0;
            
            // Look at the sequence of chunks from the end
            for (let i = chunks.length - 1; i >= 0; i--) {
                const typeLabel = chunks[i].querySelector('.chunk-label').innerText.toLowerCase();
                if (typeLabel.includes('practice') || typeLabel.includes('check')) {
                    break; // Met a check already
                }
                if (typeLabel.includes('concept') || typeLabel.includes('example') || typeLabel.includes('use case')) {
                    informationalCount++;
                }
            }

            if (informationalCount >= 2) {
                console.log("Pedagogical Cluster detected. Injecting Retrieval Practice...");
                const checkBtn = document.querySelector('.dynamic-btn[data-type="check"]');
                if (checkBtn) {
                    // Update label slightly for transparency
                    const originalText = checkBtn.innerText;
                    checkBtn.innerText = "Interleaving Check...";
                    setTimeout(() => {
                        checkBtn.click();
                        checkBtn.innerText = originalText;
                    }, 1000);
                }
            }
        }

        // Mark complete button
        const markCompleteBtn = document.getElementById('markCompleteBtn');
        if (markCompleteBtn) {
            markCompleteBtn.addEventListener('click', async () => {
                try {
                    await fetch('/api/topic/complete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ topic_id: topicId })
                    });
                    // Reload to show completion state
                    window.location.reload();
                } catch (err) {
                    console.error('Error completing:', err);
                }
            });
        }
        
        // Re-explain Modal Logic
        const fabStuck = document.getElementById('fab-stuck');
        const modal = document.getElementById('reexplainModal');
        const cancelReexplain = document.getElementById('cancelReexplain');
        const submitReexplain = document.getElementById('submitReexplain');
        const feedbackText = document.getElementById('feedbackText');
        const modalSpinner = document.getElementById('modal-spinner');

        fabStuck.addEventListener('click', () => {
            modal.style.display = 'flex';
        });

        cancelReexplain.addEventListener('click', () => {
            modal.style.display = 'none';
            feedbackText.value = '';
        });

        submitReexplain.addEventListener('click', async () => {
            const feedback = feedbackText.value;
            if (!feedback.trim()) return;

            // Get the last concept's text context as context
            const allChunks = document.querySelectorAll('.chunk-content');
            let lastConceptText = "";
            if (allChunks.length > 0) {
                lastConceptText = allChunks[allChunks.length - 1].innerText;
            }

            modalSpinner.classList.remove('loader-hidden');
            submitReexplain.disabled = true;

            try {
                const response = await fetch('/api/chunk/reexplain', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ concept: lastConceptText, feedback: feedback })
                });

                const data = await response.json();
                
                modal.style.display = 'none';
                feedbackText.value = '';
                
                if (data.content_html) {
                    const newChunkBox = document.createElement('div');
                    newChunkBox.className = `chunk-box chunk-reexplain`;
                    newChunkBox.style.borderLeftColor = 'var(--accent)';
                    newChunkBox.innerHTML = `
                        <div class="chunk-label">NEW EXPLANATION</div>
                        <div class="chunk-content">${data.content_html}</div>
                    `;
                    chunksArea.appendChild(newChunkBox);
                    newChunkBox.scrollIntoView({ behavior: 'smooth' });
                    renderMath();
                }

            } catch(e) {
                console.error(e);
                alert("Failed to get re-explanation.");
            } finally {
                modalSpinner.classList.add('loader-hidden');
                submitReexplain.disabled = false;
            }
        });
    }

    // Handle Curriculum Deletion
    document.querySelectorAll('.delete-curriculum-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const currId = btn.dataset.id;
            const subjectName = btn.dataset.subject;
            
            if (confirm(`Are you sure you want to permanently delete "${subjectName}"? All progress and notes for this subject will be lost.`)) {
                try {
                    const response = await fetch(`/api/curriculum/delete/${currId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    
                    const data = await response.json();
                    if (data.status === 'success') {
                        // If we are currently ON the dashboard of the deleted curriculum, redirect to home
                        const activeId = new URLSearchParams(window.location.search).get('curriculum_id');
                        if (activeId === currId || (!activeId && btn.closest('.library-item-wrapper').querySelector('.active'))) {
                            window.location.href = '/?new=1';
                        } else {
                            window.location.reload();
                        }
                    } else {
                        alert(`Error: ${data.message}`);
                    }
                } catch (err) {
                    console.error('Deletion error:', err);
                    alert('Failed to delete curriculum.');
                }
            }
        });
    });

    // Confirmation for reset (old legacy check, keep but ensure it doesn't conflict)
    document.querySelectorAll('a[href^="/reset"]').forEach(link => {
        link.addEventListener('click', (e) => {
            if (confirm('This will clear your current curriculum and progress. Are you sure?')) {
                localStorage.removeItem('teachme_curriculum');
            } else {
                e.preventDefault();
            }
        });
    });

    // Debug Environment Setup
    const debugEnvBtn = document.getElementById('debugEnvBtn');
    if (debugEnvBtn) {
        debugEnvBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                const response = await fetch('/api/debug/env');
                const data = await response.json();
                alert('DEBUG INFO:\n' + JSON.stringify(data, null, 2));
            } catch (err) {
                alert('Debug fetch failed: ' + err);
            }
        });
    }

    renderMath();
});

/* New Styles for Roadmap & Details */
const styleSheet = document.createElement("style");
styleSheet.innerText = `
    .roadmap-container { display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem; padding: 1.5rem; position: sticky; top: 100px; z-index: 80; }
    .roadmap-step { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; opacity: 0.3; transition: all 0.5s; cursor: pointer; flex: 1; }
    .roadmap-step.active { opacity: 1; color: var(--accent); }
    .step-num { width: 32px; height: 32px; border-radius: 50%; background: var(--secondary); display: flex; align-items: center; justify-content: center; font-weight: 700; border: 2px solid var(--glass-border); transition: all 0.3s;}
    .roadmap-step.active .step-num { background: var(--accent); border-color: #fff; box-shadow: 0 0 15px var(--accent); }
    .step-text { font-size: 0.75rem; text-transform: uppercase; font-weight: 700; letter-spacing: 1px; text-align: center; }
    .roadmap-line { flex-grow: 1; height: 2px; background: var(--glass-border); margin: 0 10px; margin-bottom: 1.5rem; }

    /* Details Styling */
    details { background: rgba(0,0,0,0.2); border-radius: 8px; border: 1px solid var(--glass-border); margin-top: 1.5rem; overflow: hidden; }
    summary { padding: 1rem; font-weight: 700; cursor: pointer; color: var(--accent); outline: none; list-style: none; transition: background 0.3s;}
    summary:hover { background: rgba(255,255,255,0.05); }
    summary::-webkit-details-marker { display: none; }
    details[open] summary { border-bottom: 1px solid var(--glass-border); background: rgba(0,0,0,0.3); }
    details > div { padding: 1.5rem; background: rgba(0,0,0,0.1); }
`;
document.head.appendChild(styleSheet);
