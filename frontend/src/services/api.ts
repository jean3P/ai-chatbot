// frontend/src/services/api.ts

import axios, {
    AxiosError,
    AxiosResponse,
    InternalAxiosRequestConfig,
    RawAxiosRequestHeaders,
} from 'axios'

const API_BASE_URL =
    (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api'

export const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' } as RawAxiosRequestHeaders,
})

// Request interceptor
api.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const method = (config.method ?? '').toUpperCase()
        console.log('🚀 API Request:', method, config.url)
        return config
    },
    (error: AxiosError) => {
        console.error('❌ Request Error:', error)
        return Promise.reject(error)
    }
)

// Response interceptor
api.interceptors.response.use(
    (response: AxiosResponse) => {
        console.log('✅ API Response:', response.status, response.config.url)
        return response
    },
    (error: AxiosError) => {
        const status = (error.response && error.response.status) ?? 'NO_STATUS'
        const data = (error.response && error.response.data) ?? 'NO_DATA'
        console.error('❌ API Error:', status, data)
        return Promise.reject(error)
    }
)

// Chat API types
export interface ChatRequest {
    message: string
    conversation_id?: string
    language?: string
}

export interface ChatResponse {
    success: boolean
    conversation_id: string
    message: {
        id: string
        role: string
        content: string
        citations: any[]
        created_at: string
    }
}

export const chatAPI = {
    // Send message to backend
    sendMessage: async (data: ChatRequest): Promise<ChatResponse> => {
        const response = await api.post('/chat/', data)
        return response.data
    },

    // Get conversation history
    getConversation: async (conversationId: string) => {
        const response = await api.get(`/chat/conversations/${conversationId}/`)
        return response.data
    },

    // Get all conversations
    getConversations: async (sessionId?: string) => {
        const response = await api.get('/chat/conversations/', {
            params: sessionId ? { session_id: sessionId } : undefined,
        })
        return response.data
    },

    // Delete conversation
    deleteConversation: async (conversationId: string) => {
        const response = await api.delete(`/chat/conversations/${conversationId}/`)
        return response.data
    },

    // Send feedback
    sendFeedback: async (messageId: string, isHelpful: boolean, comment?: string) => {
        const response = await api.post('/chat/feedback/', {
            message: messageId,
            feedback_type: 'helpful',
            is_positive: isHelpful,
            comment: comment || '',
        })
        return response.data
    },
}

export default api
