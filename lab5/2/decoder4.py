import os
import struct
import sys

class LZW_Decoder:
    def __init__(self):
        self.expected_major_version = 4
        self.expected_minor_version = 0
        self.expected_context_algorithm = 0
    
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
        
        return f"{size_float:.2f} {units[unit_index]}"
    
    def validate_header(self, header_data):
        """Проверяет корректность заголовка файла"""
        if len(header_data) < 24:
            raise ValueError("Заголовок файла слишком короткий")
        
        # Проверяем сигнатуру
        signature = header_data[0:6]
        expected_signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])
        if signature != expected_signature:
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
    
    def unpack_bytes_to_codes(self, packed_data, num_codes):
        """Распаковка байтов в коды LZW"""
        codes = []
        # Каждый код занимает 4 байта (big-endian)
        for i in range(0, len(packed_data), 4):
            if len(codes) >= num_codes:
                break
            code_data = packed_data[i:i+4]
            if len(code_data) < 4:
                break
            code = struct.unpack('>I', code_data)[0]
            codes.append(code)
        return codes
    
    def lzw_decompress(self, codes):
        """Реализация LZW-распаковки"""
        # Инициализация словаря: все одиночные байты
        dictionary = {}
        next_code = 0
        
        # Инициализируем словарь обратным отображением
        for i in range(256):
            dictionary[next_code] = bytes([i])
            next_code += 1
        
        result = b""
        
        if not codes:
            return result
        
        # Первый код
        old = codes[0]
        if old in dictionary:
            result += dictionary[old]
            s = dictionary[old]
        else:
            raise ValueError(f"Некорректный код {old} в начале потока")
        
        # Обработка остальных кодов
        for code in codes[1:]:
            if code in dictionary:
                entry = dictionary[code]
                result += entry
                # Добавляем новую последовательность в словарь
                new_entry = dictionary[old] + entry[0:1]
                dictionary[next_code] = new_entry
                next_code += 1
                s = entry
            else:
                # Особый случай: код еще не в словаре
                new_entry = dictionary[old] + dictionary[old][0:1]
                result += new_entry
                dictionary[next_code] = new_entry
                next_code += 1
                s = new_entry
            
            old = code
        
        return result
    
    def decompress_file(self, input_file):
        """Извлекает файл из контейнера версии 2.0"""
        try:
            # Генерируем имя выходного файла
            if input_file.endswith('.klusha'):
                base_name = input_file[:-7]  # Убираем .klusha
            else:
                base_name = input_file
            
            # Создаем имя для восстановленного файла
            output_file = f"{base_name}_restored"
            
            # Читаем сжатый файл
            with open(input_file, 'rb') as f:
                # Читаем и проверяем заголовок (24 байта)
                header_data = f.read(24)
                if not self.validate_header(header_data):
                    print("Ошибка: Неверная версия формата или неподдерживаемый алгоритм")
                    return
                
                # Извлекаем данные из заголовка - используем big-endian
                file_size_bytes = header_data[16:24]
                original_size = struct.unpack('>Q', file_size_bytes)[0]
                
                # Читаем размер служебных данных алгоритма (4 байта)
                algo_data_size_data = f.read(4)
                if len(algo_data_size_data) < 4:
                    raise ValueError("Не удалось прочитать размер служебных данных")
                algo_data_size = struct.unpack('>I', algo_data_size_data)[0]
                
                # Читаем служебные данные алгоритма (сжатые данные)
                algo_data = f.read(algo_data_size)
                if len(algo_data) < algo_data_size:
                    raise ValueError(f"Не удалось прочитать все сжатые данные. Ожидалось {algo_data_size} байт, прочитано {len(algo_data)}")
                
            # Распаковываем сжатые данные
            # Первые 4 байта - количество кодов
            if len(algo_data) < 4:
                raise ValueError("Сжатые данные слишком короткие")
            
            num_codes = struct.unpack('>I', algo_data[0:4])[0]
            packed_codes = algo_data[4:]
            
            # Распаковываем коды
            codes = self.unpack_bytes_to_codes(packed_codes, num_codes)
            
            if len(codes) != num_codes:
                print(f"Предупреждение: ожидалось {num_codes} кодов, получено {len(codes)}")
            
            # Выполняем LZW-распаковку
            decompressed_data = self.lzw_decompress(codes)
            
            # Проверяем размер
            if len(decompressed_data) != original_size:
                print(f"Предупреждение: размер восстановленных данных ({len(decompressed_data)} байт) не совпадает с ожидаемым ({original_size} байт)")
            
            # Записываем восстановленный файл
            with open(output_file, 'wb') as f:
                f.write(decompressed_data)
                
            print(f"Файл успешно восстановлен: {input_file} -> {output_file}")
            print(f"Размер восстановленного файла: {self.format_size(len(decompressed_data))}")
            
        except FileNotFoundError:
            print(f"Ошибка: Файл {input_file} не найден")
        except Exception as e:
            print(f"Ошибка при восстановлении: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Основная функция для самостоятельного использования декодера"""
    decoder = LZW_Decoder()
    
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