import { useState } from 'react'
import HomeView from './views/HomeView'
import BankRatesView from './views/BankRatesView'
import FSSView from './views/FSSView'
import CounselorView from './views/CounselorView'

export default function App() {
  const [view, setView] = useState('home')

  const goHome = () => setView('home')

  return (
    <div>
      {view === 'home' && <HomeView key="home" onNavigate={setView} />}
      {view === 'bank' && <BankRatesView key="bank" onBack={goHome} />}
      {view === 'fss' && <FSSView key="fss" onBack={goHome} />}
      {view === 'counselor' && <CounselorView key="counselor" onBack={goHome} />}
    </div>
  )
}
