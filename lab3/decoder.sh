#!/bin/bash

ARCHIVE_FILE=${1:-Q.klusha}
OUTPUT_FILE="${ARCHIVE_FILE%.klusha}_restored"

echo "Декодирование архива: $ARCHIVE_FILE"
echo "Выходной файл: $OUTPUT_FILE"

SIGNATURE=$(head -c 6 "$ARCHIVE_FILE")
VERSION_HEX=$(head -c 8 "$ARCHIVE_FILE" | tail -c 2 | xxd -p)
FILE_SIZE_HEX=$(head -c 16 "$ARCHIVE_FILE" | tail -c 8 | xxd -p)

VERSION=$((16#$VERSION_HEX))
FILE_SIZE=$((16#$FILE_SIZE_HEX))

echo "Сигнатура: '$SIGNATURE'"
echo "Версия: $VERSION"
echo "Размер данных: $FILE_SIZE байт"

if [ "$SIGNATURE" != "klusha" ]; then
    echo "Ошибка: неверная сигнатура архива"
    exit 1
fi

if [ "$VERSION" -ne 0 ]; then
    echo "Ошибка: неверная версия формата"
    exit 1
fi

ARCHIVE_SIZE=$(wc -c < "$ARCHIVE_FILE")
EXPECTED_SIZE=$((16 + FILE_SIZE))

if [ "$ARCHIVE_SIZE" -ne "$EXPECTED_SIZE" ]; then
    echo "Ошибка: несоответствие размера архива"
    echo "Ожидалось: $EXPECTED_SIZE байт, фактически: $ARCHIVE_SIZE байт"
    exit 1
fi

tail -c "$FILE_SIZE" "$ARCHIVE_FILE" > "$OUTPUT_FILE"

echo "Файл успешно восстановлен: $OUTPUT_FILE"
echo "Размер восстановленного файла: $(wc -c < "$OUTPUT_FILE") байт"

ORIGINAL_FILE="${ARCHIVE_FILE%.klusha}"
if [ -f "$ORIGINAL_FILE" ]; then
    if diff "$ORIGINAL_FILE" "$OUTPUT_FILE" > /dev/null; then
        echo "Файлы идентичны (используя diff)"
    else
        echo "Файлы различаются!"
    fi
fi