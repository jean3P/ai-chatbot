// frontend/src/components/ChatWidget.tsx

import React, { useState, useRef, useLayoutEffect, useCallback, useEffect } from 'react'
import { chatAPI, ChatRequest } from '../services/api'
import MarkdownContent from './MarkdownContent'

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

type ChatMode = 'compact' | 'expanded'

export default function ChatWidget({ isOpen, onClose }: ChatWidgetProps) {
    // Chat mode state with localStorage persistence
    const [mode, setMode] = useState<ChatMode>(() => {
        const saved = localStorage.getItem('chatMode')
        return (saved === 'expanded' || saved === 'compact') ? saved : 'compact'
    })

    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content:
                "Hello! I'm your AI assistant. I can help you with questions about documentation. What would you like to know?",
            timestamp: new Date(),
        },
    ])
    const [input, setInput] = useState<string>('')
    const [isLoading, setIsLoading] = useState<boolean>(false)
    const [conversationId, setConversationId] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)

    const listRef = useRef<HTMLDivElement | null>(null)
    const endRef = useRef<HTMLDivElement | null>(null)

    // Check if mobile device
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent) || window.innerWidth < 640

    // Force expanded mode on mobile
    useEffect(() => {
        if (isMobile && mode === 'compact') {
            setMode('expanded')
        }
    }, [isMobile, mode])

    // Save mode preference to localStorage
    useEffect(() => {
        localStorage.setItem('chatMode', mode)
    }, [mode])

    const scrollToBottom = useCallback((smooth = true) => {
        if (endRef.current) {
            if ("scrollIntoView" in endRef.current) {
                endRef.current.scrollIntoView({
                    behavior: smooth ? 'smooth' : 'auto',
                    block: 'end',
                })
            }
        } else if (listRef.current) {
            if ("scrollTop" in listRef.current) {
                listRef.current.scrollTop = listRef.current.scrollHeight
            }
        }
    }, [])

    useLayoutEffect(() => {
        scrollToBottom(true)
    }, [messages, isLoading, scrollToBottom])

    const toggleMode = () => {
        setMode(prev => prev === 'compact' ? 'expanded' : 'compact')
    }

    const handleSend = async (): Promise<void> => {
        if (!input.trim() || isLoading) return

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input.trim(),
            timestamp: new Date(),
        }

        setMessages((prev) => [...prev, userMessage])
        queueMicrotask(() => scrollToBottom(false))

        setInput('')
        setIsLoading(true)
        setError(null)

        try {
            const chatRequest: ChatRequest = {
                message: userMessage.content,
                language: 'auto',
            }
            if (conversationId) chatRequest.conversation_id = conversationId

            const response = await chatAPI.sendMessage(chatRequest)

            if (response.conversation_id && !conversationId) {
                setConversationId(response.conversation_id)
            }

            const assistantMessage: Message = {
                id: response.message.id,
                role: 'assistant',
                content: response.message.content,
                timestamp: new Date(response.message.created_at),
                citations: response.message.citations || [],
            }
            setMessages((prev) => [...prev, assistantMessage])
        } catch (error: any) {
            console.error('Chat API Error:', error)
            let errorMessage =
                "Sorry, I'm having technical difficulties. Please try again."

            if (error?.response?.status === 400) {
                errorMessage = 'Invalid request. Please check your message and try again.'
            } else if (error?.response?.status === 500) {
                errorMessage = 'Server error. Please try again in a moment.'
            } else if (error?.code === 'ERR_NETWORK' || !error?.response) {
                errorMessage =
                    'Cannot connect to server. Please check if the backend is running on port 8000.'
            }

            setError(errorMessage)

            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: errorMessage,
                timestamp: new Date(),
            }
            setMessages((prev) => [...prev, errorMsg])
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>): void => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const clearError = (): void => setError(null)

    if (!isOpen) return null

    // Dynamic styles based on mode
    const containerStyles = mode === 'compact'
        ? 'w-full max-w-md h-[600px]'  // Compact: 400px width, 600px height
        : 'w-[90vw] h-[90vh] max-w-6xl' // Expanded: 90% viewport

    const overlayStyles = mode === 'compact'
        ? 'bg-black/50'
        : 'bg-black/70' // Darker overlay in expanded mode

    const positionStyles = mode === 'compact'
        ? 'items-end justify-end'  // Bottom-right corner
        : 'items-center justify-center' // Centered

    const messageMaxWidth = mode === 'compact'
        ? 'max-w-[85%]'
        : 'max-w-[75%]' // Wider messages in expanded mode

    return (
        <div className={`fixed inset-0 ${overlayStyles} flex ${positionStyles} p-4 z-50 transition-all duration-300`}>
            <div className={`bg-white rounded-lg shadow-xl ${containerStyles} flex flex-col transition-all duration-300 ease-in-out`}>
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b bg-primary-500 text-white rounded-t-lg">
                    <div className="flex items-center gap-2">
                        <span className="text-xl">🤖</span>
                        <h3 className="font-semibold">AI Assistant</h3>
                        {conversationId && (
                            <span className="text-xs opacity-90">Connected</span>
                        )}
                    </div>

                    <div className="flex items-center gap-2">
                        {/* Mode toggle button (hide on mobile) */}
                        {!isMobile && (
                            <button
                                onClick={toggleMode}
                                className="hover:bg-primary-600 p-2 rounded transition-colors"
                                type="button"
                                aria-label={mode === 'compact' ? 'Expand chat' : 'Compact chat'}
                                title={mode === 'compact' ? 'Expand' : 'Compact'}
                            >
                                {mode === 'compact' ? (
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                                    </svg>
                                ) : (
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
                                    </svg>
                                )}
                            </button>
                        )}

                        {/* Close button */}
                        <button
                            onClick={onClose}
                            className="hover:bg-primary-600 p-2 rounded transition-colors"
                            type="button"
                            aria-label="Close chat"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Error Banner */}
                {error && (
                    <div className="bg-red-50 border-l-4 border-primary-500 text-red-900 p-3 text-sm flex items-start justify-between">
                        <div className="flex items-start gap-2">
                            <span className="text-primary-500 font-bold">⚠️</span>
                            <span>{error}</span>
                        </div>
                        <button
                            onClick={clearError}
                            className="text-primary-500 hover:text-primary-700 font-bold ml-2"
                            type="button"
                            aria-label="Dismiss error"
                        >
                            ✕
                        </button>
                    </div>
                )}

                {/* Messages */}
                <div
                    ref={listRef}
                    className="flex-1 overflow-y-auto p-4 space-y-4"
                    aria-live="polite"
                    aria-relevant="additions"
                >
                    {messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex ${
                                message.role === 'user' ? 'justify-end' : 'justify-start'
                            }`}
                        >
                            <div
                                className={`${messageMaxWidth} rounded-lg px-4 py-3 ${
                                    message.role === 'user'
                                        ? 'bg-primary-500 text-white'
                                        : 'bg-gray-100 text-gray-900'
                                }`}
                            >
                                {/* Message Content */}
                                {message.role === 'assistant' ? (
                                    <div className="text-sm">
                                        <MarkdownContent content={message.content} />
                                    </div>
                                ) : (
                                    <p className="text-sm whitespace-pre-wrap">
                                        {message.content}
                                    </p>
                                )}

                                {/* Citations */}
                                {message.citations && message.citations.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-gray-300">
                                        <div className="flex items-center gap-2 text-xs text-gray-600">
                                            <span className="font-semibold">📚 Sources:</span>
                                            <span>
                                                {message.citations.length} reference
                                                {message.citations.length > 1 ? 's' : ''}
                                            </span>
                                        </div>
                                    </div>
                                )}

                                {/* Timestamp */}
                                <div className="text-xs opacity-75 mt-2">
                                    {message.timestamp.toLocaleTimeString()}
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* Loading indicator */}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="bg-gray-100 rounded-lg px-4 py-3">
                                <div className="flex gap-2 items-center">
                                    <div className="flex gap-1">
                                        <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" />
                                        <div
                                            className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"
                                            style={{ animationDelay: '0.1s' }}
                                        />
                                        <div
                                            className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"
                                            style={{ animationDelay: '0.2s' }}
                                        />
                                    </div>
                                    <span className="text-xs text-gray-600 ml-2">
                                        AI is thinking...
                                    </span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={endRef} />
                </div>

                {/* Input */}
                <div className="p-4 border-t bg-gray-50">
                    <div className="flex gap-2">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Type your question..."
                            className="flex-1 resize-none border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                            rows={mode === 'expanded' ? 3 : 2}
                            disabled={isLoading}
                            aria-label="Message input"
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading}
                            className="bg-primary-500 hover:bg-primary-600 active:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg transition-colors font-medium"
                            type="button"
                            aria-label="Send message"
                        >
                            {isLoading ? '⏳' : '📤'}
                        </button>
                    </div>

                    {/* Status bar */}
                    <div className="text-xs text-gray-500 mt-2 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${conversationId ? 'bg-green-500' : 'bg-gray-400'}`} />
                            <span>{conversationId ? 'Connected' : 'Ready'}</span>
                            {mode === 'expanded' && (
                                <span className="text-gray-400">• {messages.length} messages</span>
                            )}
                        </div>
                        <span className="text-gray-400">localhost:8000</span>
                    </div>
                </div>
            </div>
        </div>
    )
}