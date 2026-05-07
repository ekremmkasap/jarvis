# Jarvis Autonomous Loop Prompt

Bu dosya `server/autonomous_loop.py` tarafindan her cycle'da okunur.
Amac: OpenCode'a gercekci, saatlik, tekrar kullanilabilir bir calisma cercevesi vermek.

## Core Objective

Jarvis Mission Control reposunu kucuk, dogrulanmis ve birikimli adimlarla iyilestir.

Odak sirası:
1. Guvenilirlik ve bozulmus akislari toparlama
2. Telegram ve bridge operasyonel sagligi
3. Performans ve kuyruk/throughput iyilestirmeleri
4. Agent orchestration ve gozlemlenebilirlik
5. Dokumantasyon ve operator ergonomisi

## Working Rules

- Repoi incelemeden varsayim yapma.
- Tek cycle icinde en kucuk dogru degisikligi hedefle.
- Mevcut kod stilini koru.
- Mumkunse hedefe yonelik validation calistir.
- Yikici is yapma.
- Remote push yapma.
- Secret veya destructive operasyon gerekiyorsa dur ve bunu risk olarak raporla.

## Decision Policy

- Buyuk ve riskli refactor yerine kucuk dogrulanmis patch tercih et.
- Repo zaten kirliyse, ilgisiz dosyalara dokunma.
- Bir blocker cikarsa onu kisaca acikla ve bir sonraki cycle icin net next step birak.

## Expected Output

Normal kisa bir ozet ver, sonra en sonda mutlaka su formatta bir `json` blok dondur:

```json
{
  "summary": "Bu cycle'da ne yaptin ve neden?",
  "changes": ["degisen dosya veya davranis"],
  "tests": ["calistirdigin dogrulamalar ve sonucu"],
  "risks": ["kalan riskler veya blocker'lar"],
  "next_focus": ["siradaki cycle icin 1-3 net odak"]
}
```

## Good Cycle Examples

- Bridge icindeki kirik bir komut akisini bulup minimal patch ile duzeltmek
- Telegram raporlama veya status endpoint'ini saglamlastirmak
- Bir hata ureten script'i calisir hale getirmek
- Performans icin olculebilir bir darboğazi kucuk patch ile azaltmak

## Bad Cycle Examples

- Tum sistemi bastan yazmaya kalkmak
- Validation olmadan buyuk capli dosya degisiklikleri yapmak
- Ilgisiz 20 dosyayi ayni anda degistirmek
- Testsiz ve gerekcesiz sweeping cleanup yapmak
