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

function RefreshIcon({ spinning }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
      className={spinning ? 'animate-spin' : ''}
    >
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  )
}

export default function PageHeader({ title, subtitle, onBack, onRefresh, isRefreshing = false, accent = 'blue' }) {
  return (
    <div className={`bg-gradient-to-r ${GRADIENTS[accent]} text-white px-6 py-5 shadow-md`}>
      <div className="max-w-screen-xl mx-auto flex items-center gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-bold leading-tight truncate">{title}</h1>
          <p className="text-white/65 text-xs mt-0.5">{subtitle}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-2 bg-white/15 hover:bg-white/25 active:bg-white/30 transition-colors px-4 py-2 rounded-lg text-sm font-medium border border-white/20 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <RefreshIcon spinning={isRefreshing} />
              <span>{isRefreshing ? '로딩 중...' : '새로고침'}</span>
            </button>
          )}
          <button
            onClick={onBack}
            className="flex items-center gap-2 bg-white/15 hover:bg-white/25 active:bg-white/30 transition-colors px-4 py-2 rounded-lg text-sm font-medium border border-white/20"
          >
            <HomeIcon />
            <span>메인으로</span>
          </button>
        </div>
      </div>
    </div>
  )
}
