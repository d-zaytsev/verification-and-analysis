i = 0

while i < 5:
    i += 1
    if i % 2 == 0:
        continue
    for j in range(i):
        print(i, j)
    print(i)

print("end")
