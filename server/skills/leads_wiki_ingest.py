"""
CSV to Wiki Markdown Ingestion
Karpathy LLM Wiki pattern
"""

import csv
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

class LeadsWikiIngester:
    def __init__(self, wiki_root="leads-wiki"):
        self.wiki_root = Path(wiki_root)
        self.wiki_dir = self.wiki_root / "wiki"
        self.niche_dir = self.wiki_dir / "niche"
        self.niche_dir.mkdir(parents=True, exist_ok=True)
        self.leads = []
        self.niches = defaultdict(list)
        
    def load_csv(self, csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.leads = list(reader)
        print("OK Loaded " + str(len(self.leads)) + " leads")
    
    def extract_niche(self, biography, username):
        if not biography:
            return "other"
        
        bio_lower = (biography + " " + username).lower()
        
        niche_map = {
            "fitness": ["fitness", "trainer", "workout", "gym", "crossfit"],
            "coaching": ["coach", "coaching", "mentor", "consultant"],
            "agency": ["agency", "marketing", "advertising", "digital", "seo"],
            "ecommerce": ["shop", "store", "seller", "products"],
            "creator": ["content", "creator", "influencer", "blogger"],
        }
        
        for niche, keywords in niche_map.items():
            if any(k in bio_lower for k in keywords):
                return niche
        return "other"
    
    def extract_keywords(self, biography):
        if not biography:
            return []
        
        bio_lower = biography.lower()
        words = [w.strip(".,!?@#") for w in bio_lower.split() if len(w) > 3]
        stop = {"and", "the", "for", "with", "your", "but"}
        return [w for w in words if w not in stop][:3]
    
    def create_lead_markdown(self, lead):
        lead_id = lead.get('number', '0').zfill(6)
        username = lead.get('username', 'unknown')
        full_name = lead.get('full_name', '')
        biography = lead.get('biography', '')
        followers = lead.get('followers_count', '0')
        email = lead.get('email', '')
        city = lead.get('city', '')
        external_url = lead.get('external_url', '')
        
        niche = self.extract_niche(biography, username)
        keywords = self.extract_keywords(biography)
        
        lines = ["# @" + username, ""]
        lines.append("## Profile")
        lines.append("- Name: " + (full_name or "N/A"))
        lines.append("- Followers: " + followers)
        lines.append("- Bio: " + (biography or "N/A"))
        lines.append("- City: " + (city or "N/A"))
        lines.append("- Email: " + (email or "Not found"))
        if external_url:
            lines.append("- Website: [Link](" + external_url + ")")
        lines.append("")
        lines.append("## Classification")
        lines.append("- Niche: [[" + niche + "]]")
        kw = ", ".join(keywords) if keywords else "N/A"
        lines.append("- Keywords: " + kw)
        
        try:
            fol_int = int(followers or 0)
            if fol_int >= 50000:
                tier = "HIGH"
            elif fol_int >= 5000:
                tier = "MID"
            else:
                tier = "LOW"
        except:
            tier = "UNKNOWN"
        lines.append("- Tier: " + tier)
        lines.append("")
        lines.append("- ID: " + lead_id)
        lines.append("")
        
        md = "\n".join(lines)
        return md, niche
    
    def ingest_all(self):
        print("\nProcessing " + str(len(self.leads)) + " leads...")
        
        for i, lead in enumerate(self.leads):
            md_content, niche = self.create_lead_markdown(lead)
            lead_id = lead.get('number', '0').zfill(6)
            username = lead.get('username', 'unknown').replace('/', '_')
            
            lead_file = self.wiki_dir / ("lead_" + lead_id + "_" + username + ".md")
            with open(lead_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            self.niches[niche].append("lead_" + lead_id + "_" + username)
            
            if (i + 1) % 5 == 0:
                print("  OK " + str(i + 1) + "/" + str(len(self.leads)))
        
        self._create_niche_pages()
        self._create_index()
        self._create_log()
    
    def _create_niche_pages(self):
        for niche, leads in self.niches.items():
            if niche == "other":
                continue
            
            niche_lines = ["# " + niche.upper(), ""]
            niche_lines.append("Total leads: " + str(len(leads)))
            niche_lines.append("")
            for lead in leads[:10]:
                niche_lines.append("- [[" + lead + "]]")
            if len(leads) > 10:
                niche_lines.append("... and " + str(len(leads) - 10) + " more")
            
            niche_file = self.niche_dir / (niche + ".md")
            with open(niche_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(niche_lines))
            print("  OK Niche: " + niche)
    
    def _create_index(self):
        lines = ["# Leads Index", ""]
        lines.append("Total: " + str(len(self.leads)) + " leads")
        lines.append("")
        lines.append("## By Niche")
        for niche in sorted(self.niches.keys()):
            if niche != "other":
                lines.append("- [[" + niche + "]] (" + str(len(self.niches[niche])) + ")")
        
        index_file = self.wiki_dir / "index.md"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        print("  OK Index created")
    
    def _create_log(self):
        log_entry = "## " + datetime.now().strftime('%Y-%m-%d %H:%M') + " - CSV ingest OK\n"
        log_file = self.wiki_dir / "log.md"
        
        if log_file.exists():
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        else:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("# Log\n\n" + log_entry)
        print("  OK Log updated")


def main():
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "leads-wiki/raw/test_batch.csv"
    
    ingester = LeadsWikiIngester()
    ingester.load_csv(csv_path)
    ingester.ingest_all()
    print("\nOK Done!")


if __name__ == "__main__":
    main()
