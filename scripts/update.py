"""
매일 10시 실행: 5대 은행 금리 스크레이핑 → public/rates.json 업데이트
"""
import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, '..', 'public', 'rates.json')

BANK_META = {
    '우리은행':   {'id': 'woori',   'colorHex': '#3b82f6', 'name': '우리은행'},
    'KB국민은행': {'id': 'kb',      'colorHex': '#f59e0b', 'name': 'KB국민은행'},
    '하나은행':   {'id': 'hana',    'colorHex': '#14b8a6', 'name': '하나은행'},
    '신한은행':   {'id': 'shinhan', 'colorHex': '#f97316', 'name': '신한은행'},
    'NH농협은행': {'id': 'nh',      'colorHex': '#22c55e', 'name': 'NH농협은행'},
}

INSURANCE_STATIC = [
    {'id': 'samsung-life', 'name': '삼성생명', 'colorHex': '#6366f1', 'product': '삼성생명주택담보대출', 'minRate': 4.54, 'maxRate': 6.34},
    {'id': 'hanwha',       'name': '한화생명', 'colorHex': '#ef4444', 'product': '홈드림 모기지론',      'minRate': 4.82, 'maxRate': 6.83},
    {'id': 'kyobo',        'name': '교보생명', 'colorHex': '#10b981', 'product': '교보e아파트론',        'minRate': 5.39, 'maxRate': 5.81},
    {'id': 'samsung-fire', 'name': '삼성화재', 'colorHex': '#e11d48', 'product': '삼성화재 주택담보대출', 'minRate': 4.65, 'maxRate': 6.78},
]

BANK_ORDER = ['kb', 'shinhan', 'hana', 'woori', 'nh']


def parse_rate(s):
    try:
        return round(float(str(s).replace('%', '').replace(',', '').strip()), 3)
    except Exception:
        return None


async def scrape_woori(browser):
    page = await browser.new_page()
    try:
        await page.goto("https://spot.wooribank.com/pot/Dream?withyou=POLON0070", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        data = await page.evaluate("""() => {
            for (const table of document.querySelectorAll('table')) {
                const cap = table.querySelector('caption');
                if (!cap || !cap.textContent.includes('우리아파트론(일반자금)')) continue;
                for (const row of table.querySelectorAll('tbody tr')) {
                    const c = [...row.querySelectorAll('td')];
                    if (c[0] && c[0].textContent.includes('변동금리(5년)'))
                        return { min_rate: c[3]?.textContent.trim(), max_rate: '-' };
                }
            }
            return null;
        }""")
        if data:
            return {'bank': '우리은행', 'product': '우리아파트론 변동금리(5년)',
                    'min_rate': data['min_rate'], 'max_rate': data['max_rate'], 'status': 'success'}
        return {'bank': '우리은행', 'status': 'error'}
    except Exception as e:
        return {'bank': '우리은행', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_kb(browser):
    page = await browser.new_page()
    try:
        await page.goto(
            "https://obank.kbstar.com/quics?page=C103557&cc=b104363:b104516&isNew=N&prcode=LN20001160&QSL=F",
            timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.get_by_role("tab", name="금리 및 이율").click()
        await page.wait_for_timeout(2000)
        data = await page.evaluate("""() => {
            for (const row of document.querySelectorAll('table tbody tr')) {
                const c = [...row.querySelectorAll('td')];
                if (c[0] && c[0].textContent.trim() === '금융채5년')
                    return { min_rate: c[4]?.textContent.trim(), max_rate: c[5]?.textContent.trim() };
            }
            return null;
        }""")
        if data:
            return {'bank': 'KB국민은행', 'product': 'KB주택담보대출 금융채5년',
                    'min_rate': data['min_rate'], 'max_rate': data['max_rate'], 'status': 'success'}
        return {'bank': 'KB국민은행', 'status': 'error'}
    except Exception as e:
        return {'bank': 'KB국민은행', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_hana(browser):
    page = await browser.new_page()
    try:
        await page.goto(
            "https://www.kebhana.com/app/portal/mkt/contents/rate_p02_03.do?actionCode=02&subMenu=21&RateIrdCd=072100210001D",
            timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        data = await page.evaluate("""() => {
            for (const table of document.querySelectorAll('table')) {
                for (const row of table.querySelectorAll('tbody tr')) {
                    const c = [...row.querySelectorAll('td')];
                    if (c[0] && c[0].textContent.includes('5년물 금융채')) {
                        const range = c[5]?.textContent.trim() || '';
                        const parts = range.split('~');
                        return { min_rate: parts[0]?.trim(), max_rate: parts[1]?.trim() };
                    }
                }
            }
            return null;
        }""")
        if data:
            return {'bank': '하나은행', 'product': '하나 혼합금리 모기지론 5년물 금융채',
                    'min_rate': data['min_rate'], 'max_rate': data['max_rate'], 'status': 'success'}
        return {'bank': '하나은행', 'status': 'error'}
    except Exception as e:
        return {'bank': '하나은행', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_shinhan(browser):
    page = await browser.new_page()
    try:
        await page.goto("https://bank.shinhan.com/index.jsp?cr=020305010000&pcd=S614221100", timeout=30000)
        await page.wait_for_selector('[role="tab"]', timeout=10000)
        await page.wait_for_timeout(1000)
        tabs = await page.query_selector_all('[role="tab"]')
        for t in tabs:
            if "금리안내" in await t.inner_text():
                await t.click()
                break
        await page.wait_for_timeout(4000)
        data = await page.evaluate("""() => {
            for (const row of document.querySelectorAll('[role="row"]')) {
                const cells = [...row.querySelectorAll('[role="gridcell"]')];
                if (cells[0] && cells[0].textContent.trim() === '금융채(5년)') {
                    const s = v => (v || '').replace('%', '').trim() || '-';
                    return { min_rate: s(cells[4]?.textContent), max_rate: s(cells[5]?.textContent) };
                }
            }
            return null;
        }""")
        if data:
            return {'bank': '신한은행', 'product': '신한주택대출(아파트) 금융채(5년)',
                    'min_rate': data['min_rate'], 'max_rate': data['max_rate'], 'status': 'success'}
        return {'bank': '신한은행', 'status': 'error'}
    except Exception as e:
        return {'bank': '신한은행', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_nh(browser):
    page = await browser.new_page()
    try:
        await page.goto("https://smartmarket.nonghyup.com/servlet/BFLNW0004R.view", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        data = await page.evaluate("""() => {
            for (const row of document.querySelectorAll('table tr')) {
                const c = [...row.querySelectorAll('td')];
                if (!c.find(td => td.textContent.includes('NH주택담보대출_5년주기형'))) continue;
                const text = (c[3] || c[c.length - 2])?.textContent || '';
                const maxM = text.match(/최고\\s*연\\s*([\\d.]+)/);
                const minM = text.match(/최저\\s*연\\s*([\\d.]+)/);
                return { min_rate: minM?.[1] || '-', max_rate: maxM?.[1] || '-' };
            }
            return null;
        }""")
        if data:
            return {'bank': 'NH농협은행', 'product': 'NH주택담보대출_5년주기형',
                    'min_rate': data['min_rate'], 'max_rate': data['max_rate'], 'status': 'success'}
        return {'bank': 'NH농협은행', 'status': 'error'}
    except Exception as e:
        return {'bank': 'NH농협은행', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def main():
    # 이전 rates.json 읽기 (히스토리 누적용)
    prev_banks = {}
    bank_history = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, encoding='utf-8') as f:
                prev = json.load(f)
            for b in prev.get('banks', []):
                prev_banks[b['id']] = b
            bank_history = prev.get('bankHistory', [])
        except Exception:
            pass

    print("금리 수집 시작...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        scraped = []
        for fn in [scrape_woori, scrape_kb, scrape_hana, scrape_shinhan, scrape_nh]:
            r = await fn(browser)
            scraped.append(r)
            ok = r.get('status') == 'success'
            detail = r.get('message') or f"{r.get('min_rate')} ~ {r.get('max_rate')}"
            print(f"  [{'OK' if ok else 'NG'}] {r.get('bank')}: {detail}")
        await browser.close()

    banks = []
    for raw in scraped:
        if raw.get('status') != 'success':
            continue
        meta = BANK_META.get(raw['bank'])
        if not meta:
            continue
        min_r = parse_rate(raw.get('min_rate'))
        max_r = parse_rate(raw.get('max_rate'))
        prev = prev_banks.get(meta['id'], {})
        prev_min = prev.get('minRate')
        prev_max = prev.get('maxRate')
        min_change = round(min_r - prev_min, 3) if min_r is not None and prev_min is not None else 0
        max_change = round(max_r - prev_max, 3) if max_r is not None and prev_max is not None else 0
        banks.append({
            'id': meta['id'],
            'name': meta['name'],
            'colorHex': meta['colorHex'],
            'product': raw.get('product', '주택담보대출'),
            'minRate': min_r,
            'maxRate': max_r,
            'minChange': min_change,
            'maxChange': max_change,
        })

    banks.sort(key=lambda b: BANK_ORDER.index(b['id']) if b['id'] in BANK_ORDER else 99)

    now = datetime.now()

    # 오늘 날짜 히스토리 항목 생성
    today_key = f"{now.month}/{now.day}"
    today_entry = {'date': today_key}
    for b in banks:
        bid = b['id']
        today_entry[f'{bid}_min'] = b['minRate']
        today_entry[f'{bid}_max'] = b['maxRate']

    # 오늘 날짜가 이미 있으면 갱신, 없으면 추가
    if bank_history and bank_history[-1]['date'] == today_key:
        bank_history[-1] = today_entry
    else:
        bank_history.append(today_entry)

    result = {
        'updatedAt': now.strftime('%Y.%m.%d %H:%M 기준'),
        'banks': banks,
        'insurances': INSURANCE_STATIC,
        'bankHistory': bank_history,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ public/rates.json 업데이트 완료: {result['updatedAt']}")

    # 상담사 금리 업데이트 (lovable.app)
    await scrape_counselor_from_lovable(browser, now)

    # Git commit & push
    import subprocess
    repo_dir = os.path.join(BASE_DIR, '..')
    commit_msg = f"chore: update rates {result['updatedAt']} [skip ci]"
    try:
        subprocess.run(['git', 'add', 'public/rates.json', 'public/counselor.json'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'commit', '-m', commit_msg], cwd=repo_dir, check=True)
        subprocess.run(['git', 'push', 'origin', 'master'], cwd=repo_dir, check=True)
        print("✅ GitHub 푸시 완료")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git 오류: {e}")


async def scrape_counselor_from_lovable(browser, now):
    """loan-rate-scoop.lovable.app에서 금리표 파싱 → counselor.json 저장"""
    COUNSELOR_FILE = os.path.join(BASE_DIR, '..', 'public', 'counselor.json')
    LOVABLE_URL = 'https://loan-rate-scoop.lovable.app/'

    BANK_META = {
        '국민':   {'id': 'kb',      'name': 'KB국민은행', 'colorHex': '#f59e0b'},
        '신한':   {'id': 'shinhan', 'name': '신한은행',   'colorHex': '#f97316'},
        '하나':   {'id': 'hana',    'name': '하나은행',   'colorHex': '#14b8a6'},
        '우리':   {'id': 'woori',   'name': '우리은행',   'colorHex': '#3b82f6'},
        '농협은행': {'id': 'nh',    'name': 'NH농협은행', 'colorHex': '#22c55e'},
    }
    INS_META = {
        '한화생명': {'id': 'hanwha',       'name': '한화생명', 'colorHex': '#ef4444'},
        '삼성화재': {'id': 'samsung-fire', 'name': '삼성화재', 'colorHex': '#e11d48'},
    }
    # 컬럼명 정규화 (OCR 오인식 → 실제 유형명)
    COL_NORMALIZE = {'5년년': '5년변동', '5년(혼합)': '5년혼합', '5년(주기)': '5년주기'}
    BANK_ORDER = ['kb', 'shinhan', 'hana', 'woori', 'nh']

    print("\n상담사 금리 수집 시작 (loan-rate-scoop.lovable.app)...")
    try:
        page = await browser.new_page()
        await page.goto(LOVABLE_URL, timeout=30000)

        # 테이블이 나타날 때까지 대기 (최대 40초)
        try:
            await page.wait_for_selector('table tbody tr', timeout=40000)
        except Exception:
            print("  [NG] 테이블 로드 타임아웃")
            await page.close()
            return

        # 헤더 + 전체 행 추출
        raw = await page.evaluate("""() => {
            const headers = [...document.querySelectorAll('table thead th')]
                .map(h => h.innerText.trim());
            const rows = [...document.querySelectorAll('table tbody tr')].map(r =>
                [...r.querySelectorAll('td, th')].map(c => c.innerText.trim())
            );
            const dateMatch = document.body.innerText.match(/기준일\\s*([\\d-]+)/);
            return { headers, rows, date: dateMatch ? dateMatch[1] : '' };
        }""")
        await page.close()

        headers = raw['headers']  # ['금융기관', '구분', '1년', '5년', ...]
        rows = raw['rows']
        date_str = raw['date']    # e.g. '2026-05-29'

        def parse_rate(s):
            s = s.strip().replace('%', '')
            try:
                return round(float(s), 3)
            except Exception:
                return None

        # 헤더 인덱스 매핑 (index 0=금융기관, 1=구분, 2~=금리유형)
        rate_cols = [COL_NORMALIZE.get(h, h) for h in headers[2:]]

        # 행 파싱: 매매 행(bank, '매매', r[2]...) / 생활안정 행('생활안정', r[1]...)
        institution_data = {}  # key: 기관명, value: {sell: [], lease: []}
        current_bank = None
        for row in rows:
            if not row:
                continue
            if row[0] not in ('생활안정',) and len(row) > 1 and row[1] == '매매':
                current_bank = row[0]
                institution_data[current_bank] = {'sell': row[2:], 'lease': []}
            elif row[0] == '생활안정' and current_bank:
                institution_data[current_bank]['lease'] = row[1:]

        def build_rates(sell_vals, lease_vals):
            rates = []
            for i, col_name in enumerate(rate_cols):
                s = parse_rate(sell_vals[i]) if i < len(sell_vals) else None
                l = parse_rate(lease_vals[i]) if i < len(lease_vals) else None
                if s is not None or l is not None:
                    rates.append({'type': col_name, 'sell': s, 'lease': l})
            return rates or None

        banks_out = []
        for key, meta in BANK_META.items():
            d = institution_data.get(key, {})
            rates = build_rates(d.get('sell', []), d.get('lease', []))
            banks_out.append({'id': meta['id'], 'name': meta['name'],
                              'colorHex': meta['colorHex'], 'rates': rates})
        banks_out.sort(key=lambda b: BANK_ORDER.index(b['id']) if b['id'] in BANK_ORDER else 99)

        ins_out = []
        for key, meta in INS_META.items():
            d = institution_data.get(key, {})
            rates = build_rates(d.get('sell', []), d.get('lease', []))
            ins_out.append({'id': meta['id'], 'name': meta['name'],
                            'colorHex': meta['colorHex'], 'rates': rates})

        # 기존 파일에서 삼성생명·교보생명 유지 (lovable에 없음)
        if os.path.exists(COUNSELOR_FILE):
            with open(COUNSELOR_FILE, encoding='utf-8') as f:
                prev = json.load(f)
            existing_ids = {i['id'] for i in ins_out}
            for ins in prev.get('insurances', []):
                if ins['id'] not in existing_ids:
                    ins_out.append(ins)

        updated_at = date_str.replace('-', '.') + ' 기준' if date_str else now.strftime('%Y.%m.%d 기준')
        counselor_result = {
            'updatedAt': updated_at,
            'banks': banks_out,
            'insurances': ins_out,
        }
        with open(COUNSELOR_FILE, 'w', encoding='utf-8') as f:
            json.dump(counselor_result, f, ensure_ascii=False, indent=2)
        print(f"  [OK] counselor.json 업데이트 완료: {updated_at}")

    except Exception as e:
        print(f"  [NG] 상담사 금리 업데이트 실패: {e}")


if __name__ == '__main__':
    asyncio.run(main())
