for i in range(10):
    if i % 2 == 0:
        continue
    if i > 7:
        break
    print(i)
else:
    print("no break")

print("end")
