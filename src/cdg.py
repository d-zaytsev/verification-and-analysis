import ast
from collections import deque
from typing import cast

import pygraphviz as pgv

from cfg import CFG, FALSE_STMT, TRUE_STMT, BasicBlock


class ACFG:
    exit_node: BasicBlock
    start_node: BasicBlock
    nodes: list[BasicBlock]

    def __init__(self, cfg: CFG) -> None:
        self.start_node = cfg.root
        self.nodes = []

        self._prepare()

    def _prepare(self) -> None:
        # Add single exit node
        q: list[BasicBlock] = [self.start_node]
        end_nodes: list[BasicBlock] = []

        while q:
            node = q.pop(-1)

            if node in self.nodes:
                continue

            self.nodes.append(node)

            if node.is_end_block:
                end_nodes.append(node)
                continue
            q.extend(list(node.edges.values()))

        if len(end_nodes) < 1:
            raise ValueError("Illegal CFG")

        # New single exit node
        self.exit_node = BasicBlock()
        for n in end_nodes:
            n.add_edge_to(self.exit_node)

        # Augment CFG
        start_node = BasicBlock()
        start_node.add_edge_to(self.start_node, TRUE_STMT)  # T (start, entry)
        start_node.add_edge_to(self.exit_node, FALSE_STMT)  # F (start, exit)

        # Change root
        self.start_node = start_node
        self.nodes.append(self.exit_node)
        self.nodes.append(start_node)


class PDTree:
    _start_node: BasicBlock

    def __init__(self, cfg: ACFG) -> None:
        self._cfg = cfg
        self._pds: dict[BasicBlock, set[BasicBlock]] = {}  # postdominators
        self._children: dict[BasicBlock, list[BasicBlock]] = {}
        self._parent: dict[BasicBlock, BasicBlock | None] = {}

        self._compute_post_dom()
        self._build_pd_tree()

    @property
    def root(self) -> BasicBlock:
        return self._start_node

    def get_children(self, block: BasicBlock) -> list[BasicBlock]:
        return self._children[block].copy()

    def find_lca(self, a: BasicBlock, b: BasicBlock) -> BasicBlock:
        if a is b:
            return a

        a_visited: set[BasicBlock] = {a}
        b_visited: set[BasicBlock] = {b}

        a_cur, b_cur = a, b
        while (a_cur is not self._start_node) or (b_cur is not self._start_node):
            if self._parent.get(a_cur) is not None:
                a_cur = cast(BasicBlock, self._parent[a_cur])
            if self._parent.get(b_cur) is not None:
                b_cur = cast(BasicBlock, self._parent[b_cur])

            a_visited.add(a_cur)
            b_visited.add(b_cur)

            if a_cur in b_visited:
                return a_cur
            if b_cur in a_visited:
                return b_cur
        raise ValueError

    def traverse_backward(self, a: BasicBlock, b: BasicBlock) -> list[BasicBlock]:
        if a is b:
            return [a]

        path = [a]
        cur = a

        while cur is not self._start_node:
            parent = self._parent[cur]

            if not parent:
                break

            if parent is b:
                return path

            path.append(parent)
            cur = parent
        raise ValueError

    def _compute_post_dom(self) -> None:
        self._pds = {n: set(self._cfg.nodes) for n in self._cfg.nodes}
        self._pds[self._cfg.exit_node] = {self._cfg.exit_node}

        changed = True
        while changed:
            changed = False

            for n in self._cfg.nodes:
                if n is self._cfg.exit_node:
                    continue
                new_pds: set[BasicBlock] = {
                    n,
                    *set.intersection(*(self._pds[p] for p in n.edges.values())),
                }

                if new_pds != self._pds[n]:
                    changed = True
                    self._pds[n] = new_pds

    def _build_pd_tree(self) -> None:
        self._children = {n: [] for n in self._pds}
        pds = {n: v - {n} for n, v in self._pds.items()}
        self._start_node = self._cfg.exit_node
        self._parent = {self._start_node: None}
        queue: list[BasicBlock] = [self._start_node]

        while queue:
            m = queue.pop(-1)

            for n, rest in pds.items():
                if m not in rest:
                    continue

                rest.remove(m)
                if not rest:
                    queue.append(n)
                    self._children[m].append(n)
                    self._parent[n] = m

    def __str__(self) -> str:
        ids: dict[str, int] = {}
        order: list[BasicBlock] = []
        queue = deque([self._start_node])

        while queue:
            block = queue.popleft()
            if block.name in ids:
                continue
            ids[block.name] = len(order)
            order.append(block)
            if block in self._children:
                queue.extend(self._children[block])

        lines: list[str] = []
        for block in order:
            lines.append(f"B{ids[block.name]}:")
            for stmt in block.stmts:
                lines.extend("    " + line for line in ast.unparse(stmt).splitlines())

            if block in self._children:
                for target in self._children[block]:
                    lines.append(f"    → B{ids[target.name]}")
        return "\n".join(lines)


class CDG:
    def __init__(
        self,
        start_node: BasicBlock,
        children: dict[
            BasicBlock, dict[ast.match_case | ast.stmt | None, list[BasicBlock]]
        ],
    ) -> None:
        self._start_node = start_node
        self._children = children

    @classmethod
    def from_ast(cls, body: list[ast.stmt]) -> "CDG":
        cfg = CFG.from_ast(body)
        acfg = ACFG(cfg)
        pdt = PDTree(acfg)

        s = [
            (a, b)
            for a in acfg.nodes
            for b in a.edges.values()
            # (a,b) in ACFG such that B is not ancestor of A in PDT
            if a not in pdt.get_children(b)
        ]

        children: dict[
            BasicBlock, dict[ast.match_case | ast.stmt | None, list[BasicBlock]]
        ] = {}

        for a, b in s:
            # L is a postdominator of A
            l = pdt.find_lca(a, b)

            visited: list[BasicBlock] = []

            # Traverse backwards from B to L
            visited.extend([n for n in pdt.traverse_backward(b, l) if n is not l])

            if l is a:
                # Add branching node itself
                visited.append(l)

            label = a.get_label_to(b)
            if a in children:
                if label not in children[a]:
                    children[a][label] = []
                children[a][label].extend(visited)
            else:
                children[a] = {label: visited}

        return cls(acfg.start_node, children)

    def __str__(self) -> str:
        ids: dict[str, int] = {}
        order: list[BasicBlock] = []
        queue = deque([self._start_node])

        while queue:
            block = queue.popleft()
            if block.name in ids:
                continue
            ids[block.name] = len(order)
            order.append(block)
            if block in self._children:
                for child_blocks in self._children[block].values():
                    queue.extend(child_blocks)

        lines: list[str] = []
        for block in order:
            lines.append(f"B{ids[block.name]}:")
            for stmt in block.stmts:
                lines.extend("    " + line for line in ast.unparse(stmt).splitlines())

            if block in self._children:
                for cond, targets in self._children[block].items():
                    for target in targets:
                        label = "always" if cond is None else ast.unparse(cond)
                        lines.append(f"    → B{ids[target.name]} [{label}]")
        return "\n".join(lines)

    def to_dot(self) -> pgv.AGraph:
        G = pgv.AGraph(strict=False, directed=True)
        ppnames: dict[BasicBlock, str] = {}
        order: list[BasicBlock] = []
        queue = deque([self._start_node])

        while queue:
            block = queue.popleft()
            if block in ppnames:
                continue

            node_name = f"B{len(order)}"
            ppnames[block] = node_name
            order.append(block)
            if block in self._children:
                for child_blocks in self._children[block].values():
                    queue.extend(child_blocks)

        for block in order:
            # "\l" ends a left-justified line in Graphviz labels
            node_label = "".join(
                line + "\\l"
                for stmt in block.stmts
                for line in ast.unparse(stmt).replace("\\", "\\\\").splitlines()
            )
            is_condition = any(cond is not None for cond in block.edges)
            G.add_node(
                ppnames[block],
                label=node_label,
                peripheries=2 if block.is_end_block else 1,
                shape="diamond" if is_condition else "box",
                style="filled" if is_condition else "",
                fillcolor="lightyellow" if is_condition else "",
            )

            if block not in self._children:
                continue
            
            for cond, targets in self._children[block].items():
                edge_label = (
                    "" if cond is None else ast.unparse(cond).replace("\\", "\\\\")
                )
                
                for i, target in enumerate(targets):
                    G.add_edge(ppnames[block], ppnames[target], label=f"({i})" + edge_label)
        return G
