import pytest

from rosetta.utils import role_expr

instance = role_expr.MetaRoleEvaluator(
    {"711534517432614922": True, "711534523879522304": False}
)


def test_and():
    assert instance.evaluate("711534517432614922&&711534523879522304") is False


def test_or():
    assert instance.evaluate("711534517432614922||711534523879522304") is True


def test_not():
    assert instance.evaluate("!711534517432614922") is False


def test_no_operator():
    with pytest.raises(Exception):
        instance.evaluate("711534517432614922 + 711534523879522304")


def test_afternot():
    with pytest.raises(Exception):
        instance.evaluate("711534517432614922!")


def test_symbol_not_symbol():
    with pytest.raises(Exception):
        instance.evaluate("711534517432614922!711534523879522304")


def test_operator_first():
    with pytest.raises(Exception):
        instance.evaluate("&&711534517432614922")


def test_paran():
    assert instance.evaluate("(711534517432614922)") is True


def test_not_paran():
    assert instance.evaluate("!(711534517432614922)") is False


def test_not_paran_operator():
    assert instance.evaluate("!(711534517432614922) && !(711534523879522304)") is False


def test_complex_paran():
    assert (
        instance.evaluate(
            (
                "(711534517432614922 && 711534523879522304)"
                " || (711534517432614922 || 711534523879522304)"
            )
        )
        is True
    )


def test_folded_paran():
    assert (
        instance.evaluate(
            "(711534517432614922 && (711534517432614922 || 711534523879522304)) "
            "|| (711534517432614922 || 711534523879522304)"
        )
        is True
    )


def test_folded_paran_not():
    assert (
        instance.evaluate(
            (
                "(711534517432614922 && !(711534517432614922 || 711534523879522304)) "
                "|| !(711534517432614922 || 711534523879522304)"
            )
        )
        is False
    )


def test_paran_end_not():
    with pytest.raises(Exception):
        instance.evaluate(
            (
                "(711534517432614922 && !(711534517432614922 || 711534523879522304)!) "
                "|| !(711534517432614922 || 711534523879522304)"
            )
        )


def test_paran_end_not_2():
    with pytest.raises(Exception):
        instance.evaluate(
            "(711534517432614922 && !(711534517432614922 || 711534523879522304)!)"
        )


def test_paren_no_r_operand():
    with pytest.raises(Exception):
        instance.evaluate("(711534517432614922 &&)")


def test_no_r_operand():
    with pytest.raises(Exception):
        instance.evaluate("711534517432614922 &&")


def test_no_r_paranthesis():
    with pytest.raises(Exception):
        instance.evaluate("(711534517432614922")


def test_no_l_paranthesis():
    with pytest.raises(Exception):
        instance.evaluate("711534517432614922)")


def test_no_l_paranthesis_2():
    with pytest.raises(Exception):
        instance.evaluate("711534517432614922 && 711534523879522304)")


def test_empty_str():
    with pytest.raises(Exception):
        instance.evaluate("")


def test_empty_paran():
    with pytest.raises(Exception):
        instance.evaluate("()")


def test_empty_paran_operand():
    with pytest.raises(Exception):
        instance.evaluate("711534517432614922 && ()")
