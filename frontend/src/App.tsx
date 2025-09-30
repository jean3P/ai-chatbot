// frontend/src/App.tsx

import { useState } from 'react'
import ChatWidget from './components/ChatWidget'

function App() {
    const [isOpen, setIsOpen] = useState(false)

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
            <div className="container mx-auto px-4 py-16">
                <div className="text-center">
                    {/* Logo/Brand area */}
                    <div className="mb-8">
                        <h1 className="text-5xl font-bold text-gray-900 mb-2">
                            Swisson AI Assistant
                        </h1>
                        <div className="w-24 h-1 bg-primary-500 mx-auto rounded-full"></div>
                    </div>

                    <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto">
                        Get instant answers from our technical documentation powered by AI
                    </p>

                    {/* Feature Cards */}
                    <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto mb-12">
                        <div className="bg-white rounded-lg shadow-md p-6 border-t-4 border-primary-500">
                            <div className="text-3xl mb-3">🔍</div>
                            <h3 className="font-semibold text-gray-900 mb-2">Smart Search</h3>
                            <p className="text-sm text-gray-600">
                                Find answers across all documentation instantly
                            </p>
                        </div>
                        <div className="bg-white rounded-lg shadow-md p-6 border-t-4 border-primary-500">
                            <div className="text-3xl mb-3">📚</div>
                            <h3 className="font-semibold text-gray-900 mb-2">Source Citations</h3>
                            <p className="text-sm text-gray-600">
                                Every answer includes references to source documents
                            </p>
                        </div>
                        <div className="bg-white rounded-lg shadow-md p-6 border-t-4 border-primary-500">
                            <div className="text-3xl mb-3">🌍</div>
                            <h3 className="font-semibold text-gray-900 mb-2">Multi-language</h3>
                            <p className="text-sm text-gray-600">
                                Ask questions in English, German, French, or Spanish
                            </p>
                        </div>
                    </div>

                    {/* Example Questions */}
                    <div className="bg-white rounded-lg shadow-lg p-8 max-w-2xl mx-auto mb-8">
                        <h2 className="text-2xl font-semibold mb-6 text-gray-900">
                            Try asking:
                        </h2>
                        <ul className="text-left space-y-3 text-gray-700">
                            <li className="flex items-start gap-3">
                                <span className="text-primary-500 font-bold">•</span>
                                <span>"How do I troubleshoot connection issues?"</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-primary-500 font-bold">•</span>
                                <span>"What are the DMX splitter setup instructions?"</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-primary-500 font-bold">•</span>
                                <span>"Tell me about the warranty policy"</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-primary-500 font-bold">•</span>
                                <span>"How to configure Ethernet DMX nodes?"</span>
                            </li>
                        </ul>
                    </div>

                    {/* CTA Button */}
                    <button
                        onClick={() => setIsOpen(true)}
                        className="bg-primary-500 hover:bg-primary-600 active:bg-primary-700 text-white px-8 py-4 rounded-lg text-lg font-semibold shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
                    >
                        🤖 Start Chat
                    </button>

                    {/* Footer note */}
                    <p className="mt-8 text-sm text-gray-500">
                        Powered by Swisson • AI-enhanced technical support
                    </p>
                </div>
            </div>

            <ChatWidget isOpen={isOpen} onClose={() => setIsOpen(false)} />
        </div>
    )
}

export default App