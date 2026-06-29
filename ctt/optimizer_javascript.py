from typing import Any, List, Optional, Tuple

import escodegen
import esprima
from esprima import nodes

from ctt.optimizer import OptimizationRecord


def _line_of(node: nodes.Node) -> int:
    loc = getattr(node, "loc", None)
    if loc and getattr(loc, "start", None):
        return int(getattr(loc.start, "line", 0) or 0)
    return 0


def _is_number_literal(node: nodes.Node) -> bool:
    return isinstance(node, nodes.Literal) and isinstance(getattr(node, "value", None), (int, float))


def _make_literal(value: Any) -> nodes.Literal:
    if value is True:
        return nodes.Literal(True, "true")
    if value is False:
        return nodes.Literal(False, "false")
    if value is None:
        return nodes.Literal(None, "null")
    return nodes.Literal(value, repr(value))


def _make_identifier(name: str) -> nodes.Identifier:
    return nodes.Identifier(name)


def _record(records: List[OptimizationRecord], node: nodes.Node, description: str, before_node: nodes.Node, after_node: nodes.Node) -> None:
    records.append(
        OptimizationRecord(
            line=_line_of(node),
            description=description,
            before=escodegen.generate(before_node),
            after=escodegen.generate(after_node),
        )
    )


def _node_code(node: nodes.Node) -> str:
    return escodegen.generate(node)


def _ast_equal(a: nodes.Node, b: nodes.Node) -> bool:
    return _node_code(a) == _node_code(b)


def _is_string_literal(node: nodes.Node) -> bool:
    return isinstance(node, nodes.Literal) and isinstance(getattr(node, "value", None), str)


def _is_safe_expression(expr: nodes.Node) -> bool:
    if isinstance(expr, (nodes.Literal, nodes.Identifier, nodes.ThisExpression)):
        return True
    if isinstance(expr, nodes.BinaryExpression):
        return _is_safe_expression(expr.left) and _is_safe_expression(expr.right)
    if isinstance(expr, nodes.UnaryExpression):
        return _is_safe_expression(expr.argument)
    if isinstance(expr, nodes.ConditionalExpression):
        return (
            _is_safe_expression(expr.test)
            and _is_safe_expression(expr.consequent)
            and _is_safe_expression(expr.alternate)
        )
    if isinstance(expr, nodes.ArrayExpression):
        return all(_is_safe_expression(element) for element in expr.elements)
    if isinstance(expr, nodes.ObjectExpression):
        return all(
            _is_safe_expression(prop.value)
            for prop in expr.properties
            if getattr(prop, "value", None) is not None
        )
    return False


def _contains_name(node: nodes.Node, name: str) -> bool:
    if isinstance(node, nodes.Identifier) and node.name == name:
        return True
    for value in node.__dict__.values():
        if isinstance(value, nodes.Node) and _contains_name(value, name):
            return True
        if isinstance(value, list) and any(isinstance(item, nodes.Node) and _contains_name(item, name) for item in value):
            return True
    return False


def _statement_assignment_info(stmt: nodes.Node) -> tuple[str, nodes.Node, str, str] | None:
    if isinstance(stmt, nodes.VariableDeclaration) and len(stmt.declarations) == 1:
        decl = stmt.declarations[0]
        if isinstance(decl.id, nodes.Identifier) and decl.init is not None:
            return decl.id.name, decl.init, "declaration", stmt.kind

    if isinstance(stmt, nodes.ExpressionStatement) and isinstance(stmt.expression, nodes.AssignmentExpression):
        expr = stmt.expression
        if expr.operator == "=" and isinstance(expr.left, nodes.Identifier):
            return expr.left.name, expr.right, "assignment", ""

    return None


def _body_contains_control_flow(body: List[nodes.Node]) -> bool:
    terminal_types = (
        nodes.BreakStatement,
        nodes.ContinueStatement,
        nodes.ReturnStatement,
        nodes.ThrowStatement,
        nodes.YieldExpression,
        nodes.AwaitExpression,
    )

    def walk(node: nodes.Node) -> bool:
        if isinstance(node, terminal_types):
            return True
        for value in node.__dict__.values():
            if isinstance(value, nodes.Node) and walk(value):
                return True
            if isinstance(value, list) and any(isinstance(item, nodes.Node) and walk(item) for item in value):
                return True
        return False

    return any(walk(stmt) for stmt in body)


def _get_statement_body_list(stmt: nodes.Node) -> List[nodes.Node] | None:
    if isinstance(stmt, nodes.BlockStatement):
        return stmt.body
    return None


def _maybe_wrap_block(stmt: nodes.Node) -> nodes.BlockStatement:
    if isinstance(stmt, nodes.BlockStatement):
        return stmt
    return nodes.BlockStatement([stmt])


def _safe_numeric_eval(operator: str, left: float, right: float) -> Optional[float]:
    try:
        if operator == "+":
            return left + right
        if operator == "-":
            return left - right
        if operator == "*":
            return left * right
        if operator == "/":
            if right == 0:
                return None
            return left / right
        if operator == "%":
            if right == 0:
                return None
            return left % right
        if operator == "**":
            if abs(right) > 1000:
                return None
            return left**right
    except Exception:
        return None
    return None


def _transform_expression(node: nodes.Node, mode: str, records: List[OptimizationRecord]) -> nodes.Node:
    if isinstance(node, nodes.BinaryExpression):
        node.left = _transform_expression(node.left, mode, records)
        node.right = _transform_expression(node.right, mode, records)

        if mode in ("both", "energy"):
            if _is_number_literal(node.left) and _is_number_literal(node.right):
                result = _safe_numeric_eval(node.operator, float(node.left.value), float(node.right.value))
                if result is not None:
                    if isinstance(node.left.value, int) and isinstance(node.right.value, int) and result.is_integer():
                        literal_value: Any = int(result)
                    else:
                        literal_value = result
                    replacement = _make_literal(literal_value)
                    _record(records, node, "Constant folding", node, replacement)
                    return replacement

            if node.operator == "**" and _is_number_literal(node.right):
                exponent = node.right.value
                if isinstance(exponent, int) and 2 <= exponent <= 4:
                    replacement: nodes.Node = node.left
                    for _ in range(exponent - 1):
                        replacement = nodes.BinaryExpression("*", replacement, node.left)
                    _record(records, node, "Strength reduction: power -> multiplication", node, replacement)
                    return replacement

        if mode in ("both", "general"):
            if node.operator == "*":
                if _is_number_literal(node.right) and node.right.value == 1:
                    _record(records, node, "Identity operation removal: x * 1 -> x", node, node.left)
                    return node.left
                if _is_number_literal(node.left) and node.left.value == 1:
                    _record(records, node, "Identity operation removal: 1 * x -> x", node, node.right)
                    return node.right
            elif node.operator == "+":
                if _is_number_literal(node.right) and node.right.value == 0:
                    _record(records, node, "Identity operation removal: x + 0 -> x", node, node.left)
                    return node.left
                if _is_number_literal(node.left) and node.left.value == 0:
                    _record(records, node, "Identity operation removal: 0 + x -> x", node, node.right)
                    return node.right
            elif node.operator == "-":
                if _is_number_literal(node.right) and node.right.value == 0:
                    _record(records, node, "Identity operation removal: x - 0 -> x", node, node.left)
                    return node.left
            elif node.operator == "/":
                if _is_number_literal(node.right) and node.right.value == 1:
                    _record(records, node, "Identity operation removal: x / 1 -> x", node, node.left)
                    return node.left

    if isinstance(node, nodes.UnaryExpression):
        node.argument = _transform_expression(node.argument, mode, records)

    if isinstance(node, nodes.CallExpression):
        node.callee = _transform_expression(node.callee, mode, records)
        node.arguments = [_transform_expression(arg, mode, records) for arg in node.arguments]

    if isinstance(node, (nodes.StaticMemberExpression, nodes.ComputedMemberExpression)):
        node.object = _transform_expression(node.object, mode, records)
        node.property = _transform_expression(node.property, mode, records)

    if isinstance(node, nodes.AssignmentExpression):
        node.left = _transform_expression(node.left, mode, records)
        node.right = _transform_expression(node.right, mode, records)

    if isinstance(node, nodes.UpdateExpression):
        node.argument = _transform_expression(node.argument, mode, records)

    if isinstance(node, nodes.ConditionalExpression):
        node.test = _transform_expression(node.test, mode, records)
        node.consequent = _transform_expression(node.consequent, mode, records)
        node.alternate = _transform_expression(node.alternate, mode, records)

    return node


def _eliminate_dead_code(body: List[nodes.Node], records: List[OptimizationRecord]) -> List[nodes.Node]:
    terminal_types = (
        nodes.ReturnStatement,
        nodes.BreakStatement,
        nodes.ContinueStatement,
        nodes.ThrowStatement,
    )

    new_body: List[nodes.Node] = []
    for stmt in body:
        new_body.append(stmt)
        if isinstance(stmt, terminal_types):
            remaining = len(body) - len(new_body)
            if remaining > 0:
                records.append(
                    OptimizationRecord(
                        line=_line_of(stmt),
                        description=f"Dead code elimination: removed {remaining} unreachable statement(s)",
                        before="(unreachable code after return/break/continue/throw)",
                        after="(removed)",
                    )
                )
            break
    return new_body


def _inline_variable_returns(body: List[nodes.Node], records: List[OptimizationRecord]) -> List[nodes.Node]:
    if len(body) < 2:
        return body

    new_body: List[nodes.Node] = []
    i = 0
    while i < len(body):
        current = body[i]
        nxt = body[i + 1] if i + 1 < len(body) else None

        if isinstance(current, nodes.VariableDeclaration) and isinstance(nxt, nodes.ReturnStatement):
            if len(current.declarations) == 1:
                decl = current.declarations[0]
                if (
                    isinstance(decl.id, nodes.Identifier)
                    and decl.init is not None
                    and isinstance(nxt.argument, nodes.Identifier)
                    and nxt.argument.name == decl.id.name
                    and _is_safe_expression(decl.init)
                ):
                    before_code = f"{_node_code(current)}\n{_node_code(nxt)}"
                    replacement = nodes.ReturnStatement(decl.init)
                    _record(
                        records,
                        current,
                        "Variable inlining: assignment inlined into return",
                        nodes.BlockStatement([current, nxt]),
                        replacement,
                    )
                    new_body.append(replacement)
                    i += 2
                    continue

        new_body.append(current)
        i += 1

    return new_body


def _reuse_common_subexpressions(body: List[nodes.Node], records: List[OptimizationRecord]) -> List[nodes.Node]:
    if len(body) < 2:
        return body

    new_body = list(body)
    for i in range(len(new_body) - 1):
        first_info = _statement_assignment_info(new_body[i])
        second_info = _statement_assignment_info(new_body[i + 1])
        if not first_info or not second_info:
            continue

        first_name, first_expr, _, _ = first_info
        second_name, second_expr, second_kind, _ = second_info

        if first_name == second_name:
            continue
        if not _is_safe_expression(first_expr) or not _is_safe_expression(second_expr):
            continue
        if not _ast_equal(first_expr, second_expr):
            continue
        if _contains_name(second_expr, first_name):
            continue

        before_code = _node_code(new_body[i + 1])
        if second_kind == "declaration":
            decl = new_body[i + 1].declarations[0]
            decl.init = _make_identifier(first_name)
        else:
            assignment = new_body[i + 1].expression
            assignment.right = _make_identifier(first_name)
        records.append(
            OptimizationRecord(
                line=_line_of(new_body[i + 1]),
                description="Common subexpression reuse: reused previous computed value",
                before=before_code,
                after=_node_code(new_body[i + 1]),
                )
        )

    return new_body


def _loop_header_code(stmt: nodes.Node) -> str:
    if isinstance(stmt, nodes.ForStatement):
        parts = [stmt.init, stmt.test, stmt.update]
        return "|".join(_node_code(part) if isinstance(part, nodes.Node) else "" for part in parts)
    if isinstance(stmt, (nodes.ForOfStatement, nodes.ForInStatement)):
        return f"{_node_code(stmt.left)}|{_node_code(stmt.right)}"
    return ""


def _fuse_adjacent_loops(body: List[nodes.Node], records: List[OptimizationRecord]) -> List[nodes.Node]:
    if len(body) < 2:
        return body

    new_body: List[nodes.Node] = []
    i = 0
    while i < len(body):
        current = body[i]
        nxt = body[i + 1] if i + 1 < len(body) else None
        if (
            isinstance(current, (nodes.ForStatement, nodes.ForOfStatement, nodes.ForInStatement))
            and isinstance(nxt, type(current))
            and _loop_header_code(current) == _loop_header_code(nxt)
        ):
            current_block = _get_statement_body_list(current.body)
            next_block = _get_statement_body_list(nxt.body)
            if current_block is not None and next_block is not None and not _body_contains_control_flow(current_block) and not _body_contains_control_flow(next_block):
                if isinstance(current, nodes.ForStatement):
                    fused = nodes.ForStatement(current.init, current.test, current.update, nodes.BlockStatement(current_block + next_block))
                elif isinstance(current, nodes.ForOfStatement):
                    fused = nodes.ForOfStatement(current.left, current.right, nodes.BlockStatement(current_block + next_block))
                else:
                    fused = nodes.ForInStatement(current.left, current.right, nodes.BlockStatement(current_block + next_block))
                before_code = f"{_node_code(current)}\n{_node_code(nxt)}"
                after_code = _node_code(fused)
                records.append(
                    OptimizationRecord(
                        line=_line_of(current),
                        description="Loop fusion: merged adjacent loops over same iterator",
                        before=before_code,
                        after=after_code,
                    )
                )
                new_body.append(fused)
                i += 2
                continue
        new_body.append(current)
        i += 1

    return new_body


def _string_concat_to_join(body: List[nodes.Node], records: List[OptimizationRecord]) -> List[nodes.Node]:
    if len(body) < 2:
        return body

    new_body: List[nodes.Node] = []
    i = 0
    while i < len(body):
        current = body[i]
        nxt = body[i + 1] if i + 1 < len(body) else None

        if (
            isinstance(current, nodes.VariableDeclaration)
            and len(current.declarations) == 1
            and isinstance(current.declarations[0].id, nodes.Identifier)
            and current.declarations[0].init is not None
            and _is_string_literal(current.declarations[0].init)
            and current.declarations[0].init.value == ""
            and isinstance(nxt, nodes.ForOfStatement)
            and isinstance(nxt.body, nodes.BlockStatement)
            and len(nxt.body.body) == 1
        ):
            decl = current.declarations[0]
            loop_stmt = nxt.body.body[0]
            loop_var = None
            if isinstance(nxt.left, nodes.Identifier):
                loop_var = nxt.left.name
            elif isinstance(nxt.left, nodes.VariableDeclaration) and len(nxt.left.declarations) == 1 and isinstance(nxt.left.declarations[0].id, nodes.Identifier):
                loop_var = nxt.left.declarations[0].id.name

            if loop_var and isinstance(loop_stmt, nodes.ExpressionStatement) and isinstance(loop_stmt.expression, nodes.AssignmentExpression):
                assign = loop_stmt.expression
                if (
                    assign.operator == "+="
                    and isinstance(assign.left, nodes.Identifier)
                    and assign.left.name == decl.id.name
                    and isinstance(assign.right, nodes.Identifier)
                    and assign.right.name == loop_var
                    and isinstance(nxt.right, (nodes.Identifier, nodes.ArrayExpression, nodes.StaticMemberExpression, nodes.ComputedMemberExpression))
                ):
                    join_call = nodes.CallExpression(
                        nodes.StaticMemberExpression(nxt.right, _make_identifier("join")),
                        [nodes.Literal("", '""')],
                    )
                    before_code = f"{_node_code(current)}\n{_node_code(nxt)}"
                    current.declarations[0].init = join_call
                    after_code = _node_code(current)
                    records.append(
                        OptimizationRecord(
                            line=_line_of(current),
                            description="String optimization: loop concatenation -> ''.join(...)",
                            before=before_code,
                            after=after_code,
                        )
                    )
                    new_body.append(current)
                    i += 2
                    continue

        new_body.append(current)
        i += 1

    return new_body


def _simplify_if_test(stmt: nodes.IfStatement, records: List[OptimizationRecord]) -> None:
    test = stmt.test
    if not isinstance(test, nodes.BinaryExpression):
        return

    if test.operator not in ("===", "=="):
        return

    if isinstance(test.right, nodes.Literal) and isinstance(test.right.value, bool):
        if test.right.value is True:
            _record(records, stmt, "Boolean comparison simplification", test, test.left)
            stmt.test = test.left
            return
        replacement = nodes.UnaryExpression("!", test.left, True)
        _record(records, stmt, "Boolean comparison simplification", test, replacement)
        stmt.test = replacement


def _remove_redundant_variable_declarations(body: List[nodes.Node], records: List[OptimizationRecord]) -> List[nodes.Node]:
    if len(body) < 2:
        return body

    new_body: List[nodes.Node] = []
    i = 0
    while i < len(body):
        current = body[i]
        if (
            i + 1 < len(body)
            and isinstance(current, nodes.VariableDeclaration)
            and isinstance(body[i + 1], nodes.VariableDeclaration)
            and len(current.declarations) == 1
            and len(body[i + 1].declarations) == 1
        ):
            d1 = current.declarations[0]
            d2 = body[i + 1].declarations[0]
            if isinstance(d1.id, nodes.Identifier) and isinstance(d2.id, nodes.Identifier) and d1.id.name == d2.id.name:
                records.append(
                    OptimizationRecord(
                        line=_line_of(current),
                        description=f"Removed redundant assignment to '{d1.id.name}'",
                        before=escodegen.generate(current),
                        after="(removed)",
                    )
                )
                i += 1
                continue
        new_body.append(current)
        i += 1

    return new_body


def _transform_statement(stmt: nodes.Node, mode: str, records: List[OptimizationRecord]) -> nodes.Node:
    if isinstance(stmt, nodes.ExpressionStatement):
        stmt.expression = _transform_expression(stmt.expression, mode, records)
        return stmt

    if isinstance(stmt, nodes.VariableDeclaration):
        for decl in stmt.declarations:
            if decl.init is not None:
                decl.init = _transform_expression(decl.init, mode, records)
        return stmt

    if isinstance(stmt, nodes.ReturnStatement) and stmt.argument is not None:
        stmt.argument = _transform_expression(stmt.argument, mode, records)
        return stmt

    if isinstance(stmt, nodes.IfStatement):
        stmt.test = _transform_expression(stmt.test, mode, records)
        _simplify_if_test(stmt, records)
        stmt.consequent = _transform_statement(stmt.consequent, mode, records)
        if stmt.alternate is not None:
            stmt.alternate = _transform_statement(stmt.alternate, mode, records)
        return stmt

    if isinstance(stmt, nodes.ForStatement):
        if stmt.init is not None and isinstance(stmt.init, nodes.Node):
            if isinstance(stmt.init, nodes.VariableDeclaration):
                for decl in stmt.init.declarations:
                    if decl.init is not None:
                        decl.init = _transform_expression(decl.init, mode, records)
            else:
                stmt.init = _transform_expression(stmt.init, mode, records)
        if stmt.test is not None:
            stmt.test = _transform_expression(stmt.test, mode, records)
        if stmt.update is not None:
            stmt.update = _transform_expression(stmt.update, mode, records)
        stmt.body = _transform_statement(stmt.body, mode, records)
        return stmt

    if isinstance(stmt, nodes.WhileStatement):
        stmt.test = _transform_expression(stmt.test, mode, records)
        stmt.body = _transform_statement(stmt.body, mode, records)
        return stmt

    if isinstance(stmt, nodes.BlockStatement):
        stmt.body = _transform_body(stmt.body, mode, records)
        return stmt

    if isinstance(stmt, nodes.FunctionDeclaration):
        if isinstance(stmt.body, nodes.BlockStatement):
            stmt.body.body = _transform_body(stmt.body.body, mode, records)
        return stmt

    if isinstance(stmt, nodes.FunctionExpression):
        if isinstance(stmt.body, nodes.BlockStatement):
            stmt.body.body = _transform_body(stmt.body.body, mode, records)
        return stmt

    if isinstance(stmt, nodes.ArrowFunctionExpression):
        if isinstance(stmt.body, nodes.BlockStatement):
            stmt.body.body = _transform_body(stmt.body.body, mode, records)
        else:
            stmt.body = _transform_expression(stmt.body, mode, records)
        return stmt

    if isinstance(stmt, nodes.ForStatement):
        if isinstance(stmt.body, nodes.BlockStatement):
            stmt.body.body = _transform_body(stmt.body.body, mode, records)
        return stmt

    if isinstance(stmt, (nodes.ForOfStatement, nodes.ForInStatement, nodes.WhileStatement, nodes.DoWhileStatement)):
        if isinstance(stmt.body, nodes.BlockStatement):
            stmt.body.body = _transform_body(stmt.body.body, mode, records)
        return stmt

    if isinstance(stmt, nodes.IfStatement):
        if isinstance(stmt.consequent, nodes.BlockStatement):
            stmt.consequent.body = _transform_body(stmt.consequent.body, mode, records)
        else:
            stmt.consequent = _transform_statement(stmt.consequent, mode, records)
        if stmt.alternate is not None:
            if isinstance(stmt.alternate, nodes.BlockStatement):
                stmt.alternate.body = _transform_body(stmt.alternate.body, mode, records)
            else:
                stmt.alternate = _transform_statement(stmt.alternate, mode, records)
        return stmt

    if isinstance(stmt, nodes.SwitchStatement):
        stmt.discriminant = _transform_expression(stmt.discriminant, mode, records)
        for case in stmt.cases:
            if case.test is not None:
                case.test = _transform_expression(case.test, mode, records)
            case.consequent = _transform_body(case.consequent, mode, records)
        return stmt

    return stmt


def _transform_body(body: List[nodes.Node], mode: str, records: List[OptimizationRecord]) -> List[nodes.Node]:
    transformed = [_transform_statement(stmt, mode, records) for stmt in body]

    if mode in ("both", "general"):
        transformed = _eliminate_dead_code(transformed, records)
        transformed = _inline_variable_returns(transformed, records)
        transformed = _reuse_common_subexpressions(transformed, records)
        transformed = _fuse_adjacent_loops(transformed, records)
        transformed = _string_concat_to_join(transformed, records)

    return transformed


def optimize_javascript_source(
    source: str,
    mode: str = "both",
    hotspots: Optional[List[dict[str, Any]]] = None,
) -> Tuple[str, List[OptimizationRecord]]:
    del hotspots

    records: List[OptimizationRecord] = []
    if not source.strip():
        return source, records

    tree = esprima.parseScript(source, {"loc": True})
    tree.body = _transform_body(tree.body, mode, records)

    optimized = escodegen.generate(tree)
    if source.endswith("\n") and not optimized.endswith("\n"):
        optimized += "\n"

    return optimized, records
