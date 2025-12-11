import struct
import os
import sys
from decimal import Decimal, getcontext

# Установим высокую точность для Decimal
getcontext().prec = 128

class ShannonDecoder:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])  # "klusha"
        self.expected_major_version = 1
        self.expected_minor_version = 4  # Версия для метода Шеннона
        self.expected_context_algorithm = 4  # Код алгоритма Шеннона
    
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
            if minor_version < 4:
                print("   ✗ Версия несовместима, прекращаем работу")
                return False
            else:
                print("   → Версия совместима, продолжаем...")
        
        print(f"✓ Версия формата: {major_version}.{minor_version}")
        
        # Проверяем алгоритм сжатия
        context_algorithm = header_data[8]
        if context_algorithm != self.expected_context_algorithm:
            print(f"✗ Ошибка: Неподдерживаемый алгоритм сжатия")
            print(f"  Ожидается: {self.expected_context_algorithm} (метод Шеннона)")
            print(f"  Получено:  {context_algorithm}")
            return False
        
        print(f"✓ Алгоритм сжатия: Метод Шеннона")
        
        return True
    
    def parse_probability_table(self, tree_data):
        """Восстанавливает таблицу вероятностей и кодов из данных дерева"""
        if len(tree_data) < 10:
            return {}, {}, {}, {}, 0
        
        offset = 0
        unique_count = struct.unpack('<H', tree_data[offset:offset+2])[0]
        offset += 2
        
        total_count = struct.unpack('<Q', tree_data[offset:offset+8])[0]
        offset += 8
        
        frequencies = {}
        code_lengths = {}
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
            
            if offset + 1 > len(tree_data):
                raise ValueError("Недостаточно данных для чтения длины кода")
            
            length = struct.unpack('<B', tree_data[offset:offset+1])[0]
            offset += 1
            
            frequencies[symbol] = freq
            code_lengths[symbol] = length
            actual_total += freq
        
        if actual_total != total_count and total_count > 0:
            print(f"⚠  Предупреждение: Общее количество символов не совпадает")
            print(f"   Заявлено: {total_count}, фактически: {actual_total}")
            total_count = actual_total
        
        # Сортируем символы по убыванию частоты (как в кодере)
        sorted_symbols = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
        sorted_symbols = [symbol for symbol, _ in sorted_symbols]
        
        # Строим таблицы вероятностей и кумулятивных сумм
        probabilities = {}
        cumulative = {}
        cum_prob = Decimal('0')
        
        for symbol in sorted_symbols:
            if total_count > 0:
                prob = Decimal(frequencies[symbol]) / Decimal(total_count)
            else:
                prob = Decimal('0')
            probabilities[symbol] = prob
            cumulative[symbol] = cum_prob
            cum_prob += prob
        
        # Восстанавливаем коды Шеннона
        codes = {}
        for symbol in sorted_symbols:
            code, _ = self.shannon_encode_symbol(
                probabilities[symbol], 
                cumulative[symbol],
                code_lengths[symbol]
            )
            codes[symbol] = code
        
        return frequencies, probabilities, cumulative, codes, code_lengths, total_count, sorted_symbols
    
    def shannon_encode_symbol(self, probability, cumulative_prob, code_length):
        """Восстанавливает код символа методом Шеннона (как в кодере)"""
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
    
    def build_prefix_tree(self, codes):
        """Строит префиксное дерево из кодов Шеннона"""
        root = {}
        
        for symbol, code in codes.items():
            node = root
            for bit in code:
                if bit not in node:
                    node[bit] = {}
                node = node[bit]
            node['symbol'] = symbol
        
        return root
    
    def shannon_decode(self, encoded_bits, codes, original_length, padding_bits):
        """Выполняет декодирование методом Шеннона"""
        # Преобразуем байты в битовую строку
        bit_string = ''
        for byte in encoded_bits:
            bit_string += format(byte, '08b')
        
        # Убираем биты дополнения
        if padding_bits > 0:
            bit_string = bit_string[:-padding_bits]
        
        if not bit_string:
            return b''
        
        # Строим префиксное дерево для быстрого декодирования
        prefix_tree = self.build_prefix_tree(codes)
        
        # Декодируем данные
        decoded_data = bytearray()
        node = prefix_tree
        bits_processed = 0
        
        for bit in bit_string:
            if bit in node:
                node = node[bit]
                bits_processed += 1
                
                # Проверяем, достигли ли мы символа
                if 'symbol' in node:
                    decoded_data.append(node['symbol'])
                    
                    # Проверяем, не декодировали ли мы всё
                    if len(decoded_data) >= original_length:
                        break
                    
                    # Начинаем с корня для следующего символа
                    node = prefix_tree
            else:
                # Это не должно происходить при корректных данных
                raise ValueError(f"Неверный бит в позиции {bits_processed}")
        
        # Проверяем, что декодировали все символы
        if len(decoded_data) != original_length:
            print(f"⚠  Предупреждение: Декодировано {len(decoded_data)} символов, ожидалось {original_length}")
            print(f"   Обработано битов: {bits_processed} из {len(bit_string)}")
        
        return bytes(decoded_data)
    
    def decompress_file(self, input_file):
        """Разжимает файл, сжатый методом Шеннона"""
        try:
            print("=" * 60)
            print("ДЕКОДЕР ШЕННОНА")
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
                
                # Читаем служебные данные (таблицу частот и длин кодов)
                tree_data = f.read(tree_size)
                if len(tree_data) != tree_size:
                    raise ValueError(f"Не удалось прочитать все служебные данные: получено {len(tree_data)} байт из {tree_size}")
                
                print(f"✓ Таблица частот прочитана")
                
                # Читаем закодированные данные
                encoded_data = f.read()
                print(f"✓ Закодированные данные: {len(encoded_data)} байт")
            
            # Восстанавливаем таблицу вероятностей и коды
            print("\nВосстановление таблицы вероятностей и кодов...")
            frequencies, probabilities, cumulative, codes, code_lengths, total_count, sorted_symbols = self.parse_probability_table(tree_data)
            
            print(f"✓ Уникальных символов: {len(frequencies)}")
            print(f"✓ Общее количество символов: {total_count}")
            
            # Декодируем данные
            print("\nДекодирование данных...")
            if original_size == 0:
                decoded_data = b''
                print("✓ Файл пустой")
            else:
                decoded_data = self.shannon_decode(
                    encoded_data, codes, original_size, padding_bits
                )
                print(f"✓ Данные успешно декодированы: {len(decoded_data)} байт")
            
            # Проверяем размер декодированных данных
            if len(decoded_data) != original_size:
                print(f"\n⚠  Предупреждение: Размер декодированных данных не совпадает")
                print(f"   Ожидалось: {original_size} байт")
                print(f"   Получено:  {len(decoded_data)} байт")
            
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
            
            # Вывод информации о кодах для маленьких файлов
            if original_size > 0 and original_size < 100:
                print()
                print("ВОССТАНОВЛЕННЫЕ КОДЫ (первые 10):")
                print(f"{'Символ':<10} {'Частота':<10} {'Длина кода':<12} {'Код':<15}")
                print("-" * 50)
                
                count = 0
                for symbol in sorted_symbols:
                    if count >= 10:
                        break
                    
                    # Представление символа
                    if 32 <= symbol <= 126:
                        char_repr = f"'{chr(symbol)}'"
                    else:
                        char_repr = f"0x{symbol:02X}"
                    
                    freq = frequencies[symbol]
                    length = code_lengths[symbol]
                    code = codes[symbol]
                    
                    print(f"{char_repr:<10} {freq:<10} {length:<12} {code:<15}")
                    count += 1
            
            print("=" * 60)
            print("\n✓ Разжатие методом Шеннона завершено успешно!")
            
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
    """Главная функция декодировщика Шеннона"""
    if len(sys.argv) != 2:
        print("Использование: python shannon_decoder.py <имя_файла.klusha>")
        print()
        print("Примеры:")
        print("  python shannon_decoder.py document.txt.klusha")
        print("  python shannon_decoder.py image.jpg.klusha")
        print()
        print("Сначала создайте сжатый файл:")
        print('  echo "Test data for Shannon coding" > test.txt')
        print("  python shannon_encoder.py test.txt")
        print("  python shannon_decoder.py test.txt.klusha")
        return
    
    input_file = sys.argv[1]
    
    if not input_file.endswith('.klusha'):
        print(f"⚠  Внимание: Обычно файлы имеют расширение .klusha")
        print(f"   Вы указали: {input_file}")
        response = input("   Продолжить? (y/n): ")
        if response.lower() != 'y':
            print("Отменено пользователем")
            return
    
    decoder = ShannonDecoder()
    decoder.decompress_file(input_file)

if __name__ == "__main__":
    main()