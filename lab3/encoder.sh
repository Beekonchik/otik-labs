#!/bin/bash

INPUT_FILE=${1:-Q}
OUTPUT_FILE="${INPUT_FILE}.klusha"

FILE_SIZE=$(wc -c < "$INPUT_FILE")

echo "Кодирование файла: $INPUT_FILE"
echo "Размер файла: $FILE_SIZE байт"
echo "Создание архива: $OUTPUT_FILE"

{
    # Сигнатура (6 байт)
    printf "klusha"
    # Версия формата (2 байта)
    printf "\x00\x00"
    # Длина файла (8 байт)
    printf "\\$(printf '%03o' $((FILE_SIZE & 0xFF)))"
    printf "\\$(printf '%03o' $(( (FILE_SIZE >> 8) & 0xFF )))"
    printf "\\$(printf '%03o' $(( (FILE_SIZE >> 16) & 0xFF )))"
    printf "\\$(printf '%03o' $(( (FILE_SIZE >> 24) & 0xFF )))"
    printf "\\$(printf '%03o' $(( (FILE_SIZE >> 32) & 0xFF )))"
    printf "\\$(printf '%03o' $(( (FILE_SIZE >> 40) & 0xFF )))"
    printf "\\$(printf '%03o' $(( (FILE_SIZE >> 48) & 0xFF )))"
    printf "\\$(printf '%03o' $(( (FILE_SIZE >> 56) & 0xFF )))"

    cat "$INPUT_FILE"
} > "$OUTPUT_FILE"

echo "Архив успешно создан: $OUTPUT_FILE"
echo "Размер архива: $(wc -c < "$OUTPUT_FILE") байт"