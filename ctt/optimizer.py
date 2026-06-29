import ast
import copy
import operator
from typing import Any, List, Optional, Set, Tuple

class OptimizationRecord:

    def __init__(self, line: int, description: str, before: str, after: str):
        self.line = line
        self.description = description
        self.before = before
        self.after = after

    def __repr__(self):
        return f"Line {self.line}: {self.description}"


class _HotspotScopedTransformer(ast.NodeTransformer):
    """Apply an inner transformer only to selected hotspot function bodies."""

    def __init__(self, inner: ast.NodeTransformer, hotspot_functions: Set[str], include_module: bool):
        super().__init__()
        self.inner = inner
        self.hotspot_functions = hotspot_functions
        self.include_module = include_module
        self.records: List[OptimizationRecord] = []

    def visit_Module(self, node: ast.Module) -> ast.AST:
        if self.include_module:
            before_len = len(getattr(self.inner, "records", []))
            updated = self.inner.visit(node)
            after_records = getattr(self.inner, "records", [])
            self.records.extend(after_records[before_len:])
            return updated

        # Only traverse into function/class definitions to keep edits in hotspot regions.
        new_body: List[ast.stmt] = []
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                new_body.append(self.visit(stmt))
            else:
                new_body.append(stmt)
        node.body = new_body
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        # Traverse class methods; optimize only hotspot method names.
        new_body: List[ast.stmt] = []
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                new_body.append(self.visit(stmt))
            else:
                new_body.append(stmt)
        node.body = new_body
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        if node.name in self.hotspot_functions:
            before_len = len(getattr(self.inner, "records", []))
            updated = self.inner.visit(node)
            after_records = getattr(self.inner, "records", [])
            self.records.extend(after_records[before_len:])
            return updated
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        if node.name in self.hotspot_functions:
            before_len = len(getattr(self.inner, "records", []))
            updated = self.inner.visit(node)
            after_records = getattr(self.inner, "records", [])
            self.records.extend(after_records[before_len:])
            return updated
        return node


# ---------------------------------------------------------------------------
# 1. Strength Reduction Transformer
# ---------------------------------------------------------------------------

class StrengthReductionTransformer(ast.NodeTransformer):
    MAX_EXPONENT = 4  

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)

        if not isinstance(node.op, ast.Pow):
            return node

        if not isinstance(node.right, ast.Constant) or not isinstance(node.right.value, int):
            return node

        exp = node.right.value
        if exp < 2 or exp > self.MAX_EXPONENT:
            return node

        before_code = ast.unparse(node)
        base = node.left
        result = copy.deepcopy(base)
        for _ in range(exp - 1):
            result = ast.BinOp(left=result, op=ast.Mult(), right=copy.deepcopy(base))

        after_code = ast.unparse(result)

        self.records.append(OptimizationRecord(
            line=getattr(node, "lineno", 0),
            description="Strength reduction: power → multiplication",
            before=before_code,
            after=after_code,
        ))

        return ast.copy_location(result, node)


# ---------------------------------------------------------------------------
# 2. Constant Folding Transformer
# ---------------------------------------------------------------------------

_SAFE_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_SAFE_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class ConstantFoldingTransformer(ast.NodeTransformer):

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        
        self.generic_visit(node)

        if not (isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant)):
            return node

        op_type = type(node.op)
        if op_type not in _SAFE_BINOPS:
            return node

        if op_type in (ast.FloorDiv, ast.Mod) and node.right.value == 0:
            return node

        if op_type is ast.Pow and isinstance(node.right.value, int) and node.right.value > 1000:
            return node

        try:
            result_value = _SAFE_BINOPS[op_type](node.left.value, node.right.value)
        except Exception:
            return node

        before_code = ast.unparse(node)
        new_node = ast.Constant(value=result_value)
        after_code = ast.unparse(new_node)

        self.records.append(OptimizationRecord(
            line=getattr(node, "lineno", 0),
            description="Constant folding",
            before=before_code,
            after=after_code,
        ))

        return ast.copy_location(new_node, node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        self.generic_visit(node)

        if not isinstance(node.operand, ast.Constant):
            return node

        op_type = type(node.op)
        if op_type not in _SAFE_UNARYOPS:
            return node

        try:
            result_value = _SAFE_UNARYOPS[op_type](node.operand.value)
        except Exception:
            return node

        before_code = ast.unparse(node)
        new_node = ast.Constant(value=result_value)
        after_code = ast.unparse(new_node)

        self.records.append(OptimizationRecord(
            line=getattr(node, "lineno", 0),
            description="Constant folding (unary)",
            before=before_code,
            after=after_code,
        ))

        return ast.copy_location(new_node, node)


# ---------------------------------------------------------------------------
# 3. Redundant Assignment Removal
# ---------------------------------------------------------------------------

class RedundantAssignmentRemover(ast.NodeTransformer):

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_Module(self, node: ast.Module) -> ast.Module:
        node.body = self._filter_body(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._filter_body(node.body)
        self.generic_visit(node)
        return node

    def _filter_body(self, body: List[ast.stmt]) -> List[ast.stmt]:
        if len(body) < 2:
            return body

        new_body: List[ast.stmt] = []
        i = 0
        while i < len(body):
            stmt = body[i]
            if (
                i + 1 < len(body)
                and isinstance(stmt, ast.Assign)
                and isinstance(body[i + 1], ast.Assign)
                and len(stmt.targets) == 1
                and len(body[i + 1].targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(body[i + 1].targets[0], ast.Name)
                and stmt.targets[0].id == body[i + 1].targets[0].id
                and self._is_pure_expression(stmt.value)
            ):
                var_name = stmt.targets[0].id
                self.records.append(OptimizationRecord(
                    line=getattr(stmt, "lineno", 0),
                    description=f"Removed redundant assignment to '{var_name}'",
                    before=ast.unparse(stmt),
                    after="(removed)",
                ))
                i += 1
                continue
            new_body.append(stmt)
            i += 1
        return new_body

    @staticmethod
    def _is_pure_expression(node: ast.expr) -> bool:
        if isinstance(node, (ast.Constant, ast.Name)):
            return True
        if isinstance(node, ast.BinOp):
            return (RedundantAssignmentRemover._is_pure_expression(node.left)
                    and RedundantAssignmentRemover._is_pure_expression(node.right))
        if isinstance(node, ast.UnaryOp):
            return RedundantAssignmentRemover._is_pure_expression(node.operand)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return all(RedundantAssignmentRemover._is_pure_expression(e) for e in node.elts)
        return False


# ---------------------------------------------------------------------------
# 4. Identity Operation Removal
# ---------------------------------------------------------------------------

class IdentityOperationRemover(ast.NodeTransformer):

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)

        left, right, op = node.left, node.right, node.op

        replacement = None
        desc = ""

        if isinstance(op, ast.Mult):
            if isinstance(right, ast.Constant) and right.value == 1:
                replacement = left
                desc = "x * 1 → x"
            elif isinstance(left, ast.Constant) and left.value == 1:
                replacement = right
                desc = "1 * x → x"

        elif isinstance(op, ast.Add):
            if isinstance(right, ast.Constant) and right.value == 0:
                replacement = left
                desc = "x + 0 → x"
            elif isinstance(left, ast.Constant) and left.value == 0:
                replacement = right
                desc = "0 + x → x"

        elif isinstance(op, ast.Sub):
            if isinstance(right, ast.Constant) and right.value == 0:
                replacement = left
                desc = "x - 0 → x"

        elif isinstance(op, ast.Pow):
            if isinstance(right, ast.Constant) and right.value == 1:
                replacement = left
                desc = "x ** 1 → x"

        elif isinstance(op, ast.FloorDiv):
            if isinstance(right, ast.Constant) and right.value == 1:
                replacement = left
                desc = "x // 1 → x"

        if replacement is not None:
            before_code = ast.unparse(node)
            after_code = ast.unparse(replacement)
            self.records.append(OptimizationRecord(
                line=getattr(node, "lineno", 0),
                description=f"Identity operation removal: {desc}",
                before=before_code,
                after=after_code,
            ))
            return ast.copy_location(replacement, node)

        return node


# ---------------------------------------------------------------------------
# 5. Boolean Comparison Simplification
# ---------------------------------------------------------------------------

class BooleanComparisonSimplifier(ast.NodeTransformer):

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)

        if len(node.ops) != 1 or len(node.comparators) != 1:
            return node

        op = node.ops[0]
        comparator = node.comparators[0]
        left = node.left

        if not isinstance(comparator, ast.Constant) or comparator.value not in (True, False):
            return node

        before_code = ast.unparse(node)
        replacement = None

        if isinstance(op, ast.Eq):
            if comparator.value is True:
                replacement = left
            else:
                replacement = ast.UnaryOp(op=ast.Not(), operand=left)
        elif isinstance(op, ast.NotEq):
            if comparator.value is True:
                replacement = ast.UnaryOp(op=ast.Not(), operand=left)
            else:
                replacement = left

        if replacement is not None:
            after_code = ast.unparse(replacement)
            self.records.append(OptimizationRecord(
                line=getattr(node, "lineno", 0),
                description="Boolean comparison simplification",
                before=before_code,
                after=after_code,
            ))
            return ast.copy_location(replacement, node)

        return node


# ---------------------------------------------------------------------------
# 6. Dead Code Elimination
# ---------------------------------------------------------------------------

class DeadCodeEliminator(ast.NodeTransformer):

    _TERMINAL = (ast.Return, ast.Break, ast.Continue)

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def _trim_body(self, body: List[ast.stmt]) -> List[ast.stmt]:

        new_body: List[ast.stmt] = []
        for stmt in body:
            new_body.append(stmt)
            if isinstance(stmt, self._TERMINAL):
                remaining = len(body) - len(new_body)
                if remaining > 0:
                    self.records.append(OptimizationRecord(
                        line=getattr(stmt, "lineno", 0),
                        description=f"Dead code elimination: removed {remaining} unreachable statement(s)",
                        before="(unreachable code after return/break/continue)",
                        after="(removed)",
                    ))
                break
        return new_body

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        node.body = self._trim_body(node.body)
        return node

    def visit_For(self, node: ast.For) -> ast.For:
        self.generic_visit(node)
        node.body = self._trim_body(node.body)
        return node

    def visit_While(self, node: ast.While) -> ast.While:
        self.generic_visit(node)
        node.body = self._trim_body(node.body)
        return node


# ---------------------------------------------------------------------------
# 7. List Membership to Set Membership
# ---------------------------------------------------------------------------

class ListToSetMembershipTransformer(ast.NodeTransformer):

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)

        new_ops = list(node.ops)
        new_comparators = list(node.comparators)
        changed = False

        for idx, (op, comp) in enumerate(zip(node.ops, node.comparators)):
            if isinstance(op, (ast.In, ast.NotIn)) and isinstance(comp, ast.List):
                if all(isinstance(elt, ast.Constant) for elt in comp.elts):
                    before_code = ast.unparse(node)
                    new_set = ast.Set(elts=comp.elts)
                    ast.copy_location(new_set, comp)
                    new_comparators[idx] = new_set
                    changed = True

        if changed:
            new_node = ast.Compare(left=node.left, ops=new_ops, comparators=new_comparators)
            ast.copy_location(new_node, node)
            after_code = ast.unparse(new_node)
            self.records.append(OptimizationRecord(
                line=getattr(node, "lineno", 0),
                description="Membership test: list → set (O(n) → O(1) lookup)",
                before=before_code,
                after=after_code,
            ))
            return new_node

        return node


# ---------------------------------------------------------------------------
# 8. Loop-Append to List Comprehension
# ---------------------------------------------------------------------------

class LoopAppendToComprehension(ast.NodeTransformer):

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_Module(self, node: ast.Module) -> ast.Module:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    def _transform_body(self, body: List[ast.stmt]) -> List[ast.stmt]:
        new_body: List[ast.stmt] = []
        i = 0
        while i < len(body):
            if (
                i + 1 < len(body)
                and isinstance(body[i], ast.Assign)
                and len(body[i].targets) == 1
                and isinstance(body[i].targets[0], ast.Name)
                and isinstance(body[i].value, ast.List)
                and len(body[i].value.elts) == 0
                and isinstance(body[i + 1], ast.For)
            ):
                assign_stmt = body[i]
                for_stmt = body[i + 1]
                var_name = assign_stmt.targets[0].id

                if (
                    len(for_stmt.body) == 1
                    and isinstance(for_stmt.body[0], ast.Expr)
                    and isinstance(for_stmt.body[0].value, ast.Call)
                    and isinstance(for_stmt.body[0].value.func, ast.Attribute)
                    and for_stmt.body[0].value.func.attr == "append"
                    and isinstance(for_stmt.body[0].value.func.value, ast.Name)
                    and for_stmt.body[0].value.func.value.id == var_name
                    and len(for_stmt.body[0].value.args) == 1
                    and not for_stmt.orelse
                ):
                    append_arg = for_stmt.body[0].value.args[0]
                    target = for_stmt.target
                    iter_expr = for_stmt.iter

                    comp = ast.ListComp(
                        elt=append_arg,
                        generators=[ast.comprehension(
                            target=target,
                            iter=iter_expr,
                            ifs=[],
                            is_async=0,
                        )],
                    )
                    new_assign = ast.Assign(
                        targets=[ast.Name(id=var_name, ctx=ast.Store())],
                        value=comp,
                        lineno=assign_stmt.lineno,
                    )
                    ast.copy_location(new_assign, assign_stmt)

                    before_code = f"{var_name} = []\\nfor {ast.unparse(target)} in {ast.unparse(iter_expr)}:\\n    {var_name}.append({ast.unparse(append_arg)})"
                    after_code = ast.unparse(new_assign)

                    self.records.append(OptimizationRecord(
                        line=getattr(assign_stmt, "lineno", 0),
                        description="Loop-append → list comprehension",
                        before=before_code,
                        after=after_code,
                    ))

                    new_body.append(new_assign)
                    i += 2
                    continue

            new_body.append(body[i])
            i += 1
        return new_body


# ---------------------------------------------------------------------------
# 9. Loop Fusion (adjacent loops over same iterator)
# ---------------------------------------------------------------------------

class LoopFusionTransformer(ast.NodeTransformer):

    _CONTROL_FLOW_NODES = (
        ast.Break,
        ast.Continue,
        ast.Return,
        ast.Raise,
        ast.Yield,
        ast.YieldFrom,
        ast.Await,
    )

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_Module(self, node: ast.Module) -> ast.Module:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    @classmethod
    def _contains_control_flow(cls, stmts: List[ast.stmt]) -> bool:
        for stmt in stmts:
            if any(isinstance(n, cls._CONTROL_FLOW_NODES) for n in ast.walk(stmt)):
                return True
        return False

    @staticmethod
    def _ast_equal(a: ast.AST, b: ast.AST) -> bool:
        return ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)

    def _transform_body(self, body: List[ast.stmt]) -> List[ast.stmt]:
        new_body: List[ast.stmt] = []
        i = 0
        while i < len(body):
            if (
                i + 1 < len(body)
                and isinstance(body[i], ast.For)
                and isinstance(body[i + 1], ast.For)
            ):
                first = body[i]
                second = body[i + 1]

                if (
                    not first.orelse
                    and not second.orelse
                    and self._ast_equal(first.target, second.target)
                    and self._ast_equal(first.iter, second.iter)
                    and not self._contains_control_flow(first.body)
                    and not self._contains_control_flow(second.body)
                ):
                    fused = ast.For(
                        target=copy.deepcopy(first.target),
                        iter=copy.deepcopy(first.iter),
                        body=copy.deepcopy(first.body + second.body),
                        orelse=[],
                        type_comment=getattr(first, "type_comment", None),
                    )
                    ast.copy_location(fused, first)

                    before_code = f"{ast.unparse(first)}\n{ast.unparse(second)}"
                    after_code = ast.unparse(fused)
                    self.records.append(OptimizationRecord(
                        line=getattr(first, "lineno", 0),
                        description="Loop fusion: merged adjacent loops over same iterator",
                        before=before_code,
                        after=after_code,
                    ))

                    new_body.append(fused)
                    i += 2
                    continue

            new_body.append(body[i])
            i += 1
        return new_body


# ---------------------------------------------------------------------------
# 10. No-op Loop Elimination
# ---------------------------------------------------------------------------

class NoOpLoopEliminator(ast.NodeTransformer):

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_Module(self, node: ast.Module) -> ast.Module:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    def _transform_body(self, body: List[ast.stmt]) -> List[ast.stmt]:
        new_body: List[ast.stmt] = []
        for stmt in body:
            if isinstance(stmt, ast.For) and not stmt.orelse and stmt.body and all(isinstance(s, ast.Pass) for s in stmt.body):
                self.records.append(OptimizationRecord(
                    line=getattr(stmt, "lineno", 0),
                    description="No-op loop elimination: removed pass-only for loop",
                    before=ast.unparse(stmt),
                    after="(removed)",
                ))
                continue
            new_body.append(stmt)
        return new_body


# ---------------------------------------------------------------------------
# 11. Variable Inlining (assign then immediate return)
# ---------------------------------------------------------------------------

class VariableInliningTransformer(ast.NodeTransformer):

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    @staticmethod
    def _is_safe_expr(expr: ast.expr) -> bool:
        if isinstance(expr, (ast.Constant, ast.Name)):
            return True
        if isinstance(expr, ast.BinOp):
            return VariableInliningTransformer._is_safe_expr(expr.left) and VariableInliningTransformer._is_safe_expr(expr.right)
        if isinstance(expr, ast.UnaryOp):
            return VariableInliningTransformer._is_safe_expr(expr.operand)
        if isinstance(expr, (ast.Tuple, ast.List, ast.Set)):
            return all(VariableInliningTransformer._is_safe_expr(e) for e in expr.elts)
        if isinstance(expr, ast.Dict):
            return all(
                (k is None or VariableInliningTransformer._is_safe_expr(k))
                and VariableInliningTransformer._is_safe_expr(v)
                for k, v in zip(expr.keys, expr.values)
            )
        return False

    def _transform_body(self, body: List[ast.stmt]) -> List[ast.stmt]:
        if len(body) < 2:
            return body

        new_body: List[ast.stmt] = []
        i = 0
        while i < len(body):
            if (
                i + 1 < len(body)
                and isinstance(body[i], ast.Assign)
                and isinstance(body[i + 1], ast.Return)
                and len(body[i].targets) == 1
                and isinstance(body[i].targets[0], ast.Name)
                and isinstance(body[i + 1].value, ast.Name)
                and body[i].targets[0].id == body[i + 1].value.id
                and self._is_safe_expr(body[i].value)
            ):
                assign_stmt = body[i]
                ret_stmt = body[i + 1]
                replacement = ast.Return(value=copy.deepcopy(assign_stmt.value))
                ast.copy_location(replacement, ret_stmt)

                self.records.append(OptimizationRecord(
                    line=getattr(assign_stmt, "lineno", 0),
                    description="Variable inlining: assignment inlined into return",
                    before=f"{ast.unparse(assign_stmt)}\n{ast.unparse(ret_stmt)}",
                    after=ast.unparse(replacement),
                ))

                new_body.append(replacement)
                i += 2
                continue

            new_body.append(body[i])
            i += 1

        return new_body


# ---------------------------------------------------------------------------
# 12. Common Subexpression Reuse (consecutive identical assigns)
# ---------------------------------------------------------------------------

class CommonSubexpressionReuseTransformer(ast.NodeTransformer):

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_Module(self, node: ast.Module) -> ast.Module:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    @staticmethod
    def _is_safe_expr(expr: ast.expr) -> bool:
        return RedundantAssignmentRemover._is_pure_expression(expr)

    @staticmethod
    def _contains_name(expr: ast.AST, name: str) -> bool:
        return any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(expr))

    @staticmethod
    def _ast_equal(a: ast.AST, b: ast.AST) -> bool:
        return ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)

    def _transform_body(self, body: List[ast.stmt]) -> List[ast.stmt]:
        if len(body) < 2:
            return body

        new_body: List[ast.stmt] = []
        i = 0
        while i < len(body):
            if (
                i + 1 < len(body)
                and isinstance(body[i], ast.Assign)
                and isinstance(body[i + 1], ast.Assign)
                and len(body[i].targets) == 1
                and len(body[i + 1].targets) == 1
                and isinstance(body[i].targets[0], ast.Name)
                and isinstance(body[i + 1].targets[0], ast.Name)
            ):
                first = body[i]
                second = body[i + 1]
                first_name = first.targets[0].id
                second_name = second.targets[0].id

                if (
                    first_name != second_name
                    and self._is_safe_expr(first.value)
                    and self._is_safe_expr(second.value)
                    and self._ast_equal(first.value, second.value)
                    and not self._contains_name(second.value, first_name)
                ):
                    before_code = ast.unparse(second)
                    second.value = ast.Name(id=first_name, ctx=ast.Load())
                    ast.copy_location(second.value, second)
                    after_code = ast.unparse(second)

                    self.records.append(OptimizationRecord(
                        line=getattr(second, "lineno", 0),
                        description="Common subexpression reuse: reused previous computed value",
                        before=before_code,
                        after=after_code,
                    ))

            new_body.append(body[i])
            i += 1

        return new_body


# ---------------------------------------------------------------------------
# 13. String Concatenation Loop to join()
# ---------------------------------------------------------------------------

class StringConcatLoopToJoinTransformer(ast.NodeTransformer):

    def __init__(self):
        super().__init__()
        self.records: List[OptimizationRecord] = []

    def visit_Module(self, node: ast.Module) -> ast.Module:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._transform_body(node.body)
        self.generic_visit(node)
        return node

    def _transform_body(self, body: List[ast.stmt]) -> List[ast.stmt]:
        new_body: List[ast.stmt] = []
        i = 0
        while i < len(body):
            if (
                i + 1 < len(body)
                and isinstance(body[i], ast.Assign)
                and isinstance(body[i + 1], ast.For)
                and len(body[i].targets) == 1
                and isinstance(body[i].targets[0], ast.Name)
                and isinstance(body[i].value, ast.Constant)
                and body[i].value.value == ""
            ):
                assign_stmt = body[i]
                for_stmt = body[i + 1]
                var_name = assign_stmt.targets[0].id

                if (
                    len(for_stmt.body) == 1
                    and not for_stmt.orelse
                    and isinstance(for_stmt.target, ast.Name)
                    and isinstance(for_stmt.body[0], ast.AugAssign)
                    and isinstance(for_stmt.body[0].target, ast.Name)
                    and for_stmt.body[0].target.id == var_name
                    and isinstance(for_stmt.body[0].op, ast.Add)
                    and isinstance(for_stmt.body[0].value, ast.Name)
                    and for_stmt.body[0].value.id == for_stmt.target.id
                ):
                    join_call = ast.Call(
                        func=ast.Attribute(value=ast.Constant(value=""), attr="join", ctx=ast.Load()),
                        args=[copy.deepcopy(for_stmt.iter)],
                        keywords=[],
                    )
                    new_assign = ast.Assign(
                        targets=[ast.Name(id=var_name, ctx=ast.Store())],
                        value=join_call,
                        lineno=assign_stmt.lineno,
                    )
                    ast.copy_location(new_assign, assign_stmt)

                    before_code = f"{ast.unparse(assign_stmt)}\n{ast.unparse(for_stmt)}"
                    after_code = ast.unparse(new_assign)
                    self.records.append(OptimizationRecord(
                        line=getattr(assign_stmt, "lineno", 0),
                        description="String optimization: loop concatenation -> ''.join(...)",
                        before=before_code,
                        after=after_code,
                    ))

                    new_body.append(new_assign)
                    i += 2
                    continue

            new_body.append(body[i])
            i += 1

        return new_body


def _build_transformers(mode: str) -> List[ast.NodeTransformer]:
    if mode == "energy":
        transformer_types = [
            ConstantFoldingTransformer,
            StrengthReductionTransformer,
            ListToSetMembershipTransformer,
            LoopAppendToComprehension,
            LoopFusionTransformer,
            NoOpLoopEliminator,
            StringConcatLoopToJoinTransformer,
        ]
    elif mode == "general":
        transformer_types = [
            IdentityOperationRemover,
            BooleanComparisonSimplifier,
            DeadCodeEliminator,
            RedundantAssignmentRemover,
            VariableInliningTransformer,
            CommonSubexpressionReuseTransformer,
        ]
    else:
        transformer_types = [
            ConstantFoldingTransformer,
            StrengthReductionTransformer,
            IdentityOperationRemover,
            BooleanComparisonSimplifier,
            DeadCodeEliminator,
            RedundantAssignmentRemover,
            ListToSetMembershipTransformer,
            LoopAppendToComprehension,
            LoopFusionTransformer,
            NoOpLoopEliminator,
            VariableInliningTransformer,
            CommonSubexpressionReuseTransformer,
            StringConcatLoopToJoinTransformer,
        ]

    return [transformer_type() for transformer_type in transformer_types]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def optimize_ast(
    tree: ast.Module,
    mode: str = "both",
    hotspots: Optional[List[dict[str, Any]]] = None,
) -> Tuple[ast.Module, List[OptimizationRecord]]:
    all_records: List[OptimizationRecord] = []

    tree = copy.deepcopy(tree)

    transformers = _build_transformers(mode)

    if hotspots is None:
        for transformer in transformers:
            tree = transformer.visit(tree)
            all_records.extend(transformer.records)
    else:
        hotspot_functions = {
            str(h.get("function", ""))
            for h in hotspots
            if isinstance(h, dict) and h.get("function")
        }
        include_module = "<module>" in hotspot_functions

        # If profiling produced no actionable names, keep backward-compatible full optimization.
        if not hotspot_functions:
            for transformer in transformers:
                tree = transformer.visit(tree)
                all_records.extend(transformer.records)
            ast.fix_missing_locations(tree)
            return tree, all_records

        for transformer in transformers:
            scoped = _HotspotScopedTransformer(transformer, hotspot_functions, include_module)
            tree = scoped.visit(tree)
            all_records.extend(scoped.records)

    ast.fix_missing_locations(tree)

    return tree, all_records
