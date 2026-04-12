document.addEventListener('DOMContentLoaded', () => {
    
    // Mastery Sequence defined by the Instructional Design
    const MASTERY_SEQUENCE = [
        "intro", "level1", "level2", "level3", "level4", "level5", 
        "examples", "practice_guided", "practice_independent", 
        "checkpoints", "mini_project", "mistakes", "summary"
    ];

    const LEVEL_MAP = {
        "intro": "Orientation & Big Picture",
        "level1": "L1: Absolute Beginner",
        "level2": "L2: Expanding Horizons",
        "level3": "L3: Structural Analysis",
        "level4": "L4: Advanced theory",
        "level5": "L5: Mastery & Insight",
        "practice": "Applied Practice", // Groups examples + guided + independent
        "mastery": "Final Synthesis"    // Groups checkpoints + project + mistakes + summary
    };

    // Global Math Renderer
    function renderMath() {
        if (typeof renderMathInElement === 'function') {
            renderMathInElement(document.body, {
                delimiters: [
                    {left: "$$", right: "$$", display: true},
                    {left: "$", right: "$", display: false},
                    {left: "\\(", right: "\\)", display: false},
                    {left: "\\[", right: "\\]", display: true}
                ],
                throwOnError : false
            });
        }
    }

    // Auth & Sync Logic (Preserved)
    const urlParams = new URLSearchParams(window.location.search);
    const isNewSubject = urlParams.get('new') === '1';
    const hasUserId = urlParams.has('user_id');

    if (isNewSubject) {
        localStorage.removeItem('teachme_curriculum');
    }

    if (document.getElementById('setupForm') && !isNewSubject && !hasUserId) {
        const savedData = localStorage.getItem('teachme_curriculum');
        if (savedData) {
            const data = JSON.parse(savedData);
            document.getElementById('setupForm').style.display = 'none';
            const loader = document.getElementById('loader');
            loader.classList.remove('loader-hidden');
            
            fetch('/api/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(syncData => {
                if (syncData.status === 'success') {
                    window.location.href = '/?user_id=' + syncData.user_id;
                }
            })
            .catch(() => {
                document.getElementById('setupForm').style.display = 'block';
                loader.classList.add('loader-hidden');
            });
            return;
        }
    }

    // Setup Form
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
            
            const response = await fetch('/api/setup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subject, level, goal, background, style: '' })
            });
            const data = await response.json();
            if (data.status === 'success') {
                localStorage.setItem('teachme_curriculum', JSON.stringify({
                    subject: data.subject,
                    level: data.level,
                    topics: data.topics
                }));
                window.location.href = '/?user_id=' + data.user_id;
            }
        });
    }

    // Topic Guide Mastery Flow
    const learningContainer = document.getElementById('learning-container');
    if (learningContainer) {
        const topicId = learningContainer.dataset.topicId;
        const chunksArea = document.getElementById('chunks-area');
        const chunkLoader = document.getElementById('chunk-loader');
        const nextBtn = document.getElementById('nextChunkBtn');
        const roadmapItems = document.querySelectorAll('.roadmap-item');

        initMasteryFlow();

        function initMasteryFlow() {
            const loadedChunks = Array.from(chunksArea.querySelectorAll('.chunk-box')).map(c => {
                return Array.from(c.classList).find(cls => cls.startsWith('chunk-')).replace('chunk-', '');
            });

            updateRoadmap(loadedChunks);
            renderMath();
            
            // Roadmap Click Handling (Modular Access)
            roadmapItems.forEach(item => {
                item.addEventListener('click', () => {
                    const level = item.dataset.level;
                    
                    // If already loaded, scroll to it
                    const targetChunk = chunksArea.querySelector(`.chunk-${level}`);
                    if (targetChunk) {
                        targetChunk.scrollIntoView({ behavior: 'smooth' });
                        updateRoadmapState(level);
                        return;
                    }

                    // For grouped levels (Practice/Mastery), handle special entry points
                    let typeToGen = level;
                    if (level === 'practice') typeToGen = 'examples';
                    if (level === 'mastery') typeToGen = 'checkpoints';

                    const specificChunk = chunksArea.querySelector(`.chunk-${typeToGen}`);
                    if (specificChunk) {
                        specificChunk.scrollIntoView({ behavior: 'smooth' });
                    } else {
                        // Generate the standalone comprehensive section
                        generateChunk(typeToGen);
                    }
                });
            });

            // Handle Start Button
            const startBtn = document.querySelector('.start-lesson-btn');
            if (startBtn) {
                startBtn.addEventListener('click', () => {
                    generateChunk('intro');
                });
            }

            if (nextBtn) {
                nextBtn.addEventListener('click', () => {
                    const currentChunks = Array.from(chunksArea.querySelectorAll('.chunk-box')).map(c => {
                        return Array.from(c.classList).find(cls => cls.startsWith('chunk-')).replace('chunk-', '');
                    });
                    
                    const lastChunk = currentChunks[currentChunks.length - 1];
                    const nextIndex = MASTERY_SEQUENCE.indexOf(lastChunk) + 1;
                    
                    if (nextIndex < MASTERY_SEQUENCE.length) {
                        generateChunk(MASTERY_SEQUENCE[nextIndex]);
                    } else {
                        markTopicComplete();
                    }
                });
            }
        }

        async function generateChunk(type) {
            chunkLoader.classList.remove('loader-hidden');
            if (nextBtn) nextBtn.disabled = true;

            try {
                const response = await fetch('/api/chunk/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic_id: topicId, chunk_type: type })
                });
                
                const data = await response.json();
                if (data.content_html) {
                    const welcome = document.querySelector('.welcome-card');
                    if (welcome) welcome.remove();

                    const newBox = document.createElement('div');
                    newBox.className = `chunk-box chunk-${type} animate-in`;
                    newBox.innerHTML = `
                        <div class="chunk-label">${type.replace('_', ' ').toUpperCase()}</div>
                        <div class="chunk-content markdown-body">${data.content_html}</div>
                    `;
                    chunksArea.appendChild(newBox);
                    newBox.scrollIntoView({ behavior: 'smooth' });
                    
                    const loaded = Array.from(chunksArea.querySelectorAll('.chunk-box')).map(c => {
                        return Array.from(c.classList).find(cls => cls.startsWith('chunk-')).replace('chunk-', '');
                    });
                    updateRoadmap(loaded);
                    renderMath();
                }
            } catch (err) {
                console.error(err);
            } finally {
                chunkLoader.classList.add('loader-hidden');
                if (nextBtn) nextBtn.disabled = false;
            }
        }

        function updateRoadmap(loadedTypes) {
            roadmapItems.forEach(item => {
                const level = item.dataset.level;
                item.classList.remove('active', 'completed', 'locked');

                let isLoaded = false;
                if (level === 'practice') isLoaded = loadedTypes.includes('examples') || loadedTypes.includes('practice_guided');
                else if (level === 'mastery') isLoaded = loadedTypes.includes('checkpoints');
                else isLoaded = loadedTypes.includes(level);

                if (isLoaded) item.classList.add('completed');
                
                // All items are pointers in modular mode
                item.style.cursor = 'pointer';
                item.style.opacity = '1';
            });
        }

        function updateRoadmapState(activeLevel) {
            roadmapItems.forEach(item => {
                item.classList.remove('active');
                if (item.dataset.level === activeLevel) item.classList.add('active');
            });
        }

        async function markTopicComplete() {
            await fetch('/api/topic/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic_id: topicId })
            });
            window.location.href = '/';
        }

    }

    // Dashboard Stats (Preserved)
    if (document.querySelector('.curriculum-grid-container')) {
        const cards = document.querySelectorAll('.topic-card');
        const completed = document.querySelectorAll('.topic-card.completed').length;
        const total = cards.length;
        const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
        if (document.getElementById('progress-fill')) document.getElementById('progress-fill').style.width = percent + '%';
        if (document.getElementById('progress-percent')) document.getElementById('progress-percent').innerText = percent + '%';
    }

    renderMath();
});

function cleanJson(str) {
    let cleaned = str.replace(/```json\s?/g, '').replace(/```/g, '').trim();
    const firstBracket = cleaned.indexOf('[');
    const firstBrace = cleaned.indexOf('{');
    let start = (firstBracket !== -1 && (firstBrace === -1 || firstBracket < firstBrace)) ? firstBracket : firstBrace;
    let end = (start === firstBracket) ? cleaned.lastIndexOf(']') : cleaned.lastIndexOf('}');
    return (start !== -1 && end !== -1) ? cleaned.substring(start, end + 1) : str;
}

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
