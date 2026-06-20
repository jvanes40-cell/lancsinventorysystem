from waitress import serve
from inventory_system.wsgi import application

if __name__ == '__main__':
    print("==========================================")
    print("  LANCS WMS is running!")
    print("  Access it at: http://YOUR-IP:8000")
    print("  Press Ctrl+C to stop")
    print("==========================================")
    serve(application, host='0.0.0.0', port=8000)