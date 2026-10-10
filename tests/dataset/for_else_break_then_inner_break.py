# Classic "break out of nested loops" idiom: `break` in the inner `for ... else`
# belongs to the outer loop, the next inner loop has its own `break`.
for i in range(3):
    for j in range(3):
        if j == i:
            break
    else:
        break
    for k in range(3):
        if k == 1:
            break
        print(i, k)

print("end")
