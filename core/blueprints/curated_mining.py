from flask import Blueprint, render_template
curated_mining_bp = Blueprint('curated_mining', __name__)

@curated_mining_bp.route('/curated-mining')
def curated_mining():
    return render_template('curated_mining.html')
