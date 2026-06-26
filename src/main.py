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


def scan_folder(folder_path, hash_to_paths, max_size_gb=1):
    """Сканирует папку и возвращает метаданные файлов"""
    files_metadata = []
    total_size = 0
    total_files = 0
    total_hashed = 0
    hash_errors = 0

    if not os.path.exists(folder_path):
        print(f"Папка {folder_path} не существует!")
        return None, 0, 0, 0, 0

    print(f"Сканирую папку: {folder_path}")
    print("=" * 80)

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # Получаем информацию о файле
                stat_info = os.stat(file_path)

                # Пропускаем очень большие файлы (более 1 ГБ) для ускорения
                if stat_info.st_size > max_size_gb * 1024 * 1024 * 1024:
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

                # Получаем относительный путь для сравнения
                rel_path = os.path.relpath(file_path, folder_path)

                # Собираем метаданные
                metadata = {
                    'path': file_path,
                    'rel_path': rel_path,  # Относительный путь для сравнения
                    'size': stat_info.st_size,
                    'size_mb': stat_info.st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(stat_info.st_mtime),
                    'created': datetime.fromtimestamp(stat_info.st_ctime),
                    'accessed': datetime.fromtimestamp(stat_info.st_atime),
                    'hash': file_hash
                }

                files_metadata.append(metadata)
                total_size += stat_info.st_size
                total_files += 1

            except (OSError, PermissionError) as e:
                print(f"Не удалось получить доступ к файлу: {file_path} - {e}")

    return files_metadata, total_size, total_files, total_hashed, hash_errors


def find_duplicates(hash_to_paths):
    """Находит дубликаты файлов"""
    duplicates = {hash_val: paths for hash_val, paths in hash_to_paths.items()
                  if len(paths) > 1 and hash_val not in ["SKIPPED_LARGE_FILE", "HASH_ERROR"]}
    return duplicates


def compare_folders(source_folder, backup_folder):
    """Сравнивает исходную папку с резервной копией"""
    print("\n" + "=" * 80)
    print("СРАВНЕНИЕ С РЕЗЕРВНОЙ КОПИЕЙ")
    print("=" * 80)

    # Сканируем исходную папку
    print("\n[1/2] Сканируем исходную папку...")
    source_hash_to_paths = defaultdict(list)
    source_metadata, source_size, source_files, source_hashed, source_errors = scan_folder(
        source_folder, source_hash_to_paths
    )

    if source_metadata is None:
        print("Не удалось просканировать исходную папку")
        return

    source_by_relpath = {meta['rel_path']: meta for meta in source_metadata}

    # Сканируем папку резервной копии
    print("\n[2/2] Сканируем папку резервной копии...")
    backup_hash_to_paths = defaultdict(list)
    backup_metadata, backup_size, backup_files, backup_hashed, backup_errors = scan_folder(
        backup_folder, backup_hash_to_paths
    )

    if backup_metadata is None:
        print("Не удалось просканировать папку резервной копии")
        return

    backup_by_relpath = {meta['rel_path']: meta for meta in backup_metadata}

    # Сравниваем по относительным путям
    source_paths = set(source_by_relpath.keys())
    backup_paths = set(backup_by_relpath.keys())

    # Находим различия
    only_in_source = source_paths - backup_paths
    only_in_backup = backup_paths - source_paths
    common_paths = source_paths & backup_paths

    # Проверяем измененные файлы
    modified_files = []
    for rel_path in common_paths:
        source_hash = source_by_relpath[rel_path]['hash']
        backup_hash = backup_by_relpath[rel_path]['hash']
        if source_hash != backup_hash and source_hash not in ["SKIPPED_LARGE_FILE", "HASH_ERROR"]:
            modified_files.append({
                'rel_path': rel_path,
                'source_path': source_by_relpath[rel_path]['path'],
                'backup_path': backup_by_relpath[rel_path]['path'],
                'source_hash': source_hash,
                'backup_hash': backup_hash,
                'source_size': source_by_relpath[rel_path]['size'],
                'backup_size': backup_by_relpath[rel_path]['size'],
                'source_modified': source_by_relpath[rel_path]['modified'],
                'backup_modified': backup_by_relpath[rel_path]['modified']
            })

    # Выводим результаты
    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТЫ СРАВНЕНИЯ")
    print("=" * 80)

    # 1. Файлы только в исходной папке
    if only_in_source:
        print(f"\n[ФАЙЛЫ ТОЛЬКО В ИСХОДНОЙ ПАПКЕ] ({len(only_in_source)} шт.):")
        print("-" * 40)
        for rel_path in sorted(only_in_source):
            meta = source_by_relpath[rel_path]
            print(f"  * {rel_path}")
            print(f"    Путь: {meta['path']}")
            print(f"    Размер: {meta['size']:,} байт ({meta['size_mb']:.2f} МБ)")
            print(f"    Изменён: {meta['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\n[OK] Все файлы из исходной папки присутствуют в резервной копии")

    # 2. Файлы только в резервной копии
    if only_in_backup:
        print(f"\n[ЛИШНИЕ ФАЙЛЫ В РЕЗЕРВНОЙ КОПИИ] ({len(only_in_backup)} шт.):")
        print("-" * 40)
        for rel_path in sorted(only_in_backup):
            meta = backup_by_relpath[rel_path]
            print(f"  * {rel_path}")
            print(f"    Путь: {meta['path']}")
            print(f"    Размер: {meta['size']:,} байт ({meta['size_mb']:.2f} МБ)")
            print(f"    Изменён: {meta['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\n[OK] В резервной копии нет лишних файлов")

    # 3. Измененные файлы
    if modified_files:
        print(f"\n[ИЗМЕНЕННЫЕ ФАЙЛЫ] ({len(modified_files)} шт.):")
        print("-" * 40)
        for item in modified_files:
            print(f"  * {item['rel_path']}")
            print(f"    Исходный путь: {item['source_path']}")
            print(f"    Путь в бэкапе: {item['backup_path']}")
            print(f"    Размер (исх.): {item['source_size']:,} байт")
            print(f"    Размер (бэкап): {item['backup_size']:,} байт")
            print(f"    Изменён (исх.): {item['source_modified'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Изменён (бэкап): {item['backup_modified'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Хэш (исх.): {item['source_hash'][:16]}...")
            print(f"    Хэш (бэкап): {item['backup_hash'][:16]}...")
    else:
        print("\n[OK] Все общие файлы идентичны")

    # Общая статистика
    print("\n" + "=" * 80)
    print("ОБЩАЯ СТАТИСТИКА СРАВНЕНИЯ:")
    print(f"  Общих файлов: {len(common_paths)}")
    print(f"  Только в исходной папке: {len(only_in_source)}")
    print(f"  Только в резервной копии: {len(only_in_backup)}")
    print(f"  Измененных файлов: {len(modified_files)}")
    print("=" * 80)

    return {
        'only_in_source': only_in_source,
        'only_in_backup': only_in_backup,
        'modified_files': modified_files,
        'common_paths': common_paths
    }


# ============ ОСНОВНАЯ ПРОГРАММА ============

if os.path.exists(folder_path):
    print(f"Принимаю папку: {folder_path}")
    print("\n" + "=" * 80)

    # Сканируем папку
    files_metadata, total_size, total_files, total_hashed, hash_errors = scan_folder(
        folder_path, hash_to_paths
    )

    if files_metadata is None:
        print("Не удалось просканировать папку")
    else:
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
        duplicates = find_duplicates(hash_to_paths)

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

        # Группировка по расширениям
        print("\nГРУППИРОВКА ПО РАСШИРЕНИЯМ:")
        extensions = {}
        for meta in files_metadata:
            ext = os.path.splitext(meta['path'])[1].lower() or 'без расширения'
            extensions[ext] = extensions.get(ext, 0) + 1

        for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
            print(f"   {ext}: {count} файлов")

        # Сохраняем результат в файл
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

        # === Сравнение с резервной копией ===
        print("\n" + "=" * 80)
        compare_choice = input("Хотите сравнить эту папку с резервной копией? (y/n): ").strip().lower()
        if compare_choice == 'y':
            backup_path = input("Введите путь к папке резервной копии: ").strip()
            backup_path = backup_path.strip('"\'')

            if os.path.exists(backup_path):
                compare_folders(folder_path, backup_path)
            else:
                print(f"Папка резервной копии не найдена: {backup_path}")

else:
    print("Такой папки нет, попробуйте снова")
