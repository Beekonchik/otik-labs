import struct
import os
import sys
import math
from decimal import Decimal, getcontext

# Установим высокую точность для Decimal
getcontext().prec = 128

class ArithmeticDecoder:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
        self.expected_major_version = 1
        self.expected_minor_version = 3
        self.expected_context_algorithm = 3
    
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
    
    def validate_header(self, header_data):
        """Проверяет корректность заголовка файла"""
        if len(header_data) < 24:
            print("✗ Ошибка: Заголовок файла слишком короткий")
            return False
        
        # Проверяем сигнатуру
        signature = header_data[0:6]
        if signature != self.signature:
            print("✗ Ошибка: Неверная сигнатура")
            print(f"  Ожидается: {self.signature.hex()}")
            print(f"  Получено:  {signature.hex()}")
            return False
        
        print("✓ Сигнатура: klusha")
        
        # Проверяем версию
        major_version = header_data[6]
        minor_version = header_data[7]
        
        # Проверка мажорной версии
        if major_version != self.expected_major_version:
            print(f"✗ Ошибка: Неподдерживаемая мажорная версия")
            print(f"  Ожидается: {self.expected_major_version}")
            print(f"  Получено:  {major_version}")
            return False
        
        # Проверка минорной версии
        if minor_version != self.expected_minor_version:
            print(f"⚠  Внимание: Минорная версия отличается")
            print(f"   Ожидается: {self.expected_minor_version}")
            print(f"   Получено:  {minor_version}")
            
            # Проверяем совместимость версий
            if minor_version < 3:
                print("   ✗ Версия несовместима, прекращаем работу")
                return False
            else:
                print("   → Версия совместима, продолжаем...")
        
        print(f"✓ Версия формата: {major_version}.{minor_version}")
        
        # Проверяем алгоритм сжатия
        context_algorithm = header_data[8]
        if context_algorithm != self.expected_context_algorithm:
            print(f"✗ Ошибка: Неподдерживаемый алгоритм сжатия")
            print(f"  Ожидается: {self.expected_context_algorithm} (арифметическое кодирование)")
            print(f"  Получено:  {context_algorithm}")
            return False
        
        print(f"✓ Алгоритм сжатия: Арифметическое кодирование")
        
        return True
    
    def parse_probability_table(self, tree_data):
        """Восстанавливает таблицу вероятностей из данных дерева"""
        if len(tree_data) < 10:
            return {}, {}, {}, 0
        
        offset = 0
        unique_count = struct.unpack('<H', tree_data[offset:offset+2])[0]
        offset += 2
        
        total_count = struct.unpack('<Q', tree_data[offset:offset+8])[0]
        offset += 8
        
        frequencies = {}
        actual_total = 0
        
        for _ in range(unique_count):
            if offset >= len(tree_data):
                raise ValueError("Недостаточно данных для чтения таблицы частот")
            
            symbol = tree_data[offset]
            offset += 1
            
            if offset + 4 > len(tree_data):
                raise ValueError("Недостаточно данных для чтения частоты")
            
            freq = struct.unpack('<I', tree_data[offset:offset+4])[0]
            offset += 4
            
            frequencies[symbol] = freq
            actual_total += freq
        
        if actual_total != total_count and total_count > 0:
            print(f"⚠  Предупреждение: Общее количество символов не совпадает")
            print(f"   Заявлено: {total_count}, фактически: {actual_total}")
            total_count = actual_total
        
        probabilities = {}
        cumulative = {}
        
        sorted_symbols = sorted(frequencies.keys())
        cum_prob = Decimal('0')
        
        for symbol in sorted_symbols:
            if total_count > 0:
                prob = Decimal(frequencies[symbol]) / Decimal(total_count)
            else:
                prob = Decimal('0')
            probabilities[symbol] = prob
            cumulative[symbol] = cum_prob
            cum_prob += prob
        
        return frequencies, probabilities, cumulative, total_count
    
    def calculate_required_bits(self, encoded_data, padding_bits):
        """Вычисляет количество битов, сгенерированных кодером"""
        # Кодер генерировал биты до тех пор, пока не создал достаточное количество
        # Нам нужно знать, сколько именно битов было сгенерировано
        total_bits = len(encoded_data) * 8 - padding_bits
        return total_bits
    
    def bits_to_decimal(self, bit_string):
        """Преобразует битовую строку в Decimal число"""
        value = Decimal('0')
        power = Decimal('0.5')
        
        for bit in bit_string:
            if bit == '1':
                value += power
            power /= Decimal('2')
        
        return value
    
    def arithmetic_decode(self, encoded_bits, probabilities, cumulative, original_length, padding_bits, total_bits):
        """арифметическое декодирование с учетом количества битов"""
        # Преобразуем байты в битовую строку
        bit_string = ''
        for byte in encoded_bits:
            bit_string += format(byte, '08b')
        
        # Убираем биты дополнения
        if padding_bits > 0:
            bit_string = bit_string[:-padding_bits]
        
        # Ограничиваем строку количеством битов, которые сгенерировал кодер
        if len(bit_string) > total_bits:
            bit_string = bit_string[:total_bits]
        elif len(bit_string) < total_bits:
            # Если битов меньше, чем заявлено, добавляем нули
            bit_string += '0' * (total_bits - len(bit_string))
        
        if not bit_string:
            return b''
        
        # Преобразуем битовую строку обратно в Decimal число
        value = self.bits_to_decimal(bit_string)
        
        # Выполняем декодирование
        decoded_data = bytearray()
        low = Decimal('0')
        high = Decimal('1')
        
        for _ in range(original_length):
            # Находим символ, соответствующий текущему значению
            range_width = high - low
            if range_width == Decimal('0'):
                # Если интервал нулевой (все символы одинаковы)
                symbol = list(cumulative.keys())[0]
            else:
                current = (value - low) / range_width
                
                # Ищем символ, чей кумулятивный интервал содержит current
                symbol = None
                for sym, cum_prob in cumulative.items():
                    prob = probabilities[sym]
                    # Учитываем границы интервалов
                    if cum_prob <= current < cum_prob + prob:
                        symbol = sym
                        break
                    # Обрабатываем граничный случай
                    elif current == cum_prob + prob and sym == list(cumulative.keys())[-1]:
                        symbol = sym
                        break
                
                if symbol is None:
                    # Для отладки
                    print(f"Отладка: current={current}, cumulative={cumulative}")
                    raise ValueError(f"Не найден символ для значения {current}")
            
            decoded_data.append(symbol)
            
            # Обновляем интервал
            high = low + range_width * (cumulative[symbol] + probabilities[symbol])
            low = low + range_width * cumulative[symbol]
        
        return bytes(decoded_data)
    
    def decompress_file(self, input_file):
        """Разжимает файл, сжатый арифметическим кодированием"""
        try:
            print("=" * 60)
            print("АРИФМЕТИЧЕСКИЙ ДЕКОДЕР")
            print("=" * 60)
            print(f"Входной файл: {input_file}")
            
            if not os.path.exists(input_file):
                print(f"✗ Ошибка: Файл не найден")
                return
            
            # Генерируем имя выходного файла
            base_name = input_file.replace('.klusha', '')
            
            if '.' in base_name and not base_name.endswith('_restored'):
                name_parts = base_name.rsplit('.', 1)
                if len(name_parts) == 2:
                    output_file = f"{name_parts[0]}_restored.{name_parts[1]}"
                else:
                    output_file = f"{base_name}_restored"
            else:
                output_file = f"{base_name}_restored"
            
            print(f"Выходной файл: {output_file}")
            
            # Читаем сжатый файл
            print("\nЧтение и проверка заголовка...")
            with open(input_file, 'rb') as f:
                # Читаем заголовок
                header_data = f.read(24)
                if not self.validate_header(header_data):
                    print("\n✗ Работа прекращена из-за ошибки в заголовке")
                    return
                
                # Извлекаем данные из заголовка
                original_size = struct.unpack('<Q', header_data[16:24])[0]
                print(f"✓ Исходный размер: {self.format_size(original_size)}")
                
                # Читаем размер служебных данных
                tree_size_data = f.read(4)
                if len(tree_size_data) < 4:
                    raise ValueError("Не удалось прочитать размер служебных данных")
                tree_size = struct.unpack('<I', tree_size_data)[0]
                print(f"✓ Размер таблицы частот: {tree_size} байт")
                
                # Читаем количество бит дополнения
                padding_bits_data = f.read(1)
                if len(padding_bits_data) < 1:
                    raise ValueError("Не удалось прочитать биты дополнения")
                padding_bits = padding_bits_data[0]
                print(f"✓ Биты дополнения: {padding_bits}")
                
                # Читаем закодированное значение
                encoded_value_len_data = f.read(2)
                if len(encoded_value_len_data) < 2:
                    raise ValueError("Не удалось прочитать длину закодированного значения")
                encoded_value_len = struct.unpack('<H', encoded_value_len_data)[0]
                
                encoded_value_bytes = f.read(encoded_value_len)
                if len(encoded_value_bytes) != encoded_value_len:
                    raise ValueError("Не удалось прочитать закодированное значение")
                
                encoded_value_str = encoded_value_bytes.decode('utf-8')
                encoded_value = Decimal(encoded_value_str)
                print(f"✓ Закодированное значение: {encoded_value}")
                
                # Читаем служебные данные (таблицу частот)
                tree_data = f.read(tree_size)
                if len(tree_data) != tree_size:
                    raise ValueError(f"Не удалось прочитать все служебные данные: получено {len(tree_data)} байт из {tree_size}")
                
                print(f"✓ Таблица частот прочитана")
                
                # Читаем закодированные данные
                encoded_data = f.read()
                print(f"✓ Закодированные данные: {len(encoded_data)} байт")
            
            # Восстанавливаем таблицу вероятностей
            print("\nВосстановление таблицы вероятностей...")
            frequencies, probabilities, cumulative, total_count = self.parse_probability_table(tree_data)
            
            print(f"✓ Уникальных символов: {len(frequencies)}")
            print(f"✓ Общее количество символов: {total_count}")
            
            # Вычисляем количество битов, которое сгенерировал кодер
            # В кодере используется формула: int(-math.log2(float(high - low))) + 2
            # Но так как мы не знаем high-low, будем использовать длину данных
            total_bits = len(encoded_data) * 8 - padding_bits
            print(f"✓ Расчетное количество битов: {total_bits}")
            
            # Декодируем данные
            print("\nДекодирование данных...")
            if original_size == 0:
                decoded_data = b''
                print("✓ Файл пустой")
            else:
                decoded_data = self.arithmetic_decode(
                    encoded_data, probabilities, cumulative, original_size, padding_bits, total_bits
                )
                print(f"✓ Данные успешно декодированы: {len(decoded_data)} байт")
            
            # Проверяем размер декодированных данных
            if len(decoded_data) != original_size:
                print(f"\n⚠  Предупреждение: Размер декодированных данных не совпадает")
                print(f"   Ожидалось: {original_size} байт")
                print(f"   Получено:  {len(decoded_data)} байт")
                # Продолжаем, но с предупреждением
            
            # Записываем разжатый файл
            print(f"\nЗапись выходного файла...")
            with open(output_file, 'wb') as f:
                f.write(decoded_data)
            
            restored_size = os.path.getsize(output_file)
            
            print("\n" + "=" * 60)
            print("РЕЗУЛЬТАТ ДЕКОДИРОВАНИЯ")
            print("=" * 60)
            print(f"✓ Файл успешно восстановлен")
            print(f"  Входной файл:  {input_file}")
            print(f"  Выходной файл: {output_file}")
            print(f"  Исходный размер: {self.format_size(original_size)}")
            print(f"  Размер после восстановления: {self.format_size(restored_size)}")
            
            if original_size == restored_size:
                print(f"  ✓ Размеры совпадают")
            else:
                print(f"  ⚠  Размеры не совпадают")
            
            print("=" * 60)
            print("\n✓ Разжатие завершено успешно!")
            
        except FileNotFoundError:
            print(f"\n✗ Ошибка: Файл {input_file} не найден")
        except ValueError as e:
            print(f"\n✗ Ошибка проверки данных: {e}")
        except KeyboardInterrupt:
            print("\n✗ Операция прервана пользователем")
        except Exception as e:
            print(f"\n✗ Ошибка при разжатии: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Главная функция декодировщика"""
    if len(sys.argv) != 2:
        print("Использование: python arithmetic_decoder.py <имя_файла.klusha>")
        print()
        print("Примеры:")
        print("  python arithmetic_decoder.py document.txt.klusha")
        print("  python arithmetic_decoder.py image.jpg.klusha")
        print()
        print("Сначала создайте сжатый файл:")
        print('  echo "Test data" > test.txt')
        print("  python arithmetic_encoder.py test.txt")
        print("  python arithmetic_decoder.py test.txt.klusha")
        return
    
    input_file = sys.argv[1]
    
    if not input_file.endswith('.klusha'):
        print(f"⚠  Внимание: Обычно файлы имеют расширение .klusha")
        print(f"   Вы указали: {input_file}")
        response = input("   Продолжить? (y/n): ")
        if response.lower() != 'y':
            print("Отменено пользователем")
            return
    
    decoder = ArithmeticDecoder()
    decoder.decompress_file(input_file)

if __name__ == "__main__":
    main()