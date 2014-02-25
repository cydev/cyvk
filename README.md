cyvk transport
======

Форк VK4XMPP с целью сильного рефакторинга

Внимание: не рекомендуется к использованию до появления стабильной ветки

**Что точно будет реализовано**:
* Поддержка python 3

**Главные отличия от vk4xmpp**:
* Используется lxml вместо simplexml
* Полностью переработан xmpppy - выброшено всё, кроме необходимого для конкретно этого транспорта
* Добавлены в стек redis и go
* Транспорт разделен на несколько частей: long-polling клиент, транспорт и обработчик событий
* Убрана поддержка авторизации по паре логин-пароль
* Изменена форма регистрации