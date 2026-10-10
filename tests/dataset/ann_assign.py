# Annotated assignments are ordinary sequential statements.
x: int = 0
y: list[int]
if x:
    y = [x]
else:
    y: list[int] = []
print(y)
