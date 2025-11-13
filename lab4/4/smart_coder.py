import os
import sys
import subprocess

class SmartCoder:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
    
    def format_size(self, size):
        """Форматирует размер файла в читаемом виде"""
        units = ['байт', 'КБ']
        unit_index = 0
        size_float = float(size)
        while size_float >= 1024 and unit_index < len(units) - 1:
            size_float /= 1024.0
            unit_index += 1
        
        if unit_index == 0:  # Байты
            return f"{size_float:.0f} {units[unit_index]}"
        else: 
            return f"{size_float:.2f} {units[unit_index]}"
    
    def estimate_huffman_size(self, input_file):
        """Оценивает размер сжатых данных по алгоритму Хаффмана"""
        try:
            # Импортируем функционал из coder2.py для оценки
            sys.path.append('.')
            from coder2 import HuffmanCoder
            
            coder = HuffmanCoder()
            
            # Читаем исходный файл
            with open(input_file, 'rb') as f:
                original_data = f.read()
            
            original_size = len(original_data)
            
            # Если файл пустой, возвращаем минимальный размер
            if original_size == 0:
                return 29  # Минимальный размер заголовка + пустые данные
            
            # Строим дерево Хаффмана и коды
            frequency = coder.build_frequency_table(original_data)
            huffman_tree = coder.build_huffman_tree(frequency)
            
            if huffman_tree is None:
                # Пустой файл
                encoded_data = b''
                padding_bits = 0
                encoded_tree = b''
                tree_size = 0
            else:
                codes = coder.build_codes(huffman_tree)
                
                # Кодируем данные
                encoded_data, padding_bits = coder.encode_data(original_data, codes)
                
                # Кодируем дерево Хаффмана
                encoded_tree = coder.encode_huffman_tree(huffman_tree)
                tree_size = len(encoded_tree)
            
            # Оцениваем общий размер сжатых данных
            # Заголовок (29 байт) + дерево + данные
            estimated_size = 29 + tree_size + len(encoded_data)
            
            return estimated_size
            
        except Exception as e:
            print(f"Ошибка при оценке размера Хаффмана: {e}")
            return float('inf')  # В случае ошибки считаем размер бесконечным
    
    def compress_file(self, input_file):
        """Сжимает файл, выбирая оптимальный алгоритм"""
        try:
            output_file = f"{input_file}.klusha"
            
            # Получаем размер исходного файла
            original_size = os.path.getsize(input_file)
            
            n = original_size - 24
            
            print(f"Исходный размер файла: {self.format_size(original_size)}")
            print(f"Пороговое значение n: {self.format_size(n) if n >= 24 else '<24 байт'}")
            
            # Оцениваем размер сжатых данных по Хаффману
            n_compr = self.estimate_huffman_size(input_file)
            print(f"Оценка размера сжатых данных (n_compr): {self.format_size(n_compr)}")
            
            # Выбираем алгоритм сжатия
            if n_compr >= n:
                print("Выбран алгоритм: coder1.py (несжатое хранение)")
                # Запускаем coder1.py
                result = subprocess.run([sys.executable, 'coder1.py', input_file], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"Ошибка при выполнении coder1.py: {result.stderr}")
                    return False
                print(result.stdout)
            else:
                print("Выбран алгоритм: coder2.py (сжатие Хаффмана)")
                # Запускаем coder2.py
                result = subprocess.run([sys.executable, 'coder2.py', input_file], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"Ошибка при выполнении coder2.py: {result.stderr}")
                    return False
                print(result.stdout)
            
            # Проверяем результат
            if not os.path.exists(output_file):
                print("Ошибка: выходной файл не создан")
                return False
                
            return True
            
        except Exception as e:
            print(f"Ошибка при сжатии: {e}")
            return False

def main():
    coder = SmartCoder()
    
    # Обработка аргументов командной строки
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "Q"
    
    # Проверяем существование входного файла
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден в текущей директории")
        return
    
    # Сжимаем файл
    coder.compress_file(input_file)

if __name__ == "__main__":
    main()