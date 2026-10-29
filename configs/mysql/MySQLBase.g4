grammar MySQLBase;

options { caseInsensitive = true; }

query: withClause? selectStatement SEMI? EOF;
withClause: 'WITH' cte (COMMA cte)*;
cte: identifier (LP identifier (COMMA identifier)* RP)? 'AS' LP selectStatement RP;
selectStatement: selectCore (setOperator selectCore)* orderBy? limitClause?;
setOperator: ('UNION' | 'INTERSECT' | 'EXCEPT') ('ALL' | 'DISTINCT')?;
selectCore: 'SELECT' 'DISTINCT'? selectItem (COMMA selectItem)* fromClause?
            ('WHERE' expression)? ('GROUP' 'BY' expression (COMMA expression)*)?
            ('HAVING' expression)?;
selectItem: STAR | expression ('AS' identifier)?;
fromClause: 'FROM' relation (COMMA relation | joinClause)*;
relation: identifier ('AS' identifier)? | LP selectStatement RP 'AS' identifier;
joinClause: ('INNER' | 'LEFT' 'OUTER'? | 'RIGHT' 'OUTER'? | 'CROSS' | 'NATURAL')?
            'JOIN' relation ('ON' expression | 'USING' LP identifier (COMMA identifier)* RP)?;
orderBy: 'ORDER' 'BY' expression ('ASC' | 'DESC')? (COMMA expression ('ASC' | 'DESC')?)*;
limitClause: 'LIMIT' INTEGER ('OFFSET' INTEGER | COMMA INTEGER)?;
expression
    : ('+' | '-' | '~' | 'NOT' | '!' | 'BINARY') expression
    | expression ('*' | '/' | '%' | 'DIV' | 'MOD') expression
    | expression ('+' | '-') expression
    | expression ('<<' | '>>' | '&' | '|' | '^') expression
    | expression ('=' | '<>' | '!=' | '<' | '<=' | '>' | '>=' | '<=>') expression
    | expression 'IS' 'NOT'? ('NULL' | 'TRUE' | 'FALSE')
    | expression 'NOT'? ('LIKE' | 'REGEXP' | 'RLIKE') expression ('ESCAPE' expression)?
    | expression 'NOT'? 'BETWEEN' expression 'AND' expression
    | expression 'NOT'? 'IN' LP (selectStatement | expression (COMMA expression)*) RP
    | expression ('AND' | '&&' | 'XOR' | 'OR' | '||') expression
    | primary
    ;
primary
    : literal
    | identifier (DOT identifier)?
    | identifier LP ('DISTINCT'? expression (COMMA expression)* | STAR)? RP
    | LP expression RP
    | LP selectStatement RP
    | 'EXISTS' LP selectStatement RP
    | 'CASE' expression? ('WHEN' expression 'THEN' expression)+ ('ELSE' expression)? 'END'
    | 'CAST' LP expression 'AS' castType RP
    | 'CONVERT' LP expression (COMMA castType | 'USING' identifier) RP
    | 'EXTRACT' LP identifier 'FROM' expression RP
    | 'INTERVAL' expression identifier
    ;
castType: identifier (LP INTEGER (COMMA INTEGER)? RP)? identifier?;
literal: INTEGER | DECIMAL | STRING | BIT_STRING | HEX_STRING | 'NULL' | 'TRUE' | 'FALSE';
identifier: IDENTIFIER | QUOTED_IDENTIFIER;

LP: '(';
RP: ')';
COMMA: ',';
DOT: '.';
SEMI: ';';
STAR: '*';
BIT_STRING: 'B' '\'' [01]* '\'' | '0B' [01]+;
HEX_STRING: 'X' '\'' [0-9a-f]* '\'' | '0X' [0-9a-f]+;
DECIMAL: ([0-9]+ '.' [0-9]* | '.' [0-9]+) ([e] [+-]? [0-9]+)? | [0-9]+ [e] [+-]? [0-9]+;
INTEGER: [0-9]+;
STRING: '\'' ('\'\'' | '\\' . | ~['\\])* '\'';
QUOTED_IDENTIFIER: '`' ('``' | ~'`')+ '`';
IDENTIFIER: [a-z_] [a-z_0-9$]*;
WS: [ \t\r\n]+ -> skip;
LINE_COMMENT: '--' [ \t] ~[\r\n]* -> skip;
BLOCK_COMMENT: '/*' .*? '*/' -> skip;
