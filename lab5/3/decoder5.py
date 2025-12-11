import os
import struct
import sys

class LZ77:
    def __init__(self):
        self.expected_major_version = 5
        self.expected_minor_version = 0
        self.expected_context_algorithm = 1
    
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
    
    def decode_bits(self, bit_data, num_tokens):
        """Декодирование битового потока"""
        # Конвертируем в битовую строку
        bit_string = ''
        for byte in bit_data:
            bit_string += format(byte, '08b')
        
        tokens = []
        pos = 0
        
        for _ in range(num_tokens):
            if pos + 16 > len(bit_string):
                break
            
            # Читаем L-3 (6 бит)
            l_minus_3 = int(bit_string[pos:pos+6], 2)
            pos += 6
            
            # Читаем S (10 бит)
            next_char = int(bit_string[pos:pos+10], 2)
            pos += 10
            
            # Восстанавливаем длину
            length = l_minus_3 + 3 if l_minus_3 > 0 else 0
            
            tokens.append((length, next_char))
        
        return tokens
    
    def decompress_lz77_simple(self, tokens):
        """Декомпрессия LZ77 (упрощенная версия)"""
        result = bytearray()
        buffer = bytearray(4096)  # Буфер для скользящего окна
        buf_pos = 0
        
        for length, next_char in tokens:
            if length == 0:
                # Литерал
                result.append(next_char)
                buffer[buf_pos % 4096] = next_char
                buf_pos += 1
            else:
                # Копирование из буфера
                # В упрощенной версии копируем последний символ length раз
                for _ in range(length):
                    if buf_pos > 0:
                        last_byte = buffer[(buf_pos - 1) % 4096]
                        result.append(last_byte)
                        buffer[buf_pos % 4096] = last_byte
                        buf_pos += 1
                
                # Добавляем следующий символ
                result.append(next_char)
                buffer[buf_pos % 4096] = next_char
                buf_pos += 1
        
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
            
            # Извлекаем количество токенов
            num_tokens = struct.unpack('>I', algo_data[0:4])[0]
            compressed_data = algo_data[4:]
            
            # Декодируем токены
            tokens = self.decode_bits(compressed_data, num_tokens)
            
            # Декомпрессия
            decompressed = self.decompress_lz77_simple(tokens)
            
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

def main():
    decoder = LZ77()
    
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