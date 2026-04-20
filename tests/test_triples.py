from mnemosyne import Triple


def test_iri_subject_predicate_literal_object():
    t = Triple(
        "urn:concept:1",
        "http://www.w3.org/2004/02/skos/core#prefLabel",
        "phi-crystal",
    )
    assert t.canonical() == (
        b"<urn:concept:1> <http://www.w3.org/2004/02/skos/core#prefLabel> "
        b'"phi-crystal" .\n'
    )


def test_literal_escaping():
    t = Triple("urn:x", "urn:says", 'hello "world"\n')
    assert t.canonical() == b'<urn:x> <urn:says> "hello \\"world\\"\\n" .\n'


def test_triple_is_hashable_and_ordered():
    a = Triple("urn:a", "urn:p", "1")
    b = Triple("urn:a", "urn:p", "2")
    assert {a, b} == {a, b}
    assert sorted([b, a]) == [a, b]
