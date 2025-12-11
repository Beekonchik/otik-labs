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
        dictionary = {}
        next_code = 1
        result = []
        i = 0
        
        # Инициализируем пустую строку
        dictionary[b""] = 0
        
        while i < len(data):
            # Начинаем с пустой строки
            current_match = b""
            longest_match = b""
            parent = 0
            
            # Ищем совпадение, начиная с текущей позиции
            for j in range(i, len(data)):
                current_match += bytes([data[j]])
                
                if current_match in dictionary:
                    # Нашли совпадение - запоминаем
                    longest_match = current_match
                    parent = dictionary[current_match]
                else:
                    # Больше не совпадает
                    break
            
            if len(longest_match) > 0:
                # Нашли совпадение в словаре
                # Следующий символ
                next_pos = i + len(longest_match)
                if next_pos < len(data):
                    next_char = data[next_pos]
                else:
                    next_char = 0
                
                result.append((parent, next_char))
                
                # Добавляем новую строку в словарь
                new_str = longest_match + bytes([next_char]) if next_char != 0 else longest_match
                dictionary[new_str] = next_code
                next_code += 1
                
                i += len(longest_match) + (1 if next_char != 0 else 0)
            else:
                # Нет совпадения - литерал
                result.append((0, data[i]))
                
                # Добавляем в словарь
                dictionary[bytes([data[i]])] = next_code
                next_code += 1
                
                i += 1
        
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
            if (len(lz78_pairs) < 10): print(f"Пары: {lz78_pairs}")
                
            
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