function app() {
    return {
        // State
        inputType: 'url',
        url: '',
        file: null,
        rawText: '',
        selectedModel: 'facebook/bart-large-cnn',
        processing: false,
        currentStage: 'Initializing',
        progress: 0,
        jobId: null,
        transcript: '',
        summaries: {
            short: '',
            detailed: '',
            bullets: []
        },
        activeTab: 'short',
        mediaUrl: null,
        isVideo: false,
        isAudio: false,
        isImage: false,
        theme: 'dark',

        // Methods
        async init() {
            this.loadTheme()
            this.setupEventListeners()
        },

        setupEventListeners() {
            window.addEventListener('storage', this.handleStorageChange)
        },

        async submitJob() {
            try {
                this.processing = true
                this.progress = 0
                this.currentStage = 'Initializing'

                const formData = new FormData()
                formData.append('type', this.inputType)
                
                if (this.inputType === 'url') {
                    formData.append('url', this.url)
                } else if (this.inputType === 'file') {
                    formData.append('file', this.file)
                } else {
                    formData.append('text', this.rawText)
                }

                formData.append('options', JSON.stringify({
                    models: [this.selectedModel]
                }))

                const response = await fetch('/api/v1/submit', {
                    method: 'POST',
                    body: formData
                })

                if (!response.ok) throw new Error('Job submission failed')

                const { job_id } = await response.json()
                this.jobId = job_id
                this.pollJobStatus()

            } catch (error) {
                console.error('Job submission error:', error)
                this.showError('Failed to submit job')
            }
        },

        async pollJobStatus() {
            if (!this.jobId) return

            try {
                const response = await fetch(`/api/v1/status/${this.jobId}`)
                if (!response.ok) throw new Error('Status check failed')

                const { stage, progress, logs } = await response.json()
                
                this.currentStage = stage
                this.progress = progress

                if (stage === 'completed') {
                    await this.fetchResults()
                } else if (stage !== 'failed') {
                    setTimeout(() => this.pollJobStatus(), 1000)
                }

            } catch (error) {
                console.error('Status check error:', error)
                this.showError('Failed to check job status')
            }
        },

        async fetchResults() {
            try {
                const response = await fetch(`/api/v1/result/${this.jobId}`)
                if (!response.ok) throw new Error('Failed to fetch results')

                const results = await response.json()
                
                this.transcript = results.transcript
                this.summaries = {
                    short: results.summaries.short,
                    detailed: results.summaries.detailed,
                    bullets: results.summaries.bullets || []
                }

                this.processing = false

            } catch (error) {
                console.error('Results fetch error:', error)
                this.showError('Failed to fetch results')
            }
        },

        async exportPDF() {
            if (!this.jobId) return

            try {
                const response = await fetch(`/api/v1/export/pdf/${this.jobId}`)
                if (!response.ok) throw new Error('PDF export failed')

                const blob = await response.blob()
                const url = window.URL.createObjectURL(blob)
                
                const a = document.createElement('a')
                a.href = url
                a.download = `summary-${this.jobId}.pdf`
                a.click()

                window.URL.revokeObjectURL(url)

            } catch (error) {
                console.error('PDF export error:', error)
                this.showError('Failed to export PDF')
            }
        },

        handleFileUpload(event) {
            const file = event.target.files[0]
            if (!file) return

            this.file = file

            // Preview if media file
            if (file.type.startsWith('video/')) {
                this.mediaUrl = URL.createObjectURL(file)
                this.isVideo = true
                this.isAudio = false
                this.isImage = false
            } else if (file.type.startsWith('audio/')) {
                this.mediaUrl = URL.createObjectURL(file)
                this.isVideo = false
                this.isAudio = true
                this.isImage = false
            } else if (file.type.startsWith('image/')) {
                this.mediaUrl = URL.createObjectURL(file)
                this.isVideo = false
                this.isAudio = false
                this.isImage = true
            }
        },

        toggleTheme() {
            this.theme = this.theme === 'dark' ? 'light' : 'dark'
            document.documentElement.classList.toggle('dark')
            localStorage.setItem('theme', this.theme)
        },

        loadTheme() {
            this.theme = localStorage.getItem('theme') || 'dark'
            if (this.theme === 'dark') {
                document.documentElement.classList.add('dark')
            }
        },

        changeLanguage(event) {
            const lang = event.target.value
            document.documentElement.lang = lang
            // Implement language change logic
        },

        showError(message) {
            // Implement error notification
            console.error(message)
        }
    }
}