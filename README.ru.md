# suz-sdk-python

Python SDK для **СУЗ API 3.0** (СУЗ-Облако 4.0, версия API 3.0.33).

Оборачивает HTTP API системы управления заказами кодов маркировки CRPT в удобный типизированный Python-интерфейс.
Это **Итерация 1** — базовое ядро. Что реализовано, а что нет — в разделе [Область применения](#область-применения).

[English version](README.md)

---

## Установка

```bash
pip install -e ".[dev]"   # установка в режиме разработки с тестовыми зависимостями
```

Требуется Python 3.11+.

---

## Быстрый старт

```python
from suz_sdk import SuzClient, Environment

client = SuzClient(
    oms_id="cdf12109-10d3-11e6-8b6f-0050569977a1",
    environment=Environment.SANDBOX,
    client_token="ваш-клиентский-токен",  # получается через процедуру авторизации
)

info = client.health.ping()
print(info.oms_version)   # например, "3.1.8.0"
print(info.api_version)   # например, "2.0.0.54"
```

---

## Конфигурация

`SuzClient` принимает все настройки через аргументы конструктора:

| Аргумент           | Тип                   | По умолчанию | Описание                                                   |
|--------------------|-----------------------|--------------|------------------------------------------------------------|
| `oms_id`           | `str`                 | обязательный | UUID экземпляра СУЗ (параметр запроса `omsId`)             |
| `environment`      | `Environment`         | `SANDBOX`    | Определяет базовый URL                                     |
| `base_url`         | `str \| None`         | `None`       | Явное переопределение базового URL (специфично для стенда) |
| `client_token`     | `str \| None`         | `None`       | Заранее полученный `clientToken` для авторизации           |
| `signer`           | `BaseSigner \| None`  | `None`       | Реализация подписи для заголовка `X-Signature`             |
| `oms_connection`   | `str \| None`         | `None`       | UUID зарегистрированной установки интеграционного решения  |
| `registration_key` | `str \| None`         | `None`       | Код регистрации интеграционного решения от CRPT            |
| `timeout`          | `float`               | `30.0`       | Таймаут HTTP-запроса в секундах                            |
| `verify_ssl`       | `bool`                | `True`       | Проверка TLS-сертификатов                                  |

### Окружения

| Константа                | Базовый URL (подтверждён для эндпоинта регистрации) |
|--------------------------|-----------------------------------------------------|
| `Environment.SANDBOX`    | `https://suz-integrator.sandbox.crptech.ru`         |
| `Environment.PRODUCTION` | `https://suzgrid.crpt.ru:16443`                     |

> **Примечание:** Базовый URL основного API (для ping, заказов и т.д.) в документации СУЗ
> обозначается как `<url стенда>` и зависит от конкретного экземпляра ОМС.
> Передавайте собственный `base_url`, если ваш стенд использует другой адрес.

---

## Авторизация

API СУЗ использует маркер безопасности `clientToken` (§9.1 документа API).

Ключевые факты:
- Для каждой установки интеграционного решения (`omsConnection`) активен **только один** токен
- Повторный выпуск токена **инвалидирует** предыдущий
- Время действия токена через True API (ГИС МТ): **10 часов**
- Время действия токена через ИС МДЛП: указывается в ответе при выдаче

**Итерация 1** требует передавать `client_token` вручную.
**Итерация 2** добавит `TokenManager` с автоматическим обновлением.

```python
# Сейчас: получите токен внешним способом и передайте его:
client = SuzClient(
    oms_id="...",
    client_token="1cecc8fb-fb47-4c8a-af3d-d34c1ead8c4f",
)
```

---

## Абстракция подписи

Ряд эндпоинтов требует подписи запроса в заголовке `X-Signature`.

Требования (§2.3.1 документа API):
- Формат: **откреплённая подпись CMS** (IETF RFC 5652), **не** прикреплённая (сервер вернёт HTTP 413)
- Алгоритм: российский ГОСТ (ГОСТ Р 34.10-2012, ГОСТ Р 34.11-2012)
- Кодировка: Base64
- Для GET-запросов: подписываются `REQUEST_PATH + QUERY_STRING`
- Для POST-запросов: подписывается тело запроса в виде сырых байт JSON

### Реализация своего signer

```python
from suz_sdk import BaseSigner

class МойКриптоПроСайнер:
    def sign_bytes(self, payload: bytes) -> str:
        # Вызов CLI или библиотеки КриптоПро
        return base64_encoded_detached_cms_signature

client = SuzClient(
    oms_id="...",
    signer=МойКриптоПроСайнер(),
)
```

### NoopSigner (только для тестов)

```python
from suz_sdk import NoopSigner

# Возвращает пустую строку — реальный сервер отклонит запросы,
# требующие X-Signature
client = SuzClient(oms_id="...", signer=NoopSigner())
```

---

## Обработка ошибок

Все исключения SDK наследуются от `SuzError`:

```
SuzError
├── SuzTransportError       # сетевая ошибка
│   └── SuzTimeoutError     # таймаут запроса
├── SuzAuthError            # HTTP 401
│   └── SuzTokenExpiredError
├── SuzSignatureError       # HTTP 413 (прикреплённая подпись отклонена)
├── SuzValidationError      # HTTP 400
├── SuzApiError             # прочие ошибки (есть .status_code, .error_code, .raw_body)
└── SuzRateLimitError
```

```python
from suz_sdk import SuzClient, SuzApiError, SuzAuthError, SuzTimeoutError

try:
    info = client.health.ping()
except SuzTimeoutError:
    print("Запрос завис по таймауту")
except SuzAuthError:
    print("Токен недействителен или истёк")
except SuzApiError as e:
    print(f"Ошибка API {e.status_code}: {e}")
```

---

## Запуск тестов

```bash
pip install -e ".[dev]"
pytest
```

---

## Область применения

### Итерация 1 — Ядро (текущий релиз)

- `pyproject.toml` и структура пакета в `src/suz_sdk/`
- Точка входа `SuzClient`
- `SuzConfig` + `Environment`
- Типизированная иерархия исключений
- Протокол `BaseSigner` + `NoopSigner`
- `HttpxTransport` с полным маппингом ошибок
- `client.health.ping()` — проверка доступности и версии СУЗ

### Ещё не реализовано (будущие итерации)

- `TokenManager` — автообновление, учёт TTL, потокобезопасное обновление
- `client.integration.register_connection()`
- `client.auth.authenticate()`
- `client.orders.*` — create, get_status, get_codes, close
- `client.reports.*` — send_utilisation, get_status
- `client.receipts.*`
- Асинхронный клиент
- Интеграция с КриптоПро

---

## Архитектура

```
src/suz_sdk/
├── __init__.py              # публичный API пакета
├── client.py                # точка входа SuzClient
├── config.py                # SuzConfig + Environment
├── exceptions.py            # иерархия исключений
├── signing/
│   ├── base.py              # протокол BaseSigner
│   └── noop.py              # NoopSigner
├── transport/
│   ├── base.py              # протокол BaseTransport + Request/Response
│   └── httpx_transport.py   # реализация на httpx
└── api/
    └── health.py            # HealthApi.ping()
```

Ответственности слоёв:

| Слой          | Ответственность                                              |
|---------------|--------------------------------------------------------------|
| `transport`   | HTTP-механика, таймауты, парсинг ответов, маппинг ошибок     |
| `signing`     | `bytes → Base64 откреплённая CMS-подпись`                   |
| `api`         | Высокоуровневые типизированные методы (бизнес-логика)        |
| `client`      | Связывает слои, добавляет заголовки авторизации              |
