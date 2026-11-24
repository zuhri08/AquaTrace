from dataclasses import dataclass


class TreeNode:
    """Node pohon umum; daftar children menyimpan referensi node anak."""

    def __init__(self, value):
        """Buat node tanpa anak. Kompleksitas waktu dan ruang O(1)."""
        self.value = value
        self.children = []


class Tree:
    """Pohon umum untuk decision tree dan hierarki wilayah."""

    def __init__(self, root_value):
        """Buat pohon dengan root. Kompleksitas waktu dan ruang O(1)."""
        self.root = root_value if isinstance(root_value, TreeNode) else TreeNode(root_value)

    def add_node(self, parent_value, value):
        """Tambahkan anak ke parent pertama yang cocok. Kompleksitas waktu O(n)."""
        parent = self.find(parent_value)
        if parent is None:
            raise ValueError(f"parent tidak ditemukan: {parent_value!r}")
        node = TreeNode(value)
        parent.children.append(node)
        return node

    def find(self, value):
        """Cari nilai secara pre-order rekursif. Kompleksitas waktu O(n)."""

        def visit(node):
            """Kunjungi tiap node sekali. Kompleksitas waktu O(n)."""
            if node.value == value:
                return node
            for child in node.children:
                found = visit(child)
                if found is not None:
                    return found
            return None

        return visit(self.root)

    def pre_order(self):
        """Urutan root-anak secara rekursif. Kompleksitas waktu O(n)."""
        result = []

        def visit(node):
            """Tambahkan nilai pre-order. Kompleksitas waktu O(n)."""
            result.append(node.value)
            for child in node.children:
                visit(child)

        visit(self.root)
        return result

    def level_order(self):
        """Urutan per level dengan cursor, tanpa operasi hapus depan. O(n)."""
        result = []
        frontier = [self.root]
        cursor = 0
        while cursor < len(frontier):
            node = frontier[cursor]
            cursor += 1
            result.append(node.value)
            frontier.extend(node.children)
        return result

    def height(self):
        """Hitung jumlah level secara rekursif. Kompleksitas waktu O(n)."""

        def height_of(node):
            """Hitung level subtree. Kompleksitas waktu O(n)."""
            if not node.children:
                return 1
            return 1 + max(height_of(child) for child in node.children)

        return height_of(self.root)

    def hitung_tercemar(self, is_contaminated):
        """Hitung node tercemar rekursif. Kompleksitas waktu O(n)."""
        return hitung_tercemar(self.root, is_contaminated)


def hitung_tercemar(node, is_contaminated):
    """Jumlahkan node tercemar di subtree secara rekursif, O(n)."""
    count = int(is_contaminated(node.value))
    for child in node.children:
        count += hitung_tercemar(child, is_contaminated)
    return count


@dataclass
class DecisionNode:
    """Simpul kondisi biner atau daun vonis pada pohon keputusan."""

    feature: str = None
    operator: str = None
    threshold: float = None
    when_true: object = None
    when_false: object = None
    verdict: str = None
    message: str = None

    def __post_init__(self):
        """Validasi simpul kondisi. Kompleksitas waktu dan ruang O(1)."""
        if self.verdict is None:
            if not self.feature or self.operator not in {"<", "<=", ">", ">=", "=="}:
                raise ValueError("simpul kondisi memerlukan feature dan operator valid")
            if self.threshold is None:
                raise ValueError("simpul kondisi memerlukan threshold")
            if self.when_true is None or self.when_false is None:
                raise ValueError("simpul kondisi memerlukan dua cabang")


class DecisionTree:
    """Pembungkus pohon keputusan yang dievaluasi rekursif."""

    def __init__(self, root):
        self.root = root

    def evaluate(self, data):
        """Evaluasi root dan kembalikan vonis beserta jejak. Kompleksitas O(h)."""
        return evaluate(self.root, data)


def evaluate(node, data):
    """Evaluasi satu simpul rekursif dan hasilkan (vonis, jejak), O(h)."""
    if node.verdict is not None:
        return node.verdict, [node.message or f"Vonis: {node.verdict}"]

    if node.feature not in data:
        raise KeyError(f"nilai pengukuran tidak tersedia: {node.feature}")

    value = data[node.feature]
    operations = {
        "<": value < node.threshold,
        "<=": value <= node.threshold,
        ">": value > node.threshold,
        ">=": value >= node.threshold,
        "==": value == node.threshold,
    }
    passed = operations[node.operator]
    branch = node.when_true if passed else node.when_false
    result, trace = evaluate(branch, data)
    comparison = f"{node.feature} {value} {node.operator} {node.threshold}"
    outcome = "terpenuhi" if passed else "tidak terpenuhi"
    return result, [f"{comparison} ({outcome})"] + trace
