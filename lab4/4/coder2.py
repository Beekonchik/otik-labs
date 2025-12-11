import heapq
import os
import struct
import sys
from collections import Counter

class HuffmanCoder:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
        self.major_version = 2
        self.minor_version = 0
        self.context_algorithm = 0 
        self.context_free = 1
        self.error_protection = 0
        self.reserved = bytes(5)
        
    class HuffmanNode:
        def __init__(self, char, freq):
            self.char = char
            self.freq = freq
            self.left = None
            self.right = None
            
        def __lt__(self, other):
            return self.freq < other.freq
    
    def build_frequency_table(self, data):
        """Строит таблицу частот символов"""
        return Counter(data)
    
    def build_huffman_tree(self, frequency):
        """Строит дерево Хаффмана"""
        heap = []
        for char, freq in frequency.items():
            node = self.HuffmanNode(char, freq)
            heapq.heappush(heap, node)
            
        while len(heap) > 1:
            node1 = heapq.heappop(heap)
            node2 = heapq.heappop(heap)
            
            merged = self.HuffmanNode(None, node1.freq + node2.freq)
            merged.left = node1
            merged.right = node2
            heapq.heappush(heap, merged)
            
        return heap[0] if heap else None
    
    def build_codes(self, root):
        """Строит коды Хаффмана для каждого символа"""
        codes = {}
        
        def traverse(node, current_code):
            if node is None:
                return
                
            if node.char is not None:
                codes[node.char] = current_code
                return
                
            traverse(node.left, current_code + '0')
            traverse(node.right, current_code + '1')
            
        traverse(root, '')
        return codes
    
    def encode_huffman_tree(self, root):
        """Кодирует дерево Хаффмана для сохранения в файл"""
        encoded_tree = []
        
        def preorder_traversal(node):
            if node is None:
                return
                
            if node.char is not None:
                # Лист - записываем 1 + байт символа
                encoded_tree.append(b'\x01')
                encoded_tree.append(bytes([node.char]))
            else:
                # Внутренний узел - записываем 0
                encoded_tree.append(b'\x00')
                preorder_traversal(node.left)
                preorder_traversal(node.right)
                
        preorder_traversal(root)
        return b''.join(encoded_tree)
    
    def encode_data(self, data, codes):
        """Кодирует данные используя коды Хаффмана"""
        encoded_bits = ''.join(codes[byte] for byte in data)
        
        # Дополняем до целого числа байт
        padding = 8 - len(encoded_bits) % 8
        if padding == 8:
            padding = 0
        encoded_bits += '0' * padding
        
        # Преобразуем битовую строку в байты
        encoded_bytes = bytearray()
        for i in range(0, len(encoded_bits), 8):
            byte = encoded_bits[i:i+8]
            encoded_bytes.append(int(byte, 2))
            
        return bytes(encoded_bytes), padding
    
    def format_size(self, size):
        """Форматирует размер файла в читаемом виде"""
        if size == 0:
            return "0 B"
        units = ['байт', 'КБ']
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        return f"{size:.2f} {units[unit_index]}"
    
    def format_encoded_tree(self, encoded_tree):
        """Форматирует закодированное дерево с пробелами"""
        hex_string = encoded_tree.hex()
        # Разбиваем на пары символов и добавляем пробелы
        return ' '.join(hex_string[i:i+2] for i in range(0, len(hex_string), 2))
    
    def char_to_string(self, char):
        """Преобразует байт в читаемое строковое представление"""
        byte_val = char
        if 32 <= byte_val <= 126:
            char_str = chr(byte_val)
            if char_str == '\\':
                return "'\\\\'"
            elif char_str == "'":
                return "'\\''"
            else:
                return f"'{char_str}'"
        else:
            return f"0x{byte_val:02x}"
    
    def compress_file(self, input_file):
        """Сжимает файл методом Хаффмана"""
        try:
            # Генерируем имя выходного файла
            output_file = f"{input_file}.klusha"
            
            # Читаем исходный файл
            with open(input_file, 'rb') as f:
                original_data = f.read()
                
            original_size = len(original_data)
            
            # Строим дерево Хаффмана и коды
            frequency = self.build_frequency_table(original_data)
            huffman_tree = self.build_huffman_tree(frequency)
            
            if huffman_tree is None:
                # Пустой файл
                codes = {}
                encoded_data = b''
                padding_bits = 0
                encoded_tree = b''
                tree_size = 0
            else:
                codes = self.build_codes(huffman_tree)
                
                # Кодируем данные
                encoded_data, padding_bits = self.encode_data(original_data, codes)
                
                # Кодируем дерево Хаффмана
                encoded_tree = self.encode_huffman_tree(huffman_tree)
                tree_size = len(encoded_tree)
            
            # Записываем сжатый файл
            with open(output_file, 'wb') as f:
                # Заголовок (24 байта)
                f.write(self.signature)  # 6 байт
                f.write(bytes([self.major_version]))  # 1 байт
                f.write(bytes([self.minor_version]))  # 1 байт
                f.write(bytes([self.context_algorithm]))  # 1 байт
                f.write(bytes([self.context_free]))  # 1 байт
                f.write(bytes([self.error_protection]))  # 1 байт
                f.write(self.reserved)  # 5 байт
                
                # Исходная длина файла (8 байт, little-endian)
                f.write(struct.pack('<Q', original_size))
                
                # Размер дерева Хаффмана (4 байта, little-endian)
                f.write(struct.pack('<I', tree_size))
                
                # Количество бит дополнения (1 байт)
                f.write(bytes([padding_bits]))
                
                # Закодированное дерево Хаффмана
                f.write(encoded_tree)
                
                # Закодированные данные
                f.write(encoded_data)
                
            compressed_size = os.path.getsize(output_file)
            
            print(f"Файл успешно сжат: {input_file} -> {output_file}")
            print(f"Исходный размер: {self.format_size(original_size)}")
            print(f"Сжатый размер: {self.format_size(compressed_size)}")
            print(f"Длина сжатых данных: {len(encoded_data) * 8 - padding_bits} бит")
                        
            # Выводим дополнительную информацию только если входной файл - Q
            if input_file == "Q":
                formatted_tree = self.format_encoded_tree(encoded_tree)
                print(f"Закодированное дерево: {formatted_tree}")
            
        except FileNotFoundError:
            print(f"Ошибка: Файл {input_file} не найден")
        except Exception as e:
            print(f"Ошибка при сжатии: {e}")

def main():
    coder = HuffmanCoder()
    
    # Обработка аргументов командной строки
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Значения по умолчанию
        input_file = "Q"
    
    # Проверяем существование входного файла
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден в текущей директории")
        return
    
    # Сжимаем файл
    coder.compress_file(input_file)

if __name__ == "__main__":
    main()