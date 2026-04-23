# Парсер контрактов zakupki.gov.ru

Скрипт для сбора информации о государственных контрактах с сайта Единой информационной системы в сфере закупок (zakupki.gov.ru). Данные сохраняются в CSV и PostgreSQL.

## Возможности

- Парсинг контрактов по 50 на странице
- Извлечение информации о заказчике и поставщике
- Очистка данных (ИНН, КПП, телефон, email)
- Сохранение в CSV с последующей загрузкой в PostgreSQL
- Автоматическое обновление существующих записей

## Установка

### Требования

- Python 3.10+
- Docker и Docker Compose (для базы данных)
- PostgreSQL 15 (опционально, если не через Docker)

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Настройка базы данных

1. Запуск контейнера с PostgreSQL:

```bash
docker-compose up -d
```

2. Проверка работы контейнера:

```bash
docker ps | grep postgres
```

### Настройка конфигурации

Проверка настроек подключения к БД в файле `config.py`:

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zakupki_db',
    'user': 'zakupki_user',
    'password': 'zakupki_pass'
}
```

## Запуск

### Парсинг контрактов

```bash
python main.py
```

Скрипт запросит ввести количество страниц (по 50 контрактов на странице). После выполнения появится два файла:

- `contracts_raw.csv` — сырые данные
- `contracts_clean.csv` — очищенные данные

### Заливка данных в PostgreSQL

```bash
python database.py
```


## Структура проекта

```
contracts_analysis/
├── v1/
│   ├── __init__.py
│   ├── config.py              # Настройки (URL, заголовки, БД)
│   ├── contracts_clean.csv    # Очищенные данные о контрактах   
│   ├── contracts_raw.csv      # Сырые данные до очистки
│   ├── database.py            # Заливка данных в PostgreSQL
│   ├── main.py                # Основной скрипт парсинга контрактов
│   ├── parsers.py             # Функции для парсинга HTML страниц
│   └── utils.py               # Функции для очистки данных
├── .gitignore
├── .python-version
├── docker-compose.yml         # Конфигурация контейнера PostgreSQL
├── get-docker.sh
├── README.md
└── requirements.txt           # Python-зависимости
```

## SQL-запросы для проверки

```bash
# Количество записей в БД
docker exec -it zakupki_postgres psql -U zakupki_user -d zakupki_db -c "SELECT COUNT(*) FROM contracts;"

# Первые 5 записей
docker exec -it zakupki_postgres psql -U zakupki_user -d zakupki_db -c "SELECT * FROM contracts LIMIT 5;"
```

## Возможные ошибки и их решение

### 1. Ошибка 429 Too Many Requests

**Причина:** слишком частые запросы к сайту

**Решение:** увеличить задержки в `main.py`:

```python
time.sleep(1.5)   # между карточками
time.sleep(3)     # между страницами
```

### 2. Connection refused (порт 5432)

**Причина:** PostgreSQL не запущен

**Решение:**

```bash
docker-compose up -d
# или
docker start zakupki_postgres
```

### 3. password authentication failed

**Причина:** неверный пароль в `config.py`

**Решение:** проверить пароль в `DB_CONFIG` или сбросить пароль в PostgreSQL:

```bash
docker exec -it zakupki_postgres psql -U postgres -c "ALTER USER zakupki_user WITH PASSWORD 'zakupki_pass';"
```

### 4. Column "supplier_inn.1" does not exist

**Причина:** дублирующиеся колонки в CSV

**Решение:** удалить дубликаты:

```bash
python -c "
import pandas as pd
df = pd.read_csv('contracts_clean.csv')
df = df.loc[:, ~df.columns.duplicated()]
df.to_csv('contracts_clean.csv', index=False)
"
```

## Рекомендации

- Не ставить задержки меньше 1.5 секунд — сайт может забанить
- На парсинг 100 страниц (5000 контрактов) уходит около 2.5 часов
- При ошибках бана подождать 10-15 минут и продолжить
