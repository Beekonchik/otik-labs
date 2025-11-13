import os
import struct
import sys

class HuffmanDecoder10:
    def __init__(self):
        self.expected_major_version = 1
        self.expected_minor_version = 0
        self.expected_context_algorithm = 0
        self.expected_context_free_algorithm = 0
        self.expected_error_protection_algorithm = 0
    
    def format_size(self, size):
        """Форматирует размер файла в читаемом виде"""
        if size == 0:
            return "0 B"
        units = ['Байт', 'КБ', 'МБ']
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        return f"{size:.2f} {units[unit_index]}"
    
    def validate_header(self, header_data):
        """Проверяет корректность заголовка файла для версии 1.0"""
        if len(header_data) < 24:
            raise ValueError("Заголовок файла слишком короткий")
        
        # Проверяем версию
        major_version = header_data[6]
        minor_version = header_data[7]
        if major_version != self.expected_major_version or minor_version != self.expected_minor_version:
            return False
        
        # Проверяем алгоритмы сжатия (должны быть 0 в этой версии)
        context_algorithm = header_data[8]
        context_free_algorithm = header_data[9]
        error_protection_algorithm = header_data[10]
        
        if (context_algorithm != self.expected_context_algorithm or 
            context_free_algorithm != self.expected_context_free_algorithm or
            error_protection_algorithm != self.expected_error_protection_algorithm):
            return False
        
        return True
    
    def decompress_file(self, input_file):
        """Извлекает файл из контейнера версии 1.0"""
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
                    print("Ошибка: Неверная версия формата или алгоритм для версии 1.0")
                    return
                
                # Извлекаем данные из заголовка - используем big-endian
                file_size_bytes = header_data[16:24]
                original_size = struct.unpack('>Q', file_size_bytes)[0]
                
                # Читаем размер служебных данных алгоритма (4 байта) - big-endian
                algo_data_size_data = f.read(4)
                if len(algo_data_size_data) < 4:
                    raise ValueError("Не удалось прочитать размер служебных данных")
                algo_data_size = struct.unpack('>I', algo_data_size_data)[0]
                
                # Пропускаем служебные данные алгоритма
                if algo_data_size > 0:
                    f.read(algo_data_size)
                
                # Читаем исходные данные файла
                file_data = f.read(original_size)
                
            # Записываем восстановленный файл
            with open(output_file, 'wb') as f:
                f.write(file_data)
                
            print(f"Файл успешно восстановлен: {input_file} -> {output_file}")
            print(f"Восстановленный размер: {self.format_size(len(file_data))}")
            
        except FileNotFoundError:
            print(f"Ошибка: Файл {input_file} не найден")
        except Exception as e:
            print(f"Ошибка при восстановлении: {e}")

def main():
    """Основная функция для самостоятельного использования decoder1"""
    decoder = HuffmanDecoder10()
    
    # Обработка аргументов командной строки
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "Q.klusha"
    
    # Проверяем существование входного файла
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден")
        return
    
    # Восстанавливаем файл
    decoder.decompress_file(input_file)

if __name__ == "__main__":
    main()