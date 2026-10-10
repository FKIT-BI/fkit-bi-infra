# Примеры контрактов

## Компактный Scenario

```json
{
  "enterpriseId": "10000000-0000-0000-0000-000000000001",
  "code": "LINE_A_DEMO",
  "name": "Демонстрация линии A",
  "cycleMode": "LOOP",
  "machineTargets": [{
    "machineId": "20000000-0000-0000-0000-000000000001",
    "baseBehaviors": [{
      "signalId": "30000000-0000-0000-0000-000000000001",
      "behavior": {
        "generationIntervalMs": 5000,
        "model": "NORMAL",
        "mean": 65.0,
        "standardDeviation": 2.0
      }
    }]
  }],
  "phases": [{
    "code": "NORMAL",
    "name": "Нормальная работа",
    "durationMs": 600000,
    "expectedState": "RUN",
    "behaviorOverrides": []
  }, {
    "code": "OVERHEAT",
    "name": "Перегрев",
    "durationMs": 180000,
    "expectedState": "DOWN",
    "behaviorOverrides": [{
      "signalId": "30000000-0000-0000-0000-000000000001",
      "action": "REPLACE",
      "behavior": {
        "generationIntervalMs": 5000,
        "model": "RAMP",
        "from": 65.0,
        "to": 110.0,
        "durationMs": 180000,
        "repeat": false
      }
    }]
  }]
}
```

## Historical Run

```json
{
  "mode": "HISTORICAL",
  "scenarioId": "40000000-0000-0000-0000-000000000001",
  "randomSeed": 482901,
  "from": "2026-10-01T00:00:00Z",
  "to": "2026-10-02T00:00:00Z"
}
```

## Analytics handoff

```json
{
  "enterpriseId": "10000000-0000-0000-0000-000000000001",
  "machineIds": ["20000000-0000-0000-0000-000000000001"],
  "from": "2026-10-01T00:00:00Z",
  "to": "2026-10-02T00:00:00Z",
  "generatedThrough": "2026-10-02T00:00:00Z"
}
```
