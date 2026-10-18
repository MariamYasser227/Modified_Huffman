import heapq
import json


class Node:
    def __init__(self, symbol, freq):
        self.symbol = symbol
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq


def calculate_probabilities(data):
    total_length = len(data)
    frequencies = {}
    for symbol in data:
        if symbol in frequencies:
            frequencies[symbol] = frequencies[symbol] + 1
        else:
            frequencies[symbol] = 1

    probs = {}
    for symbol, count in frequencies.items():
        probs[symbol] = count / total_length

    return probs


def separate_freq_others(probs, limit):
    freq = {}
    others_dict = {}
    others_total_prob = 0.0

    for symbol, prob in probs.items():
        if prob > limit:
            freq[symbol] = prob
        else:
            others_dict[symbol] = prob
            others_total_prob += prob

    return freq, others_dict, others_total_prob


def build_huffman_tree(probs):
    heap = []
    for symbol, prob in probs.items():
        node = Node(symbol, prob)
        heapq.heappush(heap, node)

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = Node(None, left.freq + right.freq)
        merged.left = left
        merged.right = right
        heapq.heappush(heap, merged)

    if len(heap) > 0:
        return heap[0]
    else:
        return None


def generate_huffman_codes(root):
    huffman_codes = {}

    def traverse(node, current_code):
        if node is None:
            return

        if node.left is None and node.right is None:
            if current_code == "":
                huffman_codes[node.symbol] = "0"
            else:
                huffman_codes[node.symbol] = current_code
            return

        traverse(node.left, current_code + "0")
        traverse(node.right, current_code + "1")

    traverse(root, "")
    return huffman_codes


def get_final_encoding_map(huffman_codes, others_dict):
    final_map = {}

    for symbol, code in huffman_codes.items():
        if symbol != "Others":
            final_map[symbol] = code

    if "Others" in huffman_codes:
        others_prefix = huffman_codes["Others"]
        for symbol in others_dict.keys():
            original_binary = format(ord(symbol), "08b")
            final_map[symbol] = others_prefix + original_binary

    return final_map

#convert the bit string to bytes and return the bytes along with the padding count --> 8 bits
def pack_bits(bit_string):
    remainder = len(bit_string) % 8
    if remainder != 0:
        padding_count = 8 - remainder
    else:
        padding_count = 0

    for i in range(padding_count):
        bit_string += "0"

    bytes_list = bytearray()
    for i in range(0, len(bit_string), 8):
        byte_chunk = bit_string[i : i + 8]
        number = int(byte_chunk, 2)
        bytes_list.append(number)

    return bytes(bytes_list), padding_count


def unpack_bits(binary_data, padding_count):
    bit_string = ""
    for byte in binary_data:
        binary_char = format(byte, "08b")
        bit_string += binary_char

    if padding_count > 0:
        bit_string = bit_string[:-padding_count]

    return bit_string


def compress(input_file, compressed_file, limit):
    with open(input_file, "r", encoding="utf-8") as f:
        data = f.read()

    if len(data) == 0:
        return

    probs = calculate_probabilities(data)
    freq, others_dict, others_total_prob = separate_freq_others(probs, limit)

    tree_probs = {}
    for symbol, prob in freq.items():
        tree_probs[symbol] = prob

    if others_total_prob > 0:
        tree_probs["Others"] = others_total_prob

    root = build_huffman_tree(tree_probs)
    huffman_codes = generate_huffman_codes(root)
    final_map = get_final_encoding_map(huffman_codes, others_dict)

    bit_string = ""
    for symbol in data:
        bit_string += final_map[symbol]

    binary_data, padding_count = pack_bits(bit_string)

    header = {
        "huffman_codes": huffman_codes,
        "padding_count": padding_count,
    }

    header_json = json.dumps(header)
    header_bytes = header_json.encode("utf-8")
    header_length = len(header_bytes)

    with open(compressed_file, "wb") as f:
        f.write(header_length.to_bytes(4, byteorder="big"))
        f.write(header_bytes)
        f.write(binary_data)


def decompress(compressed_file, decompressed_file):
    with open(compressed_file, "rb") as f:
        header_length_bytes = f.read(4)
        header_length = int.from_bytes(header_length_bytes, byteorder="big")

        header_bytes = f.read(header_length)
        header_json = header_bytes.decode("utf-8")
        header = json.loads(header_json)

        binary_data = f.read()

    huffman_codes = header["huffman_codes"]
    padding_count = header["padding_count"]

    bit_string = unpack_bits(binary_data, padding_count)

    reverse_huffman = {}
    for symbol, code in huffman_codes.items():
        reverse_huffman[code] = symbol

    decoded_text = ""
    current_code = ""

    i = 0
    while i < len(bit_string):
        current_code = current_code + bit_string[i]
        i = i + 1

        if current_code in reverse_huffman:
            symbol = reverse_huffman[current_code]
            if symbol == "Others":
                ascii_bits = bit_string[i : i + 8]
                i = i + 8
                character = chr(int(ascii_bits, 2))
                decoded_text += character
            else:
                decoded_text = decoded_text + symbol

            current_code = ""

    with open(decompressed_file, "w", encoding="utf-8") as f:
        f.write(decoded_text)


if __name__ == "__main__":
    limit = float(input("Enter probability limit: "))
    compress("input.txt", "compressed.bin", limit)
    decompress("compressed.bin", "decompressed.txt")