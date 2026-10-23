"""SQLite固有の検証式をPostgreSQLでも同じ意味で評価する。"""

from sqlalchemy import Boolean
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement


class IntegerMinimum(FunctionElement):
    type = Boolean()
    inherit_cache = True


@compiles(IntegerMinimum)
def integer_minimum(expression, compiler, **kwargs):
    value, minimum = [compiler.process(arg, **kwargs) for arg in expression.clauses]
    return f"({value} >= {minimum})"


@compiles(IntegerMinimum, "sqlite")
def sqlite_integer_minimum(expression, compiler, **kwargs):
    value, minimum = [compiler.process(arg, **kwargs) for arg in expression.clauses]
    return f"(typeof({value}) = 'integer' AND {value} >= {minimum})"


class ValidJson(FunctionElement):
    type = Boolean()
    inherit_cache = True


@compiles(ValidJson, "sqlite")
def sqlite_valid_json(expression, compiler, **kwargs):
    return f"json_valid({compiler.process(expression.clauses, **kwargs)})"


@compiles(ValidJson, "postgresql")
def postgres_valid_json(expression, compiler, **kwargs):
    return (
        f"(CAST({compiler.process(expression.clauses, **kwargs)} AS JSON) IS NOT NULL)"
    )
