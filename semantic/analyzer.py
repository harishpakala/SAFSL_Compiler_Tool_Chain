'''
Created on Aug 4, 2026

@author: haris
'''
from safsl_ast.nodes import (
    ProcessNode,
    AssignmentNode,
    IfNode,
    Operation,
    Identifier,
    Literal
)


class SemanticAnalyzer:

    def __init__(self, reference_table):
        self.reference_table = reference_table

    def analyze_specification(self, specification):

        for process in specification.processes:
            self.analyze_process(process)



    def analyze_process(self, process: ProcessNode):

        if process.body:
            for statement in process.body.statements:
                self.analyze_statement(statement)



    def analyze_statement(self, statement):

        if isinstance(statement, AssignmentNode):

            self.check_assignment(statement)


        elif isinstance(statement, IfNode):

            self.check_expression(statement.condition)

            for stmt in statement.statements:
                self.analyze_statement(stmt)



    def check_assignment(self, statement):

        target = statement.target

        target_type = self.get_semantic_type(target)


        value_type = self.check_expression(
            statement.value.expression
        )


        if statement.operator == "assignS":

            if target_type != value_type:

                raise Exception(
                    f"Semantic assignment error: "
                    f"{target_type} <- {value_type}"
                )



    def check_expression(self, expr):

        if isinstance(expr, Identifier):

            return self.get_semantic_type(
                expr.name
            )


        elif isinstance(expr, Literal):

            if hasattr(expr, "unit"):
                return expr.unit

            return None


        elif isinstance(expr, Operation):

            return self.check_operation(expr)


        raise Exception(
            f"Unsupported expression {expr}"
        )



    def check_operation(self, operation):

        operator = operation.operator


        operands = [
            self.check_expression(op)
            for op in operation.operands
        ]


        if operator.endswith("S"):

            # semantic operator

            if None in operands:
                raise Exception(
                    f"{operator} requires semantic operands. "
                    f"Use qualified literals like 10@QUDT:K"
                )


            first = operands[0]


            for operand in operands[1:]:

                if operand != first:

                    raise Exception(
                        f"Semantic mismatch in {operator}: "
                        f"{first} != {operand}"
                    )


            return first


        else:
            return None



    def get_semantic_type(self, identifier):

        if identifier not in self.reference_table:

            raise Exception(
                f"Unknown identifier {identifier}"
            )


        reference = self.reference_table[identifier]


        if hasattr(reference, "semantic_id"):

            return reference.semantic_id


        if hasattr(reference, "resolved"):

            if reference.resolved:
                return reference.resolved.semantic_id

        return None