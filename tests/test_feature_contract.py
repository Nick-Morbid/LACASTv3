import pytest

from lacastv3.feature_contract import validate_feature
from lacastv3.productions import Rule


@pytest.mark.parametrize('feature,production', [
    ('|', 'integerAtom'),
    ('ABS(x)', '("ABS(" integerAtom ")" | integerAtom)'),
    ('ABS(x)', '"ABS("? integerAtom ")"?'),
    ('IS NOT NULL', 'integerAtom "IS NULL"'),
    ('ABS(x)', '"CONCAT(\'ABS\'," integerAtom ")"'),
    ('CURRENT_TIME', '"CAST(\'12:00:00\' AS TIME)"'),
    ('CURRENT_TIMESTAMP', '("CURRENT_TIMESTAMP()" | "NULL")'),
    ('CASE value WHEN value THEN result END', '"IF(TRUE," integerAtom ", 0)"'),
])
def test_feature_cannot_disappear_from_an_alternative(feature, production):
    with pytest.raises(ValueError, match='removed'):
        validate_feature(feature, Rule('r', 'integer', production))


@pytest.mark.parametrize('feature,production', [
    ('|', 'integerAtom "|" integerAtom'),
    ('ABS(x)', '"ABS(" (integerAtom | doubleAtom) ")"'),
    ('IS NOT NULL', 'integerAtom "IS NOT NULL"'),
    ('N % M', 'integerAtom "% 3"'),
    ('CURRENT_TIMESTAMP', '"CURRENT_TIMESTAMP(3)"'),
    ('CASE value WHEN value THEN result END', '"CASE WHEN TRUE THEN" integerAtom "END"'),
])
def test_documented_operation_is_guaranteed(feature, production):
    validate_feature(feature, Rule('r', 'integer', production))
