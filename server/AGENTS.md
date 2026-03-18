# Agent Rolleri ve Yetkiler (FAZ 1)

| Rol         | Yetkiler                        | Kısıt                    |
|-------------|----------------------------------|--------------------------|
| core        | tum yetkiler                    | policy gate gecmeli      |
| planner     | read, analyze                   | yazma yok                |
| implementer | read, write, execute            | forbidden list gecer     |
| reviewer    | read                            | SADECE okur, yazamaz     |
| curator     | read, memory_write              | sadece memory            |
| operator    | read, execute, system           | audit trail zorunlu      |

## Temel Kural (j.txt Section 7)
Sub-agent kendi yetkisini buyutemez. Her eylem policy_check skill'inden gecer.
