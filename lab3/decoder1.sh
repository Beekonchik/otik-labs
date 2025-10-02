#!/bin/bash

ARCHIVE_FILE=${1:-Q.klusha}
OUTPUT_FILE="${ARCHIVE_FILE%.klusha}_restored"

echo "Декодирование архива: $ARCHIVE_FILE"
echo "Выходной файл: $OUTPUT_FILE"

# Чтение заголовка
SIGNATURE=$(head -c 6 "$ARCHIVE_FILE")
MAJOR_VERSION=$(head -c 7 "$ARCHIVE_FILE" | tail -c 1 | od -An -tu1)
MINOR_VERSION=$(head -c 8 "$ARCHIVE_FILE" | tail -c 1 | od -An -tu1)
CONTEXT_ALG=$(head -c 9 "$ARCHIVE_FILE" | tail -c 1 | od -An -tu1)
NOCONTEXT_ALG=$(head -c 10 "$ARCHIVE_FILE" | tail -c 1 | od -An -tu1)
ERROR_ALG=$(head -c 11 "$ARCHIVE_FILE" | tail -c 1 | od -An -tu1)

# Чтение числовых полей
FILE_SIZE_HEX=$(head -c 24 "$ARCHIVE_FILE" | tail -c 8 | xxd -p)
ALGO_DATA_SIZE_HEX=$(head -c 28 "$ARCHIVE_FILE" | tail -c 4 | xxd -p)

FILE_SIZE=$((16#$FILE_SIZE_HEX))
ALGO_DATA_SIZE=$((16#$ALGO_DATA_SIZE_HEX))

echo "Сигнатура: '$SIGNATURE'"
echo "Версия: $MAJOR_VERSION.$MINOR_VERSION"
echo "Алгоритмы: контекстный=$CONTEXT_ALG, бесконтекстный=$NOCONTEXT_ALG, защита=$ERROR_ALG"
echo "Размер данных: $FILE_SIZE байт"
echo "Размер служебных данных: $ALGO_DATA_SIZE байт"

# Валидация
if [ "$SIGNATURE" != "klusha" ]; then
    echo "Ошибка: неверная сигнатура архива"
    exit 1
fi

if [ "$MAJOR_VERSION" -eq 0 ] && [ "$MINOR_VERSION" -eq 0 ]; then
    echo "Ошибка: версия формата должна быть больше 0"
    exit 1
fi

# Проверка зарезервированных байтов
RESERVED=$(head -c 16 "$ARCHIVE_FILE" | tail -c 5 | od -An -tx1)
if [ "$RESERVED" != "00 00 00 00 00" ]; then
    echo "Предупреждение: зарезервированные байты не нулевые"
fi

# Проверка размера
ARCHIVE_SIZE=$(wc -c < "$ARCHIVE_FILE")
EXPECTED_SIZE=$((28 + ALGO_DATA_SIZE + FILE_SIZE))

if [ "$ARCHIVE_SIZE" -ne "$EXPECTED_SIZE" ]; then
    echo "Ошибка: несоответствие размера архива"
    echo "Ожидалось: $EXPECTED_SIZE байт, фактически: $ARCHIVE_SIZE байт"
    exit 1
fi

# Проверка поддержки алгоритмов
if [ "$CONTEXT_ALG" -ne 0 ] || [ "$NOCONTEXT_ALG" -ne 0 ] || [ "$ERROR_ALG" -ne 0 ]; then
    echo "Предупреждение: используются алгоритмы сжатия/защиты (пока не поддерживаются)"
fi

# Извлечение данных (пропускаем заголовок и служебные данные)
HEADER_AND_ALGO_SIZE=$((28 + ALGO_DATA_SIZE))
tail -c "+$((HEADER_AND_ALGO_SIZE + 1))" "$ARCHIVE_FILE" | head -c "$FILE_SIZE" > "$OUTPUT_FILE"

echo "Файл успешно восстановлен: $OUTPUT_FILE"
echo "Размер восстановленного файла: $(wc -c < "$OUTPUT_FILE") байт"

# Верификация с исходным файлом
ORIGINAL_FILE="${ARCHIVE_FILE%.klusha}"
if [ -f "$ORIGINAL_FILE" ]; then
    if diff "$ORIGINAL_FILE" "$OUTPUT_FILE" > /dev/null; then
        echo "Файлы идентичны (используя diff)"
    else
        echo "Файлы различаются!"
    fi
fi