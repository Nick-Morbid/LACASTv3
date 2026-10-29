"""Construct valid regex arguments; ANTLR continues to recognize SQL syntax only."""


def regex_pattern(random):
    """Compose ICU-compatible patterns rather than treating arbitrary text as regex.

    The vocabulary varies literals, classes, grouping, alternatives, anchors and
    bounded/unbounded repetition. This is a generation domain, not an ICU parser
    or a claim to cover every regex construct supported by MySQL.
    """
    atoms = ('a', 'b', 'abc', '[a-z]', '[0-9]', '[[:alpha:]]', '.', r'\.', '中')

    def sequence():
        return ''.join(random.choice(atoms) + random.choice(('', '?', '*', '+', '{1,3}'))
                       for _ in range(random.randint(1, 3)))

    pattern = sequence()
    if random.random() < .5:
        pattern = '(' + pattern + '|' + sequence() + ')'
    return random.choice(('', '^')) + pattern + random.choice(('', '$'))


def mysql_string(value):
    """Quote for the recorded MySQL mode (backslash escapes enabled)."""
    return "'" + value.replace('\\', '\\\\').replace("'", "''") + "'"
