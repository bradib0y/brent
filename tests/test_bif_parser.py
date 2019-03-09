import pandas as pd
import pytest

from brent import parsers
from brent.parsers.bif import join_independent, join_dependent, parse_network_type, parse_variables, \
    parse_unconditional_probabilities, parse_conditional_probabilities


@pytest.fixture
def test_bif():
    return """network unknown {
}
variable A {
  type discrete [ 2 ] { yes, no };
}
variable B {
  type discrete [ 2 ] { yes, no };
}
variable C {
  type discrete [ 2 ] { yes, no };
}
variable D {
  type discrete [ 2 ] { yes, no };
}
probability ( A ) {
  table 0.01, 0.99;
}
probability ( C | B ) {
  (yes) 0.05, 0.95;
  (no) 0.01, 0.99;
}
probability ( B ) {
  table 0.5, 0.5;
}
probability ( D | B, A ) {
  (yes, yes) 1.0, 0.0;
  (no, yes) 1.0, 0.0;
  (yes, no) 1.0, 0.0;
  (no, no) 0.0, 1.0;
}
"""


@pytest.fixture
def prob_a():
    return pd.DataFrame({'A': ['true', 'false'], 'prob': [0.5, 0.5]})


@pytest.fixture
def prob_b():
    return pd.DataFrame({'B': ['true', 'false'], 'prob': [0.5, 0.5]})


@pytest.fixture
def cond_prob_b():
    return pd.DataFrame({
        'A': ['true', 'false', 'true', 'false'],
        'B': ['true', 'true', 'false', 'false'],
        'prob': [0.3, 0.7, 0.8, 0.2]}).set_index('A')


def test_join_independent(prob_a, prob_b):
    target = pd.DataFrame({
        'A': ['true', 'true', 'false', 'false'],
        'B': ['true', 'false', 'true', 'false'],
        'prob': [0.25, 0.25, 0.25, 0.25]
    })
    pd.testing.assert_frame_equal(join_independent(prob_a, prob_b), target)


def test_join_independent_input_checks(prob_a, prob_b):
    with pytest.raises(ValueError):
        join_independent(prob_a.drop(columns=['prob']), prob_b)

    with pytest.raises(ValueError):
        join_independent(prob_a, prob_b.drop(columns=['prob']))


def test_join_dependent(prob_a, cond_prob_b):
    target = pd.DataFrame({
        'A': ['true', 'true', 'false', 'false'],
        'B': ['true', 'false', 'true', 'false'],
        'prob': [0.15, 0.4, 0.35, 0.1]
    })
    pd.testing.assert_frame_equal(join_dependent(prob_a, cond_prob_b), target)


def test_join_dependent_input_checks(prob_a, cond_prob_b):
    with pytest.raises(ValueError):
        join_dependent(prob_a.drop(columns=['prob']), cond_prob_b)

    with pytest.raises(ValueError):
        join_dependent(prob_a, cond_prob_b.drop(columns=['prob']))

    with pytest.raises(ValueError):
        join_dependent(prob_a.drop(columns=['A']), cond_prob_b)

    with pytest.raises(ValueError):
        join_dependent(prob_a, cond_prob_b.reset_index())


def test_parse(test_bif):
    probability_df, links = parsers.bif(test_bif)

    target = pd.DataFrame({
        'A': ['yes', 'yes', 'yes', 'yes', 'no', 'no', 'no', 'no', 'yes', 'yes', 'yes', 'yes', 'no', 'no', 'no', 'no'],
        'B': ['yes', 'yes', 'yes', 'yes', 'yes', 'yes', 'yes', 'yes', 'no', 'no', 'no', 'no', 'no', 'no', 'no', 'no'],
        'C': ['yes', 'yes', 'no', 'no', 'yes', 'yes', 'no', 'no', 'yes', 'yes', 'no', 'no', 'yes', 'yes', 'no', 'no'],
        'D': ['yes', 'no', 'yes', 'no', 'yes', 'no', 'yes', 'no', 'yes', 'no', 'yes', 'no', 'yes', 'no', 'yes', 'no'],
        'prob': [0.00025, 0.0, 0.00475, 0.0, 0.02475, 0.0, 0.47025, 0.0, 5e-05, 0.0, 0.00495, 0.0, 0.0, 0.00495, 0.0,
                 0.49005]
    })

    pd.testing.assert_frame_equal(probability_df, target)
    target_links = [
        ('A', 'D'),
        ('B', 'D'),
        ('B', 'C'),
    ]
    assert sorted(links) == sorted(target_links)


def test_parse_network_type(test_bif):
    assert parse_network_type(test_bif) == 'unknown'


def test_parse_variables(test_bif):
    target = [
        ('A', ['yes', 'no']),
        ('B', ['yes', 'no']),
        ('C', ['yes', 'no']),
        ('D', ['yes', 'no']),
    ]
    assert list(parse_variables(test_bif)) == target


def test_parse_unconditional_variables(test_bif):
    target = [
        ('A', [0.01, 0.99]),
        ('B', [0.5, 0.5]),
    ]
    assert list(parse_unconditional_probabilities(test_bif)) == target


def test_parse_conditional_variables(test_bif):
    target = [
        ('C', ['B'], [
            ['yes', 0.05, 0.95],
            ['no', 0.01, 0.99]
        ]),
        ('D', ['B', 'A'], [
            ['yes', 'yes', 1.0, 0.0],
            ['no', 'yes', 1.0, 0.0],
            ['yes', 'no', 1.0, 0.0],
            ['no', 'no', 0.0, 1.0]
        ]),
    ]
    assert list(parse_conditional_probabilities(test_bif)) == target
