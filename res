digraph "clustertests/dataset/while_else_break.py" {
	graph [label="tests/dataset/while_else_break.py"]
	1 [label="do = True
"]
	2 [label="while do:
"]
	3 [label="print('делаем итерацию')
"]
	"3_calls" [label=print shape=box]
	3 -> "3_calls" [label=calls style=dashed]
	4 [label="print('вышли из цикла')
"]
	"4_calls" [label=print shape=box]
	4 -> "4_calls" [label=calls style=dashed]
	3 -> 4 [label=""]
	2 -> 3 [label=do]
	2 -> 4 [label="(not do)"]
	1 -> 2 [label=""]
}
