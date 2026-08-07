"""
Progressive Knowledge Base for Java → Cangjie translation.

Inspired by: ArkAdapter (ACM ISSTA 2025) - Adaptation Knowledge Repository
Paper: "Porting Software Libraries to OpenHarmony: Transitioning from TS/JS to ArkTS"

Core idea:
    Instead of relying solely on static document RAG retrieval, progressively
    accumulate real "Java → Cangjie" translation pairs during the translation
    process, categorized by scenario, and inject them as few-shot examples
    in subsequent translations. Let the LLM "learn from examples" rather
    than "read documentation".

Relationship to existing RAG:
    - This is NOT a replacement; it is an upper-layer supplement.
    - Existing RAG continues to query Cangjie official documentation.
    - Progressive KB is checked BEFORE RAG: first look for existing translation
      examples, then fall back to documentation if none found.

Usage:
    from src.java.progressive_kb import get_progressive_kb

    kb = get_progressive_kb()

    # Before translation: retrieve few-shot examples
    examples = kb.retrieve(java_code=current_fragment, top_k=3)

    # After verification (compile pass): store the pair
    kb.add_example(
        java_code=fragment.java_code,
        cangjie_code=translated_code,
        signature="com.example.MyClass.myMethod",
        scenario="method_with_generics",
        compile_pass=True,
    )

Data layout:
    data/java/progressive_kb/
        type_mappings.json      # Type mapping cache
        translation_pool.json   # Translation pair pool (incremental)
        scenarios.json          # Scenario classification index
"""

from src.java.progressive_kb.progressive_kb import (
    ProgressiveKB,
    TranslationPair,
    TypeMapping,
    ScenarioClassifier,
    get_progressive_kb,
)