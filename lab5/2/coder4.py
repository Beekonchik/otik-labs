import os
import struct
import sys

class LZ78:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])
        self.major_version = 4
        self.minor_version = 0
        self.context_algorithm = 1
        self.context_free_algorithm = 0
        self.error_protection_algorithm = 0
        
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
    
    def lz78_compress(self, data):
        """
        LZ78-сжатие по концепту 1978 года
        Возвращает список пар (parent_index, next_char)
        """
        dictionary = {b"": 0}  # Пустая строка с индексом 0
        next_code = 1
        result = []
        
        i = 0
        while i < len(data):
            current_str = b""
            parent = 0
            
            # Ищем самую длинную строку, уже имеющуюся в словаре
            for j in range(i, len(data)):
                test_str = current_str + bytes([data[j]])
                if test_str in dictionary:
                    current_str = test_str
                    parent = dictionary[test_str]
                else:
                    # Нашли новую строку
                    break
            
            # Если current_str пустая (символ не найден в словаре)
            if not current_str:
                next_char = data[i]
                parent = 0
                i += 1
            else:
                # Текущая строка есть в словаре, берем следующий символ
                if i + len(current_str) < len(data):
                    next_char = data[i + len(current_str)]
                else:
                    next_char = 0  # Конец файла
                i += len(current_str) + 1
            
            # Добавляем новую строку в словарь
            new_str = current_str + bytes([next_char]) if current_str else bytes([next_char])
            dictionary[new_str] = next_code
            next_code += 1
            
            # Сохраняем пару (P, a)
            result.append((parent, next_char))
        
        return result
    
    def pack_lz78_pairs(self, pairs, use_variable_bit_length=True):
        """
        Упаковка пар LZ78 в байты
        use_variable_bit_length: True - переменная длина P, False - фиксированная
        """
        if not pairs:
            return b""
        
        if use_variable_bit_length:
            return self._pack_variable_bit(pairs)
        else:
            return self._pack_fixed_bit(pairs)
    
    def _pack_fixed_bit(self, pairs):
        """Упаковка с фиксированной длиной (4 байта на P, 1 на a)"""
        packed = bytearray()
        
        for parent, char in pairs:
            # P как 4-байтовое целое (big-endian)
            packed.extend(struct.pack('>I', parent))
            # a как 1 байт
            packed.append(char & 0xFF)
        
        return bytes(packed)
    
    def _pack_variable_bit(self, pairs):
        """Упаковка с переменной длиной P (минимальный код)"""
        bit_stream = []
        
        for i, (parent, char) in enumerate(pairs):
            # Определяем минимальную длину для P
            # На шаге m номер P ∈ {0, 1, ..., m-1}
            m = i + 1  # Текущий шаг (начинаем с 1)
            bits_for_p = max(1, (m-1).bit_length()) if m > 1 else 1
            
            # Если parent = 0 и это первый шаг, можно использовать 0 бит
            if i == 0 and parent == 0:
                bits_for_p = 0
            
            # Кодируем P
            if bits_for_p > 0:
                bit_stream.append(format(parent, f'0{bits_for_p}b'))
            
            # Кодируем символ (8 бит)
            bit_stream.append(format(char, '08b'))
        
        # Конвертируем биты в байты
        bit_string = ''.join(bit_stream)
        while len(bit_string) % 8 != 0:
            bit_string += '0'
        
        result = bytearray()
        for i in range(0, len(bit_string), 8):
            result.append(int(bit_string[i:i+8], 2))
        
        return bytes(result)
    
    def compress_file(self, input_file):
        """Создает контейнер с LZ78-сжатием"""
        try:
            output_file = input_file + ".klusha"
            
            # Читаем исходный файл
            with open(input_file, 'rb') as f:
                file_data = f.read()
            
            original_size = len(file_data)
            
            # Выполняем LZ78-сжатие
            lz78_pairs = self.lz78_compress(file_data)
            
            # Упаковываем пары (используем фиксированную длину для простоты)
            packed_data = self._pack_fixed_bit(lz78_pairs)
            
            # Создаем служебные данные
            algo_data = struct.pack('>I', len(lz78_pairs)) + packed_data
            algo_data_size = len(algo_data)
            
            # Создаем архив
            with open(output_file, 'wb') as f:
                # Заголовок (24 байта)
                f.write(self.signature)
                f.write(bytes([self.major_version]))
                f.write(bytes([self.minor_version]))
                f.write(bytes([self.context_algorithm]))
                f.write(bytes([self.context_free_algorithm]))
                f.write(bytes([self.error_protection_algorithm]))
                f.write(b'\x00\x00\x00\x00\x00')
                f.write(struct.pack('>Q', original_size))
                
                # Размер служебных данных (4 байта)
                f.write(struct.pack('>I', algo_data_size))
                
                # Служебные данные алгоритмов
                f.write(algo_data)
            
            compressed_size = os.path.getsize(output_file)
            
            print(f"Файл успешно сжат: {input_file} -> {output_file}")
            print(f"Исходный размер: {self.format_size(original_size)}")
            print(f"Сжатый размер: {self.format_size(compressed_size)}")
            
            # Отладочная информация
            print(f"Количество пар (P,a): {len(lz78_pairs)}")
            if len(lz78_pairs) > 0:
                print(f"Пример первых 5 пар: {lz78_pairs[:5]}")
            
        except FileNotFoundError:
            print(f"Ошибка: Файл {input_file} не найден")
        except Exception as e:
            print(f"Ошибка при создании архива: {e}")
            import traceback
            traceback.print_exc()

def main():
    coder = LZ78()
    
    # Обработка аргументов командной строки
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "Q"
    
    # Проверяем существование входного файла
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден")
        return
    
    # Создаем архив
    coder.compress_file(input_file)

if __name__ == "__main__":
    main()