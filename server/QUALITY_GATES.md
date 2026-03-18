# Quality Gates Checklist (FAZ 1)

## Policy Gate (CoreAgent._policy_check)
- [ ] Goal bos degil
- [ ] Minimum uzunluk karsilaniyor
- [ ] Forbidden pattern yok

## Quality Gate (CoreAgent._quality_gate)
- [ ] Result None degil
- [ ] Error field bos
- [ ] Output field dolu

## Reviewer Checklist
- [ ] Artifact uretildi
- [ ] Plan bos degil
- [ ] Onceki task'larla cakisma yok

## Audit Trail
- Her policy_check karar'i /opt/jarvis/logs/audit.jsonl'e yazilir
