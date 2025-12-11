import struct
import os
import sys
import math
from collections import Counter
from decimal import Decimal, getcontext

# Установим высокую точность для Decimal
getcontext().prec = 128

class ArithmeticEncoder:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
        self.major_version = 1
        self.minor_version = 3  # Изменено на 3
        self.context_algorithm = 3  # Арифметическое кодирование
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
        
        # Сортируем символы для детерминированного порядка
        sorted_symbols = sorted(frequencies.keys())
        
        # Вычисляем вероятности и кумулятивные суммы
        cum_prob = Decimal('0')
        for symbol in sorted_symbols:
            prob = Decimal(frequencies[symbol]) / Decimal(total_count)
            probabilities[symbol] = prob
            cumulative[symbol] = cum_prob
            cum_prob += prob
        
        return frequencies, probabilities, cumulative, total_count
    
    def arithmetic_encode(self, data, probabilities, cumulative):
        """арифметическое кодирование с фиксированным количеством битов"""
        low = Decimal('0')
        high = Decimal('1')
        
        for symbol in data:
            range_width = high - low
            high = low + range_width * (cumulative[symbol] + probabilities[symbol])
            low = low + range_width * cumulative[symbol]
        
        # Выбираем число из последнего интервала
        # Берем середину интервала для простоты
        result = (low + high) / Decimal('2')
        
        # Вмеwhile True:меняем сложную логику на фиксированное количество битов
        # Вычисляем необходимое количество битов: -log2(длина_интервала) + запас
        interval_length = high - low
        if interval_length == Decimal('0'):
            # Если интервал нулевой (все символы одинаковы), нужно минимальное количество битов
            required_bits = 1
        else:
            # Теоретически необходимое количество битов + запас
            required_bits = int(-math.log2(float(interval_length))) + 2
        
        # Генерируем битовую строку
        bit_string = ""
        value = result
        
        for _ in range(required_bits):
            value *= Decimal('2')
            if value >= Decimal('1'):
                bit_string += '1'
                value -= Decimal('1')
            else:
                bit_string += '0'
        
        # Преобразуем битовую строку в байты
        padding = 8 - len(bit_string) % 8
        if padding == 8:
            padding = 0
        bit_string += '0' * padding
        
        encoded_bytes = bytearray()
        for i in range(0, len(bit_string), 8):
            byte_str = bit_string[i:i+8]
            encoded_bytes.append(int(byte_str, 2))
        
        return bytes(encoded_bytes), padding, result, low, high, required_bits
    
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
        """Сжимает файл арифметическим кодированием"""
        try:
            print("Начинаем сжатие...")
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
                encoded_value = Decimal('0')
                tree_data = b''
                final_low = Decimal('0')
                final_high = Decimal('1')
                entropy = 0
                total_bits_estimate = 0
                required_bits = 0
            else:
                # Строим таблицы вероятностей
                print("Построение таблицы вероятностей...")
                frequencies, probabilities, cumulative, total_count = self.build_probability_table(original_data)
                print(f"Уникальных символов: {len(frequencies)}")
                
                # Вычисляем энтропию для оценки
                entropy = self.calculate_entropy(frequencies, total_count)
                total_bits_estimate = entropy * total_count
                
                # Кодируем данные
                print("Арифметическое кодирование...")
                encoded_data, padding_bits, encoded_value, final_low, final_high, required_bits = self.arithmetic_encode(
                    original_data, probabilities, cumulative
                )
                print(f"Закодировано: {len(encoded_data)} байт")
                
                # Подготавливаем данные о дереве (таблицу частот)
                tree_data = bytearray()
                
                # Записываем количество уникальных символов (2 байта)
                unique_count = len(frequencies)
                tree_data.extend(struct.pack('<H', unique_count))
                
                # Записываем общее количество символов (8 байт)
                tree_data.extend(struct.pack('<Q', total_count))
                
                # Записываем пары (символ, частота)
                for symbol, freq in sorted(frequencies.items()):
                    tree_data.append(symbol)
                    tree_data.extend(struct.pack('<I', freq))
            
            tree_size = len(tree_data)
            compressed_data_size = len(encoded_data)
            
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
                
                # Закодированное значение
                encoded_str = str(encoded_value)
                encoded_value_bytes = encoded_str.encode('utf-8')
                f.write(struct.pack('<H', len(encoded_value_bytes)))
                f.write(encoded_value_bytes)
                
                # Служебные данные (таблица частот)
                f.write(tree_data)
                
                # Закодированные данные
                f.write(encoded_data)
            
            compressed_size = os.path.getsize(output_file)
            
            # Вывод результатов
            print("\n" + "=" * 60)
            print("АРИФМЕТИЧЕСКИЙ КОДЕР - РЕЗУЛЬТАТЫ")
            print("=" * 60)
            print(f"Входной файл: {input_file}")
            print(f"Выходной файл: {output_file}")
            print(f"Версия формата: {self.major_version}.{self.minor_version}")
            print(f"Алгоритм сжатия: {self.context_algorithm} (арифметическое кодирование)")
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
            print("ОЦЕНКИ ИНФОРМАЦИИ:")
            if original_size > 0:
                print(f"  Энтропия Шеннона: {entropy:.4f} бит/символ")
                print(f"  Оценка информации: {total_bits_estimate:.2f} бит")
                print(f"  Фактическая длина: {compressed_data_size * 8 - padding_bits} бит")
                print(f"  Теоретически необходимо битов: {required_bits}")
                
                # Длина архива = сжатые данные + таблица частот
                archive_bits = (compressed_data_size * 8 - padding_bits) + tree_size * 8
                print(f"  Длина архива (без заголовка): {archive_bits:.2f} бит")
                
                # Теоретическая нижняя оценка
                lower_bound = total_bits_estimate
                print(f"  Нижняя оценка (теоретическая): {lower_bound:.2f} бит")
                
                if archive_bits > 0:
                    efficiency = lower_bound / archive_bits * 100
                    print(f"  Эффективность: {efficiency:.2f}%")
            
            print()
            print("ДЕТАЛИ КОДИРОВАНИЯ:")
            print(f"  Уникальных символов: {len(frequencies)}")
            print(f"  Общее количество символов: {original_size}")
            print(f"  Биты дополнения: {padding_bits}")
            print(f"  Размер таблицы частот: {tree_size} байт")
            
            if original_size > 0:
                print(f"  Конечный интервал: [{float(final_low):.15f}, {float(final_high):.15f})")
                print(f"  Длина интервала: {float(final_high - final_low):.15e}")
            
            print("=" * 60)
            print("\n✓ Сжатие завершено успешно!")
            
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
    """Главная функция кодировщика"""
    if len(sys.argv) != 2:
        print("Использование: python arithmetic_encoder.py <имя_файла>")
        print()
        print("Примеры:")
        print("  python arithmetic_encoder.py document.txt")
        print("  python arithmetic_encoder.py image.jpg")
        print()
        print("Создайте тестовый файл для проверки:")
        print('  echo "Hello, World!" > test.txt')
        print("  python arithmetic_encoder.py test.txt")
        return
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"✗ Ошибка: Файл '{input_file}' не найден")
        print(f"  Текущая директория: {os.getcwd()}")
        print(f"  Содержимое директории:")
        for file in os.listdir('.'):
            print(f"    {file}")
        return
    
    # Проверяем размер файла
    file_size = os.path.getsize(input_file)
    if file_size > 100 * 1024 * 1024:  # 100 МБ
        print(f"⚠  Предупреждение: Файл очень большой ({file_size:,} байт)")
        print("  Это может занять много времени и памяти")
        response = input("  Продолжить? (y/n): ")
        if response.lower() != 'y':
            print("Отменено пользователем")
            return
    
    encoder = ArithmeticEncoder()
    encoder.compress_file(input_file)

if __name__ == "__main__":
    main()