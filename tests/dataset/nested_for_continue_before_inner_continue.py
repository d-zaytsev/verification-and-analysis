# The outer `continue` is still pending when the inner loop resolves its own
# `continue`: each must jump to the header of its own loop.
for i in range(3):
    if i == 0:
        continue
    for j in range(3):
        if j == 1:
            continue
        print(i, j)

print("end")
