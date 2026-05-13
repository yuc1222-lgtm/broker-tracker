import asyncio
import csv
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright

URL = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGB/ZGB.djhtm"
CSV_FILE = "broker_history.csv"
FIELDNAMES = ["資料日期", "類型", "券商名稱", "買進金額", "賣出金額", "差額", "單位億元"]

def parse_number(s):
    s = s.strip().replace(",", "").replace(" ", "")
    try:
        return int(s)
    except:
        return 0

async def fetch_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        # 抓取日期
        try:
            date_text = await page.locator(".t11").first.inner_text()
            date_match = re.search(r"\d{4}/\d{2}/\d{2}", date_text)
            date_str = date_match.group(0) if date_match else datetime.now().strftime("%Y/%m/%d")
        except:
            date_str = datetime.now().strftime("%Y/%m/%d")

        # 抓取表格
        async def parse_table(index):
            rows = []
            tables = await page.locator("table.t0").all()
            if len(tables) <= index:
                return rows
            trs = await tables[index].locator("tr").all()
            for tr in trs:
                tds = await tr.locator("td").all()
                if len(tds) < 4:
                    continue
                cells = [await td.inner_text() for td in tds[:4]]
                name = cells[0].strip()
                if name in ["券商名稱", "買超", "賣超", ""]:
                    continue
                rows.append(cells)
            return rows[:4]

        buy_rows = await parse_table(0)
        sell_rows = await parse_table(1)
        await browser.close()
        return date_str, buy_rows, sell_rows

def save_to_csv(date_str, buy_rows, sell_rows):
    # 檢查今日是否已存在
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["資料日期"] == date_str:
                    print(f"今日資料已存在：{date_str}，跳過")
                    return False

    # 寫入資料
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        for row in buy_rows:
            diff = parse_number(row[3])
            writer.writerow({
                "資料日期": date_str,
                "類型": "買超",
                "券商名稱": row[0].strip(),
                "買進金額": parse_number(row[1]),
                "賣出金額": parse_number(row[2]),
                "差額": diff,
                "單位億元": round(diff / 1e8, 2)
            })

        for row in sell_rows:
            diff = parse_number(row[3])
            writer.writerow({
                "資料日期": date_str,
                "類型": "賣超",
                "券商名稱": row[0].strip(),
                "買進金額": parse_number(row[1]),
                "賣出金額": parse_number(row[2]),
                "差額": diff,
                "單位億元": round(abs(diff) / 1e8, 2)
            })

    print(f"寫入完成：{date_str}，買超 {len(buy_rows)} 筆，賣超 {len(sell_rows)} 筆")
    return True

async def main():
    print("開始抓取...")
    date_str, buy_rows, sell_rows = await fetch_data()
    print(f"日期：{date_str}，買超：{len(buy_rows)} 筆，賣超：{len(sell_rows)} 筆")
    save_to_csv(date_str, buy_rows, sell_rows)

if __name__ == "__main__":
    asyncio.run(main())
