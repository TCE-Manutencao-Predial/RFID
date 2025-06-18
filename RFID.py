# RFID.py
from app import create_app
from werkzeug.middleware.proxy_fix import ProxyFix

app = create_app()

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1)

if __name__ == '__main__':
    # from waitress import serve
    # serve(app, listen='127.0.0.1:5074')
    app.run(debug=True, port=5074)