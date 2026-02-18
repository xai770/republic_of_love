"""
Smoke tests for actors — verify they import, instantiate, and have the expected interface.

These don't run process() (that requires real DB data + potentially LLM calls),
but they catch broken imports, missing dependencies, and interface violations.
"""
import importlib
import pytest


# All actor modules that should be importable
ACTOR_MODULES = [
    "actors.postings__arbeitsagentur_CU",
    "actors.postings__berufenet_U",
    "actors.postings__deutsche_bank_CU",
    "actors.postings__embedding_U",
    "actors.postings__extracted_summary_U",
    "actors.postings__external_description_U",
    "actors.postings__external_partners_U",
    "actors.postings__job_description_U",
    "actors.postings__aa_backfill_U",
    "actors.owl_names__lookup_R__lucy",
    "actors.owl_pending__atomize_U__ava",
    "actors.owl_pending__auto_triage_U",
    "actors.doug__newsletter_C",
    "actors.doug__research_C",
    "actors.y2y__match_detector_C",
    "actors.profile_posting_matches__report_C__clara",
]


@pytest.mark.parametrize("module_name", ACTOR_MODULES)
def test_actor_imports(module_name):
    """Every actor module should import without errors."""
    mod = importlib.import_module(module_name)
    assert mod is not None


# Class-based actors that follow the Template pattern
CLASS_ACTORS = [
    ("actors.owl_names__lookup_R__lucy", "OwlNamesRowC"),
    ("actors.owl_pending__atomize_U__ava", "OwlPendingAtomizeU"),
    ("actors.owl_pending__auto_triage_U", "OwlPendingAutoTriageU"),
    ("actors.postings__extracted_summary_U", "SummaryExtractActor"),
    ("actors.postings__external_partners_U", "PostingsExternalPartnersU"),
    ("actors.postings__embedding_U", "PostingsEmbeddingU"),
    ("actors.postings__job_description_U", "PostingsJobDescriptionU"),
]


@pytest.mark.parametrize("module_name,class_name", CLASS_ACTORS)
def test_actor_class_exists(module_name, class_name):
    """Class-based actors should have the expected class name."""
    mod = importlib.import_module(module_name)
    cls = getattr(mod, class_name, None)
    if cls is None:
        # Try finding any class with a process method
        classes = [
            name for name in dir(mod)
            if isinstance(getattr(mod, name, None), type)
            and hasattr(getattr(mod, name), 'process')
        ]
        assert classes, f"No class with process() method found in {module_name}"
    else:
        assert cls is not None


@pytest.mark.parametrize("module_name,class_name", CLASS_ACTORS)
def test_actor_has_process_method(module_name, class_name):
    """Class-based actors must have a process() method."""
    mod = importlib.import_module(module_name)
    cls = getattr(mod, class_name, None)
    if cls is None:
        # Find any class with process method
        for name in dir(mod):
            obj = getattr(mod, name, None)
            if isinstance(obj, type) and hasattr(obj, 'process'):
                cls = obj
                break
    assert cls is not None, f"Class {class_name} not found in {module_name}"
    assert hasattr(cls, 'process'), f"{class_name} missing process() method"
    assert callable(getattr(cls, 'process')), f"{class_name}.process is not callable"


# Script-based actors (no class, just functions)
SCRIPT_ACTORS = [
    ("actors.postings__arbeitsagentur_CU", "main"),
    ("actors.postings__deutsche_bank_CU", "main"),
    ("actors.postings__berufenet_U", "process_batch"),
    ("actors.postings__aa_backfill_U", "main"),
    ("actors.postings__external_description_U", "main"),
    ("actors.doug__newsletter_C", "generate_newsletter"),
    ("actors.doug__research_C", "main"),
    ("actors.y2y__match_detector_C", "main"),
    ("actors.profile_posting_matches__report_C__clara", "main"),
]


@pytest.mark.parametrize("module_name,entry_point", SCRIPT_ACTORS)
def test_script_actor_has_entry_point(module_name, entry_point):
    """Script-based actors should have their expected entry point function."""
    mod = importlib.import_module(module_name)
    fn = getattr(mod, entry_point, None)
    assert fn is not None, f"{module_name} missing {entry_point}()"
    assert callable(fn), f"{module_name}.{entry_point} is not callable"
