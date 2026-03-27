TASK: Fix missing book cover images in recommended reading section

Books in the media/sovereign library section are missing cover images.
Amazon PA API is supposedly integrated. Fix:

1. Find the books data source:
   grep -rn "amazon\|book.*image\|cover_image\|amazon_url" ~/protocol_pulse/core/routes.py | grep -v "#" | head -10
   grep -n "all_books\|books_data\|recommended" ~/protocol_pulse/core/routes.py | head -10

2. Find the Amazon PA API integration:
   find ~/protocol_pulse -name "*.py" | xargs grep -l "amazon\|PAAPI\|ProductAdvertising" 2>/dev/null | head -5

3. Check what image fields are available for books in the DB or static data:
   grep -n "cover_image\|book_image\|thumbnail\|amazon_image" ~/protocol_pulse/templates/media_hub.html | head -10

4. For each book without an image:
   - If Amazon ASIN is available, call Amazon PA API: GET /paapi5/getitems with ASIN
   - Extract Images.Primary.Large.URL
   - Store in DB or static config
   - Fallback: use Open Library API (free, no key): https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg

5. Update the books template to use: {{ book.cover_image or book.amazon_image or '/static/images/book-placeholder.svg' }}

6. git add -A && git commit -m "fix(media): book cover images via Amazon PA API + Open Library fallback" && git push
