import os, logging, requests
logger = logging.getLogger(__name__)
_CACHE = {}
DEFAULT = "/static/images/default-header.png"
QUERIES = {
    "mining": ["bitcoin mining facility","data center servers gpu","cryptocurrency mining rig","server farm technology"],
    "hashrate": ["data center server rack","computing infrastructure","network hardware technology"],
    "etf": ["wall street stock market","financial trading floor","investment finance charts"],
    "halving": ["bitcoin gold digital","cryptocurrency scarcity","bitcoin blockchain network"],
    "regulation": ["government law financial","capitol building regulation","financial compliance law"],
    "defi": ["decentralized blockchain finance","smart contract technology"],
    "stablecoin": ["digital currency finance","cryptocurrency payment"],
    "gamestop": ["stock market retail trading","financial markets volatility"],
    "ripple": ["cross border payment technology","financial network digital"],
    "ethereum": ["blockchain smart contract","ethereum network technology"],
    "bear": ["bear market financial decline","stock market falling chart"],
    "bull": ["bull market financial growth","cryptocurrency price rising"],
    "macro": ["global economy finance","macro economic trends"],
    "prediction": ["financial prediction market","data analytics forecast"],
    "default": ["bitcoin cryptocurrency dark","blockchain technology network","digital currency abstract","crypto finance technology","bitcoin protocol network","cryptocurrency market data"],
}
def _pick(title, category, aid=0):
    t = f"{title} {category}".lower()
    for kw, opts in QUERIES.items():
        if kw in t:
            return opts[aid % len(opts)]
    opts = QUERIES["default"]
    return opts[aid % len(opts)]
def get_pexels_image(title, category="bitcoin", article_id=0):
    api_key = os.environ.get("PEXELS_API_KEY","").strip()
    if not api_key:
        return DEFAULT
    q = _pick(title, category, article_id)
    page = (article_id % 4) + 1
    ck = f"{q}|{page}"
    if ck in _CACHE:
        return _CACHE[ck]
    try:
        r = requests.get("https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": q, "per_page": 5, "page": page, "orientation": "landscape"},
            timeout=8)
        r.raise_for_status()
        photos = r.json().get("photos",[])
        if photos:
            url = photos[article_id % len(photos)]["src"]["large2x"]
            _CACHE[ck] = url
            return url
    except Exception as e:
        logger.error(f"Pexels: {e}")
    _CACHE[ck] = DEFAULT
    return DEFAULT
