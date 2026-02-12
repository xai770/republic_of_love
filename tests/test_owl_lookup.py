"""
Unit tests for owl_lookup() three-tier ambiguity handling.
Uses a mock cursor to simulate OWL query results.
"""
import pytest
from unittest.mock import MagicMock
from actors.postings__berufenet_U import owl_lookup


def _make_row(owl_id, canonical_name, berufenet_id, kldb, qualification_level):
    """Build a dict that looks like a psycopg2 RealDictRow."""
    return {
        'owl_id': owl_id,
        'canonical_name': canonical_name,
        'berufenet_id': str(berufenet_id),
        'kldb': kldb,
        'qualification_level': qualification_level,
    }


def _mock_cursor(rows):
    """Create a mock cursor that returns the given rows from fetchall()."""
    cur = MagicMock()
    cur.fetchall.return_value = rows
    return cur


class TestOwlLookupExactMatch:
    """Single owl entity — original behavior."""

    def test_single_match(self):
        rows = [_make_row(100, 'Koch/Köchin', 1234, 'B 29302', 2)]
        result = owl_lookup('Koch', _mock_cursor(rows))
        assert result is not None
        assert result['confidence'] == 'owl'
        assert result['berufenet_id'] == 1234
        assert result['qualification_level'] == 2

    def test_multiple_names_same_entity(self):
        """Two owl_names rows pointing to same owl_id."""
        rows = [
            _make_row(100, 'Koch/Köchin', 1234, 'B 29302', 2),
            _make_row(100, 'Koch/Köchin', 1234, 'B 29302', 2),
        ]
        result = owl_lookup('Koch', _mock_cursor(rows))
        assert result is not None
        assert result['confidence'] == 'owl'

    def test_no_match(self):
        result = owl_lookup('Quantum Unicorn Wrangler', _mock_cursor([]))
        assert result is None


class TestOwlLookupTier1Unanimous:
    """Multiple owl entities, same QL + same domain."""

    def test_same_ql_same_domain(self):
        """Techniker: 3 specializations, all QL=3, same domain prefix."""
        rows = [
            _make_row(201, 'Drucktechniker/in', 5001, 'B 23413', 3),
            _make_row(202, 'Elektrotechniker/in', 5002, 'B 23423', 3),
            _make_row(203, 'Maschinenbautechniker/in', 5003, 'B 23433', 3),
        ]
        result = owl_lookup('Techniker', _mock_cursor(rows))
        assert result is not None
        assert result['confidence'] == 'owl_unanimous'
        assert result['qualification_level'] == 3

    def test_helfer_all_ql1(self):
        """Helfer: all QL=1."""
        rows = [
            _make_row(301, 'Helfer/in - Küche', 6001, 'B 29201', 1),
            _make_row(302, 'Helfer/in - Lager', 6002, 'B 29202', 1),
        ]
        result = owl_lookup('Helfer', _mock_cursor(rows))
        assert result is not None
        assert result['confidence'] == 'owl_unanimous'
        assert result['qualification_level'] == 1


class TestOwlLookupTier2Majority:
    """Multiple owl entities, same domain, mixed QL — majority vote."""

    def test_mixed_ql_same_domain(self):
        """Fachkraft: QL=2 appears 3x, QL=3 appears 1x → picks QL=2."""
        rows = [
            _make_row(401, 'Fachkraft A', 7001, 'B 51212', 2),
            _make_row(402, 'Fachkraft B', 7002, 'B 51222', 2),
            _make_row(403, 'Fachkraft C', 7003, 'B 51232', 2),
            _make_row(404, 'Fachkraft D', 7004, 'B 51243', 3),
        ]
        result = owl_lookup('Fachkraft', _mock_cursor(rows))
        assert result is not None
        assert result['confidence'] == 'owl_majority'
        assert result['qualification_level'] == 2

    def test_tischler_variants(self):
        """Tischler: QL=2 vs QL=3 (1 each) → picks first QL in most_common."""
        rows = [
            _make_row(501, 'Tischler/in', 8001, 'B 22342', 2),
            _make_row(502, 'Tischler/in - Restaurierung', 8002, 'B 22343', 3),
        ]
        result = owl_lookup('Tischler', _mock_cursor(rows))
        assert result is not None
        assert result['confidence'] == 'owl_majority'
        # When tied, Counter.most_common picks one — just verify it's valid
        assert result['qualification_level'] in (2, 3)


class TestOwlLookupTier3Reject:
    """Different KLDB domains — reject (fall to Phase 2)."""

    def test_different_domains(self):
        """Hypothetical: same name, different top-level KLDB domains."""
        rows = [
            _make_row(601, 'Ambiguous A', 9001, 'B 23413', 3),
            _make_row(602, 'Ambiguous B', 9002, 'B 81624', 4),
        ]
        result = owl_lookup('Ambiguous', _mock_cursor(rows))
        assert result is None

    def test_same_domain_prefix_accepted(self):
        """Same 2-digit domain prefix → NOT rejected (Tier 1 or 2)."""
        rows = [
            _make_row(701, 'Sub A', 10001, 'B 23413', 3),
            _make_row(702, 'Sub B', 10002, 'B 23423', 3),
        ]
        result = owl_lookup('SubSpecialization', _mock_cursor(rows))
        assert result is not None


class TestOwlLookupEdgeCases:
    """Edge cases and defensive behavior."""

    def test_null_kldb(self):
        """Row with None kldb should not crash."""
        rows = [
            _make_row(801, 'Weird Job', 11001, None, 2),
        ]
        result = owl_lookup('Weird Job', _mock_cursor(rows))
        # Single entity — should still match
        assert result is not None
        assert result['confidence'] == 'owl'

    def test_null_qualification_level(self):
        """Row with None QL should not crash in ambiguous path."""
        rows = [
            _make_row(901, 'Job A', 12001, 'B 23413', None),
            _make_row(902, 'Job B', 12002, 'B 23423', 3),
        ]
        result = owl_lookup('NullQL', _mock_cursor(rows))
        # Same domain → should still work (unanimous or majority)
        assert result is not None

    def test_duplicate_owl_ids_deduped(self):
        """Multiple owl_names rows for same owl_id — should dedup before ambiguity check."""
        rows = [
            _make_row(1001, 'Koch/Köchin', 1234, 'B 29302', 2),
            _make_row(1001, 'Koch/Köchin', 1234, 'B 29302', 2),
            _make_row(1002, 'Koch/Köchin - Hotel', 1235, 'B 29303', 2),
        ]
        result = owl_lookup('Koch', _mock_cursor(rows))
        assert result is not None
        # 2 unique entities, same domain, same QL → owl_unanimous
        assert result['confidence'] == 'owl_unanimous'
