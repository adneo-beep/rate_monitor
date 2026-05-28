import { useState } from 'react'

export default function RateChart({ bankData, insuranceData, bankSeries, insuranceSeries, xKey = 'date' }) {
  const [tab, setTab] = useState('bank')

  const data = tab === 'bank' ? bankData : insuranceData
  const series = tab === 'bank' ? bankSeries : insuranceSeries

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="px-5 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-3">
        <h2 className="font-bold text-slate-800">최저금리 추이</h2>
        <div className="flex bg-slate-200 rounded-lg p-0.5 text-xs font-medium">
          <button
            onClick={() => setTab('bank')}
            className={`px-3 py-1.5 rounded-md transition-colors ${tab === 'bank' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            은행권
          </button>
          <button
            onClick={() => setTab('insurance')}
            className={`px-3 py-1.5 rounded-md transition-colors ${tab === 'insurance' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            보험사
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-4 py-2.5 text-left text-slate-400 font-medium w-16 sticky left-0 bg-slate-50">
                {xKey === 'month' ? '월' : '날짜'}
              </th>
              {series.map((s) => (
                <th key={s.key} className="px-3 py-2.5 text-center text-slate-600 font-semibold">
                  <div className="flex items-center justify-center gap-1.5">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: s.color }} />
                    {s.name}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[...data].reverse().map((row, i) => (
              <tr
                key={row[xKey]}
                className={`border-b border-slate-50 last:border-0 ${i === 0 ? 'bg-emerald-50/40' : 'hover:bg-slate-50/60'} transition-colors`}
              >
                <td className="px-4 py-2 text-slate-500 font-medium sticky left-0 bg-inherit tabular-nums">
                  {row[xKey]}
                </td>
                {series.map((s) => (
                  <td key={s.key} className="px-3 py-2 text-center tabular-nums font-semibold text-slate-700">
                    {row[s.key] != null ? `${Number(row[s.key]).toFixed(2)}%` : '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
