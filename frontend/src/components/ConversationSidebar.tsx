// frontend/src/components/ConversationSidebar.tsx

import React, { useState, useEffect } from 'react'
import { chatAPI } from '../services/api'

interface Conversation {
    id: string
    title: string
    created_at: string
    updated_at: string
    message_count?: number
}

interface ConversationSidebarProps {
    isOpen: boolean
    onClose: () => void
    currentConversationId: string | null
    onSelectConversation: (conversationId: string) => void
    onNewChat: () => void
}

export default function ConversationSidebar({
                                                isOpen,
                                                onClose,
                                                currentConversationId,
                                                onSelectConversation,
                                                onNewChat
                                            }: ConversationSidebarProps) {
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [filteredConversations, setFilteredConversations] = useState<Conversation[]>([])
    const [searchQuery, setSearchQuery] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

    useEffect(() => {
        if (isOpen) {
            fetchConversations()
        }
    }, [isOpen])

    useEffect(() => {
        if (!searchQuery.trim()) {
            setFilteredConversations(conversations)
        } else {
            const query = searchQuery.toLowerCase()
            const filtered = conversations.filter(conv =>
                conv.title.toLowerCase().includes(query)
            )
            setFilteredConversations(filtered)
        }
    }, [searchQuery, conversations])

    const fetchConversations = async () => {
        setIsLoading(true)
        try {
            const response = await chatAPI.getConversations()
            const convs = response.results || response || []
            setConversations(convs)
            setFilteredConversations(convs)
        } catch (error) {
            console.error('Failed to fetch conversations:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const handleDelete = async (id: string) => {
        try {
            await chatAPI.deleteConversation(id)
            setConversations(prev => prev.filter(c => c.id !== id))
            setDeleteConfirmId(null)

            if (id === currentConversationId) {
                onNewChat()
            }
        } catch (error) {
            console.error('Failed to delete conversation:', error)
        }
    }

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

        if (diffDays === 0) return 'Today'
        if (diffDays === 1) return 'Yesterday'
        if (diffDays < 7) return `${diffDays} days ago`
        return date.toLocaleDateString()
    }

    if (!isOpen) return null

    return (
        <>
            {/* Overlay - Higher z-index than chat */}
            <div
                className="fixed inset-0 bg-black/30 z-[55] transition-opacity duration-300"
                onClick={onClose}
            />

            {/* Sidebar - Even higher z-index */}
            <div
                className="fixed top-0 left-0 h-full w-80 bg-white shadow-2xl z-[60] transform transition-transform duration-300 ease-in-out flex flex-col"
                onClick={(e) => e.stopPropagation()} // Prevent clicks from closing
            >
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b bg-primary-500 text-white shrink-0">
                    <h2 className="font-semibold text-lg">Conversations</h2>
                    <button
                        onClick={onClose}
                        className="hover:bg-primary-600 p-2 rounded transition-colors"
                        type="button"
                        aria-label="Close sidebar"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* New Chat Button */}
                <div className="p-4 border-b shrink-0">
                    <button
                        onClick={() => {
                            onNewChat()
                            onClose()
                        }}
                        className="w-full bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg transition-colors font-medium flex items-center justify-center gap-2"
                        type="button"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        New Chat
                    </button>
                </div>

                {/* Search Bar */}
                <div className="p-4 border-b shrink-0">
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="Search conversations..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
                        />
                        <svg
                            className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                </div>

                {/* Conversation List - Scrollable */}
                <div className="flex-1 overflow-y-auto min-h-0">
                    {isLoading ? (
                        <div className="flex items-center justify-center p-8">
                            <div className="flex gap-1">
                                <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" />
                                <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                                <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                            </div>
                        </div>
                    ) : filteredConversations.length === 0 ? (
                        <div className="flex flex-col items-center justify-center p-8 text-center">
                            <svg className="w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                            <p className="text-gray-500 font-medium">
                                {searchQuery ? 'No conversations found' : 'No conversations yet'}
                            </p>
                            <p className="text-gray-400 text-sm mt-1">
                                {searchQuery ? 'Try a different search term' : 'Start a new chat to begin'}
                            </p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-200">
                            {filteredConversations.map((conversation) => (
                                <div
                                    key={conversation.id}
                                    className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                                        conversation.id === currentConversationId ? 'bg-primary-50 border-l-4 border-primary-500' : ''
                                    }`}
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        onSelectConversation(conversation.id)
                                        onClose()
                                    }}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-medium text-gray-900 truncate">
                                                {conversation.title || 'Untitled Conversation'}
                                            </h3>
                                            <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                                                <span>{formatDate(conversation.updated_at)}</span>
                                                {conversation.message_count && (
                                                    <>
                                                        <span>•</span>
                                                        <span>{conversation.message_count} messages</span>
                                                    </>
                                                )}
                                            </div>
                                        </div>

                                        {/* Delete Button */}
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                setDeleteConfirmId(conversation.id)
                                            }}
                                            className="text-gray-400 hover:text-red-500 transition-colors p-1 shrink-0"
                                            type="button"
                                            aria-label="Delete conversation"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Delete Confirmation Modal - Highest z-index */}
            {deleteConfirmId && (
                <div
                    className="fixed inset-0 bg-black/50 flex items-center justify-center z-[70] p-4"
                    onClick={() => setDeleteConfirmId(null)}
                >
                    <div
                        className="bg-white rounded-lg shadow-xl max-w-md w-full p-6"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                            Delete Conversation?
                        </h3>
                        <p className="text-gray-600 mb-6">
                            This will permanently delete this conversation and all its messages. This action cannot be undone.
                        </p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setDeleteConfirmId(null)}
                                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                                type="button"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => {
                                    if (deleteConfirmId) {
                                        handleDelete(deleteConfirmId)
                                    }
                                }}
                                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors font-medium"
                                type="button"
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}