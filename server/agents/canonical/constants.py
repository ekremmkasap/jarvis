from __future__ import annotations


CANONICAL_AGENT_IDS = (
    "planner",
    "repo_analyst",
    "developer",
    "reviewer",
    "debug",
    "release",
    "docs",
    "voice_narrator",
    "mission_control",
)


CANONICAL_AGENT_KEYWORDS = {
    "planner": ("plan yap", "hedef", "gorev olustur", "ne yapayim"),
    "repo_analyst": ("repo analiz", "saglik raporu", "git durum", "kod durumu"),
    "developer": ("kod yaz", "implement", "feature ekle", "degistir"),
    "reviewer": ("review", "incele", "pr kontrol", "kod incele"),
    "debug": ("hata", "debug", "neden calismiyor", "fix"),
    "release": ("release", "changelog", "versiyon", "ne degisti"),
    "docs": ("dokumantasyon", "readme guncelle", "acikla"),
    "mission_control": ("sistem durumu", "agent saglik", "ne calisiyor"),
    "voice_narrator": (),
}
