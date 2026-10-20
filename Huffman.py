import heapq
import json
import math

#Initialize a Node class to represent each node in the Huffman tree
class Node:
    def __init__(self, symbol, freq):
        self.symbol = symbol
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq


#calculate the probabilities of each symbol in the input
def calculate_probabilities(data):
    total_length = len(data)
    frequencies = {}
    for symbol in data:
        if symbol in frequencies:
            frequencies[symbol] += 1
        else:
            frequencies[symbol] = 1

    probs = {}
    for symbol, count in frequencies.items():
        probs[symbol] = count / total_length

    return probs

#separate the symbols into two groups based on the probability limit
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


#generate binary mapping for symbols in the others group based on unique count
def generate_others_mapping(others_dict):
    num_unique = len(others_dict)
    if num_unique == 0:
        return {}, 0
    if num_unique == 1:
        bit_len = 1
    else:
        bit_len = math.ceil(math.log2(num_unique))
    
    others_map = {}
    for idx, symbol in enumerate(others_dict.keys()):
        binary_code = format(idx, f"0{bit_len}b")
        others_map[symbol] = binary_code

    return others_map, bit_len


#build the Huffman tree using a priority queue (min-heap) by adding nodes with the lowest frequencies until only one node remains
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


#generate the Huffman codes by traversing the tree and assigning binary codes to each symbol
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

#assign the final codes to the symbols, including handling the "Others" group by the prefix code + the original binary representation of the symbol
def get_final_encoding_map(huffman_codes, others_map):
    final_map = {}

    for symbol, code in huffman_codes.items():
        if symbol != "Others":
            final_map[symbol] = code

    if "Others" in huffman_codes:
        others_prefix = huffman_codes["Others"]
        for symbol, custom_binary in others_map.items():
            final_map[symbol] = others_prefix + custom_binary

    return final_map

#convert the bit string to bytes and return the bytes along with the padding count --> 8 bits, 
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


#convert the bytes back to a bit string and remove the padding bits to start decoding the compressed data
def unpack_bits(binary_data, padding_count):
    bit_string = ""
    for byte in binary_data:
        binary_char = format(byte, "08b")
        bit_string += binary_char

    if padding_count > 0:
        bit_string = bit_string[:-padding_count]

    return bit_string


#compress the input file using the Huffman coding algorithm and save the compressed data to a binary file, including a header with the Huffman codes and padding count
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

    others_map = {}
    others_bit_len = 0
    if others_total_prob > 0:
        tree_probs["Others"] = others_total_prob
        others_map, others_bit_len = generate_others_mapping(others_dict)

    root = build_huffman_tree(tree_probs)
    huffman_codes = generate_huffman_codes(root)
    final_map = get_final_encoding_map(huffman_codes, others_map)

    bit_string = ""
    for symbol in data:
        bit_string += final_map[symbol]

    binary_data, padding_count = pack_bits(bit_string)

    reverse_others_map = {code: sym for sym, code in others_map.items()}

    header = {
        "huffman_codes": huffman_codes,
        "padding_count": padding_count,
        "others_map": reverse_others_map,
        "others_bit_len": others_bit_len,
    }

    header_json = json.dumps(header)
    header_bytes = header_json.encode("utf-8")
    header_length = len(header_bytes)

    with open(compressed_file, "wb") as f:
        f.write(header_length.to_bytes(4, byteorder="big"))
        f.write(header_bytes)
        f.write(binary_data)

#reconstructing the original symbols from the bit string using the Huffman codes
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
    reverse_others_map = header.get("others_map", {})
    others_bit_len = header.get("others_bit_len", 0)

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
                custom_bits = bit_string[i : i + others_bit_len]
                i = i + others_bit_len
                character = reverse_others_map[custom_bits]
                decoded_text += character
            else:
                decoded_text = decoded_text + symbol

            current_code = ""

    with open(decompressed_file, "w", encoding="utf-8") as f:
        f.write(decoded_text)


if __name__ == "__main__":
    limit = float(input("Enter probability limit: "))
    compress("input.txt", "compressed.bin", limit)

    with open("input.txt", "r", encoding="utf-8") as f:
        text = f.read()

    with open("compressed.bin", "rb") as f:
        header_len = int.from_bytes(f.read(4), byteorder="big")
        header_bytes = f.read(header_len)
        data_bytes = f.read()

    print("Compressed -> compressed.bin")
    print("Original size  :", len(text.encode("utf-8")), "bytes")
    print("Compressed data:", len(data_bytes), "bytes and", len(header_bytes) + 4, "bytes for header")

    decompress("compressed.bin", "decompressed.txt")