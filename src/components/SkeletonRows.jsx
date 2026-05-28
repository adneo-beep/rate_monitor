function SkeletonRow() {
  return (
    <div className="flex items-center py-4 px-5 border-b border-slate-100 last:border-0">
      <div className="flex items-center gap-3 flex-1 min-w-0 mr-4">
        <div className="w-1.5 h-10 rounded-full bg-slate-200 animate-pulse shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="h-3.5 bg-slate-200 rounded animate-pulse w-2/5 mb-2" />
          <div className="h-3 bg-slate-100 rounded animate-pulse w-3/5" />
        </div>
      </div>
      <div className="flex items-center gap-4 shrink-0">
        <div className="text-center min-w-[64px]">
          <div className="h-2.5 bg-slate-100 rounded animate-pulse w-12 mx-auto mb-2" />
          <div className="h-6 bg-slate-200 rounded animate-pulse w-14 mx-auto" />
          <div className="h-2.5 bg-slate-100 rounded animate-pulse w-10 mx-auto mt-2" />
        </div>
        <div className="w-px h-10 bg-slate-200" />
        <div className="text-center min-w-[64px]">
          <div className="h-2.5 bg-slate-100 rounded animate-pulse w-12 mx-auto mb-2" />
          <div className="h-6 bg-slate-200 rounded animate-pulse w-14 mx-auto" />
          <div className="h-2.5 bg-slate-100 rounded animate-pulse w-10 mx-auto mt-2" />
        </div>
      </div>
    </div>
  )
}

export default function SkeletonRows({ count = 5 }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </>
  )
}
