"""
Semantic Paraphraser and Perturbation Generator.
Creates semantic linguistic variations of operational optimization descriptions
to evaluate formulation invariance under prompt rephrasing (Gap 1).
"""

from typing import List
import re


class SemanticParaphraserTool:
    """Generates controlled linguistic transformations and perturbations of problem descriptions."""

    def __init__(self):
        # Operational synonyms mapping
        self.synonyms = {
            "require": ["mandate", "necessitate", "demand", "call for"],
            "must not exceed": ["shall be at most", "is capped at", "cannot surpass", "must stay under"],
            "at least": ["no fewer than", "a minimum of", "not less than"],
            "maximize": ["optimize to greatest possible", "increase to the highest level", "maximize total"],
            "minimize": ["reduce to lowest possible", "minimize total", "keep to an absolute minimum"],
            "cost": ["expenditure", "expense", "budget outlay", "operational fee"],
            "profit": ["net return", "revenue margin", "net gain"],
            "available": ["on hand", "accessible", "allocated", "dispatched"],
        }

    def generate_paraphrases(self, text: str, n_variants: int = 3) -> List[str]:
        """Generates n_variants of semantically equivalent texts."""
        variants = []
        sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip()]

        for variant_idx in range(n_variants):
            transformed_sentences = []
            for s in sentences:
                new_s = s
                # Apply deterministic synonym replacements based on variant index
                for key, syn_list in self.synonyms.items():
                    if key in new_s.lower():
                        replacement = syn_list[variant_idx % len(syn_list)]
                        pattern = re.compile(re.escape(key), re.IGNORECASE)
                        new_s = pattern.sub(replacement, new_s)
                transformed_sentences.append(new_s)

            # Variant 1: reverse sentence order of independent clauses if possible
            if variant_idx == 1 and len(transformed_sentences) > 2:
                # Keep objective (often first or last) and reorder inner constraints
                head = transformed_sentences[0]
                tail = transformed_sentences[-1]
                mid = transformed_sentences[1:-1]
                mid.reverse()
                variant_text = " ".join([head] + mid + [tail])
            else:
                variant_text = " ".join(transformed_sentences)

            variants.append(variant_text)

        return variants
