import math

from app.ds.queue import Queue


class MinHeap:
    """Min-heap array manual dengan tie-break sequence untuk nilai sebanding."""

    def __init__(self):
        """Buat heap kosong. Kompleksitas waktu dan ruang O(1)."""
        self._items = []
        self._sequence = 0

    def push(self, priority, value):
        """Masukkan pasangan prioritas. Kompleksitas waktu O(log n)."""
        entry = (priority, self._sequence, value)
        self._sequence += 1
        self._items.append(entry)
        self._sift_up(len(self._items) - 1)

    def pop(self):
        """Ambil pasangan berprioritas minimum. Kompleksitas waktu O(log n)."""
        if not self._items:
            raise IndexError("pop dari MinHeap kosong")
        minimum = self._items[0]
        last = self._items.pop()
        if self._items:
            self._items[0] = last
            self._sift_down(0)
        return minimum[0], minimum[2]

    def is_empty(self):
        """Periksa apakah heap kosong. Kompleksitas waktu O(1)."""
        return not self._items

    def size(self):
        """Kembalikan jumlah elemen. Kompleksitas waktu O(1)."""
        return len(self._items)

    def _sift_up(self, index):
        """Pulihkan heap ke arah root. Kompleksitas waktu O(log n)."""
        while index > 0:
            parent = (index - 1) // 2
            if self._items[parent][:2] <= self._items[index][:2]:
                break
            self._items[parent], self._items[index] = (
                self._items[index],
                self._items[parent],
            )
            index = parent

    def _sift_down(self, index):
        """Pulihkan heap ke arah daun. Kompleksitas waktu O(log n)."""
        size = len(self._items)
        while True:
            left = index * 2 + 1
            right = left + 1
            smallest = index
            if left < size and self._items[left][:2] < self._items[smallest][:2]:
                smallest = left
            if right < size and self._items[right][:2] < self._items[smallest][:2]:
                smallest = right
            if smallest == index:
                return
            self._items[index], self._items[smallest] = (
                self._items[smallest],
                self._items[index],
            )
            index = smallest


class Graph:
    """Graph berarah berbobot dengan adjacency list buatan sendiri."""

    def __init__(self):
        """Buat adjacency list kosong. Kompleksitas waktu dan ruang O(1)."""
        self._adjacency = {}

    def add_node(self, node):
        """Tambahkan node jika belum ada. Kompleksitas waktu O(1)."""
        self._adjacency.setdefault(node, [])

    def add_edge(self, source, target, weight):
        """Tambahkan edge unik berbobot positif. Kompleksitas waktu O(deg(source))."""
        if source == target:
            raise ValueError("edge ke diri sendiri tidak diizinkan")
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or weight <= 0
        ):
            raise ValueError("bobot edge harus lebih besar dari nol")
        self.add_node(source)
        self.add_node(target)
        if any(neighbor == target for neighbor, _ in self._adjacency[source]):
            raise ValueError(f"edge {source!r} -> {target!r} sudah ada")
        self._adjacency[source].append((target, weight))

    def remove_edge(self, source, target):
        """Hapus edge terarah; hasil True bila ditemukan. Kompleksitas O(deg(source))."""
        if source not in self._adjacency:
            return False
        edges = self._adjacency[source]
        for index, (neighbor, _) in enumerate(edges):
            if neighbor == target:
                del edges[index]
                return True
        return False

    def neighbors(self, node):
        """Salin tetangga berbobot. Kompleksitas waktu dan ruang O(deg(node))."""
        return list(self._adjacency.get(node, ()))

    def nodes(self):
        """Salin seluruh node graph. Kompleksitas waktu dan ruang O(V)."""
        return list(self._adjacency)

    def bfs(self, start):
        """Jelajahi graph breadth-first dengan Queue manual. Kompleksitas O(V+E)."""
        if start not in self._adjacency:
            return []
        visited = {start}
        result = []
        frontier = Queue()
        frontier.enqueue(start)
        while not frontier.is_empty():
            node = frontier.dequeue()
            result.append(node)
            for neighbor, _ in self._adjacency[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    frontier.enqueue(neighbor)
        return result

    def dfs(self, start):
        """Jelajahi graph depth-first secara rekursif. Kompleksitas O(V+E)."""
        if start not in self._adjacency:
            return []
        visited = set()
        result = []

        def visit(node):
            visited.add(node)
            result.append(node)
            for neighbor, _ in self._adjacency[node]:
                if neighbor not in visited:
                    visit(neighbor)

        visit(start)
        return result

    def dijkstra(self, start):
        """Hitung jarak dan predecessor dengan MinHeap manual; O((V+E)log V)."""
        if start not in self._adjacency:
            return {}, {}
        distances = {node: float("inf") for node in self._adjacency}
        previous = {node: None for node in self._adjacency}
        distances[start] = 0
        frontier = MinHeap()
        frontier.push(0, start)

        while not frontier.is_empty():
            distance, node = frontier.pop()
            if distance != distances[node]:
                continue
            for neighbor, weight in self._adjacency[node]:
                candidate = distance + weight
                if candidate < distances[neighbor]:
                    distances[neighbor] = candidate
                    previous[neighbor] = node
                    frontier.push(candidate, neighbor)
        return distances, previous

    def shortest_path(self, start, target):
        """Kembalikan (rute, jarak), atau None jika tanpa jalur. Kompleksitas Dijkstra."""
        distances, previous = self.dijkstra(start)
        if target not in distances or distances[target] == float("inf"):
            return None
        route = []
        current = target
        while current is not None:
            route.append(current)
            current = previous[current]
        route.reverse()
        return route, distances[target]
