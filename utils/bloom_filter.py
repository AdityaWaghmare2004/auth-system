import hashlib 

class BloomFilter:
    def __init__(self, size: int = 1000,num_hashes: int = 3 ):
        self.size = size
        self.num_hashes = num_hashes
        self.bit_array = [0] * size

    def _get_hash(self, item: str, seed: int) -> int:
        combined = f"{item}{seed}".encode("utf-8")
        digest = hashlib.sha256(combined).hexdigest()
        return int(digest, 16) % self.size
    
    def add(self, item: str):
        for seed in range(self.num_hashes):
            index = self._get_hash(item, seed)
            self.bit_array[index] = 1

    def contains(self, item: str) -> bool:
        for seed in range(self.num_hashes):
            index = self._get_hash(item, seed)
            if self.bit_array[index] == 0:
                return False
            return True