import { useState, useEffect } from 'react'
import { MOCK_BANK_RATES, BANK_CHART_DATA, INSURANCE_CHART_DATA } from '../data/mockData'
import RateRow from '../components/RateRow'
import RateChart from '../components/RateChart'
import PageHeader from '../components/PageHeader'

const BANK_SERIES = [
  { key: 'kb',     name: 'KB국민',  color: '#f59e0b' },
  { key: 'shinhan',name: '신한',    color: '#3b82f6' },
  { key: 'hana',   name: '하나',    color: '#10b981' },
  { key: 'woori',  name: '우리',    color: '#8b5cf6' },
  { key: 'nh',     name: '농협',    color: '#f97316' },
]
const INSURANCE_SERIES = [
  { key: 'samsungLife', name: '삼성생명', color: '#6366f1' },
  { key: 'hanwha',      name: '한화생명', color: '#f43f5e' },
  { key: 'kyobo',       name: '교보생명', color: '#0ea5e9' },
  { key: 'samsungFire', name: '삼성화재', color: '#14b8a6' },
]

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

function SummaryBadge({ label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex items-center gap-3 shadow-sm">
      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      <div>
        <div className="text-xs text-slate-400">{label}</div>
        <div className="font-bold text-slate-800 text-sm tabular-nums">{value}</div>
      </div>
    </div>
  )
}

export default function BankRatesView({ onBack }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/rates.json', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setData)
      .catch(() => setData(MOCK_BANK_RATES))
      .finally(() => setLoading(false))
  }, [])

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

  const allItems = [...data.banks, ...data.insurances].filter((d) => d.minRate !== null)
  const minAll = Math.min(...allItems.map((d) => d.minRate))
  const maxAll = Math.max(...allItems.map((d) => d.maxRate ?? d.minRate))
  const lowestItem = allItems.find((d) => d.minRate === minAll)
  const highestItem = allItems.find((d) => (d.maxRate ?? d.minRate) === maxAll)

  return (
    <div className="min-h-screen bg-slate-50 animate-fade-in">
      <PageHeader
        title="금융사 홈페이지 공시 기준"
        subtitle={`일 단위 업데이트 · ${data.updatedAt}`}
        onBack={onBack}
        accent="blue"
      />

      <div className="max-w-screen-xl mx-auto px-5 py-6 space-y-5">
        {/* Summary strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <SummaryBadge label="전체 최저금리" value={`${minAll.toFixed(2)}%`} color="#10b981" />
          <SummaryBadge label="기관" value={lowestItem?.name ?? '-'} color={lowestItem?.colorHex ?? '#94a3b8'} />
          <SummaryBadge label="전체 최고금리" value={`${maxAll.toFixed(2)}%`} color="#f43f5e" />
          <SummaryBadge label="기관" value={highestItem?.name ?? '-'} color={highestItem?.colorHex ?? '#94a3b8'} />
        </div>

        {/* Split panels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <SectionPanel title="🏦 은행권" subtitle="국민 · 신한 · 하나 · 우리 · 농협">
            {data.banks.map((b) => (
              <RateRow key={b.id} {...b} />
            ))}
          </SectionPanel>

          <SectionPanel title="🛡️ 보험사" subtitle="삼성생명 · 한화생명 · 교보생명 · 삼성화재">
            {data.insurances.map((ins) => (
              <RateRow key={ins.id} {...ins} />
            ))}
          </SectionPanel>
        </div>

        {/* Time series chart */}
        <RateChart
          bankData={BANK_CHART_DATA}
          insuranceData={INSURANCE_CHART_DATA}
          bankSeries={BANK_SERIES}
          insuranceSeries={INSURANCE_SERIES}
        />

        <p className="text-xs text-slate-400 text-center pb-2">
          * 공시 기준 금리는 실제 적용 금리와 다를 수 있으며, 개인 신용등급 및 대출 조건에 따라 차등 적용됩니다.
        </p>
      </div>
    </div>
  )
}
