def find(items, target):
    for i in items:
        if i == target:
            return True
    return False


print(find([1, 2, 3], 2))
