// frontend/src/components/ChatWidget.tsx

import React, { useState, useRef, useLayoutEffect, useCallback, useEffect } from 'react'
import { chatAPI, ChatRequest } from '../services/api'
import MarkdownContent from './MarkdownContent'
import CitationList from './CitationList'
import ConversationSidebar from './ConversationSidebar'

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
    const [mode, setMode] = useState<ChatMode>(() => {
        try {
            const saved = localStorage.getItem('chatMode')
            return (saved === 'expanded' || saved === 'compact') ? saved : 'compact'
        } catch (e) {
            console.warn('Could not access localStorage:', e)
            return 'compact'
        }
    })

    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content:
                "Hello! I'm your AI assistant. I can help you with questions about documentation. What would you like to know?",
            timestamp: new Date(),
            citations: [
                {
                    document_title: 'DMX Splitter XPD-42 Manual',
                    page_number: 12,
                    chunk_text: 'Connect the DMX input cable from your controller to the INPUT port on the splitter. Ensure the cable is securely fastened and the connection LED illuminates green.'
                },
                {
                    document_title: 'Installation Guide',
                    page_number: 5,
                    chunk_text: 'Before powering on the device, verify all connections are secure.'
                },
                {
                    document_title: 'Troubleshooting FAQ',
                    page_number: 8,
                    chunk_text: 'If the LED does not illuminate, check the power supply connection and ensure the voltage matches the device specifications.'
                },
                {
                    document_title: 'Advanced Configuration',
                    page_number: 15,
                    chunk_text: 'For optimal performance, configure the termination resistor.'
                }
            ]
        },
    ])
    const [input, setInput] = useState<string>('')
    const [isLoading, setIsLoading] = useState<boolean>(false)
    const [conversationId, setConversationId] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [isSidebarOpen, setIsSidebarOpen] = useState(false)

    const listRef = useRef<HTMLDivElement | null>(null)
    const endRef = useRef<HTMLDivElement | null>(null)

    const isMobile = typeof window !== 'undefined' && (
        /iPhone|iPad|iPod|Android/i.test(navigator.userAgent) || window.innerWidth < 640
    )

    useEffect(() => {
        if (isMobile && mode === 'compact') {
            setMode('expanded')
        }
    }, [isMobile, mode])

    useEffect(() => {
        try {
            localStorage.setItem('chatMode', mode)
        } catch (e) {
            console.warn('Could not save to localStorage:', e)
        }
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
        if (isOpen) {
            scrollToBottom(true)
        }
    }, [messages, isLoading, scrollToBottom, isOpen])

    const toggleMode = () => {
        setMode(prev => prev === 'compact' ? 'expanded' : 'compact')
    }

    const handleNewChat = () => {
        setConversationId(null)
        setMessages([
            {
                id: Date.now().toString(),
                role: 'assistant',
                content: "Hello! I'm your AI assistant. How can I help you today?",
                timestamp: new Date(),
            },
        ])
        setInput('')
        setError(null)
    }

    const handleSelectConversation = async (convId: string) => {
        try {
            const response = await chatAPI.getConversation(convId)
            setConversationId(convId)

            // Convert API messages to local format
            const loadedMessages: Message[] = response.messages.map((msg: any) => ({
                id: msg.id,
                role: msg.role,
                content: msg.content,
                timestamp: new Date(msg.created_at),
                citations: msg.citations || [],
            }))

            setMessages(loadedMessages)
        } catch (error) {
            console.error('Failed to load conversation:', error)
            setError('Failed to load conversation')
        }
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

    const containerStyles = mode === 'compact'
        ? 'w-full max-w-md h-[600px]'
        : 'w-[90vw] h-[90vh] max-w-6xl'

    const overlayStyles = mode === 'compact'
        ? 'bg-black/50'
        : 'bg-black/70'

    const positionStyles = mode === 'compact'
        ? 'items-end justify-end'
        : 'items-center justify-center'

    const messageMaxWidth = mode === 'compact'
        ? 'max-w-[85%]'
        : 'max-w-[75%]'

    return (
        <>
            {/* Conversation Sidebar */}
            <ConversationSidebar
                isOpen={isSidebarOpen}
                onClose={() => setIsSidebarOpen(false)}
                currentConversationId={conversationId}
                onSelectConversation={handleSelectConversation}
                onNewChat={handleNewChat}
            />

            {/* Main Chat */}
            <div
                className={`fixed inset-0 ${overlayStyles} flex ${positionStyles} p-4 z-50 transition-colors duration-300`}
                onClick={(e) => {
                    if (mode === 'compact' && e.target === e.currentTarget) {
                        onClose()
                    }
                }}
            >
                <div
                    className={`bg-white rounded-lg shadow-2xl ${containerStyles} flex flex-col transition-all duration-300 ease-in-out`}
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-4 border-b bg-primary-500 text-white rounded-t-lg shrink-0">
                        <div className="flex items-center gap-2">
                            {/* Sidebar Toggle */}
                            <button
                                onClick={() => setIsSidebarOpen(prev => !prev)}  // Changed from setIsSidebarOpen(true)
                                className="hover:bg-primary-600 p-2 rounded transition-colors"
                                type="button"
                                aria-label="Toggle conversation history"
                                title="Conversation History"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                                </svg>
                            </button>

                            <span className="text-xl">🤖</span>
                            <h3 className="font-semibold">AI Assistant</h3>
                            {conversationId && (
                                <span className="text-xs opacity-90">Connected</span>
                            )}
                        </div>

                        <div className="flex items-center gap-1">
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
                        <div className="bg-red-50 border-l-4 border-primary-500 text-red-900 p-3 text-sm flex items-start justify-between shrink-0">
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
                        className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0"
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
                                    {message.role === 'assistant' ? (
                                        <div className="text-sm">
                                            <MarkdownContent content={message.content} />
                                        </div>
                                    ) : (
                                        <p className="text-sm whitespace-pre-wrap break-words">
                                            {message.content}
                                        </p>
                                    )}

                                    {message.role === 'assistant' && message.citations && message.citations.length > 0 && (
                                        <CitationList citations={message.citations} />
                                    )}

                                    <div className="text-xs opacity-75 mt-2">
                                        {message.timestamp.toLocaleTimeString()}
                                    </div>
                                </div>
                            </div>
                        ))}

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
                    <div className="p-4 border-t bg-gray-50 shrink-0">
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
                                className="bg-primary-500 hover:bg-primary-600 active:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg transition-colors font-medium self-end"
                                type="button"
                                aria-label="Send message"
                            >
                                {isLoading ? '⏳' : '📤'}
                            </button>
                        </div>

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
        </>
    )
}

