import telebot
import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------
# ১. বটের টোকেন
BOT_TOKEN = "8508230875:AAGEldhmFI56fkrc_O_op-epuf9gdTaezvg"
bot = telebot.TeleBot(BOT_TOKEN)

# ২. মুভি সাইট লিস্ট
MOVIE_SITES = [
    {"name": "FilmyZilla", "url": "https://www.filmyzilla.com.cm/search/"},
    {"name": "VegaMovies", "url": "https://vegamovies.ngo/?s="},
    {"name": "9xMovies", "url": "https://9xmovies.photo/?s="},
    {"name": "HDHub4u", "url": "https://hdhub4u.work/?s="}
]

# ৩. ক্লিন প্লেয়ার এবং ডিফল্ট ছবি
CLEAN_PLAYER_URL = "https://hlsjs.video-dev.org/demo/?src="
DEFAULT_THUMB = "https://cdn-icons-png.flaticon.com/512/12560/12560376.png"
# ---------------------------------------------------------

def extract_video_file(page_url):
    """পেজের ভেতর থেকে ডাইরেক্ট ভিডিও ফাইল খোঁজা"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(page_url, headers=headers, timeout=5)
        
        # m3u8 বা mp4 লিংক আছে কি না চেক
        m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8)', res.text)
        if m3u8_match:
            return CLEAN_PLAYER_URL + m3u8_match.group(1), "🛡 Clean Player ✅"
            
        mp4_match = re.search(r'(https?://[^\s"\'<>]+\.mp4)', res.text)
        if mp4_match:
            return mp4_match.group(1), "🚀 Direct Play ✅"
            
        return None, None
    except:
        return None, None

def scrape_site(site, movie_name):
    """সাইট থেকে মুভি, ছবি এবং লিংক স্ক্র্যাপ করা"""
    results = []
    try:
        query = movie_name.replace(" ", "+")
        search_url = site["url"] + query
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(search_url, headers=headers, timeout=8)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # মুভি আইটেম খোঁজা (ক্লাস নেম সাইট অনুযায়ী ভিন্ন হতে পারে)
        items = soup.find_all(['div', 'a'], class_=re.compile(r'post|movie|item|poster', re.I))
        
        found_count = 0
        for item in items:
            link_tag = item.find('a', href=True) if item.name != 'a' else item
            img_tag = item.find('img')
            
            if link_tag:
                title = (img_tag.get('alt') or link_tag.text or "Movie").strip()
                href = link_tag['href']
                thumb = img_tag.get('src') or img_tag.get('data-src') if img_tag else DEFAULT_THUMB
                
                # মুভির নাম আংশিক মিললে (ছোট শব্দে সার্চ)
                if movie_name.lower() in title.lower() and len(href) > 20:
                    if not href.startswith("http"):
                        base = "/".join(site["url"].split("/")[:3])
                        href = base + href
                    
                    # ক্লিন ভিডিও ফাইল চেক
                    clean_link, status = extract_video_file(href)
                    
                    if clean_link:
                        results.append({
                            "title": title,
                            "url": clean_link,
                            "thumb": thumb,
                            "status": status,
                            "site": site["name"]
                        })
                        found_count += 1
                        if found_count >= 1: break # প্রতি সাইট থেকে ১টা সেরা ক্লিন রেজাল্ট
    except: pass
    return results

@bot.message_handler(func=lambda message: True)
def handle_search(message):
    movie_name = message.text
    chat_id = message.chat.id
    
    if len(movie_name) < 2:
        bot.send_message(chat_id, "⚠️ মুভির নাম অন্তত ২ অক্ষরের লিখুন মামু।")
        return

    # সার্চিং স্ট্যাটাস
    searching_msg = bot.send_message(chat_id, f"🔍 *{movie_name}* এর ক্লিন লিংক খোঁজা হচ্ছে... একটু দাঁড়ান।", parse_mode='Markdown')
    bot.send_chat_action(chat_id, 'upload_photo')
    
    final_list = []
    # মাল্টি-থ্রেডিং এ দ্রুত সার্চ
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scrape_site, site, movie_name) for site in MOVIE_SITES]
        for f in futures:
            final_list.extend(f.result())

    # যদি মুভি পাওয়া যায়
    if final_list:
        bot.delete_message(chat_id, searching_msg.message_id)
        for m in final_list[:5]:
            caption = (
                f"🎬 **{m['title']}**\n"
                f"✅ **Status:** {m['status']}\n"
                f"🌐 **Site:** {m['site']}\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"▶️ [এখানে ক্লিক করে দেখুন]({m['url']})"
            )
            try:
                # যদি ছবিতে প্রোটোকল না থাকে (যেমন //cdn...)
                if m['thumb'].startswith('//'): m['thumb'] = 'https:' + m['thumb']
                bot.send_photo(chat_id, m['thumb'], caption=caption, parse_mode='Markdown')
            except:
                bot.send_message(chat_id, caption, parse_mode='Markdown')
    
    # যদি কিছুই না পাওয়া যায়
    else:
        bot.edit_message_text(f"❌ দুঃখিত মামু, *{movie_name}* এর কোনো ক্লিন ভিডিও ফাইল পাওয়া যায়নি। অন্য মুভির নাম ট্রাই করুন!", chat_id, searching_msg.message_id, parse_mode='Markdown')

print("Advanced Movie Bot is Running...")
bot.infinity_polling()
