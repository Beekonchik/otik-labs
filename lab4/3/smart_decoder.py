import os
import struct
import sys
import subprocess

class SmartDecoder:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
    
    def get_file_version(self, input_file):
        """Определяет версию формата файла"""
        try:
            with open(input_file, 'rb') as f:
                # Читаем сигнатуру и версию
                header_data = f.read(24)
                if len(header_data) < 24:
                    raise ValueError("Файл слишком короткий для формата klusha")
                
                # Проверяем сигнатуру
                signature = header_data[0:6]
                if signature != self.signature:
                    raise ValueError("Неверная сигнатура файла")
                
                # Читаем версию
                major_version = header_data[6]
                minor_version = header_data[7]
                
                return major_version, minor_version
                
        except Exception as e:
            raise ValueError(f"Ошибка при чтении заголовка файла: {e}")
    
    def decompress_file(self, input_file):
        try:
            if not os.path.exists(input_file):
                print(f"Ошибка: Файл {input_file} не найден")
                return False
            
            # Определяем версию формата
            major_version, minor_version = self.get_file_version(input_file)
            print(f"Обнаружен файл версии: {major_version}.{minor_version}")
            
            # Выбираем соответствующий декодер
            if major_version == 1 and minor_version == 0:
                print("Используется decoder1.py для формата 1.0")
                result = subprocess.run([sys.executable, 'decoder1.py', input_file], 
                                      capture_output=True, text=True)
            elif major_version == 2 and minor_version == 0:
                print("Используется decoder2.py для формата 2.0")
                result = subprocess.run([sys.executable, 'decoder2.py', input_file], 
                                      capture_output=True, text=True)
            else:
                print(f"Ошибка: Неподдерживаемая версия формата {major_version}.{minor_version}")
                return False
            
            # Выводим результат работы декодера
            if result.returncode == 0:
                print(result.stdout)
                return True
            else:
                print(f"Ошибка при декодировании: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Ошибка при разжатии: {e}")
            return False

def main():
    decoder = SmartDecoder()
    
    # Обработка аргументов командной строки
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # По умолчанию ищем любой .klusha файл в текущей директории
        klusha_files = [f for f in os.listdir('.') if f.endswith('.klusha')]
        if klusha_files:
            input_file = klusha_files[0]
            print(f"Используется файл: {input_file}")
        else:
            print("Ошибка: Не указан входной файл и не найдены .klusha файлы в текущей директории")
            print("Использование: python smart_decoder.py <файл.klusha>")
            return
    
    # Проверяем расширение файла
    if not input_file.endswith('.klusha'):
        print("Предупреждение: Рекомендуется использовать файлы с расширением .klusha")
    
    # Разжимаем файл
    decoder.decompress_file(input_file)

if __name__ == "__main__":
    main()