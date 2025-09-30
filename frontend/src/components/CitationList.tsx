// frontend/src/components/CitationsList.tsx

import React, { useState } from 'react'

interface Citation {
    id?: string
    document_title?: string
    page_number?: number
    chunk_text?: string
    source?: string
}

interface CitationListProps {
    citations: Citation[]
}

export default function CitationList({ citations }: CitationListProps) {
    const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())
    const [showAll, setShowAll] = useState(false)

    if (!citations || citations.length === 0) {
        return null
    }

    const toggleExpand = (index: number) => {
        setExpandedIds(prev => {
            const newSet = new Set(prev)
            if (newSet.has(index)) {
                newSet.delete(index)
            } else {
                newSet.add(index)
            }
            return newSet
        })
    }

    const displayedCitations = showAll ? citations : citations.slice(0, 3)
    const hasMore = citations.length > 3

    return (
        <div className="mt-3 pt-3 border-t border-gray-300">
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-gray-700">📚 Sources</span>
                <span className="text-xs text-gray-500">
                    ({citations.length} reference{citations.length > 1 ? 's' : ''})
                </span>
            </div>

            {/* Citation List */}
            <div className="space-y-2">
                {displayedCitations.map((citation, index) => {
                    const isExpanded = expandedIds.has(index)
                    const title = citation.document_title || citation.source || 'Unknown Source'
                    const page = citation.page_number
                    const text = citation.chunk_text || ''
                    const snippet = text.length > 100 ? text.substring(0, 100) + '...' : text

                    return (
                        <div
                            key={index}
                            className="bg-gray-50 rounded px-3 py-2 text-xs border border-gray-200 hover:border-primary-300 transition-colors"
                        >
                            {/* Citation Header */}
                            <button
                                onClick={() => toggleExpand(index)}
                                className="w-full text-left focus:outline-none group"
                                type="button"
                                title="Click to expand/collapse"
                            >
                                <div className="flex items-start gap-2">
                                    <span className="text-primary-500 font-bold shrink-0">
                                        [{index + 1}]
                                    </span>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="text-gray-400">📄</span>
                                            <span className="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors">
                                                {title}
                                            </span>
                                            {page && (
                                                <span className="text-gray-500">
                                                    • Page {page}
                                                </span>
                                            )}
                                        </div>

                                        {/* Snippet or Full Text */}
                                        {text && (
                                            <div className="mt-1 text-gray-600 leading-relaxed">
                                                {isExpanded ? (
                                                    <span className="whitespace-pre-wrap">
                                                        "{text}"
                                                    </span>
                                                ) : (
                                                    <span className="italic">
                                                        "{snippet}"
                                                    </span>
                                                )}
                                            </div>
                                        )}

                                        {/* Expand/Collapse Indicator */}
                                        {text.length > 100 && (
                                            <div className="mt-1 text-primary-500 font-medium">
                                                {isExpanded ? '▲ Show less' : '▼ Read more'}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </button>
                        </div>
                    )
                })}
            </div>

            {/* Show All Button */}
            {hasMore && !showAll && (
                <button
                    onClick={() => setShowAll(true)}
                    className="mt-2 text-xs text-primary-500 hover:text-primary-600 font-medium transition-colors"
                    type="button"
                >
                    + Show {citations.length - 3} more source{citations.length - 3 > 1 ? 's' : ''}
                </button>
            )}

            {/* Show Less Button */}
            {showAll && hasMore && (
                <button
                    onClick={() => setShowAll(false)}
                    className="mt-2 text-xs text-primary-500 hover:text-primary-600 font-medium transition-colors"
                    type="button"
                >
                    − Show less
                </button>
            )}
        </div>
    )
}
