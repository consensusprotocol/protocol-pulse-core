Read PIPELINE_LAWS.md briefly.

TASK: Remove duplicate product grid from merch.html

The merch page shows all 5 products twice. There are two separate
{% for product in products %} HTML loops in the template.

1. Run: grep -n "for product in products\|products-grid\|product-card" ~/protocol_pulse/templates/merch.html
2. Find the SECOND products-grid div with its for loop (not the JS one inside <script> tags)
3. Delete the entire second HTML products-grid section (from its opening section/div tag to closing tag)
4. Verify only ONE {% for product in products %} loop remains outside of <script> tags
5. Test: curl -s http://localhost:5000/merch | grep -c "product-card" should return 5 not 10
6. kill -1 $(pgrep -f "gunicorn.*5000" | grep -v golds | grep -v relay | head -1)
7. git add templates/merch.html && git commit -m "fix(merch): remove duplicate product grid" && git push
