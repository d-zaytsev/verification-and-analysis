# A break in the inner loop's else exits the outer loop.
for i in [1, 2]:
    for j in []:
        pass
    else:
        break
    print("after inner")

print("done")
