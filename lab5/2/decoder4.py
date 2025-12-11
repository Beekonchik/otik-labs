import os
import struct
import sys

class LZ78:
    def __init__(self):
        self.expected_major_version = 4
        self.expected_minor_version = 0
        self.expected_context_algorithm = 1
    
    def format_size(self, size):
        """Форматирует размер файла"""
        if size == 0:
            return "0 байт"
        size_float = float(size)
        if size_float < 1024:
            return f"{size_float:.0f} байт"
        else:
            return f"{size_float/1024:.2f} КБ"
    
    def validate_header(self, header):
        """Проверка заголовка"""
        if len(header) < 24:
            return False
        
        signature = header[0:6]
        if signature != bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61]):
            return False
        
        if header[6] != self.expected_major_version:
            return False
        
        if header[8] != self.expected_context_algorithm:
            return False
        
        return True
    
    def unpack_fixed_bit_pairs(self, data, num_pairs):
        """Распаковка пар с фиксированной длиной"""
        pairs = []
        pos = 0
        
        for _ in range(num_pairs):
            if pos + 5 > len(data):  # 4 байта P + 1 байт a
                break
            
            # Читаем P (4 байта, big-endian)
            parent = struct.unpack('>I', data[pos:pos+4])[0]
            pos += 4
            
            # Читаем a (1 байт)
            char = data[pos]
            pos += 1
            
            pairs.append((parent, char))
        
        return pairs
    
    def lz78_decompress(self, pairs):
        """
        LZ78-распаковка по концепту 1978 года
        """
        dictionary = {0: b""}  # Словарь: номер -> строка
        result = bytearray()
        next_code = 1
        
        for parent, char in pairs:
            # Получаем строку из словаря
            if parent in dictionary:
                parent_str = dictionary[parent]
            else:
                # Ошибка - ссылка на несуществующий индекс
                parent_str = b""
            
            # Новая строка = родительская строка + новый символ
            new_str = parent_str + bytes([char])
            
            # Добавляем в результат
            result.extend(new_str)
            
            # Добавляем новую строку в словарь
            dictionary[next_code] = new_str
            next_code += 1
        
        return bytes(result)
    
    def decompress_file(self, input_file):
        """Распаковка LZ78-файла"""
        try:
            if input_file.endswith('.klusha'):
                base_name = input_file[:-7]
            else:
                base_name = input_file
            
            output_file = f"{base_name}_restored"
            
            with open(input_file, 'rb') as f:
                header = f.read(24)
                if not self.validate_header(header):
                    print("Ошибка: Неверный формат файла")
                    return
                
                original_size = struct.unpack('>Q', header[16:24])[0]
                
                algo_size_data = f.read(4)
                algo_size = struct.unpack('>I', algo_size_data)[0]
                
                algo_data = f.read(algo_size)
            
            # Извлекаем количество пар
            num_pairs = struct.unpack('>I', algo_data[0:4])[0]
            compressed_data = algo_data[4:]
            
            # Распаковываем пары
            pairs = self.unpack_fixed_bit_pairs(compressed_data, num_pairs)
            
            if len(pairs) != num_pairs:
                print(f"Предупреждение: ожидалось {num_pairs} пар, получено {len(pairs)}")
            
            # Декомпрессия LZ78
            decompressed = self.lz78_decompress(pairs)
            
            # Обрезаем до исходного размера
            if len(decompressed) > original_size:
                decompressed = decompressed[:original_size]
            
            # Записываем результат
            with open(output_file, 'wb') as f:
                f.write(decompressed)
            
            print(f"Файл успешно восстановлен: {input_file} -> {output_file}")
            print(f"Размер восстановленного файла: {self.format_size(len(decompressed))}")
            
            # Отладочная информация
            print(f"Количество пар при декомпрессии: {len(pairs)}")
            
        except Exception as e:
            print(f"Ошибка: {e}")
            import traceback
            traceback.print_exc()

def main():
    decoder = LZ78()
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "Q.klusha"
    
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден")
        return
    
    decoder.decompress_file(input_file)

if __name__ == "__main__":
    main()