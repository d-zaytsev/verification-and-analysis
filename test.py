a = [0] * 100
i = 0

while True:
    i += 1
    if i > len(a):
        print("break!")
        break
    if i % 2 == 0:
        a[i] *= 2
    else:
        a[i] += 2
else:
    print("while else block!")
    
print("end of program!")

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