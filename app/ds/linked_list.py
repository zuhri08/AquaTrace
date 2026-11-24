class Node:
    """Node untuk singly linked list."""

    __slots__ = ("value", "next")

    def __init__(self, value):
        """Buat node baru. Kompleksitas waktu dan ruang O(1)."""
        self.value = value
        self.next = None


class LinkedList:
    """Singly linked list dengan pointer HEAD dan TAIL."""

    def __init__(self, id_getter=None):
        """Buat list kosong. Kompleksitas waktu dan ruang O(1)."""
        self.head = None
        self.tail = None
        self._length = 0
        self._id_getter = id_getter or self._default_id

    @staticmethod
    def _default_id(value):
        """Ambil id dari mapping/objek, atau gunakan nilai. Kompleksitas O(1)."""
        if isinstance(value, dict) and "id" in value:
            return value["id"]
        return getattr(value, "id", value)

    def insert_head(self, value):
        """Masukkan nilai di HEAD. Kompleksitas waktu O(1)."""
        node = Node(value)
        if self.head is None:
            self.head = self.tail = node
        else:
            node.next = self.head
            self.head = node
        self._length += 1

    def insert_tail(self, value):
        """Masukkan nilai di TAIL. Kompleksitas waktu O(1)."""
        node = Node(value)
        if self.tail is None:
            self.head = self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self._length += 1

    def search(self, item_id):
        """Cari dan kembalikan nilai berdasarkan id. Kompleksitas waktu O(n)."""
        current = self.head
        while current is not None:
            if self._id_getter(current.value) == item_id:
                return current.value
            current = current.next
        return None

    def delete(self, item_id):
        """Hapus id pertama yang cocok, atau None. Kompleksitas waktu O(n)."""
        previous = None
        current = self.head
        while current is not None:
            if self._id_getter(current.value) == item_id:
                if previous is None:
                    self.head = current.next
                else:
                    previous.next = current.next
                if self.tail is current:
                    self.tail = previous
                self._length -= 1
                if self.head is None:
                    self.tail = None
                return current.value
            previous, current = current, current.next
        return None

    def traverse(self):
        """Salin nilai berurutan dari HEAD. Kompleksitas waktu dan ruang O(n)."""
        result = []
        current = self.head
        while current is not None:
            result.append(current.value)
            current = current.next
        return result

    def length(self):
        """Kembalikan jumlah elemen. Kompleksitas waktu O(1)."""
        return self._length

    def is_empty(self):
        """Periksa apakah list kosong. Kompleksitas waktu O(1)."""
        return self.head is None

    def remove_head(self):
        """Hapus HEAD, atau None bila kosong. Kompleksitas waktu O(1)."""
        if self.head is None:
            return None
        value = self.head.value
        self.head = self.head.next
        self._length -= 1
        if self.head is None:
            self.tail = None
        return value
