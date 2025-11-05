// Initialize all services and features
const app = {
    data() {
        return {
            // State management
            inputType: 'url',
            url: '',
            file: null,
            rawText: '',
            selectedModel: 'facebook/bart-large-cnn',
            processing: false,
            currentStage: 'Ready',
            progress: 0,
            jobId: null,
            error: null,
            theme: localStorage.getItem('theme') || 'dark',
            language: localStorage.getItem('language') || 'en',

            // Results
            transcript: '',
            summaries: {
                short: '',
                detailed: '',
                bullets: []
            },
            chapters: [],
            quiz: {
                mcq: [],
                true_false: []
            },
            sentiment: {
                overall: '',
                emotions: {},
                confidence: 0
            },
            translations: {},
            
            // UI State
            activeTab: 'transcript',
            showQuiz: false,
            quizScore: 0,
            answeredQuestions: new Set(),
            currentChapterIndex: 0,
            isPlaying: false,
            currentTime: 0,
            duration: 0,
            
            // Media
            mediaUrl: null,
            mediaType: null,
            mediaPlayer: null,
            
            // History
            jobHistory: JSON.parse(localStorage.getItem('jobHistory') || '[]'),
            favorites: new Set(JSON.parse(localStorage.getItem('favorites') || '[]'))
        }
    },

    mounted() {
        this.initializeTheme();
        this.initializeLanguage();
        this.setupMediaHandlers();
        this.loadHistory();
    },

    methods: {
        async submitJob() {
            try {
                this.processing = true;
                this.error = null;
                this.progress = 0;
                this.currentStage = 'Initializing';

                const formData = new FormData();
                formData.append('type', this.inputType);

                if (this.inputType === 'url') {
                    formData.append('url', this.url);
                } else if (this.inputType === 'file') {
                    formData.append('file', this.file);
                } else {
                    formData.append('text', this.rawText);
                }

                const response = await fetch('/api/v1/submit', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error('Job submission failed');

                const { job_id } = await response.json();
                this.jobId = job_id;
                this.pollJobStatus();

            } catch (error) {
                this.handleError('Failed to submit job', error);
            }
        },

        async pollJobStatus() {
            if (!this.jobId) return;

            try {
                const response = await fetch(`/api/v1/status/${this.jobId}`);
                if (!response.ok) throw new Error('Status check failed');

                const { stage, progress, logs } = await response.json();
                this.currentStage = stage;
                this.progress = progress;

                if (stage === 'completed') {
                    await this.fetchResults();
                    this.saveToHistory();
                } else if (stage === 'failed') {
                    throw new Error('Job processing failed');
                } else {
                    setTimeout(() => this.pollJobStatus(), 1000);
                }

            } catch (error) {
                this.handleError('Job status check failed', error);
            }
        },

        async fetchResults() {
            try {
                const response = await fetch(`/api/v1/result/${this.jobId}`);
                if (!response.ok) throw new Error('Failed to fetch results');

                const results = await response.json();
                
                this.transcript = results.transcript;
                this.summaries = results.summaries;
                this.chapters = results.chapters;
                this.quiz = results.quiz;
                this.sentiment = results.sentiment;
                this.translations = results.translations;

                this.processing = false;
                this.initializeMedia();

            } catch (error) {
                this.handleError('Failed to fetch results', error);
            }
        },

        async exportResults(format) {
            try {
                let url, filename;

                switch (format) {
                    case 'pdf':
                        const pdfResponse = await fetch(`/api/v1/export/pdf/${this.jobId}`);
                        const pdfBlob = await pdfResponse.blob();
                        url = URL.createObjectURL(pdfBlob);
                        filename = `summary-${this.jobId}.pdf`;
                        break;

                    case 'markdown':
                        const mdContent = this.generateMarkdown();
                        const mdBlob = new Blob([mdContent], { type: 'text/markdown' });
                        url = URL.createObjectURL(mdBlob);
                        filename = `summary-${this.jobId}.md`;
                        break;

                    case 'json':
                        const jsonContent = JSON.stringify(this.getExportData(), null, 2);
                        const jsonBlob = new Blob([jsonContent], { type: 'application/json' });
                        url = URL.createObjectURL(jsonBlob);
                        filename = `summary-${this.jobId}.json`;
                        break;
                }

                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
                URL.revokeObjectURL(url);

            } catch (error) {
                this.handleError(`Failed to export as ${format}`, error);
            }
        },

        generateMarkdown() {
            return `# Summary Report

## Transcript
${this.transcript}

## Summaries
### Short Summary
${this.summaries.short}

### Detailed Summary
${this.summaries.detailed}

### Key Points
${this.summaries.bullets.map(point => `- ${point}`).join('\n')}

## Chapters
${this.chapters.map(chapter => `
### ${chapter.title}
Time: ${chapter.start_time} - ${chapter.end_time}
${chapter.content}
`).join('\n')}

## Quiz
### Multiple Choice Questions
${this.quiz.mcq.map((q, i) => `
${i + 1}. ${q.question}
${q.options.map(opt => `   - ${opt}`).join('\n')}
Answer: ${q.correct_answer}
`).join('\n')}

### True/False Questions
${this.quiz.true_false.map((q, i) => `
${i + 1}. ${q.question}
Answer: ${q.correct_answer}
`).join('\n')}

## Sentiment Analysis
Overall: ${this.sentiment.overall}
Confidence: ${this.sentiment.confidence}

### Emotions
${Object.entries(this.sentiment.emotions).map(([emotion, score]) => `- ${emotion}: ${score}`).join('\n')}
`;
        },

        getExportData() {
            return {
                jobId: this.jobId,
                timestamp: new Date().toISOString(),
                transcript: this.transcript,
                summaries: this.summaries,
                chapters: this.chapters,
                quiz: this.quiz,
                sentiment: this.sentiment,
                translations: this.translations
            };
        },

        handleQuizAnswer(questionId, answer) {
            if (this.answeredQuestions.has(questionId)) return;

            const question = this.quiz.mcq.find(q => q.id === questionId) ||
                           this.quiz.true_false.find(q => q.id === questionId);

            if (question.correct_answer === answer) {
                this.quizScore++;
            }

            this.answeredQuestions.add(questionId);
        },

        async translateText(text, targetLang) {
            try {
                const response = await fetch('/api/v1/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, target_lang: targetLang })
                });

                if (!response.ok) throw new Error('Translation failed');

                const result = await response.json();
                return result.translated_text;

            } catch (error) {
                this.handleError('Translation failed', error);
                return text;
            }
        },

        initializeMedia() {
            if (this.mediaUrl) {
                this.mediaPlayer = document.createElement(this.mediaType);
                this.mediaPlayer.src = this.mediaUrl;
                this.mediaPlayer.addEventListener('timeupdate', this.handleTimeUpdate);
                this.mediaPlayer.addEventListener('loadedmetadata', () => {
                    this.duration = this.mediaPlayer.duration;
                });
            }
        },

        handleTimeUpdate() {
            this.currentTime = this.mediaPlayer.currentTime;
            this.updateCurrentChapter();
        },

        updateCurrentChapter() {
            const currentTime = this.currentTime;
            const newIndex = this.chapters.findIndex(chapter => 
                currentTime >= chapter.start_seconds && currentTime < chapter.end_seconds
            );

            if (newIndex !== -1 && newIndex !== this.currentChapterIndex) {
                this.currentChapterIndex = newIndex;
            }
        },

        jumpToChapter(index) {
            if (this.mediaPlayer && this.chapters[index]) {
                this.mediaPlayer.currentTime = this.chapters[index].start_seconds;
                this.mediaPlayer.play();
            }
        },

        saveToHistory() {
            const historyItem = {
                jobId: this.jobId,
                timestamp: new Date().toISOString(),
                title: this.summaries.short.slice(0, 100),
                type: this.inputType,
                favorite: false
            };

            this.jobHistory.unshift(historyItem);
            this.jobHistory = this.jobHistory.slice(0, 50); // Keep last 50 items
            localStorage.setItem('jobHistory', JSON.stringify(this.jobHistory));
        },

        toggleFavorite(jobId) {
            if (this.favorites.has(jobId)) {
                this.favorites.delete(jobId);
            } else {
                this.favorites.add(jobId);
            }
            localStorage.setItem('favorites', JSON.stringify([...this.favorites]));
        },

        handleError(message, error) {
            console.error(message, error);
            this.error = message;
            this.processing = false;
        },

        initializeTheme() {
            document.documentElement.classList.toggle('dark', this.theme === 'dark');
        },

        toggleTheme() {
            this.theme = this.theme === 'dark' ? 'light' : 'dark';
            this.initializeTheme();
            localStorage.setItem('theme', this.theme);
        },

        initializeLanguage() {
            document.documentElement.lang = this.language;
        },

        changeLanguage(lang) {
            this.language = lang;
            this.initializeLanguage();
            localStorage.setItem('language', lang);
        }
    }
};

// Initialize Alpine.js
document.addEventListener('alpine:init', () => {
    Alpine.data('app', app);
});