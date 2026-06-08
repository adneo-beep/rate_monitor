'use client'
import { useState, useEffect, useCallback } from 'react'
import PageHeader from '../components/PageHeader'

const RATE_KEYS = ['ktb3y', 'ktb10y', 'fin6m', 'fin1y', 'fin3y', 'fin5y']

const RATE_META = {
  ktb3y:  { label: '국고채 3년',   group: 'gov',  color: '#3b82f6' },
  ktb10y: { label: '국고채 10년',  group: 'gov',  color: '#6366f1' },
  fin6m:  { label: '금융채 6개월', group: 'fin',  color: '#f59e0b' },
  fin1y:  { label: '금융채 1년',   group: 'fin',  color: '#f97316' },
  fin3y:  { label: '금융채 3년',   group: 'fin',  color: '#ef4444' },
  fin5y:  { label: '금융채 5년',   group: 'fin',  color: '#e11d48' },
}

function ChangeChip({ value }) {
  if (value == null) return null
  if (value === 0)   return <span className="text-slate-400 text-[11px]">변동없음</span>
  return value > 0
    ? <span className="text-rose-500 text-[11px] font-semibold">▲ +{value.toFixed(3)}%</span>
    : <span className="text-blue-500 text-[11px] font-semibold">▼ {value.toFixed(3)}%</span>
}

function RateCard({ rateKey, data }) {
  const meta  = RATE_META[rateKey]
  const entry = data?.rates?.[rateKey]
  const val   = entry?.value
  const chg   = entry?.change

  return (
    <div className="bg-white rounded-xl border border-slate-200 px-5 py-4 hover:shadow-sm transition-shadow">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: meta.color }} />
        <span className="text-xs font-semibold text-slate-600">{meta.label}</span>
      </div>

      <div className="text-2xl font-bold text-slate-800 tabular-nums mb-1">
        {val != null ? `${val.toFixed(3)}%` : '—'}
      </div>

      <div className="text-[11px] text-slate-400">
        {chg != null ? <ChangeChip value={chg} /> : <span>전일 대비</span>}
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 px-5 py-4 animate-pulse">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-2 h-2 rounded-full bg-slate-200" />
        <div className="h-3 w-20 rounded bg-slate-200" />
      </div>
      <div className="h-8 w-24 rounded bg-slate-200 mb-2" />
      <div className="h-3 w-16 rounded bg-slate-100" />
    </div>
  )
}

export default function MarketRatesView({ onBack }) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    fetch('/market-rates.json', { cache: 'no-store' })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const govKeys = RATE_KEYS.filter(k => RATE_META[k].group === 'gov')
  const finKeys = RATE_KEYS.filter(k => RATE_META[k].group === 'fin')

  return (
    <div className="min-h-screen bg-slate-50 animate-fade-in">
      <PageHeader
        title="시장금리"
        subtitle={data?.updatedAt ?? 'BOK · KOFIA 기준'}
        onBack={onBack}
        onRefresh={load}
        isRefreshing={loading}
        accent="blue"
      />

      <div className="max-w-screen-xl mx-auto px-5 py-6 space-y-6">
        {/* 안내 배너 */}
        <div className="rounded-xl bg-blue-50 border border-blue-200 px-4 py-3 text-xs text-blue-700 space-y-0.5">
          <p>🏛️ <b>국고채</b>: 한국은행 ECOS API 기준 (일별)</p>
          <p>🏦 <b>금융채</b>: 채권시가평가수익률 기준 무보증 AAA (KOFIA 채권정보센터 기준)</p>
        </div>

        {/* 국고채 섹션 */}
        <div>
          <h2 className="text-sm font-bold text-slate-700 mb-3">🏛️ 국고채</h2>
          <div className="grid grid-cols-2 sm:grid-cols-2 gap-3">
            {loading
              ? govKeys.map(k => <SkeletonCard key={k} />)
              : govKeys.map(k => <RateCard key={k} rateKey={k} data={data} />)
            }
          </div>
        </div>

        {/* 금융채 섹션 */}
        <div>
          <h2 className="text-sm font-bold text-slate-700 mb-3">🏦 금융채 (무보증 AAA, 시가평가)</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {loading
              ? finKeys.map(k => <SkeletonCard key={k} />)
              : finKeys.map(k => <RateCard key={k} rateKey={k} data={data} />)
            }
          </div>
        </div>

        {/* 금융채 데이터 없는 경우 안내 */}
        {!loading && data && finKeys.every(k => data.rates?.[k]?.value == null) && (
          <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-xs text-amber-700">
            ⚠️ 금융채 시가평가 데이터는 매일 자동 수집됩니다. 첫 수집 후 표시됩니다.
          </div>
        )}

        <p className="text-xs text-slate-400 text-center pb-2">
          국고채: 한국은행 ECOS | 금융채 무보증 AAA: 금융투자협회 채권정보센터
        </p>
      </div>
    </div>
  )
}
