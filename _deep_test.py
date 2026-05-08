"""
Diagnostico profundo: abre site 5x, identifica EXATAMENTE quais slots
fillam cada vez, posicao na pagina, e padrao.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(__file__).parent / '_deep'
OUT.mkdir(exist_ok=True)
URL = 'https://noticiareality.blog/?nc='


async def inspect(page, run_idx):
    print(f'\n=== RUN {run_idx} ===')
    page.on('pageerror', lambda e: None)  # silencia erros de redirect blocked

    await page.goto(URL + str(run_idx), wait_until='domcontentloaded', timeout=30000)
    await page.wait_for_timeout(7000)

    # screenshot do topo
    await page.screenshot(path=str(OUT/f'run{run_idx}_top.png'), clip={'x':0,'y':0,'width':1440,'height':1100})

    # scroll pra meio + bottom
    await page.evaluate('window.scrollTo(0, 1500)')
    await page.wait_for_timeout(1500)
    await page.screenshot(path=str(OUT/f'run{run_idx}_mid.png'), clip={'x':0,'y':0,'width':1440,'height':1100})

    # inspeciona cada iframe
    iframes = await page.query_selector_all('iframe[src*="/ads/"]')
    summary = []
    for i, fr in enumerate(iframes):
        src = await fr.get_attribute('src') or ''
        slot = src.split('/')[-1].replace('.html','').replace('-clean','').replace('300x250-','300x250 ')
        box = await fr.bounding_box()
        y = int(box['y']) if box else 0

        try:
            cf = await fr.content_frame()
            if not cf:
                summary.append({'i':i,'slot':slot,'y':y,'status':'NO_FRAME'})
                continue

            inner_iframes = await cf.query_selector_all('iframe')
            biggest = 0
            for sub in inner_iframes:
                bb = await sub.bounding_box()
                if bb and bb['width']*bb['height'] > biggest:
                    biggest = bb['width']*bb['height']

            fb_visible = await cf.evaluate('''() => {
                const fb = document.getElementById('fb');
                return fb && fb.classList.contains('show');
            }''')

            if biggest > 1000:
                summary.append({'i':i,'slot':slot,'y':y,'status':f'REAL ({int(biggest)}px2)'})
            elif fb_visible:
                summary.append({'i':i,'slot':slot,'y':y,'status':'FALLBACK'})
            else:
                summary.append({'i':i,'slot':slot,'y':y,'status':'LOADING'})
        except Exception as e:
            summary.append({'i':i,'slot':slot,'y':y,'status':f'ERR: {str(e)[:30]}'})

    # ordena por posicao Y (topo p baixo)
    summary.sort(key=lambda x: x['y'])
    real_count = 0
    for s in summary:
        flag = '✅' if 'REAL' in s['status'] else ('🟧' if s['status']=='FALLBACK' else '⏳')
        if 'REAL' in s['status']: real_count += 1
        print(f"  {flag} y={s['y']:5d} {s['slot']:18s} → {s['status']}")
    print(f'  TOTAL REAL: {real_count}/{len(summary)} ({real_count/len(summary)*100:.0f}%)')
    return real_count, len(summary), summary


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        results = []
        for run in range(5):
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                viewport={'width':1440,'height':900},
                locale='es-MX',
            )
            page = await ctx.new_page()
            r, t, summ = await inspect(page, run + 1)
            results.append((r, t, summ))
            await ctx.close()
            await asyncio.sleep(1)

        await browser.close()

        # padrao: quais slots fillaram em quais runs
        print('\n' + '='*70)
        print('PADRAO POR SLOT (5 runs):')
        print('='*70)
        all_slots = {}
        for run_idx, (r, t, summ) in enumerate(results):
            for s in summ:
                key = f"{s['slot']} @ y={s['y']}"
                if key not in all_slots:
                    all_slots[key] = []
                all_slots[key].append('REAL' in s['status'])

        for key in sorted(all_slots.keys(), key=lambda k: int(k.split('y=')[1])):
            vals = all_slots[key]
            fills = sum(vals)
            bar = ''.join(['█' if v else '·' for v in vals])
            print(f'  {key:40s} {bar} ({fills}/{len(vals)})')

        total_real = sum(r for r,t,_ in results)
        total_slots = sum(t for r,t,_ in results)
        print(f'\nTOTAL: {total_real}/{total_slots} ({total_real/total_slots*100:.1f}%) ad real')


asyncio.run(main())
