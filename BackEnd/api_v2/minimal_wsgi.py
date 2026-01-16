def app(environ, start_response):
    """
    A minimal WSGI application to test IIS/FastCGI integration.
    No external dependencies (database, flask, etc.) are imported.
    """
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    start_response(status, headers)
    return [b'Hello from minimal Python on IIS!']
