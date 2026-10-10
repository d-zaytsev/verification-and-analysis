x = 7
flag = False

match x:
    case 1 | _ if flag:
        print("matched")

print("end")
