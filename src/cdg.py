import ast
import itertools

from cfg import CFG, FALSE_STMT, TRUE_STMT, BasicBlock


class ACFG:
    exit_node: BasicBlock
    start_node: BasicBlock
    nodes: set[BasicBlock]

    def __init__(self, cfg: CFG) -> None:
        self.start_node = cfg.root
        self.nodes = set()

        self._prepare()

    def _prepare(self) -> None:
        # Add single exit node
        q: list[BasicBlock] = [self.start_node]
        end_nodes: set[BasicBlock] = set()

        while q:
            node = q.pop(-1)

            if node in self.nodes:
                continue

            self.nodes.add(node)

            if node.is_end_block:
                end_nodes.add(node)
                continue
            q.extend(list(node.edges.values()))

        if len(end_nodes) < 1:
            raise ValueError("Illegal CFG")
        elif len(end_nodes) == 1:
            self.exit_node = end_nodes.pop()
        else:
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
        self.nodes.add(self.exit_node)
        self.nodes.add(start_node)


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
        a_ancestors = set(self._path_to_root(a))
        for node in self._path_to_root(b):
            if node in a_ancestors:
                return node

        raise ValueError("Nodes are not in the same tree")

    def find_path(self, a: BasicBlock, b: BasicBlock) -> list[BasicBlock]:
        lca = self.find_lca(a, b)
        a_path = self._path_to_root(a)
        b_path = self._path_to_root(b)

        up = a_path[: a_path.index(lca) + 1]
        down = b_path[: b_path.index(lca)]
        return up + down[::-1]

    def _path_to_root(self, node: BasicBlock) -> list[BasicBlock]:
        path = [node]
        while (parent := self._parent[node]) is not None:
            path.append(parent)
            node = parent
        return path

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


class CDG:
    def __init__(
        self,
        root: BasicBlock,
        children: dict[
            BasicBlock, tuple[ast.match_case | ast.stmt | None, set[BasicBlock]]
        ],
    ) -> None:
        self._root = root
        self._children = children

    @classmethod
    def from_ast(cls, body: list[ast.stmt]) -> "CDG":
        cfg = CFG.from_ast(body)
        acfg = ACFG(cfg)
        pdt = PDTree(acfg)

        nodes = acfg.nodes
        s = {
            (a, b)
            for a, b in itertools.product(nodes, nodes)
            if a.has_edge_to(b) and a not in pdt.get_children(b)
        }

        children: dict[
            BasicBlock, tuple[ast.match_case | ast.stmt | None, set[BasicBlock]]
        ] = {}

        for a, b in s:
            l = pdt.find_lca(a, b)

            blocks: set[BasicBlock] = set()

            for n in pdt.find_path(b, l):
                if n is not l:
                    blocks.add(n)

            if l is a:
                blocks.add(l)

            label = None
            for k, a_child in a.edges.items():
                if a_child is b:
                    label = k
                    break

            children[a] = (label, blocks)

        return cls(acfg.start_node, children)
