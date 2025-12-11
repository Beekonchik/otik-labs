import heapq
from collections import Counter, defaultdict
import math
import os
import sys
import argparse

class HuffmanNode:
    def __init__(self, symbol=None, freq=0):
        self.symbol = symbol
        self.freq = freq
        self.left = None
        self.right = None
    
    def __lt__(self, other):
        return self.freq < other.freq

def build_huffman_tree(frequencies):
    """Построение дерева Хаффмана по частотам символов"""
    heap = [HuffmanNode(symbol, freq) for symbol, freq in frequencies.items() if freq > 0]
    heapq.heapify(heap)
    
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = HuffmanNode(freq=left.freq + right.freq)
        merged.left = left
        merged.right = right
        heapq.heappush(heap, merged)
    
    return heap[0] if heap else None

def generate_codes(node, current_code="", codes=None):
    """Генерация кодов Хаффмана для всех символов"""
    if codes is None:
        codes = {}
    
    if node is None:
        return codes
    
    if node.symbol is not None:
        codes[node.symbol] = current_code
        return codes
    
    generate_codes(node.left, current_code + "0", codes)
    generate_codes(node.right, current_code + "1", codes)
    
    return codes

def calculate_compressed_length(frequencies, codes):
    """Расчет длины сжатых данных в битах"""
    total_bits = 0
    for symbol, freq in frequencies.items():
        if symbol in codes and freq > 0:
            total_bits += freq * len(codes[symbol])
    return total_bits

def normalize_frequencies(frequencies, target_range, total_count):
    """Приведение частот к заданному диапазону"""
    max_val = (1 << target_range) - 1  # Максимальное значение в целевом диапазоне
    
    # Находим максимальную частоту для масштабирования
    max_freq = max(frequencies.values()) if frequencies else 1
    
    if total_count == 0:
        return {symbol: 0 for symbol in range(256)}
    
    normalized = {}
    for symbol in range(256):
        freq = frequencies.get(symbol, 0)
        
        # Нормализация с сохранением нулевых значений
        if freq == 0:
            normalized[symbol] = 0
        elif total_count <= max_val:
            # Если общее количество символов помещается в диапазон
            normalized[symbol] = max(1, round(freq))
        else:
            # Масштабирование для больших файлов
            if max_freq <= max_val:
                scaled = freq
            else:
                scaled = max(1, round((freq / max_freq) * max_val))
            
            # Убеждаемся, что ненулевые частоты не становятся нулевыми
            if freq > 0 and scaled == 0:
                scaled = 1
            
            normalized[symbol] = scaled
    
    return normalized

def calculate_compressed_size(file_path):
    """Основная функция для расчета размеров с разными представлениями частот"""
    
    # Чтение файла и подсчет частот
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
        return None, None
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return None, None
    
    file_size = len(data)
    
    # Подсчет исходных частот
    raw_frequencies = Counter(data)
    total_symbols = sum(raw_frequencies.values())
    
    # Заполняем все возможные байты (0-255)
    frequencies_64 = {i: raw_frequencies.get(i, 0) for i in range(256)}
    
    # Нормализация для разных представлений
    # ν64: исходные частоты (8 байт на частоту)
    frequencies_64_norm = frequencies_64.copy()
    
    # ν32: нормализация к 32-битному диапазону
    frequencies_32 = normalize_frequencies(frequencies_64, 32, total_symbols)
    
    # ν8: нормализация к 8-битному диапазону (0-255)
    frequencies_8 = normalize_frequencies(frequencies_64, 8, total_symbols)
    
    # ν4: нормализация к 4-битному диапазону (0-15)
    frequencies_4 = normalize_frequencies(frequencies_64, 4, total_symbols)
    
    results = {}
    
    # Расчет для каждого представления частот
    for bit_size, freqs in [("64", frequencies_64_norm), 
                           ("32", frequencies_32), 
                           ("8", frequencies_8), 
                           ("4", frequencies_4)]:
        
        # Фильтруем ненулевые частоты для построения дерева
        non_zero_freqs = {k: v for k, v in freqs.items() if v > 0}
        
        if not non_zero_freqs:
            results[bit_size] = {"E": 0, "G": 256 * int(bit_size) // 8}
            continue
        
        # Строим дерево Хаффмана
        root = build_huffman_tree(non_zero_freqs)
        codes = generate_codes(root)
        
        # Рассчитываем длину сжатых данных в битах
        compressed_bits = calculate_compressed_length(non_zero_freqs, codes)
        
        # Переводим в байты (округляем вверх)
        E = math.ceil(compressed_bits / 8)
        
        # Размер таблицы частот в байтах
        freq_table_size = 256 * int(bit_size) // 8
        
        # Общий размер G = E + размер таблицы частот
        G = E + freq_table_size
        
        results[bit_size] = {
            "E": E, 
            "G": G, 
            "codes": codes, 
            "freqs": freqs,
            "compressed_bits": compressed_bits,
            "freq_table_size": freq_table_size
        }
    
    return results, file_size

def print_results(file_path, results, file_size):
    """Вывод результатов анализа для файла"""
    print(f"\n{'='*80}")
    print(f"АНАЛИЗ ФАЙЛА: {os.path.abspath(file_path)}")
    print(f"Размер файла: {file_size:,} байт")
    print('='*80)
    
    # Вывод результатов
    print("\nРЕЗУЛЬТАТЫ ДЛЯ РАЗНЫХ ПРЕДСТАВЛЕНИЙ ЧАСТОТ:")
    print(f"{'Тип':<6} | {'E (байт)':<15} | {'G (байт)':<15} | {'Сжатие E':<12} | "
          f"{'Общее G':<12} | {'Таблица':<10}")
    print("-" * 90)
    
    best_G = float('inf')
    best_B = None
    best_result = None
    
    for B in ["64", "32", "8", "4"]:
        res = results[B]
        E = res["E"]
        G = res["G"]
        table_size = res["freq_table_size"]
        
        compression_ratio_E = (E / file_size * 100) if file_size > 0 else 0
        compression_ratio_G = (G / file_size * 100) if file_size > 0 else 0
        
        print(f"ν{B:<4} | {E:<15,} | {G:<15,} | {compression_ratio_E:<11.1f}% | "
              f"{compression_ratio_G:<11.1f}% | {table_size:<10,}")
        
        if G < best_G:
            best_G = G
            best_B = B
            best_result = res
    
    print(f"\n✓ НАИБОЛЕЕ ВЫГОДНАЯ РАЗРЯДНОСТЬ: B* = {best_B}")
    print(f"  Общий размер G* = {best_G:,} байт")
    print(f"  Отношение к исходному: {best_G/file_size*100:.1f}%")
    
    # Сравнение эффективности
    print("\nСРАВНЕНИЕ ЭФФЕКТИВНОСТИ:")
    base_G = results["64"]["G"]
    for B in ["32", "8", "4"]:
        G = results[B]["G"]
        improvement = (base_G - G) / base_G * 100 if base_G > 0 else 0
        if improvement > 0:
            print(f"  G{B} лучше G64 на: {improvement:.1f}%")
        elif improvement < 0:
            print(f"  G{B} хуже G64 на: {-improvement:.1f}%")
        else:
            print(f"  G{B} равен G64")
    
    return best_B, best_result

def print_detailed_statistics(file_path, results, best_B):
    """Вывод детальной статистики для файла"""
    print(f"\n{'='*80}")
    print(f"ДЕТАЛЬНАЯ СТАТИСТИКА ДЛЯ ФАЙЛА: {file_path}")
    print(f"Оптимальное представление: ν{best_B}")
    print('='*80)
    
    res = results[best_B]
    freqs = res["freqs"]
    codes = res["codes"]
    
    # Подсчет ненулевых частот
    non_zero_symbols = [s for s, f in freqs.items() if f > 0]
    non_zero_count = len(non_zero_symbols)
    
    print(f"\n1. Статистика частот (ν{best_B}):")
    print(f"   • Ненулевых символов: {non_zero_count}/256 ({non_zero_count/256*100:.1f}%)")
    print(f"   • Всего символов в файле: {sum(freqs.values()):,}")
    
    # Сортировка символов по частоте
    sorted_symbols = sorted([(f, s) for s, f in freqs.items() if f > 0], reverse=True)
    
    print(f"\n2. Топ-10 самых частых символов:")
    print(f"   {'Символ':<10} {'Dec':<6} {'Hex':<6} {'Частота':<12} {'Вероятность':<12} {'Код Хаффмана':<20}")
    print("   " + "-" * 70)
    
    total_freq = sum(freqs.values())
    for i, (freq, symbol) in enumerate(sorted_symbols[:10]):
        prob = freq / total_freq if total_freq > 0 else 0
        code = codes.get(symbol, "")
        
        # Определяем отображаемое значение символа
        if 32 <= symbol <= 126:  # Печатные ASCII символы
            char_repr = f"'{chr(symbol)}'"
        else:
            char_repr = "---"
        
        print(f"   {char_repr:<10} {symbol:<6} 0x{symbol:02X}  {freq:<12,} {prob:<11.4%} {code:<20}")
    
    # Информация о кодах Хаффмана
    print(f"\n3. Характеристики кодов Хаффмана:")
    
    # Средняя длина кода
    if total_freq > 0 and codes:
        avg_length = sum(len(codes.get(s, "")) * freqs[s] for s in range(256)) / total_freq
    
    # Энтропия
    entropy = 0
    for freq in freqs.values():
        if freq > 0 and total_freq > 0:
            p = freq / total_freq
            entropy -= p * math.log2(p)
    
    print(f"   • Средняя длина кода: {avg_length:.3f} бит")
    print(f"   • Энтропия: {entropy:.3f} бит/символ")
    
    # Эффективность кодирования
    if avg_length > 0:
        efficiency = entropy / avg_length * 100
        redundancy = 100 - efficiency
        print(f"   • Эффективность кодирования: {efficiency:.1f}%")
        print(f"   • Избыточность: {redundancy:.1f}%")
    
    # Длина самого короткого и самого длинного кода
    if codes:
        code_lengths = [len(code) for code in codes.values()]
        print(f"   • Минимальная длина кода: {min(code_lengths)} бит")
        print(f"   • Максимальная длина кода: {max(code_lengths)} бит")
    
    # Размеры
    print(f"\n4. Размеры (ν{best_B}):")
    print(f"   • Исходный файл: {sum(freqs.values()):,} байт")
    print(f"   • Сжатые данные (E): {res['E']:,} байт")
    print(f"   • Таблица частот: {res['freq_table_size']:,} байт")
    print(f"   • Общий размер (G): {res['G']:,} байт")

def analyze_single_file(file_path, detailed=True):
    """Анализ одного файла"""
    if not os.path.exists(file_path):
        print(f"Ошибка: файл '{file_path}' не найден!")
        return
    
    results, file_size = calculate_compressed_size(file_path)
    if results is None:
        return
    
    best_B, best_result = print_results(file_path, results, file_size)
    
    if detailed and best_result:
        print_detailed_statistics(file_path, results, best_B)

def analyze_multiple_files(file_paths, detailed=False):
    """Анализ нескольких файлов и сравнение результатоpв"""
    all_results = {}
    
    print(f"\n{'='*80}")
    print(f"СРАВНИТЕЛЬНЫЙ АНАЛИЗ {len(file_paths)} ФАЙЛОВ")
    print('='*80)
    
    # Собираем результаты для всех файлов
    for file_path in file_paths:
        if not os.path.exists(file_path):
            print(f"Предупреждение: файл '{file_path}' не найден, пропускаем...")
            continue
        
        results, file_size = calculate_compressed_size(file_path)
        if results is not None:
            all_results[file_path] = {
                'results': results,
                'size': file_size,
                'best_B': None,
                'best_G': float('inf')
            }
            
            # Находим лучший B для этого файла
            for B in ["64", "32", "8", "4"]:
                G = results[B]["G"]
                if G < all_results[file_path]['best_G']:
                    all_results[file_path]['best_G'] = G
                    all_results[file_path]['best_B'] = B
    
    # Сводная таблица
    print(f"\n{'Файл':<40} {'Размер':<12} {'B*':<6} {'G*':<15} {'G*/исходный':<12}")
    print("-" * 90)
    
    for file_path, data in all_results.items():
        file_name = os.path.basename(file_path)
        if len(file_name) > 37:
            file_name = "..." + file_name[-34:]
        
        original_size = data['size']
        best_B = data['best_B']
        best_G = data['best_G']
        ratio = best_G / original_size * 100 if original_size > 0 else 0
        
        print(f"{file_name:<40} {original_size:<12,} {best_B:<6} {best_G:<15,} {ratio:<11.1f}%")
    
    # Анализ оптимальных представлений
    print(f"\nРАСПРЕДЕЛЕНИЕ ОПТИМАЛЬНЫХ ПРЕДСТАВЛЕНИЙ:")
    best_counts = {"64": 0, "32": 0, "8": 0, "4": 0}
    for data in all_results.values():
        best_counts[data['best_B']] += 1
    
    for B in ["64", "32", "8", "4"]:
        count = best_counts[B]
        percentage = count / len(all_results) * 100 if all_results else 0
        print(f"  ν{B}: {count} файлов ({percentage:.1f}%)")
    
    return all_results

def main():
    parser = argparse.ArgumentParser(
        description="Программа для расчета кодов Хаффмана и анализа эффективности сжатия "
                    "с разными представлениями частот"
    )
    parser.add_argument(
        "files", 
        nargs="+", 
        help="Файлы для анализа"
    )
    parser.add_argument(
        "-d", "--detailed", 
        action="store_true", 
        help="Вывод детальной статистики для каждого файла"
    )
    parser.add_argument(
        "-c", "--compare", 
        action="store_true", 
        help="Сравнительный анализ нескольких файлов"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("ПРОГРАММА АНАЛИЗА КОДОВ ХАФФМАНА")
    print("="*80)
    
    # Проверяем существование файлов
    valid_files = []
    for file_path in args.files:
        if os.path.exists(file_path):
            valid_files.append(file_path)
        else:
            print(f"Ошибка: файл '{file_path}' не найден!")
    
    if not valid_files:
        print("Нет доступных файлов для анализа.")
        return
    
    if args.compare and len(valid_files) > 1:
        # Сравнительный анализ нескольких файлов
        analyze_multiple_files(valid_files, args.detailed)
        
        # Дополнительно детальный анализ каждого файла если нужно
        if args.detailed:
            for file_path in valid_files:
                analyze_single_file(file_path, detailed=True)
    else:
        # Анализ каждого файла отдельно
        for i, file_path in enumerate(valid_files):
            if len(valid_files) > 1:
                print(f"\nФайл {i+1} из {len(valid_files)}")
            analyze_single_file(file_path, args.detailed)

if __name__ == "__main__":
    main()