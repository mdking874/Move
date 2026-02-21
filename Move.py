import telebot
import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------
BOT_TOKEN = "8508230875:AAGEldhmFI56fkrc_O_op-epuf9gdTaezvg"
bot = telebot.TeleBot(BOT_TOKEN)

# মুভি সাইট লিস্ট
MOVIE_SITES = [
    {"name": "FilmyZilla", "url": "https://www.filmyzilla.com.cm/search/"},
    {"name": "VegaMovies", "url": "https://vegamovies.ngo/?s="},
    {"name": "9xMovies", "url": "https://9xmovies.photo/?s="},
    {"name": "HDHub4u", "url": "https://hdhub4u.work/?s="}
]

CLEAN_PLAYER_URL = "https://hlsjs.video-dev.org/demo/?src="
DEFAULT_THUMB = "https://cdn-icons-png.flaticon.com/512/12560/12560376.png"
# ---------------------------------------------------------

def extract_video_file(page_url):
    """পেজের ভেতর থেকে ডাইরেক্ট ভিডিও ফাইল (m3u8/mp4) খুঁজে বের করা"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(page_url, headers=headers, timeout=5)
        
        # m3u8 লিংক খুঁজবে (সবচেয়ে ভালো ক্লিন প্লেয়ারের জন্য)
        m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8)', res.text)
        if m3u8_match:
            return CLEAN_PLAYER_URL + m3u8_match.group(1), "🛡 Clean Player ✅"
            
        # mp4 ডাইরেক্ট লিংক
        mp4_match = re.search(r'(https?://[^\s"\'<>]+\.mp4)', res.text)
        if mp4_match:
            return mp4_match.group(1), "🚀 Direct Play ✅"
            
        return None, None # যদি কোনো ক্লিন ফাইল না পায়
    except:
        return None, None

def scrape_site(site, movie_name):
    """সাইট থেকে মুভি, থাম্বনেইল এবং ক্লিন লিংক বের করা"""
    results = []
    try:
        query = movie_name.replace(" ", "+")
        search_url = site["url"] + query
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(search_url, headers=headers, timeout=7)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # মুভি আইটেমগুলো খোঁজা (পোস্টারসহ)
        for item in soup.find_all(['div', 'a'], class_=re.compile(r'post|movie|item|poster', re.I)):
            link_tag = item.find('a', href=True) if item.name != 'a' else item
            img_tag = item.find('img')
            
            if link_tag:
                title = (img_tag.get('alt') or link_tag.text or "Movie").strip()
                href = link_tag['href']
                thumb = img_tag.get('src') or img_tag.get('data-src') if img_tag else DEFAULT_THUMB
                
                # মুভির নাম আংশিক মিললে (অল্প শব্দে সার্চ)
                if movie_name.lower() in title.lower() and len(href) > 20:
                    if not href.startswith("http"):
                        base = "/".join(site["url"].split("/")[:3])
                        href = base + href
                    
                    # এখন চেক করবে ক্লিন ভিডিও ফাইল আছে কি না
                    clean_link, status = extract_video_file(href)
                    
                    if clean_link: # শুধুমাত্র ক্লিন লিংক পেলেই লিস্টে নিবে
                        results.append({
                            "title": title,
                            "url": clean_link,
                            "thumb": thumb,
                            "status": status,
                            "site": site["name"]
                        })
                        if len(results) >= 1: break 
    except: pass
    return results

@bot.message_handler(func=lambda message: True)
def handle_search(message):
    movie_name = message.text
    chat_id = message.chat.id
    
    if len(movie_name) < 2: return # ১ অক্ষরের সার্চ ইগনোর করবে

    bot.send_chat_action(chat_id, 'upload_photo')
    
    final_list = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scrape_site, site, movie_name) for site in MOVIE_SITES]
        for f in futures:
            final_list.extend(f.result())

    if not final_list:
        # যদি কোনো ক্লিন লিংক না পাওয়া যায়, তবে কিছু পাঠানোর দরকার নেই
        # অথবা চাইলে একটা ছোট মেসেজ দিতে পারেন:
        # bot.send_message(chat_id, "❌ কোনো ক্লিন ভিডিও ফাইল পাওয়া যায়নি।")
        return

    # রেজাল্ট পাঠানো (থাম্বনেইলসহ)
    for m in final_list[:5]: # সেরা ৫টি ক্লিন রেজাল্ট
        caption = (
            f"🎬 **{m['title']}**\n"
            f"✅ **Status:** {m['status']}\n"
            f"🌐 **Site:** {m['site']}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"▶️ [Click To Play Now]({m['url']})"
        )
        try:
            bot.send_photo(chat_id, m['thumb'], caption=caption, parse_mode='Markdown')
        except:
            bot.send_message(chat_id, caption, parse_mode='Markdown')

print("Clean Player Bot is Running...")
bot.infinity_polling()
