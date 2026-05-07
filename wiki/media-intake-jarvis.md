# Media Intake - Jarvis

Jarvis artik linkleri kendi runtime'i icinde isleyebilir:

- `/izle <url>`: Instagram/Reels/YouTube/PDF kaynagini Jarvis'e alir.
- `/reel <instagram-url>`: Instagram Reel icin yt-dlp metadata, rapor ve wiki notu uretir.
- `/media --download <url>`: metadata yaninda video dosyasini da indirir.
- `/repo-index`: repo dosya manifestini `wiki/repo-file-index.md` ve `wiki/repo-file-index.json` olarak gunceller.
- `/repo-find <dosya>`: manifest icinde dosya yolu arar.

## Guvenlik

Cookie veya API key icerigi wiki'ye yazilmaz. Media intake sadece dosya yolu ve metadata yazar.

Instagram icin varsayilan guvenli yol export edilmis cookie dosyasidir:

`JARVIS_YTDLP_COOKIES=server/instagram_cookies.txt`

Chrome/Edge/Firefox session cookie okuma destegi kodda vardir ama otomatik acik degildir. Bu yol sadece kullanici acik izin verirse `JARVIS_YTDLP_COOKIES_FROM_BROWSER=chrome` gibi bir env ile acilmalidir.

## Cikti

Her islem `outputs/media_intake/<tarih>_<slug>/` altina yazar:

- `metadata.json`
- `report.md`
- indirildiyse video/media dosyasi

## Not

Instagram tarafinda transcript yoksa ilk asama metadata/caption alir. Derin gorsel veya konusma analizi icin video indirme veya ayrica transkripsiyon gerekir.

