> [!WARNING]  
> Ссылка на видео и презу: https://disk.yandex.ru/d/djhUwr6MMKQJlA


Интерактивная платформа для обучения программированию с нуля.

![Python](https://img.shields.io/badge/Python-3.14.3-blue.svg)
![Django](https://img.shields.io/badge/Django-6.0.3-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey.svg)

В проекте по умолчание идет готовая БД для тестов

## Установка пошагово
> [!WARNING]  
> В случае ошибок с установкой, пожалуйста, обратитесь в ЛС Discord: nestov13 или Telegram: @nestovSa
### Клонирование проекта

### Установка зависимостей
**Python** | 3.14.3 | 
Прямая ссылка для Windows installer (64-bit) - [Скачать](https://www.python.org/ftp/python/3.14.3/python-3.14.3-amd64.exe)


**Git** | 2.x+ | [Скачать](https://git-scm.com/install/) 

> **Важно:** При установке Python отметьте галочку **"Add Python to PATH"**.

> [!WARNING]  
> Только после установки зависимостей переходите к пункту с PowerShell

Откройте **PowerShell от имени администратора**:

```powershell
# Перейдите в корень диска
cd C:\

# Клонируйте репозиторий
git clone https://github.com/Nestov1337/edu_platform.git

# Перейдите в папку проекта
cd edu_platform

# Настройка виртуального окружения

# Создайте виртуальное окружение
python -m venv venv

# Активируйте его
.\venv\Scripts\Activate.ps1
(В случае ошибки введите: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass и в
ответ на выбор введите: Y.
Повторите команду .\venv\Scripts\Activate.ps1)

# Установка зависимостей Python

# Обновите pip
python -m pip install --upgrade pip

# Установите зависимости из requirements.txt
pip install -r requirements.txt

# Примените миграции
python manage.py migrate

# Создайте суперпользователя (администратора)
python manage.py createsuperuser

Следуйте подсказкам для создания учётной записи:

Username: admin
Email: admin@example.com  # можно оставить пустым
Password:  # введите пароль


# Запуск сервера

# Запустите Django development server
python manage.py runserver

Готово. Сайт запущен по ip адрессу http://127.0.0.1:8000/
Панель администратора: http://127.0.0.1:8000/admin
# В логин и пароль вводите данные, которые вводили при создание суперпользователя
```

### Администрирование

```powershell
# Создать суперпользователя
python manage.py createsuperuser

# Изменить пароль пользователя
python manage.py changepassword username
```
