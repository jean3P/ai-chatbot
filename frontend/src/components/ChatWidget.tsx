// frontend/src/components/ChatWidget.tsx

import { useState } from 'react'
import { chatAPI, ChatRequest } from '../services/api'

interface ChatWidgetProps {
    isOpen: boolean
    onClose: () => void
}

interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    citations?: any[]
}

export default function ChatWidget({ isOpen, onClose }: ChatWidgetProps) {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content: 'Hello! I\'m your AI assistant. I can help you with questions about documentation. What would you like to know?',
            timestamp: new Date(),
        }
    ])
    const [input, setInput] = useState<string>('')
    const [isLoading, setIsLoading] = useState<boolean>(false)
    const [conversationId, setConversationId] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)

    const handleSend = async (): Promise<void> => {
        if (!input.trim() || isLoading) return

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input.trim(),
            timestamp: new Date(),
        }

        setMessages(prev => [...prev, userMessage])
        setInput('')
        setIsLoading(true)
        setError(null)

        try {
            // Prepare API request
            const chatRequest: ChatRequest = {
                message: userMessage.content,
                language: 'en'
            }

            // Add conversation ID if we have one
            if (conversationId) {
                chatRequest.conversation_id = conversationId
            }

            console.log('📤 Sending to backend:', chatRequest)

            // Call real backend API
            const response = await chatAPI.sendMessage(chatRequest)

            console.log('📥 Backend response:', response)

            // Save conversation ID for future messages
            if (response.conversation_id && !conversationId) {
                setConversationId(response.conversation_id)
            }

            // Add AI response to messages
            const assistantMessage: Message = {
                id: response.message.id,
                role: 'assistant',
                content: response.message.content,
                timestamp: new Date(response.message.created_at),
                citations: response.message.citations || []
            }

            setMessages(prev => [...prev, assistantMessage])

        } catch (error: any) {
            console.error('❌ Chat API Error:', error)

            // Show error message to user
            let errorMessage = 'Sorry, I\'m having technical difficulties. Please try again.'

            if (error.response?.status === 400) {
                errorMessage = 'Invalid request. Please check your message and try again.'
            } else if (error.response?.status === 500) {
                errorMessage = 'Server error. Please try again in a moment.'
            } else if (error.code === 'ERR_NETWORK' || !error.response) {
                errorMessage = 'Cannot connect to server. Please check if the backend is running on port 8000.'
            }

            setError(errorMessage)

            // Add error message to chat
            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: errorMessage,
                timestamp: new Date(),
            }

            setMessages(prev => [...prev, errorMsg])
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>): void => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const clearError = (): void => {
        setError(null)
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 bg-black/50 flex items-end justify-end p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-md h-[600px] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b bg-primary-600 text-white rounded-t-lg">
                    <div className="flex items-center gap-2">
                        <span className="text-xl">🤖</span>
                        <h3 className="font-semibold">AI Assistant</h3>
                        {conversationId && (
                            <span className="text-xs opacity-75">
                Connected
              </span>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="hover:bg-primary-700 p-1 rounded text-xl"
                        type="button"
                    >
                        ✕
                    </button>
                </div>

                {/* Error Banner */}
                {error && (
                    <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-2 text-sm">
                        ⚠️ {error}
                        <button
                            onClick={clearError}
                            className="float-right text-red-500 hover:text-red-700"
                            type="button"
                        >
                            ✕
                        </button>
                    </div>
                )}

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                                    message.role === 'user'
                                        ? 'bg-primary-600 text-white'
                                        : 'bg-gray-100 text-gray-900'
                                }`}
                            >
                                <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                                {/* Show citations if available */}
                                {message.citations && message.citations.length > 0 && (
                                    <div className="mt-2 text-xs opacity-75">
                                        📚 Citations: {message.citations.length}
                                    </div>
                                )}

                                <span className="text-xs opacity-70 mt-1 block">
                  {message.timestamp.toLocaleTimeString()}
                </span>
                            </div>
                        </div>
                    ))}

                    {/* Loading indicator */}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="bg-gray-100 rounded-lg px-4 py-2">
                                <div className="flex gap-1 items-center">
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                    <span className="text-xs text-gray-500 ml-2">
                    Calling backend API...
                  </span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Input */}
                <div className="p-4 border-t">
                    <div className="flex gap-2">
            <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your question..."
                className="flex-1 resize-none border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent"
                rows={2}
                disabled={isLoading}
            />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading}
                            className="bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 text-white px-4 py-2 rounded-lg transition-colors"
                            type="button"
                        >
                            {isLoading ? '⏳' : '📤'}
                        </button>
                    </div>

                    {/* Connection Status */}
                    <div className="text-xs text-gray-500 mt-2 flex justify-between">
            <span>
              Backend: {conversationId ? 'Connected' : 'Ready'}
            </span>
                        <span>
              API: http://localhost:8000/api
            </span>
                    </div>
                </div>
            </div>
        </div>
    )
}
