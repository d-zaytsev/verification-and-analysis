code = 404
status = "-"

match code:
    case 200:
        status = "ok"
    case 201:
        status = "created"
    case 404 | 410:
        status = "not found"
    case 301:
        status = "Moved Permanently"
    case 400:
        status = "Bad Request"
    case 401:
        status = "Unauthorized"
    case 403:
        status = "Forbidden"
        

print(status)
