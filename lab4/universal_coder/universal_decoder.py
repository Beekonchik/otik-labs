import os
import sys
import struct

class UniversalDecoder:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
    
    def read_header(self, input_file):
        """Читает и проверяет заголовок файла"""
        try:
            with open(input_file, 'rb') as f:
                header_data = f.read(24)
                
            if len(header_data) < 24:
                raise ValueError("Заголовок файла слишком короткий")
            
            # Проверяем сигнатуру
            signature = header_data[0:6]
            if signature != self.signature:
                return None, "Неверная сигнатура файла"
            
            # Извлекаем версию
            major_version = header_data[6]
            minor_version = header_data[7]
            
            # Извлекаем коды алгоритмов
            context_algorithm = header_data[8]
            context_free_algorithm = header_data[9]
            error_protection_algorithm = header_data[10]
            
            # Извлекаем исходный размер файла
            original_size = struct.unpack('<Q', header_data[16:24])[0]
            
            header_info = {
                'major_version': major_version,
                'minor_version': minor_version,
                'context_algorithm': context_algorithm,
                'context_free_algorithm': context_free_algorithm,
                'error_protection_algorithm': error_protection_algorithm,
                'original_size': original_size,
                'input_file': input_file
            }
            
            return header_info, None
            
        except Exception as e:
            return None, f"Ошибка чтения заголовка: {e}"
    
    def decompress_file(self, input_file):
        """Основной метод для декомпрессии файла"""
        # Читаем заголовок
        header_info, error = self.read_header(input_file)
        if error:
            print(f"Ошибка: {error}")
            return
        
        print(f"Сигнатура: klusha")
        print(f"Версия: {header_info['major_version']}.{header_info['minor_version']}")
        print(f"Алгоритмы: контекстный={header_info['context_algorithm']}, "
              f"бесконтекстный={header_info['context_free_algorithm']}, "
              f"защита={header_info['error_protection_algorithm']}")
        
        # Проверяем версию и вызываем соответствующий декодер
        major_version = header_info['major_version']
        
        if major_version == 1:
            print("Вызов декодера версии 1.0")
            # Импортируем и вызываем decoder1
            try:
                from decoder1 import HuffmanDecoder10
                decoder = HuffmanDecoder10()
                decoder.decompress_file(input_file)
            except ImportError:
                print("Ошибка: Декодер версии 1.0 не найден")
            except Exception as e:
                print(f"Ошибка при декомпрессии версии 1.0: {e}")
                
        elif major_version == 2:
            print("Вызов декодера версии 2.0")
            # Импортируем и вызываем decoder2
            try:
                from decoder2 import HuffmanDecoder20
                decoder = HuffmanDecoder20()
                decoder.decompress_file(input_file)
            except ImportError:
                print("Ошибка: Декодер версии 2.0 не найден")
            except Exception as e:
                print(f"Ошибка при декомпрессии версии 2.0: {e}")
                
        else:
            print(f"Ошибка: Неподдерживаемая версия формата: {major_version}.{header_info['minor_version']}")

def main():
    decoder = UniversalDecoder()
    
    # Обработка аргументов командной строки
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "Q.klusha"
    
    # Проверяем существование входного файла
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден")
        return
    
    # Декомпрессируем файл
    decoder.decompress_file(input_file)

if __name__ == "__main__":
    main()