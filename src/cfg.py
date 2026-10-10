import ast
from collections import deque
from types import EllipsisType

import pygraphviz as pgv


class BasicBlock:
    """A sequential block of code with no branches.
    If you execute the first instruction of this block,
    you are guaranteed to reach the last one."""

    _stmts: list[ast.stmt]
    """List of block sequential statements."""
    _edges: dict[ast.match_case | ast.stmt | None, "BasicBlock"]
    """Dict of edges that transfer control from one block to another
       ("the program may take that path")."""

    def __init__(self, stmts: ast.stmt | list[ast.stmt] | None = None) -> None:
        self._stmts = (
            stmts if isinstance(stmts, list) else [stmts] if stmts is not None else []
        )
        self._edges = {}

    @property
    def stmts(self) -> list[ast.stmt]:
        return self._stmts.copy()

    @property
    def edges(self) -> dict[ast.match_case | ast.stmt | None, "BasicBlock"]:
        return self._edges.copy()

    @property
    def is_decision_block(self) -> bool:
        return (
            len(self._stmts) == 1
            and isinstance(self._stmts[0], ast.Expr)
            and any(isinstance(k, ast.stmt) for k in self.edges)
        )

    @property
    def is_end_block(self) -> bool:
        return len(self._edges) == 0

    @property
    def is_empty_block(self) -> bool:
        return len(self._stmts) == 0

    def append_stmt(self, stmt: ast.stmt) -> "BasicBlock":
        self._stmts.append(stmt)
        return self

    def extend_stmts(self, block: "BasicBlock") -> None:
        self._stmts.extend(block.stmts)

    def add_edge_to(
        self, block: "BasicBlock", const: ast.match_case | ast.stmt | None = None
    ) -> None:
        if const in self._edges:
            raise ValueError(f"Edge with const {const!r} already exist in {self!s}")
        self._edges[const] = block

    def remove_edge(self, const: ast.match_case | ast.stmt | None) -> None:
        if const in self._edges:
            del self._edges[const]

    @property
    def name(self) -> str:
        return f"B{id(self):x}"

    def __str__(self) -> str:
        stmts = "; ".join(ast.unparse(s) for s in self._stmts)
        edges = ", ".join(
            f"{'always' if cond is None else ast.unparse(cond)} -> {target.name}"
            for cond, target in self._edges.items()
        )
        return f"{self.name}([{stmts}], edges={{{edges}}})"


class CFG:
    def __init__(self, root: BasicBlock) -> None:
        self._root = root

    @classmethod
    def from_ast(cls, body: list[ast.stmt]) -> "CFG":
        root = BasicBlock()
        CFGBuilder().stmts_helper(body, root)
        res = cls(root)
        res._clean()
        return res

    def _clean(self) -> None:
        visited: set[BasicBlock] = set()
        # Skip empty root
        while self._root.is_empty_block and None in self._root.edges:
            self._root = self._root.edges[None]

        stack: list[BasicBlock] = [self._root]

        while stack:
            block = stack.pop()
            if block in visited:
                continue
            visited.add(block)

            for key, child_block in block.edges.items():
                target: BasicBlock | None = child_block
                while target is not None and (
                    target.is_empty_block and not target.is_end_block
                ):
                    target = target.edges.get(None)
                block.remove_edge(key)
                if target is not None:
                    block.add_edge_to(target, key)
                    stack.append(target)

    def __str__(self) -> str:
        ids: dict[int, int] = {}
        order: list[BasicBlock] = []
        queue = deque([self._root])
        while queue:
            block = queue.popleft()
            if id(block) in ids:
                continue
            ids[id(block)] = len(order)
            order.append(block)
            queue.extend(block.edges.values())

        lines: list[str] = []
        for block in order:
            block_statuses = []  # "final"/"start"/empty
            if block.is_end_block:
                block_statuses.append("F")
            if block is order[0]:
                block_statuses.append("S")
            lines.append(f"B{ids[id(block)]}{','.join(block_statuses)}:")
            for stmt in block.stmts:
                lines.extend("    " + line for line in ast.unparse(stmt).splitlines())
            for cond, target in block.edges.items():
                label = "always" if cond is None else ast.unparse(cond)
                lines.append(f"    → B{ids[id(target)]} [{label}]")
        return "\n".join(lines)

    def to_dot(self) -> pgv.AGraph:
        G = pgv.AGraph(strict=False, directed=True)
        ppnames: dict[BasicBlock, str] = {}
        order: list[BasicBlock] = []
        queue = deque([self._root])

        while queue:
            block = queue.popleft()
            if block in ppnames:
                continue

            node_name = f"B{len(order)}"
            ppnames[block] = node_name
            order.append(block)
            queue.extend(block.edges.values())

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

            for cond, target in block.edges.items():
                edge_label = (
                    "" if cond is None else ast.unparse(cond).replace("\\", "\\\\")
                )
                G.add_edge(ppnames[block], ppnames[target], label=edge_label)
        return G


def _const(value: str | bytes | bool | complex | None | EllipsisType) -> ast.stmt:
    return ast.Expr(ast.Constant(value))


def _is_irrefutable(pattern: ast.pattern) -> bool:
    if isinstance(pattern, ast.MatchAs):
        return pattern.pattern is None or _is_irrefutable(pattern.pattern)
    if isinstance(pattern, ast.MatchOr):
        return any(_is_irrefutable(p) for p in pattern.patterns)
    return False


TRUE_STMT = _const(True)
FALSE_STMT = _const(False)


class CFGBuilder:
    _ctx_break: list[BasicBlock]
    _ctx_continue: list[BasicBlock]

    def __init__(self) -> None:
        self._ctx_break = []
        self._ctx_continue = []

    def stmts_helper(
        self,
        stmts: list[ast.stmt],
        _cur: BasicBlock,
    ) -> BasicBlock:
        cur = _cur
        for stmt in stmts:
            cur = self.stmt_helper(stmt, cur)

            if cur in self._ctx_break or cur in self._ctx_continue:
                break

        return cur  # last processed stmt

    def stmt_helper(
        self,
        stmt: ast.stmt,
        _cur: BasicBlock,
    ) -> BasicBlock:
        cur_ctx_break = len(self._ctx_break)
        cur_ctx_continue = len(self._ctx_continue)

        match stmt:
            case ast.Pass():
                return _cur
            case ast.If():
                if_cond_block = BasicBlock(ast.Expr(stmt.test))
                _cur.add_edge_to(if_cond_block)
                if_join_block = BasicBlock()

                if_then_block = BasicBlock()
                if_cond_block.add_edge_to(if_then_block, TRUE_STMT)
                self.stmts_helper(stmt.body, if_then_block).add_edge_to(if_join_block)

                if len(stmt.orelse) > 0:
                    if_else_block = BasicBlock()
                    if_cond_block.add_edge_to(if_else_block, FALSE_STMT)
                    self.stmts_helper(stmt.orelse, if_else_block).add_edge_to(
                        if_join_block
                    )
                else:
                    if_cond_block.add_edge_to(if_join_block, FALSE_STMT)

                return if_join_block
            case ast.While():  # While(expr test, stmt* body, stmt* orelse)
                while_cond = ast.copy_location(ast.While(stmt.test, [], []), stmt)
                while_cond_block = BasicBlock(while_cond)
                _cur.add_edge_to(while_cond_block)
                while_join_block = BasicBlock()

                while_body_block = BasicBlock()
                while_cond_block.add_edge_to(while_body_block, TRUE_STMT)
                self.stmts_helper(stmt.body, while_body_block).add_edge_to(
                    while_cond_block
                )

                while len(self._ctx_break) > cur_ctx_break:
                    while_break_block = self._ctx_break.pop(-1)
                    while_break_block.remove_edge(None)
                    while_break_block.add_edge_to(while_join_block)
                while len(self._ctx_continue) > cur_ctx_continue:
                    while_continue_block = self._ctx_continue.pop(-1)
                    while_continue_block.remove_edge(None)
                    while_continue_block.add_edge_to(while_cond_block)

                if stmt.orelse:
                    while_else_block = BasicBlock()
                    while_cond_block.add_edge_to(while_else_block, FALSE_STMT)
                    self.stmts_helper(stmt.orelse, while_else_block).add_edge_to(
                        while_join_block
                    )
                else:
                    while_cond_block.add_edge_to(while_join_block, FALSE_STMT)

                return while_join_block
            case ast.Break():
                _cur.append_stmt(stmt)
                self._ctx_break.append(_cur)
                return _cur
            case ast.Continue():
                _cur.append_stmt(stmt)
                self._ctx_continue.append(_cur)
                return _cur
            case ast.For():  # For(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
                for_main_block = BasicBlock(
                    ast.copy_location(ast.For(stmt.target, stmt.iter, [], []), stmt)
                )
                _cur.add_edge_to(for_main_block)
                for_join_block = BasicBlock()

                for_body_block = BasicBlock()
                for_main_block.add_edge_to(for_body_block, ast.Expr(stmt.iter))
                self.stmts_helper(stmt.body, for_body_block).add_edge_to(for_main_block)

                while len(self._ctx_break) > cur_ctx_break:
                    for_break_block = self._ctx_break.pop(-1)
                    for_break_block.remove_edge(None)
                    for_break_block.add_edge_to(for_join_block)
                while len(self._ctx_continue) > cur_ctx_continue:
                    for_continue_block = self._ctx_continue.pop(-1)
                    for_continue_block.remove_edge(None)
                    for_continue_block.add_edge_to(for_main_block)
                if stmt.orelse:
                    for_else_block = BasicBlock()
                    for_main_block.add_edge_to(for_else_block, FALSE_STMT)
                    self.stmts_helper(stmt.orelse, for_else_block).add_edge_to(
                        for_join_block
                    )
                else:
                    for_main_block.add_edge_to(for_join_block, FALSE_STMT)

                return for_join_block
            case ast.Match():  # Match(expr subject, match_case* cases)
                match_main_block = BasicBlock(
                    ast.copy_location(ast.Match(stmt.subject, []), stmt)
                )
                _cur.add_edge_to(match_main_block)
                match_join_block = BasicBlock()

                for case in stmt.cases:
                    match_case_body_block = BasicBlock()
                    self.stmts_helper(case.body, match_case_body_block).add_edge_to(
                        match_join_block
                    )
                    case_label = ast.copy_location(
                        ast.match_case(case.pattern, case.guard, []), case
                    )
                    match_main_block.add_edge_to(match_case_body_block, case_label)

                is_exhaustive = any(case.guard is None and _is_irrefutable(case.pattern) for case in stmt.cases)
                if not is_exhaustive:
                    default_label = ast.copy_location(
                        ast.match_case(ast.MatchAs(), None, []), stmt
                    )
                    match_main_block.add_edge_to(match_join_block, default_label)

                return match_join_block
            case _:
                return _cur.append_stmt(stmt)
        raise ValueError("???")
