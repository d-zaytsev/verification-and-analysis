# A continue in the inner loop's else advances the outer loop.
for i in [1, 2]:
    for j in range(i):
        if j == 1:
            break
    else:
        continue
    print("after inner")

print("done")
