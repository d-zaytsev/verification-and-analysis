command = "stop"

match command:
    case "start":
        print("starting")
    case "stop":
        print("stopping")
    case _:
        print("unknown")

print("end")
