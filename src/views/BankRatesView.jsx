import { useState, useEffect, useCallback } from 'react'
import { MOCK_BANK_RATES } from '../data/mockData'
import RateRow from '../components/RateRow'
import PageHeader from '../components/PageHeader'

const BANK_SERIES = [
  { key: 'kb',     name: 'KB국민',   color: '#f59e0b' },
  { key: 'shinhan',name: '신한',     color: '#3b82f6' },
  { key: 'hana',   name: '하나',     color: '#10b981' },
  { key: 'woori',  name: '우리',     color: '#8b5cf6' },
  { key: 'nh',     name: '농협',     color: '#f97316' },
  { key: 'kakao',  name: '카카오',   color: '#facc15' },
  { key: 'kbank',  name: '케이뱅크', color: '#a78bfa' },
]

// 은행/인터넷은행 구분
const TRAD_BANK_IDS   = new Set(['kb', 'shinhan', 'hana', 'woori', 'nh'])
const INET_BANK_IDS   = new Set(['kakao', 'kbank'])

const HOMEPAGE_URLS = {
  'kb':           'https://obank.kbstar.com/quics?page=C103557&cc=b104363:b104516&isNew=N&prcode=LN20001160&QSL=F#loading',
  'woori':        'https://spot.wooribank.com/pot/Dream?withyou=POLON0056&cc=c010528:c010531;c012425:c012399&PLM_PDCD=P020000125&PRD_CD=P020000125&HOST_PRD_CD=2001110150000',
  'nh':           'https://smartmarket.nonghyup.com/servlet/BFLNW0100R.view',
  'hana':         'https://www.kebhana.com/app/portal/mkt/contents/rate_p02_03.do?actionCode=02&subMenu=21&RateIrdCd=072100210001D',
  'shinhan':      'https://bank.shinhan.com/index.jsp#020305010000',
  'kakao':        'https://www.kakaobank.com/products/mortgageLoan',
  'kbank':        'https://www.kbanknow.com/ib20/mnu/FPMLON250000?phashid=sAySEh8',
  'samsung-life': 'https://www.samsunglife.com/individual/products/loan/detail/F34820',
  'hanwha':       'https://m.hanwhalife.com/mobile/finance/loan/FN_LNTGD000_P20000.do?catecode=LD020100',
  'kyobo':        'https://www.kyobo.com/dgt/web/loan/product/house/security/apartment-security-text-detail',
  'samsung-fire': 'https://www.samsungfire.com/vh/page/VH.HPLN0023.do?_ic=direct',
}

function SectionPanel({ title, subtitle, children }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="px-5 py-4 bg-slate-50 border-b border-slate-200 flex items-baseline justify-between gap-2">
        <h2 className="font-bold text-slate-800">{title}</h2>
        <span className="text-xs text-slate-400 shrink-0">{subtitle}</span>
      </div>
      <div>{children}</div>
    </div>
  )
}


export default function BankRatesView({ onBack }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    fetch('/rates.json', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setData)
      .catch(() => setData(MOCK_BANK_RATES))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400 text-sm animate-pulse">
          <div className="w-4 h-4 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin" />
          데이터를 불러오는 중...
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 animate-fade-in">
      <PageHeader
        title="금융사 홈페이지 공시 기준"
        subtitle={`일 단위 업데이트 · ${data.updatedAt}`}
        onBack={onBack}
        onRefresh={load}
        isRefreshing={loading}
        accent="blue"
      />

      <div className="max-w-screen-xl mx-auto px-5 py-6 space-y-5">
        {/* Split panels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* 시중은행 */}
          <SectionPanel title="🏦 시중은행" subtitle="금융채(5년)변동 기준">
            {data.banks.filter(b => TRAD_BANK_IDS.has(b.id)).map((b) => (
              <RateRow key={b.id} {...b} url={HOMEPAGE_URLS[b.id]} />
            ))}
          </SectionPanel>

          {/* 보험사 */}
          <SectionPanel title="🛡️ 보험사" subtitle="삼성생명 · 한화생명 · 교보생명 · 삼성화재">
            {data.insurances.map((ins) => (
              <RateRow key={ins.id} {...ins} url={HOMEPAGE_URLS[ins.id]} />
            ))}
          </SectionPanel>
        </div>

        {/* 인터넷 은행 */}
        <SectionPanel title="🌐 인터넷은행" subtitle="카카오뱅크 · 케이뱅크">
          <div className="grid grid-cols-1 sm:grid-cols-2">
            {data.banks.filter(b => INET_BANK_IDS.has(b.id)).map((b) => (
              <RateRow key={b.id} {...b} url={HOMEPAGE_URLS[b.id]} />
            ))}
            {!data.banks.some(b => INET_BANK_IDS.has(b.id)) && (
              <div className="col-span-2 py-6 text-center text-sm text-slate-400">데이터를 불러오는 중입니다</div>
            )}
          </div>
        </SectionPanel>

        <p className="text-xs text-slate-400 text-center pb-2">
          * 공시 기준 금리는 실제 적용 금리와 다를 수 있으며, 개인 신용등급 및 대출 조건에 따라 차등 적용됩니다.
        </p>
      </div>
    </div>
  )
}
