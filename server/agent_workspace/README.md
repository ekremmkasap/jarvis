# Agent Workspace

Bu klasor Jarvis'i tek bot yerine departman tabanli bir agent operating system olarak calistirmak icin kullanilir.

## Yapi
- `departments/<id>/AGENT.md` - departman kimligi, kurallar, style guide
- `departments/<id>/MEMORY.md` - kalici departman hafizasi
- `departments/<id>/skills/*.md` - departmana ozel SOP/skill dosyalari

## Ilk Departmanlar
- assistant
- builder
- guard
- research
- marketing
- sales

Bridge tarafinda `/team` veya karmaşık istek geldikten sonra runtime uygun departmanlari secer ve bu dosyalari context olarak kullanir.
