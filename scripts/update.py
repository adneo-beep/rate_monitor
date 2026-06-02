"""
매일 10시 실행: 금리 스크레이핑 → public/rates.json, public/market-rates.json 업데이트
변경: 5대 은행 → 7개 은행(카카오뱅크·케이뱅크 추가), 시장금리 BOK API 추가
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE       = os.path.join(BASE_DIR, '..', 'public', 'rates.json')
FSS_JSON_FILE     = os.path.join(BASE_DIR, '..', 'public', 'fss.json')
MARKET_RATES_FILE = os.path.join(BASE_DIR, '..', 'public', 'market-rates.json')

BANK_META = {
    '우리은행':    {'id': 'woori',   'colorHex': '#3b82f6', 'name': '우리은행'},
    'KB국민은행':  {'id': 'kb',      'colorHex': '#f59e0b', 'name': 'KB국민은행'},
    '하나은행':    {'id': 'hana',    'colorHex': '#14b8a6', 'name': '하나은행'},
    '신한은행':    {'id': 'shinhan', 'colorHex': '#f97316', 'name': '신한은행'},
    'NH농협은행':  {'id': 'nh',      'colorHex': '#22c55e', 'name': 'NH농협은행'},
    '카카오뱅크':  {'id': 'kakao',   'colorHex': '#fde047', 'name': '카카오뱅크'},
    '케이뱅크':    {'id': 'kbank',   'colorHex': '#a78bfa', 'name': '케이뱅크'},
}

INSURANCE_STATIC = [
    {'id': 'samsung-life', 'name': '삼성생명', 'colorHex': '#6366f1', 'product': '삼성생명주택담보대출', 'minRate': 4.54, 'maxRate': 6.34},
    {'id': 'hanwha',       'name': '한화생명', 'colorHex': '#ef4444', 'product': '홈드림 모기지론',      'minRate': 4.82, 'maxRate': 6.83},
    {'id': 'kyobo',        'name': '교보생명', 'colorHex': '#10b981', 'product': '교보e아파트론',        'minRate': 5.39, 'maxRate': 5.81},
    {'id': 'samsung-fire', 'name': '삼성화재', 'colorHex': '#e11d48', 'product': '삼성화재 주택담보대출', 'minRate': 4.65, 'maxRate': 6.78},
]

BOK_API_KEY = 'Y2VMNWAZOAZNS0806QB9'
BOK_BASE    = 'https://ecos.bok.or.kr/api'

BANK_ORDER = ['kb', 'shinhan', 'hana', 'woori', 'nh', 'kakao', 'kbank']


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
                        // c[1]=기본금리, c[2]=가산금리, c[3]=최종금리(적용금리)
                        return {
                            min_rate: c[3]?.textContent.trim(),
                            max_rate: c[1]?.textContent.trim()   // 기본금리를 최고금리로 표시
                        };
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


async def scrape_kakao(browser):
    """카카오뱅크 - https://www.kakaobank.com/products/mortgageLoan"""
    page = await browser.new_page()
    try:
        await page.goto("https://www.kakaobank.com/products/mortgageLoan", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        data = await page.evaluate("""() => {
            // 금리 범위 텍스트 탐색
            const allText = document.body.innerText;
            // "연 X.XX% ~ Y.YY%" 패턴 찾기
            const m = allText.match(/연\\s*([\\d.]+)%?\\s*[~\\-]\\s*([\\d.]+)%/);
            if (m) return { min_rate: m[1], max_rate: m[2] };
            // 단일 금리 탐색
            const m2 = allText.match(/([\\d.]+)%/);
            if (m2) return { min_rate: m2[1], max_rate: null };
            return null;
        }""")
        if data and data.get('min_rate'):
            return {'bank': '카카오뱅크', 'product': '카카오뱅크 주택담보대출',
                    'min_rate': data['min_rate'], 'max_rate': data.get('max_rate', '-'), 'status': 'success'}
        # fallback: 텍스트에서 직접 탐색
        content = await page.evaluate("() => document.body.innerText")
        import re
        rates = re.findall(r'(\d+\.\d+)%', content)
        rates_f = [float(r) for r in rates if 1 < float(r) < 15]
        if rates_f:
            return {'bank': '카카오뱅크', 'product': '카카오뱅크 주택담보대출',
                    'min_rate': str(min(rates_f)), 'max_rate': str(max(rates_f)), 'status': 'success'}
        return {'bank': '카카오뱅크', 'status': 'error', 'message': '금리 데이터 없음'}
    except Exception as e:
        return {'bank': '카카오뱅크', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_kbank(browser):
    """케이뱅크 - https://www.kbanknow.com/ib20/mnu/FPMLON250000"""
    page = await browser.new_page()
    try:
        await page.goto(
            "https://www.kbanknow.com/ib20/mnu/FPMLON250000?phashid=sAySEh8",
            timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)
        data = await page.evaluate("""() => {
            const allText = document.body.innerText;
            // "연 X.XX% ~ Y.YY%" 패턴
            const m = allText.match(/연\\s*([\\d.]+)%?\\s*[~\\-]\\s*([\\d.]+)%/);
            if (m) return { min_rate: m[1], max_rate: m[2] };
            return null;
        }""")
        if data and data.get('min_rate'):
            return {'bank': '케이뱅크', 'product': '케이뱅크 아파트담보대출',
                    'min_rate': data['min_rate'], 'max_rate': data.get('max_rate', '-'), 'status': 'success'}
        content = await page.evaluate("() => document.body.innerText")
        import re
        rates = re.findall(r'(\d+\.\d+)%', content)
        rates_f = [float(r) for r in rates if 1 < float(r) < 15]
        if rates_f:
            return {'bank': '케이뱅크', 'product': '케이뱅크 아파트담보대출',
                    'min_rate': str(min(rates_f)), 'max_rate': str(max(rates_f)), 'status': 'success'}
        return {'bank': '케이뱅크', 'status': 'error', 'message': '금리 데이터 없음'}
    except Exception as e:
        return {'bank': '케이뱅크', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


def update_market_rates(now):
    """BOK API + KOFIA 스크레이핑으로 시장금리 업데이트 → public/market-rates.json"""
    import re

    # --- BOK ECOS API 국고채 조회 ---
    def fetch_bok_rate(item_code, days_back=7):
        end_d   = now.strftime('%Y%m%d')
        start_d = (now - timedelta(days=days_back)).strftime('%Y%m%d')
        url = f'{BOK_BASE}/StatisticSearch/{BOK_API_KEY}/json/kr/1/10/817Y002/D/{start_d}/{end_d}/{item_code}'
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                j = json.loads(r.read().decode('utf-8'))
            rows = [x for x in (j.get('StatisticSearch', {}).get('row') or [])
                    if x.get('DATA_VALUE') and x['DATA_VALUE'] != '-']
            if rows:
                return round(float(rows[-1]['DATA_VALUE']), 3)
        except Exception as e:
            print(f'    BOK fetch error ({item_code}): {e}')
        return None

    # --- KOFIA 금융채 AAA 시가평가 스크레이핑 ---
    def fetch_kofia_fin_bonds():
        """KOFIA 채권정보센터에서 금융채 AAA 시가평가수익률 조회"""
        date_str = now.strftime('%Y%m%d')
        # 공공데이터 API 시도 (JSON 응답)
        base_url = 'https://kofiabond.or.kr'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/json, */*',
            'Referer': 'https://kofiabond.or.kr/',
        }
        # 방법 1: getDiscountCurveInfo (금융채=4)
        try:
            import urllib.request as ureq
            req = ureq.Request(
                f'{base_url}/publicData/getDiscountCurveInfo.json?workDate={date_str}&typecode=4',
                headers=headers
            )
            with ureq.urlopen(req, timeout=10) as r:
                text = r.read().decode('utf-8')
                j = json.loads(text)
                # 응답 구조: [{term: '0.5', yield: '3.xx'}, ...]
                result = {}
                for item in j:
                    term = str(item.get('term') or item.get('TERM') or '')
                    rate = item.get('yield') or item.get('YIELD') or item.get('rate') or item.get('RATE')
                    if term and rate:
                        try:
                            result[float(term)] = round(float(str(rate).replace('%','')), 3)
                        except Exception:
                            pass
                if result:
                    return {
                        'fin6m':  result.get(0.5),
                        'fin1y':  result.get(1.0),
                        'fin3y':  result.get(3.0),
                        'fin5y':  result.get(5.0),
                    }
        except Exception as e:
            print(f'    KOFIA fetch error: {e}')
        return {}

    # 이전 값 읽기
    prev = {}
    if os.path.exists(MARKET_RATES_FILE):
        try:
            with open(MARKET_RATES_FILE, encoding='utf-8') as f:
                prev = json.load(f).get('rates', {})
        except Exception:
            pass

    def make_rate(key, new_val):
        old_val = (prev.get(key) or {}).get('value')
        change = round(new_val - old_val, 3) if new_val is not None and old_val is not None else None
        return {'value': new_val, 'change': change}

    print('  BOK 국고채 조회 중...')
    ktb3y  = fetch_bok_rate('010200000')
    ktb10y = fetch_bok_rate('010210000')
    print(f'    국고채 3년: {ktb3y}%  |  10년: {ktb10y}%')

    print('  KOFIA 금융채 AAA 시가평가 조회 중...')
    fin = fetch_kofia_fin_bonds()
    print(f'    금융채: {fin}')

    rates_out = {
        'ktb3y':  make_rate('ktb3y',  ktb3y ),
        'ktb10y': make_rate('ktb10y', ktb10y),
        'fin6m':  make_rate('fin6m',  fin.get('fin6m') ),
        'fin1y':  make_rate('fin1y',  fin.get('fin1y') ),
        'fin3y':  make_rate('fin3y',  fin.get('fin3y') ),
        'fin5y':  make_rate('fin5y',  fin.get('fin5y') ),
    }

    # 레이블 추가
    labels = {
        'ktb3y':  '국고채 3년',
        'ktb10y': '국고채 10년',
        'fin6m':  '금융채 6개월',
        'fin1y':  '금융채 1년',
        'fin3y':  '금융채 3년',
        'fin5y':  '금융채 5년',
    }
    for k in rates_out:
        rates_out[k]['label'] = labels[k]

    result = {
        'updatedAt': now.strftime('%Y.%m.%d %H:%M 기준'),
        'rates': rates_out,
    }
    with open(MARKET_RATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'  [OK] market-rates.json 업데이트: {result["updatedAt"]}')


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

    now = datetime.now()

    print("금리 수집 시작...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        scraped = []
        for fn in [scrape_woori, scrape_kb, scrape_hana, scrape_shinhan, scrape_nh,
                   scrape_kakao, scrape_kbank]:
            r = await fn(browser)
            scraped.append(r)
            ok = r.get('status') == 'success'
            detail = r.get('message') or f"{r.get('min_rate')} ~ {r.get('max_rate')}"
            print(f"  [{'OK' if ok else 'NG'}] {r.get('bank')}: {detail}")

        # 상담사 금리 업데이트 (browser 열린 상태에서 실행)
        await scrape_counselor_from_lovable(browser, now)

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
    print(f"\n[OK] public/rates.json 업데이트 완료: {result['updatedAt']}")

    # FSS 월별 데이터 업데이트
    print("\nFSS 월별 금리 수집 시작...")
    update_fss_history(now)

    # 시장금리 업데이트 (BOK + KOFIA)
    print("\n시장금리 수집 시작...")
    update_market_rates(now)

    # Git commit & push (로컬 실행 시에만, GitHub Actions는 EndBug/add-and-commit이 처리)
    if not os.environ.get('CI'):
        import subprocess
        repo_dir = os.path.join(BASE_DIR, '..')
        commit_msg = f"chore: update rates {result['updatedAt']} [skip ci]"
        try:
            subprocess.run(['git', 'add', 'public/rates.json', 'public/counselor.json', 'public/fss.json', 'public/market-rates.json'], cwd=repo_dir, check=True)
            subprocess.run(['git', 'commit', '-m', commit_msg], cwd=repo_dir, check=True)
            subprocess.run(['git', 'push', 'origin', 'master'], cwd=repo_dir, check=True)
            print("[OK] GitHub 푸시 완료")
        except subprocess.CalledProcessError as e:
            print(f"[NG] Git 오류: {e}")


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


def update_fss_history(now):
    """FSS API로 이번 달 최저금리 수집 → fss.json 월별 누적"""
    FSS_API_KEY = '736b1d88e7160ca02d43154c35ca6bc6'
    FSS_BASE = 'https://finlife.fss.or.kr/finlifeapi/mortgageLoanProductsSearch.json'

    BANK_MATCH = {
        '국민은행': 'kb', '신한은행': 'shinhan', '하나은행': 'hana',
        '우리은행': 'woori', '농협은행': 'nh',
    }
    INS_MATCH = {
        '삼성생명': 'samsungLife', '한화생명': 'hanwha',
        '교보생명': 'kyobo', '삼성화재': 'samsungFire',
    }

    def fetch_fss(grp):
        url = f'{FSS_BASE}?auth={FSS_API_KEY}&topFinGrpNo={grp}&pageNo=1'
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode('utf-8'))

    def calc_mins(base_list, option_list, match_map):
        """
        아파트(mrtg_type=A) + 분할상환(rpay_type=D) + (아파트) 상품명 우선 필터
        """
        result = {}
        for keyword, uid in match_map.items():
            # 기관 매칭
            matched_prods = [p for p in base_list if keyword in p.get('kor_co_nm', '')]
            # 신한은행처럼 여러 상품 있을 경우, '(아파트)' 포함 상품 우선
            apt_prods = [p for p in matched_prods if '(아파트)' in p.get('fin_prdt_nm', '')]
            target_prods = apt_prods if apt_prods else matched_prods
            codes = {p['fin_prdt_cd'] for p in target_prods}

            # mrtg_type=A(아파트) AND rpay_type=D(분할상환)
            opts = [o for o in option_list
                    if o.get('fin_prdt_cd') in codes
                    and o.get('mrtg_type') == 'A'
                    and o.get('rpay_type') == 'D']
            # 위 조건 없으면 mrtg_type=A 만
            if not opts:
                opts = [o for o in option_list
                        if o.get('fin_prdt_cd') in codes and o.get('mrtg_type') == 'A']
            # 그래도 없으면 전체
            if not opts:
                opts = [o for o in option_list if o.get('fin_prdt_cd') in codes]

            mins = [o['lend_rate_min'] for o in opts if o.get('lend_rate_min') and o['lend_rate_min'] > 0]
            result[uid] = round(min(mins), 2) if mins else None
        return result

    try:
        b_json = fetch_fss('020000')
        i_json = fetch_fss('050000')
        bank_mins = calc_mins(b_json['result']['baseList'], b_json['result']['optionList'], BANK_MATCH)
        ins_mins  = calc_mins(i_json['result']['baseList'], i_json['result']['optionList'], INS_MATCH)

        month_label = f"{str(now.year)[2:]}/{now.month:02d}"

        entry = {'month': month_label}
        for uid in ['kb', 'shinhan', 'hana', 'woori', 'nh']:
            entry[uid] = bank_mins.get(uid)
        for uid in ['samsungLife', 'hanwha', 'kyobo', 'samsungFire']:
            entry[uid] = ins_mins.get(uid)

        history = []
        if os.path.exists(FSS_JSON_FILE):
            with open(FSS_JSON_FILE, encoding='utf-8') as f:
                history = json.load(f).get('history', [])

        if history and history[-1].get('month') == month_label:
            history[-1] = entry  # 이달 값 변경됐으면 덮어쓰기
        else:
            history.append(entry)  # 새 달이면 추가

        with open(FSS_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump({'history': history}, f, ensure_ascii=False, indent=2)
        print(f"  [OK] fss.json 업데이트 완료: {month_label}")
    except Exception as e:
        print(f"  [NG] FSS 수집 실패: {e}")


if __name__ == '__main__':
    asyncio.run(main())
