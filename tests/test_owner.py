from fractions import Fraction as F

import pytest

from data.owner import MissingOwnerNumber, havens, ladder, lambda_usd, load, need, prices


def test_brief_ladder_and_havens():
    o = load()
    assert ladder(o)[0] == 100 and ladder(o)[-1] == 1_000_000 and len(ladder(o)) == 15
    assert [ladder(o)[h] for h in havens(o)] == [F(1000), F(32000)]
    assert need(o, "rulings.read_first") is True


def test_missing_numbers_fail_loud_and_name_the_key():
    o = load()
    for f in (lambda_usd, prices):
        with pytest.raises(MissingOwnerNumber, match="lambda_usd|instruments"):
            f(o)


def test_prices_from_declared_costs():
    o = {"lambda_usd": "2", "rulings": {"fifty_usd": "0"},
         "instruments": {k: {"model": "m", "usd_per_call": "0.01"} for k in ("llm", "phone", "audience")}}
    assert prices(o) == {"llm": F(1, 50), "phone": F(1, 50), "audience": F(1, 50), "fifty": F(0)}
