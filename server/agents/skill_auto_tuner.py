#!/usr/bin/env python3
"""
JARVIS SKILL AUTO-TUNER — Karpathy Autoresearch Döngüsü
Bir skill'in sistem promptunu otomatik iyileştirir:
  1. Mevcut promptu oku
  2. Varyasyon üret (LLM ile)
  3. Her ikisiyle test çalıştır
  4. Kalite skoru karşılaştır
  5. İyiyse kaydet, değilse geri al
  6. Tekrar et
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger("jarvis.skill_tuner")

# Kalite ölçüm kriterleri (0-10)
QUALITY_CRITERIA = """
Bir AI yanıtını 0-10 arasında değerlendir:
- 10: Mükemmel, tam isteneni verdi, kısa ve net
- 7-9: İyi, gerekli bilgiyi içeriyor
- 4-6: Orta, eksik veya gereksiz bilgi var
- 1-3: Kötü, yanlış veya alakasız
- 0: Tamamen başarısız

Sadece sayıyı yaz (örn: 8)
"""


class SkillAutoTuner:
    """
    Karpathy autoresearch döngüsü.
    Hedef: bir skill'in prompt kalitesini iteratif olarak artır.
    """

    def __init__(
        self,
        call_ollama_fn: Callable,
        data_dir: str = "server/logs/tuning",
    ):
        self.call_ollama = call_ollama_fn
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tuning_log = self.data_dir / "tuning_log.jsonl"

    def tune(
        self,
        skill_name: str,
        current_prompt: str,
        test_inputs: list[str],
        iterations: int = 3,
        model: str = "llama3.2:latest",
    ) -> dict:
        """
        Bir skill'in promptunu tune et.
        Returns: {"best_prompt": str, "improvement": float, "iterations": int}
        """
        log.info(f"[Tuner] {skill_name} tune başlıyor ({iterations} iterasyon)")

        best_prompt = current_prompt
        best_score = self._score_prompt(best_prompt, test_inputs, model)
        history = []

        for i in range(iterations):
            log.info(f"[Tuner] İterasyon {i+1}/{iterations} — mevcut skor: {best_score:.1f}")

            # Varyasyon üret
            candidate = self._generate_variation(best_prompt, history, model)
            if not candidate or candidate == best_prompt:
                log.info("[Tuner] Yeni varyasyon üretilemedi, atlıyorum")
                continue

            # Test et
            candidate_score = self._score_prompt(candidate, test_inputs, model)
            log.info(f"[Tuner] Varyasyon skoru: {candidate_score:.1f}")

            iteration_result = {
                "iteration": i + 1,
                "score_before": best_score,
                "score_after": candidate_score,
                "improved": candidate_score > best_score,
            }
            history.append(iteration_result)

            # İyiyse tut
            if candidate_score > best_score:
                best_prompt = candidate
                best_score = candidate_score
                log.info(f"[Tuner] İyileşme kabul edildi: {best_score:.1f}")
            else:
                log.info("[Tuner] İyileşme yok, geri alındı")

        improvement = best_score - self._score_prompt(current_prompt, test_inputs, model)

        result = {
            "skill": skill_name,
            "original_score": self._score_prompt(current_prompt, test_inputs, model),
            "final_score": best_score,
            "improvement": round(improvement, 2),
            "iterations": len(history),
            "best_prompt": best_prompt,
            "history": history,
            "ts": datetime.now().isoformat(),
        }

        self._log_result(result)
        return result

    def _score_prompt(self, prompt: str, test_inputs: list[str], model: str) -> float:
        """Test girdileriyle promptu çalıştır, kalite skorunu döndür."""
        scores = []
        for test_input in test_inputs[:3]:  # Maks 3 test
            try:
                # Skill yanıtı üret
                response = self.call_ollama(
                    model,
                    [{"role": "user", "content": test_input}],
                    system=prompt,
                    max_tokens=200,
                )

                # Yanıtı değerlendir
                score_text = self.call_ollama(
                    model,
                    [{"role": "user", "content": f"Bu yanıtı değerlendir:\n\nSoru: {test_input}\nYanıt: {response}\n\nSadece 0-10 arası sayı yaz:"}],
                    system=QUALITY_CRITERIA,
                    max_tokens=5,
                )

                score = self._parse_score(score_text)
                scores.append(score)
                time.sleep(0.5)  # Rate limit

            except Exception as e:
                log.error(f"Skorlama hatası: {e}")
                scores.append(5.0)  # Nötr skor

        return sum(scores) / len(scores) if scores else 5.0

    def _generate_variation(
        self, current_prompt: str, history: list, model: str
    ) -> Optional[str]:
        """Mevcut promptun daha iyi bir versiyonunu üret."""
        history_note = ""
        if history:
            last = history[-1]
            if last["improved"]:
                history_note = "Son varyasyon iyiydi, aynı yönde devam et."
            else:
                history_note = "Son varyasyon işe yaramadı, farklı bir yaklaşım dene."

        variation_prompt = f"""Aşağıdaki AI sistem promptunu İYİLEŞTİR.

MEVCUT PROMPT:
{current_prompt}

{f"NOT: {history_note}" if history_note else ""}

Kurallar:
- Daha net, daha kısa, daha odaklı yap
- Türkçe kal
- Sadece geliştirilmiş promptu yaz, başka hiçbir şey yazma
- Açıklama yapma, direkt promptu ver"""

        try:
            result = self.call_ollama(
                model,
                [{"role": "user", "content": variation_prompt}],
                system="Sen bir prompt mühendisisin. Sadece iyileştirilmiş promptu yaz.",
                max_tokens=500,
            )
            return result.strip() if result and len(result) > 20 else None
        except Exception as e:
            log.error(f"Varyasyon üretme hatası: {e}")
            return None

    def _parse_score(self, text: str) -> float:
        """LLM çıktısından sayısal skor çıkar."""
        import re
        numbers = re.findall(r'\b([0-9]|10)\b', text.strip())
        if numbers:
            return float(numbers[0])
        return 5.0

    def _log_result(self, result: dict):
        """Tuning sonucunu kaydet."""
        try:
            loggable = {k: v for k, v in result.items() if k != "best_prompt"}
            with open(self.tuning_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(loggable, ensure_ascii=False) + "\n")
        except Exception as e:
            log.error(f"Log yazma hatası: {e}")

    def get_tuning_history(self, skill_name: Optional[str] = None) -> list:
        """Tuning geçmişini oku."""
        if not self.tuning_log.exists():
            return []
        try:
            entries = []
            for line in self.tuning_log.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                    if skill_name is None or entry.get("skill") == skill_name:
                        entries.append(entry)
                except Exception:
                    pass
            return entries[-20:]  # Son 20
        except Exception:
            return []
