# The outer `break` is still pending when the inner loop resolves its own
# `break`: the outer one must leave the outer loop, the inner one only the inner.
i = 0
while i < 5:
    i += 1
    if i == 4:
        break
    j = 0
    while j < i:
        j += 1
        if j == 2:
            break
    print(i, j)

print("end")
