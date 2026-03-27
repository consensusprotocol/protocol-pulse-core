TASK: Optimize Protocol Pulse site load speed

Current state: pages taking too long to load. Fix:

1. CHECK current response times:
   time curl -s -o /dev/null http://localhost:5000/
   time curl -s -o /dev/null http://localhost:5000/articles
   time curl -s -o /dev/null http://localhost:5000/merch

2. ADD Flask response caching for slow routes:
   Find core/app.py or core/routes.py - add flask_caching or simple cache dict
   Cache these routes for 60 seconds: /, /articles, /merch, /charts, /media
   Do NOT cache: /admin, /oracle-live, /stage, /api/* endpoints

3. ADD static file cache headers in app.py:
   app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year for static
   Or add Cache-Control headers to the gunicorn/nginx config

4. ADD gzip compression to Flask responses:
   pip install flask-compress --break-system-packages
   from flask_compress import Compress; Compress(app)

5. FIX slow Printful API call on /merch:
   The merch route calls Printful on every page load (slow!)
   Add a simple in-memory cache with 5-minute TTL:
   _product_cache = {'data': None, 'ts': 0}
   In merch_store(): if time.time() - _product_cache['ts'] < 300: use cache

6. CHECK if any route is doing N+1 DB queries - look for query inside a loop

7. Test after each change - target <200ms for main pages

8. git add -A && git commit -m "perf: add response caching, gzip, Printful cache" && git push
