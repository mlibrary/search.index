from api.marc import bidi


def test_bidi_surrounds_string_with_bidirectional_quotes():
    assert bidi("string") == "\u2068string\u2069"


def test_bidi_returns_empty_string_when_given_one():
    assert bidi("   ") == ""
