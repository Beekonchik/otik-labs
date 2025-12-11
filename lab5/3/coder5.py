import os
import struct
import sys

class LZ77:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])
        self.major_version = 5
        self.minor_version = 0
        self.context_algorithm = 1
        self.context_free_algorithm = 0
        self.error_protection_algorithm = 0
        self.window_size = 4096  # Размер скользящего окна
    
    def format_size(self, size):
        """Форматирует размер файла"""
        if size == 0:
            return "0 байт"
        units = ['байт', 'КБ']
        unit_index = 0
        size_float = float(size)
        while size_float >= 1024 and unit_index < len(units) - 1:
            size_float /= 1024.0
            unit_index += 1
        
        if unit_index == 0:
            return f"{size_float:.0f} {units[unit_index]}"
        else:
            return f"{size_float:.2f} {units[unit_index]}"
    
    def find_best_match(self, data, pos):
        """Ищет лучшее совпадение в скользящем окне"""
        start = max(0, pos - self.window_size)
        best_len = 0
        best_pos = 0
        
        # Простой поиск (можно оптимизировать)
        for i in range(start, pos):
            if data[i] == data[pos]:
                length = 1
                while (pos + length < len(data) and 
                       i + length < pos and
                       data[i + length] == data[pos + length]):
                    length += 1
                
                if length > best_len:
                    best_len = length
                    best_pos = pos - i
        
        # Ограничиваем максимальную длину 66
        if best_len > 66:
            best_len = 66
        
        # Возвращаем только если длина >= 3
        if best_len >= 3:
            return (best_pos, best_len)
        return (0, 0)
    
    def compress_lz77_simple(self, data):
        """Простая реализация LZ77 по схеме с изображения"""
        tokens = []
        i = 0
        
        while i < len(data):
            offset, length = self.find_best_match(data, i)
            
            if length >= 3:
                # Кодируем совпадение
                # L-3 (6 бит): length ∈ [3, 66] -> L-3 ∈ [0, 63]
                l_code = length - 3
                
                # Следующий символ (10 бит)
                if i + length < len(data):
                    next_char = data[i + length]
                else:
                    next_char = 0
                
                tokens.append((offset, l_code, next_char))
                i += length + 1
            else:
                # Литерал: кодируем как совпадение длины 0
                tokens.append((0, 0, data[i]))
                i += 1
        
        return tokens
    
    def encode_tokens(self, tokens):
        """Кодирование токенов в битовый поток по формату (L-3):6, S:10"""
        bits = []
        
        for offset, l_code, next_char in tokens:
            # L-3 (6 бит)
            bits.append(format(l_code, '06b'))
            # S (10 бит) - следующий символ
            bits.append(format(next_char, '010b'))
            # В реальном LZ77 здесь был бы offset, но в данной схеме его нет
        
        # Конвертируем в байты
        bit_string = ''.join(bits)
        while len(bit_string) % 8 != 0:
            bit_string += '0'
        
        result = bytearray()
        for i in range(0, len(bit_string), 8):
            result.append(int(bit_string[i:i+8], 2))
        
        return bytes(result)
    
    def compress_file(self, input_file):
        """Основная функция сжатия"""
        try:
            output_file = input_file + ".klusha"
            
            with open(input_file, 'rb') as f:
                data = f.read()
            
            original_size = len(data)
            
            # Сжимаем данные
            tokens = self.compress_lz77_simple(data)
            compressed_data = self.encode_tokens(tokens)
            
            # Формируем алгоритмические данные
            algo_data = struct.pack('>I', len(tokens)) + compressed_data
            algo_data_size = len(algo_data)
            
            # Записываем файл
            with open(output_file, 'wb') as f:
                # Заголовок
                f.write(self.signature)
                f.write(bytes([self.major_version]))
                f.write(bytes([self.minor_version]))
                f.write(bytes([self.context_algorithm]))
                f.write(bytes([self.context_free_algorithm]))
                f.write(bytes([self.error_protection_algorithm]))
                f.write(b'\x00' * 5)
                f.write(struct.pack('>Q', original_size))
                
                # Размер алгоритмических данных
                f.write(struct.pack('>I', algo_data_size))
                
                # Алгоритмические данные
                f.write(algo_data)
            
            compressed_size = os.path.getsize(output_file)
            
            print(f"Файл успешно сжат: {input_file} -> {output_file}")
            print(f"Исходный размер: {self.format_size(original_size)}")
            print(f"Сжатый размер: {self.format_size(compressed_size)}")
            
        except Exception as e:
            print(f"Ошибка: {e}")

def main():
    coder = LZ77()
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "Q"
    
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден")
        return
    
    coder.compress_file(input_file)

if __name__ == "__main__":
    main()