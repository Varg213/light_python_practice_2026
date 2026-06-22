import os

# Запрашиваем путь у пользователя
folder_path = input("Введите путь к папке: ").strip()

# Убираем кавычки, если пользователь их поставил
folder_path = folder_path.strip('"\'')

if os.path.exists(folder_path):
    print(f"Принимаю папку: {folder_path}")
else:
    print("Такой папки нет, попробуйте снова")
