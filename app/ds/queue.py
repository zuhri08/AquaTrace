class Node:
    """Node tunggal untuk Queue."""

    __slots__ = ("value", "next")

    def __init__(self, value):
        """Buat node baru. Kompleksitas waktu dan ruang O(1)."""
        self.value = value
        self.next = None


class Queue:
    """Queue FIFO berantai dengan pointer HEAD dan TAIL."""

    def __init__(self):
        """Buat Queue kosong. Kompleksitas waktu dan ruang O(1)."""
        self._head = None
        self._tail = None
        self._size = 0

    def enqueue(self, value):
        """Tambahkan nilai di REAR. Kompleksitas waktu dan ruang O(1)."""
        node = Node(value)
        if self._tail is None:
            self._head = self._tail = node
        else:
            self._tail.next = node
            self._tail = node
        self._size += 1

    def dequeue(self):
        """Ambil nilai FRONT atau None bila kosong. Kompleksitas waktu O(1)."""
        if self._head is None:
            return None
        value = self._head.value
        self._head = self._head.next
        self._size -= 1
        if self._head is None:
            self._tail = None
        return value

    def peek(self):
        """Baca nilai FRONT atau None. Kompleksitas waktu O(1)."""
        return None if self._head is None else self._head.value

    def is_empty(self):
        """Periksa apakah Queue kosong. Kompleksitas waktu O(1)."""
        return self._head is None

    def size(self):
        """Kembalikan jumlah elemen. Kompleksitas waktu O(1)."""
        return self._size

    def to_list(self):
        """Salin elemen dari FRONT ke REAR. Kompleksitas waktu dan ruang O(n)."""
        result = []
        current = self._head
        while current is not None:
            result.append(current.value)
            current = current.next
        return result

    def display(self):
        """Kembalikan daftar dari FRONT ke REAR. Kompleksitas waktu O(n)."""
        return self.to_list()


class PriorityAwareQueue:
    """Dua Queue FIFO; semua elemen prioritas dilayani sebelum elemen reguler."""

    def __init__(self):
        """Buat dua lajur kosong. Kompleksitas waktu dan ruang O(1)."""
        self._priority = Queue()
        self._regular = Queue()

    def enqueue(self, value, priority=False):
        """Masukkan di lajur prioritas atau reguler. Kompleksitas waktu O(1)."""
        (self._priority if priority else self._regular).enqueue(value)

    def dequeue(self):
        """Keluarkan FRONT prioritas dahulu. Kompleksitas waktu O(1)."""
        if not self._priority.is_empty():
            return self._priority.dequeue()
        return self._regular.dequeue()

    def peek(self):
        """Lihat FRONT yang akan dilayani. Kompleksitas waktu O(1)."""
        if not self._priority.is_empty():
            return self._priority.peek()
        return self._regular.peek()

    def is_empty(self):
        """Periksa kedua lajur. Kompleksitas waktu O(1)."""
        return self._priority.is_empty() and self._regular.is_empty()

    def size(self):
        """Jumlahkan ukuran kedua lajur. Kompleksitas waktu O(1)."""
        return self._priority.size() + self._regular.size()

    def display(self):
        """Kembalikan tampilan tiap lajur. Kompleksitas waktu dan ruang O(n)."""
        return {
            "priority": self._priority.to_list(),
            "regular": self._regular.to_list(),
        }
