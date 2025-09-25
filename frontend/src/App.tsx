import { useState } from 'react'
import ChatWidget from './components/ChatWidget'

function App() {
    const [isOpen, setIsOpen] = useState(false)

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
            <div className="container mx-auto px-4 py-16">
                <div className="text-center">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">
                        AI Document Chatbot
                    </h1>
                    <p className="text-xl text-gray-600 mb-8">
                        Ask questions about our documentation and get instant answers
                    </p>
                    <div className="bg-white rounded-lg shadow-lg p-8 max-w-2xl mx-auto mb-8">
                        <h2 className="text-2xl font-semibold mb-4">Try asking:</h2>
                        <ul className="text-left space-y-2 text-gray-700">
                            <li>• "How do I troubleshoot connection issues?"</li>
                            <li>• "What are the setup instructions?"</li>
                            <li>• "Tell me about the warranty policy"</li>
                        </ul>
                    </div>
                    <button
                        onClick={() => setIsOpen(true)}
                        className="bg-primary-600 hover:bg-primary-700 text-white px-8 py-4 rounded-lg text-lg font-semibold shadow-lg hover:shadow-xl transition-all"
                    >
                        🤖 Open AI Chat
                    </button>
                </div>
            </div>

            <ChatWidget isOpen={isOpen} onClose={() => setIsOpen(false)} />
        </div>
    )
}

export default App