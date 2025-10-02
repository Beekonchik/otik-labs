#!/bin/bash

INPUT_FILE=${1:-Q}
OUTPUT_FILE="${INPUT_FILE}.klusha"

FILE_SIZE=$(wc -c < "$INPUT_FILE")

# Параметры кодирования 
MAJOR_VERSION=1
MINOR_VERSION=0
CONTEXT_ALG=0    # 0 = без сжатия
NOCONTEXT_ALG=0  # 0 = без сжатия  
ERROR_ALG=0      # 0 = без защиты от помех
ALGO_DATA=""     # Служебные данные алгоритмов 

ALGO_DATA_SIZE=${#ALGO_DATA}

echo "Кодирование файла: $INPUT_FILE"
echo "Размер файла: $FILE_SIZE байт"
echo "Версия: $MAJOR_VERSION.$MINOR_VERSION"
echo "Алгоритмы: контекстный=$CONTEXT_ALG, бесконтекстный=$NOCONTEXT_ALG, защита=$ERROR_ALG"
echo "Создание архива: $OUTPUT_FILE"

{
    # Сигнатура (6 байт)
    printf "klusha"
    # Версия формата (2 байта)
    printf "\\$(printf '%03o' $MAJOR_VERSION)"
    printf "\\$(printf '%03o' $MINOR_VERSION)"
    # Алгоритмы (3 байта)
    printf "\\$(printf '%03o' $CONTEXT_ALG)"
    printf "\\$(printf '%03o' $NOCONTEXT_ALG)" 
    printf "\\$(printf '%03o' $ERROR_ALG)"
    # Резерв (5 байт)
    printf '\0\0\0\0\0'
    # Длина файла (8 байт)
    printf "%016x" $FILE_SIZE | xxd -r -p
    # Длина служебных данных (4 байта)
    printf "%08x" $ALGO_DATA_SIZE | xxd -r -p
    # Служебные данные алгоритмов
    printf "%s" "$ALGO_DATA"
    # Исходные данные
    cat "$INPUT_FILE"
} > "$OUTPUT_FILE"

echo "Архив успешно создан: $OUTPUT_FILE"
echo "Размер архива: $(wc -c < "$OUTPUT_FILE") байт"