import os
import struct
import sys
from collections import Counter

class LZ77_Coder_Correct:
    def __init__(self):
        self.signature = bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61])
        self.major_version = 5
        self.minor_version = 0
        self.context_algorithm = 1
        self.context_free_algorithm = 0
        self.error_protection_algorithm = 0
        self.window_size = 1024  # Максимальное смещение 1023 (10 бит)
        self.min_match_length = 3  # Минимальная длина совпадения
        self.max_match_length = 66  # Максимальная длина (L-3=63 → L=66)
        
    def format_size(self, size):
        """Форматирует размер файла"""
        if size == 0:
            return "0 байт"
        units = ['байт', 'КБ']
        unit_index = 0
        size_float = float(size)
        while size_float >= 1024 and unit_index < len(units) - 1:
            size_float /= 1024.0
            unit_index += 1
        
        if unit_index == 0:
            return f"{size_float:.0f} {units[unit_index]}"
        else:
            return f"{size_float:.2f} {units[unit_index]}"
    
    def find_best_match(self, data, current_pos):
        """
        Ищет лучшее совпадение в скользящем окне
        Возвращает (offset, length) или (0, 0) если нет совпадения
        """
        start_pos = max(0, current_pos - self.window_size)
        best_length = 0
        best_offset = 0
        
        # Простой линейный поиск
        for i in range(start_pos, current_pos):
            length = 0
            while (current_pos + length < len(data) and 
                   i + length < current_pos and
                   data[i + length] == data[current_pos + length]):
                length += 1
                if length >= self.max_match_length:
                    break
            
            if length > best_length and length >= self.min_match_length:
                best_length = length
                best_offset = current_pos - i
        
        return (best_offset, best_length)
    
    def compress_lz77_with_flags(self, data):
        """
        Сжатие LZ77 с флаг-байтами
        Возвращает список токенов и флаг-байты
        """
        tokens = []  # Список токенов (type, value1, value2)
        flags = []   # Флаг-байты (биты указывают тип следующих токенов)
        current_flag_byte = 0
        current_flag_bit = 0
        
        i = 0
        while i < len(data):
            offset, length = self.find_best_match(data, i)
            
            if length >= self.min_match_length:
                # Нашли совпадение - кодируем как ссылку
                # Устанавливаем бит флага в 1 (ссылка)
                current_flag_byte |= (1 << current_flag_bit)
                
                # Кодируем ссылку: (L-3):6, S:10
                encoded_length = length - self.min_match_length  # L-3
                if encoded_length > 63:
                    encoded_length = 63
                
                tokens.append(('reference', offset, encoded_length))
                i += length
            else:
                # Нет совпадения - кодируем как символ
                # Биты флага остаются 0 (символ)
                
                # Кодируем символ: (c:8)
                char = data[i]
                tokens.append(('literal', char, 0))
                i += 1
            
            current_flag_bit += 1
            
            # Если набрали 8 бит в флаг-байте, сохраняем и начинаем новый
            if current_flag_bit >= 8:
                flags.append(current_flag_byte)
                current_flag_byte = 0
                current_flag_bit = 0
        
        # Добавляем последний неполный флаг-байт
        if current_flag_bit > 0:
            flags.append(current_flag_byte)
        
        return tokens, flags
    
    def encode_tokens_correct(self, tokens):
        """
        Кодирование токенов в правильном формате:
        - Для ссылок: (L-3):6, S:10 (16 бит)
        - Для символов: (c:8) (8 бит)
        """
        bit_stream = []
        
        for token_type, value1, value2 in tokens:
            if token_type == 'reference':
                # Ссылка: (L-3):6, S:10
                # L-3 (6 бит)
                bit_stream.append(format(value2, '06b'))  # encoded_length = L-3
                # S (10 бит) - offset
                bit_stream.append(format(value1, '010b'))
            else:
                # Символ: (c:8)
                bit_stream.append(format(value1, '08b'))
        
        # Конвертируем биты в байты
        bit_string = ''.join(bit_stream)
        
        # Дополняем до целого числа байт
        padding_bits = (8 - len(bit_string) % 8) % 8
        bit_string += '0' * padding_bits
        
        # Преобразуем в байты
        result = bytearray()
        for i in range(0, len(bit_string), 8):
            result.append(int(bit_string[i:i+8], 2))
        
        return bytes(result), padding_bits
    
    def compress_file(self, input_file):
        """Основная функция сжатия с правильным форматом"""
        try:
            output_file = input_file + ".klusha"
            
            # Читаем исходный файл
            with open(input_file, 'rb') as f:
                file_data = f.read()
            
            original_size = len(file_data)
            
            # Сжимаем данные LZ77 с флагами
            tokens, flags = self.compress_lz77_with_flags(file_data)
            
            # Кодируем токены в правильном формате
            compressed_data, padding_bits = self.encode_tokens_correct(tokens)

            algo_data = (
                struct.pack('>I', len(flags)) +  # 1. Количество флаг-байтов (4 байта)
                bytes(flags) +                   # 2. Флаг-байты
                struct.pack('>I', len(tokens)) + # 3. Количество токенов
                compressed_data +                # 4. Сжатые данные
                bytes([padding_bits])            # 5. Padding битов
            )
            
            algo_data_size = len(algo_data)
            
            # Создаем архив
            with open(output_file, 'wb') as f:
                # Заголовок (24 байта)
                f.write(self.signature)
                f.write(bytes([self.major_version]))
                f.write(bytes([self.minor_version]))
                f.write(bytes([self.context_algorithm]))
                f.write(bytes([self.context_free_algorithm]))
                f.write(bytes([self.error_protection_algorithm]))
                f.write(b'\x00\x00\x00\x00\x00')
                f.write(struct.pack('>Q', original_size))
                
                # Размер служебных данных (4 байта)
                f.write(struct.pack('>I', algo_data_size))
                
                # Служебные данные алгоритмов
                f.write(algo_data)
            
            compressed_size = os.path.getsize(output_file)
            
            print(f"Размер исходного файла: {original_size} байт")
            print(f"Сгенерировано токенов: {len(tokens)}")
            print(f"Флаг-байтов: {len(flags)}")
            
            # Показываем первые несколько токенов (только для маленьких файлов)
            if len(tokens) <= 20:
                print("Токены:")
                for i, token in enumerate(tokens):
                    token_type, value1, value2 = token
                    if token_type == 'reference':
                        actual_length = value2 + self.min_match_length
                        print(f"{i}: Ссылка: offset={value1}, length={actual_length}")
                    else:
                        char = value1
                        char_repr = f"'{chr(char)}'" if 32 <= char < 127 else f"0x{char:02x}"
                        print(f"{i}: Символ: {char_repr}")
            
            print(f"Файл успешно сжат: {input_file} -> {output_file}")
            print(f"Исходный размер: {self.format_size(original_size)}")
            print(f"Сжатый размер: {self.format_size(compressed_size)}")
            
        except Exception as e:
            print(f"Ошибка: {e}")
            import traceback
            traceback.print_exc()

def main():
    coder = LZ77_Coder_Correct()
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "Q"
    
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден")
        return
    
    coder.compress_file(input_file)

if __name__ == "__main__":
    main()