#!/usr/bin/env python3
"""RSS 抓取脚本 — 每天运行一次，保存新文章到 data/articles.json"""

import json
import os
import hashlib
from datetime import datetime
from xml.etree import ElementTree
from urllib.request import urlopen, Request
from urllib.error import URLError

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'articles.json')
FEEDS_FILE = os.path.join(os.path.dirname(__file__), 'feeds.json')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

def fetch_feed(url):
    """抓取单个 RSS 源"""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  ❌ 抓取失败 {url}: {e}")
        return None

def parse_rss(xml_content, feed_name):
    """解析 RSS XML，返回文章列表"""
    articles = []
    try:
        root = ElementTree.fromstring(xml_content)
        
        # RSS 2.0 格式
        items = root.findall('.//item')
        for item in items:
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            desc = item.findtext('description', '').strip()
            # 清理 HTML 标签
            import re
            desc = re.sub(r'<[^>]+>', '', desc) if desc else ''
            pub_date = item.findtext('pubDate', '')
            
            if title and link:
                articles.append({
                    'id': hashlib.md5(link.encode()).hexdigest()[:12],
                    'title': title,
                    'link': link,
                    'description': desc[:200],
                    'feed': feed_name,
                    'pubDate': pub_date,
                    'fetched_at': datetime.now().isoformat()
                })
        
        # Atom 格式
        if not items:
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            for entry in entries:
                title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
                summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
                updated_elem = entry.find('{http://www.w3.org/2005/Atom}updated')
                
                title = title_elem.text.strip() if title_elem is not None else ''
                link = link_elem.get('href', '') if link_elem is not None else ''
                desc = summary_elem.text.strip() if summary_elem is not None else ''
                pub_date = updated_elem.text if updated_elem is not None else ''
                
                if title and link:
                    articles.append({
                        'id': hashlib.md5(link.encode()).hexdigest()[:12],
                        'title': title,
                        'link': link,
                        'description': desc[:200],
                        'feed': feed_name,
                        'pubDate': pub_date,
                        'fetched_at': datetime.now().isoformat()
                    })
    except Exception as e:
        print(f"  ❌ 解析失败 {feed_name}: {e}")
    
    return articles

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 加载已有文章
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for article in json.load(f):
                existing[article['id']] = article
    
    # 加载 feeds
    with open(FEEDS_FILE, 'r', encoding='utf-8') as f:
        feeds = json.load(f)['feeds']
    
    new_count = 0
    print(f"📡 开始抓取 {len(feeds)} 个 RSS 源...")
    
    for feed in feeds:
        name = feed['name']
        url = feed['url']
        print(f"\n  📰 {name}")
        
        xml = fetch_feed(url)
        if not xml:
            continue
        
        articles = parse_rss(xml, name)
        print(f"    获取 {len(articles)} 篇文章")
        
        for article in articles:
            if article['id'] not in existing:
                existing[article['id']] = article
                new_count += 1
            else:
                # 更新抓取时间
                existing[article['id']]['fetched_at'] = datetime.now().isoformat()
    
    # 按时间倒序
    all_articles = sorted(
        existing.values(),
        key=lambda x: x.get('pubDate', '') or x['fetched_at'],
        reverse=True
    )
    
    # 只保留最近 500 篇
    all_articles = all_articles[:500]
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成！新增 {new_count} 篇，总计 {len(all_articles)} 篇")

if __name__ == '__main__':
    main()
