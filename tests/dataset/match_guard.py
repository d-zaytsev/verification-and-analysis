point = (1, 2)
label = "-"

match point:
    case (0, 0):
        label = "origin"
    case (x, y) if x == y:
        label = "diagonal"
    case (x, _) as p if x > 0:
        label = "right"
    case _ if point:
        label = "other"

print(label)
