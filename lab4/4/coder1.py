import os
import struct
import sys

class HuffmanCoder10:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
        self.major_version = 1
        self.minor_version = 0
        self.context_algorithm = 0
        self.context_free_algorithm = 0
        self.error_protection_algorithm = 0
    
    def format_size(self, size):
        """Форматирует размер файла в читаемом виде"""
        if size == 0:
            return "0 B"
        units = ['байт', 'КБ']
        unit_index = 0
        size_float = float(size)
        while size_float >= 1024 and unit_index < len(units) - 1:
            size_float /= 1024.0
            unit_index += 1
        
        if unit_index == 0:  # Байты
            return f"{size_float:.0f} {units[unit_index]}"
        else:  # КБ, МБ, ГБ
            return f"{size_float:.2f} {units[unit_index]}"
    
    def compress_file(self, input_file):
        """Создает контейнер версии 1.0"""
        try:
            output_file = input_file + ".klusha"
            
            # Читаем исходный файл
            with open(input_file, 'rb') as f:
                file_data = f.read()
            
            original_size = len(file_data)
            algo_data = b""  # Пустые служебные данные
            algo_data_size = len(algo_data)
            
            # Создаем архив
            with open(output_file, 'wb') as f:
                # Заголовок (24 байта)
                f.write(self.signature)  # 6 байт - сигнатура
                f.write(bytes([self.major_version]))  # 1 байт - мажорная версия
                f.write(bytes([self.minor_version]))  # 1 байт - минорная версия
                f.write(bytes([self.context_algorithm]))  # 1 байт - алгоритм контекстного сжатия
                f.write(bytes([self.context_free_algorithm]))  # 1 байт - алгоритм бесконтекстного сжатия
                f.write(bytes([self.error_protection_algorithm]))  # 1 байт - алгоритм защиты
                f.write(b'\x00\x00\x00\x00\x00')  # 5 байт - зарезервированные октеты
                f.write(struct.pack('>Q', original_size))  # 8 байт - размер файла (big-endian)
                
                # Размер служебных данных (4 байта)
                f.write(struct.pack('>I', algo_data_size))  # big-endian
                
                # Служебные данные алгоритмов
                f.write(algo_data)
                
                # Исходные данные файла
                f.write(file_data)
            
            compressed_size = os.path.getsize(output_file)
            
            print(f"Файл успешно сжат: {input_file} -> {output_file}")
            print(f"Исходный размер: {self.format_size(original_size)}")
            print(f"Сжатый размер: {self.format_size(compressed_size)}")
            
        except FileNotFoundError:
            print(f"Ошибка: Файл {input_file} не найден")
        except Exception as e:
            print(f"Ошибка при создании архива: {e}")

def main():
    coder = HuffmanCoder10()
    
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