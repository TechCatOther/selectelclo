# Пример коннектора для подключения к OpenStack

## Авторзиация
Для подключения к openstack использует файл  ~/.selectelclo/app_clouds.yaml
В файле конфигрурации распологаются настройки авторизации с ключом приложения
Требуется поля:
  - auth_url
  - application_credential_id
  - application_credential_secret

Пример:
```
clouds:
  openstack:
    auth:
      auth_url: http://127.0.0.1/identity/v3
      application_credential_id: "some_id"
      application_credential_secret: "supersecret"
    region_name: "RegionOne"
    interface: "public"
    identity_api_version: 3
    auth_type: "v3applicationcredential"
```

## Интерфес API

Для интерфеса опередлен префикс версии в начале. Требуется, что бы все запросы с него начинались.
В данный момент доступны запросы со следующих версии
 - v1

### Список серверов

Для получения списка серверов с их IP адресами существует запрос GET
```
http://localhost/v1/servers/list
```

### Создание сервера
Для создания сервер есть запросы типа POST
```
http://localhost/v1/servers/create
```
Параметры для создания индийтичы OpenStackAPI.
[Документация](https://docs.openstack.org/api-ref/compute/#create-server)

### Список типов серверов

Для получения типа серверов возможно воспользоваться следующим GET запросом:
```
http://localhost/v1/flavors/list
```
ID пакетов возможно примернить для создания сервера