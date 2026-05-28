import { useState, useEffect } from 'react'
import { COUNSELOR_TABLE_DATA, COUNSELOR_SOURCE_URL } from '../data/mockData'
import PageHeader from '../components/PageHeader'

const COUNSELOR_API_URL = 'https://api.example.com/counselor-rates'

function RateTypeBadge({ type }) {
  return (
    <span className="inline-block text-[10px] font-semibold bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
      {type}
    </span>
  )
}

function InstitutionCard({ institution }) {
  const { name, colorHex, rates } = institution

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-sm transition-shadow">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-slate-100">
        <div className="w-1 h-5 rounded-full shrink-0" style={{ backgroundColor: colorHex }} />
        <span className="font-bold text-slate-800 text-sm">{name}</span>
      </div>

      {/* Rate table */}
      {rates === null ? (
        <div className="px-4 py-4 text-xs text-slate-400 text-center">
          findsr.kr 미등록
        </div>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-100">
              <th className="px-3 py-2 text-left text-slate-400 font-medium w-20">금리유형</th>
              <th className="px-3 py-2 text-center text-slate-500 font-semibold">매매</th>
              <th className="px-3 py-2 text-center text-slate-500 font-semibold">가계</th>
            </tr>
          </thead>
          <tbody>
            {rates.map((row, i) => (
              <tr key={i} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60 transition-colors">
                <td className="px-3 py-2.5">
                  <RateTypeBadge type={row.type} />
                </td>
                <td className="px-3 py-2.5 text-center">
                  <span className="font-bold text-emerald-600 tabular-nums">{row.sell.toFixed(2)}%</span>
                </td>
                <td className="px-3 py-2.5 text-center">
                  <span className="font-bold text-blue-600 tabular-nums">{row.lease.toFixed(2)}%</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function PanelHeader({ title, subtitle }) {
  return (
    <div className="flex items-baseline justify-between mb-3">
      <h2 className="font-bold text-slate-700 text-sm">{title}</h2>
      <span className="text-xs text-slate-400">{subtitle}</span>
    </div>
  )
}

export default function CounselorView({ onBack }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        const res = await fetch(COUNSELOR_API_URL, { signal: AbortSignal.timeout(5000) })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        setData(json)
      } catch (err) {
        console.warn('상담사 API 연결 실패:', err.message)
        setData(COUNSELOR_TABLE_DATA)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 animate-fade-in">
      <PageHeader
        title="우리동네 대출상담사 기준"
        subtitle={`일 단위 업데이트${data ? ` · ${data.updatedAt}` : ''}`}
        onBack={onBack}
        accent="violet"
      />

      <div className="max-w-screen-xl mx-auto px-5 py-6 space-y-4">
        {/* Source */}
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>출처:</span>
          <a
            href={COUNSELOR_SOURCE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-violet-600 hover:underline font-medium"
          >
            {COUNSELOR_SOURCE_URL}
          </a>
        </div>

        {loading ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-12 flex items-center justify-center">
            <div className="flex items-center gap-3 text-slate-400 text-sm animate-pulse">
              <div className="w-4 h-4 border-2 border-slate-300 border-t-violet-500 rounded-full animate-spin" />
              데이터를 불러오는 중...
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Banks */}
            <div>
              <PanelHeader title="🏦 은행권" subtitle="국민 · 신한 · 하나 · 우리 · 농협" />
              <div className="space-y-3">
                {data.banks.map((b) => (
                  <InstitutionCard key={b.id} institution={b} />
                ))}
              </div>
            </div>

            {/* Right: Insurance */}
            <div>
              <PanelHeader title="🛡️ 보험사" subtitle="삼성생명 · 한화생명 · 교보생명 · 삼성화재" />
              <div className="space-y-3">
                {data.insurances.map((ins) => (
                  <InstitutionCard key={ins.id} institution={ins} />
                ))}
              </div>
            </div>
          </div>
        )}

        <p className="text-xs text-slate-400 text-center pb-2">
          * 매매: 아파트 매매 기준 / 가계: 가계자금(생활안정) 기준 · MCI 미가입·부수거래 충족 기준
        </p>
      </div>
    </div>
  )
}
