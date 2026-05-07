# Contract: Persona Commands and Behaviors

## 1. Persona Switch

### Inputs

- `Seda ile konus`
- `Buse'ye gec`
- `Mert'i cagir`
- `Jarvis'e don`

### Expected Behavior

1. Persona resolve edilir
2. `state/active_agent.json` guncellenir
3. Chat session active persona prompt'u ile devam eder
4. Assistant switch acknowledgement dondurur

### Expected Reply Shape

```text
Baglaniyor: Seda... Merhaba, Seda burada. Hangi kodla basliyoruz?
```

---

## 2. Save to Obsidian

### Inputs

- `bunu kaydet: ...`
- `not al: ...`
- `Obsidian'a yaz: ...`

### Expected Behavior

1. Active persona belirlenir
2. Vault path cozulur
3. `%OBSIDIAN_VAULT_PATH%/personas/<persona_id>/` altina markdown note yazilir
4. Assistant note path veya basarili save ozeti dondurur

### Failure Mode

- Vault path yoksa: net fail-soft mesaj
- Invalid path traversal denemesi ignore edilir; note sadece persona klasorune yazilir

---

## 3. Recall from Obsidian

### Inputs

- `bu konuda ne biliyorsun?`
- `arastirdiklarimizi ozetle`
- `gecen notlarimi getir`

### Expected Behavior

1. Sadece aktif persona klasoru taranir
2. Keyword + recency ile ilgili note'lar secilir
3. En az bir note varsa response icinde note referansi veya note ozeti bulunur

---

## 4. Swarm Task

### Inputs

- `su repoyu analiz et`
- `arastir ve ozetle`
- `dosyalari oku, hatalari listele, refactor oner`

### Expected Behavior

1. Complexity detector gorevi multi-step olarak isaretler
2. Persona `sub_agents` listesine gore step plan olusturur
3. Step'ler sirali veya paralel yurutulur
4. Final output tek persona cevabi olarak dondurulur

### Failure Mode

- Tek step fail olursa final response `su adimda sorun cikti` bilgisini icerir
- Tum runtime ckmemeli; diger step sonuclari korunmali

---

## 5. Fleet Summary

### Input

- `tum ajanlarin ozetini ver`

### Expected Behavior

1. Her persona klasorunden son uygun note okunur
2. Persona bazli ozetler tek cevapta konsolide edilir
3. Eksik note varsa ilgili persona `note yok` olarak raporlanir
