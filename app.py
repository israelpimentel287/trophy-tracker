from app import create_app
import logging
from flask import request

app = create_app()

@app.before_request
def log_request_info():
    print(f"{request.remote_addr} - - {request.method} {request.path}")

if __name__ == '__main__':
    print("Server started on http://127.0.0.1:5000")

    logging.getLogger('werkzeug').setLevel(logging.INFO)
    logging.getLogger('gevent.access').setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)