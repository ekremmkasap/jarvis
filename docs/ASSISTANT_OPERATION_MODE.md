# Assistant Operation Mode

Bu dosya, Jarvis icinde asistanin nasil davranmasi gerektigini tanimlar.

## Hedef

Kullanici her kucuk adim icin tekrar tekrar "devam et" demeden sistemin guvenli sekilde ilerlemesi.

## Varsayilan Mod

`build_autopilot`

Bu modda asistan:

- once okur, sonra yazar
- en kucuk dogru degisikligi tercih eder
- syntax check yapar
- guvenli smoke testleri uygular
- kullanicidan tekrar tekrar mikro-onay beklemez

## Hard Guard Cizgileri

Asistan bunlari yapmaz:

- secret/token/cookie/password degerlerini output'a yazmak
- `.env` icine kullanicinin adina gizli deger doldurmak
- destructive shell komutlari
- force push
- main/master kritik degisiklikleri sessizce yapmak
- geri alinmaz sistem degisiklikleri

## Uygun Isler

Asistan bu isleri sormadan ilerletebilir:

- kucuk kod patchi
- syntax fix
- task bus / dashboard / summary endpoint guncellemesi
- UI polish
- policy enforcement ve non-destructive backend iyilestirme

## Uygun Olmayan Isler

Asistan su konularda durur:

- secret girisi veya degistirilmesi
- hesap login/auth
- billing / plan / odeme
- branch protection veya force push

## Not

Bu mod, platformun gercek plan/build permission sistemini degistirmez.
Ama repo icinde asistanin beklenen davranisini kalici hale getirir.
