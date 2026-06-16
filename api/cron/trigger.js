// Vercel Cron: 매일 00:10 UTC (09:10 KST) → GitHub Actions workflow_dispatch 실행
export default async function handler(req, res) {
  // Vercel Cron 요청만 허용
  if (req.headers['authorization'] !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: 'Unauthorized' })
  }

  const token = process.env.GITHUB_PAT
  if (!token) {
    return res.status(500).json({ error: 'GITHUB_PAT not set' })
  }

  const response = await fetch(
    'https://api.github.com/repos/adneo-beep/rate_monitor/actions/workflows/update-rates.yml/dispatches',
    {
      method: 'POST',
      headers: {
        Authorization: `token ${token}`,
        Accept: 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ref: 'master' }),
    }
  )

  if (response.status === 204) {
    console.log('✅ GitHub Actions workflow triggered')
    return res.status(200).json({ ok: true, triggered: new Date().toISOString() })
  }

  const body = await response.text()
  console.error('❌ GitHub dispatch failed:', response.status, body)
  return res.status(500).json({ error: 'GitHub dispatch failed', status: response.status })
}
