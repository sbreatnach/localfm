"""
Unit tests for the track identifier generator.
"""

import unicodedata

from localfm.tracks.models import artist_name_variants, generate_identifier


def test_generate_identifier_normalises_unicode():
    """Composed and decomposed forms of the same text should match."""
    composed = "Sémba Braguez"
    decomposed = unicodedata.normalize("NFD", composed)

    assert composed != decomposed
    assert generate_identifier(composed, "Os Korimbas") == generate_identifier(
        decomposed, "Os Korimbas"
    )


def test_generate_identifier_is_case_insensitive():
    assert generate_identifier("MORNINGTON CRESCENT") == generate_identifier(
        "Mornington Crescent"
    )


def test_generate_identifier_strips_whitespace():
    assert generate_identifier("  Mornington Crescent\t") == generate_identifier(
        "Mornington Crescent"
    )


def test_generate_identifier_coerces_non_string_arguments():
    assert generate_identifier(123) == generate_identifier("123")


def test_generate_identifier_distinguishes_different_values():
    assert generate_identifier("Track A") != generate_identifier("Track B")


def test_generate_identifier_matches_expected_hash():
    """Lock the identifier format so accidental changes are caught."""
    assert (
        generate_identifier(
            "Mornington Crescent", "Belle & Sebastian", "The Life Pursuit"
        )
        == "10a49d0d7be3dfd7c55c0a646af61e54"
    )


def test_artist_name_variants_removes_leading_article():
    assert artist_name_variants("The Smashing Pumpkins") == [
        "The Smashing Pumpkins",
        "Smashing Pumpkins",
    ]


def test_artist_name_variants_adds_leading_article():
    assert artist_name_variants("Smashing Pumpkins") == [
        "Smashing Pumpkins",
        "The Smashing Pumpkins",
    ]


def test_artist_name_variants_preserves_the_the():
    """Stripping "The The" would produce the distinct name "The"."""
    assert artist_name_variants("The The") == ["The The"]


def test_artist_name_variants_does_not_prefix_the():
    """Expanding "The" would produce the distinct name "The The"."""
    assert artist_name_variants("The") == ["The"]


def test_artist_name_variants_strips_only_one_article():
    assert artist_name_variants("The The The") == ["The The The"]
    assert artist_name_variants("The Themselves") == [
        "The Themselves",
        "Themselves",
    ]
