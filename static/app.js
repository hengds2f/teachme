document.addEventListener('DOMContentLoaded', () => {

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
                    window.location.href = '/';
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

    // Topic Guide Chunk Generation
    const learningContainer = document.getElementById('learning-container');
    if (learningContainer) {
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
                        newChunkBox.innerHTML = `
                            <div class="chunk-label">${data.type.toUpperCase()}</div>
                            <div class="chunk-content">${data.content_html}</div>
                        `;
                        chunksArea.appendChild(newChunkBox);
                        newChunkBox.scrollIntoView({ behavior: 'smooth' });
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
                }

            } catch(e) {
                console.error(e);
                alert("Failed to get re-explanation.");
            } finally {
                modalSpinner.classList.add('loader-hidden');
                submitReexplain.disabled = false;
            }
        });
    // Confirmation for reset
    document.querySelectorAll('a[href="/reset"]').forEach(link => {
        link.addEventListener('click', (e) => {
            if (!confirm('This will clear your current curriculum and progress. Are you sure?')) {
                e.preventDefault();
            }
        });
    });
});
