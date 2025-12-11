import struct
import os
import sys
import math
from collections import Counter
from decimal import Decimal, getcontext

# Установим высокую точность для Decimal
getcontext().prec = 128

class ShannonEncoder:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
        self.major_version = 1
        self.minor_version = 4  # Версия для метода Шеннона
        self.context_algorithm = 4  # Код алгоритма Шеннона
        self.context_free = 0
        self.error_protection = 0
        self.reserved = bytes(5)
    
    def calculate_entropy(self, frequencies, total_count):
        """Вычисляет энтропию по формуле Шеннона"""
        entropy = 0.0
        for count in frequencies.values():
            if count > 0:
                probability = count / total_count
                entropy -= probability * math.log2(probability)
        return entropy
    
    def build_probability_table(self, data):
        """Строит таблицу вероятностей символов"""
        total_count = len(data)
        frequencies = Counter(data)
        probabilities = {}
        cumulative = {}
        
        # Сортируем символы по убыванию вероятности 
        sorted_symbols = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
        sorted_symbols = [symbol for symbol, _ in sorted_symbols]
        
        # Вычисляем вероятности и кумулятивные суммы
        cum_prob = Decimal('0')
        for symbol in sorted_symbols:
            prob = Decimal(frequencies[symbol]) / Decimal(total_count)
            probabilities[symbol] = prob
            cumulative[symbol] = cum_prob
            cum_prob += prob
        
        return frequencies, probabilities, cumulative, total_count, sorted_symbols
    
    def shannon_encode_symbol(self, probability, cumulative_prob):
        """Кодирует один символ методом Шеннона"""
        # Длина кода по Шеннону: ⌈-log2(p)⌉
        code_length = math.ceil(-math.log2(float(probability)))
        
        # Получаем первые code_length битов из двоичного представления cumulative_prob
        # Метод Шеннона: берём первые L битов от F(s) = кумулятивная вероятность
        value = cumulative_prob
        bit_string = ""
        
        for _ in range(code_length):
            value *= Decimal('2')
            if value >= Decimal('1'):
                bit_string += '1'
                value -= Decimal('1')
            else:
                bit_string += '0'
        
        return bit_string, code_length
    
    def shannon_encode(self, data, probabilities, cumulative, sorted_symbols):
        """Выполняет кодирование методом Шеннона"""
        # Создаём таблицу кодов для каждого символа
        codes = {}
        code_lengths = {}
        
        for symbol in sorted_symbols:
            code, length = self.shannon_encode_symbol(
                probabilities[symbol], 
                cumulative[symbol]
            )
            codes[symbol] = code
            code_lengths[symbol] = length
        
        # Кодируем данные
        encoded_bits = ""
        for symbol in data:
            encoded_bits += codes[symbol]
        
        # Преобразуем битовую строку в байты
        padding = 8 - len(encoded_bits) % 8
        if padding == 8:
            padding = 0
        encoded_bits += '0' * padding
        
        encoded_bytes = bytearray()
        for i in range(0, len(encoded_bits), 8):
            byte_str = encoded_bits[i:i+8]
            encoded_bytes.append(int(byte_str, 2))
        
        return bytes(encoded_bytes), padding, codes, code_lengths
    
    def format_size(self, size):
        """Форматирует размер файла в читаемом виде"""
        if size == 0:
            return "0 B"
        units = ['байт', 'КБ', 'МБ', 'ГБ']
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        return f"{size:.2f} {units[unit_index]}"
    
    def compress_file(self, input_file):
        """Сжимает файл методом Шеннона"""
        try:
            print("Начинаем сжатие методом Шеннона...")
            output_file = f"{input_file}.klusha"
            
            # Читаем исходный файл
            print(f"Чтение файла: {input_file}")
            with open(input_file, 'rb') as f:
                original_data = f.read()
            
            original_size = len(original_data)
            print(f"Прочитано: {original_size} байт")
            
            if original_size == 0:
                # Пустой файл
                print("Файл пустой, создаем минимальный архив...")
                encoded_data = b''
                padding_bits = 0
                frequencies = {}
                probabilities = {}
                cumulative = {}
                sorted_symbols = []
                codes = {}
                code_lengths = {}
                tree_data = b''
                entropy = 0
                total_bits_estimate = 0
                average_code_length = 0
            else:
                # Строим таблицы вероятностей
                print("Построение таблицы вероятностей...")
                frequencies, probabilities, cumulative, total_count, sorted_symbols = self.build_probability_table(original_data)
                print(f"Уникальных символов: {len(frequencies)}")
                
                # Вычисляем энтропию для оценки
                entropy = self.calculate_entropy(frequencies, total_count)
                total_bits_estimate = entropy * total_count
                
                # Кодируем данные
                print("Кодирование методом Шеннона...")
                encoded_data, padding_bits, codes, code_lengths = self.shannon_encode(
                    original_data, probabilities, cumulative, sorted_symbols
                )
                print(f"Закодировано: {len(encoded_data)} байт")
                
                # Вычисляем среднюю длину кода
                total_coded_bits = sum(frequencies[symbol] * code_lengths[symbol] for symbol in frequencies)
                average_code_length = total_coded_bits / total_count if total_count > 0 else 0
                
                # Подготавливаем данные о дереве (таблицу частот и кодов)
                tree_data = bytearray()
                
                # Записываем количество уникальных символов (2 байта)
                unique_count = len(frequencies)
                tree_data.extend(struct.pack('<H', unique_count))
                
                # Записываем общее количество символов (8 байт)
                tree_data.extend(struct.pack('<Q', total_count))
                
                # Записываем пары (символ, частота, длина кода)
                for symbol in sorted_symbols:
                    tree_data.append(symbol)
                    tree_data.extend(struct.pack('<I', frequencies[symbol]))
                    tree_data.extend(struct.pack('<B', code_lengths[symbol]))
            
            tree_size = len(tree_data)
            compressed_data_size = len(encoded_data)
            actual_bits = compressed_data_size * 8 - padding_bits
            
            print(f"Запись сжатого файла: {output_file}")
            # Записываем сжатый файл
            with open(output_file, 'wb') as f:
                # Заголовок (24 байта)
                f.write(self.signature)  # 6 байт
                f.write(bytes([self.major_version]))  # 1 байт
                f.write(bytes([self.minor_version]))  # 1 байт
                f.write(bytes([self.context_algorithm]))  # 1 байт
                f.write(bytes([self.context_free]))  # 1 байт
                f.write(bytes([self.error_protection]))  # 1 байт
                f.write(self.reserved)  # 5 байт
                
                # Исходная длина файла (8 байт, little-endian)
                f.write(struct.pack('<Q', original_size))
                
                # Размер служебных данных (4 байта, little-endian)
                f.write(struct.pack('<I', tree_size))
                
                # Количество бит дополнения (1 байт)
                f.write(bytes([padding_bits]))
                
                # Служебные данные (таблица частот и длин кодов)
                f.write(tree_data)
                
                # Закодированные данные
                f.write(encoded_data)
            
            compressed_size = os.path.getsize(output_file)
            
            # Вывод результатов
            print("\n" + "=" * 70)
            print("КОДЕР ШЕННОНА - РЕЗУЛЬТАТЫ")
            print("=" * 70)
            print(f"Входной файл: {input_file}")
            print(f"Выходной файл: {output_file}")
            print(f"Версия формата: {self.major_version}.{self.minor_version}")
            print(f"Алгоритм сжатия: {self.context_algorithm} (метод Шеннона)")
            print()
            
            print("РАЗМЕРЫ ФАЙЛОВ:")
            print(f"  Исходный размер: {self.format_size(original_size)}")
            print(f"  Сжатый размер: {self.format_size(compressed_size)}")
            
            if original_size > 0:
                compression_ratio = compressed_size / original_size * 100
                savings = 100 - compression_ratio
                print(f"  Коэффициент сжатия: {compression_ratio:.2f}%")
                print(f"  Экономия: {savings:.2f}%")
            
            print()
            print("ТЕОРЕТИЧЕСКИЕ ОЦЕНКИ:")
            if original_size > 0:
                print(f"  Энтропия Шеннона: {entropy:.4f} бит/символ")
                print(f"  Оценка информации: {total_bits_estimate:.2f} бит")
                print(f"  Средняя длина кода Шеннона: {average_code_length:.4f} бит/символ")
                print(f"  Избыточность кодирования: {average_code_length - entropy:.4f} бит/символ")
                
                efficiency = entropy / average_code_length * 100 if average_code_length > 0 else 0
                print(f"  Эффективность кодирования: {efficiency:.2f}%")
            
            print()
            print("ФАКТИЧЕСКИЕ РЕЗУЛЬТАТЫ:")
            print(f"  Фактическая длина: {actual_bits} бит")
            print(f"  Размер таблицы частот: {tree_size} байт")
            print(f"  Биты дополнения: {padding_bits}")
            print(f"  Уникальных символов: {len(frequencies)}")
            
            if original_size > 0:
                actual_bits_per_symbol = actual_bits / original_size
                print(f"  Фактическая длина на символ: {actual_bits_per_symbol:.4f} бит")
                
                # Сравнение с теорией
                print()
                print("СРАВНЕНИЕ С ТЕОРИЕЙ:")
                print(f"  Энтропия:                    {entropy:.4f} бит/символ")
                print(f"  Теория Шеннона (ceil(-log2 p)): {average_code_length:.4f} бит/символ")
                print(f"  Фактически:                 {actual_bits_per_symbol:.4f} бит/символ")
                
                if actual_bits_per_symbol > 0:
                    total_efficiency = total_bits_estimate / actual_bits * 100
                    print(f"  Общая эффективность: {total_efficiency:.2f}%")
            
            # Вывод кодов символов для маленьких файлов
            if original_size > 0 and original_size < 100:
                print()
                print("КОДЫ СИМВОЛОВ (первые 10):")
                print(f"{'Символ':<10} {'Вероятность':<12} {'Кумулятивная':<12} {'Длина':<8} {'Код':<15}")
                print("-" * 60)
                
                count = 0
                for symbol in sorted_symbols:
                    if count >= 10:
                        break
                    
                    # Представление символа
                    if 32 <= symbol <= 126:
                        char_repr = f"'{chr(symbol)}'"
                    else:
                        char_repr = f"0x{symbol:02X}"
                    
                    prob = float(probabilities[symbol])
                    cum_prob = float(cumulative[symbol])
                    length = code_lengths[symbol]
                    code = codes[symbol]
                    
                    print(f"{char_repr:<10} {prob:<12.6f} {cum_prob:<12.6f} {length:<8} {code:<15}")
                    count += 1
            
            print("=" * 70)
            print("\n✓ Сжатие методом Шеннона завершено успешно!")
            
        except MemoryError:
            print("\n✗ Ошибка: Недостаточно памяти для обработки файла")
            print("  Попробуйте использовать файл меньшего размера")
        except KeyboardInterrupt:
            print("\n✗ Операция прервана пользователем")
        except Exception as e:
            print(f"\n✗ Ошибка при сжатии: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Главная функция кодировщика Шеннона"""
    if len(sys.argv) != 2:
        print("Использование: python shannon_encoder.py <имя_файла>")
        print()
        print("Примеры:")
        print("  python shannon_encoder.py document.txt")
        print("  python shannon_encoder.py image.jpg")
        print()
        print("Создайте тестовый файл для проверки:")
        print('  echo "Hello, World!" > test.txt')
        print("  python shannon_encoder.py test.txt")
        return
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"✗ Ошибка: Файл '{input_file}' не найден")
        print(f"  Текущая директория: {os.getcwd()}")
        return
    
    # Проверяем размер файла
    file_size = os.path.getsize(input_file)
    if file_size > 100 * 1024 * 1024:  # 100 МБ
        print(f"⚠  Предупреждение: Файл очень большой ({file_size:,} байт)")
        response = input("  Продолжить? (y/n): ")
        if response.lower() != 'y':
            print("Отменено пользователем")
            return
    
    encoder = ShannonEncoder()
    encoder.compress_file(input_file)

if __name__ == "__main__":
    main()