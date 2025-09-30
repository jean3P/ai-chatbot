// frontend/src/components/MarkdownContent.tsx

import React from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface MarkdownContentProps {
    content: string
    className?: string
}

export default function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
    const components: Components = {
        /* Headings */
        h1: ({ children }) => <h1 className="text-2xl font-bold text-primary-500 mt-4 mb-2">{children}</h1>,
        h2: ({ children }) => <h2 className="text-xl font-bold text-primary-500 mt-3 mb-2">{children}</h2>,
        h3: ({ children }) => <h3 className="text-lg font-semibold text-primary-600 mt-3 mb-1">{children}</h3>,
        h4: ({ children }) => <h4 className="text-base font-semibold text-primary-600 mt-2 mb-1">{children}</h4>,

        /* Paragraphs */
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,

        /* Emphasis */
        strong: ({ children }) => <strong className="font-bold text-gray-900">{children}</strong>,
        em: ({ children }) => <em className="italic text-gray-700">{children}</em>,

        /* Code (inline & blocks) */
        code: ({ inline, className: cls, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(cls || '')
            const language = match ? match[1] : ''

            if (!inline && language) {
                return (
                    <div className="my-3 rounded-lg overflow-hidden border border-gray-300">
                        <div className="bg-gray-800 text-gray-300 text-xs px-3 py-1 flex justify-between items-center">
                            <span className="font-mono">{language}</span>
                            <button
                                onClick={() => navigator.clipboard.writeText(String(children))}
                                className="text-gray-400 hover:text-white text-xs px-2 py-1 rounded transition-colors"
                                type="button"
                            >
                                Copy
                            </button>
                        </div>
                        <SyntaxHighlighter
                            language={language}
                            style={vscDarkPlus}
                            customStyle={{ margin: 0, padding: '1rem', fontSize: '0.875rem', lineHeight: '1.5' }}
                            PreTag="div"
                        >
                            {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                    </div>
                )
            }

            return (
                <code className="bg-gray-200 text-primary-700 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                    {children}
                </code>
            )
        },

        /* Links (open in new tab, safe) */
        a: ({ href, children, ...props }: any) => (
            <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-500 hover:text-primary-600 underline font-medium transition-colors"
                {...props}
            >
                {children}
                <span className="inline-block ml-1 text-xs">↗</span>
            </a>
        ),

        /* Lists */
        ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1 ml-2">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1 ml-2">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,

        /* Blockquote */
        blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-primary-500 pl-4 py-2 my-3 bg-gray-50 italic text-gray-700">
                {children}
            </blockquote>
        ),

        /* HR */
        hr: () => <hr className="my-4 border-t-2 border-gray-200" />,

        /* Tables */
        table: ({ children }) => (
            <div className="overflow-x-auto my-3">
                <table className="min-w-full border border-gray-300 text-sm">{children}</table>
            </div>
        ),
        thead: ({ children }) => <thead className="bg-gray-100">{children}</thead>,
        tbody: ({ children }) => <tbody className="divide-y divide-gray-200">{children}</tbody>,
        tr: ({ children }) => <tr>{children}</tr>,
        th: ({ children }) => (
            <th className="px-4 py-2 text-left font-semibold text-gray-900 border-b border-gray-300">{children}</th>
        ),
        td: ({ children }) => <td className="px-4 py-2 border-b border-gray-200">{children}</td>,

        /* GFM task list checkboxes (read-only) */
        input: ({ checked, ...props }: any) => (
            <input type="checkbox" checked={!!checked} disabled className="mr-2 accent-primary-500" {...props} />
        ),
    }

    return (
        <div className={className}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                {content}
            </ReactMarkdown>
        </div>
    )
}
