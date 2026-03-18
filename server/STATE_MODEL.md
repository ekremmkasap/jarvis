# Task State Model (FAZ 1)

## Durumlar
queued -> planning -> running -> reviewing -> done
                   -> blocked
                   -> failed
                   -> waiting (dis bagimlilik)
                   -> cancelled

## Gecis Kurallari
- Her gecis event olarak kaydedilir (timestamp, from, to, reason)
- failed/blocked durumundan recovery: yeni Task olustur
- done sonrasi working_memory'e kaydedilir

## Veri Modeli (Task)
id, title, goal, constraints, inputs, acceptance_criteria,
status, plan, artifacts, events, result, created_at
