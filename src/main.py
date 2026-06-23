import os
import time
from datetime import datetime

# Запрашиваем путь у пользователя
folder_path = input("Введите путь к папке: ").strip()

# Убираем кавычки, если пользователь их поставил
folder_path = folder_path.strip('"\'')

if os.path.exists(folder_path):
    print(f"Принимаю папку: {folder_path}")
    print("\n" + "=" * 80)

    # Список для хранения метаданных
    files_metadata = []
    total_size = 0
    total_files = 0

    # Обходим папку (включая все вложенные)
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # Получаем информацию о файле
                stat_info = os.stat(file_path)

                # Собираем метаданные
                metadata = {
                    'path': file_path,
                    'size': stat_info.st_size,  # размер в байтах
                    'size_mb': stat_info.st_size / (1024 * 1024),  # размер в МБ
                    'modified': datetime.fromtimestamp(stat_info.st_mtime),
                    'created': datetime.fromtimestamp(stat_info.st_ctime),
                    'accessed': datetime.fromtimestamp(stat_info.st_atime)
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
    print(f"Размер папки: {total_size / (1024 * 1024 * 1024):.2f} ГБ" if total_size > 1024 ** 3 else "")
    print("\n" + "=" * 80)

    # Выводим полный список файлов с метаданными
    print(f"\nПОЛНЫЙ СПИСОК ФАЙЛОВ ({total_files} шт.):")
    print("-" * 80)

    for i, meta in enumerate(files_metadata, 1):
        print(f"\n{i}. 📄 {os.path.basename(meta['path'])}")
        print(f"   Путь: {meta['path']}")
        print(f"   Размер: {meta['size']:,} байт ({meta['size_mb']:.2f} МБ)")
        print(f"   Изменён: {meta['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Создан: {meta['created'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Открыт: {meta['accessed'].strftime('%Y-%m-%d %H:%M:%S')}")
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
            for meta in files_metadata:
                f.write(f"Файл: {os.path.basename(meta['path'])}\n")
                f.write(f"Путь: {meta['path']}\n")
                f.write(f"Размер: {meta['size']:,} байт\n")
                f.write(f"Изменён: {meta['modified'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 40 + "\n")
        print(f"Отчёт сохранён в файл: {report_name}")

else:
    print("Такой папки нет, попробуйте снова")
