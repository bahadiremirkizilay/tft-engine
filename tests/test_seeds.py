import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from tft_engine.repro import derive_seed, make_rng


def test_known_value_is_stable_across_machines():
    # Pinned value: if this changes, every recorded experiment stops replaying.
    assert derive_seed(0) == 4066689987807800415
    assert derive_seed(42, "shop", 3) == 12992379321320753221


@given(st.integers(0, 2**63), st.text(max_size=20))
def test_same_inputs_same_seed(base, name):
    assert derive_seed(base, name) == derive_seed(base, name)


@given(st.integers(0, 2**32))
def test_different_names_give_different_seeds(base):
    assert derive_seed(base, "shop") != derive_seed(base, "combat")


def test_name_boundaries_matter():
    # ("ab", "c") must not collide with ("a", "bc").
    assert derive_seed(1, "ab", "c") != derive_seed(1, "a", "bc")


def test_seed_fits_64_bits():
    assert 0 <= derive_seed(123, "x") < 2**64


def test_make_rng_reproducible():
    a = make_rng(7, "stream").integers(0, 1000, size=50)
    b = make_rng(7, "stream").integers(0, 1000, size=50)
    assert np.array_equal(a, b)


def test_adding_a_stream_does_not_shift_another():
    before = make_rng(7, "shop").random(10)
    _ = make_rng(7, "new_stream").random(1000)
    after = make_rng(7, "shop").random(10)
    assert np.array_equal(before, after)


def test_negative_seed_rejected():
    import pytest

    with pytest.raises(ValueError):
        derive_seed(-1)
