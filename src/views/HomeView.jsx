const CARDS = [
  {
    id: 'bank',
    title: '금융사 홈페이지\n공시 기준',
    badge: '일별 업데이트',
    badgeBg: 'bg-blue-100 text-blue-700',
    desc: '5대 은행 + 4대 보험사의 최신 주택담보대출 금리를 확인하세요.',
    topBar: 'from-blue-500 to-indigo-600',
    btnColor: 'text-blue-600 group-hover:text-blue-700',
    institutions: ['KB국민 · 신한 · 하나 · 우리 · 농협', '삼성생명 · 한화 · 교보 · 삼성화재'],
    icon: '🏦',
  },
  {
    id: 'fss',
    title: '금융감독원\n공시 기준',
    badge: '월별 업데이트',
    badgeBg: 'bg-emerald-100 text-emerald-700',
    desc: '금융감독원이 공시하는 주택담보대출 금리를 비교하세요.',
    topBar: 'from-emerald-500 to-teal-600',
    btnColor: 'text-emerald-600 group-hover:text-emerald-700',
    institutions: ['5대 은행 공시 기준', '4대 보험사 공시 기준'],
    icon: '🏛️',
  },
  {
    id: 'counselor',
    title: '우리동네\n대출상담사 기준',
    badge: '일별 업데이트',
    badgeBg: 'bg-violet-100 text-violet-700',
    desc: '지역별 대출상담사가 제안하는 실제 금리 조건을 비교하세요.',
    topBar: 'from-violet-500 to-purple-600',
    btnColor: 'text-violet-600 group-hover:text-violet-700',
    institutions: ['서울 · 경기 · 부산 지역 상담사', '은행별 실제 제안 금리'],
    icon: '🤝',
  },
]

export default function HomeView({ onNavigate }) {
  return (
    <div className="min-h-screen bg-slate-900 animate-fade-in">
      {/* Hero */}
      <div className="pt-16 pb-14 px-6 text-center">
        <div className="inline-flex items-center gap-2 bg-white/10 border border-white/15 px-4 py-1.5 rounded-full text-white/75 text-sm font-medium mb-7">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          실시간 금리 모니터링
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 leading-tight tracking-tight">
          주택담보대출 금리 비교
        </h1>
        <p className="text-slate-400 text-base sm:text-lg max-w-lg mx-auto leading-relaxed">
          은행 · 보험사 · 대출상담사 기준별로<br className="hidden sm:block" />
          최저·최고 금리를 한눈에 비교하세요.
        </p>
      </div>

      {/* Cards */}
      <div className="px-5 pb-16 -mt-2">
        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-5">
          {CARDS.map((card, i) => (
            <button
              key={card.id}
              onClick={() => onNavigate(card.id)}
              className="group text-left bg-white rounded-2xl overflow-hidden shadow-lg hover:shadow-2xl hover:-translate-y-1.5 transition-all duration-300 animate-fade-in-up focus:outline-none focus:ring-2 focus:ring-white/50"
              style={{ animationDelay: `${i * 0.09}s` }}
            >
              {/* Top accent bar */}
              <div className={`h-1.5 bg-gradient-to-r ${card.topBar}`} />

              <div className="p-6">
                {/* Icon + badge */}
                <div className="flex items-start justify-between mb-5">
                  <span className="text-4xl leading-none">{card.icon}</span>
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${card.badgeBg}`}>
                    {card.badge}
                  </span>
                </div>

                {/* Title */}
                <h2 className="text-xl font-bold text-slate-900 mb-2 whitespace-pre-line leading-snug">
                  {card.title}
                </h2>

                {/* Description */}
                <p className="text-sm text-slate-500 mb-5 leading-relaxed">
                  {card.desc}
                </p>

                {/* Institution tags */}
                <div className="space-y-1.5 mb-5">
                  {card.institutions.map((inst, j) => (
                    <div key={j} className="flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-slate-300 shrink-0" />
                      <span className="text-xs text-slate-500">{inst}</span>
                    </div>
                  ))}
                </div>

                {/* CTA */}
                <div className={`flex items-center gap-1.5 text-sm font-semibold ${card.btnColor} transition-all`}>
                  자세히 보기
                  <span className="transition-transform duration-200 group-hover:translate-x-1">→</span>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
