from app import app, socketio

if __name__ == "__main__":
    if socketio is not None:
        socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
