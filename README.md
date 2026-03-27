Интерактивная платформа для обучения программированию с нуля.

![Python](https://img.shields.io/badge/Python-3.14.3-blue.svg)
![Django](https://img.shields.io/badge/Django-6.0.3-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey.svg)

В проекте по умолчание идет готовая БД для тестов

## Установка пошагово

### Установка зависимостей

**Python** | 3.14.3 | [Скачать](https://www.python.org/downloads/) |
**Git** | 2.x+ | [Скачать](https://git-scm.com/install/) |

> **Важно:** При установке Python отметьте галочку **"Add Python to PATH"**.

### Клонирование проекта

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
(В случае ошибки введите: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass Затем повторите активацию. Вы должны увидеть префикс `(venv)` в терминале.

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
```

### Администрирование

```powershell
# Создать суперпользователя
python manage.py createsuperuser

# Изменить пароль пользователя
python manage.py changepassword username
```
