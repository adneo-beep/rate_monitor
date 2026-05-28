const GRADIENTS = {
  blue: 'from-blue-600 to-indigo-700',
  emerald: 'from-emerald-600 to-teal-700',
  violet: 'from-violet-600 to-purple-700',
}

function HomeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V9.5z" />
      <polyline points="9 21 9 12 15 12 15 21" />
    </svg>
  )
}

export default function PageHeader({ title, subtitle, onBack, accent = 'blue' }) {
  return (
    <div className={`bg-gradient-to-r ${GRADIENTS[accent]} text-white px-6 py-5 shadow-md`}>
      <div className="max-w-screen-xl mx-auto flex items-center gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-bold leading-tight truncate">{title}</h1>
          <p className="text-white/65 text-xs mt-0.5">{subtitle}</p>
        </div>
        <button
          onClick={onBack}
          className="flex items-center gap-2 bg-white/15 hover:bg-white/25 active:bg-white/30 transition-colors px-4 py-2 rounded-lg text-sm font-medium shrink-0 border border-white/20"
        >
          <HomeIcon />
          <span>메인으로</span>
        </button>
      </div>
    </div>
  )
}
