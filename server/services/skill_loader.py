"""
Dinamik Markdown-Tabanlı Skill Loader

Kullanım:
  skills/ dizinindeki .md dosyalarından runtime'da skill yükle.
  Dosya formatı: YAML frontmatter + Python code block
  
Örnek skill dosyası (skills/email_summarizer.md):
  ---
  name: email_summarizer
  description: E-postaları özetle
  params:
    - email_text: str
    - max_length: int = 200
  returns: str
  ---
  
  ```python
  def execute(email_text: str, max_length: int = 200) -> str:
      sentences = email_text.split('.')
      return '.'.join(sentences[:3])[:max_length]
  ```
"""

import os
import re
import json
import yaml
from pathlib import Path
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillDefinition:
    """Skill metadata ve execute function"""
    name: str
    description: str
    params: Dict[str, str]
    returns: str
    execute_fn: Callable
    file_path: str
    last_modified: float


class SkillRegistry:
    """Runtime skill registry — dinamik olarak skill'ler ekle/kaldır"""
    
    def __init__(self):
        self.skills: Dict[str, SkillDefinition] = {}
        self.file_watchers: Dict[str, float] = {}  # path -> last_modified
    
    def register(self, skill: SkillDefinition) -> None:
        """Skill'i registre et"""
        self.skills[skill.name] = skill
        self.file_watchers[skill.file_path] = skill.last_modified
        logger.info(f"✓ Skill '{skill.name}' loaded from {skill.file_path}")
    
    def unregister(self, name: str) -> None:
        """Skill'i kaldır"""
        if name in self.skills:
            skill = self.skills.pop(name)
            del self.file_watchers[skill.file_path]
            logger.info(f"✗ Skill '{name}' unloaded")
    
    def get(self, name: str) -> Optional[SkillDefinition]:
        """Skill'i al"""
        return self.skills.get(name)
    
    def list_skills(self) -> Dict[str, Dict[str, Any]]:
        """Tüm skill'leri listele"""
        return {
            name: {
                'description': skill.description,
                'params': skill.params,
                'returns': skill.returns,
                'file': skill.file_path
            }
            for name, skill in self.skills.items()
        }


def parse_skill_markdown(file_path: str) -> SkillDefinition:
    """
    Markdown skill dosyasını parse et.
    
    Format:
      ---
      name: skill_name
      description: Açıklama
      params:
        param1: type
        param2: type = default
      returns: return_type
      ---
      
      ```python
      def execute(**kwargs):
          return result
      ```
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Frontmatter'ı çıkar
    match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid skill format in {file_path}: missing YAML frontmatter")
    
    frontmatter_str = match.group(1)
    metadata = yaml.safe_load(frontmatter_str)
    
    # Python code block'unu çıkar
    code_match = re.search(r'```python\n(.*?)\n```', content, re.DOTALL)
    if not code_match:
        raise ValueError(f"Invalid skill format in {file_path}: missing Python code block")
    
    code_str = code_match.group(1)
    
    # Metadata'yı validate et
    required_fields = {'name', 'description', 'returns'}
    if not required_fields.issubset(metadata.keys()):
        raise ValueError(f"Missing required fields: {required_fields - set(metadata.keys())}")
    
    # Execute function'ı compile et (güvenlik: eval kullanma!)
    exec_globals = {'json': json}
    exec(code_str, exec_globals)
    
    if 'execute' not in exec_globals:
        raise ValueError(f"Skill {file_path} must define 'execute' function")
    
    execute_fn = exec_globals['execute']
    
    # SkillDefinition oluştur
    skill = SkillDefinition(
        name=metadata['name'],
        description=metadata.get('description', ''),
        params=metadata.get('params', {}),
        returns=metadata.get('returns', 'Any'),
        execute_fn=execute_fn,
        file_path=file_path,
        last_modified=os.path.getmtime(file_path)
    )
    
    return skill


def load_skills_from_directory(
    skills_dir: str,
    registry: Optional[SkillRegistry] = None,
    ignore_errors: bool = False
) -> SkillRegistry:
    """
    skills/ direktöründeki tüm .md dosyalarını yükle.
    
    Args:
      skills_dir: Skill dosyalarının dizini
      registry: Var olan registry (None ise yeni oluştur)
      ignore_errors: Hatalı skill'leri atla (True) / hata fırla (False)
    
    Returns:
      SkillRegistry
    """
    if registry is None:
        registry = SkillRegistry()
    
    skills_path = Path(skills_dir)
    if not skills_path.exists():
        logger.warning(f"Skills directory not found: {skills_dir}")
        return registry
    
    md_files = sorted(skills_path.glob('*.md'))
    logger.info(f"Found {len(md_files)} skill files in {skills_dir}")
    
    for file_path in md_files:
        try:
            skill = parse_skill_markdown(str(file_path))
            registry.register(skill)
        except Exception as e:
            error_msg = f"Failed to load skill {file_path}: {e}"
            if ignore_errors:
                logger.warning(error_msg)
            else:
                logger.error(error_msg)
                raise
    
    return registry


def reload_skill(
    name: str,
    file_path: str,
    registry: SkillRegistry
) -> bool:
    """
    Skill'i yeniden yükle (özellikle hot-reload için).
    
    Returns:
      True if reloaded, False if unchanged
    """
    current_modified = os.path.getmtime(file_path)
    old_skill = registry.get(name)
    
    if old_skill and old_skill.last_modified == current_modified:
        return False  # unchanged
    
    try:
        new_skill = parse_skill_markdown(file_path)
        registry.register(new_skill)
        logger.info(f"⟳ Skill '{name}' reloaded (modified: {current_modified})")
        return True
    except Exception as e:
        logger.error(f"Failed to reload skill {name}: {e}")
        return False


def watch_skills_directory(
    skills_dir: str,
    registry: SkillRegistry,
    interval_seconds: int = 5
) -> None:
    """
    Skills directive'yi izle ve değişiklikleri detect et (opsiyonel background task).
    
    Args:
      skills_dir: Skill dizini
      registry: SkillRegistry instance
      interval_seconds: Check interval
    """
    import time
    import threading
    
    def watcher():
        while True:
            try:
                for skill_name, skill in list(registry.skills.items()):
                    if os.path.exists(skill.file_path):
                        current_modified = os.path.getmtime(skill.file_path)
                        if current_modified > skill.last_modified:
                            reload_skill(skill_name, skill.file_path, registry)
                    else:
                        # Dosya silinmiş
                        registry.unregister(skill_name)
                
                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in skill directory watcher: {e}")
    
    thread = threading.Thread(target=watcher, daemon=True)
    thread.start()


# Export
__all__ = [
    'SkillRegistry',
    'SkillDefinition',
    'parse_skill_markdown',
    'load_skills_from_directory',
    'reload_skill',
    'watch_skills_directory'
]
