class Node:
    """Node tunggal untuk Stack."""

    __slots__ = ("value", "next")

    def __init__(self, value, next_node=None):
        """Buat node baru. Kompleksitas waktu dan ruang O(1)."""
        self.value = value
        self.next = next_node


class Stack:
    """Stack LIFO berbasis node dengan operasi ujung atas O(1)."""

    def __init__(self):
        """Buat Stack kosong. Kompleksitas waktu dan ruang O(1)."""
        self._top = None
        self._size = 0

    def push(self, value):
        """Tambahkan nilai di TOP. Kompleksitas waktu O(1), ruang O(1)."""
        self._top = Node(value, self._top)
        self._size += 1

    def pop(self):
        """Ambil nilai TOP; kosong melempar IndexError. Kompleksitas waktu O(1)."""
        if self._top is None:
            raise IndexError("pop dari Stack kosong")
        value = self._top.value
        self._top = self._top.next
        self._size -= 1
        return value

    def peek(self):
        """Baca nilai TOP tanpa menghapusnya. Kompleksitas waktu O(1)."""
        if self._top is None:
            raise IndexError("peek pada Stack kosong")
        return self._top.value

    def is_empty(self):
        """Periksa apakah Stack kosong. Kompleksitas waktu O(1)."""
        return self._top is None

    def size(self):
        """Kembalikan jumlah elemen. Kompleksitas waktu O(1)."""
        return self._size

    def to_list(self):
        """Salin nilai dari TOP ke bawah. Kompleksitas waktu dan ruang O(n)."""
        result = []
        current = self._top
        while current is not None:
            result.append(current.value)
            current = current.next
        return result
