import os
import struct
import sys

class HuffmanDecoder:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
        self.expected_major_version = 2
        self.expected_minor_version = 0
        self.expected_context_algorithm = 0
        
    class HuffmanNode:
        def __init__(self, char=None):
            self.char = char
            self.left = None
            self.right = None
    
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
    
    def validate_header(self, header_data):
        """Проверяет корректность заголовка файла"""
        if len(header_data) < 24:
            raise ValueError("Заголовок файла слишком короткий")
        
        # Проверяем сигнатуру
        signature = header_data[0:6]
        if signature != self.signature:
            return False
        
        # Проверяем версию
        major_version = header_data[6]
        minor_version = header_data[7]
        if major_version != self.expected_major_version or minor_version != self.expected_minor_version:
            return False
        
        # Проверяем алгоритм сжатия
        context_algorithm = header_data[8]
        if context_algorithm != self.expected_context_algorithm:
            return False
        
        return True
    
    def decode_huffman_tree(self, encoded_tree):
        """Декодирует дерево Хаффмана из бинарного представления"""
        if not encoded_tree:
            return None
            
        index = 0
        
        def build_tree():
            nonlocal index
            if index >= len(encoded_tree):
                return None
                
            marker = encoded_tree[index]
            index += 1
            
            if marker == 1:  # Лист
                if index >= len(encoded_tree):
                    raise ValueError("Неожиданный конец данных при чтении дерева")
                char = encoded_tree[index]
                index += 1
                return self.HuffmanNode(char)
            elif marker == 0:  # Внутренний узел
                node = self.HuffmanNode()
                node.left = build_tree()
                node.right = build_tree()
                return node
            else:
                raise ValueError(f"Неизвестный маркер узла: {marker}")
                
        root = build_tree()
        
        # Проверяем, что прочитали все дерево
        if index != len(encoded_tree):
            raise ValueError("Не все данные дерева были использованы")
            
        return root
    
    def decode_data(self, encoded_data, huffman_tree, original_size, padding_bits):
        """Декодирует данные используя дерево Хаффмана"""
        if huffman_tree is None or original_size == 0:
            return b''
            
        # Преобразуем закодированные данные в битовую строку
        bit_string = ''
        for byte in encoded_data:
            bit_string += format(byte, '08b')
        
        # Убираем биты дополнения
        if padding_bits > 0:
            bit_string = bit_string[:-padding_bits]
        
        # Декодируем битовую строку
        decoded_data = bytearray()
        current_node = huffman_tree
        
        for bit in bit_string:
            if bit == '0':
                current_node = current_node.left
            else:
                current_node = current_node.right
                
            if current_node is None:
                raise ValueError("Ошибка декодирования: достигнут нулевой узел")
                
            if current_node.char is not None:
                decoded_data.append(current_node.char)
                current_node = huffman_tree
                
                # Проверяем, не достигли ли мы исходного размера
                if len(decoded_data) >= original_size:
                    break
        
        return bytes(decoded_data)
    
    def decompress_file(self, input_file):
        """Разжимает файл, сжатый методом Хаффмана"""
        try:
            # Генерируем имя выходного файла
            base_name = input_file.replace('.klusha', '')
            
            # Разделяем имя файла и расширение
            if '.' in base_name:
                name_parts = base_name.split('.')
                if len(name_parts) > 1:
                    # Если есть расширение, создаем имя_restored.расширение
                    extension = name_parts[-1]
                    file_name = '.'.join(name_parts[:-1])
                    output_file = f"{file_name}_restored.{extension}"
                else:
                    # Если точка есть, но нет расширения (например, "file.")
                    output_file = f"{base_name}_restored"
            else:
                # Если нет расширения
                output_file = f"{base_name}_restored"
            
            # Читаем сжатый файл
            with open(input_file, 'rb') as f:
                # Читаем и проверяем заголовок (24 байта)
                header_data = f.read(24)
                if not self.validate_header(header_data):
                    print("Сигнатура: не совпадает")
                    return
                
                print("Сигнатура: klusha")
                
                # Извлекаем данные из заголовка
                original_size = struct.unpack('<Q', header_data[16:24])[0]
                
                # Читаем размер дерева Хаффмана (4 байта)
                tree_size_data = f.read(4)
                if len(tree_size_data) < 4:
                    raise ValueError("Не удалось прочитать размер дерева")
                tree_size = struct.unpack('<I', tree_size_data)[0]
                
                # Читаем количество бит дополнения (1 байт)
                padding_bits_data = f.read(1)
                if len(padding_bits_data) < 1:
                    raise ValueError("Не удалось прочитать биты дополнения")
                padding_bits = padding_bits_data[0]
                
                # Читаем закодированное дерево Хаффмана
                encoded_tree = f.read(tree_size)
                if len(encoded_tree) != tree_size:
                    raise ValueError(f"Не удалось прочитать все дерево: получено {len(encoded_tree)} байт из {tree_size}")
                
                # Читаем оставшиеся данные (закодированное содержимое)
                encoded_data = f.read()
            
            # Декодируем дерево Хаффмана
            huffman_tree = self.decode_huffman_tree(encoded_tree)
            
            # Декодируем данные
            decoded_data = self.decode_data(encoded_data, huffman_tree, original_size, padding_bits)
            
            # Проверяем размер декодированных данных
            if len(decoded_data) != original_size:
                raise ValueError(f"Размер декодированных данных ({len(decoded_data)}) не совпадает с исходным ({original_size})")
            
            # Записываем разжатый файл
            with open(output_file, 'wb') as f:
                f.write(decoded_data)
                
            print(f"Файл успешно восстановлен: {input_file} -> {output_file}")
            print(f"Исходный размер: {self.format_size(original_size)}")
            print(f"Размер восстановленного файла: {self.format_size(len(decoded_data))}")
            
        except FileNotFoundError:
            print(f"Ошибка: Файл {input_file} не найден")
        except Exception as e:
            print(f"Ошибка при разжатии: {e}")

def main():
    decoder = HuffmanDecoder()
    
    # Обработка аргументов командной строки
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Значения по умолчанию
        input_file = "Q.klusha"
    
    # Проверяем существование входного файла
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден в текущей директории")
        return
    
    # Разжимаем файл
    decoder.decompress_file(input_file)

if __name__ == "__main__":
    main()