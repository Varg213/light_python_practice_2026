import os
import time
import hashlib
from datetime import datetime
from collections import defaultdict

# Запрашиваем путь у пользователя
folder_path = input("Введите путь к папке: ").strip()

# Убираем кавычки, если пользователь их поставил
folder_path = folder_path.strip('"\'')

# Словарь для хранения хэшей: хэш -> список путей
hash_to_paths = defaultdict(list)


def calculate_file_hash(file_path, chunk_size=8192):
    """Вычисляет SHA-256 хэш файла по частям"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Читаем файл по кусочкам, чтобы не загружать большие файлы целиком в память
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (OSError, PermissionError, IOError) as e:
        print(f"Не удалось вычислить хэш для файла: {file_path} - {e}")
        return None


if os.path.exists(folder_path):
    print(f"Принимаю папку: {folder_path}")
    print("\n" + "=" * 80)

    # Список для хранения метаданных
    files_metadata = []
    total_size = 0
    total_files = 0
    total_hashed = 0
    hash_errors = 0

    # Обходим папку (включая все вложенные)
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # Получаем информацию о файле
                stat_info = os.stat(file_path)

                # Пропускаем очень большие файлы (более 1 ГБ) для ускорения
                if stat_info.st_size > 1024 * 1024 * 1024:  # 1 ГБ
                    print(
                        f"Пропускаем хэширование большого файла: {file_path} ({stat_info.st_size / (1024 ** 3):.2f} ГБ)")
                    file_hash = "SKIPPED_LARGE_FILE"
                else:
                    # Вычисляем хэш файла
                    file_hash = calculate_file_hash(file_path)
                    if file_hash:
                        hash_to_paths[file_hash].append(file_path)
                        total_hashed += 1
                    else:
                        hash_errors += 1
                        file_hash = "HASH_ERROR"

                # Собираем метаданные
                metadata = {
                    'path': file_path,
                    'size': stat_info.st_size,  # размер в байтах
                    'size_mb': stat_info.st_size / (1024 * 1024),  # размер в МБ
                    'modified': datetime.fromtimestamp(stat_info.st_mtime),
                    'created': datetime.fromtimestamp(stat_info.st_ctime),
                    'accessed': datetime.fromtimestamp(stat_info.st_atime),
                    'hash': file_hash  # Добавляем хэш в метаданные
                }

                files_metadata.append(metadata)
                total_size += stat_info.st_size
                total_files += 1

            except (OSError, PermissionError) as e:
                print(f"Не удалось получить доступ к файлу: {file_path} - {e}")

    # Выводим статистику
    print(f"\nСТАТИСТИКА:")
    print(f"Всего файлов: {total_files}")
    print(f"Общий размер: {total_size:,} байт ({total_size / (1024 * 1024):.2f} МБ)")
    if total_size > 1024 ** 3:
        print(f"Размер папки: {total_size / (1024 * 1024 * 1024):.2f} ГБ")
    print(f"Файлов с вычисленным хэшем: {total_hashed}")
    if hash_errors > 0:
        print(f"Ошибок при вычислении хэша: {hash_errors}")
    print("\n" + "=" * 80)

    # Находим дубликаты
    duplicates = {hash_val: paths for hash_val, paths in hash_to_paths.items()
                  if len(paths) > 1 and hash_val not in ["SKIPPED_LARGE_FILE", "HASH_ERROR"]}

    if duplicates:
        print(f"\nНАЙДЕНЫ ДУБЛИКАТЫ ФАЙЛОВ:")
        print("-" * 80)
        for hash_val, paths in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True):
            # Получаем размер файла (из первого файла в списке)
            try:
                first_file_size = os.path.getsize(paths[0])
                size_mb = first_file_size / (1024 * 1024)
                print(f"\nХэш: {hash_val[:16]}... (размер: {size_mb:.2f} МБ)")
                print(f"   Найдено {len(paths)} копий:")
                for idx, path in enumerate(paths, 1):
                    print(f"      {idx}. {path}")
            except OSError:
                print(f"\nХэш: {hash_val[:16]}... (размер: неизвестен)")
                print(f"   Найдено {len(paths)} копий:")
                for idx, path in enumerate(paths, 1):
                    print(f"      {idx}. {path}")
    else:
        print("\nДубликатов не найдено.")

    # Выводим полный список файлов с метаданными
    print(f"\nПОЛНЫЙ СПИСОК ФАЙЛОВ ({total_files} шт.):")
    print("-" * 80)

    for i, meta in enumerate(files_metadata, 1):
        print(f"\n{i}. {os.path.basename(meta['path'])}")
        print(f"   Путь: {meta['path']}")
        print(f"   Размер: {meta['size']:,} байт ({meta['size_mb']:.2f} МБ)")
        print(f"   Изменён: {meta['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Создан: {meta['created'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Открыт: {meta['accessed'].strftime('%Y-%m-%d %H:%M:%S')}")
        if meta['hash']:
            hash_display = meta['hash'][:16] + "..." if len(meta['hash']) > 16 else meta['hash']
            print(f"   Хэш (SHA-256): {hash_display}")
        print("-" * 40)

    # Дополнительно: группировка по расширениям (опционально)
    print("\nГРУППИРОВКА ПО РАСШИРЕНИЯМ:")
    extensions = {}
    for meta in files_metadata:
        ext = os.path.splitext(meta['path'])[1].lower() or 'без расширения'
        extensions[ext] = extensions.get(ext, 0) + 1

    for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
        print(f"   {ext}: {count} файлов")

    # Сохраняем результат в файл (опционально)
    save = input("\nСохранить отчёт в файл? (y/n): ").strip().lower()
    if save == 'y':
        report_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_name, 'w', encoding='utf-8') as f:
            f.write(f"Отчёт по папке: {folder_path}\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            # Записываем информацию о дубликатах
            if duplicates:
                f.write("НАЙДЕНЫ ДУБЛИКАТЫ:\n")
                f.write("-" * 40 + "\n")
                for hash_val, paths in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True):
                    f.write(f"\nХэш: {hash_val}\n")
                    f.write(f"Найдено {len(paths)} копий:\n")
                    for idx, path in enumerate(paths, 1):
                        f.write(f"  {idx}. {path}\n")
                f.write("\n" + "=" * 80 + "\n\n")

            # Записываем все файлы
            for meta in files_metadata:
                f.write(f"Файл: {os.path.basename(meta['path'])}\n")
                f.write(f"Путь: {meta['path']}\n")
                f.write(f"Размер: {meta['size']:,} байт\n")
                f.write(f"Изменён: {meta['modified'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                if meta['hash']:
                    f.write(f"Хэш (SHA-256): {meta['hash']}\n")
                f.write("-" * 40 + "\n")
        print(f"Отчёт сохранён в файл: {report_name}")

else:
    print("Такой папки нет, попробуйте снова")
