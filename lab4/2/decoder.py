import heapq
from collections import Counter, defaultdict
import math
import os

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
    """Нормализация частот к заданному диапазону"""
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
        return None
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return None
    
    file_size = len(data)
    print(f"Размер файла: {file_size} байт")
    
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
        
        results[bit_size] = {"E": E, "G": G, "codes": codes, "freqs": freqs}
    
    return results, file_size

def analyze_files(file_paths):
    """Анализ нескольких файлов"""
    all_results = {}
    
    for file_path in file_paths:
        print(f"\n{'='*60}")
        print(f"Анализ файла: {file_path}")
        print('='*60)
        
        results, file_size = calculate_compressed_size(file_path)
        if results is None:
            continue
        
        all_results[file_path] = results
        
        # Вывод результатов
        print("\nРезультаты для разных представлений частот:")
        print(f"{'Тип':<6} | {'E (байт)':<12} | {'G (байт)':<12} | {'E/исходный':<12} | {'G/исходный':<12}")
        print("-" * 70)
        
        best_G = float('inf')
        best_B = None
        
        for B in ["64", "32", "8", "4"]:
            res = results[B]
            E = res["E"]
            G = res["G"]
            
            E_ratio = E / file_size if file_size > 0 else 0
            G_ratio = G / file_size if file_size > 0 else 0
            
            print(f"ν{B:<4} | {E:<12} | {G:<12} | {E_ratio:<12.3%} | {G_ratio:<12.3%}")
            
            if G < best_G:
                best_G = G
                best_B = B
        
        print(f"\nНаиболее выгодная разрядность B* = {best_B} (G* = {best_G} байт)")
        
        # Сравнение эффективности
        print("\nСравнение эффективности:")
        base_G = results["64"]["G"]
        for B in ["32", "8", "4"]:
            G = results[B]["G"]
            improvement = (base_G - G) / base_G * 100 if base_G > 0 else 0
            print(f"G{B} по сравнению с G64: {improvement:+.1f}%")
    
    return all_results

def print_detailed_statistics(results, file_path):
    """Вывод детальной статистики для файла"""
    print(f"\n{'='*60}")
    print(f"Детальная статистика для файла: {file_path}")
    print('='*60)
    
    for B in ["64", "32", "8", "4"]:
        res = results[B]
        freqs = res["freqs"]
        codes = res["codes"]
        
        print(f"\nПредставление ν{B}:")
        
        # Подсчет ненулевых частот
        non_zero = sum(1 for f in freqs.values() if f > 0)
        print(f"  Ненулевых частот: {non_zero}/256")
        
        # Средняя длина кода
        total_freq = sum(freqs.values())
        if total_freq > 0 and codes:
            avg_length = sum(len(codes.get(s, "")) * freqs[s] for s in range(256)) / total_freq
            print(f"  Средняя длина кода: {avg_length:.2f} бит")
        
        # Энтропия
        entropy = 0
        for freq in freqs.values():
            if freq > 0 and total_freq > 0:
                p = freq / total_freq
                entropy -= p * math.log2(p)
        print(f"  Энтропия: {entropy:.2f} бит/символ")
        
        # Эффективность кодирования
        if avg_length > 0:
            efficiency = entropy / avg_length * 100
            print(f"  Эффективность кодирования: {efficiency:.1f}%")

# Пример использования
if __name__ == "__main__":
    # Создаем тестовые файлы для демонстрации
    def create_test_files():
        # 1. Файл с повторяющимися символами (хорошо сжимается)
        with open("test_repeat.bin", "wb") as f:
            data = bytes([65] * 1000 + [66] * 500 + [67] * 250 + [68] * 125)
            f.write(data)
        
        # 2. Файл со случайными данными (плохо сжимается)
        import random
        with open("test_random.bin", "wb") as f:
            data = bytes(random.randint(0, 255) for _ in range(2000))
            f.write(data)
        
        # 3. Текстовый файл
        with open("test_text.txt", "w", encoding="utf-8") as f:
            text = "Пример текстового файла для тестирования алгоритма Хаффмана. " * 20
            f.write(text)
        
        return ["test_repeat.bin", "test_random.bin", "test_text.txt"]
    
    # Создаем тестовые файлы
    test_files = create_test_files()
    
    # Анализируем файлы
    results = analyze_files(test_files)
    
    # Детальная статистика для первого файла
    if results:
        first_file = test_files[0]
        print_detailed_statistics(results[first_file], first_file)
    
    # Очистка тестовых файлов (опционально)
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)