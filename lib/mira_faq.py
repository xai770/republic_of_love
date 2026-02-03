"""
Mira FAQ Embedding Module

Parses Sage's FAQ corpus and provides embedding-based semantic matching.
Uses BGE-M3 via Ollama for multilingual support (DE/EN).

Usage:
    from lib.mira_faq import MiraFAQ
    
    faq = MiraFAQ()
    result = faq.find_answer(query, uses_du=True)
    
    if result['confidence'] == 'high':
        return result['answer']  # Direct match ≥0.85
    elif result['confidence'] == 'medium':
        # Use result['context'] with LLM
    else:
        # Freeform LLM
"""
import re
import json
import hashlib
import numpy as np
import requests
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass

# Embedding config
OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "bge-m3:567m"

# Matching thresholds (from Sage's spec)
HIGH_THRESHOLD = 0.85   # Direct curated answer
MEDIUM_THRESHOLD = 0.60  # LLM with FAQ context


@dataclass
class FAQEntry:
    """Single FAQ entry with all variants and answers."""
    faq_id: str
    category: str
    question_variants: list[str]
    answer_de: str  # Default du-form
    answer_en: str
    answer_informal_de: Optional[str] = None  # Extra casual du-form
    answer_sie_de: Optional[str] = None  # Formal Sie-form


@dataclass
class FAQMatch:
    """Result of FAQ matching."""
    confidence: Literal['high', 'medium', 'low']
    score: float
    faq_entry: Optional[FAQEntry]
    answer: Optional[str]  # Pre-selected based on uses_du
    context: Optional[str]  # For medium confidence (LLM grounding)


def get_embedding(text: str) -> Optional[np.ndarray]:
    """Get embedding from Ollama BGE-M3."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={'model': EMBED_MODEL, 'prompt': text},
            timeout=30
        )
        if resp.status_code == 200:
            return np.array(resp.json()['embedding'])
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
    return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class MiraFAQ:
    """
    Embedding-based FAQ matcher for Mira.
    
    Loads Sage's FAQ corpus, pre-computes embeddings for all question variants,
    and provides semantic matching with confidence thresholds.
    """
    
    def __init__(self, faq_path: Optional[Path] = None, cache_path: Optional[Path] = None):
        """
        Initialize FAQ matcher.
        
        Args:
            faq_path: Path to mira_faq.md (default: config/mira_faq.md)
            cache_path: Path to cache embeddings (default: data/mira_faq_embeddings.npz)
        """
        self.faq_path = faq_path or Path(__file__).parent.parent / 'config' / 'mira_faq.md'
        self.cache_path = cache_path or Path(__file__).parent.parent / 'data' / 'mira_faq_embeddings.npz'
        
        self.entries: list[FAQEntry] = []
        self.variant_embeddings: list[np.ndarray] = []
        self.variant_to_entry: list[int] = []  # Maps variant index to entry index
        
        self._load_faq()
        self._load_or_compute_embeddings()
    
    def _load_faq(self) -> None:
        """Parse the FAQ markdown file into structured entries."""
        if not self.faq_path.exists():
            raise FileNotFoundError(f"FAQ file not found: {self.faq_path}")
        
        content = self.faq_path.read_text(encoding='utf-8')
        
        # Split into FAQ blocks (### faq_xxx_nnn)
        blocks = re.split(r'\n### (faq_\w+_\d+)\n', content)
        
        # blocks[0] is header, then alternating: [id, content, id, content, ...]
        for i in range(1, len(blocks), 2):
            if i + 1 >= len(blocks):
                break
                
            faq_id = blocks[i]
            block_content = blocks[i + 1]
            
            entry = self._parse_faq_block(faq_id, block_content)
            if entry:
                self.entries.append(entry)
        
        print(f"📚 Loaded {len(self.entries)} FAQ entries")
    
    def _parse_faq_block(self, faq_id: str, content: str) -> Optional[FAQEntry]:
        """Parse a single FAQ block into an entry."""
        # Extract category
        cat_match = re.search(r'\*\*category:\*\*\s*(\w+)', content)
        category = cat_match.group(1) if cat_match else 'unknown'
        
        # Extract question variants
        variants_match = re.search(
            r'\*\*question_variants:\*\*\s*\n((?:- .+\n)+)',
            content
        )
        if not variants_match:
            return None
        
        variants_text = variants_match.group(1)
        variants = [v.strip('- \n') for v in variants_text.strip().split('\n') if v.strip().startswith('-')]
        
        if not variants:
            return None
        
        # Extract answers
        answer_de_match = re.search(
            r'\*\*answer_de:\*\*\s*\n([\s\S]*?)(?=\n\*\*answer_(?:en|sie_de|informal_de):\*\*|\n---|\Z)',
            content
        )
        answer_en_match = re.search(
            r'\*\*answer_en:\*\*\s*\n([\s\S]*?)(?=\n\*\*answer_(?:sie_de|informal_de):\*\*|\n---|\Z)',
            content
        )
        answer_sie_match = re.search(
            r'\*\*answer_sie_de:\*\*\s*\n([\s\S]*?)(?=\n\*\*answer_informal_de:\*\*|\n---|\Z)',
            content
        )
        answer_informal_match = re.search(
            r'\*\*answer_informal_de:\*\*\s*\n([\s\S]*?)(?=\n---|\Z)',
            content
        )
        
        answer_de = answer_de_match.group(1).strip() if answer_de_match else ""
        answer_en = answer_en_match.group(1).strip() if answer_en_match else ""
        answer_sie = answer_sie_match.group(1).strip() if answer_sie_match else None
        answer_informal = answer_informal_match.group(1).strip() if answer_informal_match else None
        
        if not answer_de:
            return None
        
        return FAQEntry(
            faq_id=faq_id,
            category=category,
            question_variants=variants,
            answer_de=answer_de,
            answer_en=answer_en,
            answer_informal_de=answer_informal,
            answer_sie_de=answer_sie
        )
    
    def _compute_content_hash(self) -> str:
        """Compute hash of FAQ content for cache invalidation."""
        content = self.faq_path.read_text(encoding='utf-8')
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _load_or_compute_embeddings(self) -> None:
        """Load cached embeddings or compute them."""
        content_hash = self._compute_content_hash()
        
        # Try loading from cache
        if self.cache_path.exists():
            try:
                cache = np.load(self.cache_path, allow_pickle=True)
                if cache['content_hash'].item() == content_hash:
                    self.variant_embeddings = list(cache['embeddings'])
                    self.variant_to_entry = list(cache['variant_to_entry'])
                    print(f"✅ Loaded {len(self.variant_embeddings)} cached embeddings")
                    return
                else:
                    print("📝 FAQ content changed, recomputing embeddings...")
            except Exception as e:
                print(f"⚠️ Cache load failed: {e}")
        
        # Compute embeddings
        self._compute_embeddings(content_hash)
    
    def _compute_embeddings(self, content_hash: str) -> None:
        """Compute embeddings for all question variants."""
        print("🔄 Computing FAQ embeddings...")
        
        self.variant_embeddings = []
        self.variant_to_entry = []
        
        for entry_idx, entry in enumerate(self.entries):
            for variant in entry.question_variants:
                emb = get_embedding(variant)
                if emb is not None:
                    self.variant_embeddings.append(emb)
                    self.variant_to_entry.append(entry_idx)
        
        print(f"✅ Computed {len(self.variant_embeddings)} embeddings")
        
        # Save cache
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez(
                self.cache_path,
                embeddings=np.array(self.variant_embeddings),
                variant_to_entry=np.array(self.variant_to_entry),
                content_hash=content_hash
            )
            print(f"💾 Cached embeddings to {self.cache_path}")
        except Exception as e:
            print(f"⚠️ Failed to cache embeddings: {e}")
    
    def find_answer(
        self, 
        query: str, 
        uses_du: bool = True,
        language: str = 'de'
    ) -> FAQMatch:
        """
        Find the best matching FAQ answer for a query.
        
        Args:
            query: User's question
            uses_du: True for informal "du", False for formal "Sie"
            language: 'de' or 'en'
            
        Returns:
            FAQMatch with confidence level and answer/context
        """
        if not self.variant_embeddings:
            return FAQMatch(
                confidence='low',
                score=0.0,
                faq_entry=None,
                answer=None,
                context=None
            )
        
        # Embed query
        query_emb = get_embedding(query)
        if query_emb is None:
            return FAQMatch(
                confidence='low',
                score=0.0,
                faq_entry=None,
                answer=None,
                context=None
            )
        
        # Find best match
        best_score = 0.0
        best_entry_idx = -1
        
        for i, variant_emb in enumerate(self.variant_embeddings):
            score = cosine_similarity(query_emb, variant_emb)
            if score > best_score:
                best_score = score
                best_entry_idx = self.variant_to_entry[i]
        
        # Determine confidence
        if best_score >= HIGH_THRESHOLD:
            confidence = 'high'
        elif best_score >= MEDIUM_THRESHOLD:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        # Get entry and select answer
        if best_entry_idx >= 0:
            entry = self.entries[best_entry_idx]
            
            # Select answer based on language and formality
            if language == 'en':
                answer = entry.answer_en or entry.answer_de
            elif uses_du:
                # Prefer informal, fall back to default du-form
                answer = entry.answer_informal_de or entry.answer_de
            else:
                # Sie-form: prefer answer_sie_de, fall back to answer_de
                answer = entry.answer_sie_de or entry.answer_de
            
            # Build context for medium confidence (LLM grounding)
            context = None
            if confidence == 'medium':
                context = self._build_context(entry, best_score)
            
            return FAQMatch(
                confidence=confidence,
                score=best_score,
                faq_entry=entry,
                answer=answer,
                context=context
            )
        
        return FAQMatch(
            confidence='low',
            score=best_score,
            faq_entry=None,
            answer=None,
            context=None
        )
    
    def _build_context(self, entry: FAQEntry, score: float) -> str:
        """Build context string for LLM grounding."""
        return f"""Related FAQ (similarity: {score:.2f}):
Category: {entry.category}
Question variants: {', '.join(entry.question_variants[:3])}
Curated answer: {entry.answer_de[:500]}..."""
    
    def get_top_matches(
        self, 
        query: str, 
        top_k: int = 3
    ) -> list[tuple[FAQEntry, float]]:
        """Get top-k matching FAQ entries (for debugging/analysis)."""
        query_emb = get_embedding(query)
        if query_emb is None:
            return []
        
        # Score all variants
        scores = {}
        for i, variant_emb in enumerate(self.variant_embeddings):
            entry_idx = self.variant_to_entry[i]
            score = cosine_similarity(query_emb, variant_emb)
            
            # Keep best score per entry
            if entry_idx not in scores or score > scores[entry_idx]:
                scores[entry_idx] = score
        
        # Sort and return top-k
        sorted_entries = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.entries[idx], score) for idx, score in sorted_entries]


# Singleton instance for API use
_faq_instance: Optional[MiraFAQ] = None


def get_faq() -> MiraFAQ:
    """Get or create the singleton FAQ instance."""
    global _faq_instance
    if _faq_instance is None:
        _faq_instance = MiraFAQ()
    return _faq_instance


# CLI for testing
if __name__ == '__main__':
    import sys
    
    faq = MiraFAQ()
    
    test_queries = [
        "Was kostet talent.yoga?",
        "Speichert ihr meine Daten?",
        "Wie funktioniert das Matching?",
        "Wer ist Doug?",
        "Ich bin verzweifelt",
        "Kannst du mir beim Kochen helfen?",  # Off-topic
    ]
    
    if len(sys.argv) > 1:
        test_queries = [' '.join(sys.argv[1:])]
    
    print("\n" + "="*60)
    for query in test_queries:
        result = faq.find_answer(query, uses_du=True)
        print(f"\n🔍 Query: {query}")
        print(f"   Confidence: {result.confidence} ({result.score:.3f})")
        if result.faq_entry:
            print(f"   Matched: {result.faq_entry.faq_id} ({result.faq_entry.category})")
        if result.confidence == 'high':
            print(f"   Answer: {result.answer[:100]}...")
        elif result.confidence == 'medium':
            print(f"   Context available for LLM grounding")
        else:
            print(f"   → Fallback to freeform LLM")
    print("\n" + "="*60)
