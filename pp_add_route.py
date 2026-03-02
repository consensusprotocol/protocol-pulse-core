import os, logging
W = "/home/runner/workspace"

with open(W + "/routes.py") as f:
    routes = f.read()

if "def media_unified()" in routes:
    print("Route already present, skipping")
else:
    new_route = """

@app.route('/media-unified')
def media_unified():
    try:
        from models import Podcast
        series_list = [
            {"key": "everything_21m", "title": "Everything Divided by 21 Million", "description": "Bitcoin, time, freedom.", "first_id": "FA8tvWEydcA", "ep_count": 11},
            {"key": "big_print", "title": "The Big Print", "description": "Fed wealth extraction.", "first_id": "W09CNU_q6Yo", "ep_count": 12},
            {"key": "daylight_robbery", "title": "Daylight Robbery", "description": "Taxation shaped civilization.", "first_id": "ZCc78wvwd6U", "ep_count": 13},
            {"key": "genesis_book", "title": "The Genesis Book", "description": "Origins of Bitcoin.", "first_id": "y7KBeC4jfbo", "ep_count": 5},
        ]
        tag = os.environ.get("AMAZON_AFFILIATE_TAG", "protocolpulse-20")
        all_books = [
            {"title": "The Bitcoin Standard", "author": "Saifedean Ammous", "amazon_url": "https://www.amazon.com/dp/1119473861?tag=" + tag, "color": "#f7931a"},
            {"title": "Broken Money", "author": "Lyn Alden", "amazon_url": "https://www.amazon.com/dp/B0CG8985FR?tag=" + tag, "color": "#3b82f6"},
            {"title": "The Sovereign Individual", "author": "Davidson & Rees-Mogg", "amazon_url": "https://www.amazon.com/dp/0684832720?tag=" + tag, "color": "#8b5cf6"},
            {"title": "Mastering Bitcoin", "author": "Andreas Antonopoulos", "amazon_url": "https://www.amazon.com/dp/1098150090?tag=" + tag, "color": "#f59e0b"},
        ]
        latest_episodes = Podcast.query.order_by(Podcast.published_date.desc()).limit(12).all()
        podcast_count = Podcast.query.count()
        return render_template("media_unified.html",
            series_list=series_list, series_count=len(series_list),
            latest_episodes=latest_episodes, podcast_count=podcast_count,
            all_books=all_books)
    except Exception as e:
        logging.error("media_unified error: " + str(e))
        return render_template("media_unified.html",
            series_list=[], series_count=0,
            latest_episodes=[], podcast_count=0, all_books=[])

"""
    # Insert before the media_terminal redirect function
    if "\ndef media_terminal():" in routes:
        routes = routes.replace("\ndef media_terminal():", new_route + "\ndef media_terminal():", 1)
    else:
        # Fallback: append at end of file
        routes += new_route
    with open(W + "/routes.py", "w") as f:
        f.write(routes)
    print("Route /media-unified added to routes.py")
