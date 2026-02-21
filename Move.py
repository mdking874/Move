import telebot
import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------
# ১. বটের টোকেন
BOT_TOKEN = "8508230875:AAGEldhmFI56fkrc_O_op-epuf9gdTaezvg"
bot = telebot.TeleBot(BOT_TOKEN)

# ২. বিশাল মুভি ওয়েবসাইট লিস্ট (২০২৬ লেটেস্ট ডোমেইন)
MOVIE_SITES = [
    {"name": "FilmyZilla", "url": "https://www.filmyzilla.com.cm/search/"},
    {"name": "VegaMovies", "url": "https://vegamovies.ngo/?s="},
    {"name": "9xMovies", "url": "https://9xmovies.photo/?s="},
    {"name": "MoviesFlix", "url": "https://moviesflix.uno/?s="},
    {"name": "HDHub4u", "url": "https://hdhub4u.tv/?s="},
    {"name": "Bolly4u", "url": "https://bolly4u.org/?s="},
    {"name": "KatMovieHD", "url": "https://katmoviehd.net.in/?s="},
    {"name": "9xFlix", "url": "https://9xflix.com/?s="},
    {"name": "Mp4Moviez", "url": "https://www.mp4moviez.com.mx/search.php?q="},
    {"name": "SkyMoviesHD", "url": "https://skymovieshd.ink/search.php?q="},
    {"name": "MovieZilla", "url": "https://www.moviezilla.xyz/search?q="},
    {"name": "DownloadHub", "url": "https://downloadhub.cloud/?s="},
    {"name": "123MKV", "url": "https://123mkv.center/?s="},
    {"name": "Pahe", "url": "https://pahe.ink/?s="},
    {"name": "Khatrimaza", "url": "https://khatrimaza.org.in/?s="}
]

# ৩. ক্লিন প্লেয়ার ইউআরএল
CLEAN_PLAYER_URL = "https://hlsjs.video-dev.org/demo/?src="
# ---------------------------------------------------------

def get_clean_link(page_url):
    """পেজের ভেতর থেকে ডাইরেক্ট ভিডিও লিংক বের করার চেষ্টা"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(page_url, headers=headers, timeout=5)
        # m3u8 বা mp4 খুঁজবে
        video_match = re.search(r'(https?://[^\s"\'<>]+\.(m3u8|mp4))', res.text)
        if video_match:
            link = video_match.group(1)
            return (CLEAN_PLAYER_URL + link if ".m3u8" in link else link), "🛡 Clean Player ✅"
        return page_url, "🔗 Web Link (Page)"
    except:
        return page_url, "🔗 Web Link"

def scrape_single_site(site, movie_name):
    """একটি নির্দিষ্ট সাইট থেকে ডেটা স্ক্র্যাপ করার ফাংশন"""
    results = []
    try:
        query = movie_name.replace(" ", "+")
        search_url = site["url"] + query
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(search_url, headers=headers, timeout=8)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # সব লিংক থেকে মুভির নাম মিলিয়ে বের করা
        links = soup.find_all('a', href=True)
        found_count = 0
        
        for link in links:
            title = link.text.strip()
            href = link['href']
            
            if movie_name.lower() in title.lower() and len(href) > 25:
                # ফুল ইউআরএল চেক
                if not href.startswith("http"):
                    base = "/".join(site["url"].split("/")[:3])
                    href = base + href
                
                play_url, status = get_clean_link(href)
                
                results.append({
                    "title": title,
                    "url": play_url,
                    "status": status,
                    "site": site["name"]
                })
                found_count += 1
                if found_count >= 2: break # প্রতি সাইট থেকে সেরা ২টা রেজাল্ট
    except:
        pass
    return results

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 **মুভি কিং বট চালু হয়েছে!**\nসবচেয়ে বড় ১৫+ ওয়েবসাইট থেকে মুভি খুঁজতে শুধু নাম লিখে পাঠান।\n\nযেমন: `Pushpa 2` বা `Tiger 3`")

@bot.message_handler(func=lambda message: True)
def search_handler(message):
    movie_name = message.text
    chat_id = message.chat.id
    
    bot.send_chat_action(chat_id, 'typing')
    msg = bot.send_message(chat_id, f"🔍 ১৫টি ওয়েবসাইটে *{movie_name}* খোঁজা হচ্ছে... একটু সময় দিন মামু।", parse_mode='Markdown')

    all_found = []
    
    # মাল্টি-থ্রেডিং ব্যবহার করে একসাথে সব সাইটে সার্চ (সুপার ফাস্ট)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scrape_single_site, site, movie_name) for site in MOVIE_SITES]
        for future in futures:
            all_found.extend(future.result())

    if not all_found:
        bot.edit_message_text("❌ দুঃখিত মামু, ১৫টি সাইট খুঁজেও কোনো মুভি পেলাম না। মুভির নাম ঠিক আছে তো?", chat_id, msg.message_id)
        return

    # আউটপুট সাজানো (সেরা ১০টি রেজাল্ট দেখাবে)
    response_text = f"🍿 **{movie_name}** এর জন্য সেরা রেজাল্টসমূহ:\n\n"
    for i, m in enumerate(all_found[:10], 1):
        response_text += f"{i}. 🎬 **{m['title']}**\n"
        response_text += f"   🌐 সাইট: {m['site']} | {m['status']}\n"
        response_text += f"   ▶️ [এখানে ক্লিক করে দেখুন]({m['url']})\n\n"
    
    response_text += "➖➖➖➖➖➖➖➖➖➖\n💡 মুভি না চললে তালিকার অন্য লিংকে ক্লিক করুন।"
    
    bot.delete_message(chat_id, msg.message_id)
    bot.send_message(chat_id, response_text, parse_mode='Markdown', disable_web_page_preview=True)

print("Ultimate Movie Search Engine is Live...")
bot.infinity_polling()
