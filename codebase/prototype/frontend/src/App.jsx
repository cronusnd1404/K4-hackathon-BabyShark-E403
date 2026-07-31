import { useState } from 'react'
import Onboarding from './components/Onboarding'
import MainScreen from './components/MainScreen'

function App() {
  const [sessionId, setSessionId] = useState(null)
  const [documentId, setDocumentId] = useState(null)
  const [chatHistory, setChatHistory] = useState([])

  if (!sessionId) {
    return <Onboarding onComplete={setSessionId} />
  }

  return (
    <MainScreen
      sessionId={sessionId}
      documentId={documentId}
      setDocumentId={setDocumentId}
      chatHistory={chatHistory}
      setChatHistory={setChatHistory}
    />
  )
}

export default App
