# Проверочные примеры

## Одна машина

За один час получены:

```text
RUN           = 30 min
IDLE          = 15 min
DOWN          = 10 min
SETUP         =  5 min
PLANNED_STOP  =  0 min
OFFLINE       =  0 min
nominalRate   = 100 pcs/hour
output        = 50 pcs
scrap         = 5 pcs
failureCount  = 2
```

Результат:

```text
coveredTime           = 60 min
plannedProductionTime = 60 min
operatingTime         = 45 min
availability          = 45 / 60 = 0.75
idealOutput           = 100 × 45/60 = 75 pcs
performance           = 50 / 75 = 0.6667
quality               = 45 / 50 = 0.90
oee                   = 0.75 × 0.6667 × 0.90 = 0.45
mtbf                  = 45 / 2 = 22.5 min
mttr                  = 10 / 2 = 5 min
```

## PLANNED_STOP и OFFLINE

Если из 60 минут 15 минут являются `PLANNED_STOP`, они остаются видимыми, но не входят в `plannedProductionTime`. Если 10 минут являются underlying `OFFLINE`, то:

```text
dataCoverage = (60 - 10) / 60 = 0.8333
```

Низкий coverage не превращает эти 10 минут в DOWN и не меняет Availability автоматически.

## Агрегация

Две машины одной единицы имеют:

```text
Machine A: operating=45 min, planned=60 min, output=50, ideal=75
Machine B: operating=30 min, planned=60 min, output=20, ideal=50
```

Правильный расчёт:

```text
availability = (45 + 30) / (60 + 60) = 0.625
performance  = (50 + 20) / (75 + 50) = 0.56
```

Среднее процентов машин не используется.
