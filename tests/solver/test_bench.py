"""O cartão explícito do benchmark (o `solver` não importa `rules`) bate com o cartão carregado de `data/regras/`."""

from datetime import date
from pathlib import Path

from escalista.rules.loader import load_rule_card
from escalista.solver.bench import PRIMITIVE_KINDS, bench_rule_card

REFERENCE = date(2027, 1, 11)


def test_bench_card_matches_loaded_card_on_five_primitives():
    loaded = {r.kind: (r.id, r.layer, r.params) for r in load_rule_card(Path("data/regras"), REFERENCE).rules}
    built = bench_rule_card(REFERENCE)

    assert built.reference_date == REFERENCE
    assert sorted(r.kind for r in built.rules) == sorted(PRIMITIVE_KINDS)
    assert len(PRIMITIVE_KINDS) == 5
    for r in built.rules:
        assert (r.id, r.layer, r.params) == loaded[r.kind], r.kind


def test_bench_spec_option_none_or_default():
    from escalista.domain.spec import SolveSpec
    from escalista.rules.spec import default_spec
    from escalista.solver.bench import bench_spec

    assert bench_spec("none") is None
    assert bench_spec("default") == default_spec() == SolveSpec()
