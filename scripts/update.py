"""
매일 10시 실행: 5대 은행 금리 스크레이핑 → public/rates.json 업데이트
                findsr.kr 이미지 → Claude Vision → public/counselor.json 업데이트
"""
import asyncio
import base64
import json
import os
import urllib.request
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

    # findsr.kr 상담사 금리 업데이트
    await update_counselor(browser_instance=None, now=now)

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


async def update_counselor(browser_instance, now):
    """findsr.kr에서 오늘 금리표 이미지를 가져와 Claude Vision으로 파싱 후 counselor.json 저장"""
    COUNSELOR_FILE = os.path.join(BASE_DIR, '..', 'public', 'counselor.json')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    if not ANTHROPIC_API_KEY:
        print("⚠️  ANTHROPIC_API_KEY 없음 — 상담사 금리 건너뜀")
        return

    print("\n상담사 금리 수집 시작 (findsr.kr)...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto('https://findsr.kr/new1/product.html', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=15000)

            # 오늘 날짜의 '아파트담보대출 금리표' 게시글 찾기
            today_str = f"{now.month:02d}/{now.day:02d}"
            post_url = await page.evaluate(f"""() => {{
                for (const span of document.querySelectorAll('span.title')) {{
                    const text = span.innerText.trim();
                    if (text.includes('{today_str}') && text.includes('아파트담보대출')) {{
                        const m = span.getAttribute('onclick').match(/href='([^']+)'/);
                        return m ? 'https://findsr.kr' + m[1] : null;
                    }}
                }}
                return null;
            }}""")

            if not post_url:
                print(f"  [NG] {today_str} 아파트담보대출 금리표 게시글 없음")
                await browser.close()
                return

            await page.goto(post_url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=15000)

            # 금리표 이미지 URL 추출 (로고 제외, 가장 큰 이미지)
            img_url = await page.evaluate("""() => {
                const imgs = [...document.querySelectorAll('img')]
                    .filter(i => i.width > 200 && i.height > 200);
                return imgs[0]?.src || null;
            }""")
            await browser.close()

        if not img_url:
            print("  [NG] 금리표 이미지 없음")
            return

        print(f"  이미지: {img_url}")

        # 이미지 다운로드
        req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_bytes = resp.read()
        img_b64 = base64.standard_b64encode(img_bytes).decode()

        # Claude Vision으로 파싱
        import urllib.request as urlreq
        payload = json.dumps({
            "model": "claude-opus-4-7",
            "max_tokens": 2048,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                    {"type": "text", "text": (
                        "이 이미지는 한국 주택담보대출 금리표입니다. "
                        "은행별(KB국민은행, 신한은행, 하나은행, 우리은행, NH농협은행)로 "
                        "금리유형(예: 6개월, 1년, 3년, 5년, 5년변동, 5년주기, 5년혼합 등)별 "
                        "매매금리와 가계금리를 추출해 아래 JSON 형식으로만 답하세요.\n"
                        "형식: [{\"bank\":\"KB국민은행\",\"rates\":[{\"type\":\"5년\",\"sell\":4.52,\"lease\":4.68}]}]\n"
                        "보험사(삼성생명, 한화생명, 교보생명, 삼성화재)가 있으면 같은 형식으로 포함하세요. "
                        "숫자는 float, 없으면 null. JSON만 출력하세요."
                    )}
                ]
            }]
        }, ensure_ascii=False).encode()

        api_req = urlreq.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'x-api-key': ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            }
        )
        with urlreq.urlopen(api_req, timeout=60) as resp:
            api_result = json.loads(resp.read())

        raw_json = api_result['content'][0]['text'].strip()
        # 코드블록 제거
        if raw_json.startswith('```'):
            raw_json = raw_json.split('```')[1]
            if raw_json.startswith('json'):
                raw_json = raw_json[4:]
        parsed = json.loads(raw_json.strip())

        BANK_META_C = {
            'KB국민은행':  {'id': 'kb',      'colorHex': '#f59e0b'},
            '신한은행':    {'id': 'shinhan', 'colorHex': '#f97316'},
            '하나은행':    {'id': 'hana',    'colorHex': '#14b8a6'},
            '우리은행':    {'id': 'woori',   'colorHex': '#3b82f6'},
            'NH농협은행':  {'id': 'nh',      'colorHex': '#22c55e'},
        }
        INS_META_C = {
            '삼성생명': {'id': 'samsung-life', 'colorHex': '#6366f1'},
            '한화생명': {'id': 'hanwha',       'colorHex': '#ef4444'},
            '교보생명': {'id': 'kyobo',        'colorHex': '#10b981'},
            '삼성화재': {'id': 'samsung-fire', 'colorHex': '#e11d48'},
        }
        BANK_ORDER_C = ['kb', 'shinhan', 'hana', 'woori', 'nh']

        banks_out, ins_out = [], []
        for item in parsed:
            name = item.get('bank', '')
            rates = item.get('rates', [])
            if name in BANK_META_C:
                m = BANK_META_C[name]
                banks_out.append({'id': m['id'], 'name': name, 'colorHex': m['colorHex'], 'rates': rates})
            elif name in INS_META_C:
                m = INS_META_C[name]
                ins_out.append({'id': m['id'], 'name': name, 'colorHex': m['colorHex'], 'rates': rates or None})

        banks_out.sort(key=lambda b: BANK_ORDER_C.index(b['id']) if b['id'] in BANK_ORDER_C else 99)

        # 기존 파일에서 누락된 보험사 채우기
        existing_ids = {i['id'] for i in ins_out}
        if os.path.exists(COUNSELOR_FILE):
            with open(COUNSELOR_FILE, encoding='utf-8') as f:
                prev = json.load(f)
            for ins in prev.get('insurances', []):
                if ins['id'] not in existing_ids:
                    ins_out.append(ins)

        counselor_result = {
            'updatedAt': now.strftime('%Y.%m.%d 기준'),
            'banks': banks_out,
            'insurances': ins_out,
        }
        with open(COUNSELOR_FILE, 'w', encoding='utf-8') as f:
            json.dump(counselor_result, f, ensure_ascii=False, indent=2)
        print(f"  ✅ counselor.json 업데이트 완료: {counselor_result['updatedAt']}")

    except Exception as e:
        print(f"  [NG] 상담사 금리 업데이트 실패: {e}")


if __name__ == '__main__':
    asyncio.run(main())
