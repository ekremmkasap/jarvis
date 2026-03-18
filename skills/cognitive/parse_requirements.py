"""
Skill: parse_requirements
Kategori: cognitive
j.txt Section 5 - Requirement parsing skill
"""
import re
import logging

log = logging.getLogger("skill.parse_requirements")

MANIFEST = {
    "name": "parse_requirements",
    "version": "1.0",
    "category": "cognitive",
    "inputs": {"text": "str"},
    "outputs": {"requirements": "list", "constraints": "list", "keywords": "list"},
    "permissions": ["read"],
    "failure_modes": ["empty_input", "unparseable_text"],
    "logs": ["parsed_count", "constraint_count"]
}


def run(text: str) -> dict:
    if not text or not text.strip():
        log.warning("Empty input")
        return {"requirements": [], "constraints": [], "keywords": [], "error": "empty_input"}

    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    requirements = []
    constraints = []
    keywords = []

    constraint_markers = ["olmali", "gerekli", "zorunlu", "must", "should", "required", "sadece", "only"]
    keyword_pattern = re.compile(r"\b[A-Z][a-z]{2,}|\b[a-z]{4,}\b")

    for line in lines:
        lower = line.lower()
        if any(m in lower for m in constraint_markers):
            constraints.append(line)
        elif line.endswith("?"):
            pass  # soru - clarification needed
        else:
            requirements.append(line)

        found = keyword_pattern.findall(line)
        keywords.extend([k.lower() for k in found if len(k) > 3])

    keywords = list(dict.fromkeys(keywords))[:10]  # deduplicate, max 10

    log.info(f"Parsed: {len(requirements)} reqs, {len(constraints)} constraints, {len(keywords)} keywords")
    return {
        "requirements": requirements,
        "constraints": constraints,
        "keywords": keywords,
        "error": None
    }


if __name__ == "__main__":
    sample = """
    Sistem her zaman online olmali.
    Telegram botu mesajlari alip yanit vermeli.
    Kullanici kimlik dogrulamasi zorunlu.
    Raporlar PDF formatinda uretilmeli.
    """
    result = run(sample)
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
