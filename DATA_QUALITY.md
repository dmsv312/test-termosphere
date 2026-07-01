# DATA_QUALITY.md — проблемы качества данных

Каталог дефектов, найденных в выгрузке, и реакция на каждый. По ходу реализации каждый случай логируется в таблицу `data_quality_issues` (поля: `entity`, `entity_id`, `issue_type`, `action`, `details`), из которой собирается отчёт №7 «список проблем».

## Три реакции

- **fixed** — есть однозначно правильное значение, нормализуем.
- **quarantined** — данные бессмысленны, в core/отчёты не пускаем (но логируем, не удаляем).
- **flagged** — это бизнес-сигнал, а не грязь; оставляем и помечаем.

## Каталог

| # | Проблема | Где / пример | Реакция |
|---|---|---|---|
| 1 | Фантомная сделка `D9999` — нет в `deals`, но есть дети | `deal_products`, `payments` PAY005, `activities` A903, `production_orders` PO004 | quarantined (дети) |
| 2 | Фантомная сделка `D1012` — есть в истории, нет в `deals` | `stage_history` EVT005 | quarantined |
| 3 | Позиция ссылается на несуществующий товар | `deal_products` D1008 → `PR999` | quarantined |
| 4 | Контакт ссылается на несуществующую компанию | `contacts` P304 → `C999` | flagged, `company_id=NULL` |
| 5 | Стадия вне справочника | `deals` D1011 → `WAIT_CLIENT` | flagged, `stage=NULL` |
| 6 | Сделка без компании | `deals` D1006 | flagged `missing_company` |
| 7 | Дубль сделки (2 строки, конфликт) | `deals` D1008: 68000 `website` / 69000 `Website` | dedup → max(updated_at)=69000 |
| 8 | Дубль товара по SKU | `products` PR006 = PR001 (SKU `PNL-100`, cost 1490 vs 1450) | flagged `duplicate_sku` |
| 9 | Дубль события (2 идентичные строки) | `stage_history` EVT004 | dedup |
| 10 | Канал в разных регистрах/алфавитах | `deals.source`: Avito / avito / AVITO / Авито, website / Website | fixed → `sources` |
| 11 | Канал в затратах в разном регистре | `marketing_costs.source`: avito / AVITO / ... | fixed → `sources` |
| 12 | Кривой формат даты | `deals` D1010.created_at = `14.06.2026 09:20` | fixed (парсер) + flag |
| 13 | Кривой формат даты | `payments` PAY006.payment_date = `2026/06/15` | fixed (парсер) + flag |
| 14 | Телефон в другом формате | `contacts` P303 = `89170003003` | fixed → `+7...` |
| 15 | ИНН с ведущими нулями | `companies` (`0278123456` и т.п.) | fixed: грузить TEXT, не число |
| 16 | Отрицательная сумма сделки | `deals` D1007 = `-12000` | flagged `negative_amount` |
| 17 | Отрицательная оплата (возврат) | `payments` PAY006 = `-5000` `correction` | оставляем (легально), помечаем тип |
| 18 | WON без даты закрытия | `deals` D1009 (stage WON, `closed_at` пусто) | flagged, дату не выдумываем |
| 19 | Пустая валюта | `deals` D1010 | fixed → `RUB` + flag |
| 20 | Компания без данных | `companies` C205 (нет name/inn/industry) | flagged `incomplete` |
| 21 | Контакт без email | `contacts` P301 | flagged (minor) |
| 22 | Неактивный менеджер владеет сделкой | `users` U12 `active=false` → сделка D1004 | flagged (бизнес-сигнал) |
| 23 | Сделка без менеджера | `deals` D1011 | flagged |
| 24 | Нелегальный переход стадий | `stage_history` D1001: QUALIFICATION → PRODUCTION (минуя стадии) | flagged `illegal_transition` |
| 25 | Неоднозначная скидка | `deal_products` D1001/PR003 = 5000 | допущение: рубли; защита discount>суммы позиции |
| 26 | Переплата по сделке | D1005: сумма 92000, оплачено 100000 → остаток −8000 | flagged `overpayment` |
| 27 | Производство создано раньше своей сделки | PO003 создан 01.06, сделка D1005 — 05.06 (−4 дня) | flagged `temporal_inconsistency` |
| 28 | Неизвестный тип оплаты | `payments` PAY005 `unknown` (+ на фантомной сделке) | flagged |

## Сводка по видам

- **Битые связи (сироты):** 1, 2, 3, 4, 5, 6
- **Дубликаты:** 7, 8, 9
- **Нормализация значений:** 10, 11, 12, 13, 14, 15, 19
- **Бизнес-аномалии:** 16, 17, 18, 20, 21, 22, 23, 26, 28
- **Нарушения процесса/логики:** 24, 27
- **Допущение:** 25
