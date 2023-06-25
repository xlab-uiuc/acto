import pytest as pytest

from acto.k8s_util.k8sutil import canonicalize_quantity, double_quantity, call_k8s_util, half_quantity

testcases = [
    ("172.18.0.4", "172.18.0.4"),
    ("1Mi", "1048576.000"),
    ("asd", "asd"),
    ("+.9", "0.900"),
    ("900m", "0.900"),
    ("0", "0.000"),
    ("-.298Mi", "-312475.648"),
    ("-312475648m", "-312475.648"),
    ("-.01Ki", "-10.240"),
    (".01Ki", "10.240"),
    ("0", "0.000"),
    ("+4678410156.347680E+.6994785", "INVALID"),
    ("+838612.516637636", "838612.517"),
    ("838612517m", "838612.517"),
    ("+838612.516637636", "838612.517"),
    ("838612517m", "838612.517"),
    ("+099", "99.000"),
    ("99", "99.000"),
    (".2316344e999842", "inf"),
    (".6064887", "0.607"),
]


@pytest.mark.parametrize(
    ("value", "canonicalized_value"),
    testcases + [pytest.param("-.484785E-7466", "0.000", marks=pytest.mark.xfail(reason="Not sure about the right answer here"))]
)
def test_canonicalize_quantity(value, canonicalized_value):
    assert canonicalize_quantity(value) == canonicalized_value


@pytest.mark.parametrize(
    ("value", "canonicalized_value"),
    testcases
)
def test_double_quantity(value, canonicalized_value):
    doubled, ok = call_k8s_util('doubleIt')(value)
    if doubled == 'INVALID':
        assert not ok
        assert double_quantity(value) == 'INVALID'
        return

    if ok:
        assert double_quantity(value) == doubled
        equal = float(canonicalize_quantity(double_quantity(value))) == float(canonicalize_quantity(value)) * 2
        almost_equal = abs(float(canonicalize_quantity(double_quantity(value))) - float(canonicalize_quantity(value)) * 2) <= 0.001
        assert equal or almost_equal
        return

    assert double_quantity(value) == value


@pytest.mark.parametrize(
    ("value", "canonicalized_value"),
    testcases
)
def test_half_quantity(value, canonicalized_value):
    halved, ok = call_k8s_util('halfIt')(value)
    if halved == 'INVALID':
        assert not ok
        assert half_quantity(value) == 'INVALID'
        return

    if ok:
        assert half_quantity(value) == halved
        equal = float(canonicalize_quantity(half_quantity(value))) == float(canonicalize_quantity(value)) / 2
        almost_equal = abs(float(canonicalize_quantity(half_quantity(value))) - float(canonicalize_quantity(value)) / 2) <= 0.001
        assert equal or almost_equal
        return

    assert half_quantity(value) == value
