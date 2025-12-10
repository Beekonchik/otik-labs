import os
import struct
import sys

class LZW_Coder:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
        self.major_version = 4
        self.minor_version = 0
        self.context_algorithm = 0
        self.context_free_algorithm = 0
        self.error_protection_algorithm = 0
        
    def format_size(self, size):
        """Форматирует размер файла в читаемом виде"""
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
    
    def lzw_compress(self, data):
        """Реализация LZW-сжатия"""
        # Инициализация словаря: все одиночные байты
        dictionary = {}
        next_code = 0
        
        # Добавляем все возможные байты в словарь (0-255)
        for i in range(256):
            dictionary[bytes([i])] = next_code
            next_code += 1
        
        w = b""
        result = []
        
        for byte in data:
            c = bytes([byte])
            wc = w + c
            
            if wc in dictionary:
                w = wc
            else:
                # Выводим код для w
                result.append(dictionary[w])
                
                # Добавляем wc в словарь
                dictionary[wc] = next_code
                next_code += 1
                
                # Начинаем новую последовательность с c
                w = c
        
        # Вывод последнего кода
        if w:
            result.append(dictionary[w])
        
        return result
    
    def pack_codes_to_bytes(self, codes):
        """Упаковка кодов в байты"""
        # Упаковываем коды как 4-байтовые целые (big-endian)
        packed_data = b""
        for code in codes:
            packed_data += struct.pack('>I', code)
        return packed_data
    
    def compress_file(self, input_file):
        """Создает контейнер версии 2.0 с LZW-сжатием"""
        try:
            output_file = input_file + ".klusha"
            
            # Читаем исходный файл
            with open(input_file, 'rb') as f:
                file_data = f.read()
            
            original_size = len(file_data)
            
            # Выполняем LZW-сжатие
            compressed_codes = self.lzw_compress(file_data)
            
            # Упаковываем коды в байты
            packed_data = self.pack_codes_to_bytes(compressed_codes)
            
            # Создаем служебные данные: сначала количество кодов, потом коды
            algo_data = struct.pack('>I', len(compressed_codes)) + packed_data
            algo_data_size = len(algo_data)
            
            # Создаем архив
            with open(output_file, 'wb') as f:
                # Заголовок (24 байта)
                f.write(self.signature)  # 6 байт
                f.write(bytes([self.major_version]))  # 1 байт
                f.write(bytes([self.minor_version]))  # 1 байт
                f.write(bytes([self.context_algorithm]))  # 1 байт
                f.write(bytes([self.context_free_algorithm]))  # 1 байт
                f.write(bytes([self.error_protection_algorithm]))  # 1 байт
                f.write(b'\x00\x00\x00\x00\x00')  # 5 байт
                f.write(struct.pack('>Q', original_size))  # 8 байт
                
                # Размер служебных данных (4 байта)
                f.write(struct.pack('>I', algo_data_size))
                
                # Служебные данные алгоритмов (сжатые данные)
                f.write(algo_data)
                
                # ИСХОДНЫЕ ДАННЫЕ НЕ ЗАПИСЫВАЕМ - только сжатые
            
            compressed_size = os.path.getsize(output_file)
            
            print(f"Файл успешно сжат: {input_file} -> {output_file}")
            print(f"Исходный размер: {self.format_size(original_size)}")
            print(f"Сжатый размер: {self.format_size(compressed_size)}")
            
        except FileNotFoundError:
            print(f"Ошибка: Файл {input_file} не найден")
        except Exception as e:
            print(f"Ошибка при создании архива: {e}")

def main():
    coder = LZW_Coder()
    
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