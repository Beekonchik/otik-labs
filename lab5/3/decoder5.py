import os
import struct
import sys

class LZ77_Decoder_Correct:
    def __init__(self):
        self.expected_major_version = 5
        self.expected_minor_version = 0
        self.expected_context_algorithm = 1
        self.min_match_length = 3
    
    def format_size(self, size):
        """Форматирует размер файла"""
        if size == 0:
            return "0 байт"
        size_float = float(size)
        if size_float < 1024:
            return f"{size_float:.0f} байт"
        else:
            return f"{size_float/1024:.2f} КБ"
    
    def validate_header(self, header):
        """Проверка заголовка"""
        if len(header) < 24:
            return False
        
        signature = header[0:6]
        if signature != bytes([0x6B, 0x6C, 0x75, 0x73, 0x68, 0x61]):
            return False
        
        if header[6] != self.expected_major_version:
            return False
        
        if header[8] != self.expected_context_algorithm:
            return False
        
        return True
    
    def decode_with_flags(self, flags, compressed_data, num_tokens, padding_bits):
        """
        Декодирование с использованием флаг-байтов
        """
        # Преобразуем флаг-байты в битовую строку
        flag_bits = ''
        for flag_byte in flags:
            flag_bits += format(flag_byte, '08b')
        
        # Преобразуем сжатые данные в битовую строку
        data_bits = ''
        for byte in compressed_data:
            data_bits += format(byte, '08b')
        
        # Убираем padding биты
        if padding_bits > 0:
            data_bits = data_bits[:-padding_bits]
        
        tokens = []
        flag_pos = 0
        data_pos = 0
        
        for _ in range(num_tokens):
            if flag_pos >= len(flag_bits):
                break
            
            # Читаем флаг
            is_reference = flag_bits[flag_pos] == '1'
            flag_pos += 1
            
            if is_reference:
                # Ссылка: (L-3):6, S:10
                if data_pos + 16 > len(data_bits):
                    break
                
                # Читаем L-3 (6 бит)
                l_minus_3 = int(data_bits[data_pos:data_pos+6], 2)
                data_pos += 6
                
                # Читаем S (10 бит)
                offset = int(data_bits[data_pos:data_pos+10], 2)
                data_pos += 10
                
                # Восстанавливаем длину
                length = l_minus_3 + self.min_match_length
                
                tokens.append(('reference', offset, length))
            else:
                # Символ: (c:8)
                if data_pos + 8 > len(data_bits):
                    break
                
                char = int(data_bits[data_pos:data_pos+8], 2)
                data_pos += 8
                
                tokens.append(('literal', char, 0))
        
        return tokens
    
    def decompress_lz77(self, tokens):
        """
        Распаковка LZ77
        """
        result = bytearray()
        window = bytearray(1024)  # Скользящее окно
        window_pos = 0
        
        for token_type, value1, value2 in tokens:
            if token_type == 'literal':
                # Символ
                result.append(value1)
                window[window_pos % 1024] = value1
                window_pos += 1
            else:
                # Ссылка: offset, length
                offset, length = value1, value2
                
                # Копируем из окна
                for i in range(length):
                    if offset > 0 and offset <= min(window_pos, 1024):
                        # Вычисляем позицию в окне
                        src_pos = (window_pos - offset) % 1024
                        byte_to_copy = window[src_pos]
                    else:
                        # Если смещение некорректное, копируем последний символ
                        if result:
                            byte_to_copy = result[-1]
                        else:
                            byte_to_copy = 0
                    
                    result.append(byte_to_copy)
                    window[window_pos % 1024] = byte_to_copy
                    window_pos += 1
        
        return bytes(result)
    
    def decompress_file(self, input_file):
        """Основная функция декомпрессии"""
        try:
            if input_file.endswith('.klusha'):
                base_name = input_file[:-7]
            else:
                base_name = input_file
            
            output_file = f"{base_name}_restored"
            
            with open(input_file, 'rb') as f:
                header = f.read(24)
                if not self.validate_header(header):
                    print("Ошибка: Неверный формат файла")
                    return
                
                original_size = struct.unpack('>Q', header[16:24])[0]
                
                algo_size_data = f.read(4)
                algo_size = struct.unpack('>I', algo_size_data)[0]
                
                algo_data = f.read(algo_size)
            
            # Разбираем алгоритмические данные:
            # 1. Количество флаг-байтов (4 байта)
            num_flag_bytes = struct.unpack('>I', algo_data[0:4])[0]
            
            # 2. Флаг-байты
            flags_start = 4
            flags_end = flags_start + num_flag_bytes
            flags = list(algo_data[flags_start:flags_end])
            
            # 3. Количество токенов (4 байта)
            num_tokens = struct.unpack('>I', algo_data[flags_end:flags_end+4])[0]
            
            # 4. Сжатые данные и 5. Padding битов
            data_start = flags_end + 4
            
            # Последний байт - padding биты
            padding_bits = algo_data[-1]
            
            # Сжатые данные - все между data_start и последним байтом
            compressed_data = algo_data[data_start:-1]
            
            # Декодируем токены
            tokens = self.decode_with_flags(flags, compressed_data, num_tokens, padding_bits)
            
            # Декомпрессия
            decompressed = self.decompress_lz77(tokens)
            
            # Обрезаем до исходного размера
            if len(decompressed) > original_size:
                decompressed = decompressed[:original_size]
            
            # Записываем результат
            with open(output_file, 'wb') as f:
                f.write(decompressed)
            
            print(f"Файл успешно восстановлен: {input_file} -> {output_file}")
            print(f"Размер восстановленного файла: {self.format_size(len(decompressed))}")
            
        except Exception as e:
            print(f"Ошибка: {e}")
            import traceback
            traceback.print_exc()

def main():
    decoder = LZ77_Decoder_Correct()
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "Q.klusha"
    
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден")
        return
    
    decoder.decompress_file(input_file)

if __name__ == "__main__":
    main()